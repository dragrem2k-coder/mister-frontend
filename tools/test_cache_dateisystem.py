#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Keine Dateisystem-Arbeit mehr im Zeichenweg (Build 212).

ZWEI UMBAUTEN, und sie sind unterschiedlich gut begruendet - das gehoert
in denselben Test, damit niemand sie spaeter gleich behandelt.

1. os.utime() je Cache-Treffer ist aus dem Lesepfad heraus.

   Bei einer Rasterseite mit 21 Kacheln waren das 21 Metadaten-
   Schreibvorgaenge je Seitenaufbau, mitten im Scrollen, auf dieselbe
   Karte, von der gleichzeitig die Miniaturen gelesen werden.

   ZUR ERWARTUNG, denn die Messung steht schon in diesem Projekt
   (Build 74, vom Geraet des Nutzers, siehe
   _thumb_cache_evict_if_needed()):

       lesen     11.2 ms      entpacken 1.3 ms      utime 0.1 ms

   0,1 ms je Marke, bei 21 Kacheln also 2 ms von rund 227 ms. Der Umbau
   ist NICHT mit Geschwindigkeit begruendet, sondern mit
   Kartenverschleiss und Schreib-Konkurrenz. Wer ihn als Tempogewinn
   verkauft, hat die eigene Messung nicht gelesen.

2. os.stat() je Nachschlagen ist aus dem Zeichenweg heraus.

   Dafuer gibt es KEINE Messung von echter Hardware - deshalb behauptet
   dieser Test auch keinen Gewinn. Er sichert nur zu, dass es passiert
   und dass der PREIS beherrscht bleibt: die Aenderungszeit ist die
   Marke, an der ein ausgetauschtes Cover erkannt wird.

WAS DIESER TEST ABSICHERT

  - dass ein Cache-Treffer NICHTS mehr auf die Karte schreibt,
  - dass die Marke trotzdem nicht verloren geht, sondern nachgezogen
    wird - im Leerlauf portionsweise, vor jeder Verdraengung ganz,
  - dass ohne gestellte Uhr weiterhin gar nichts geschrieben wird,
  - dass os.stat() je Quellpfad nur EINMAL passiert,
  - dass der Schluessel dabei BITGENAU derselbe bleibt (sonst waeren
    alle Miniaturen auf der Karte entwertet),
  - und dass ein Neueinlesen den Zwischenspeicher verwirft.
