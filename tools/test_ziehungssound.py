#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Ziehungssound und die Spannungsphase in Zufalls-Zock (Build 246).

Nutzerwunsch: "kann man bei zufalls zock wenn man spiele zieht noch ein
ziehungssound einbauen? der abgespielt wird bis die spiele erscheinen!"

WORAN DIESES FEATURE SCHEITERN KANN, und genau das steht hier:

  1. Der Sound laeuft WEITER, wenn die Spiele schon dastehen. Seine MP3
     ist 7,9 Sekunden lang, die Phase dauert eine bis fuenf - ohne das
     vorzeitige Beenden spielt er in den Auswahlbildschirm hinein.
  2. Der Sound wird ueberhaupt erst GESTARTET, nachdem schon
     abgebrochen wurde. Der Klang laeuft in einem eigenen Faden; bei
     warmem Zwischenspeicher ist die Phase regelmaessig vorbei, bevor
     mpg123 hochgefahren ist. Dann faengt der Ton an, wenn er aufhoeren
     sollte - und niemand haelt ihn mehr.
  3. Die Phase laedt die Cover NICHT, und dann wartet man zweimal:
     einmal die Spannung ab und danach noch das Laden.
  4. Die Einstellung 0 ("aus") kostet trotzdem Zeit oder spielt einen
     Klang - dann gibt es kein Zurueck zum Verhalten von vorher.
  5. Eine von Hand verstellte Datei blockiert den Bildschirm minutenlang.

Ausfuehren:
    python3 tools/test_ziehungssound.py
