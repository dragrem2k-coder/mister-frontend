#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Spielelisten-Cache, je System lesbar (Build 248).

WARUM ES DIESE DATEI GIBT, und das ist der unangenehmste Teil:

scan_games() baut die KOMPLETTE Spieleliste - die Funktion, ohne die
das Frontend nichts anzeigt. Und **kein einziger Test hat sie je
aufgerufen.** Build 248 hat ihre drei Cache-Helfer umgebaut
(_cache_kopf_lesen, _cache_systeme_lesen, _cache_schreiben), die
Aufrufstellen geaendert - und die Funktionen selbst nie geschrieben.
Das Ergebnis war ein NameError beim ersten Aufruf, also ein Frontend
ohne Spieleliste. Gefunden hat es niemand, weil niemand hinsah.

Test 1 ist deshalb der wichtigste in dieser Datei: **scan_games()
laeuft ueberhaupt.** Alles andere darf scheitern, dieser nicht.

Der Rest prueft, woran das neue Format scheitern kann:

  2. Hin und zurueck: geschrieben ist nicht gelesen.
  3. nur= liest WIRKLICH nur die verlangten Systeme - sonst ist der
     ganze Umbau sinnlos.
  4. Die ALTE Datei (alles in einem Stueck) wird weiter gelesen. Ohne
     diesen Rueckfall haette jeder vorhandene Nutzer nach dem Update
     einen vollen Scan - bei 30.000 Spielen Minuten, fuer nichts.
  5. Eine halbe oder beschaedigte Datei wird nicht als gueltig
     gelesen, und der Fehler ist einer, den scan_games() faengt.
  6. Ein abgebrochener Schreibvorgang hinterlaesst keine .tmp-Leiche
     und keine halbe Cache-Datei.

Ausfuehren:
    python3 tools/test_scan_cache.py
