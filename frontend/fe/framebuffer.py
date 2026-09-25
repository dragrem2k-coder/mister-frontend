#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Framebuffer - reine Zeichen-Grundfunktionen, ausgelagert aus
frontend.py (Modularisierung, Git-Branch 'modular-refactor').

WICHTIG (dieselbe Python-Import-Falle wie bei fe/translations.py/
CURRENT_LANG): C_BG/C_TEXT werden als Rueckfallwerte in text()
verwendet, wenn keine Farbe explizit uebergeben wird - und aendern
sich beim Theme-Wechsel (apply_theme() in frontend.py). Ein einfacher
Import wuerde hier ebenfalls eine eingefrorene Kopie erzeugen.

Diesmal ANDERE Loesung als current_lang() (bewusst KEINE Funktions-
Indirektion): text() ist eine sehr heisse Stelle (wird fuer JEDES
einzelne gezeichnete Zeichen aufgerufen) - ein Funktionsaufruf pro
Zeichen nur fuer die Farbe waere unnoetiger Overhead. Stattdessen
haelt dieses Modul C_BG/C_TEXT als EIGENE globale Variablen mit
sinnvollen Standardwerten (identisch zum "dark"-Theme), und
frontend.py schreibt bei jedem Themenwechsel per Modul-qualifiziertem
Zugriff (fe.framebuffer.C_BG = ...) direkt hinein - das ist eine
normale Zuweisung, kein Neu-Binden einer importierten Kopie, wirkt
also sofort auch hier.
"""
import os, sys, mmap, fcntl, time, struct, threading
from fe.log import LOG

FBDEV = "/dev/fb0"

# NEU (Build 111, Nutzer-Rueckmeldung: "einige Nutzer haben auf den
# neuen Kernel gewechselt, und da lief unser Frontend nicht mehr").
#
# Das MiSTer-Update vom 07.09.2026 hat den Linux-Kernel gewechselt und
# dabei den Zugriff auf den Bildspeicher veraendert. Mehrere Frontends
# (Zaparoo, Degauss) starteten danach nicht mehr - sie beendeten sich,
# BEVOR ueberhaupt etwas auf dem Schirm stand. Kernelseitig ist nichts
# zurueckgenommen worden; jedes Programm hat sich selbst gepatcht.
#
# Bei uns haengt genau eine Stelle daran: _read_geometry() las drei
# Dateien unter /sys/class/graphics/fb0/. Fehlt oder aendert sich eine
# davon, fliegt eine Ausnahme, und das Frontend endet still - Wort fuer
# Wort das gemeldete Verhalten.
#
# Der Ausweg sind die beiden ioctls hier. Sie sind stabile Kernel-ABI
# und seit Jahrzehnten unveraendert; die sysfs-Attribute sind es nicht.
# Benutzt werden sie NUR als Rueckfall - der sysfs-Weg bleibt der erste
# Versuch, damit sich auf dem alten Kernel buchstaeblich nichts aendert.
# (Dieselben Konstanten benutzt tools/fb_probe.py schon laenger, dort
# auf echter Hardware erprobt.)
FBIOGET_VSCREENINFO = 0x4600
FBIOGET_FSCREENINFO = 0x4602

# Falls der neue Kernel das Geraet anders benennt. Der erste Eintrag ist
# der Normalfall und wird auf jedem bisherigen MiSTer sofort treffen.
FBDEV_KANDIDATEN = ("/dev/fb0", "/dev/fb1", "/dev/fb2")

# Als Konstante, damit der Test beide Wege gegen einen nachgebauten
# Ordner pruefen kann - auf dem Geraet gibt es nur diesen einen Pfad.
SYSFS_GRAPHICS = "/sys/class/graphics"

# Grenzen fuer die Plausibilitaetspruefung. Ein Kernel, der Unsinn
# liefert, soll nicht in einem mmap ueber mehrere Gigabyte enden,
# sondern sauber in den naechsten Versuch laufen.
GEO_MAX_KANTE = 8192
GEO_MAX_BYTES = 64 * 1024 * 1024
C_BG = (16, 18, 24)          # siehe Modul-Kommentar oben - von
C_TEXT = (220, 224, 232)     # apply_theme() aktuell gehalten

FONT8X8 = bytes.fromhex('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000183c3c1818001800363600000000000036367f367f3636000c3e031e301f0c00006333180c6663001c361c6e3b336e000606030000000000180c0606060c1800060c1818180c060000663cff3c660000000c0c3f0c0c000000000000000c0c060000003f0000000000000000000c0c006030180c060301003e63737b6f673e000c0e0c0c0c0c3f001e33301c06333f001e33301c30331e00383c36337f3078003f031f3030331e001c06031f33331e003f3330180c0c0c001e33331e33331e001e33333e30180e00000c0c00000c0c00000c0c00000c0c06180c0603060c180000003f00003f0000060c1830180c06001e3330180c000c003e637b7b7b031e000c1e33333f3333003f66663e66663f003c66030303663c001f36666666361f007f46161e16467f007f46161e16060f003c66030373667c003333333f333333001e0c0c0c0c0c1e007830303033331e006766361e366667000f06060646667f0063777f7f6b63630063676f7b736363001c36636363361c003f66663e06060f001e3333333b1e38003f66663e366667001e33070e38331e003f2d0c0c0c0c1e003333333333333f0033333333331e0c006363636b7f7763006363361c1c3663003333331e0c0c1e007f6331184c667f001e06060606061e0003060c18306040001e18181818181e00081c36630000000000000000000000ff0c0c18000000000000001e303e336e000706063e66663b0000001e3303331e003830303e33336e0000001e333f031e001c36060f06060f0000006e33333e301f0706366e666667000c000e0c0c0c1e00300030303033331e070666361e3667000e0c0c0c0c0c1e000000337f7f6b630000001f333333330000001e3333331e0000003b66663e060f00006e33333e307800003b6e66060f0000003e031e301f00080c3e0c0c2c18000000333333336e0000003333331e0c000000636b7f7f3600000063361c36630000003333333e301f00003f190c263f00380c0c070c0c38001818180018181800070c0c380c0c07006e3b0000000000000000000000000000')

# NEU (uebernommen von TheRealSutefan): Latin-1-Ergaenzung (0xA0-0xFF,
# gleiches 8x8-Bitmap-Format wie FONT8X8) - damit Umlaute (ä/ö/ü/ß) und
# Akzente in Spielnamen/Texten echt dargestellt werden statt als "?".
FONT_EXTRA = bytes.fromhex('0000000000000000181800181818180018187e03037e18181c36260f06673f000000633e363e630033331e3f0c3f0c0c18181800181818007cc61c36361c331e33000000000000003c4299858599423c3c36367c0000000000cc663366cc00000000003f3030000000000000000000003c429da59da5423c7e000000000000001c36361c0000000018187e1818007e001c30180c3c0000001c3018301c000000180c00000000000000006666663e0603fedbdbded8d8d8000000001818000000000000000018301e080c081c000000001c36361c00000000003366cc66330000c36333bdecf6f303c363337bcc6633f003c463b4dbace6800c000c0603331e0007001c36637f630070001c36637f63001c36003e637f63006e3b003e637f6300631c36637f6363000c0c001e333f33007c36337f333373001e3303331e18301e07003f061e063f0038003f061e063f000c123f061e063f0036003f061e063f0007001e0c0c0c1e0038001e0c0c0c1e000c12001e0c0c1e0033001e0c0c0c1e003f666f6f66663f003f0033373f3b33000e00183c663c18007000183c663c18003c66183c663c18006e3b003e63633e00c3183c66663c180000361c081c3600005c36737b6f361d000e00666666663c007000666666663c003c66006666663c003300333333331e00700066663c1818000f063e66663e060f001e331f331f030307001e303e337e0038001e303e337e007ec33c607c66fc006e3b1e303e337e0033001e303e337e000c0c1e303e337e000000fe30fe33fe0000001e03031e301c07001e333f031e0038001e333f031e007ec33c667e063c0033001e333f031e0007000e0c0c0c1e001c000e0c0c0c1e003e631c1818183c0033000e0c0c0c1e001b0e1b303e331e00001f001f333333000007001e33331e000038001e33331e001e33001e33331e006e3b001e33331e000033001e33331e001818007e0018180000603c767e6e3c060007003333337e000038003333337e001e33003333337e000033003333337e0000380033333e301f0000063e663e060000330033333e301f')

# ----------------------------------------------------------------------------
# FRAMEBUFFER
# ----------------------------------------------------------------------------

ROWCACHE_MAX_ENTRIES = 150  # siehe Framebuffer.rect()/clear() - verhindert
                            # unbegrenztes Cache-Wachstum durch leicht
                            # wechselnde (Farbe, Breite)-Kombinationen
# ENTFERNT (Build 102): hier stand VIGNETTE_FLAT_BAND, ein Zeilenband
# mit flacher statt verlaufender Randabdunkelung. Es existierte
# ausschliesslich als Voraussetzung fuer das Scroll-Blitting aus Build
# 96 (verschobene Bildzeilen haetten ihre Abdunkelung mitgenommen und
# der Fehler haette sich Schritt fuer Schritt aufsummiert). Mit dem
# Blitting faellt auch das Band weg - die Vignette verlaeuft wieder
# ueber das ganze Bild, so wie vor Build 96.

VIGNETTE_ENABLED = True    # dezente Randabdunkelung auf einfarbigen
                            # Flaechen (siehe Framebuffer.clear()) - rein
                            # optisch, kostet dank Zeilen-Cache nichts
                            # beim eigentlichen Zeichnen

class Framebuffer:
    # Der haeppchenweise Flip, siehe _flip_haeppchenweise(). Hier als
    # KLASSENvorgabe und nicht nur in _map(): der Regressionstest und
    # die Zeichen-Tests ersetzen __init__() durch eine Attrappe, die
    # _map() nie ruft - ohne diese beiden Zeilen liefe flip() dort in
    # einen AttributeError, und zwar in jedem einzelnen Test.
    haeppchen = 1
    haeppchen_pause = 0.0

    # Der Rueckleser, siehe _rueckleser_pruefen(). Aus denselben
    # Gruenden hier als Klassenvorgabe: eine Attrappe, die _map() nie
    # ruft, soll flip() trotzdem ueberstehen.
    rueckleser = 0
    _rueck_offsets = ()
    _rueck_proben = None

    # FBIO_WAITFORVSYNC (siehe linux/fb.h: _IOW('F', 0x20, __u32)) - wartet
    # auf den naechsten vertikalen Bildwechsel der Anzeige-Hardware, BEVOR
    # in den Framebuffer geschrieben wird. Ohne das kann ein Schreibvorgang
    # (egal ob flip() oder flip_rows()) mitten in einem laufenden Scanvorgang
    # der Hardware landen - der Bildschirm zeigt dann fuer einen Sekundenbruch-
    # teil einen Mix aus altem und neuem Bildinhalt ("Tearing"). Sichtbar wird
    # das z.B. als leicht verschobener, "doppelt belichtet" wirkender Text bei
    # der markierten Zeile (Nutzer-Rueckmeldung: Text ueberlappt beim
    # Scrollen). Je groesser der Schreibvorgang (volle Seite vs. einzelne
    # Zeile), desto laenger dauert er und desto wahrscheinlicher ein
    # sichtbarer Treffer mitten im Scan.
    FBIO_WAITFORVSYNC = 0x40044620

    def __init__(self):
        # BUGFIX Teil 2 (Nutzer-Rueckmeldung: "1 von 10 Faellen startet
        # nicht richtig, bleibt im OSD" - siehe frontend_boot.sh fuer
        # Teil 1/die volle Herleitung): selbst mit der grosszuegigeren
        # 120s-Wartezeit in frontend_boot.sh kann es in seltenen Faellen
        # noch vorkommen, dass MiSTer's eigener Uebergang vom OSD zum
        # Framebuffer im exakt falschen Sekundenbruchteil noch nicht
        # ganz abgeschlossen ist, wenn wir hier ankommen - das Oeffnen
        # des Geraets (oder das Lesen seiner Geometrie) schlaegt dann
        # kurzzeitig fehl, obwohl eine Sekunde spaeter alles bereit
        # waere. Bisher fuehrte das zu einem sofortigen, harten Absturz
        # (sauber geloggt, aber das Frontend erschien nie - das alte
        # OSD blieb einfach stehen). Fix: bis zu 5 Versuche mit 0.5s
        # Pause dazwischen (insgesamt max. 2.5s zusaetzliche Wartezeit,
        # nur im Fehlerfall - beim ERSTEN, ueblichen erfolgreichen
        # Versuch entsteht KEINE zusaetzliche Verzoegerung).
        # GEAENDERT (Build 111): erst das Geraet OEFFNEN, dann die
        # Geometrie lesen - vorher war es umgekehrt. Der Rueckfall ueber
        # ioctl braucht einen offenen Dateideskriptor, und ohne ihn
        # haette er gar nicht erst zum Zug kommen koennen.
        self.fd = -1
        last_error = None
        for attempt in range(5):
            try:
                self._geraet_oeffnen()
                self._read_geometry()
                break
            except OSError as e:
                last_error = e
                if self.fd >= 0:
                    try:
                        os.close(self.fd)
                    except OSError:
                        pass
                    self.fd = -1
                LOG("Framebuffer-Oeffnen fehlgeschlagen (Versuch %d/5): %s"
                    % (attempt + 1, e))
                time.sleep(0.5)
        else:
            # Bevor wir aufgeben: aufschreiben, WAS der Kernel anbietet.
            # Genau diese Zeilen fehlen den anderen Frontends, die nach
            # dem Kernelwechsel "einfach nicht mehr starten".
            LOG("Framebuffer: alle 5 Versuche gescheitert - Diagnose folgt")
            self.diagnose()
            raise last_error
        self._map()
        self._rowcache = {}
        self._rectcache = {}   # eigener Cache fuer rect() (siehe dort) -
                                # getrennt von _rowcache, damit dessen
                                # Obergrenze nicht die selten wechselnden,
                                # teuren Hintergrundmuster von clear() mitloescht
        self._glyphcache = {}
        self._textcache = {}          # (text, scale, fg, bg) -> Liste von Byte-Zeilen
        self._textcache_order = []
        # BUGFIX (Nutzerwunsch "Scrollen soll butterweich sein" fuehrte zu
        # echten DRAGEND_PROFILE-Logs auf echter Hardware - siehe TEXTCACHE-
        # Zeilen dort): die fruehere Vermutung aus dem Kommentar unten
        # ("ob das an echten Cache-Fehltreffern liegt... laesst sich ohne
        # echte Daten nicht serioes unterscheiden") ist jetzt beantwortet -
        # Verdraengungen wurden auf echter Hardware nachweislich beobachtet
        # (von 0 auf ueber 350 waehrend weniger Minuten aktiven Scrollens
        # durch eine grosse NES-Sammlung angestiegen). 400 Eintraege waren
        # zu knapp: bereits gecachte, kuerzlich gesehene Titel flogen
        # wieder raus, bevor man zu ihnen zurueckscrollte, und mussten
        # unnoetig neu gerendert werden. Auf 2000 angehoben (~60MB bei
        # typischen Labellaengen, siehe Rechnung unten) - grosszuegiger
        # Puffer fuer auch sehr grosse Sammlungen, weiterhin unbedenklich
        # auf einem MiSTer mit ueblicherweise ≥1GB RAM.
        self._TEXTCACHE_LIMIT = 2000  # ~60MB bei typischen Labellaengen
        # NEU (Nutzerwunsch: "noch mehr Performance rausholen" - text()
        # hat bereits einen Ganze-Zeile-Cache, im echten Profiling aber
        # weiterhin 20-100ms je nach Bild). Ob das an echten Cache-
        # Fehltreffern liegt (z.B. weil _TEXTCACHE_LIMIT=400 bei einer
        # grossen Sammlung zu knapp bemessen ist und haeufig gesehene
        # Titel wieder rausfliegen) oder schlicht daran, dass beim
        # Scrollen staendig NEUE, noch nie gezeichnete Titel auftauchen
        # (strukturell kaum vermeidbar), laesst sich ohne echte Daten
        # nicht serioes unterscheiden - hier NUR mitzaehlen (guenstige
        # Zaehler-Erhoehung, kein spuerbarer Zusatzaufwand), Auswertung
        # optional ueber DRAGEND_PROFILE (siehe frontend.py).
        self._textcache_hits = 0
        self._textcache_misses = 0
        self._textcache_evictions = 0
        # None = noch nicht getestet, True/False = Ergebnis des ersten
        # Versuchs. Wird nur EINMAL probiert - unterstuetzt der Treiber es
        # nicht (ENOTTY/EINVAL o.ae.), schalten wir dauerhaft ab, statt bei
        # JEDEM Frame erneut einen fehlschlagenden ioctl-Aufruf zu riskieren.
        self._vsync_supported = None
        # NEU (Nutzerwunsch: "HDMI-Modus muss fluessiger laufen" - der
        # groesste verbliebene Einzelposten war der komplette Puffer-
        # Neuaufbau bei JEDEM Bild, selbst beim reinen Scrollen innerhalb
        # derselben Liste). Zaehler, der bei JEDEM vollstaendigen
        # Neuaufbau (clear() oder eine gleichwertige volle Pufferkopie)
        # hochgezaehlt wird - unabhaengig davon, WELCHE Funktion das
        # ausloest. _draw_page_items_impl() nutzt das, um zuverlaessig zu
        # erkennen, ob seit dem letzten eigenen vollen Neuaufbau
        # ZWISCHENDURCH irgendetwas anderes (Hilfe-Bildschirm, WoT,
        # Bestaetigungsdialog, Attract-Modus, ...) den Puffer ebenfalls
        # komplett neu geschrieben hat - nur dann ist der schnelle,
        # NICHT-loeschende Pfad wirklich sicher.
        self.full_redraw_gen = 0

        # NEUES FEATURE (Nutzerwunsch nach dem Bildschirmspiegel-Test:
        # "die 2-Sekunden-Aktualisierung sieht aus wie Standbilder,
        # geht das fluessiger?") - bewusst NICHT einfach das Intervall
        # verkuerzt (haette bei UNVERAENDERTEM Bildschirm, z.B. wenn
        # man einfach nur im Menue steht, unnoetig oft neu kodiert -
        # dieselbe Verschwendung, die full_redraw_gen oben schon fuer
        # den HDMI-Fast-Path vermeidet). Stattdessen: EIGENER Zaehler,
        # der bei JEDER tatsaechlich sichtbaren Aenderung hochzaehlt
        # (flip() UND flip_rows(), z.B. auch Laufschrift/Puls-Effekte -
        # full_redraw_gen oben zaehlt bewusst NUR bei vollen
        # Neuaufbauten, waere hierfuer also zu grob). Der Bildschirm-
        # spiegel-Hintergrund-Thread (siehe _screen_mirror_loop() in
        # frontend.py) prueft diesen Zaehler haeufiger, kodiert aber
        # nur neu, wenn sich seit dem letzten Schnappschuss wirklich
        # etwas geaendert hat.
        self.flip_gen = 0
        # NACHTRAEGLICH ERGAENZT (Nutzerwunsch: "kann man beim Mirror
        # noch mehr rausholen?") - bisher musste der Spiegel-Hintergrund-
        # Thread bis zu 0.2s auf den naechsten Pruef-Zyklus warten, selbst
        # bei einer einzelnen, isolierten Aenderung (z.B. Menuewechsel
        # nach laengerem Stillstand). Dieses Event weckt ihn SOFORT auf,
        # sobald flip()/flip_rows() etwas Neues geschrieben hat - die
        # bestehende Mindest-Abstand-Drosselung (siehe _screen_mirror_loop
        # in frontend.py) bleibt UNVERAENDERT bestehen, verhindert also
        # weiterhin Dauerfeuer bei schnellem, durchgehendem Scrollen.
        # threading.Event().set() ist eine reine Flag-Operation (kein
        # Locking-Overhead wie ein echtes Lock) - vernachlaessigbare
        # Kosten fuer flip()/flip_rows(), auch wenn kein Spiegel-Thread
        # gerade wartet.
        self.flip_event = threading.Event()

    def mark_full_redraw(self):
        """Von JEDEM Code aufzurufen, der den Puffer auf andere Weise als
        clear() komplett neu schreibt (aktuell: die Hintergrundbild-Kopie
        in _draw_page_items_impl()) - haelt full_redraw_gen konsistent,
        egal auf welchem Weg ein voller Neuaufbau passiert ist."""
        self.full_redraw_gen += 1

    def _wait_vsync(self):
        """Wartet, falls moeglich, auf den naechsten vertikalen Bildwechsel -
        siehe FBIO_WAITFORVSYNC oben. Schlaegt der ioctl fehl (Treiber
        unterstuetzt es nicht), wird das dauerhaft vermerkt und nie wieder
        versucht - kostet dann nichts mehr, faellt einfach auf das bisherige
        Verhalten (ohne Vsync-Wartezeit) zurueck."""
        if self._vsync_supported is False:
            return
        try:
            fcntl.ioctl(self.fd, self.FBIO_WAITFORVSYNC, struct.pack("I", 0))
            self._vsync_supported = True
        except (OSError, AttributeError):
            self._vsync_supported = False

    def _geraet_oeffnen(self):
        """Den Bildspeicher oeffnen und sich merken, welcher es war.

        Bisher stand hier fest /dev/fb0. Das ist weiterhin der erste und
        in aller Regel einzige Versuch - die Liste dahinter kostet
        nichts, solange der erste trifft, und faengt den Fall ab, dass
        ein neuer Kernel das Geraet anders durchnummeriert.
        DRAGEND_FBDEV setzt den Weg fuer eine gezielte Fehlersuche
        ausser Kraft."""
        kandidaten = list(FBDEV_KANDIDATEN)
        erzwungen = os.environ.get("DRAGEND_FBDEV")
        if erzwungen:
            kandidaten = [erzwungen]
        letzter = None
        for pfad in kandidaten:
            try:
                self.fd = os.open(pfad, os.O_RDWR)
            except OSError as e:
                letzter = e
                continue
            self.fbdev = pfad
            self.fbname = os.path.basename(pfad)
            if pfad != FBDEV:
                LOG("Framebuffer: %s statt %s benutzt" % (pfad, FBDEV))
            return
        raise letzter or OSError("kein Bildspeicher-Geraet gefunden")

    @staticmethod
    def _geo_plausibel(w, h, bpp, stride):
        """Sieht das nach einem echten Bildspeicher aus?

        Ohne diese Pruefung wuerde ein Kernel, der unerwartete Werte
        liefert, direkt in ein mmap ueber viele Gigabyte laufen - der
        Fehler daraus waere dann weit weg von seiner Ursache."""
        return (0 < w <= GEO_MAX_KANTE and 0 < h <= GEO_MAX_KANTE
                and bpp in (16, 24, 32)
                and stride >= w * (bpp // 8)
                and 0 < stride * h <= GEO_MAX_BYTES)

    def _geometrie_aus_sysfs(self):
        """Der bisherige Weg. Liefert None, wenn irgendetwas fehlt."""
        basis = "%s/%s" % (SYSFS_GRAPHICS, self.fbname)
        try:
            w, h = open(basis + "/virtual_size").read().strip().split(",")
            bpp = int(open(basis + "/bits_per_pixel").read())
            stride = int(open(basis + "/stride").read())
            return int(w), int(h), bpp, stride
        except (OSError, ValueError) as e:
            LOG("Framebuffer: sysfs nicht verwendbar (%s: %s)"
                % (type(e).__name__, e))
            return None

    def _geometrie_per_ioctl(self):
        """Der Rueckfall: direkt beim Geraetetreiber nachfragen.

        fb_var_screeninfo beginnt mit acht 32-Bit-Werten (xres, yres,
        xres_virtual, yres_virtual, xoffset, yoffset, bits_per_pixel,
        grayscale) - das ist der stabile Teil der Struktur, mehr
        brauchen wir nicht.

        Die Zeilenlaenge steht in fb_fix_screeninfo, und deren Aufbau
        haengt an der Wortbreite (smem_start ist ein unsigned long).
        Deshalb wird sie nicht fest ausgerechnet, sondern beide
        moeglichen Stellen werden probiert und die genommen, die zur
        Breite passt. Faellt auch das aus, tut es w * 4 - bei 32 Bit je
        Bildpunkt ohne Zeilenauffuellung ist das genau richtig, und mehr
        als eine unnoetig grosse Kopie kann dabei nicht herauskommen."""
        roh = bytearray(160)
        fcntl.ioctl(self.fd, FBIOGET_VSCREENINFO, roh, True)
        xres, yres, _xv, _yv, _xo, _yo, bpp, _gray = struct.unpack_from("<8I", roh)
        stride = 0
        try:
            fix = bytearray(160)
            fcntl.ioctl(self.fd, FBIOGET_FSCREENINFO, fix, True)
            for offset in (44, 52):          # 32-Bit- bzw. 64-Bit-Aufbau
                kandidat = struct.unpack_from("<I", fix, offset)[0]
                if xres * (bpp // 8) <= kandidat <= GEO_MAX_KANTE * 4:
                    stride = kandidat
                    break
        except OSError as e:
            LOG("Framebuffer: FBIOGET_FSCREENINFO nicht verfuegbar (%s)" % e)
        if not stride:
            stride = xres * (bpp // 8 or 4)
        return xres, yres, bpp, stride

    def _read_geometry(self):
        """Groesse und Zeilenlaenge des Bildspeichers bestimmen.

        GEAENDERT (Build 111): erst sysfs wie bisher, dann der ioctl-
        Rueckfall. Auf dem alten Kernel greift Zweig eins und es aendert
        sich nichts; auf einem Kernel, der die sysfs-Dateien nicht mehr
        so anbietet, uebernimmt Zweig zwei, statt dass das Frontend
        lautlos endet."""
        geo = self._geometrie_aus_sysfs()
        quelle = "sysfs"
        if geo is None or not self._geo_plausibel(*geo):
            if geo is not None:
                LOG("Framebuffer: sysfs liefert unplausible Werte %r" % (geo,))
            geo = self._geometrie_per_ioctl()
            quelle = "ioctl"
            if not self._geo_plausibel(*geo):
                raise OSError("Bildspeicher-Geometrie unbrauchbar: %r" % (geo,))
        w, h, bpp, stride = geo
        if getattr(self, "_geo_quelle", None) != quelle:
            LOG("Framebuffer: %s, Geometrie per %s: %dx%d, %d bpp, "
                "Zeile %d Bytes" % (self.fbname, quelle, w, h, bpp, stride))
            self._geo_quelle = quelle
        self.width, self.height, self.bpp, self.stride = w, h, bpp, stride
        if self.bpp != 32:
            # Der gesamte Zeichenweg rechnet mit vier Bytes je Bildpunkt
            # (BGRA). Das ist keine Kleinigkeit, die sich hier abfangen
            # laesst - aber es soll wenigstens IM LOG stehen und nicht
            # nur auf einer Konsole, die in diesem Moment niemand sieht.
            LOG("Framebuffer: %d bpp - nur 32 werden unterstuetzt, Abbruch"
                % self.bpp)
            sys.exit("Nur 32bpp wird unterstuetzt, gefunden: %d" % self.bpp)
        self.size = self.stride * self.height

    @staticmethod
    def diagnose():
        """Alles ins Log schreiben, was ueber den Bildspeicher zu
        erfahren ist - gerufen, wenn das Oeffnen endgueltig scheitert.

        Ohne das steht im Log nur "ging nicht". Mit dem hier steht da,
        WAS der Kernel anbietet, und die naechste Runde ist eine Frage
        von Minuten statt von Rueckfragen."""
        try:
            LOG("FB-DIAGNOSE: /dev/fb* -> %s"
                % sorted(n for n in os.listdir("/dev") if n.startswith("fb")))
        except OSError as e:
            LOG("FB-DIAGNOSE: /dev nicht lesbar: %s" % e)
        try:
            knoten = sorted(os.listdir(SYSFS_GRAPHICS))
        except OSError as e:
            LOG("FB-DIAGNOSE: %s nicht lesbar: %s" % (SYSFS_GRAPHICS, e))
            return
        LOG("FB-DIAGNOSE: %s -> %s" % (SYSFS_GRAPHICS, knoten))
        for k in knoten:
            if not k.startswith("fb"):
                continue
            basis = SYSFS_GRAPHICS + "/" + k
            try:
                dateien = sorted(os.listdir(basis))
            except OSError:
                continue
            LOG("FB-DIAGNOSE: %s hat %s" % (k, dateien))
            for name in ("virtual_size", "stride", "bits_per_pixel", "name"):
                try:
                    LOG("FB-DIAGNOSE:   %s/%s = %r"
                        % (k, name, open(basis + "/" + name).read().strip()))
                except OSError as e:
                    LOG("FB-DIAGNOSE:   %s/%s nicht lesbar (%s)" % (k, name, e))

    def _map(self):
        """Den Bildspeicher einblenden - mit Rueckfall ueber /dev/mem.

        WOZU DER RUECKFALL (Build 168).

        Das MiSTer-Linux-Update vom 07.09.2026 (Kernel 6.18.x) hat den
        Treiber MiSTer_fb auf die System-Memory-Helfer umgestellt,
        obwohl sein Speicher in einem iomem/CMA-Bereich liegt, der gar
        nicht im virtuellen Adressraum des Kernels steht. Im Log des
        Geraets steht dann woertlich:

            fb0: sys_fillrect: framebuffer is not in virtual address
            space.

        Der Treiber bringt seither keine eigene mmap-Funktion mehr mit.
        Bei manchen Programmen schlaegt das Einblenden von /dev/fb0
        deshalb fehl (Console Mode meldet "Unable to memory map the
        video hardware", Degauss startete gar nicht mehr). Degauss hat
        genau diesen Rueckfall eingebaut: bleibt /dev/fb0 verschlossen,
        wird die vom Treiber GEMELDETE physische Adresse ueber /dev/mem
        eingeblendet - derselbe Weg, den MiSTers eigenes OSD benutzt.

        EHRLICH DAZU: auf dem Geraet, an dem dieser Fehler gemeldet
        wurde, ging der normale Weg weiterhin - das Frontend war ja
        sichtbar. Dieser Rueckfall ist also KEINE Reparatur des dort
        beobachteten Fehlers, sondern Vorsorge fuer die Geraete, auf
        denen das Einblenden hart scheitert. Er kostet nichts, solange
        der erste Versuch klappt, und auf dem alten Kernel wird er nie
        betreten.

        Unsere Zeichenweise passt ohnehin schon dazu: gezeichnet wird
        in self.buf (normaler Arbeitsspeicher), und flip() kopiert das
        Ergebnis in einem Rutsch hinueber. Genau darauf musste Degauss
        bei physischer Einblendung erst umstellen - Schreibzugriffe
        direkt in nicht gepufferten Gerätespeicher sind langsam."""
        # refresh_geometry() ruft _map() ein zweites Mal (nach einem
        # Aufloesungswechsel). Einen alten /dev/mem-Zeiger hier
        # schliessen - sonst bliebe er bei jedem Wechsel liegen.
        alt = getattr(self, "_mem_fd", None)
        if alt is not None:
            try:
                os.close(alt)
            except OSError:
                pass
        self._mem_fd = None
        try:
            self.mm = mmap.mmap(self.fd, self.size, mmap.MAP_SHARED,
                                mmap.PROT_READ | mmap.PROT_WRITE)
        except (OSError, ValueError) as e:
            LOG("Framebuffer: mmap auf %s schlug fehl (%s) - versuche "
                "den Weg ueber /dev/mem" % (self.fbdev, e))
            self.mm = self._map_ueber_dev_mem()
        self.buf = bytearray(self.size)
        self._haeppchen_einrichten()
        self._rueckleser_einrichten()

    def _haeppchen_einrichten(self):
        """Den haeppchenweisen Flip vorbereiten - siehe
        _flip_haeppchenweise().

        EINMAL beim Oeffnen, nicht bei jedem Bild: der Schalter aendert
        sich zur Laufzeit nicht, und die beiden memoryview-Objekte
        haetten pro Bild sonst nichts zu tun, als erzeugt und wieder
        weggeworfen zu werden.

        Der Schalter wird hier direkt gelesen und NICHT ueber
        fe.settings geholt: dieses Modul kommt bewusst ohne
        Abhaengigkeit zum Einstellungsmodul aus (der Framebuffer muss
        auch dann aufgehen, wenn oben etwas fehlt). Die Umgebungs-
        variable steht daneben, damit sich zwei Laeufe vergleichen
        lassen, ohne eine Datei anzulegen."""
        self.haeppchen = 1
        self.haeppchen_pause = 0.0
        self._mv_mm = self._mv_buf = None
        wert = os.environ.get("DRAGEND_FLIP_HAEPPCHEN")
        if wert is None:
            try:
                with open("/media/fat/frontend/flip_haeppchen") as f:
                    wert = f.read().strip() or "16"
            except OSError:
                return
        wert = (wert or "").strip()
        if not wert or wert in ("0", "1", "aus", "off"):
            return
        # "16" oder "16:200" - Haeppchen, und wieviele Mikrosekunden
        # dazwischen gewartet wird.
        teile = wert.split(":")
        try:
            n = int(teile[0])
        except ValueError:
            n = 16
        us = 0
        if len(teile) > 1:
            try:
                us = int(teile[1])
            except ValueError:
                us = 0
        # Obergrenze mit Ansage: bei sehr vielen Haeppchen misst man
        # vor allem den eigenen Mehraufwand.
        self.haeppchen = max(2, min(n, 256))
        self.haeppchen_pause = max(0.0, min(us, 5000)) / 1000000.0
        try:
            self._mv_mm = memoryview(self.mm)
            self._mv_buf = memoryview(self.buf)
        except TypeError as e:
            LOG("Flip-Haeppchen: memoryview geht hier nicht (%s) - "
                "bleibe beim Flip in einem Zug" % e)
            self.haeppchen = 1
            return
        LOG("Flip-Haeppchen: %d Stuecke, %.0f us Pause dazwischen"
            % (self.haeppchen, self.haeppchen_pause * 1000000))

    def _rueckleser_einrichten(self):
        """Den Rueckleser vorbereiten - siehe _rueckleser_pruefen().

        MESSGEGENSTAND (Build 182), standardmaessig AUS. Geschaltet
        ueber DRAGEND_FLIP_RUECKLESER oder die Datei
        /media/fat/frontend/flip_rueckleser; der Wert ist die Anzahl
        der Proben-Zeilen (leer = 8, Grenzen 1 bis 64).

        Wie beim Haeppchen-Schalter wird hier direkt gelesen und nicht
        ueber fe.settings: dieses Modul kommt ohne Abhaengigkeit nach
        oben aus."""
        self.rueckleser = 0
        self._rueck_offsets = ()
        self._rueck_proben = None
        self._rueck_treffer = 0
        self._rueck_bilder = 0
        self._rueck_letzte_meldung = 0.0
        self._rueck_letzte_bilanz = time.monotonic()
        self._rueck_start = time.monotonic()
        wert = os.environ.get("DRAGEND_FLIP_RUECKLESER")
        if wert is None:
            try:
                with open("/media/fat/frontend/flip_rueckleser") as f:
                    wert = f.read().strip() or "8"
            except OSError:
                return
        wert = (wert or "").strip()
        if not wert or wert in ("0", "aus", "off"):
            return
        try:
            n = int(wert)
        except ValueError:
            n = 8
        n = max(1, min(n, 64))
        # DIE PROBEN LIEGEN NICHT NUR GLEICHMAESSIG (Build 189).
        #
        # Vorher waren es schlicht n gleich verteilte Zeilen - bei acht
        # Proben also 0, 135, 270, 405 ... Genau dazwischen liegt aber
        # der Bereich, in dem fremde Ausgabe auf diesem Geraet
        # nachweislich auftaucht: der Textcursor der Konsole sitzt in
        # den Zeilen 32 bis 47 (gemessen mit fb_wacht --wache, 116
        # Treffer in 30 Sekunden), und der Login-Gruss steht in
        # denselben obersten Zeilen.
        #
        # Der Rueckleser war damit blind fuer genau das, wofuer man ihn
        # am dringendsten braucht. Deshalb liegt jetzt ein Viertel der
        # Proben dicht im oberen Textbereich, der Rest wie bisher
        # gleichmaessig ueber das Bild - ein Vollbild-Ereignis faellt
        # so weiterhin auf, ein Fleck oben aber eben auch.
        # Verteilt ueber die obersten TEXTHOEHE Zeilen, nicht in den
        # ersten paar: der Cursor sass bei 32-47, und eine Probe bei
        # Zeile 0 und 8 haette ihn wieder verfehlt. Genau dieser Fehler
        # war beim ersten Anlauf noch drin.
        TEXTHOEHE = 64
        dicht = max(1, n // 4)
        abstand = max(1, TEXTHOEHE // dicht)
        oben = [z for z in range(0, min(self.height, TEXTHOEHE), abstand)]
        schritt = max(1, self.height // max(1, n - len(oben)))
        gleich = [z for z in range(0, self.height, schritt)]
        zusammen = sorted(set(oben + gleich))
        self._rueck_offsets = tuple(zusammen[:n])
        self._rueck_proben = [None] * len(self._rueck_offsets)
        self.rueckleser = n
        LOG("Rueckleser: %d Proben-Zeilen (%s) - es wird nach jedem Bild "
            "geprueft, ob unser Inhalt noch im Bildspeicher steht"
            % (len(self._rueck_offsets),
               ",".join(str(z) for z in self._rueck_offsets[:8])))

    def _rueckleser_pruefen(self):
        """Nachsehen, ob im Bildspeicher noch steht, was wir zuletzt
        hineingeschrieben haben.

        WOZU (Build 182). Beim Zucken auf 1080p sind vier Erklaerungen
        durchgemessen und tot: Eingabe-Leck, uebersprungenes Vsync,
        Speicherdurchsatz (Build 181: dreifach entzerrter Flip aendert
        nichts) und der Cover-Weg (es zuckt auch ohne ein einziges
        Cover). Uebrig bleiben genau zwei, die einander ausschliessen:

          A) Jemand SCHREIBT in den Bildspeicher hinein.
          B) Niemand schreibt, die Anzeige-Ebene wird WEGGESCHALTET.

        fb_wacht.py entscheidet das ohne Frontend - aber eben ohne
        Frontend, und MiSTer verhaelt sich anders, wenn niemand sonst
        zeichnet. Der Rueckleser stellt dieselbe Frage IM LAUFENDEN
        BETRIEB: er merkt sich beim Schreiben ein paar Zeilen und
        vergleicht sie beim naechsten Bild mit dem, was dort jetzt
        steht.

          Abweichung -> A, mit Zeitpunkt und Zeilennummern.
          Nie eine Abweichung, waehrend es sichtbar zuckt -> B.

        Warum nur Proben und nicht alles: gelesen wird aus
        ungepuffertem Speicher. Acht Zeilen sind 61 KB je Bild und
        damit bezahlbar; 7,9 MB waeren es nicht, und die Messung
        wuerde vor allem sich selbst messen."""
        proben = self._rueck_proben
        if not proben:
            return
        zl = self.stride
        kaputt = []
        for i, z in enumerate(self._rueck_offsets):
            soll = proben[i]
            if soll is None:
                continue
            a = z * zl
            if self.mm[a:a + zl] != soll:
                kaputt.append(z)
        self._rueck_bilder += 1
        if not kaputt:
            self._rueckleser_bilanz()
            return
        self._rueck_treffer += 1
        jetzt = time.monotonic()
        # Hoechstens eine Zeile je Sekunde: ein Dauerfeuer im Log waere
        # unbrauchbar, und die Gesamtzahl steht ja daneben.
        if jetzt - self._rueck_letzte_meldung < 1.0:
            return
        self._rueck_letzte_meldung = jetzt
        LOG("RUECKLESER: nach %.1f s steht in %d von %d Proben-Zeilen "
            "fremder Inhalt (Zeilen %s) - %d Treffer bei %d Bildern"
            % (jetzt - self._rueck_start, len(kaputt),
               len(self._rueck_offsets),
               ",".join(str(z) for z in kaputt[:8]),
               self._rueck_treffer, self._rueck_bilder))

    def _rueckleser_bilanz(self):
        """Alle 30 Sekunden eine Zeile ins Log, auch wenn nichts war.

        NEU (Build 183), und der Grund ist ein Fehler in Build 182:
        dort schrieb der Rueckleser nur bei einem TREFFER. Bleibt er
        stumm, weiss niemand, ob er nichts gefunden hat oder ob er gar
        nicht gelaufen ist - und aus 'kein Eintrag im Log' laesst sich
        dann beides lesen. Genau das ist bei der ersten Messung
        passiert: ein einzelner Treffer beim Start, danach Stille, und
        die Stille war nicht auswertbar.

        Ein Messgegenstand, der nur bei Erfolg redet, kann eine
        Vermutung nur bestaetigen und nie widerlegen. Mit dieser Zeile
        wird aus dem Schweigen eine Messung: so und so viele Bilder
        geprueft, so und so viele Treffer."""
        jetzt = time.monotonic()
        if jetzt - self._rueck_letzte_bilanz < 30.0:
            return
        self._rueck_letzte_bilanz = jetzt
        LOG("RUECKLESER-BILANZ: %.0f s, %d Bilder geprueft, %d Treffer"
            % (jetzt - self._rueck_start, self._rueck_bilder,
               self._rueck_treffer))

    def _rueckleser_merken(self, y0=0, y1=None):
        """Die Proben der gerade geschriebenen Zeilen auffrischen.

        Muss nach JEDEM Schreiben geschehen, auch nach flip_rows() -
        sonst meldete der Rueckleser die Laufschrift als fremden
        Inhalt, und das waere ein Fehlalarm, der wie ein Befund
        aussieht."""
        proben = self._rueck_proben
        if proben is None:
            return
        if y1 is None:
            y1 = self.height
        zl = self.stride
        for i, z in enumerate(self._rueck_offsets):
            if y0 <= z < y1:
                a = z * zl
                proben[i] = bytes(self.buf[a:a + zl])

    def _map_ueber_dev_mem(self):
        """Die physische Adresse des Bildspeichers direkt einblenden.

        Die Adresse kommt aus FBIOGET_FSCREENINFO (smem_start), also
        vom Treiber selbst - nicht geraten und nicht fest verdrahtet.

        Ist sie nicht seitenausgerichtet, wird hier ABGEBROCHEN statt
        mit einem Versatz weiterzumachen: der gesamte Zeichenweg
        rechnet damit, dass Bildpunkt (0,0) bei Index 0 liegt. Ein
        stillschweigender Versatz waere ein um ein paar Bytes
        verschobenes Bild - der unangenehmste Fehler von allen, weil
        er aussieht wie ein Grafikproblem und keines ist."""
        fix = bytearray(160)
        try:
            fcntl.ioctl(self.fd, FBIOGET_FSCREENINFO, fix, True)
        except OSError as e:
            raise OSError("weder mmap noch FBIOGET_FSCREENINFO "
                          "funktionieren (%s)" % e)
        # fb_fix_screeninfo: char id[16]; unsigned long smem_start;
        # __u32 smem_len; ... - auf 32-Bit-ARM ist unsigned long
        # vier Bytes gross.
        smem_start, smem_len = struct.unpack_from("<II", fix, 16)
        LOG("Framebuffer: Treiber meldet smem_start=0x%08X, smem_len=%d "
            "(gebraucht: %d)" % (smem_start, smem_len, self.size))
        if not smem_start:
            raise OSError("der Treiber meldet keine physische Adresse - "
                          "der Rueckfall ueber /dev/mem ist nicht moeglich")
        if smem_len and smem_len < self.size:
            raise OSError("der Treiber meldet nur %d Bytes, gebraucht "
                          "werden %d" % (smem_len, self.size))
        if smem_start % mmap.PAGESIZE:
            raise OSError("smem_start 0x%08X ist nicht seitenausgerichtet "
                          "- abgebrochen, bevor ein verschobenes Bild "
                          "entsteht" % smem_start)
        self._mem_fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
        try:
            mm = mmap.mmap(self._mem_fd, self.size, mmap.MAP_SHARED,
                           mmap.PROT_READ | mmap.PROT_WRITE,
                           offset=smem_start)
        except (OSError, ValueError):
            os.close(self._mem_fd)
            self._mem_fd = None
            raise
        LOG("Framebuffer: ueber /dev/mem eingeblendet - das Geraet laeuft "
            "auf einem Kernel, dessen fb-Treiber kein eigenes mmap mehr "
            "anbietet (Linux-Update vom 07.09.2026)")
        return mm

    def refresh_geometry(self):
        """Nach Rueckkehr aus einem Core neu einlesen - die Aufloesung
        kann sich geaendert haben (z.B. anderer Videomodus)."""
        old = (self.width, self.height, self.stride)
        self._read_geometry()
        if (self.width, self.height, self.stride) != old:
            try:
                self.mm.close()
            except Exception:
                pass
            self._map()
            self._rowcache.clear()

    @staticmethod
    def _vignette_row_variants(rgb, width, stride, levels=12, strength=0.30):
        """Vorberechnet `levels` unterschiedlich dunkle Varianten einer
        vollen Bildzeile in EINER Farbe - Grundlage fuer eine schnelle,
        zeilenbasierte Vignette (siehe clear()). NUR fuer Flaechen mit
        einer einzelnen Fuellfarbe geeignet (kein Bild), da eine ganze
        Zeile hier IMMER dieselbe Farbe hat - genau das macht die
        Kopie so billig (eine Slice-Zuweisung pro Zeile statt Pixel
        fuer Pixel).

        WICHTIG (Performance-Grund): eine echte, pixelgenaue radiale
        Vignette (mit Verlauf auch in X-Richtung, wie bei einem Foto)
        wurde direkt gemessen - ueber 1 Sekunde fuer eine einzelne
        1080p-Flaeche, selbst nur EINMALIG berechnet - das haette bei
        jedem Wechsel der Hintergrundfarbe (Themenwechsel) zu
        spuerbaren Haengern gefuehrt, nicht vertretbar. Diese Zeilen-Variante ist rein vertikal
        (oben/unten dunkler, kein staerkerer Effekt in den Ecken) -
        optisch ein etwas einfacherer, aber immer noch deutlich
        hochwertiger wirkender Verlauf, dafuer um Groessenordnungen
        schneller (siehe _apply_vignette_rows())."""
        pad = b"\x00" * (stride - width * 4)
        r, g, b = rgb
        out = []
        for lvl in range(levels):
            f = 1.0 - strength * (lvl / max(1, levels - 1))
            drgb = (int(r * f), int(g * f), int(b * f))
            out.append(Framebuffer.px(drgb) * width + pad)
        return out

    @staticmethod
    def _apply_vignette_rows(out, height, stride, row_variants):
        """Setzt out (bytearray, bereits mit vollem Puffer-Speicher
        allokiert) zeilenweise aus den vorberechneten, unterschiedlich
        dunklen Varianten zusammen - Mitte hell, Rand oben/unten
        dunkler. Aufeinanderfolgende Zeilen mit derselben (quantisierten)
        Helligkeitsstufe werden zu einem Block zusammengefasst und per
        EINER Bytes-Multiplikation (variante * anzahl) statt einzelner
        Zeilen-Kopien geschrieben - deutlich weniger Einzeloperationen."""
        levels = len(row_variants)
        cy = height / 2.0

        def stufe(zeile):
            d_ = abs(zeile - cy) / cy if cy else 0.0
            return min(levels - 1, int(d_ * d_ * (levels - 1)))

        y = 0
        while y < height:
            lvl = stufe(y)
            run_start = y
            y += 1
            while y < height:
                if stufe(y) != lvl:
                    break
                y += 1
            run_len = y - run_start
            off = run_start * stride
            block = row_variants[lvl] * run_len
            out[off:off + len(block)] = block

    @staticmethod
    def _scale_brightness(pix, factor):
        """Skaliert die Helligkeit eines kompletten BGRA-Pixelpuffers
        (siehe blit()) um factor (0.0-1.0+) - per bytes.translate() mit
        vorberechneter 256-Werte-Tabelle, deutlich schneller als eine
        Python-Schleife pro Byte. Der Alpha-Kanal wird zwar mit
        skaliert (translate() kennt keine Kanaele, wirkt gleichmaessig
        auf JEDES Byte), das ist aber unschaedlich: blit() kopiert
        Pixel direkt ohne Alpha-Blending, der Alpha-Wert wird beim
        Zeichnen also nie ausgewertet. Fuer den Logo-Flacker-Effekt
        beim Start (siehe _draw_dragend_logo_boot()) - dieselbe
        Wirkung wie das bisherige dunkel/mittel/voll beim generischen
        D-Pad-Symbol, nur auf ein echtes Bild statt auf einfache
        Rechtecke angewendet."""
        factor = max(0.0, min(1.0, factor))
        lut = bytes(min(255, int(i * factor)) for i in range(256))
        return pix.translate(lut)

    @staticmethod
    def px(rgb):
        r, g, b = rgb
        return bytes((b, g, r, 0))

    @staticmethod
    def _darken(rgb, factor=0.82):
        r, g, b = rgb
        return (int(r*factor), int(g*factor), int(b*factor))

    def bg_key(self, rgb):
        """Schluessel des zwischengespeicherten Hintergrundmusters.

        Bewusst EINE Stelle, an der dieser Schluessel gebildet wird. Er
        stand vorher an drei Stellen von Hand ausgeschrieben (hier, in
        _restore_row_bg() und in _bg_fill()) - waechst der Schluessel um
        einen Bestandteil, greifen die anderen sonst still daneben und
        fuellen einfarbig statt mit Vignette."""
        return ("bg", rgb, self.width, self.height)

    def clear(self, rgb):
        key = self.bg_key(rgb)
        bg = self._rowcache.get(key)
        if bg is None:
            if VIGNETTE_ENABLED:
                variants = self._vignette_row_variants(rgb, self.width, self.stride)
                bg = bytearray(self.stride * self.height)
                self._apply_vignette_rows(bg, self.height, self.stride, variants)
            else:
                row = self.px(rgb) * self.width
                pad = b"\x00" * (self.stride - self.width * 4)
                bg = (row + pad) * self.height
            self._rowcache[key] = bg
        self.buf[:] = bg
        self.mark_full_redraw()

    def blend_rect(self, x, y, w, h, rgb, alpha):
        """Rechteck mit einer Farbe UEBERBLENDEN statt zu ueberschreiben -
        fuer Glow-/Schatten-Effekte. alpha=0..1 (0=keine Wirkung, 1=wie
        rect()). Kann NICHT gecacht werden (haengt vom vorhandenen
        Bildinhalt ab) - deshalb bewusst nur fuer kleine Bereiche
        (Glow-Ringe, Schatten), nicht fuer grosse Flaechen. Wie bei
        allen anderen Zeichenmethoden: schreibt nie mehr/weniger Bytes
        als der Zielbereich hat, um den Puffer nicht zu verschieben."""
        x = max(0, x); y = max(0, y)
        w = min(w, self.width - x); h = min(h, self.height - y)
        if w <= 0 or h <= 0 or alpha <= 0:
            return
        alpha = min(1.0, alpha)
        nb, ng, nr = rgb[2], rgb[1], rgb[0]  # BGRA-Reihenfolge im Puffer
        buflen = len(self.buf)
        need = w * 4
        for yy in range(y, y + h):
            off = yy * self.stride + x * 4
            end = off + need
            if end > buflen:
                continue
            row = bytearray(self.buf[off:end])
            for i in range(0, need, 4):
                row[i]   = int(row[i]   + (nb - row[i])   * alpha)
                row[i+1] = int(row[i+1] + (ng - row[i+1]) * alpha)
                row[i+2] = int(row[i+2] + (nr - row[i+2]) * alpha)
            if len(row) == need:
                self.buf[off:end] = row

    def blend_border(self, x, y, w, h, rgb, alpha, thickness=2):
        """Nur den RAND eines Rechtecks ueberblenden (vier duenne
        Streifen) statt der ganzen Flaeche - fuer Glow-Ringe deutlich
        billiger als blend_rect() auf die volle Flaeche, da nur der
        Umfang statt die Flaeche skaliert. Fuer KLEINE, bildschirm-
        unabhaengige Bereiche gedacht (z.B. Boxart-Rahmen/Schatten).
        Fuer breite, bildschirmfuellende Streifen gab es frueher die
        billigere Variante glow_border_fast() - sie ist mit dem
        Entfernen des Leuchtrands um die Listenmarkierung weggefallen
        (Nutzerwunsch: "glow Effekt komplett raus"). Die Technik dahinter
        lebt in blend_rect_fast() weiter, siehe dort."""
        t = max(1, thickness)
        self.blend_rect(x, y, w, t, rgb, alpha)                    # oben
        self.blend_rect(x, y + h - t, w, t, rgb, alpha)             # unten
        self.blend_rect(x, y, t, h, rgb, alpha)                     # links
        self.blend_rect(x + w - t, y, t, h, rgb, alpha)             # rechts

    def blend_rect_fast(self, x, y, w, h, base_bg, color, alpha):
        """Wie blend_rect(), aber mit vorgemischter FESTER Farbe statt
        echter Pixel-fuer-Pixel-Mischung - fuer FLAECHEN (z.B. den
        Boxart-Schatten). Der Trick: die
        Zielfarbe wird EINMAL berechnet statt pro Pixel, dann ueber
        das gecachte rect() gezeichnet. Wichtig bei groesseren
        Flaechen (z.B. schattenbreite = Cover-Breite) - echtes
        Pixel-Blending kostete hier auf HDMI bei einem Boxart-Schatten
        gemessen ueber 60% der gesamten Zeichenzeit einer Navigation
        (per cProfile bestaetigt), obwohl der Schatten selbst klein
        wirkt. Nimmt an, dass der Untergrund etwa base_bg entspricht -
        bei aktivem Hintergrundbild kann die Farbe dadurch leicht
        abweichen, bewusster Kompromiss fuer Geschwindigkeit."""
        mixed = tuple(int(bg + (c - bg) * alpha)
                      for bg, c in zip(base_bg, color))
        self.rect(x, y, w, h, mixed)

    def rect(self, x, y, w, h, rgb, scanlines=False):
        """scanlines=True: jede 2. Zeile dezent abgedunkelt (Retro-Look) -
        nur fuer reine Hintergrundflaechen, nicht fuer Markierungsbalken."""
        x = max(0, x); y = max(0, y)
        w = min(w, self.width - x); h = min(h, self.height - y)
        if w <= 0 or h <= 0:
            return
        # WICHTIG (Bugfix): _rectcache cacht nach (Farbe, EXAKTER Breite)
        # - bei leicht wechselnden Breiten (z.B. je nach Cover-
        # Seitenverhaeltnis, Glow-Ring-Position, Info-Textlaenge) sammelt
        # sich ueber viele Navigationen hinweg eine WACHSENDE Zahl nie
        # wieder verwendeter Eintraege an, die nie geloescht wird -
        # aehnliches Muster wie der in v1.32 behobene Pulsier-Cache-Bug,
        # nur an anderer Stelle. Per Differenzmessung bestaetigt: das
        # macht sich als spuerbare, mit der Zeit zunehmende Verzoegerung
        # bemerkbar. Einfache, sichere Absicherung: Cache bei
        # Ueberschreiten einer Obergrenze komplett leeren, statt einzelne
        # Eintraege aufwendig zu verwalten (LRU o.ae.) - der haeufige
        # Fall (dieselbe Farbe/Breite ueber mehrere Bilder hinweg, z.B.
        # Equalizer-Balken, Zeilen-Markierungen) bleibt dadurch weiterhin
        # schnell. Eigener Cache (nicht _rowcache), damit das Leeren
        # nicht die selten wechselnden, teuren Hintergrundmuster von
        # clear() mitreisst.
        if len(self._rectcache) > ROWCACHE_MAX_ENTRIES:
            self._rectcache.clear()
        key = (rgb, w)
        row = self._rectcache.get(key)
        if row is None:
            row = self.px(rgb) * w
            self._rectcache[key] = row
        row_dark = None
        if scanlines:
            key2 = (rgb, w, "dark")
            row_dark = self._rectcache.get(key2)
            if row_dark is None:
                row_dark = self.px(self._darken(rgb)) * w
                self._rectcache[key2] = row_dark
        # PERFORMANCE (gemessen, HDMI 1920x1080): diese Schleife laeuft bei
        # grossen Flaechen mehrere hundert Mal pro Aufruf und war im
        # Profiling der teuerste Einzelposten eines Seitenaufbaus. Die
        # Arbeit pro Durchlauf war unnoetig hoch: zwei Attributzugriffe
        # (self.stride, self.buf), eine Multiplikation und - obwohl
        # scanlines fast immer False ist - bei JEDEM Durchlauf eine
        # Bedingung samt Modulo-Rechnung.
        #
        # Jetzt: Puffer und Schrittweite einmal in lokale Variablen
        # (in CPython deutlich billiger als Attributzugriffe), Offset
        # fortlaufend addiert statt neu berechnet, und der haeufige Fall
        # ohne Scanlines bekommt eine eigene, minimale Schleife. Der
        # Scanlines-Fall bleibt unveraendert. Gemessen: 0.427 -> 0.382 ms
        # fuer eine 700x800-Flaeche (-11%), bei bitgenau gleichem
        # Ergebnis - es werden dieselben Bytes an dieselben Stellen
        # geschrieben, nur mit weniger Rechnerei drumherum.
        buf = self.buf
        stride = self.stride
        need = w * 4
        off = y * stride + x * 4
        if scanlines:
            for yy in range(y, y + h):
                buf[off:off + need] = row_dark if (yy % 2) else row
                off += stride
        else:
            for _ in range(h):
                buf[off:off + need] = row
                off += stride

    def _rounded_indents(self, radius):
        """Einzug je Randzeile fuer eine Eckenrundung dieses Radius -
        einmal berechnet, dann aus dem Zwischenspeicher. Ausgelagert in
        Build 97, weil rect_rounded_schatten() dieselbe Tabelle braucht:
        nur mit exakt derselben Rundung laesst sich ausrechnen, welcher
        Teil des Schattens von der Karte verdeckt wird."""
        key_ind = ("rounded_indent", radius)
        indents = self._rectcache.get(key_ind)
        if indents is None:
            indents = []
            r2 = radius * radius
            for ry in range(radius):
                dy = radius - ry - 1
                dx = 0
                while dx < radius and (radius - dx - 1) ** 2 + dy * dy <= r2:
                    dx += 1
                indents.append(radius - dx)
            self._rectcache[key_ind] = indents
        return indents

    def _zeilenband(self, rgb, n):
        """n Bildpunkte einer Farbe als fertige Bytes - gleiche
        Zwischenspeicher-Konvention wie rect()/rect_rounded()."""
        key = (rgb, n)
        row = self._rectcache.get(key)
        if row is None:
            row = self.px(rgb) * n
            self._rectcache[key] = row
        return row

    @staticmethod
    def _ohne_teile(a, b, ohne):
        """[a, b) abzueglich des ausgesparten Bereichs `ohne`, als bis zu
        zwei Teilstuecke."""
        if ohne is None:
            return ((a, b),) if b > a else ()
        oa, ob = ohne
        teile = []
        for p, q in ((a, min(b, oa)), (max(a, ob), b)):
            if q > p:
                teile.append((p, q))
        return tuple(teile)

    def karte_mit_schatten(self, x, y, w, h, versatz, karte_rgb,
                           schatten_rgb, radius=None):
        """Einen abgerundeten Kasten MIT Schlagschatten zeichnen -
        bitgenau dasselbe Ergebnis wie

            rect_rounded_schatten(x, y, w, h, versatz, schatten_rgb, r)
            rect_rounded(x, y, w, h, karte_rgb, r)

        nur schneller.

        NEU (Build 98). WARUM: Karte und sichtbarer Schattenstreifen
        liegen in den geraden Mittelzeilen direkt NEBENEINANDER - die
        Karte endet bei x+w, der Streifen geht von x+w bis x+w+versatz.
        Zwei getrennte Zeichenwege bedeuten dort zwei Zeilenschleifen
        ueber dieselben rund 900 Bildzeilen, und die Zeilenschleife ist
        der teure Teil, nicht die kopierten Bytes (gemessen: eine Zeile
        mit 36 Byte kostet 0,25 us, eine mit 3076 Byte 0,40 us - der
        Grundaufwand ueberwiegt).

        Hier wird stattdessen EINE vorgefertigte Zeile aus Kartenfarbe
        und Schattenfarbe geschrieben. Gemessen auf 1080p:

            getrennt              0,636 ms
            zusammengefasst       0,45  ms

        Ausserhalb der geraden Mittelzeilen (Eckenrundungen, die
        Schattenzeilen unterhalb der Karte) bleibt alles beim
        bewaehrten Weg - dort ueberlappen die beiden Formen nicht so
        einfach, und es sind nur wenige Dutzend Zeilen."""
        if w <= 0 or h <= 0:
            return
        if versatz <= 0:
            self.rect_rounded(x, y, w, h, karte_rgb, radius)
            return
        r = radius
        if r is None:
            r = max(1, min(w, h) // 8)
        r = max(0, min(r, w // 2, h // 2))

        # Das zusammengefasste Band gibt es nur, wenn NICHTS beschnitten
        # wird - sonst haetten Karte und Schatten verschiedene Formen
        # (rect_rounded() beschneidet vor dem Runden, siehe dort), und
        # die einfache Nebeneinander-Annahme gilt nicht mehr.
        band = None
        if (x >= 0 and y >= 0 and x + w + versatz <= self.width
                and y + h + versatz <= self.height and h - r > versatz + r):
            band = (y + versatz + r, y + h - r)

        self.rect_rounded_schatten(x, y, w, h, versatz, schatten_rgb,
                                   radius, ohne=band)
        self.rect_rounded(x, y, w, h, karte_rgb, radius, ohne=band)
        if band is None:
            return

        if len(self._rectcache) > ROWCACHE_MAX_ENTRIES:
            self._rectcache.clear()
        key = ("karte+schatten", karte_rgb, schatten_rgb, w, versatz)
        zeile = self._rectcache.get(key)
        if zeile is None:
            zeile = self.px(karte_rgb) * w + self.px(schatten_rgb) * versatz
            self._rectcache[key] = zeile
        buf, stride = self.buf, self.stride
        need = (w + versatz) * 4
        off = band[0] * stride + x * 4
        for _ in range(band[1] - band[0]):
            buf[off:off + need] = zeile
            off += stride

    def rect_rounded_schatten(self, x, y, w, h, versatz, rgb,
                              radius=None, ohne=None):
        """Den SICHTBAREN Teil eines Schlagschattens zeichnen - also den
        abgerundeten Kasten bei (x+versatz, y+versatz) OHNE alles, was
        der gleich grosse Kasten bei (x, y) gleich darueber legt.

        NEU (Build 97). WARUM: der Schatten des Cover-Panels wurde als
        volles Rechteck in Kartengroesse gemalt und danach von der Karte
        fast vollstaendig ueberdeckt. Auf 1080p sind das 769x945 =
        726.705 Bildpunkte, von denen **15.210 (2,1 %) jemals zu sehen
        sind** - der Rest wird im selben Atemzug uebermalt. Gemessen
        kostete das 0,461 ms pro Panel-Aufbau, also 35 % des gesamten
        Panels, fuer nichts.

        Statt die sichtbare Form von Hand als zwei Streifen nachzubauen
        (naheliegend, aber an den vier gerundeten Ecken nicht exakt -
        auch die Karte hat Eckkerben, durch die der Schatten stellenweise
        durchscheint), wird hier Bildzeile fuer Bildzeile gerechnet: der
        Schatten hat in jeder Zeile eine Spanne, die Karte auch, und
        gezeichnet wird die Differenz. Damit ist das Ergebnis
        bitgenau dasselbe wie vorher - nur ohne die verdeckten Punkte.
        Genau das prueft tools/test_cover_panel.py."""
        if w <= 0 or h <= 0 or versatz <= 0:
            return
        if len(self._rectcache) > ROWCACHE_MAX_ENTRIES:
            self._rectcache.clear()

        def gestalt(gx, gy):
            """Position, Groesse und Einzugstabelle eines der beiden
            Kaesten - GENAU so beschnitten, wie rect_rounded() es tut.

            Das ist keine Kosmetik: rect_rounded() beschneidet Breite und
            Hoehe am Bildrand ZUERST und rundet danach - eine am rechten
            Rand abgeschnittene Karte bekommt also eine andere Rundung
            als eine freistehende. Wer das hier nicht nachbildet, malt
            am Bildrand einen anders geformten Schatten. Genau daran ist
            der erste Versuch gescheitert (Test 2)."""
            gx_ = max(0, gx)
            gy_ = max(0, gy)
            gw = min(w, self.width - gx_)
            gh = min(h, self.height - gy_)
            if gw <= 0 or gh <= 0:
                return None
            r = radius
            if r is None:
                r = max(1, min(gw, gh) // 8)
            r = max(0, min(r, gw // 2, gh // 2))
            return (gx_, gy_, gw, gh, r,
                    self._rounded_indents(r) if r > 0 else None)

        schatten = gestalt(x + versatz, y + versatz)
        if schatten is None:
            return
        karte = gestalt(x, y)
        sx, sy, sw, sh, sr, sind = schatten

        def einzug(gestalt_, j):
            if gestalt_ is None:
                return None
            _gx, _gy, gw, gh, r, ind = gestalt_
            if not ind or not (0 <= j < gh):
                return 0 if 0 <= j < gh else None
            if j < r:
                return ind[j]
            if j >= gh - r:
                return ind[gh - 1 - j]
            return 0

        stride, buf, breite = self.stride, self.buf, self.width

        def zeile(zy, a, b):
            a = max(a, 0)
            b = min(b, breite)
            if b <= a:
                return
            n = b - a
            o = zy * stride + a * 4
            buf[o:o + n * 4] = self._zeilenband(rgb, n)

        # SCHNELLER WEG fuer den Normalfall: solange beide Kaesten
        # unbeschnitten und gleich geformt sind, ist in jeder Zeile, in
        # der BEIDE gerade verlaufen, genau ein Streifen der Breite
        # `versatz` sichtbar - der rechts neben der Karte. Das sind fast
        # alle Zeilen, und sie gehen in EINEM rect()-Aufruf weg statt in
        # neunhundert Einzelzuweisungen. Ohne diese Abkuerzung war die
        # "sparsame" Fassung gemessen VIERMAL LANGSAMER als das volle
        # Rechteck, das sie ersetzen sollte.
        gerade_von, gerade_bis = None, None
        if (karte is not None and karte[2] == sw and karte[3] == sh
                and karte[4] == sr and (sx, sy) == (x + versatz, y + versatz)
                and (karte[0], karte[1]) == (x, y)):
            gerade_von = sr
            gerade_bis = sh - sr - versatz
            if gerade_bis > gerade_von:
                # ohne= spart die Zeilen aus, die karte_mit_schatten()
                # gleich in EINER Zuweisung zusammen mit der Karte
                # schreibt.
                for a, b in self._ohne_teile(sy + gerade_von,
                                             sy + gerade_bis, ohne):
                    self.rect(sx + sw - versatz, a, versatz, b - a, rgb)
            else:
                gerade_von, gerade_bis = None, None

        for j in range(sh):
            if gerade_von is not None and gerade_von <= j < gerade_bis:
                continue
            zy = sy + j
            if zy < 0 or zy >= self.height:
                continue
            if ohne is not None and ohne[0] <= zy < ohne[1]:
                continue
            e = einzug(schatten, j)
            s0, s1 = sx + e, sx + sw - e
            if s1 <= s0:
                continue
            ce = einzug(karte, zy - (karte[1] if karte else 0))
            if karte is None or ce is None:
                zeile(zy, s0, s1)
                continue
            cx, _cy, cw = karte[0], karte[1], karte[2]
            zeile(zy, s0, min(s1, cx + ce))
            zeile(zy, max(s0, cx + cw - ce), s1)

    def rect_rounded(self, x, y, w, h, rgb, radius=None, ohne=None):
        """Wie rect(), aber mit abgerundeten Ecken. radius in Pixeln
        (bereits skaliert) - ohne Angabe ein kleiner, dezenter Wert.
        Kostet nur ein paar zusaetzliche, KUERZERE Randzeilen (die
        Eckenrundung), nicht die ganze Flaeche neu - der Mittelteil
        laeuft weiterhin ueber das normale, gecachte rect(). Die
        Einzugstabelle pro Randzeile wird nur einmal pro radius-Wert
        berechnet und mitgecacht, nicht bei jedem Aufruf neu.

        ohne=(ya, yb) (Build 98): diese Bildzeilen NICHT anfassen. Nur
        fuer karte_mit_schatten() gedacht - dort werden Karte und
        Schattenstreifen in den geraden Mittelzeilen in EINER
        Zuweisung geschrieben, und dieser Aufruf muss sie in Ruhe
        lassen. Standardwert None laesst jeden bestehenden Aufrufer
        unveraendert."""
        x = max(0, x); y = max(0, y)
        w = min(w, self.width - x); h = min(h, self.height - y)
        if w <= 0 or h <= 0:
            return
        if radius is None:
            radius = max(1, min(w, h) // 8)
        radius = max(0, min(radius, w // 2, h // 2))
        if radius <= 0:
            self.rect(x, y, w, h, rgb)
            return
        indents = self._rounded_indents(radius)
        # PERFORMANCE-FIX (Nutzerwunsch: "noch mehr Performance rausholen,
        # vor allem HDMI" - echtes Profiling auf echter Hardware zeigte
        # rect_rounded() bei nur 3 Aufrufen pro Bild trotzdem 40-50ms
        # (~15ms PRO Aufruf) - 5-6x teurer als das normale, bereits
        # gecachte rect() (~2.5-3.5ms pro Aufruf). Ursache: die FORM der
        # Rundung (indents) war zwar schon gecacht, aber die
        # eigentlichen PIXEL-ZEILEN dafuer (px * rw) wurden bei JEDEM
        # Aufruf neu berechnet - obwohl sie sich bei gleicher Farbe und
        # gleicher Zeilenbreite nicht aendern. Fix: dieselbe (Farbe,
        # Breite)-Cache-Konvention wie rect() nutzen, im GLEICHEN
        # self._rectcache - Auswahl-Markierung und Cover-Panel-Karte
        # nutzen ueber viele Navigationen hinweg immer wieder dieselben
        # paar (Farbe, Randbreite)-Kombinationen, der Cache greift also
        # praktisch sofort ab dem zweiten Aufruf.
        if len(self._rectcache) > ROWCACHE_MAX_ENTRIES:
            self._rectcache.clear()

        if ohne is None:
            def _ausgespart(_zy):
                return False
        else:
            _oa, _ob = ohne

            def _ausgespart(zy):
                return _oa <= zy < _ob

        for i, indent in enumerate(indents):
            rw = w - 2 * indent
            if rw <= 0:
                continue
            row_key = (rgb, rw)
            row = self._rectcache.get(row_key)
            if row is None:
                row = self.px(rgb) * rw
                self._rectcache[row_key] = row
            yy_top = y + i
            yy_bot = y + h - 1 - i
            if 0 <= yy_top < self.height and not _ausgespart(yy_top):
                off = yy_top * self.stride + (x + indent) * 4
                self.buf[off:off + rw * 4] = row
            if (yy_bot != yy_top and 0 <= yy_bot < self.height
                    and not _ausgespart(yy_bot)):
                off = yy_bot * self.stride + (x + indent) * 4
                self.buf[off:off + rw * 4] = row
        mid_top = y + radius
        mid_h = h - 2 * radius
        if mid_h > 0:
            if ohne is None:
                self.rect(x, mid_top, w, mid_h, rgb)
            else:
                # Der Mittelteil zerfaellt in bis zu zwei Stuecke.
                ya, yb = ohne
                for a, b in ((mid_top, min(mid_top + mid_h, ya)),
                             (max(mid_top, yb), mid_top + mid_h)):
                    if b > a:
                        self.rect(x, a, w, b - a, rgb)

    def _glyph_row(self, bits, scale, fg, bg):
        key = (bits, scale, fg, bg)
        row = self._glyphcache.get(key)
        if row is None:
            f = self.px(fg); b = self.px(bg)
            row = b"".join((f if bits >> i & 1 else b) * scale for i in range(8))
            self._glyphcache[key] = row
        return row

    def _text_strip(self, s, scale, fg, bg, cachen=True):
        """Fertigen Pixel-Streifen fuer eine komplette Textzeile liefern -
        aus dem Cache, oder einmal gebaut und dort abgelegt. Rueckgabe ist
        eine Liste von 8*scale Byte-Zeilen.

        Ganze Text-Zeile cachen: Beim Scrollen/Neuzeichnen sind die
        meisten Labels bereits bekannt (Spieltitel, Menuepunkte usw.) -
        dann reicht ein fertiger Streifen zum Blitten, statt jedes Mal
        wieder Buchstabe fuer Buchstabe (und Zeile fuer Zeile pro
        Buchstabe) zusammenzusetzen. Groesster Hebel bei den reinen
        Zeichenkosten, siehe Kopfkommentar-Changelog.

        AUSGELAGERT aus text() (wo dieser Block frueher direkt stand),
        damit text() UND text_window() sich denselben Cache-Eintrag
        teilen koennen - die ausfuehrliche Begruendung dafuer steht bei
        text_window()."""
        key = (s, scale, fg, bg)
        strip = self._textcache.get(key)
        if strip is None:
            self._textcache_misses += 1
            # cachen=False (Build 141): fuer Text, der GARANTIERT nur
            # einmal vorkommt - die Spielbeschreibung in der Galerie.
            # Jede ihrer Zeilen ist ein eigener Satz; ein Eintrag dafuer
            # wird nie wieder getroffen, verdraengt aber einen, der
            # getroffen wuerde. Im Profil des Nutzers standen 502
            # Fehltreffer bei 78,7 % Trefferquote. Gebaut wird der
            # Streifen natuerlich trotzdem - er wandert nur nicht in
            # den Cache. Dieselbe Ueberlegung wie bei text_window()
            # fuer die Laufschrift, nur andersherum geloest.
            # PERFORMANCE-FIX (Nutzer-Rueckmeldung: "muss unter HDMI
            # fluessiger laufen" - diesmal aus einer gezielten Messung
            # statt aus einer Vermutung). Der TEXTCACHE-Mitschnitt von
            # echter Hardware zeigte eine Trefferquote von 83-85% - gut
            # aussehend, aber entscheidend ist, was ein FEHLTREFFER
            # kostet: nachgemessen ist er 45x so teuer wie ein Treffer
            # (0.45ms gegen 0.010ms bei einem 40-Zeichen-Titel). Die
            # verbleibenden 15-17% Fehltreffer verursachen dadurch rund
            # 90% der gesamten text()-Zeit - genau die 34-74ms, die im
            # echten Profiling unter draw_page_items() auftauchten. Nicht
            # die Trefferquote war also das Problem, sondern der Preis
            # pro Fehltreffer.
            #
            # Der Streifen entsteht jetzt mit 8 b"".join()-Aufrufen (einer
            # je Glyphenzeile, ueber alle Zeichen auf einmal) statt mit
            # len(s)*8*scale einzelnen Slice-Zuweisungen in vorab
            # angelegte Bytearrays - bei einem 40-Zeichen-Titel auf HDMI
            # (scale=3) also 8 statt 960 Einzeloperationen, und ohne die
            # anschliessende komplette bytes()-Zweitkopie aller Zeilen.
            # Ausserdem sind die scale Wiederholungen EINER Glyphenzeile
            # zwangslaeufig identisch - sie referenzieren deshalb dasselbe
            # unveraenderliche bytes-Objekt, statt es scale-mal zu
            # kopieren (nur lesend genutzt, siehe Blit-Schleife unten).
            #
            # Gemessen: Listenzeile (40 Zeichen, scale=3) 0.382ms ->
            # 0.116ms (3.3x), Kopfzeile (scale=6) 0.243ms -> 0.049ms
            # (5.0x); Speicherbedarf pro Cache-Eintrag bei scale=3 von
            # 90KB auf 30KB (3x weniger, entlastet zusaetzlich das
            # _TEXTCACHE_LIMIT bei langen Sitzungen). Das ERGEBNIS ist
            # dabei bitgenau dasselbe wie vorher - geprueft mit 580
            # Byte-Vergleichen (kompletter ASCII- UND Latin-1-Bereich,
            # der "?"-Rueckfall ausserhalb davon, die Grenzfaelle der
            # Bereichspruefung, alle Skalierungen, 300 Zufallstexte)
            # sowie einem Vorher/Nachher-Vergleich von 40 komplett
            # gerenderten Bildschirmseiten (CRT und HDMI, inkl. einem
            # vollen Schimmer-Zyklus) - 0 Abweichungen.
            #
            # Die Font-Zuordnung passiert jetzt einmal PRO ZEICHEN statt
            # einmal pro Zeichen UND Glyphenzeile (vorher 8x redundant).
            # NEU (uebernommen von TheRealSutefan - Latin-1-Ergaenzung,
            # gleiches 8x8-Format wie FONT8X8): Umlaute/Akzente (ä/ö/ü/ß
            # usw.) wurden bisher als "?" dargestellt. FONT_EXTRA deckt
            # den Latin-1-Bereich 0xA0-0xFF ab; alles ausserhalb bleibt
            # beim bisherigen "?"-Rueckfall.
            glyphs = []
            for ch in s:
                code = ord(ch)
                if code <= 127:
                    glyphs.append((FONT8X8, code * 8))
                elif 0xA0 <= code <= 0xFF:
                    glyphs.append((FONT_EXTRA, (code - 0xA0) * 8))
                else:
                    glyphs.append((FONT8X8, 0x3F * 8))
            _glyph_row = self._glyph_row
            strip = []
            for gy in range(8):
                grow = b"".join([_glyph_row(_fnt[_base + gy], scale, fg, bg)
                                 for _fnt, _base in glyphs])
                for _rep in range(scale):
                    strip.append(grow)
            if cachen:
                self._textcache[key] = strip
                self._textcache_order.append(key)
                if len(self._textcache_order) > self._TEXTCACHE_LIMIT:
                    self._textcache_evictions += 1
                    self._textcache.pop(self._textcache_order.pop(0), None)
        else:
            self._textcache_hits += 1
        return strip

    def text(self, x, y, s, scale=2, fg=None, bg=None, cachen=True):
        if fg is None:
            fg = C_TEXT
        if bg is None:
            bg = C_BG
        cw = 8 * scale
        if y + 8 * scale > self.height or y < 0 or x < 0:
            return
        # Nur so viele Zeichen wie auf den Schirm passen - identischer
        # Abschneidepunkt wie die alte, zeichenweise Fassung (die bei
        # gx + cw > self.width abgebrochen hat), nur vorab statt
        # mitten in der Schleife berechnet.
        maxch = (self.width - x) // cw
        if maxch <= 0:
            return
        if len(s) > maxch:
            s = s[:maxch]
        if not s:
            return
        strip = self._text_strip(s, scale, fg, bg, cachen)
        w4 = len(strip[0])
        xo = x * 4
        # GEAENDERT (Build 132): memoryview auf das Ziel.
        #
        # Im DRAGEND_PROFILE des Nutzers stand text() mit 13 ms EIGENER
        # Zeit (tottime) bei 21 Aufrufen - also nicht im Aufbauen des
        # Streifens, sondern in genau dieser Schleife. Bei Schriftgroesse
        # 3 sind das 24 Zeilen je Aufruf, rund 500 Zuweisungen je
        # Seitenaufbau.
        #
        # "self.buf[off:off+w4] = row" auf einem bytearray muss den
        # allgemeinen Fall abdecken, in dem sich die Laenge aendert und
        # der Puffer wachsen oder schrumpfen koennte. Auf einem
        # memoryview ist die Groesse fest - es bleibt reines Kopieren.
        # Gemessen 0.008 -> 0.005 ms je Aufruf bei warmem Streifen-Cache.
        ziel = memoryview(self.buf)
        for i, row in enumerate(strip):
            off = (y + i) * self.stride + xo
            ziel[off:off + w4] = row

    # Obergrenze fuer text_window(): laengere Texte werden NICHT am Stueck
    # gecacht, sondern fallen auf das bisherige Verhalten zurueck (nur den
    # sichtbaren Ausschnitt rendern). Grosszuegig gewaehlt - echte
    # Spieltitel liegen weit darunter -, verhindert aber, dass ein
    # pathologisch langer Name einen entsprechend breiten Streifen anlegt.
    TEXT_WINDOW_MAX_CHARS = 300

    def text_window(self, x, y, full, off, maxc, scale=2, fg=None, bg=None):
        """Einen AUSSCHNITT von `full` zeichnen (maxc Zeichen ab Zeichen
        `off`) - gedacht fuer die Laufschrift der markierten Zeile.

        PERFORMANCE-FIX (Nutzer-Rueckmeldung: "Scrollen soll butterweich
        sein" - die Ursache wurde erst durch eine gezielte Messung
        gefunden, nicht durch Codelesen). Die Laufschrift rueckt alle
        0.18s um ein Zeichen weiter und zeichnete dafuer bisher den
        Teilstring full[off:off+maxc] - fuer den Text-Cache ist das jedes
        Mal ein voellig neuer Schluessel, also ein GARANTIERTER
        Fehltreffer im Sekundentakt, dauerhaft, auch wenn man einfach nur
        stillsteht. Nachgemessen an einem typischen langen Titel: 23
        Fehltreffer und 23 Cache-Eintraege fuer einen EINZIGEN Titel bei
        einer Trefferquote von 86.1% - das deckt sich fast exakt mit den
        83-85%, die auf echter Hardware gemessen wurden, und erklaert
        damit den Hauptteil der dortigen Fehltreffer.

        Da jedes Zeichen im fertigen Streifen exakt cw*4 Bytes an fester
        Position belegt (keine Unterschneidung), IST der Ausschnitt ab
        Zeichen `off` schlicht ein Byte-Bereich des Streifens fuer den
        VOLLEN Titel. Der volle Titel wird deshalb EINMAL gerendert und
        danach nur noch ein Fenster daraus geblittet - aus 23 teuren
        Neu-Renderings werden 3 (eines je Schimmer-Stufe), alles Weitere
        sind reine Kopien. Das Ergebnis ist bitgenau dasselbe wie vorher,
        geprueft ueber 10576 Laufschrift-Positionen (44 Titel inklusive
        Umlauten, alle Skalierungen, mehrere Farbkombinationen)."""
        if fg is None:
            fg = C_TEXT
        if bg is None:
            bg = C_BG
        cw = 8 * scale
        if y + 8 * scale > self.height or y < 0 or x < 0:
            return
        maxch = (self.width - x) // cw
        if maxch <= 0 or maxc <= 0 or not full:
            return
        # Nie mehr Zeichen zeichnen als auf den Schirm passen - dieselbe
        # Abschneide-Regel wie in text().
        maxc = min(maxc, maxch)
        if len(full) > self.TEXT_WINDOW_MAX_CHARS:
            # Rueckfall auf das bisherige Verhalten, siehe Obergrenze oben.
            self.text(x, y, full[off:off + maxc], scale, fg, bg)
            return
        strip = self._text_strip(full, scale, fg, bg)
        total = len(strip[0]) // (cw * 4)
        off = max(0, min(off, max(0, total - maxc)))
        b0 = off * cw * 4
        b1 = min(b0 + maxc * cw * 4, len(strip[0]))
        if b1 <= b0:
            return
        n = b1 - b0
        xo = x * 4
        for i, row in enumerate(strip):
            o = (y + i) * self.stride + xo
            self.buf[o:o + n] = row[b0:b1]

    def flip(self, skip_vsync=False):
        # Erst auf den Vertical-Blank warten (falls unterstuetzt), DANN
        # schreiben - vermeidet Tearing bei der grossen Vollbild-Kopie.
        #
        # NEUES FEATURE (Nutzerwunsch: "kann man das Vsync-Warten waehrend
        # des Scrollens weglassen, um schneller zu werden?" - AUSDRUECKLICH
        # als Kompromiss erklaert und vom Nutzer angefragt, nicht von mir
        # unilateral entschieden): skip_vsync=True ueberspringt das Warten
        # bewusst - spart die gemessenen 8-17ms auf echter Hardware, aber
        # mit echtem Bildriss-Risiko (Tearing), da der naechste Bildaufbau
        # dann NICHT mehr zwingend mit dem Monitor-Bildwechsel
        # synchronisiert ist. Der Aufrufer (siehe fast_scroll_enabled() in
        # fe/settings.py, verwendet in frontend.py) entscheidet gezielt UND
        # NUR waehrend aktiven Scrollens - im Ruhezustand bleibt Vsync
        # immer aktiv. Standardwert False haelt jeden bestehenden
        # Aufrufer automatisch beim bisherigen, sicheren Verhalten.
        if not skip_vsync:
            self._wait_vsync()
        # Nach dem Warten, unmittelbar vor dem Schreiben: so ist das
        # beobachtete Fenster so gross wie moeglich.
        if self._rueck_proben is not None:
            self._rueckleser_pruefen()
        if self.haeppchen > 1:
            self._flip_haeppchenweise()
        else:
            # Direkte Slice-Zuweisung: mmap nimmt das bytearray ohne die
            # teure bytes()-Zwischenkopie (auf 1080p ~8 MB pro Frame).
            self.mm[:] = self.buf
        if self._rueck_proben is not None:
            self._rueckleser_merken()
        self.flip_gen += 1
        self.flip_event.set()

    def _flip_haeppchenweise(self):
        """Dasselbe Bild, aber in mehreren Stuecken statt in einem Zug.

        NEU (Build 181) - ein MESSGEGENSTAND, kein Feature. Standard
        ist aus, siehe FLIP_HAEPPCHEN_FLAG in fe/settings.py.

        WORUM ES GEHT

        Bei 1920x1080 blitzt achtmal je Minute MiSTers eigenes
        Menuebild durch, je ein bis zwei Bilder lang, jedes Mal dicht
        an einem Scrollschritt. Bei halber Aufloesung nicht.
        Nachgemessen (zuck_probe.py, zwei Abschnitte): MiSTer wacht
        dabei nicht oefter auf als im Leerlauf - er zeichnet also
        nicht dazwischen. Unsere Ebene faellt kurz aus.

        DIE VERMUTUNG, DIE HIER GEPRUEFT WIRD

        ARM und FPGA teilen sich beim DE10-Nano denselben Speicher.
        Ein Vollbild sind 7,9 MB, und die schreiben wir in EINEM Zug -
        gemessen 12,6 ms, also fast eine ganze Bildperiode am Stueck.
        Bekommt der Scaler in dieser Zeit seine Zeilen nicht
        rechtzeitig, faellt unsere Ebene weg. Bei halber Aufloesung
        ist es ein Viertel davon, und es passt in die Luecken.

        Trifft das zu, muss es besser werden, wenn derselbe Inhalt in
        Haeppchen mit Atempausen dazwischen geschrieben wird. Trifft
        es nicht zu, aendert sich nichts - und wir sind eine
        Moeglichkeit los. Beides ist ein Ergebnis.

        WARUM MEMORYVIEW

        self.mm[a:b] = self.buf[a:b] waere der naheliegende Weg und
        der falsche: das Stueck rechts erzeugt jedes Mal eine KOPIE
        des Ausschnitts. Bei sechzehn Haeppchen waeren das sechzehn
        Zwischenkopien von je einem halben Megabyte - die Messung
        haette dann vor allem den Mehraufwand gemessen, den sie selbst
        verursacht. Ueber memoryview geht es ohne Zwischenkopie."""
        n = self.haeppchen
        schritt = ((self.size + n - 1) // n + 3) & ~3    # 4-Byte-Raster
        ziel, quelle = self._mv_mm, self._mv_buf
        pause = self.haeppchen_pause
        pos = 0
        while pos < self.size:
            ende = pos + schritt
            if ende > self.size:
                ende = self.size
            ziel[pos:ende] = quelle[pos:ende]
            pos = ende
            if pause and pos < self.size:
                time.sleep(pause)

    def flip_rows(self, y, h, skip_vsync=False):
        """Nur einen Zeilenbereich auf den Schirm bringen (Laufschrift).
        skip_vsync: siehe ausfuehrlichen Kommentar bei flip()."""
        y0 = max(0, y)
        y1 = min(self.height, y + h)
        if y1 <= y0:
            return
        if not skip_vsync:
            self._wait_vsync()
        off = y0 * self.stride
        end = y1 * self.stride
        self.mm[off:end] = self.buf[off:end]
        if self._rueck_proben is not None:
            self._rueckleser_merken(y0, y1)
        self.flip_gen += 1
        self.flip_event.set()

    def close(self):
        try:
            self.mm.close(); os.close(self.fd)
        except Exception:
            pass
        # Build 168: der Rueckfall ueber /dev/mem haelt einen zweiten
        # Dateizeiger. Eigener try-Block, damit ein Fehler oben ihn
        # nicht ueberspringt - sonst bliebe /dev/mem offen.
        try:
            if getattr(self, "_mem_fd", None) is not None:
                os.close(self._mem_fd)
                self._mem_fd = None
        except Exception:
            pass
