#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Speicher und Rueckkehr aus dem Core: gemessen (Build 343), schneller
und schlanker (Build 344).

ANLASS: ein Vergleich mit einem anderen Frontend, in dem bei Dragend
"kein belastbarer Messwert" stand - beim Speicher und bei der Rueckkehr
aus einem Core. Dazu im Bench die Zeit, eine Kategorie zu oeffnen.

GEPRUEFT WIRD:
  1. fe/messwerte.py liest /proc/self/status und /proc/meminfo; fehlt
     die Datei, gibt es ein leeres Ergebnis statt eines Fehlers.
  2. Die Rueckkehr-Datei: anhaengen, nur die letzten RUECKKEHR_MAX,
     keine .tmp-Reste, eine kaputte Datei ergibt eine leere Liste,
     fremde Eintraege fallen weg.
  3. run_core() misst eine echte Rueckkehr (mit nachgestelltem Core):
     Abschnitte, Weg, Zeit ab der Ausstiegs-Taste, Speicher waehrend des
     Spiels; die Abschnitte ergeben zusammen die Gesamtzeit; eine
     Logzeile RUECKKEHR. Seit Build 344: die Pause zaehlt ab dem Menue
     (Nacharbeit laeuft in ihr), das erste Bild entsteht in der F9-Frist
     ohne den Schirm anzufassen, erst nach dem Griff aufs Pad kommt es
     auf den Schirm; geht das schief, wird normal gezeichnet (3b).
  3c. Beim Spielstart wird Cover-Speicher freigegeben: Originale weg,
     "kein Cover" bleibt, die juengsten Miniaturen bis zum Budget
     bleiben; ein Fehler haelt das Spiel nicht auf.
  4. Eine Messung, die schiefgeht, stoert die Rueckkehr nicht; die
     Pause bleibt eine Sekunde; Menue alle 0,2 s bzw. 0,1 s gefragt.
  5. Der Bench: Nummer 26, Abschnitte R, S, T im Lauf, S und T sagen
     ohne Messung, was zu tun ist, R misst die groesste Kategorie und
     stellt die Seite danach wieder her; P stoppt das Dateisystem nur im
     eigenen Faden, gibt os wieder frei und schluesselt den laengsten
     Happen auf.

Ausfuehren:
    python3 tools/test_messwerte.py
