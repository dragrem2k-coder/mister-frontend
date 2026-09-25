#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wer zeichnet da dazwischen? - Messung zum Zucken.

    python3 /media/fat/frontend/zuck_probe.py

WORUM ES GEHT

In einer Bildschirmaufnahme bei 1920x1080 blitzt achtmal je Minute
MiSTers EIGENES Menuebild durch das Frontend - der Arcade-Hintergrund
mit dem MiSTer-Logo, je 33 bis 166 Millisekunden, jedes Mal dicht an
einem Scrollschritt. Bei halber Aufloesung tritt es nicht auf. Das
Frontend selbst laeuft dabei ungestoert weiter; es ist also nicht
unser Zeichnen, das haengt.

WAS DER ERSTE LAUF ERGEBEN HAT (SuTe, 25.09., 1080p)

    50 Aufwachmomente in 60 s, je ein einziger CPU-Tick,
    hoechste Last 48 %, zusammen 1,7 % der Zeit

MiSTer zeichnet also NICHT durchgehend - bei sichtbarem OSD waeren es
100 % am Stueck (siehe Build 152). Er schlaeft und zuckt kurz.

Aber: 50 Aufwachmomente stehen 8 sichtbaren Aufblitzern gegenueber.
Sechs zu eins. "MiSTer wacht auf" ist damit allein noch keine
Erklaerung.

WARUM DIESE FASSUNG ZWEI ABSCHNITTE MISST

Weil der erste Lauf nur den Fehlerfall gemessen hat - genau der
Fehler, der in Build 148 zwei Tage gekostet hat und in Build 152 so
festgehalten wurde:

    "Eine Messung im Fehlerfall ist keine Messung des Systems. Immer
     auch den funktionierenden Zustand aufnehmen - der Unterschied ist
     das Signal, nicht der Absolutwert."

Ohne den Ruhewert sagen die 50 nichts. Vielleicht wacht MiSTer im
Leerlauf genauso oft auf, und mit dem Scrollen hat es nichts zu tun.

Deshalb jetzt:

    Abschnitt 1   RUHE       Haende weg, nichts anfassen
    Abschnitt 2   SCROLLEN   durchscrollen, bis es zuckt

Und am Ende der Vergleich der beiden.

DER ZWEITE LAUF, DEN ES BRAUCHT

Dasselbe noch einmal bei HALBER Aufloesung, wo das Zucken nicht
auftritt. Die Aufloesung steht im Kopf der Ausgabe, damit die beiden
Dateien nicht verwechselt werden koennen.

    Ruhe klein, Scrollen gross   -> es haengt an der Eingabe
    beide gleich gross           -> normaler Haushalt von MiSTer
    halbe Aufloesung genauso     -> die Aufwachmomente sind NICHT die
                                    Ursache; dann liegt es an der
                                    Anzeige-Ebene, unterhalb von uns

WAS ES NICHT TUT

Es aendert nichts. Es liest /proc und /sys, sonst nichts. Das Frontend
laeuft dabei normal weiter - es SOLL laufen, denn gemessen wird ja,
was waehrend des Scrollens passiert.

ZUR AUFLOESUNG DER MESSUNG