"""
import io
import os
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H                                        # noqa: E402

fm = H.fm
import fe.audio as AUDIO                                    # noqa: E402
import fe.settings as SET                                   # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


class _ProcAttrappe(object):
    """Verhaelt sich wie ein subprocess.Popen, ohne einen zu sein."""

    def __init__(self):
        self.beendet = False
        self.gewartet = False

    def poll(self):
        return 0 if self.beendet else None

    def terminate(self):
        self.beendet = True

    def wait(self):
        self.gewartet = True


# ---------------------------------------------------------------------------
print("Test 1: der Griff - abbrechen, auch VOR dem Start")
# ---------------------------------------------------------------------------
g = AUDIO.SoundGriff()
check("frisch ist er nicht abgebrochen", not g.abgebrochen())
p = _ProcAttrappe()
check("setzen() nimmt den Prozess an", g.setzen(p) is True)
check("und er laeuft noch", not p.beendet)
g.stoppen()
check("stoppen() beendet ihn", p.beendet)
check("und merkt sich den Abbruch", g.abgebrochen())
g.stoppen()
check("zweites stoppen() ist harmlos", True)

# DER FALL, DER DIESE KLASSE UEBERHAUPT RECHTFERTIGT: zuerst
# abgebrochen, danach erst gestartet.
g2 = AUDIO.SoundGriff()
g2.stoppen()
p2 = _ProcAttrappe()
check("nach dem Abbruch wird ein Prozess NICHT angenommen",
      g2.setzen(p2) is False,
      "sonst wartet der Faden auf einen Klang, den niemand mehr stoppt")
check("und der eben gestartete Prozess ist gleich beendet", p2.beendet,
      "bei warmen Covern ist die Phase vorbei, bevor mpg123 laeuft")

# ---------------------------------------------------------------------------
print()
print("Test 2: die Einstellung - Stufen, Standard, Unfug in der Datei")
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    SET.ZIEHUNG_SPANNUNG_FILE = os.path.join(tmp, "ziehung_spannung")
    check("ohne Datei kommt der Standard",
          SET.load_ziehung_spannung() == SET.ZIEHUNG_SPANNUNG_STD,
          str(SET.ZIEHUNG_SPANNUNG_STD))
    check("der Standard ist 2 s", SET.ZIEHUNG_SPANNUNG_STD == 2000)
    check("0 ist eine der Stufen", 0 in SET.ZIEHUNG_SPANNUNG_STUFEN,
          "sonst gibt es kein Zurueck zum Verhalten vor Build 246")
    SET.save_ziehung_spannung(3000)
    check("gespeichert und wieder gelesen",
          SET.load_ziehung_spannung() == 3000)
    gesehen = set()
    wert = SET.load_ziehung_spannung()
    for _ in range(len(SET.ZIEHUNG_SPANNUNG_STUFEN) + 1):
        wert = SET.cycle_ziehung_spannung()
        gesehen.add(wert)
    check("weiterschalten erreicht jede Stufe",
          gesehen == set(SET.ZIEHUNG_SPANNUNG_STUFEN),
          "%d von %d" % (len(gesehen), len(SET.ZIEHUNG_SPANNUNG_STUFEN)))
    with io.open(SET.ZIEHUNG_SPANNUNG_FILE, "w", encoding="utf-8") as fh:
        fh.write("600000")
    check("eine von Hand verstellte Datei wird nicht geglaubt",
          SET.load_ziehung_spannung() == SET.ZIEHUNG_SPANNUNG_STD,
          "zehn Minuten Spannung waere ein haengender Bildschirm")
    with io.open(SET.ZIEHUNG_SPANNUNG_FILE, "w", encoding="utf-8") as fh:
        fh.write("kein Zahlwert")
    check("und Unfug darin auch nicht",
          SET.load_ziehung_spannung() == SET.ZIEHUNG_SPANNUNG_STD)
    check("die oberste Stufe bleibt im Rahmen",
          max(SET.ZIEHUNG_SPANNUNG_STUFEN) <= 5000,
          "%d ms" % max(SET.ZIEHUNG_SPANNUNG_STUFEN))

# ---------------------------------------------------------------------------
print()
print("Test 3: die Phase selbst - Dauer, Laden, Sound, Abbruch")
# ---------------------------------------------------------------------------
# DIE UHR IM PRUEFSTAND STEHT STILL (_harness.NOW) - fuer diese Phase
# muss sie laufen, sonst wird die Dauer nie erreicht. Genau dieselbe
# Vorkehrung wie in test_bench.py.
#
# Und genau daran hat sich eine echte Luecke gezeigt: ohne Notbremse
# lief die Schleife endlos, als die Uhr stillstand. Im Frontend steht
# deshalb jetzt eine Obergrenze fuer die Zahl der Bilder.
_ECHTE_UHR = time.perf_counter
fm.time.monotonic = _ECHTE_UHR

H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
f.fb.flip = lambda *a, **k: None

PICKS = [("SNES", "Super Mario World", "", "", "/f/smw.sfc", 1.0),
         ("SNES", "Zelda", "", "", "/f/zelda.sfc", 1.0),
         ("SNES", "Metroid", "", "", "/f/metroid.sfc", 1.0)]
PLAYABLE = [("SNES", "Spiel %03d" % i, "", "", "/f/%d.sfc" % i, 1.0)
            for i in range(50)]


class _EingabeAttrappe(object):
    """read_action wie das Original - und das heisst: OHNE timeout
    BLOCKIEREND.

    GENAU DARAN IST BUILD 246 GESCHEITERT, und der Pruefstand hat es
    nicht gesehen, weil hier ein nicht-blockierendes Lambda stand. Im
    Betrieb wartet read_action() ohne timeout auf die naechste Aktion,
    egal wie lange (siehe dessen Docstring in fe/input.py) - die
    Ziehung hat deshalb EIN Bild gezeichnet und dann gestanden, bis
    jemand eine Taste drueckte.

    Diese Attrappe wirft, wenn sie ohne timeout gerufen wird. Damit
    kann derselbe Fehler nicht zurueckkommen, ohne dass ein Test rot
    wird."""

    def __init__(self, eingaben=None):
        self.eingaben = list(eingaben or [])
        self.ohne_timeout = 0
        self.aufrufe = 0

    def read_action(self, timeout=None):
        self.aufrufe += 1
        if timeout is None:
            self.ohne_timeout += 1
            raise AssertionError(
                "read_action() ohne timeout blockiert im Betrieb - "
                "genau der Fehler aus Build 246")
        wert = self.eingaben.pop(0) if self.eingaben else None
        if wert is None:
            # AUCH EIN "nichts gedrueckt" KOSTET ZEIT - read_action()
            # wartet dann bis zum timeout. Ohne diesen Schlaf liefe die
            # Testschleife in Nullzeit durch, und die Tastensperre
            # (ZIEHUNG_TASTENSPERRE) waere nie vorbei. Gekuerzt auf 20
            # ms, damit der Test nicht so lange dauert wie die Phase.
            time.sleep(min(timeout, 0.02))
        return wert


def _phase(dauer_ms, eingaben=None, sfx_an=True, spaet=False):
    """Die Phase einmal laufen lassen und protokollieren, was passiert.

    spaet=True legt die Eingaben erst NACH der Tastensperre vor -
    sonst werden sie verbraucht, aber nicht als Abbruch gewertet."""
    log = {"sound": [], "geladen": [], "griffe": []}
    att = _EingabeAttrappe(eingaben)
    log["eingabe"] = att
    f.inp = att

    def _sound(name, griff=None):
        log["sound"].append(name)
        log["griffe"].append(griff)

    echt_laden = f._wot_cover_sichern

    def _laden(picks, cache, cell_w, covers_h, s):
        log["geladen"].append(len(picks))
        for p in picks:
            cache[(p[0], os.path.splitext(os.path.basename(p[4]))[0])] = None

    f._play_ducked_sfx = _sound
    f._wot_cover_sichern = _laden
    import fe.settings as _S
    echt_load = fm.load_ziehung_spannung
    fm.load_ziehung_spannung = lambda: dauer_ms
    echt_sfx = fm.sfx_enabled_flag
    fm.sfx_enabled_flag = lambda: sfx_an
    cache = {}
    t0 = time.perf_counter()
    try:
        f._wot_ziehung_zeigen(f.fb, 100, 50, 1700, 3, 300, 60, 3, 90,
                              PLAYABLE, PICKS, cache, 400, 500)
    finally:
        f._wot_cover_sichern = echt_laden
        fm.load_ziehung_spannung = echt_load
        fm.sfx_enabled_flag = echt_sfx
    log["dauer"] = time.perf_counter() - t0
    log["cache"] = cache
    return log


# a) Aus: kein Warten, kein Sound - aber geladen wird trotzdem.
l = _phase(0)
check("aus: kein Sound", l["sound"] == [], str(l["sound"]))
check("aus: die Cover werden trotzdem geholt", l["geladen"] == [3],
      str(l["geladen"]))
check("aus: praktisch keine Wartezeit", l["dauer"] < 0.2,
      "%.3f s" % l["dauer"])

# b) An: Sound, Laden, und die Dauer wird eingehalten.
l = _phase(1000)
check("an: der Ziehungssound wird gestartet",
      l["sound"] == ["zufall_ziehung"], str(l["sound"]))
check("an: mit einem Griff zum Abbrechen",
      l["griffe"] and isinstance(l["griffe"][0], AUDIO.SoundGriff),
      "ohne Griff laeuft die 7,9-s-MP3 in den Auswahlbildschirm hinein")
check("an: der Griff ist am Ende gestoppt",
      l["griffe"][0].abgebrochen(),
      "genau das ist 'bis die Spiele erscheinen'")
check("an: die Cover werden WAEHREND der Phase geholt",
      l["geladen"] == [3], str(l["geladen"]))
check("an: die Dauer wird eingehalten", 0.9 <= l["dauer"] <= 1.6,
      "%.3f s" % l["dauer"])

# c) Laenger eingestellt heisst laenger gewartet.
l2 = _phase(2000)
check("zwei Sekunden dauern laenger als eine",
      l2["dauer"] > l["dauer"] + 0.5,
      "%.2f gegen %.2f s" % (l2["dauer"], l["dauer"]))

# d) Eine Taste ueberspringt - aber erst NACH der Tastensperre.
#
#    DIE SPERRE IST KEIN SCHOENHEITSFEHLER: man kommt auf diesen
#    Bildschirm, indem man OK drueckt, und dieselbe Taste ist beim
#    ersten Blick in die Eingabe noch da (Halte-Wiederholung). Ohne
#    Sperre beendet sie die Ziehung sofort wieder - genau das hat der
#    Nutzer als "die Titel laufen nicht ueber ein Rad" gemeldet.
l3 = _phase(5000, eingaben=[None] * 25 + ["ok"])
check("eine Taste bricht die Phase ab", l3["dauer"] < 3.0,
      "%.3f s statt 5 s" % l3["dauer"])
check("aber nicht sofort - die Tastensperre haelt",
      l3["dauer"] >= fm.ZIEHUNG_TASTENSPERRE,
      "%.3f s, Sperre %.2f s" % (l3["dauer"], fm.ZIEHUNG_TASTENSPERRE))
check("und der Sound ist danach aus", l3["griffe"][0].abgebrochen())

# d2) EINE GEHALTENE TASTE direkt am Anfang darf die Ziehung NICHT
#     wegwischen - sie wird verbraucht und ignoriert.
l3b = _phase(1000, eingaben=["ok"] * 200)
check("eine von Anfang an gehaltene Taste wischt die Ziehung nicht weg",
      l3b["dauer"] >= fm.ZIEHUNG_TASTENSPERRE,
      "%.3f s" % l3b["dauer"])

# d3) UND DER EIGENTLICHE FEHLER AUS BUILD 246: read_action() ohne
#     timeout. Die Attrappe wirft dann - kommt der Aufruf zurueck,
#     steht die Lücke wieder im Code.
check("read_action wird NIE ohne timeout gerufen",
      l3["eingabe"].ohne_timeout == 0
      and l3b["eingabe"].ohne_timeout == 0,
      "ohne timeout blockiert es bis zum naechsten Tastendruck - "
      "ein Bild, dann Stillstand")
check("und es wird ueberhaupt gefragt", l3b["eingabe"].aufrufe > 0,
      "sonst ueberspringt keine Taste etwas")

# e) DER SCHALTER "NAVIGATIONS-SOUNDEFFEKTE" DARF NICHT MITREDEN.
#
#    GEAENDERT (Build 247, Nutzer-Rueckmeldung: "bei zufallszock hoere
#    ich denn sound nicht"). In Build 246 hing der Ziehungssound
#    zusaetzlich an diesem Schalter - wer die Klicktoene beim Scrollen
#    abgeschaltet hat (und das tun viele), hatte damit auch die
#    Ziehung stumm, ohne dass irgendwo stand, woran es liegt.
#
#    Gewuenscht war ein Ziehungssound, nicht ein weiterer
#    Navigationsklick. Es gibt genau EINEN Schalter fuer das Feature:
#    die Dauer der Spannungsphase. Steht sie auf "aus", passiert
#    nichts; steht sie auf einer Dauer, gehoert der Ton dazu.
l4 = _phase(1000, sfx_an=False)
check("der Klang kommt AUCH mit abgeschalteten Navigationstoenen",
      l4["sound"] == ["zufall_ziehung"], str(l4["sound"]))
check("die Ziehung laeuft dabei normal", 0.9 <= l4["dauer"] <= 1.6,
      "%.3f s" % l4["dauer"])
check("die Dauer 'aus' ist der EINE Schalter fuer alles",
      _phase(0)["sound"] == [],
      "sonst gaebe es keinen Weg, nur den Ton abzustellen")

# f) Ein Fehler im Sound darf die Ziehung nicht mitnehmen.
def _kaputt(name, griff=None):
    raise RuntimeError("keine Soundkarte")


_merk = f._play_ducked_sfx
f._play_ducked_sfx = _kaputt
try:
    l5 = _phase(1000)
    ok = True
except Exception as e:                                       # noqa: BLE001
    ok = False
    print("    AUSNAHME:", e)
finally:
    f._play_ducked_sfx = _merk
check("ein Audiofehler bricht die Ziehung nicht ab", ok,
      "ein stummer Bildschirm ist besser als keiner")

# g) DIE STEHENDE UHR. Genau daran ist der erste Testlauf zehn Minuten
#    haengen geblieben: die Phase wartet auf time.monotonic(), und im
#    Pruefstand steht die still. Auf dem Geraet kommt das nicht vor -
#    eine Schleife, aus der keine Taste herausfuehrt, darf es trotzdem
#    nicht geben.
fm.time.monotonic = lambda: 1000.0
try:
    _t0 = time.perf_counter()
    l6 = _phase(5000)
    _steh = time.perf_counter() - _t0
finally:
    fm.time.monotonic = _ECHTE_UHR
check("bei stehender Uhr steigt die Phase sofort aus", _steh < 1.5,
      "%.2f s - sonst haengt der Bildschirm" % _steh)
check("und auch dann ist der Sound danach aus",
      l6["griffe"] and l6["griffe"][0].abgebrochen())
_q_vor = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
                 encoding="utf-8").read()
check("es gibt zusaetzlich eine Obergrenze fuer die Bilder",
      "for _ in range(400)" in _q_vor,
      "zwei Netze: der Uhrvergleich und eine harte Grenze")

# ---------------------------------------------------------------------------
print()
print("Test 4: das Laden steht an EINER Stelle")
# ---------------------------------------------------------------------------
_q = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
             encoding="utf-8").read()
check("es gibt genau eine Funktion dafuer",
      _q.count("def _wot_cover_sichern") == 1)
# Drei Aufrufstellen: die abgeschaltete Phase, die laufende Phase und
# die Zeichenschleife. Alle drei fuellen denselben Zwischenspeicher.
check("Phase und Zeichenschleife rufen dieselbe Funktion",
      _q.count("self._wot_cover_sichern(") == 3,
      "sonst wartet man zweimal: erst die Spannung, dann das Laden")
check("in der Zeichenschleife steht kein eigener get_scaled mehr",
      "cover_cache[ckey] = art" not in _q,
      "zwei Ladewege fuer dasselbe Cover driften auseinander")
check("ein kaputtes Cover wird abgefangen",
      "cover_cache[ckey] = None" in _q,
      "eine Zeile ohne Bild ist immer noch spielbar")

# ---------------------------------------------------------------------------
print()
print("Test 5: der Sound selbst ist hinterlegt")
# ---------------------------------------------------------------------------
check("es gibt einen Ersatzklang",
      "zufall_ziehung" in AUDIO.SFX_CHIME_DEFS,
      "ohne ihn bleibt die Ziehung stumm, wenn die MP3 fehlt")
_seg = AUDIO.SFX_CHIME_DEFS.get("zufall_ziehung") or []
_laenge = sum(d for _a, _b, d in _seg)
check("er ist ein Wirbel und kein Einzelton", len(_seg) >= 8,
      "%d Abschnitte" % len(_seg))
check("und kuerzer als die kleinste Stufe", _laenge <= 1000,
      "%d ms gegen 1000 ms" % _laenge)
check("die MP3 des Nutzers liegt im Auslieferungsordner",
      os.path.exists(os.path.join(_REPO, "frontend", "sfx",
                                  "zufall_ziehung.mp3")),
      "play_sfx()/_play_ducked_sfx() bevorzugen die MP3")

# ---------------------------------------------------------------------------
print()
print("Test 6: der Menuepunkt ist angeschlossen")
# ---------------------------------------------------------------------------
_m = io.open(os.path.join(_REPO, "frontend", "fe", "menu.py"),
             encoding="utf-8").read()
check("der Eintrag steht im Menue", '"ziehung_spannung"' in _m)
check("die Beschriftung nennt den Wert", "ziehung_label" in _m)
check("0 wird als 'aus' geschrieben, nicht als '0,0s'",
      'sys_ziehung_aus' in _m,
      "aus ist keine Dauer, sondern ein abgeschaltetes Feature")
check("die Taste schaltet weiter",
      'elif kind == "ziehung_spannung":' in _q
      and "cycle_ziehung_spannung()" in _q)
import fe.translations as TR                                 # noqa: E402
for _k in ("sys_ziehung_spannung", "sys_ziehung_aus", "wot_drawing"):
    _e = TR.TRANSLATIONS.get(_k)
    check("Uebersetzung %s in beiden Sprachen" % _k,
          bool(_e) and bool(_e.get("de")) and bool(_e.get("en")),
          str(_e))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
