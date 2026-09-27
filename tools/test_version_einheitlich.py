#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Alle Stellen mit der Versionsnummer sagen dasselbe (Build 212).

DER FEHLER, DER DAZU GEFUEHRT HAT, und er hat ein halbes Release
gekostet.

Beim Bump auf v4.6 wurde die Zahl an EINER Stelle hochgezaehlt - in der
Datei ./VERSION im Wurzelverzeichnis. Die liest niemand. Die beiden
Stellen, auf die es ankommt, blieben auf 4.5 stehen:

    frontend/fe/update_check.py   FRONTEND_VERSION = "4.5"
    frontend/VERSION              4.5

Die zweite ist die Datei, die das Update-Popup von GitHub abholt
(UPDATE_CHECK_URL), die erste ist die, mit der es verglichen wird
(_version_newer). Beide 4.5 heisst: kein Nutzer hat je eine
Update-Meldung fuer v4.6 bekommen. Aufgefallen ist es erst beim
Aufraeumen fuer v4.7 - also viele Builds spaeter.

Der Quelltext WARNT sogar davor. In frontend.py steht bei
FRONTEND_VERSION, dass die Nummer "mit dem Header-Kommentar oben,
README, CHANGELOG und der VERSION-Datei UEBEREINSTIMMEN" muss, und in
update_check.py steht die Geschichte der drei frueheren Dubletten
("dasselbe Drift-Risiko wie zuvor schon bei den Scripts/-Kopien").
Beides half nicht, weil eine Ermahnung im Kommentar niemanden
stolpern laesst.

Dieser Test tut das. Er ist die Umsetzung derselben Lehre wie
nur_code() in test_beenden.py: gegen einen Fehler, den man wiederholt
macht, hilft ein Werkzeug und keine Ermahnung.