"""
import os
import sys
import tempfile

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))
sys.path.insert(0, _HIER)

import fe.art as A                                         # noqa: E402

fails = []


def check(name, ok, extra=""):
    print("  %s %s%s" % ("OK  " if ok else "FEHL", name,
                         ("  (%s)" % extra) if extra else ""))
    if not ok:
        fails.append(name + ((" - " + extra) if extra else ""))


TMP = tempfile.mkdtemp(prefix="dragend_cache_")
A.THUMB_CACHE_DIR = os.path.join(TMP, "cache")
os.makedirs(A.THUMB_CACHE_DIR)

# Ein Zaehler um os.utime, damit jeder Schreibvorgang sichtbar wird.
_echt_utime = os.utime
utimes = []


def _zaehl_utime(pfad, zeiten=None, **kw):
    utimes.append(pfad)
    return _echt_utime(pfad, zeiten, **kw)


_echt_stat = os.stat
stats = []


def _zaehl_stat(pfad, *a, **kw):
    if isinstance(pfad, str):
        stats.append(pfad)
    return _echt_stat(pfad, *a, **kw)


os.utime = _zaehl_utime
A.os.utime = _zaehl_utime
A.os.stat = _zaehl_stat

# Eine echte Quelldatei und ein echter Cache-Eintrag.
quelle = os.path.join(TMP, "cover.art")
with open(quelle, "wb") as f:
    f.write(b"\x00" * 256)

# ---------------------------------------------------------------------------
print("Test 1: ein Cache-Treffer schreibt NICHTS auf die Karte")
# ---------------------------------------------------------------------------
A._uhr_verlaesslich = True
A._marken_offen.clear()
cpath = os.path.join(A.THUMB_CACHE_DIR, "probe.bin")
with open(cpath, "wb") as f:
    f.write(b"y")
utimes[:] = []
A._benutzt_vermerken(cpath)
check("kein os.utime im Lesepfad", not utimes, repr(utimes))
check("die Marke ist aber vorgemerkt", A.marken_offen() == 1,
      str(A.marken_offen()))

# Derselbe Pfad zweimal soll nur EINE Vormerkung ergeben - sonst
# staut sich beim Scrollen derselbe Eintrag vielfach auf.
A._benutzt_vermerken(cpath)
A._benutzt_vermerken(cpath)
check("derselbe Pfad staut sich nicht auf", A.marken_offen() == 1,
      str(A.marken_offen()))

# ---------------------------------------------------------------------------
print()
print("Test 2: nachgezogen wird im Leerlauf, portionsweise")
# ---------------------------------------------------------------------------
A._marken_offen.clear()
viele = []
for i in range(120):
    p = os.path.join(A.THUMB_CACHE_DIR, "m%03d.bin" % i)
    with open(p, "wb") as f:
        f.write(b"z")
    viele.append(p)
    A._benutzt_vermerken(p)
check("120 Marken vorgemerkt", A.marken_offen() == 120,
      str(A.marken_offen()))
utimes[:] = []
n = A.marken_nachziehen()
check("ein Durchgang schreibt eine Portion, nicht alles",
      0 < n < 120, "%d geschrieben" % n)
check("und genau so viele os.utime", len(utimes) == n,
      "%d Aufrufe fuer %d Marken" % (len(utimes), n))
print("    Portion: %d Marken je Durchgang" % n)
runden = 1
while A.marken_offen():
    A.marken_nachziehen()
    runden += 1
    if runden > 20:
        break
check("nach mehreren Durchgaengen ist der Rueckstand abgetragen",
      A.marken_offen() == 0, "%d offen" % A.marken_offen())
print("    abgetragen in %d Durchgaengen" % runden)

# Notbremse: unbegrenzt darf sich nichts aufstauen.
A._marken_offen.clear()
for i in range(A._MARKEN_OFFEN_MAX + 200):
    A._benutzt_vermerken("/x/%d" % i)
check("der Stau ist nach oben begrenzt",
      A.marken_offen() == A._MARKEN_OFFEN_MAX, str(A.marken_offen()))
A._marken_offen.clear()

# ---------------------------------------------------------------------------
print()
print("Test 3: ohne gestellte Uhr wird gar nichts geschrieben")
# ---------------------------------------------------------------------------
# Das ist der Fehler aus Build 91: eine Marke mit falscher Uhrzeit ist
# schlimmer als keine, weil die Verdraengung dann die gerade benutzten
# Dateien wegwirft.
A._uhr_verlaesslich = False
A._marken_offen.clear()
A._vor_uhrstellung_beruehrt[:] = []
A._benutzt_vermerken(cpath)
utimes[:] = []
check("marken_nachziehen() schreibt nichts", A.marken_nachziehen() == 0)
check("und ruft kein os.utime", not utimes, repr(utimes))
check("der Eintrag steht in der Uhrstellungs-Liste",
      cpath in A._vor_uhrstellung_beruehrt)
A._uhr_verlaesslich = True

# ---------------------------------------------------------------------------
print()
print("Test 4: vor der Verdraengung wird VOLLSTAENDIG nachgezogen")
# ---------------------------------------------------------------------------
import inspect                                             # noqa: E402

q_evict = inspect.getsource(A._thumb_cache_evict_if_needed)
i_marken = q_evict.find("marken_nachziehen(")
check("die Verdraengung zieht die Marken nach", i_marken > 0)
check("und zwar ohne Portionsgrenze",
      "_MARKEN_OFFEN_MAX" in q_evict[i_marken:i_marken + 120],
      q_evict[i_marken:i_marken + 60].strip())
# Wirklich VOR dem Zaehlen/Loeschen, nicht danach.
i_anzahl = q_evict.find("_thumb_cache_anzahl is not None")
check("vor dem Zaehlen und Verdraengen", 0 < i_marken < i_anzahl,
      "%d / %d" % (i_marken, i_anzahl))
check("der Fehler von Build 91 ist als Grund genannt",
      "Build 91" in q_evict)

# ---------------------------------------------------------------------------
print()
print("Test 5: os.stat je Quellpfad nur EINMAL")
# ---------------------------------------------------------------------------
A.quelldaten_vergessen()
stats[:] = []
schluessel = [A._thumb_cache_key(quelle, 270, 361) for _ in range(20)]
eigene = [p for p in stats if p == quelle]
check("zwanzig Nachschlagevorgaenge, ein os.stat", len(eigene) == 1,
      "%d Aufrufe" % len(eigene))
check("und immer derselbe Schluessel", len(set(schluessel)) == 1)

# Andere Kastengroesse: auch dafuer kein zweites stat.
stats[:] = []
k2 = A._thumb_cache_key(quelle, 176, 235)
check("eine zweite Kastengroesse braucht kein neues os.stat",
      not [p for p in stats if p == quelle], repr(stats))
check("ergibt aber einen anderen Schluessel", k2 != schluessel[0])

# ---------------------------------------------------------------------------
print()
print("Test 6: der Schluessel bleibt BITGENAU derselbe")
# ---------------------------------------------------------------------------
# Das ist die eigentliche Gefahr dieses Umbaus: ein anderer Schluessel
# entwertet JEDE Miniatur auf der Karte des Nutzers - 121000 Dateien,
# die niemand mehr trifft, und ein Vorbereitungslauf von Stunden.
import hashlib                                             # noqa: E402

st = _echt_stat(quelle)
for w, h in ((270, 361), (176, 235), (733, 909)):
    sig = "%s|%d|%d|%d|%.6f|%s%s" % (quelle, w, h, st.st_size, st.st_mtime,
                                     A.THUMB_ALGO_VERSION,
                                     A.verkleinern_modus_kuerzel())
    erwartet = hashlib.sha1(
        sig.encode("utf-8", "surrogateescape")).hexdigest()[:24]
    check("%dx%d wie vor dem Umbau" % (w, h),
          A._thumb_cache_key(quelle, w, h) == erwartet)

# Und eine fehlende Datei fuehrt weiterhin auf den kurzen Schluessel.
A.quelldaten_vergessen()
fehlt = os.path.join(TMP, "gibtsnicht.art")
sig = "%s|%d|%d|%s%s" % (fehlt, 10, 10, A.THUMB_ALGO_VERSION,
                         A.verkleinern_modus_kuerzel())
check("eine fehlende Quelle ergibt denselben Schluessel wie vorher",
      A._thumb_cache_key(fehlt, 10, 10)
      == hashlib.sha1(sig.encode("utf-8", "surrogateescape")).hexdigest()[:24])

# ---------------------------------------------------------------------------
print()
print("Test 7: der Preis ist beherrscht - Neueinlesen verwirft")
# ---------------------------------------------------------------------------
A.quelldaten_vergessen()
k_alt = A._thumb_cache_key(quelle, 270, 361)
with open(quelle, "wb") as f:                     # Cover ausgetauscht
    f.write(b"\x01" * 4096)
check("ohne Neueinlesen bleibt der alte Schluessel - der bekannte Preis",
      A._thumb_cache_key(quelle, 270, 361) == k_alt)
A.quelldaten_vergessen()
check("nach quelldaten_vergessen() wird der Austausch erkannt",
      A._thumb_cache_key(quelle, 270, 361) != k_alt)

# Und beide Neueinlese-Pfade rufen es wirklich.
fe_quelle = open(os.path.join(_REPO, "frontend", "frontend.py"),
                 encoding="utf-8").read()
check("frontend.py importiert quelldaten_vergessen",
      "quelldaten_vergessen" in fe_quelle)
check("und ruft es an ZWEI Stellen (beide Neueinlese-Pfade)",
      fe_quelle.count("quelldaten_vergessen()") >= 2,
      "%d Aufrufe" % fe_quelle.count("quelldaten_vergessen()"))
for stelle in ("scan_games(force=True", "scan_games(force=force_rescan"):
    i = fe_quelle.find(stelle)
    check("vor %s..." % stelle[:26],
          i > 0 and "quelldaten_vergessen()" in fe_quelle[max(0, i - 400):i])

# Die Notbremse gegen unbegrenztes Wachsen.
A.quelldaten_vergessen()
for i in range(A._QUELL_STAT_MAX + 50):
    A._quell_stat["/x/%d" % i] = (1, 1.0)
A._quelldaten(quelle)
check("der Zwischenspeicher waechst nicht unbegrenzt",
      len(A._quell_stat) <= A._QUELL_STAT_MAX,
      "%d Eintraege" % len(A._quell_stat))

# ---------------------------------------------------------------------------
print()
print("Test 8: der Leerlauf-Haken sitzt an der richtigen Stelle")
# ---------------------------------------------------------------------------
# Nur im Leerlaufzweig - liegt eine Eingabe an, wird dieser Zweig mit
# "return act" uebersprungen, und genau das ist hier gewollt.
# NICHT mit find() auf den Text: der erste Treffer war beim ersten
# Anlauf eine KOMMENTARZEILE ("Siehe marken_nachziehen() in fe/art.py"),
# und der Test war rot, ohne etwas ueber das Programm zu sagen. Sechster
# Fall dieser Sorte im Projekt - also nach dem echten AUFRUF suchen, an
# der Einrueckung erkennbar, und nicht nach dem Wort.
rufe = [z for z in fe_quelle.split("\n")
        if z.strip() == "marken_nachziehen()"]
check("marken_nachziehen() wird aus frontend.py gerufen", len(rufe) == 1,
      "%d Aufrufzeilen" % len(rufe))
i_marken = fe_quelle.find("\n" + rufe[0] + "\n") if rufe else -1
umfeld = fe_quelle[max(0, i_marken - 900):i_marken]
check("hinter einer eigenen Uhr (kein Schreibstoss)",
      "MARKEN_TAKT" in umfeld)
check("und im Leerlaufzweig, erkennbar an _boot_watch daneben",
      "_boot_watch" in fe_quelle[i_marken:i_marken + 200])

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
