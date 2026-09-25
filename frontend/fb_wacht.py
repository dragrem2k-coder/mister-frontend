#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dragend - Wache am Bildspeicher.

WOZU DAS HIER DA IST

Bei 1920x1080 blitzt bei einem Geraet MiSTers eigenes Menuebild durch
das Frontend, ein bis zwei Bilder lang, mehrmals je Minute. Bei halber
Aufloesung nie. Drei Erklaerungen sind inzwischen nachgemessen und
gestorben:

  1. MiSTer zeichnet dazwischen, weil ihn unsere Eingaben erreichen.
     Widerlegt: er wacht beim Scrollen nicht oefter auf als im
     Leerlauf (zuck_probe.py, 39 gegen 52 je Minute).
  2. Uebersprungenes Vsync. Widerlegt: Vollbilder warten seit Build 93
     immer.
  3. Der Speicherbus ist dicht, weil 7,9 MB am Stueck geschrieben
     werden. Widerlegt mit Build 181: mit 16 Haeppchen und 500 us
     Pause brauchte der Flip 34 ms statt 12,6 - dreimal so entzerrt,
     und das Zucken blieb unveraendert.
  4. Es haengt am Cover-Weg, weil die Dekodierungen ungefaehr so oft
     kommen wie das Zucken. Widerlegt: es zuckt auch in Kategorien
     ohne ein einziges Cover.

Uebrig bleiben genau zwei Moeglichkeiten, und sie schliessen einander
aus:

  A) JEMAND SCHREIBT in den Bildspeicher hinein. Dann ist unser Bild
     dort tatsaechlich weg, und wir koennen es nachweisen, indem wir
     hineinschauen.

  B) NIEMAND SCHREIBT, die Anzeige-Ebene wird kurz WEGGESCHALTET.
     Dann steht unser Bild unveraendert im Speicher, waehrend auf dem
     Fernseher etwas anderes zu sehen ist.

Dieses Werkzeug entscheidet zwischen A und B - und das ist der ganze
Zweck. Es misst nichts und repariert nichts.

SO GEHT ES VOR

Es legt ein Muster in den Bildspeicher, bei dem jede Position
eindeutig ist, und laesst unten einen Balken laufen, damit weiterhin
Bild fuer Bild geschrieben wird wie beim Frontend. Den oberen,
ruhenden Teil fasst es danach NIE WIEDER AN. Dann schaut es alle
Viertelsekunde nach, ob dort noch steht, was es hingeschrieben hat.

  Muster kaputt  -> A: jemand schreibt hinein. Das Werkzeug sagt auch,
                    WO und WANN.
  Muster heil, aber es zuckt sichtbar -> B: die Ebene wird
                    weggeschaltet. Dann liegt es unterhalb von uns.

Nebenbei wird jede Viertelsekunde yoffset mitgelesen: aendert der
sich, hat der Bildspeicher mehr als eine Seite und es wird zwischen
ihnen umgeschaltet - das waere die einfachste denkbare Erklaerung fuer
B, und zwar eine, gegen die wir etwas tun koennten.

AUFRUF

    python3 fb_wacht.py              nur nachsehen, nichts anfassen
    python3 fb_wacht.py --wache      30 Sekunden Wache (Bild wird belegt)
    python3 fb_wacht.py --wache 60   ebenso, 60 Sekunden

Fuer --wache muss das Frontend BEENDET sein (F12), sonst schreiben
zwei Programme in dasselbe Bild und das Ergebnis ist wertlos. Das
Werkzeug prueft das und weigert sich.

Das Ergebnis steht am Ende auf dem Bildschirm und in
/tmp/dragend_fbwacht.txt.

