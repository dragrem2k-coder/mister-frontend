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
    check("ohne Grenze und ohne Puls wird unbegrenzt gewartet",
          "and puls is None:" in _wa and "return proc.wait()" in _wa,
          "ein Skript SOLL zu Ende laufen duerfen - geprueft wird das "
          "mit einem echten Prozess in tools/test_konsole_nachfassen.py")
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

    # -----------------------------------------------------------------
    print()
    print("Test 9: eine EIGENE Konsole fuer den Betrachter (Build 268)")
    # -----------------------------------------------------------------
    # NUTZERMELDUNG mit Build 267 drauf: "wenn ich dann durchscrolle
    # durch die Anleitung, reagiert nach ein paar Sekunden nicht mehr,
    # wirkt wie eingefroren."
    #
    # DIE MESSWERTE VOM GERAET HABEN DIE URSACHE AUS 267 WIDERLEGT:
    # free -m zeigt 208 MB verfuegbar, dmesg endet bei Sekunde 174 -
    # kein OOM-Killer, kein Treiberereignis. Es ist also kein
    # Speichermangel.
    #
    # WAS BLEIBT: auf tty1 sitzt ein Login-Prozess (belegt seit Build
    # 150, steht in back_to_frontend() woertlich). Build 266 hat ihn
    # unsichtbar gemacht, aber nicht stumm - er LIEST weiter von
    # derselben Konsole wie der Betrachter. Zwei Leser teilen sich die
    # Tasten; der Betrachter bekommt nur noch einen Teil davon und
    # steht.
    _ak = _fe[_fe.index("    def _auf_konsole(self, wrapped, raw, name="):]
    _ak = _ak[:_ak.index("\n    def ", 10)]
    check("die Anleitung bekommt eine eigene Konsole",
          "eigene_konsole=True" in _az)
    check("ein Skript dagegen NICHT",
          "eigene_konsole" not in _fe[_fe.index("    def run_script(self, path"):]
          [:_fe[_fe.index("    def run_script(self, path"):].index("\n    def ", 10)],
          "dort ist der Login-Prozess kein Problem, und die Ausgabe "
          "gehoert dorthin, wo sie immer war")
    check("gewechselt wird mit VT_ACTIVATE", "self.VT_ACTIVATE" in _fe)
    check("und VOR dem eingespeisten F9",
          _ak.index("self._konsole_oeffnen(")
          < _ak.index("self.enter_console_mode()"),
          "jedes eingespeiste F9 weckt den Login-Prozess - aber nur "
          "auf der Konsole, die vorne ist")
    _ko = _fe[_fe.index("    def _konsole_oeffnen(self, eigene):"):]
    _ko = _ko[:_ko.index("\n    def ", 10)]
    check("jeder Fehlschlag endet auf tty1",
          _ko.count("/dev/tty1") >= 1 and _ko.count("except OSError") >= 3,
          "eine Anleitung, die nicht aufgeht, waere schlimmer als ein "
          "Login-Gruss")
    check("zurueckgeschaltet wird im finally",
          _ak.index("finally:") < _ak.index("self._zurueck_auf_tty1("),
          "eine Konsole, auf der niemand mehr einloggen kann, waere "
          "schlimmer als das Problem")
    check("und es gibt einen Notausgang",
          "EIGENE_KONSOLE_AUS_FLAG" in _fe and "anleitung_tty1" in _fe,
          "dieselbe Linie wie beim Grafikmodus und bei der "
          "Konsolen-Mechanik")
    check("vor dem Start wird die Warteschlange geleert",
          "termios.TCIFLUSH" in _ak,
          "sonst liest der Betrachter das eben eingespeiste F9 als "
          "erste Taste")

    # -----------------------------------------------------------------
    print()
    print("Test 10: die Hand am Pad (Build 268)")
    # -----------------------------------------------------------------
    # NUTZERMELDUNG: "ich kann erst mit dem Joypad blaettern, wenn ich
    # einmal auf der Tastatur die Leertaste gedrueckt habe."
    #
    # WARUM: das Pad wird vom Betrachter gar nicht gelesen. MiSTers
    # eigene Dokumentation zum Betrachter (PDFViewer_MiSTer,
    # "JOYSTICK") zeigt, dass MiSTer die Knoepfe in TASTEN uebersetzt
    # - "btn1 - enter", "btn2 - escape", "L - pageup", "R - pagedn" -
    # und woertlich: "This will allow it to work well with the
    # joystick emulation." Wann MiSTer das anschaltet, haben wir nicht
    # in der Hand. Also machen wir es selbst.
    sys.path.insert(0, _HIER)
    import fe.input as FI                                 # noqa: E402

    T = None
    for _zeile in _fe.splitlines():
        if _zeile.strip().startswith("ANLEITUNG_TASTEN"):
            T = True
    check("es gibt eine Tastentabelle", T is True)
    _at = _fe[_fe.index("    ANLEITUNG_TASTEN = {"):]
    _at = _at[:_at.index("}") + 1]
    check("links/rechts blaettert (Bild-auf/Bild-ab)",
          "\"left\": KEY_PAGEUP" in _at and "\"right\": KEY_PAGEDOWN" in _at,
          "genau MiSTers eigene Zuordnung fuer L und R - und am Pad "
          "liefern die Schultertasten diese beiden Aktionen")
    check("hoch/runter scrollt",
          "\"up\": KEY_UP" in _at and "\"down\": KEY_DOWN" in _at)
    check("A blaettert vor (Enter)", "\"ok\": KEY_ENTER" in _at,
          "'btn1 - enter -- next page' - diese Taste hat MiSTer dem "
          "Betrachter eigens dafuer beigebracht")
    check("die Codes sind die echten Linux-Codes",
          (FI.KEY_PAGEUP, FI.KEY_PAGEDOWN, FI.KEY_ENTER, FI.KEY_ESC)
          == (104, 109, 28, 1),
          "%s" % ((FI.KEY_PAGEUP, FI.KEY_PAGEDOWN, FI.KEY_ENTER,
                   FI.KEY_ESC),))
    _pu = _fe[_fe.index("    def _anleitung_pult(self, proc):"):]
    _pu = _pu[:_pu.index("\n    def ", 10)]
    check("gelesen wird ohne zu warten",
          "read_action(timeout=0)" in _pu,
          "sonst stuende der Betrachter bei jedem Blick still")
    check("B/Esc schickt Escape an den Betrachter",
          "self.inp.inject(KEY_ESC" in _pu and "ANLEITUNG_RAUS" in _pu,
          "'btn2 - escape -- quit'")
    check("und wenn der nicht aufhoert, beenden WIR ihn",
          "ANLEITUNG_RAUS_FRIST" in _pu and "return True" in _pu,
          "das ist der Teil, der garantiert funktioniert - niemand "
          "muss mehr das Geraet neu starten")

    # Der Grab mit Ausnahme - an echten Objekten, nicht an einer
    # Textstelle. Die Ausnahme ist der Kern: in ein GEGRIFFENES
    # Geraet eingespeiste Tasten bekommt nur der Greifer, also wir
    # selbst - der Betrachter saehe nichts.
    class _FakeDev(object):
        def __init__(self, path, name, is_kbd):
            self.path, self.name, self.is_kbd = path, name, is_kbd
            self.grabbed = False

        def grab(self, on):
            self.grabbed = on

    mgr = FI.InputManager.__new__(FI.InputManager)
    mgr.want_grab = False
    mgr.grab_ausnahme = None
    tast = _FakeDev("/dev/input/event0", "Logitech USB Keyboard", True)
    pad = _FakeDev("/dev/input/event4", "Microsoft X-Box 360 pad", False)
    mgr.devices = {tast.path: tast, pad.path: pad}
    check("das Einspeise-Ziel ist die Tastatur",
          mgr.inject_ziel() is tast, mgr.inject_ziel().name)
    mgr.grab(True, ausser=tast.path)
    check("das Pad gehoert uns", pad.grabbed is True)
    check("die Tastatur bleibt frei", tast.grabbed is False,
          "sonst bekaeme NUR das Frontend die eingespeiste Taste")
    check("und die Ausnahme ist gemerkt",
          mgr.grab_ausnahme == tast.path,
          "rescan() greift neu aufgetauchte Geraete nach want_grab - "
          "ohne das Merken waere die Ausnahme beim naechsten "
          "Hotplug-Blick weg")
    mgr.grab(True)
    check("ein normaler Grab nimmt alles und loescht die Ausnahme",
          tast.grabbed and pad.grabbed and mgr.grab_ausnahme is None)
    check("die Suche nach dem Ziel steht an genau EINER Stelle",
          io.open(os.path.join(_FRONTEND_DIR, "fe", "input.py"),
                  encoding="utf-8").read().count(
                      '"keyboard" in d.name.lower()') == 1,
          "zwei Fassungen davon waeren der Nachbau aus Build 260")

    # -----------------------------------------------------------------
    print()
    print("Test 11: ein Blaettern kostet keine Zehntelsekunde (Build 269)")
    # -----------------------------------------------------------------
    # NUTZER-RUECKMELDUNG zu Build 268: "l und r Taste funktioniert
    # doch, aber alles sehr langsam unter dem neuen Kernel."
    #
    # GEZAEHLT, NICHT GESTOPPT - und zwar aus einem Grund, der in
    # diesem Projekt schon dreimal wehgetan hat: der Pruefstand friert
    # time.monotonic() ein (siehe tools/_harness.py), eine Stoppuhr
    # wuerde hier also das Gegenteil dessen messen, was sie behauptet.
    # Gezaehlt wird deshalb, WIE LANGE inject() zu schlafen VERLANGT -
    # und das ist die Zahl, um die es geht.
    geschlafen = []
    _echt_sleep = FI.time.sleep
    FI.time.sleep = lambda s: geschlafen.append(s)
    _r, _w = os.pipe()
    try:
        class _SchreibDev(_FakeDev):
            def __init__(self):
                _FakeDev.__init__(self, "/dev/input/event0",
                                  "Logitech USB Keyboard", True)
                self.fd = _w

        mgr.devices = {"/dev/input/event0": _SchreibDev()}
        mgr.inject(FI.KEY_F9)
        f9 = sum(geschlafen)
        del geschlafen[:]
        mgr.inject(FI.KEY_PAGEDOWN, pause=0.004)
        blaettern = sum(geschlafen)
    finally:
        FI.time.sleep = _echt_sleep
        os.close(_r)
        os.close(_w)
    check("F9 haelt die Taste weiter 0,05 s je Richtung",
          abs(f9 - 0.1) < 1e-9, "%.3f s" % f9,)
    check("ein Blaettern dagegen nur Millisekunden",
          abs(blaettern - 0.008) < 1e-9, "%.3f s statt %.3f s - "
          "gespart %.0f ms je Seite" % (blaettern, f9,
                                        (f9 - blaettern) * 1000))
    check("und die Vorgabe bleibt die alte",
          FI.InputManager.INJECT_PAUSE == 0.05,
          "F9 ist der Grund: MiSTers Main muss die Taste in seiner "
          "eigenen Abfrage SEHEN - das war die Jagd der Builds 146-152")
    _fe2 = io.open(os.path.join(_FRONTEND_DIR, "frontend.py"),
                   encoding="utf-8").read()
    check("die Anleitung speist mit der kurzen Pause ein",
          _fe2.count("pause=self.ANLEITUNG_TASTEN_PAUSE") == 2,
          "beide Stellen: die Blaettertaste und das Escape")
    # Jeder Einspeise-Aufruf im Frontend ist entweder die Anleitung
    # (kurze Pause) oder ein F9/F12 (alte Pause). Ein dritter Fall
    # waere eine Taste, deren Haltedauer niemand bedacht hat.
    _aufrufe = [z.strip() for z in _fe2.splitlines()
                if "self.inp.inject(" in z]
    check("jeder Einspeise-Aufruf ist einer der beiden Faelle",
          all(("pause=self.ANLEITUNG_TASTEN_PAUSE" in z
               or "inject(KEY_F9)" in z or "inject(KEY_F12)" in z)
              for z in _aufrufe) and len(_aufrufe) == 6,
          "%d Aufrufe: %s" % (len(_aufrufe), _aufrufe))