Die CPU-Zeit eines Prozesses waechst in festen Schritten (ueblich 100
je Sekunde, also 10 ms). Feiner als ein Tick geht nicht, egal wie oft
man nachsieht - deshalb wird hier nicht schneller abgetastet, sondern
es werden TICKS gezaehlt. Das ist die ehrliche Groesse.
"""
import os
import sys
import time

TAKT = 0.02                      # 50 Messungen je Sekunde
# Dieselbe Schwelle wie im Frontend (Frontend.MISTER_BESCHAEFTIGT):
# mittig in einer Luecke von zwei Groessenordnungen.
SCHWELLE = 25.0
AUSGABE = "/tmp/dragend_zuck.txt"

ABSCHNITTE = (
    ("RUHE", 20.0,
     "Jetzt bitte NICHTS anfassen - kein Pad, keine Tastatur."),
    ("SCROLLEN", 30.0,
     "Jetzt durchscrollen, so dass das Zucken auftritt."),
)


def _hz():
    try:
        return os.sysconf("SC_CLK_TCK") or 100
    except (ValueError, OSError):
        return 100


def mister_pid():
    """Die Prozessnummer des MiSTer-Hauptprogramms - oder None.

    Bewusst genauso gesucht wie im Frontend (_mister_last): ueber die
    Kommandozeile, nicht ueber den Prozessnamen. Der Name ist je nach
    Fassung mal 'MiSTer', mal etwas anderes."""
    try:
        eintraege = os.listdir("/proc")
    except OSError:
        return None
    for d in eintraege:
        if not d.isdigit():
            continue
        try:
            with open("/proc/%s/cmdline" % d, "rb") as f:
                roh = f.read().decode("utf-8", "replace")
        except OSError:
            continue
        if "MiSTer" in roh and "python" not in roh and "zuck_probe" not in roh:
            return int(d)
    return None


def cpu_ticks(pid):
    """utime + stime des Prozesses - oder None, wenn er weg ist."""
    try:
        with open("/proc/%d/stat" % pid, "rb") as f:
            teile = f.read().decode("utf-8", "replace").rsplit(")", 1)[-1].split()
    except (OSError, IndexError):
        return None
    try:
        # Nach dem ")" ist Feld 0 der Zustand; utime/stime sind 11 und 12.
        return int(teile[11]) + int(teile[12])
    except (IndexError, ValueError):
        return None


def aktive_konsole():
    try:
        with open("/sys/class/tty/tty0/active") as f:
            return f.read().strip()
    except OSError:
        return "?"


def aufloesung():
    """Die Groesse des Linux-Framebuffers, z.B. '1920x1080'.

    Steht im Kopf der Ausgabe, weil dieselbe Messung einmal bei voller
    und einmal bei halber Aufloesung gebraucht wird - und zwei Dateien
    ohne diese Angabe waeren nicht auseinanderzuhalten."""
    try:
        with open("/sys/class/graphics/fb0/virtual_size") as f:
            return f.read().strip().replace(",", "x")
    except OSError:
        return "?"


def frontend_laeuft():
    try:
        with open("/tmp/frontend.lock") as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return pid
    except Exception:                                    # noqa: BLE001
        return None


def messen(pid, dauer, hz, sag):
    """Einen Abschnitt lang messen.

    Rueckgabe: (Aufwachmomente, verbrauchte Ticks, hoechste Last,
    Konsolenwechsel, Liste der Zeitpunkte)."""
    t_start = time.monotonic()
    letzte = cpu_ticks(pid)
    letzte_zeit = t_start
    start_ticks = letzte
    if letzte is None:
        return None
    wach = 0
    zeitpunkte = []
    last_max = 0.0
    im_wachen = False
    konsole = aktive_konsole()
    wechsel = []
    naechste_meldung = 5.0

    while True:
        time.sleep(TAKT)
        jetzt = time.monotonic()
        vergangen = jetzt - t_start
        if vergangen >= dauer:
            break
        if vergangen >= naechste_meldung:
            sag("   ... noch %.0f s" % (dauer - vergangen))
            naechste_meldung += 5.0
        ticks = cpu_ticks(pid)
        if ticks is None:
            return None
        spanne = jetzt - letzte_zeit
        if spanne <= 0:
            continue
        last = (ticks - letzte) / float(hz) / spanne * 100.0
        letzte, letzte_zeit = ticks, jetzt
        last_max = max(last_max, last)
        k = aktive_konsole()
        if k != konsole:
            wechsel.append((vergangen, konsole, k))
            konsole = k
        if last >= SCHWELLE:
            if not im_wachen:
                wach += 1
                zeitpunkte.append(vergangen)
                im_wachen = True
        else:
            im_wachen = False

    ende_ticks = cpu_ticks(pid)
    verbraucht = (ende_ticks - start_ticks) if ende_ticks is not None else 0
    return wach, verbraucht, last_max, wechsel, zeitpunkte


def main():
    zeilen = []

    def sag(t=""):
        zeilen.append(t)
        try:
            print(t)
            sys.stdout.flush()
        except OSError:
            pass

    hz = _hz()
    sag("=" * 62)
    sag("Dragend - Messung zum Zucken")
    sag("=" * 62)
    sag("Zeit       : %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    sag("System     : %s" % " ".join(os.uname()))
    sag("Anzeige    : %s     <- BEIM VERGLEICHEN HIERAUF ACHTEN"
        % aufloesung())
    fe = frontend_laeuft()
    sag("Frontend   : %s" % ("laeuft (PID %d)" % fe if fe else
                             "LAEUFT NICHT - bitte starten, sonst misst "
                             "diese Messung nichts"))
    pid = mister_pid()
    if pid is None:
        sag("MiSTer     : NICHT GEFUNDEN - ohne den Prozess geht es nicht")
        sag("")
        sag("Laeuft der MiSTer-Hauptprozess? 'ps | grep -i mister' zeigt es.")
        return 1
    sag("MiSTer     : PID %d" % pid)
    sag("Konsole    : %s" % aktive_konsole())
    sag("Aufloesung : %d CPU-Ticks je Sekunde, ein Tick = %.0f ms"
        % (hz, 1000.0 / hz))
    sag("Schwelle   : %.0f %% Last = 'MiSTer zeichnet'" % SCHWELLE)

    ergebnisse = []
    for name, dauer, hinweis in ABSCHNITTE:
        sag("")
        sag("-" * 62)
        sag("ABSCHNITT %s - %.0f Sekunden" % (name, dauer))
        sag("-" * 62)
        sag(hinweis)
        # Drei Sekunden Vorlauf, damit die Haende rechtzeitig weg bzw.
        # am Pad sind - sonst misst der Anfang etwas anderes als der Rest.
        for i in (3, 2, 1):
            sag("   %d ..." % i)
            time.sleep(1.0)
        sag("   LOS")
        r = messen(pid, dauer, hz, sag)
        if r is None:
            sag("MiSTer-Prozess verschwunden - Abbruch.")
            return 1
        wach, ticks, last_max, wechsel, zeitpunkte = r
        ergebnisse.append((name, dauer, wach, ticks, last_max, wechsel,
                           zeitpunkte))
        sag("   fertig: %d Aufwachmomente, %d Ticks (%.0f ms CPU-Zeit)"
            % (wach, ticks, ticks * 1000.0 / hz))

    sag("")
    sag("=" * 62)
    sag("ERGEBNIS")
    sag("=" * 62)
    sag("")
    sag("   %-10s %8s %10s %10s %8s" %
        ("Abschnitt", "Dauer", "Aufwachen", "je Minute", "CPU-Zeit"))
    for name, dauer, wach, ticks, _lm, _w, _z in ergebnisse:
        sag("   %-10s %6.0f s %10d %10.1f %7.0f ms"
            % (name, dauer, wach, wach / dauer * 60.0, ticks * 1000.0 / hz))
    sag("")
    for name, dauer, wach, ticks, last_max, wechsel, zeitpunkte in ergebnisse:
        sag("   %s: hoechste Last %.0f %%, CPU-Anteil %.2f %%"
            % (name, last_max, ticks * 1000.0 / hz / (dauer * 10)))
        if wechsel:
            sag("      Konsolenwechsel: %d" % len(wechsel))
            for t, a, b in wechsel[:5]:
                sag("         %6.2f s  %s -> %s" % (t, a, b))
        if zeitpunkte:
            sag("      Zeitpunkte: %s%s"
                % (" ".join("%.1f" % t for t in zeitpunkte[:14]),
                   " ..." if len(zeitpunkte) > 14 else ""))
        sag("")

    sag("-" * 62)
    sag("WIE DAS ZU LESEN IST")
    sag("-" * 62)
    ruhe = ergebnisse[0]
    scroll = ergebnisse[1]
    r_rate = ruhe[2] / ruhe[1] * 60.0
    s_rate = scroll[2] / scroll[1] * 60.0
    sag("Ruhe     %.1f Aufwachmomente je Minute" % r_rate)
    sag("Scrollen %.1f Aufwachmomente je Minute" % s_rate)
    sag("")
    if r_rate <= 0.5 and s_rate >= 5.0:
        sag("MiSTer schlaeft im Leerlauf und wacht beim Scrollen auf.")
        sag("Das heisst: die Eingabe erreicht ihn. Der naechste Schritt")
        sag("ist dann, den Weg dorthin zu finden - ein Eingabegeraet,")
        sag("das nicht exklusiv gegriffen ist, waere der erste Verdacht.")
    elif s_rate <= r_rate * 1.5:
        sag("Er wacht im Leerlauf genauso oft auf wie beim Scrollen.")
        sag("Dann ist das sein normaler Haushalt und hat mit der")
        sag("Eingabe nichts zu tun - und auch nicht mit dem Zucken.")
        sag("Dann liegt es an der Anzeige-Ebene, unterhalb von uns.")
    else:
        sag("Beim Scrollen wacht er oefter auf als im Leerlauf, aber")
        sag("nicht ausschliesslich. Beides spielt hinein - die Zahlen")
        sag("oben sagen, in welchem Verhaeltnis.")
    sag("")
    sag("FEHLT NOCH: derselbe Lauf bei der ANDEREN Aufloesung.")
    sag("Diese Messung lief bei %s." % aufloesung())
    sag("Sind die Zahlen dort gleich, obwohl es nicht zuckt, dann sind")
    sag("die Aufwachmomente nicht die Ursache.")
    sag("=" * 62)

    try:
        with open(AUSGABE, "w") as f:
            f.write("\n".join(zeilen) + "\n")
        sag("")
        sag("Auch gespeichert in: %s" % AUSGABE)
    except OSError as e:
        sag("(konnte %s nicht schreiben: %s)" % (AUSGABE, e))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("")
        print("Abgebrochen.")
        sys.exit(1)
