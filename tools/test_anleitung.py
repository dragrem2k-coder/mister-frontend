#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Spielanleitung zum markierten Eintrag (Build 263).

NUTZERWUNSCH: "waere es ja schoen, wenn man im Frontend durch die
Spiele scrollt und per Tastendruck sich die Anleitung dazu ansehen
koennte."

WAS VOR DEM BAUEN AUF DEM GERAET GEPRUEFT WURDE - und warum das hier
oben steht: an dieser Stelle haette man sich dreimal vertun koennen,
und jedes Mal haette es einen ganzen Build gekostet.

  1. GIBT ES EINEN BETRACHTER? Ja: /media/fat/linux/pdfviewer ist ein
     jfbview 0.6.1 ("jfbview [OPTIONS] FILE"), daneben liegt glow fuer
     Markdown. Beide kommen mit update_all.
  2. LAEUFT ER AUF DIESEM KERNEL? Ja - von Hand gestartet, das Bild
     kam, und die Shell kehrte erst nach "q" zurueck. (Dass das Bild
     nach einer Sekunde verschwand, war unser eigenes Frontend, das
     darueber zeichnete - genau dagegen gibt es _auf_konsole().)
  3. WO LIEGEN DIE DATEIEN? Nicht im Core-Ordner, sondern in einem
     UNTERORDNER:
         /media/fat/docs/SMS/SMS Manuals/Ace of Aces.pdf
     206 Stueck, und neben den ROMs liegt nichts. Haette ich flach
     nachgesehen statt zu suchen, haette das Frontend bei jedem Spiel
     "keine Anleitung" gesagt.

Geprueft wird hier an einem ECHTEN Verzeichnisbaum, der genau so
gebaut ist wie der des Nutzers - samt Artwork-Ordner daneben, denn der
ist der Grund fuer die wichtigste Zusage dieses Moduls.

Ausfuehren:
    python3 tools/test_anleitung.py