finally:
    shutil.rmtree(TMP, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
print("Build 278: liegt tty1 danach wirklich wieder vorne?")
sys.path.insert(0, _HIER)
import _harness as H                                      # noqa: E402
# ---------------------------------------------------------------------------
# NUTZERMELDUNG: "wenn das frontend länger läuft und ich beende es und
# gehe ins osd zurück und möchte dann aus dem osd ein script ausführen
# zum beispiel frontend_install.sh oder sonst eins passiert nichts mehr,
# mister muss ich dann einmal kalt neustarten."
#
# DIE DIAGNOSE WAR EINE ZEILE:
#
#     # cat /sys/class/tty/tty0/active
#     tty3
#
# tty3 ist UNSERE Anleitungs-Konsole (ANLEITUNG_VT). Sie lag noch
# vorne, waehrend das Frontend lief - der Rueckwechsel hatte also nicht
# gegriffen, und zwar OHNE eine einzige Fehlermeldung. MiSTers Scripts
# laufen auf tty1; liegt eine andere Konsole vorne, startet das Script
# zwar, aber niemand sieht und bedient es.
#
# LEHRE, und es ist dieselbe wie bei den eingespeisten F9/F12 (Build
# 169/184): ein ioctl, der nicht wirft, ist kein Beweis, dass etwas
# passiert ist. Angefordert ist nicht angekommen.
_fe3 = io.open(os.path.join(_FRONTEND_DIR, "frontend.py"),
               encoding="utf-8").read()

check("es gibt eine Stelle, die den Kernel FRAGT, welche VT vorne ist",
      "/sys/class/tty/tty0/active" in _fe3 and "def _aktive_vt" in _fe3,
      "vorher wurde nur angefordert und gehofft")
check("der Rueckweg sieht danach nach",
      "def _zurueck_auf_tty1" in _fe3
      and "aktiv = self._aktive_vt()" in
          _fe3.split("def _zurueck_auf_tty1")[1][:2500])
check("und hat einen ZWEITEN Weg, nicht denselben zweimal",
      '"/dev/tty0"' in _fe3 and "def _vt_erzwingen" in _fe3,
      "der erste Aufruf geht an den Griff der eigenen Konsole, der "
      "zweite an /dev/tty0 - ein Wiederholen auf demselben Griff "
      "haette nichts gebracht")
check("der AUSSTIEG stellt die Konsole zurueck",
      "_vt = self._aktive_vt()" in _fe3.split("def _beenden")[1][:3000],
      "das ist die letzte Stelle, an der wir es richtigstellen koennen "
      "- danach gehoert die Maschine MiSTer")
check("und zwar VOR dem F12",
      _fe3.split("def _beenden")[1].index("_vt = self._aktive_vt()")
      < _fe3.split("def _beenden")[1].index("_f12_bis_das_osd_kommt"),
      "nach dem F12 wird die Konsole nicht mehr angefasst (Build 166)")
check("misslingt es, steht es im Protokoll",
      "keine Scripts" in _fe3,
      "ein stilles Scheitern hat diesen Fehler vier Wochen "
      "unentdeckt gelassen")

# UND JETZT DAS VERHALTEN, nicht der Text.
_fe4 = H.make_frontend(page=0)
_tmpvt = tempfile.mkdtemp(prefix="vt_")
try:
    _datei = os.path.join(_tmpvt, "active")
    io.open(_datei, "w").write("tty3\n")
    _fe4.AKTIVE_VT_DATEI = _datei
    check("'tty3' wird als 3 gelesen", _fe4._aktive_vt() == 3)
    io.open(_datei, "w").write("tty1\n")
    check("'tty1' als 1", _fe4._aktive_vt() == 1)
    io.open(_datei, "w").write("\n")
    check("Unsinn ergibt None, keine Ausnahme",
          _fe4._aktive_vt() is None,
          "eine fehlende oder fremde Datei darf den Ausstieg nicht "
          "aufhalten")
    os.remove(_datei)
    check("eine fehlende Datei ebenfalls", _fe4._aktive_vt() is None)

    # Der Rueckweg: der ioctl auf eine gewoehnliche Datei scheitert
    # (ENOTTY) - genau der Fall "angefordert, nicht angekommen". Danach
    # MUSS der zweite Weg versucht werden.
    io.open(_datei, "w").write("tty3\n")
    _versuche = []
    _fe4._vt_erzwingen = lambda ziel=1: (_versuche.append(ziel) or True)
    _attrappe = io.open(os.path.join(_tmpvt, "nicht_tty"), "w+b")
    _fe4._zurueck_auf_tty1(_attrappe, 3)
    _attrappe.close()
    check("liegt danach nicht tty1 vorne, wird der zweite Weg gegangen",
          _versuche == [1], repr(_versuche))

    # Und wenn tty1 vorne liegt, passiert NICHTS weiter - kein
    # unnoetiger Konsolenwechsel auf einem gesunden Geraet.
    io.open(_datei, "w").write("tty1\n")
    _versuche[:] = []
    _attrappe = io.open(os.path.join(_tmpvt, "nicht_tty"), "w+b")
    _fe4._zurueck_auf_tty1(_attrappe, 3)
    _attrappe.close()
    check("liegt tty1 schon vorne, wird nichts erzwungen",
          _versuche == [], repr(_versuche))

    # Ohne eigene Konsole (vt=0) wird gar nicht gewechselt - das war
    # schon vorher so und bleibt.
    _versuche[:] = []
    _fe4._zurueck_auf_tty1(None, 0)
    check("ohne eigene Konsole bleibt alles unberuehrt", _versuche == [])
finally:
    shutil.rmtree(_tmpvt, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
print("Build 280: der Rueckweg darf nicht warten koennen")
# ---------------------------------------------------------------------------
# NUTZERMELDUNG ZU BUILD 278: "wenn ich jetzt die anleitung schliessen
# will reagiert nichts mehr! das ging vorher!" - und zwar "nachdem ich
# build 278 installiert hab".
#
# URSACHE: _vt_erzwingen() rief VT_WAITACTIVE. Der ioctl WARTET, bis
# die Konsole vorne liegt, und zwar unbegrenzt. Verweigert der Besitzer
# der alten Konsole den Wechsel - und ein Programm im Grafikmodus darf
# das -, kommt er nie zurueck. Das Frontend stand mitten im Aufraeumen.
#
# LEHRE: ein blockierender Aufruf im Aufraeumweg ist ein Haenger mit
# Anlauf. Build 247 hat dasselbe fuer den Zeichenweg gelernt.
_fe5 = io.open(os.path.join(_FRONTEND_DIR, "frontend.py"),
               encoding="utf-8").read()
_erzw = _fe5.split("def _vt_erzwingen")[1].split("\n    def ")[0]
# Geprueft wird die VERWENDUNG (self.VT_WAITACTIVE), nicht das Wort:
# die Begruendung im Docstring nennt es ausdruecklich, und ein Test,
# der am Wort haengt, verbietet die Erklaerung.
check("_vt_erzwingen() wartet NICHT per ioctl",
      "self.VT_WAITACTIVE" not in _erzw,
      "ein unbegrenzt wartender Aufruf im Aufraeumweg haelt das ganze "
      "Frontend an")
check("es wartet selbst, mit harter Grenze",
      "VT_WECHSEL_FRIST" in _erzw and "VT_WECHSEL_TAKT" in _erzw,
      "ein Wechsel, der nicht stattfindet, kostet dann eine Sekunde "
      "und eine Zeile im Protokoll - nicht das Geraet")

_fe6 = H.make_frontend(page=0)
_tmp2 = tempfile.mkdtemp(prefix="vt2_")
try:
    _d = os.path.join(_tmp2, "active")
    io.open(_d, "w").write("tty3\n")
    _fe6.AKTIVE_VT_DATEI = _d
    _fe6.VT_WECHSEL_FRIST = 0.15
    _fe6.VT_WECHSEL_TAKT = 0.01
    # NICHT die echte Konsole des Pruefrechners anfassen.
    _fe6.TTY0_PFAD = os.path.join(_tmp2, "kein_tty0")
    io.open(_fe6.TTY0_PFAD, "w").write("")
    # Der ioctl scheitert auf einer gewoehnlichen Datei (ENOTTY).
    # Das fuehrt zu False, und zwar SOFORT und ohne Warten.
    import time as _t280
    _t0 = _t280.perf_counter()
    _ok = _fe6._vt_erzwingen(1)
    _dauer = _t280.perf_counter() - _t0
    check("ein misslungener Wechsel kehrt zurueck, statt zu haengen",
          _ok is False and _dauer < 2.0,
          "%.2f s" % _dauer)
    # Und wenn das Ziel schon vorne liegt, passiert nichts und es
    # dauert nichts.
    io.open(_d, "w").write("tty1\n")
    _t0 = _t280.perf_counter()
    check("liegt das Ziel schon vorne, ist es sofort True",
          _fe6._vt_erzwingen(1) is True
          and (_t280.perf_counter() - _t0) < 0.5)
finally:
    shutil.rmtree(_tmp2, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
print("Build 286: erst loslassen, dann umschalten")
# ---------------------------------------------------------------------------
# DAS PROTOKOLL DES NUTZERS HAT ES IN ZWEI ZEILEN ENTSCHIEDEN, und
# zwar UNMITTELBAR nach dem Schliessen der Anleitung - lange bevor
# MiSTer irgendetwas neu laedt:
#
#   09:01:45  VT: nach dem Rueckwechsel liegt tty3 vorne, nicht tty1
#   09:01:46  VT: tty1 liess sich NICHT nach vorne bringen
#
# MISTER IST UNSCHULDIG. Wir kommen von tty3 gar nicht mehr weg, und
# das ab dem ersten Augenblick. Vier Builds (278, 282, 285 und die
# Diagnose dazwischen) haben in die falsche Richtung gesehen, weil
# der einzige Beweis bis dahin aus dem AUSSTIEG kam - und dort steht
# MiSTers load_core direkt daneben. Die Zeile von 09:01 gab es erst,
# seit Build 285 auch den Rueckweg der Anleitung protokolliert.
#
# URSACHE: ein Programm, das selbst auf eine Konsole malt, uebernimmt
# den Konsolenwechsel per VT_SETMODE/VT_PROCESS - der Kernel fragt es
# dann vor jedem Wechsel um Erlaubnis. Genau das macht jfbview.
# Beendet wird er von uns, aber der Kernel setzt diese Betriebsart
# erst zurueck, wenn der LETZTE Dateizeiger auf die Konsole zugeht -
# und den hielten wir noch. Der Kernel fragte einen toten Prozess und
# bekam keine Antwort.
#
# LEHRE: wer eine fremde Betriebsart erbt, muss sie zuruecksetzen -
# und das geht nur, solange man den Griff noch hat.
_fe7 = io.open(os.path.join(_FRONTEND_DIR, "frontend.py"),
               encoding="utf-8").read()
_fin = _fe7.split("def _auf_konsole")[1].split("\n    def ")[0]
_fin = _fin[_fin.index("        finally:"):]

check("die Betriebsart der Konsole wird zurueckgestellt",
      "VT_SETMODE" in _fin and "VT_AUTO" in _fin,
      "VT_AUTO heisst: der Kernel schaltet selbst und fragt niemanden")
check("und zwar BEVOR der Dateizeiger zugeht",
      _fin.index("VT_SETMODE") < _fin.index("tty.close()"),
      "danach gibt es keinen Griff mehr, mit dem man es koennte")
check("umgeschaltet wird erst NACH dem Schliessen",
      _fin.index("tty.close()")
      < _fin.index("self._zurueck_auf_tty1"),
      "genau diese Reihenfolge war der Fehler - solange der "
      "Dateizeiger offen ist, haelt der Kernel die geerbte "
      "Betriebsart")
check("und ohne Dateizeiger, weil er weg ist",
      "self._zurueck_auf_tty1(None, vt)" in _fin)

# Und der Rueckweg muss damit umgehen koennen.
_zur = _fe7.split("def _zurueck_auf_tty1")[1].split("\n    def ")[0]
check("der Rueckweg kommt ohne Dateizeiger aus",
      "if not vt:" in _zur and "if tty is not None:" in _zur,
      "vorher stieg er bei tty=None sofort aus - dann waere nach dem "
      "Schliessen gar nichts mehr passiert")

_fe8 = H.make_frontend(page=0)
_tmp3 = tempfile.mkdtemp(prefix="vt3_")
try:
    _d3 = os.path.join(_tmp3, "active")
    io.open(_d3, "w").write("tty3\n")
    _fe8.AKTIVE_VT_DATEI = _d3
    _versuche3 = []
    _fe8._vt_erzwingen = lambda ziel=1: (_versuche3.append(ziel) or True)
    _fe8._anleitungs_vt_freigeben = lambda: _versuche3.append("frei")
    _fe8._zurueck_auf_tty1(None, 3)
    check("ohne Dateizeiger wird trotzdem umgeschaltet und freigegeben",
          _versuche3 == [1, "frei"], repr(_versuche3))
    _versuche3[:] = []
    _fe8._zurueck_auf_tty1(None, 0)
    check("ohne eigene Konsole weiterhin nichts", _versuche3 == [])
finally:
    shutil.rmtree(_tmp3, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
