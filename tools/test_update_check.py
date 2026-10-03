#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Update-Info (Build 224) - und die Zahl, die sie lahmgelegt hat.

WAS PASSIERT WAR. Im Log des Nutzers stand bei jedem Start:

    Update-Check: GitHub meldet Version '4.7' (lokal: '4.7')
    Build-Check fehlgeschlagen: Unterminated string starting at:
        line 4 column 14 (char 229)

und in seinem update_check_state.json:

    "notified_build_id": "2026-09-27-204"

Beides zusammen ergibt die Diagnose. check_for_build_update() hat die
Antwort mit resp.read(2000) gelesen. Die Obergrenze an sich ist richtig
- eine Netzantwort unbesehen komplett einzulesen waere leichtsinnig -,
aber das Feld "details" in LATEST_BUILD.json ist die ausfuehrliche
Build-Beschreibung und seit Build 205 mehrere Kilobyte lang. Gelesen
wurden also 2000 Byte MITTEN AUS EINEM STRING; json.loads() sagte voellig
zu Recht "Unterminated string", und der Aufrufer bekam None. Seit Build
205 kam deshalb nie wieder eine Update-Info an - neunzehn Builds lang.

DREI PRUEFUNGEN, und die dritte ist die, die das verhindert haette:

  1. die Grenze ist grosszuegig, aber es GIBT eine
  2. eine abgeschnittene Antwort wird als solche erkannt und geloggt
  3. die ECHTE Datei im Paket passt hinein - und zwar mit Abstand

Ausfuehren:
    python3 tools/test_update_check.py
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402,F401  (setzt den Pfad)

import fe.update_check as U   # noqa: E402

fails = []
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check(name, ok, info=""):
    if ok:
        print("  OK   %s %s" % (name, info))
    else:
        print("  FEHL %s %s" % (name, info))
        fails.append(name)


# ---------------------------------------------------------------------------
print("Test 1: es gibt eine Grenze, und sie ist grosszuegig")
# ---------------------------------------------------------------------------
check("BUILD_CHECK_MAX ist gesetzt", hasattr(U, "BUILD_CHECK_MAX"))
check("sie ist eine harte Obergrenze", U.BUILD_CHECK_MAX <= 4 * 1024 * 1024,
      "%d Byte - eine Netzantwort wird nicht unbesehen eingelesen"
      % U.BUILD_CHECK_MAX)
check("und deutlich groesser als die alten 2000 Byte",
      U.BUILD_CHECK_MAX >= 64 * 1024, "%d Byte" % U.BUILD_CHECK_MAX)
check("resp.read() benutzt sie auch",
      "resp.read(BUILD_CHECK_MAX)" in io.open(
          os.path.join(_REPO, "frontend", "fe", "update_check.py"),
          encoding="utf-8").read(),
      "sonst steht die Zahl nur dekorativ im Quelltext")

# ---------------------------------------------------------------------------
print()
print("Test 2: DIE ECHTE DATEI passt hinein - mit Abstand")
# ---------------------------------------------------------------------------
# DAS IST DIE PRUEFUNG, DIE GEFEHLT HAT. Sie waere bei Build 205
# angeschlagen, als die Beschreibung ueber die damalige Grenze wuchs.
pfad = os.path.join(_REPO, "frontend", "LATEST_BUILD.json")
roh = io.open(pfad, "rb").read()
check("LATEST_BUILD.json ist da", len(roh) > 0)
check("sie ist gueltiges JSON", json.loads(roh.decode("utf-8")) is not None)
check("sie passt in die Grenze", len(roh) <= U.BUILD_CHECK_MAX,
      "%d von %d Byte" % (len(roh), U.BUILD_CHECK_MAX))
check("und zwar mit mindestens dem Vierfachen Luft",
      len(roh) * 4 <= U.BUILD_CHECK_MAX,
      "%d Byte bei einer Grenze von %d - wer die Beschreibung "
      "ausfuehrlicher schreibt, soll nicht die Update-Info abschalten"
      % (len(roh), U.BUILD_CHECK_MAX))

daten = json.loads(roh.decode("utf-8"))
check("sie hat eine build_id", bool(daten.get("build_id")),
      "%r" % daten.get("build_id"))
check("und eine summary", bool(daten.get("summary")))
# Der summary-Text landet UNVERAENDERT im Popup, und das ist drei Zeilen
# hoch: rund 96 Zeichen auf CRT, 216 auf HDMI. Laenger heisst
# abgeschnitten mitten im Satz - einmal passiert, siehe den Kommentar in
# fe/update_check.py.
check("und die summary passt in den Dialog",
      len(daten.get("summary", "")) <= 260,
      "%d Zeichen - auf HDMI passen rund 216"
      % len(daten.get("summary", "")))

# ---------------------------------------------------------------------------
print()
print("Test 3: eine abgeschnittene Antwort wird als solche erkannt")
# ---------------------------------------------------------------------------
# Nachgestellt wird genau der Fall von damals: die Antwort ist laenger
# als die Grenze, json.loads() scheitert. Der Check muss None liefern
# (nicht abstuerzen) UND es so protokollieren, dass man die Ursache in
# einer Zeile sieht.
meldungen = []
_echt_log = U.LOG
U.LOG = lambda m: meldungen.append(m)


class _Antwort(object):
    def __init__(self, daten):
        self._d = daten

    def read(self, n=None):
        return self._d[:n] if n else self._d

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


_echt_open = U.urllib.request.urlopen
try:
    gross = json.dumps({"build_id": "2026-10-02-224",
                        "summary": "kurz",
                        "details": "x" * 4000}).encode("utf-8")

    U.BUILD_CHECK_MAX = 2000          # die alte, zu kleine Grenze
    U.urllib.request.urlopen = lambda *a, **k: _Antwort(gross)
    meldungen[:] = []
    erg = U.check_for_build_update()
    check("abgeschnitten -> kein Ergebnis, aber auch kein Absturz",
          erg is None)
    check("und das Log nennt die Laenge",
          any("unlesbar nach" in m for m in meldungen),
          "%r" % (meldungen[:1],))
    check("und sagt, dass die Grenze erreicht war",
          any("laenger als" in m for m in meldungen))

    # Dieselbe Antwort, Grenze gross genug: jetzt muss es klappen.
    U.BUILD_CHECK_MAX = 256 * 1024
    meldungen[:] = []
    erg = U.check_for_build_update()
    check("mit ausreichender Grenze kommt die Build-Kennung an",
          erg is not None and erg[0] == "2026-10-02-224", "%r" % (erg,))
    check("und die Kurzbeschreibung dazu",
          erg is not None and erg[1] == "kurz")

    # Und echtes kaputtes JSON bleibt echtes kaputtes JSON.
    meldungen[:] = []
    U.urllib.request.urlopen = lambda *a, **k: _Antwort(b"{kein json")
    check("kaputte Antwort liefert ebenfalls None",
          U.check_for_build_update() is None)
    check("wird aber NICHT als abgeschnitten gemeldet",
          not any("laenger als" in m for m in meldungen),
          "sonst sucht man beim naechsten Mal an der falschen Stelle")
finally:
    U.urllib.request.urlopen = _echt_open
    U.LOG = _echt_log
    U.BUILD_CHECK_MAX = 256 * 1024

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alles in Ordnung.")