"""
import json
import os
import shutil
import sys
import tempfile
import time

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HIER)
import _harness as H                                     # noqa: E402
from _quelle import koerper, nur_code                    # noqa: E402

import fe.messwerte as M                                 # noqa: E402
import fe.bench as B                                     # noqa: E402

fm = H.fm
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()
TMP = tempfile.mkdtemp(prefix="messwerte_")
_alt = (M.RUECKKEHR_FILE, M.STATUS_FILE, M.MEMINFO_FILE)
M.RUECKKEHR_FILE = os.path.join(TMP, "rueckkehr_zeiten.json")
try:
    # -----------------------------------------------------------------------
    print("Test 1: Speicher lesen")
    # -----------------------------------------------------------------------
    st = os.path.join(TMP, "status")
    with open(st, "w") as f:
        f.write("Name:\tpython3\nVmHWM:\t   90123 kB\nVmRSS:\t   81234 kB\n"
                "RssAnon:\t   70000 kB\nThreads:\t4\n")
    check("belegt, Spitze, eigene Daten",
          M.speicher(st) == {"belegt": 81234, "spitze": 90123,
                             "anonym": 70000}, M.speicher(st))
    mi = os.path.join(TMP, "meminfo")
    with open(mi, "w") as f:
        f.write("MemTotal:  500000 kB\nMemFree:  100000 kB\n"
                "MemAvailable:  300000 kB\n")
    check("Linux gesamt und verfuegbar",
          M.system_speicher(mi) == {"gesamt": 500000, "verfuegbar": 300000})
    check("fehlende Datei: leer statt Fehler",
          M.speicher(os.path.join(TMP, "nix")) == {}
          and M.system_speicher(os.path.join(TMP, "nix")) == {})
    if os.path.exists("/proc/self/status"):
        check("der echte Prozess hat einen Wert",
              M.speicher().get("belegt", 0) > 0, M.speicher())

    # -----------------------------------------------------------------------
    print()
    print("Test 2: die Rueckkehr-Datei")
    # -----------------------------------------------------------------------
    check("ohne Datei: leere Liste", M.rueckkehr_laden() == [])
    for i in range(M.RUECKKEHR_MAX + 5):
        M.rueckkehr_merken({"gesamt_ms": i})
    alle = M.rueckkehr_laden()
    check("nur die letzten %d" % M.RUECKKEHR_MAX,
          [e["gesamt_ms"] for e in alle]
          == list(range(5, M.RUECKKEHR_MAX + 5)))
    check("jede mit Zeitstempel", all("zeit" in e for e in alle))
    check("keine .tmp-Reste", not os.path.exists(M.RUECKKEHR_FILE + ".tmp"))
    with open(M.RUECKKEHR_FILE, "w") as f:
        f.write("{kaputt")
    check("kaputte Datei: leere Liste", M.rueckkehr_laden() == [])
    with open(M.RUECKKEHR_FILE, "w") as f:
        json.dump([{"gesamt_ms": 5}, "Text", {"ohne": 1},
                   {"gesamt_ms": "viel"}], f)
    check("fremde Eintraege fallen weg",
          M.rueckkehr_laden() == [{"gesamt_ms": 5}])
    check("und das Anhaengen danach geht", M.rueckkehr_merken(
        {"gesamt_ms": 7}) and [e["gesamt_ms"] for e in M.rueckkehr_laden()]
        == [5, 7])
    check("Median", M.median([3, 1, 2]) == 2 and M.median([1, 2, 3, 4])
          == 2.5 and M.median([]) is None)
    os.remove(M.RUECKKEHR_FILE)

    # -----------------------------------------------------------------------
    print()
    print("Test 3: run_core() - Rueckkehr gemessen und schneller (Build 344)")
    # -----------------------------------------------------------------------
    fe = H.make_frontend(page=1)
    fe.draw()
    fe.fb.flip()
    kerne = iter(["", "SNES", "SNES", "MENU"])
    letzter = ["SNES"]
    schirm_vorher = [None]
    ereignisse = []

    def cc():
        H.NOW[0] += 0.05
        try:
            letzter[0] = next(kerne)
        except StopIteration:
            pass
        if letzter[0] == "MENU" and schirm_vorher[0] is None:
            schirm_vorher[0] = bytes(fe.fb.mm)
            # waehrend des Spiels hat sich die Auswahl geaendert - das
            # naechste Bild sieht also ANDERS aus als der Schirm, und ein
            # Flip beim Vorzeichnen waere zu sehen
            fe.item_i = 3
        return letzter[0]

    def wge():
        H.NOW[0] += 0.3
        return "pad_combo"

    def nacharbeit(*a, **k):
        H.NOW[0] += 0.3                   # Spielzeit speichern: 300 ms
    meldungen = []
    _sicher = (fm.current_core, fm.launch_core, fm.time.sleep, fm.LOG,
               fm.record_playtime, fm.record_yearly_playtime,
               fm.record_diary_entry, fm.check_hidden_session_achievements)
    _echt_draw = fe.draw
    _echt_grab = fe.inp.grab
    _echt_inject = fe.inp.inject

    def langsam_zeichnen(*a, **k):
        H.NOW[0] += 0.08                  # das erste Bild kostet 80 ms
        erg = _echt_draw(*a, **k)
        ereignisse.append(("draw", schirm_vorher[0] is not None
                           and bytes(fe.fb.mm) == schirm_vorher[0]))
        return erg

    def grab(an):
        ereignisse.append(("grab", an))
        return _echt_grab(an)

    def inject(code, *a, **k):
        ereignisse.append(("inject", code))
        return _echt_inject(code, *a, **k)
    try:
        fm.current_core = cc
        fm.launch_core = lambda p: None
        fm.time.sleep = lambda d: H.NOW.__setitem__(0, H.NOW[0] + d)
        fm.LOG = lambda s: meldungen.append(s)
        fm.record_playtime = nacharbeit
        for n in ("record_yearly_playtime", "record_diary_entry",
                  "check_hidden_session_achievements"):
            setattr(fm, n, lambda *a, **k: None)
        fe.inp.wait_game_exit = wge
        fe.inp.grab = grab
        fe.inp.inject = inject
        fe.draw = langsam_zeichnen
        fe.run_core("/x/spiel.sfc", label="Spiel", syskey="SNES")
    finally:
        (fm.current_core, fm.launch_core, fm.time.sleep, fm.LOG,
         fm.record_playtime, fm.record_yearly_playtime,
         fm.record_diary_entry, fm.check_hidden_session_achievements) = _sicher
        fe.draw = _echt_draw
        fe.inp.grab = _echt_grab
        fe.inp.inject = _echt_inject
    alle = M.rueckkehr_laden()
    e = alle[-1] if alle else {}
    check("eine Messung gemerkt", len(alle) == 1, alle)
    check("Weg: die Pad-Kombination", e.get("weg") == "pad_combo")
    check("die Pause zaehlt ab dem Menue: 300 ms Nacharbeit + 700 ms Rest",
          e.get("nacharbeit_ms") == 300 and e.get("pause_ms") == 700,
          (e.get("nacharbeit_ms"), e.get("pause_ms")))
    check("das erste Bild wurde in der F9-Frist vorgezeichnet",
          e.get("vorgezeichnet_ms") == 80 and e.get("zeichnen_ms") == 0,
          (e.get("vorgezeichnet_ms"), e.get("zeichnen_ms")))
    teile = sum(e.get(k, 0) for k in ("nacharbeit_ms", "pause_ms",
                                      "listen_ms", "konsole_ms",
                                      "zeichnen_ms"))
    check("die Abschnitte ergeben die Gesamtzeit",
          abs(teile - e.get("gesamt_ms", -99)) <= 2, (teile, e.get("gesamt_ms")))
    nach = [x for x in ereignisse]
    i_f9 = max(i for i, x in enumerate(nach) if x[0] == "inject")
    i_draw = [i for i, x in enumerate(nach) if x[0] == "draw"]
    i_grab = max(i for i, x in enumerate(nach) if x == ("grab", True))
    check("Reihenfolge: F9, dann vorzeichnen, dann Pad holen",
          len(i_draw) == 1 and i_f9 < i_draw[0] < i_grab, nach)
    check("beim Vorzeichnen bleibt der Schirm unberuehrt",
          nach[i_draw[0]][1] is True)
    check("danach steht das Bild auf dem Schirm",
          bytes(fe.fb.mm) == bytes(fe.fb.buf))
    check("die Flip-Wege sind wieder frei",
          not any(n in fe.fb.__dict__ for n in
                  ("flip", "flip_rows", "flip_rechtecke")))
    check("ab der Ausstiegs-Taste laenger als ab dem erkannten Menue",
          e.get("ab_ausstieg_ms", 0) > e.get("gesamt_ms", 0), e)
    check("Speicher waehrend des Spiels",
          (e.get("speicher_im_core_kb") or 0) > 0
          or not os.path.exists("/proc/self/status"), e)
    check("eine Logzeile RUECKKEHR",
          any(m.startswith("RUECKKEHR: %d ms" % e.get("gesamt_ms", -1))
              and "Pause 700" in m and "ab der Ausstiegs-Taste" in m
              and "vorgezeichnet 80 ms" in m
              for m in meldungen), [m for m in meldungen if "RUECK" in m])
    check("eine Logzeile SPIEL: Cover-Speicher freigegeben",
          any(m.startswith("SPIEL: Cover-Speicher freigegeben")
              for m in meldungen) or not os.path.exists("/proc/self/status"))

    # -----------------------------------------------------------------------
    print()
    print("Test 3b: geht das Vorzeichnen schief, wird normal gezeichnet")
    # -----------------------------------------------------------------------
    zaehler = [0]

    def zickig(*a, **k):
        zaehler[0] += 1
        if zaehler[0] == 1:
            raise RuntimeError("Cover kaputt")
        return _echt_draw(*a, **k)
    meldungen[:] = []
    try:
        fm.LOG = lambda s: meldungen.append(s)
        fm.time.sleep = lambda d: H.NOW.__setitem__(0, H.NOW[0] + d)
        fe.draw = zickig
        fe.back_to_frontend(vorzeichnen=True)
    finally:
        fm.LOG = _sicher[3]
        fm.time.sleep = _sicher[2]
        fe.draw = _echt_draw
    check("zweimal gezeichnet, Bild auf dem Schirm",
          zaehler[0] == 2 and bytes(fe.fb.mm) == bytes(fe.fb.buf), zaehler)
    check("als nicht vorgezeichnet gemerkt, Meldung im Log",
          fe._btf_vorgezeichnet is False
          and any("Vorzeichnen fehlgeschlagen" in m for m in meldungen))
    check("auch mit Vorzeichnen wird gegen den Login-Gruss nachgefasst",
          abs((fe._f9_aufraeumen_ab or 0) - (H.NOW[0]
              + fm.Frontend.NACHFASSEN_SEK)) < 0.01)
    check("auch dann sind die Flip-Wege wieder frei",
          not any(n in fe.fb.__dict__ for n in
                  ("flip", "flip_rows", "flip_rechtecke")))
    q = open(H.FRONTEND_PY, encoding="utf-8").read()
    btf = nur_code(koerper(q, "back_to_frontend"))
    check("andere Bildgroesse nach der Frist: normal neu zeichnen",
          "_geo == (self.fb.width, self.fb.height," in btf)
    check("ohne vorzeichnen: der alte Weg unveraendert",
          "self.enter_console_mode()\n" in btf)

    # -----------------------------------------------------------------------
    print()
    print("Test 3c: Cover-Speicher fuer das Spiel freigeben")
    # -----------------------------------------------------------------------
    import fe.art as ART_MOD                             # noqa: E402
    ac = ART_MOD.ArtCache.__new__(ART_MOD.ArtCache)
    MB = 1024 * 1024
    ac.cache = {"/a": (10, 10, b"x" * MB), "/b": None,
                "/c": (10, 10, b"x" * (2 * MB))}
    ac.order = ["/a", "/b", "/c"]
    ac.nativ = {"/a": (20, 20), "/c": (10, 10)}
    ac._voll = {"/c"}
    ac._original_bytes = 3 * MB
    ac.scaled = {}
    ac.scaled_order = []
    for i in range(10):
        k = ("/s%d" % i, "box", 100, 100)
        ac.scaled[k] = (100, 100, b"y" * MB)
        ac.scaled_order.append(k)
    ac.scaled_order.append(("/s3", "box", 100, 100))     # spaeter benutzt
    ac.scaled_bytes = 10 * MB
    frei = ac.fuer_spiel_freigeben(behalten=4 * MB)
    check("Originale mit Bild weg, 'kein Cover' bleibt",
          ac.cache == {"/b": None} and ac.order == ["/b"]
          and not ac.nativ and not ac._voll and ac._original_bytes == 0)
    check("die juengsten Miniaturen bleiben, bis zum Budget",
          [k[0] for k in ac.scaled_order] == ["/s7", "/s8", "/s9", "/s3"]
          and set(ac.scaled) == set(ac.scaled_order), ac.scaled_order)
    check("Zaehler stimmt, freigegeben stimmt",
          ac.scaled_bytes == 4 * MB and frei == 3 * MB + 6 * MB,
          (ac.scaled_bytes, frei))
    ac2 = ART_MOD.ArtCache.__new__(ART_MOD.ArtCache)
    ac2.cache, ac2.order, ac2.nativ, ac2._voll = {}, [], {}, set()
    ac2._original_bytes = 0
    ac2.scaled = {("/gross", "box", 1, 1): (1, 1, b"z" * (8 * MB))}
    ac2.scaled_order = [("/gross", "box", 1, 1)]
    ac2.scaled_bytes = 8 * MB
    ac2.fuer_spiel_freigeben(behalten=4 * MB)
    check("die juengste bleibt immer, auch ueber dem Budget",
          list(ac2.scaled) == [("/gross", "box", 1, 1)])
    check("Linux bekommt den Speicher zurueck (oder es passiert nichts)",
          M.speicher_zurueckgeben() in (True, False))
    _echt_frei = fm.ART.fuer_spiel_freigeben
    meldungen[:] = []
    try:
        def boom2(*a, **k):
            raise MemoryError("kaputt")
        fm.ART.fuer_spiel_freigeben = boom2
        fm.LOG = lambda s: meldungen.append(s)
        r = fe._speicher_fuer_spiel()
    finally:
        fm.ART.fuer_spiel_freigeben = _echt_frei
        fm.LOG = _sicher[3]
    check("ein Fehler haelt das Spiel nicht auf",
          r == 0 and any("fehlgeschlagen" in m for m in meldungen))
    rc = nur_code(koerper(q, "run_core"))
    check("freigegeben wird NACH launch_core(), vor dem Warten auf den Core",
          rc.find("launch_core(path)") < rc.find("self._speicher_fuer_spiel()")
          < rc.find("started = False"))

    # -----------------------------------------------------------------------
    print()
    print("Test 4: eine kaputte Messung stoert nicht")
    # -----------------------------------------------------------------------
    _echt_merken = M.rueckkehr_merken
    try:
        def boom(*a, **k):
            raise RuntimeError("Karte voll")
        M.rueckkehr_merken = boom
        meldungen[:] = []
        fm.LOG = lambda s: meldungen.append(s)
        try:
            r = fe._rueckkehr_merken(H.NOW[0] - 2, H.NOW[0] - 1.5,
                                     H.NOW[0] - 0.5, H.NOW[0] - 0.2,
                                     "menu", None, None)
            ok = True
        except Exception:                                # noqa: BLE001
            ok = False
            r = None
    finally:
        M.rueckkehr_merken = _echt_merken
        fm.LOG = _sicher[3]
    check("kein Fehler nach aussen, Meldung im Log",
          ok and r is None
          and any("Messung fehlgeschlagen" in m for m in meldungen))
    check("die Pause bleibt eine Sekunde, gezaehlt ab dem Menue",
          fm.Frontend.RUECKKEHR_PAUSE == 1.0
          and "self.RUECKKEHR_PAUSE - (_rk_pause - _rk_menue)" in rc)
    check("gemessen wird NACH back_to_frontend()",
          rc.find("self._rueckkehr_merken(")
          > rc.find("self.back_to_frontend(vorzeichnen=True)"))
    import re                                            # noqa: E402
    check("nach der Ausstiegs-Taste alle 0,1 s nach dem Menue sehen",
          re.search(r"time\.monotonic\(\) - t1 < 10:\n\s*time\.sleep\(0\.1\)",
                    rc) is not None)
    import fe.input as I                                 # noqa: E402
    wg = nur_code(koerper(open(I.__file__, encoding="utf-8").read(),
                          "wait_game_exit"))
    check("waehrend des Spiels alle 0,2 s nach dem Menue sehen",
          I.InputManager.KERN_PRUEF_TAKT == 0.2
          and "self.KERN_PRUEF_TAKT" in wg and "> 0.7" not in wg)

    # -----------------------------------------------------------------------
    print()
    print("Test 5: der Bench")
    # -----------------------------------------------------------------------
    check("Bench-Nummer 26", B.BENCH_VERSION >= 26, B.BENCH_VERSION)
    import threading                                     # noqa: E402
    echt = (os.listdir, os.stat, os.lstat, os.scandir)
    uhr = B._FsUhr()
    with uhr:
        os.listdir(TMP)
        os.path.exists(TMP)
        with os.scandir(TMP) as it:
            list(it)
        anzahl_eigen = uhr.je.get(0, [0, 0, []])[1]
        fremd = threading.Thread(target=lambda: [os.listdir("/")
                                                 for _ in range(50)])
        fremd.start()
        fremd.join()
    gebucht = uhr.je.get(0, [0, 0, []])[1]
    check("P stoppt den eigenen Faden, den fremden nicht",
          anzahl_eigen >= 3 and gebucht == anzahl_eigen,
          (anzahl_eigen, gebucht))
    check("P gibt os danach wieder frei",
          (os.listdir, os.stat, os.lstat, os.scandir) == echt)
    p_quelle = open(B.__file__, encoding="utf-8").read()
    check("P schluesselt den laengsten Happen auf und wartet die "
          "Vorarbeit ab",
          "2b) die drei laengsten Happen" in p_quelle
          and "_va.warten(hoechstens=15.0)" in p_quelle)
    lauf = nur_code(koerper(open(B.__file__, encoding="utf-8").read(), "lauf"))
    check("R, S, T laufen, T als letztes",
          lauf.find("_abschnitt_r(") < lauf.find("_abschnitt_s(")
          < lauf.find("_abschnitt_t(") and lauf.find("_abschnitt_q(")
          < lauf.find("_abschnitt_r("))
    os.remove(M.RUECKKEHR_FILE)
    zeilen = []
    B._abschnitt_s(zeilen.append)
    text = " ".join(" ".join(zeilen).split())
    check("S ohne Messung sagt, was zu tun ist",
          "noch keine Messung" in text and "Spiel starten und beenden" in text,
          zeilen)
    zeilen = []
    B._abschnitt_t(zeilen.append, fe, M.speicher())
    if os.path.exists("/proc/self/status"):
        check("T nennt den belegten Speicher und die fehlende Spielmessung",
              any("belegt jetzt" in z for z in zeilen)
              and any("noch keine Messung" in z for z in zeilen), zeilen)
    M.rueckkehr_merken({"gesamt_ms": 1400, "pause_ms": 1000, "weg": "menu",
                        "speicher_im_core_kb": 60000})
    M.rueckkehr_merken({"gesamt_ms": 1600, "pause_ms": 1000,
                        "weg": "hid_combo", "ab_ausstieg_ms": 2500})
    zeilen = []
    B._abschnitt_s(zeilen.append)
    check("S: Median und Zeit ab der Taste",
          any("Median" in z and "1500" in z for z in zeilen)
          and any("Ausstiegs-Taste" in z and "2500" in z for z in zeilen),
          zeilen)
    zeilen = []
    B._abschnitt_t(zeilen.append, fe, M.speicher())
    check("T: Speicher waehrend des Spiels aus der Datei",
          any("waehrend eines Spiels" in z and "58.6 MB" in z
              for z in zeilen), zeilen)
    fe.page, fe.cat_i, fe.item_i = 0, 0, 0
    zeilen = []
    B._abschnitt_r(zeilen.append, fe, None)
    check("R misst die groesste Kategorie, drei Zahlen",
          sum(1 for z in zeilen if z.rstrip().endswith(" ms")) == 3, zeilen)
    check("R stellt Seite und Auswahl wieder her",
          (fe.page, fe.cat_i, fe.item_i) == (0, 0, 0))
finally:
    (M.RUECKKEHR_FILE, M.STATUS_FILE, M.MEMINFO_FILE) = _alt
    shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