"""
import io
import os
import shutil
import sys
import tempfile

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
_FRONTEND_DIR = os.path.dirname(
    os.environ.get("FRONTEND_PY",
                   os.path.join(_REPO, "frontend", "frontend.py")))
sys.path.insert(0, _FRONTEND_DIR)

import fe.anleitung as A                                 # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


TMP = tempfile.mkdtemp(prefix="anleitung_")
A.DOCS_BASE = os.path.join(TMP, "docs")


def datei(*teile):
    pfad = os.path.join(A.DOCS_BASE, *teile)
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w") as f:
        f.write("x")
    return pfad


# Genau der Aufbau des Nutzers: Anleitungen in einem Unterordner,
# Artwork daneben.
SMS_ACE = datei("SMS", "SMS Manuals", "Ace of Aces.pdf")
SMS_ACTION = datei("SMS", "SMS Manuals", "Action Fighter.pdf")
datei("SMS", "Artwork", "Ace of Aces (Europe).jpg")
datei("SMS", "Artwork", "gameinfo.tsv")
SMS_README = datei("SMS", "README.md")
SNES_TXT = datei("SNES", "Manuals", "Super Mario World.txt")
TIEF = datei("SNES", "a", "b", "c", "d", "Zu tief.pdf")

# Betrachter-Attrappen, damit der Test nicht davon abhaengt, was auf
# DIESEM Rechner installiert ist.
A.PDF_BETRACHTER = os.path.join(TMP, "pdfviewer")
A.TEXT_BETRACHTER = os.path.join(TMP, "glow")
for prog in (A.PDF_BETRACHTER, A.TEXT_BETRACHTER):
    with open(prog, "w") as f:
        f.write("#!/bin/sh\n")

try:
    # -----------------------------------------------------------------
    print("Test 1: gefunden wird im UNTERORDNER")
    # -----------------------------------------------------------------
    check("die Anleitung zum exakten Namen",
          A.anleitung_finden("SMS", "Ace of Aces") == SMS_ACE,
          str(A.anleitung_finden("SMS", "Ace of Aces")))
    check("UND zur ROM mit Regionsangabe",
          A.anleitung_finden("SMS", "Ace of Aces (Europe)") == SMS_ACE,
          "die Anleitung heisst 'Ace of Aces.pdf', die ROM "
          "'Ace of Aces (Europe).sms' - ohne den unscharfen Vergleich "
          "faende man auf einer echten Karte fast nichts")
    check("ein zweites Spiel ebenso",
          A.anleitung_finden("SMS", "Action Fighter (USA, Europe)")
          == SMS_ACTION)
    check("zu einem Spiel ohne Anleitung kommt nichts",
          A.anleitung_finden("SMS", "Alex Kidd in Miracle World") is None)
    check("auch eine Textdatei zaehlt",
          A.anleitung_finden("SNES", "Super Mario World (USA)")
          == SNES_TXT)

    # -----------------------------------------------------------------
    print()
    print("Test 2: die Core-README ist KEINE Spielanleitung")
    # -----------------------------------------------------------------
    # In jedem Core-Ordner liegt eine README.md (bei SNES ist es die
    # Core-Beschreibung von srg320). Wuerde sie als Rueckfall gelten,
    # bekaeme JEDES Spiel eine "Anleitung" - und zwar die falsche.
    check("sie wird keinem Spiel untergeschoben",
          A.anleitung_finden("SMS", "Irgendein Spiel") is None,
          "es gibt keinen Rueckfall auf 'irgendetwas im Ordner'")
    check("unter ihrem eigenen Namen ist sie trotzdem da",
          A.anleitung_finden("SMS", "README") == SMS_README,
          "gesucht wird nach dem NAMEN, nicht nach dem Ordner")

    # -----------------------------------------------------------------
    print()
    print("Test 3: der Artwork-Ordner wird nicht betreten")
    # -----------------------------------------------------------------
    # DIE WICHTIGSTE ZUSAGE. Dort liegen bei einer gepflegten Sammlung
    # Tausende Dateien; sie bei jeder Suche mitzulesen waere genau die
    # Sorte Fehler, die in v1.32 den rekursiven Fingerabdruck gekostet
    # hat (jeder Start dauerte dadurch Minuten).
    A.vergessen()
    gelesen = []
    _echt_walk = A.os.walk

    def _zaehl_walk(pfad, *a, **k):
        for ordner, unter, dateien in _echt_walk(pfad, *a, **k):
            gelesen.append(ordner)
            yield ordner, unter, dateien

    A.os.walk = _zaehl_walk
    try:
        A.anleitung_finden("SMS", "Ace of Aces")
    finally:
        A.os.walk = _echt_walk
    check("Artwork taucht in den gelesenen Ordnern NICHT auf",
          not any(os.path.basename(o).lower() == "artwork" for o in gelesen),
          str([os.path.basename(o) for o in gelesen]))
    check("der Anleitungs-Ordner schon",
          any(os.path.basename(o) == "SMS Manuals" for o in gelesen))

    # -----------------------------------------------------------------
    print()
    print("Test 4: gesucht wird EINMAL je System")
    # -----------------------------------------------------------------
    laeufe = []
    A.os.walk = lambda p, *a, **k: (laeufe.append(p), _echt_walk(p, *a, **k))[1]
    try:
        for _ in range(5):
            A.anleitung_finden("SMS", "Ace of Aces")
            A.anleitung_finden("SMS", "Action Fighter")
    finally:
        A.os.walk = _echt_walk
    check("zehn Abfragen kosten KEINEN weiteren Durchlauf",
          len(laeufe) == 0, "%d Durchlaeufe - der Stand war gemerkt"
          % len(laeufe))
    A.vergessen("SMS")
    A.os.walk = lambda p, *a, **k: (laeufe.append(p), _echt_walk(p, *a, **k))[1]
    try:
        A.anleitung_finden("SMS", "Ace of Aces")
    finally:
        A.os.walk = _echt_walk
    check("nach dem Vergessen wird wieder gesucht", len(laeufe) == 1,
          "%d" % len(laeufe))

    # -----------------------------------------------------------------
    print()
    print("Test 5: die Grenzen halten")
    # -----------------------------------------------------------------
    check("zu tief liegende Dateien werden nicht gefunden",
          A.anleitung_finden("SNES", "Zu tief") is None,
          "MAX_TIEFE = %d - wer sein Archiv dorthin legt, soll das "
          "Frontend nicht aufhalten" % A.MAX_TIEFE)
    check("es gibt eine Obergrenze fuer die Anzahl",
          A.MAX_DATEIEN > 0 and "MAX_DATEIEN" in io.open(
              os.path.join(_FRONTEND_DIR, "fe", "anleitung.py"),
              encoding="utf-8").read())

    # -----------------------------------------------------------------
    print()
    print("Test 6: der Befehl, der den Betrachter startet")
    # -----------------------------------------------------------------
    b = A.befehl(SMS_ACE)
    check("fuer ein PDF kommt der PDF-Betrachter",
          b and b[0] == A.PDF_BETRACHTER, str(b))
    check("mit --zoom_to_width", b and "--zoom_to_width" in b,
          "eine Anleitungsseite ist hochkant, der Bildschirm quer - "
          "ohne das sieht man die obere linke Ecke")
    check("mit begrenztem Seitenspeicher",
          b and "--cache_size=1" in b,
          "Build 267: 'nach ein paar Seiten haengt sich das Frontend "
          "auf' - das Einzige, was je Seite WAECHST, ist der "
          "Seitenspeicher; jfbviews eigene Hilfe empfiehlt genau das "
          "fuer Maschinen mit wenig RAM")
    check("und die Datei als letztes Argument", b and b[-1] == SMS_ACE)
    check("fuer eine Textdatei kommt glow",
          A.befehl(SNES_TXT)[0] == A.TEXT_BETRACHTER)

    fehlt = A.PDF_BETRACHTER
    A.PDF_BETRACHTER = os.path.join(TMP, "gibtsnicht")
    check("ohne installierten Betrachter gibt es keinen Befehl",
          A.befehl(SMS_ACE) is None,
          "sonst startet das Frontend etwas, das es nicht gibt")
    check("und hat_anleitung() sagt NEIN",
          A.hat_anleitung("SMS", "Ace of Aces") is False,
          "der Menuepunkt haengt an BEIDEM - Datei da UND Betrachter "
          "da; ein toter Eintrag ist schlimmer als keiner")
    A.PDF_BETRACHTER = fehlt
    check("mit Betrachter sagt sie JA",
          A.hat_anleitung("SMS", "Ace of Aces") is True)

    # -----------------------------------------------------------------
    print()
    print("Test 7: in /media/fat/docs wird NICHTS geschrieben")
    # -----------------------------------------------------------------
    _q = io.open(os.path.join(_FRONTEND_DIR, "fe", "anleitung.py"),
                 encoding="utf-8").read()
    for verboten in ("open(", "os.remove", "os.rename", "os.makedirs",
                     "shutil."):
        check("kein %s in fe/anleitung.py" % verboten.rstrip("(."),
              verboten not in _q,
              "der Ordner gehoert uns nicht - dieselbe Linie wie bei "
              "den Covern seit Build 115")

    # -----------------------------------------------------------------
    print()
    print("Test 8: die Anbindung im Frontend")
    # -----------------------------------------------------------------
    _fe = io.open(os.path.join(_FRONTEND_DIR, "frontend.py"),
                  encoding="utf-8").read()
    _az = _fe[_fe.index("    def anleitung_zeigen(self):"):]
    _az = _az[:_az.index("\n    def ", 10)]
    check("angezeigt wird ueber _auf_konsole()",
          "self._auf_konsole(" in _az,
          "ohne den Konsolenwechsel zeichnet das Frontend nach einer "
          "Sekunde darueber - genau das hat der Nutzer gesehen")
    check("und NICHT mit einem eigenen Zeichenweg",
          "self.fb." not in _az and "fb.text(" not in _az,
          "ein eigener PDF-Zeichenweg waere ein zweiter neben einem, "
          "der nachweislich funktioniert")
    check("ohne 'Taste druecken' hinterher",
          "read -rsn1" not in _az,
          "der Betrachter wartet selbst auf 'q'")
    _ae = _fe[_fe.index("    def _anleitung_zum_eintrag(self, item):"):]
    _ae = _ae[:_ae.index("\n    def ", 10)]
    check("der Systemkey kommt vom EINTRAG",
          "self._item_syskey(" in _ae,
          "in 'Zuletzt gespielt' und den Sammlungen sind Systeme "
          "gemischt - genau dieser Fehler hat in Build 261 die Cover "
          "im Overlay gekostet")
    check("und ein Ordner bekommt nie eine Anleitung",
          'item[1] != "game"' in _ae)
    check("der Betrachter darf nicht ewig haengen",
          "grenze=self.ANLEITUNG_MAX_SEK" in _az,
          "das Protokoll endete mitten im Aufruf - das Frontend war "
          "nicht abgestuerzt, es wartete ohne Ende")
    _wa = _fe[_fe.index("    def _warten_auf(self, proc, grenze"):]
    _wa = _wa[:_wa.index("\n    def ", 10)]
    check("ohne Grenze wird weiterhin unbegrenzt gewartet",
          "if not grenze or grenze <= 0:" in _wa and "proc.wait()" in _wa,
          "ein Skript SOLL zu Ende laufen duerfen")
    check("erst freundlich, dann bestimmt",
          _wa.index("proc.terminate()") < _wa.index("proc.kill()"))
    check("nach einem Neueinlesen wird der Stand verworfen",
          "ANLEITUNG.vergessen()" in _fe,
          "wer Spiele nachlegt, legt oft auch Anleitungen dazu")
    check("es gibt genau EINEN Konsolenweg",
          _fe.count("def _auf_konsole(") == 1
          and _fe.count("self._auf_konsole(") == 2,
          "run_script() und die Anleitung - zwei Aufrufer, eine "
          "Stelle")
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