"""
import io
import os
import pickle
import shutil
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H                                        # noqa: E402

import fe.scan as S                                         # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def _knoten(n, praefix):
    """Ein Knoten in genau der Form, die _scan_games_disk() erzeugt."""
    return {"items": [("%s %03d" % (praefix, i), "game",
                       ("/media/fat/games/%s/%s %03d.rom"
                        % (praefix, praefix, i), ".rom", praefix,
                        None, None))
                      for i in range(n)],
            "dirs": {}}


CATS = [("Nintendo Entertainment System", _knoten(40, "NES"), "NES"),
        ("Super Nintendo", _knoten(25, "SNES"), "SNES"),
        ("Mega Drive", _knoten(10, "MD"), "MD")]
SIG = "sig-abc"
PER_SK = {"NES": "n1", "SNES": "s1", "MD": "m1"}


class _Ordner(object):
    """Cache-Pfade in einen eigenen Ordner umbiegen - unter keinen
    Umstaenden /media/fat anfassen."""

    def __enter__(self):
        self.d = tempfile.mkdtemp(prefix="scancache_")
        self.alt = (S.GAMES_CACHE, S.GAMES_CACHE_OLD_JSON)
        S.GAMES_CACHE = os.path.join(self.d, "games_cache.pkl")
        S.GAMES_CACHE_OLD_JSON = os.path.join(self.d, "games_cache.json")
        return self

    def __exit__(self, *a):
        S.GAMES_CACHE, S.GAMES_CACHE_OLD_JSON = self.alt
        shutil.rmtree(self.d, ignore_errors=True)
        return False


# ---------------------------------------------------------------------------
print("Test 1: scan_games() laeuft ueberhaupt")
# ---------------------------------------------------------------------------
# DER TEST, DER GEFEHLT HAT. Build 248 hat drei Funktionen gerufen, die
# es nicht gab - NameError beim ersten Aufruf, kein Frontend. Diese
# Pruefung ist billig und haette es sofort gefunden.
with _Ordner():
    try:
        erg = S.scan_games()
        lief, fehler = True, ""
    except Exception as e:                                   # noqa: BLE001
        erg, lief, fehler = None, False, "%s: %s" % (type(e).__name__, e)
    check("ohne Cache-Datei laeuft sie durch", lief, fehler)
    check("und liefert eine Liste", isinstance(erg, list), type(erg).__name__)
    # Und ein zweites Mal, jetzt mit der eben geschriebenen Datei.
    try:
        erg2 = S.scan_games()
        lief2, fehler2 = True, ""
    except Exception as e:                                   # noqa: BLE001
        erg2, lief2, fehler2 = None, False, "%s: %s" % (type(e).__name__, e)
    check("und ein zweites Mal, jetzt MIT Cache-Datei", lief2, fehler2)

# ---------------------------------------------------------------------------
print()
print("Test 2: hin und zurueck")
# ---------------------------------------------------------------------------
with _Ordner():
    S._cache_schreiben(SIG, PER_SK, CATS)
    check("die Datei ist da", os.path.exists(S.GAMES_CACHE))
    check("und keine .tmp-Leiche daneben",
          not [n for n in os.listdir(os.path.dirname(S.GAMES_CACHE))
               if ".tmp" in n])
    sig, per_sk, handle = S._cache_kopf_lesen()
    check("die Signatur kommt zurueck", sig == SIG, str(sig))
    check("per_syskey auch", per_sk == PER_SK, str(per_sk))
    check("der Kopf enthaelt noch KEINEN Baum",
          handle[0] == "neu" and isinstance(handle[2], list)
          and all(isinstance(e[2], int) for e in handle[2]),
          "nur Anzeigename, Kuerzel, Offset und Laenge - genau darum "
          "geht der ganze Umbau")
    zurueck = S._cache_systeme_lesen(handle)
    check("alle drei Systeme kommen wieder", len(zurueck) == 3,
          str(len(zurueck)))
    check("Anzeigenamen und Kuerzel stimmen",
          [(d, sk) for d, _n, sk in zurueck]
          == [(d, sk) for d, _n, sk in CATS])
    check("und die Knoten sind inhaltlich gleich",
          [n for _d, n, _sk in zurueck] == [n for _d, n, _sk in CATS],
          "sonst stehen nach einem Neustart andere Spiele da")
    check("die Reihenfolge der Datei bleibt",
          [sk for _d, _n, sk in zurueck] == ["NES", "SNES", "MD"])

# ---------------------------------------------------------------------------
print()
print("Test 3: nur= liest wirklich nur die verlangten Systeme")
# ---------------------------------------------------------------------------
with _Ordner():
    S._cache_schreiben(SIG, PER_SK, CATS)
    _sig, _psk, handle = S._cache_kopf_lesen()
    teil = S._cache_systeme_lesen(handle, nur={"SNES", "MD"})
    check("zwei von drei", len(teil) == 2, str(len(teil)))
    check("und zwar die richtigen",
          sorted(sk for _d, _n, sk in teil) == ["MD", "SNES"])
    check("das ausgelassene System ist NICHT dabei",
          "NES" not in [sk for _d, _n, sk in teil],
          "sonst liegt es doppelt im Speicher, nur um weggeworfen zu "
          "werden")
    leer = S._cache_systeme_lesen(handle, nur=set())
    check("eine leere Menge liefert nichts", leer == [], str(leer))
    check("nur= mit unbekanntem Kuerzel liefert nichts",
          S._cache_systeme_lesen(handle, nur={"GIBTESNICHT"}) == [])
    # Und die Gegenprobe: nur= zaehlt die GELESENEN Bytes herunter.
    ganz_bytes = sum(e[3] for e in handle[2])
    teil_bytes = sum(e[3] for e in handle[2] if e[1] in ("SNES", "MD"))
    check("die gelesene Datenmenge sinkt messbar",
          teil_bytes < ganz_bytes * 0.8,
          "%d von %d Byte" % (teil_bytes, ganz_bytes))

# ---------------------------------------------------------------------------
print()
print("Test 4: die ALTE Datei wird weiter gelesen")
# ---------------------------------------------------------------------------
with _Ordner():
    # Genau das Format vor Build 248: alles in einem Stueck.
    with io.open(S.GAMES_CACHE, "wb") as f:
        pickle.dump({"sig": SIG, "per_syskey": PER_SK, "cats": CATS}, f)
    sig, per_sk, handle = S._cache_kopf_lesen()
    check("die Signatur kommt auch daraus", sig == SIG)
    check("und sie wird als alte Fassung erkannt", handle[0] == "alt",
          str(handle[0]))
    alles = S._cache_systeme_lesen(handle)
    check("alle Systeme kommen wieder", len(alles) == 3, str(len(alles)))
    check("nur= funktioniert auch auf der alten Fassung",
          sorted(sk for _d, _n, sk
                 in S._cache_systeme_lesen(handle, nur={"NES"})) == ["NES"],
          "sonst nimmt der inkrementelle Rescan beim ersten Lauf nach "
          "dem Update den teuren Weg")
    # Nach einem Schreiben ist die alte Fassung weg.
    S._cache_schreiben(SIG, PER_SK, CATS)
    _s, _p, h2 = S._cache_kopf_lesen()
    check("das erste Schreiben stellt auf die neue Fassung um",
          h2[0] == "neu", str(h2[0]))

# ---------------------------------------------------------------------------
print()
print("Test 5: beschaedigte Dateien gelten nicht als gueltig")
# ---------------------------------------------------------------------------
_FAENGT = (OSError, ValueError, KeyError, IndexError, TypeError,
           pickle.UnpicklingError, EOFError, AttributeError)


def _versuch(bauen, label):
    """bauen() legt eine kaputte Datei an; geprueft wird, dass
    _cache_kopf_lesen() eine Ausnahme wirft, die scan_games() auch
    faengt. Ein NameError oder struct.error waere genau der Fall, der
    bis Build 247 durchgeschlagen ist."""
    with _Ordner():
        bauen()
        try:
            S._cache_kopf_lesen()
        except _FAENGT as e:
            check(label, True, type(e).__name__)
            return
        except Exception as e:                               # noqa: BLE001
            check(label, False,
                  "%s - scan_games() faengt die NICHT"
                  % type(e).__name__)
            return
    check(label, False, "kein Fehler - die halbe Datei galt als gueltig")


_versuch(lambda: io.open(S.GAMES_CACHE, "wb").write(b""),
         "leere Datei")
_versuch(lambda: io.open(S.GAMES_CACHE, "wb").write(b"\x00" * 4),
         "vier Nullbytes")
_versuch(lambda: io.open(S.GAMES_CACHE, "wb").write(
             b"Kein Pickle, nur Text" + struct.pack("<Q", 3)),
         "Unfug mit gueltigem Zeiger-Feld")


def _abgeschnitten():
    S._cache_schreiben(SIG, PER_SK, CATS)
    roh = io.open(S.GAMES_CACHE, "rb").read()
    io.open(S.GAMES_CACHE, "wb").write(roh[:len(roh) // 2])


_versuch(_abgeschnitten, "in der Mitte abgeschnitten")


def _zeiger_verbogen():
    S._cache_schreiben(SIG, PER_SK, CATS)
    roh = bytearray(io.open(S.GAMES_CACHE, "rb").read())
    roh[-8:] = struct.pack("<Q", 2 ** 40)      # weit hinter dem Ende
    io.open(S.GAMES_CACHE, "wb").write(bytes(roh))


_versuch(_zeiger_verbogen, "Zeiger hinter das Dateiende verbogen")

# ---------------------------------------------------------------------------
print()
print("Test 6: ein abgebrochener Schreibvorgang hinterlaesst nichts")
# ---------------------------------------------------------------------------
with _Ordner():
    S._cache_schreiben(SIG, PER_SK, CATS)
    gut = io.open(S.GAMES_CACHE, "rb").read()

    class _Boese(object):
        """Ein Knoten, an dem pickle scheitert - so sieht ein
        abgebrochener Schreibvorgang von innen aus."""

        def __reduce__(self):
            raise RuntimeError("Karte voll")

    try:
        S._cache_schreiben("neu", PER_SK,
                           [("Kaputt", _Boese(), "X")])
        geflogen = False
    except Exception:                                        # noqa: BLE001
        geflogen = True
    check("der Fehler wird nach oben gegeben", geflogen,
          "scan_games() faengt ihn dort ab und laeuft ohne Cache weiter")
    check("die GUTE Datei steht unveraendert da",
          io.open(S.GAMES_CACHE, "rb").read() == gut,
          "os.replace() ist der Grund - erst die .tmp, dann tauschen")
    check("und keine .tmp-Leiche bleibt liegen",
          not [n for n in os.listdir(os.path.dirname(S.GAMES_CACHE))
               if ".tmp" in n],
          str([n for n in os.listdir(os.path.dirname(S.GAMES_CACHE))]))

# ---------------------------------------------------------------------------
print()
print("Test 7: die Aufrufstellen passen zu den Funktionen")
# ---------------------------------------------------------------------------
# GENAU HIER LAG DER FEHLER: die Aufrufstellen waren umgebaut, die
# Funktionen fehlten. Eine Pruefung, die beides vergleicht, faengt das
# auch dann, wenn wieder niemand scan_games() aufruft.
_q = io.open(os.path.join(_REPO, "frontend", "fe", "scan.py"),
             encoding="utf-8").read()
for name in ("_cache_kopf_lesen", "_cache_systeme_lesen",
             "_cache_schreiben"):
    check("%s ist definiert, nicht nur gerufen" % name,
          ("def %s(" % name) in _q and callable(getattr(S, name, None)))
check("der alte Direktzugriff auf data['cats'] ist weg",
      'data["cats"]' not in _q,
      "er hat den ganzen Baum gebaut, bevor die Signatur gepruefft war")
check("der alte Baum wird vor dem vollen Scan freigegeben",
      "data = None\n        cached_per_syskey = None\n"
      "        cats = _scan_games_disk(progress_cb)" in _q,
      "das ist die groesste Einzelersparnis am Speicher - 36 % der "
      "Spitze bei 50.000 Eintraegen")
check("der inkrementelle Zweig liest nur die unveraenderten Systeme",
      "nur=(all_syskeys - changed_syskeys)" in _q,
      "die geaenderten sind gerade frisch eingelesen worden")

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