MITGEPRUEFT WIRD DER UPDATE-POPUP-TEXT, aus demselben Geist: der
"summary" aus LATEST_BUILD.json wird dem Nutzer UNVERAENDERT im
Update-Dialog gezeigt und passt dort mit rund 96 Zeichen auf CRT und
216 auf HDMI. Das steht seit langem in update_check.py, samt dem
Hinweis, dass ein zu langer Text schon einmal mitten im Satz
abgeschnitten wurde - und ich habe trotzdem ueber viele Builds
Zusammenfassungen mit mehreren tausend Zeichen eingetragen. Also auch
das ab jetzt als Pruefung und nicht als Kommentar.
"""
import io
import json
import os
import re
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)

fails = []


def check(name, ok, extra=""):
    print("  %s %s%s" % ("OK  " if ok else "FEHL", name,
                         ("  (%s)" % extra) if extra else ""))
    if not ok:
        fails.append(name + ((" - " + extra) if extra else ""))


def lies(*teile):
    return io.open(os.path.join(_REPO, *teile), encoding="utf-8").read()


# ---------------------------------------------------------------------------
print("Test 1: die EINE Quelle der Wahrheit")
# ---------------------------------------------------------------------------
uc = lies("frontend", "fe", "update_check.py")
m = re.search(r'^FRONTEND_VERSION\s*=\s*"([^"]+)"', uc, re.M)
check("FRONTEND_VERSION steht in fe/update_check.py", m is not None)
if not m:
    print("\nFEHLGESCHLAGEN: ohne diese Zahl ist nichts zu vergleichen.")
    sys.exit(1)
VERSION = m.group(1)
print("    FRONTEND_VERSION = %s" % VERSION)
check("und hat die Form x.y", re.match(r"^\d+\.\d+$", VERSION) is not None,
      VERSION)

# Und sie ist wirklich nur EINMAL als Zeichenkette hinterlegt - genau
# das war der Fehler beim v4.4-Bump, den update_check.py beschreibt.
for datei in (("frontend", "frontend.py"), ("frontend", "fe", "menu.py")):
    q = lies(*datei)
    doppelt = re.findall(r'FRONTEND_VERSION\s*=\s*"', q)
    check("%s hinterlegt sie NICHT selbst" % "/".join(datei),
          not doppelt, "%d Fundstellen" % len(doppelt))

# ---------------------------------------------------------------------------
print()
print("Test 2: die Datei, die das Update-Popup von GitHub abholt")
# ---------------------------------------------------------------------------
# Das ist die Stelle, an der v4.6 gescheitert ist.
url = re.search(r'UPDATE_CHECK_URL\s*=\s*\(([^)]+)\)', uc, re.S)
check("UPDATE_CHECK_URL ist gesetzt", url is not None)
if url:
    ziel = "".join(re.findall(r'"([^"]*)"', url.group(1)))
    check("sie zeigt auf frontend/VERSION", ziel.endswith("frontend/VERSION"),
          ziel)

fv = lies("frontend", "VERSION").strip()
check("frontend/VERSION stimmt mit FRONTEND_VERSION ueberein",
      fv == VERSION, "frontend/VERSION=%r, FRONTEND_VERSION=%r"
      % (fv, VERSION))

wv_pfad = os.path.join(_REPO, "VERSION")
if os.path.exists(wv_pfad):
    wv = io.open(wv_pfad, encoding="utf-8").read().strip()
    check("./VERSION im Wurzelverzeichnis stimmt ebenfalls",
          wv == VERSION,
          "./VERSION=%r, FRONTEND_VERSION=%r - genau hier lief v4.6 "
          "auseinander" % (wv, VERSION))

# ---------------------------------------------------------------------------
print()
print("Test 3: Dateikopf, READMEs und Changelog")
# ---------------------------------------------------------------------------
kopf = lies("frontend", "frontend.py")[:2000]
m_kopf = re.search(r"MiSTer Custom Frontend - v(\d+\.\d+)", kopf)
check("der Dateikopf nennt eine Version", m_kopf is not None)
if m_kopf:
    check("und zwar dieselbe", m_kopf.group(1) == VERSION,
          "Kopf=%s" % m_kopf.group(1))

for name in ("README.md", "README_EN.md"):
    q = lies(name)
    m_r = re.search(r"MiSTer Custom Frontend v(\d+\.\d+)", q[:300])
    check("%s nennt eine Version in der Kopfzeile" % name, m_r is not None)
    if m_r:
        check("%s nennt dieselbe" % name, m_r.group(1) == VERSION,
              "%s=%s" % (name, m_r.group(1)))

for name in ("CHANGELOG.md", "CHANGELOG_EN.md"):
    q = lies(name)
    # Der oberste Abschnitt muss die aktuelle Version sein - und nicht
    # mehr "noch nicht veroeffentlicht", wenn die Nummer schon steht.
    m_c = re.search(r"^## v?(\d+\.\d+)", q, re.M)
    check("%s hat einen Versionsabschnitt" % name, m_c is not None)
    if m_c:
        check("%s: der oberste ist v%s" % (name, VERSION),
              m_c.group(1) == VERSION,
              "oberster Abschnitt ist v%s" % m_c.group(1))
    offen = re.search(r"^## .*(noch nicht ver|not yet rel)", q, re.M)
    if offen:
        # Ein offener Block ist erlaubt, aber nur OBERHALB des
        # Versionsabschnitts - sonst behauptet der Changelog, die
        # aktuelle Version sei unveroeffentlicht.
        check("%s: ein offener Block steht ueber dem Versionsabschnitt"
              % name, m_c is not None and offen.start() < m_c.start(),
              "offener Block steht unterhalb von v%s"
              % (m_c.group(1) if m_c else "?"))

# ---------------------------------------------------------------------------
print()
print("Test 4: der Update-Popup-Text passt auf den Bildschirm")
# ---------------------------------------------------------------------------
lb = json.loads(lies("frontend", "LATEST_BUILD.json"))
check("LATEST_BUILD.json hat eine build_id", bool(lb.get("build_id")))
check("und einen summary", bool(lb.get("summary")))
summary = lb.get("summary") or ""
print("    summary: %d Zeichen" % len(summary))

# Die Zahlen stehen in update_check.py und werden hier ABGELESEN, nicht
# nachgebaut - sonst laufen sie eines Tages auseinander wie die Version.
m_crt = re.search(r"(\d+)\s*Zeichen auf CRT", uc)
m_hd = re.search(r"bzw\.\s*(\d+)\s*Zeichen auf HDMI", uc)
grenze_crt = int(m_crt.group(1)) if m_crt else 96
grenze_hd = int(m_hd.group(1)) if m_hd else 216
print("    Grenzen laut update_check.py: %d (CRT), %d (HDMI)"
      % (grenze_crt, grenze_hd))
check("der summary passt auf HDMI", len(summary) <= grenze_hd,
      "%d von %d Zeichen - der Rest wird dem Nutzer mitten im Satz "
      "abgeschnitten" % (len(summary), grenze_hd))
if len(summary) > grenze_crt:
    print("    Hinweis: auf CRT (%d Zeichen) wird gekuerzt - hinnehmbar, "
          "solange" % grenze_crt)
    print("    der erste Satz allein schon die Aussage traegt.")
check("er endet nicht mitten im Wort",
      not summary or summary.rstrip()[-1] in ".!?",
      "letztes Zeichen %r" % (summary.rstrip()[-1:] if summary else ""))

# Die Langfassung darf es geben - nur nicht im summary.
if "details" in lb:
    print("    details: %d Zeichen (wird dem Nutzer NICHT gezeigt)"
          % len(lb["details"]))
    check("die Langfassung steht in einem eigenen Feld", True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