Auf der Karte wird nichts veraendert.
"""
import fcntl
import mmap
import os
import struct
import subprocess
import sys
import time

FBIOGET_VSCREENINFO = 0x4600
FBIOGET_FSCREENINFO = 0x4602
FBIO_WAITFORVSYNC = 0x40044620

BERICHT = "/tmp/dragend_fbwacht.txt"

_zeilen = []


def sag(text=""):
    print(text)
    _zeilen.append(text)


def bericht_schreiben():
    try:
        with open(BERICHT, "w") as f:
            f.write("\n".join(_zeilen) + "\n")
        print()
        print("Das steht auch in %s" % BERICHT)
    except OSError as e:
        print("(Bericht liess sich nicht schreiben: %s)" % e)


# ---------------------------------------------------------------------------
# Was der Treiber ueber sich selbst sagt
# ---------------------------------------------------------------------------
def vscreeninfo(fd):
    """Die veraenderlichen Angaben - Aufloesung, virtuelle Groesse und
    vor allem der Versatz, mit dem angezeigt wird."""
    roh = bytearray(160)
    fcntl.ioctl(fd, FBIOGET_VSCREENINFO, roh, True)
    (xres, yres, xres_v, yres_v, xoff, yoff, bpp, grau) = \
        struct.unpack_from("<8I", roh)
    return {"xres": xres, "yres": yres, "xres_virtual": xres_v,
            "yres_virtual": yres_v, "xoffset": xoff, "yoffset": yoff,
            "bpp": bpp, "grayscale": grau}


def fscreeninfo(fd):
    """Die festen Angaben - wo der Speicher liegt und wie gross er ist.

    smem_start ist ein unsigned long, auf 32-Bit-ARM also vier Bytes;
    die Zeilenlaenge steht je nach Wortbreite an zwei moeglichen
    Stellen. Beide werden gelesen und mitgeteilt, statt eine davon zu
    raten - wer das hier spaeter liest, soll die Rohwerte sehen."""
    roh = bytearray(160)
    fcntl.ioctl(fd, FBIOGET_FSCREENINFO, roh, True)
    kennung = bytes(roh[0:16]).split(b"\0")[0].decode("ascii", "replace")
    smem_start, smem_len = struct.unpack_from("<II", roh, 16)
    typ, = struct.unpack_from("<I", roh, 24)
    sichtbar, = struct.unpack_from("<I", roh, 32)
    zeile32, = struct.unpack_from("<I", roh, 44)
    zeile64, = struct.unpack_from("<I", roh, 52)
    return {"id": kennung, "smem_start": smem_start, "smem_len": smem_len,
            "type": typ, "visual": sichtbar,
            "line_length@44": zeile32, "line_length@52": zeile64}


def zeilenlaenge(v, f):
    """Die Zeilenlaenge, die zur Breite passt - dieselbe Wahl wie in
    fe/framebuffer.py, damit die Wache genau den Bereich prueft, den
    das Frontend auch beschreibt."""
    breite_byte = v["xres"] * (v["bpp"] // 8 or 4)
    for schluessel in ("line_length@44", "line_length@52"):
        wert = f[schluessel]
        if breite_byte <= wert <= 8192 * 4:
            return wert
    return breite_byte


def frontend_laeuft():
    try:
        aus = subprocess.check_output(["ps"], stderr=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError):
        return False
    for zeile in aus.decode("utf-8", "replace").splitlines():
        if "frontend.py" in zeile and "fb_wacht" not in zeile:
            return True
    return False


def einblenden(fd, groesse, f):
    """Erst der normale Weg, dann der ueber /dev/mem - genau wie im
    Frontend (Build 168), damit die Wache auf demselben Speicher
    arbeitet wie das Frontend und nicht auf einem anderen."""
    try:
        return mmap.mmap(fd, groesse, mmap.MAP_SHARED,
                         mmap.PROT_READ | mmap.PROT_WRITE), "/dev/fb0"
    except (OSError, ValueError) as e:
        sag("   mmap auf /dev/fb0 ging nicht (%s) - versuche /dev/mem" % e)
    start = f["smem_start"]
    if not start or start % mmap.PAGESIZE:
        raise OSError("kein brauchbarer physischer Anfang (0x%08X)" % start)
    mfd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
    return mmap.mmap(mfd, groesse, mmap.MAP_SHARED,
                     mmap.PROT_READ | mmap.PROT_WRITE, offset=start), "/dev/mem"


# ---------------------------------------------------------------------------
def abschnitt_nachsehen(fd):
    v = vscreeninfo(fd)
    f = fscreeninfo(fd)
    zl = zeilenlaenge(v, f)
    eine_seite = zl * v["yres"]

    sag("--------------------------------------------------------------")
    sag("WAS DER TREIBER MELDET")
    sag("--------------------------------------------------------------")
    sag("   Name            : %s" % f["id"])
    sag("   sichtbar        : %d x %d, %d bpp"
        % (v["xres"], v["yres"], v["bpp"]))
    sag("   virtuell        : %d x %d"
        % (v["xres_virtual"], v["yres_virtual"]))
    sag("   Versatz         : x=%d  y=%d" % (v["xoffset"], v["yoffset"]))
    sag("   Zeilenlaenge    : %d Bytes  (aus Feld %s)"
        % (zl, "44" if zl == f["line_length@44"] else "52/berechnet"))
    sag("   physisch        : 0x%08X, %d Bytes gemeldet"
        % (f["smem_start"], f["smem_len"]))
    sag("   eine Bildseite  : %d Bytes (%.1f MB)"
        % (eine_seite, eine_seite / 1048576.0))
    sag("")

    sag("--------------------------------------------------------------")
    sag("GIBT ES MEHR ALS EINE BILDSEITE?")
    sag("--------------------------------------------------------------")
    sag("   Das ist die Frage, auf die es ankommt. Liegt im Speicher")
    sag("   Platz fuer zwei Bilder, kann die Anzeige zwischen ihnen")
    sag("   umschalten - und auf der zweiten Seite steht dann noch")
    sag("   MiSTers altes Menuebild.")
    sag("")
    if f["smem_len"] and eine_seite:
        seiten = float(f["smem_len"]) / eine_seite
        sag("   gemeldeter Speicher / eine Seite = %.2f" % seiten)
        if seiten >= 1.9:
            sag("   -> PLATZ FUER MEHR ALS EINE SEITE. Das ist ein Treffer.")
        elif seiten >= 1.05:
            sag("   -> etwas mehr als eine Seite, aber keine zweite ganze.")
        else:
            sag("   -> nur eine Seite. Diese Erklaerung faellt damit weg.")
    else:
        sag("   (der Treiber meldet keine Groesse - keine Aussage moeglich)")
    if v["yres_virtual"] > v["yres"]:
        sag("   yres_virtual ist groesser als yres (%d > %d) - der Treiber"
            % (v["yres_virtual"], v["yres"]))
        sag("   raeumt also selbst ein, dass mehr als ein Bild hineinpasst.")
    else:
        sag("   yres_virtual = yres: der Treiber kennt nur ein Bild.")
    sag("")
    return v, f, zl, eine_seite


# ---------------------------------------------------------------------------
def muster(laenge, versatz=0):
    """Ein Muster, in dem jede Position eindeutig ist. Wird etwas
    darueber geschrieben, faellt es auch dann auf, wenn der fremde
    Inhalt zufaellig aehnlich aussieht."""
    return bytes(bytearray(((i + versatz) * 7 + ((i + versatz) >> 11)) & 255
                           for i in range(laenge)))


def abschnitt_wache(fd, v, f, zl, eine_seite, dauer):
    sag("--------------------------------------------------------------")
    sag("WACHE - %d Sekunden" % dauer)
    sag("--------------------------------------------------------------")

    if frontend_laeuft():
        sag("   ABGEBROCHEN: das Frontend laeuft noch.")
        sag("   Zwei Programme im selben Bild ergeben kein Ergebnis,")
        sag("   sondern Matsch. Erst F12 druecken, dann noch einmal.")
        return False

    mm, weg = einblenden(fd, eine_seite, f)
    sag("   eingeblendet ueber %s" % weg)

    # Oben drei Viertel: einmal beschrieben, danach unberuehrt.
    # Unten ein Viertel: der laufende Balken, damit weiterhin Bild fuer
    # Bild geschrieben wird - ohne das waere die Lage eine andere als
    # beim Frontend.
    ruhe_h = (v["yres"] * 3) // 4
    ruhe_len = ruhe_h * zl
    ruhe_soll = muster(ruhe_len)
    mm[0:ruhe_len] = ruhe_soll
    mm[ruhe_len:eine_seite] = b"\x00" * (eine_seite - ruhe_len)
    sag("   ruhender Teil   : Zeile 0 bis %d (%d Bytes)" % (ruhe_h, ruhe_len))
    sag("   Balken unten    : Zeile %d bis %d" % (ruhe_h, v["yres"]))
    sag("")
    sag("   Jetzt zusehen. Zuckt es auf dem Fernseher?")
    sag("")

    # Stichproben: 64 gleichmaessig verteilte Zeilen. Ein fremdes Bild
    # deckt praktisch immer mehrere davon ab, und eine Stichprobe ist
    # schnell genug, um viermal je Sekunde zu schauen. Am Ende wird
    # einmal ALLES verglichen, damit auch ein kleiner Fleck auffaellt.
    proben = [(i * ruhe_h // 64) * zl for i in range(64)]

    t0 = time.monotonic()
    ende = t0 + dauer
    naechste_probe = t0
    balken = 0
    treffer = []
    yoff_wechsel = []
    yoff_vorher = v["yoffset"]
    runden = 0
    balken_zeile = bytes(bytearray([255, 255, 255, 255] * v["xres"]))
    leer_zeile = b"\x00" * zl

    while time.monotonic() < ende:
        # Balken: eine helle Zeile im unteren Viertel, Bild fuer Bild
        # eine weiter. Geschrieben wird mit Vsync wie im Frontend.
        try:
            fcntl.ioctl(fd, FBIO_WAITFORVSYNC, struct.pack("I", 0))
        except OSError:
            time.sleep(0.016)
        y = ruhe_h + (balken % (v["yres"] - ruhe_h))
        vor = ruhe_h + ((balken - 1) % (v["yres"] - ruhe_h))
        mm[vor * zl:vor * zl + zl] = leer_zeile
        mm[y * zl:y * zl + zl] = balken_zeile[:zl]
        balken += 1

        jetzt = time.monotonic()
        if jetzt >= naechste_probe:
            naechste_probe = jetzt + 0.25
            runden += 1
            for p in proben:
                ist = mm[p:p + zl]
                if ist != ruhe_soll[p:p + zl]:
                    treffer.append((jetzt - t0, p // zl))
                    # Wieder hinschreiben, sonst meldet jede weitere
                    # Runde denselben Fleck noch einmal.
                    mm[p:p + zl] = ruhe_soll[p:p + zl]
            neu = vscreeninfo(fd)["yoffset"]
            if neu != yoff_vorher:
                yoff_wechsel.append((jetzt - t0, yoff_vorher, neu))
                yoff_vorher = neu

    # Zum Schluss einmal alles.
    ganz_kaputt = []
    ist_ganz = mm[0:ruhe_len]
    if ist_ganz != ruhe_soll:
        for z in range(ruhe_h):
            a = z * zl
            if ist_ganz[a:a + zl] != ruhe_soll[a:a + zl]:
                ganz_kaputt.append(z)

    mm[0:eine_seite] = b"\x00" * eine_seite
    mm.close()

    sag("   %d Bilder geschrieben, %d Stichproben-Runden"
        % (balken, runden))
    sag("")
    sag("--------------------------------------------------------------")
    sag("ERGEBNIS")
    sag("--------------------------------------------------------------")
    if treffer or ganz_kaputt:
        sag("   A: JEMAND SCHREIBT IN DEN BILDSPEICHER.")
        sag("")
        if treffer:
            sag("   Waehrend der Wache %d mal erwischt:" % len(treffer))
            for t, z in treffer[:20]:
                sag("      nach %6.2f s in Zeile %d" % (t, z))
            if len(treffer) > 20:
                sag("      ... und %d weitere" % (len(treffer) - 20))
        if ganz_kaputt:
            sag("   Am Ende waren %d von %d ruhenden Zeilen veraendert"
                % (len(ganz_kaputt), ruhe_h))
            sag("   (von Zeile %d bis %d)"
                % (ganz_kaputt[0], ganz_kaputt[-1]))
        sag("")
        sag("   Damit ist es kein Anzeigeproblem, sondern ein fremder")
        sag("   Schreibzugriff. Die Zeilennummern sagen, welcher Teil")
        sag("   des Bildes ueberschrieben wird.")
    else:
        sag("   B: NIEMAND SCHREIBT HINEIN.")
        sag("")
        sag("   Das Muster stand nach %d Sekunden unveraendert da -" % dauer)
        sag("   jede einzelne der %d ruhenden Zeilen." % ruhe_h)
        sag("")
        sag("   Hat es waehrenddessen sichtbar gezuckt, dann wird die")
        sag("   Anzeige-Ebene kurz weggeschaltet, ohne dass an unserem")
        sag("   Bild etwas geaendert wird. Das passiert unterhalb von")
        sag("   uns, im Scaler oder im Treiber.")
        sag("   Hat es NICHT gezuckt, liegt es an etwas, das nur das")
        sag("   Frontend tut - und dann ist die naechste Frage, was.")
    sag("")
    if yoff_wechsel:
        sag("   AUSSERDEM: der Anzeigeversatz hat sich %d mal geaendert:"
            % len(yoff_wechsel))
        for t, alt, neu in yoff_wechsel[:10]:
            sag("      nach %6.2f s: yoffset %d -> %d" % (t, alt, neu))
        sag("   Das heisst, es wird zwischen zwei Bildseiten umgeschaltet.")
        sag("   Genau das waere die Erklaerung - und dagegen laesst sich")
        sag("   etwas tun: beide Seiten beschreiben.")
    else:
        sag("   Der Anzeigeversatz (yoffset) blieb die ganze Zeit bei %d."
            % yoff_vorher)
        sag("   Zwischen Bildseiten wird also nicht umgeschaltet - oder")
        sag("   der Treiber meldet es nicht.")
    return True


# ---------------------------------------------------------------------------
def main():
    dauer = 0
    argumente = sys.argv[1:]
    if argumente and argumente[0] in ("--wache", "-w"):
        dauer = 30
        if len(argumente) > 1:
            try:
                dauer = max(5, min(int(argumente[1]), 300))
            except ValueError:
                pass

    sag("==============================================================")
    sag("Dragend - Wache am Bildspeicher")
    sag("==============================================================")
    sag("Zeit       : %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    try:
        sag("System     : %s" % " ".join(os.uname()))
    except OSError:
        pass
    sag("")

    pfad = "/dev/fb0"
    if not os.path.exists(pfad):
        sag("%s gibt es nicht. Ohne Bildspeicher kein Ergebnis." % pfad)
        bericht_schreiben()
        return 1
    fd = os.open(pfad, os.O_RDWR)
    try:
        v, f, zl, eine_seite = abschnitt_nachsehen(fd)
        if dauer:
            abschnitt_wache(fd, v, f, zl, eine_seite, dauer)
        else:
            sag("--------------------------------------------------------------")
            sag("   Das war nur das Nachsehen - geschrieben wurde nichts.")
            sag("   Die Entscheidung zwischen 'jemand schreibt hinein' und")
            sag("   'die Ebene wird weggeschaltet' bringt erst die Wache:")
            sag("")
            sag("      Frontend mit F12 beenden, dann")
            sag("      python3 fb_wacht.py --wache 30")
            sag("")
            sag("   Am besten einmal bei voller und einmal bei halber")
            sag("   Aufloesung - der Unterschied ist die eigentliche Spur.")
            sag("--------------------------------------------------------------")
    finally:
        os.close(fd)
    sag("")
    sag("==============================================================")
    sag("Ende. Auf der Karte wurde nichts veraendert.")
    sag("==============================================================")
    bericht_schreiben()
    return 0


if __name__ == "__main__":
    sys.exit(main())
