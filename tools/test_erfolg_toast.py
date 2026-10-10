#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Erfolgs-Einblendung im OBS-Overlay (Build 252).

Drei Dinge, alle im Overlay und KEINE Aenderung an der Datenleitung -
dasselbe Ereignis wie bisher, dieselben Felder. Das Overlay laeuft
damit unveraendert mit jedem Frontend, und man kann es im Browser
ansehen, ohne das Frontend neu zu starten.

  1. DER EINBLEND-MOMENT. Vorher nur opacity plus 20 Punkte von
     rechts - eine Benachrichtigung, kein Moment. Jetzt: Zurueckfedern
     statt linearem Ankommen, das Badge dreht sich einmal aus der
     Tiefe herein, ein Lichtstreifen laeuft quer ueber die Karte.
  2. DIE PUNKTE ZAEHLEN HOCH, von 0 auf den Wert in 600 ms. Die Zahl
     steht schon im Ereignis; sie heraufzuzaehlen zieht das Auge
     dorthin, wo sie steht.
  3. MEHRERE ERFOLGE HINTEREINANDER. Der zweite Toast ueberschrieb den
     ersten und setzte den Timer neu - bei einem Erfolgs-Schub sah man
     EINEN davon. Jetzt eine Warteschlange, und daneben steht, wie
     viele noch warten.

WARUM DIESER TEST KEINEN BROWSER BRAUCHT. Das Overlay ist eine einzige
HTML-Datei ohne Fremdpakete; geprueft wird deshalb ihr Inhalt - und das
JavaScript wird mit node auf Syntax geprueft, falls node da ist. Ein
echter Browsertest waere ein Fremdpaket und eine zweite Baustelle fuer
etwas, das in drei Funktionen passt.

WORAN ES SCHEITERN KANN

  1. Der zweite Toast loest keine Animation aus, weil die Klasse
     "show" schon dran ist. Das ist der klassische Fehler bei
     CSS-Animationen, und das Projekt hat ihn bei der "flash"-Klasse
     der Hauptkarte schon einmal geloest.
  2. Die Warteschlange laeuft voll und blockiert das Overlay
     minutenlang.
  3. Der Zaehler zeigt "0 Punkte" bei einem Erfolg ohne Punktangabe.
  4. Der Admin-Schalter show_ra_badges wirkt nicht mehr.
  5. Wer "weniger Bewegung" eingestellt hat, bekommt sie trotzdem.

Ausfuehren:
    python3 tools/test_erfolg_toast.py
"""
import io
import os
import re
import shutil
import subprocess
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
_HTML = os.path.join(_REPO, "frontend", "stream_overlay.html")
_Q = io.open(_HTML, encoding="utf-8").read()
_JS = _Q.split("<script>")[1].split("</script>")[0]
_CSS = _Q.split("<style>")[1].split("</style>")[0]
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


# ---------------------------------------------------------------------------
print("Test 1: das JavaScript ist syntaktisch in Ordnung")
# ---------------------------------------------------------------------------
# DER EINE FEHLER, DER ALLES KOSTET: ein Tippfehler im Skript, und das
# Overlay bleibt schwarz - ohne Meldung, denn in OBS sieht niemand die
# Browser-Konsole. Geprueft wird mit node, falls es da ist.
_node = shutil.which("node") or shutil.which("nodejs")
if _node:
    _hilfs = os.path.join(_HIER, "__erfolg_toast_pruefung.js")
    try:
        io.open(_hilfs, "w", encoding="utf-8").write(
            "const fs=require('fs');\n"
            "const s=fs.readFileSync(process.argv[2],'utf8');\n"
            "const js=s.split('<script>')[1].split('</script>')[0];\n"
            "new Function(js);\n")
        _p = subprocess.run([_node, _hilfs, _HTML],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        check("node liest das Skript ohne Fehler", _p.returncode == 0,
              _p.stderr.decode("utf-8", "replace").strip()[:200])
    finally:
        try:
            os.remove(_hilfs)
        except OSError:
            pass
else:
    print("  --   node fehlt, Syntaxpruefung uebersprungen")
# Die grobe Gegenprobe geht immer: Klammern muessen aufgehen.
for _a, _b, _name in (("{", "}", "geschweifte"), ("(", ")", "runde")):
    check("%s Klammern gehen auf" % _name,
          _JS.count(_a) == _JS.count(_b),
          "%d auf, %d zu" % (_JS.count(_a), _JS.count(_b)))

# ---------------------------------------------------------------------------
print()
print("Test 2: die Warteschlange")
# ---------------------------------------------------------------------------
check("es gibt eine", "achQueue" in _JS and "achQueue.push(" in _JS)
check("und sie wird abgearbeitet",
      "achQueue.shift()" in _JS and "achNaechster" in _JS)
check("mit einer Obergrenze",
      "ACH_SCHLANGE_MAX" in _JS and "achQueue.slice(-ACH_SCHLANGE_MAX)" in _JS,
      "ein Spiel, das hundert Ereignisse schickt, darf das Overlay "
      "nicht minutenlang blockieren")
check("und die NEUESTEN bleiben drin",
      "slice(-ACH_SCHLANGE_MAX)" in _JS,
      "was gerade passiert ist, ist das Interessantere")
check("die Zahl der wartenden steht daneben",
      "achievement-rest" in _JS and "achQueue.length" in _JS)
check("und verschwindet, wenn keine mehr warten",
      "rest.classList.add('hidden')" in _JS)
# Die Pause zwischen zwei Toasts muss laenger sein als das Ausblenden,
# sonst laufen sie ineinander.
_m = re.search(r"ACH_LUECKE\s*=\s*(\d+)", _JS)
check("es gibt eine Pause zwischen zwei Toasts", bool(_m),
      _m.group(1) + " ms" if _m else "")
_aus = re.search(r"#achievement-toast\.show\{\s*transition:opacity \.(\d+)s",
                 _CSS)
if _m and _aus:
    _luecke = int(_m.group(1))
    # ".28s" sind 280 ms, nicht 2800. Der erste Entwurf hat die
    # Nachkommastellen als ganze Zahl genommen und mit 100
    # multipliziert - und meldete prompt "420 ms Pause gegen 2800 ms
    # Ausblenden" als Fehler. Die Zusage stimmte, die Rechnung nicht.
    _ausblenden = float("0." + _aus.group(1)) * 1000.0
    check("und sie ist laenger als das Ausblenden",
          _luecke > _ausblenden,
          "%d ms Pause gegen %.0f ms Ausblenden" % (_luecke, _ausblenden))

# ---------------------------------------------------------------------------
print()
print("Test 3: der zweite Toast loest wirklich eine Animation aus")
# ---------------------------------------------------------------------------
# DER KLASSISCHE FEHLER BEI CSS-ANIMATIONEN: die Klasse ist schon dran,
# also passiert beim zweiten Mal nichts. Das Projekt hat ihn bei der
# "flash"-Klasse der Hauptkarte schon einmal geloest - derselbe Weg.
_fn = _JS.split("function achNaechster(){")[1].split("\nfunction ")[0]
check("die Klasse wird vorher entfernt",
      "toast.classList.remove('show')" in _fn)
check("mit erzwungenem Neuberechnen dazwischen",
      "void toast.offsetWidth" in _fn,
      "ohne das wendet der Browser die Aenderung nicht an, und beim "
      "zweiten Erfolg laeuft keine Animation")
check("und erst danach wieder gesetzt",
      _fn.index("toast.classList.remove('show')")
      < _fn.index("void toast.offsetWidth")
      < _fn.index("toast.classList.add('show')"))

# ---------------------------------------------------------------------------
print()
print("Test 4: die Punkte zaehlen hoch")
# ---------------------------------------------------------------------------
check("es gibt einen Zaehler", "function punkteHochzaehlen(" in _JS)
check("er laeuft ueber requestAnimationFrame",
      "requestAnimationFrame(" in _JS,
      "nicht ueber setInterval - sonst haengt die Zahl an der "
      "Bildrate des Browsers vorbei")
check("ein laufender Zaehler wird abgebrochen",
      "cancelAnimationFrame(" in _JS,
      "sonst zaehlen bei zwei Erfolgen zwei Zaehler gegeneinander")
_pz = _JS.split("function punkteHochzaehlen(")[1].split("\nfunction ")[0]
check("ohne Punktangabe steht nichts da",
      "el.textContent = punkte ? (punkte + ' Punkte') : '';" in _pz,
      "eine 0 waere eine Angabe, die es nicht gibt")
check("bei wenigen Punkten wird nicht gezaehlt",
      "ziel <= 3" in _pz,
      "ein Sprung von 0 auf 2 sieht nach einem Fehler aus")
check("am Ende steht genau der Zielwert",
      "el.textContent = ziel + ' Punkte'" in _pz,
      "nicht der gerundete Zwischenwert des letzten Bildes")
check("und er wird langsamer statt abgeschnitten",
      "Math.pow(1 - t, 3)" in _pz)

# ---------------------------------------------------------------------------
print()
print("Test 5: der Einblend-Moment steht im CSS")
# ---------------------------------------------------------------------------
check("das Badge dreht sich herein", "@keyframes badge-in" in _CSS)
check("ein Lichtstreifen laeuft quer", "@keyframes sheen" in _CSS)
check("und die Karte federt zurueck",
      "cubic-bezier(.17,.89,.32,1.28)" in _CSS,
      "der vierte Wert ueber 1 ist der Ueberschwinger")
check("der Lichtstreifen faengt keine Klicks ab",
      "pointer-events:none" in _CSS.split("#achievement-toast::after")[1][:300],
      "das Overlay liegt ueber dem Bild und darf nichts abfangen")

# ---------------------------------------------------------------------------
print()
print("Test 6: was NICHT kaputtgehen durfte")
# ---------------------------------------------------------------------------
check("der Admin-Schalter wirkt weiterhin",
      "cfg.show_ra_badges === false) return;" in _JS,
      "Standard AN, wie bei den anderen show_*-Optionen")
check("und zwar BEVOR etwas in die Schlange kommt",
      _JS.index("cfg.show_ra_badges === false) return;")
      < _JS.index("achQueue.push("),
      "sonst sammelt sich eine Schlange an, die niemand sieht - und "
      "beim Einschalten kaeme alles auf einmal")
check("das Badge kommt weiter vom eigenen Server",
      "'/badge?name=' + encodeURIComponent(data.badge)" in _JS,
      "nicht direkt von retroachievements.org - der Cache liegt bei uns")
check("ohne Badge wird das Bild versteckt",
      "badge.classList.add('hidden')" in _JS)
check("die Felder heissen unveraendert title/description/points/badge",
      all(("data." + f) in _JS
          for f in ("title", "description", "points", "badge")),
      "keine Aenderung an der Datenleitung - das Overlay laeuft mit "
      "jedem bestehenden Frontend")
check("die tote Variable von vorher ist weg",
      "achievementTimer" not in _JS,
      "eine Variable, die niemand liest, sieht beim naechsten Lesen "
      "nach einem vergessenen Weg aus")
check("wer weniger Bewegung will, bekommt sie nicht",
      "prefers-reduced-motion" in _CSS)

# ---------------------------------------------------------------------------
print()
print("Test 7: die Gegenstelle ist unveraendert")
# ---------------------------------------------------------------------------
# Wenn hier etwas rot wird, ist die Zusage "keine Aenderung an der
# Datenleitung" verletzt.
_srv = io.open(os.path.join(_REPO, "frontend", "stream_server.py"),
               encoding="utf-8").read()
check("publish_achievement() schickt weiterhin denselben Ereignistyp",
      'event: achievement\\ndata: ' in _srv)
_fe = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8").read()
check("und das Frontend schickt dieselben vier Felder",
      '"title": name, "description": desc,' in _fe
      and '"points": points, "badge": badge,' in _fe)

# ---------------------------------------------------------------------------
print()
print("Test 8: die Einblendung hat eine eigene Ecke (Build 255)")
# ---------------------------------------------------------------------------
# Nutzerwunsch: "erfolgseinblendung sollte auch frei waehlbar sein wo es
# angezeigt wird". Bis Build 254 stand der Toast FEST oben rechts -
# bewusst, damit er sich nie mit der Auswahl-Karte ueberschneiden kann,
# egal welche Ecke dort gewaehlt ist. Diese Zusage faellt jetzt
# teilweise: wer beide in dieselbe Ecke legt, darf das. Die VORGABE
# bleibt oben rechts, also merkt niemand etwas, der den Schalter nie
# anfasst - und genau das prueft die erste Zeile.
import sys as _sys2                                        # noqa: E402
_sys2.path.insert(0, os.path.join(_REPO, "frontend"))
from stream_server import DEFAULT_CONFIG as _DC            # noqa: E402

check("es gibt den Schalter", "ach_corner" in _DC)
check("und die Vorgabe ist die alte Ecke",
      _DC.get("ach_corner") == "top-right",
      "sonst springt die Einblendung bei allen, die nie etwas "
      "eingestellt haben")
for _e in ("top-right", "top-left", "bottom-right", "bottom-left"):
    check("%-13s hat eine Regel im Stylesheet" % _e,
          ("#achievement-toast.ach-%s{" % _e) in _CSS)
check("links kommt er auch von LINKS herein",
      "translateX(calc(-20px*var(--scale)))" in _CSS,
      "sonst zeigt die Karte in die falsche Richtung")
check("und der Farbbalken wandert an die linke Kante",
      "border-left:calc(4px*var(--scale)) solid #ffd452" in _CSS)
check("die Ecke wird ueber classList gesetzt, nicht ueber className",
      "toast.classList.toggle('ach-'" in _JS
      and "$('achievement-toast').className =" not in _JS,
      "auf demselben Element sitzt 'show' - ein className-Zuweisen "
      "mitten in einer laufenden Einblendung bricht sie ab")
check("und zwar schon beim Config-Paket",
      "toast.classList.toggle('ach-'"
      in _JS.split("function applyConfig(c){")[1].split("\nfunction ")[0],
      "sonst steht die Ecke erst beim ersten Erfolg")

# DAS AUSWEICHEN VOR DER WAND. Bis 254 galt es pauschal: lag die Wand
# oben rechts, rutschte der Toast nach unten - er stand ja immer dort.
# Jetzt haben beide eine eigene Ecke, also darf nur noch die GLEICHE
# Paarung ausweichen, sonst nimmt eine Regel dem Nutzer seine Wahl weg.
_weich = [z for z in _CSS.split("\n") if "~ #achievement-toast" in z]
check("das Ausweichen gilt nur bei GLEICHER Ecke",
      bool(_weich) and all(".ach-" in z for z in _weich),
      str(_weich[:2]))
check("und nur, wenn die Wand ueberhaupt angezeigt wird",
      all("#ra-wall.on." in z for z in _weich),
      "eine Wand, die aus ist, darf den Toast nicht verschieben")

_AD = io.open(os.path.join(_REPO, "frontend", "stream_admin.html"),
              encoding="utf-8").read()
check("im Backend: Feldliste",
      '"ach_corner"' in _AD.split("const F = [")[1].split("]")[0])
check("im Backend: geladen", '$("ach_corner").value = c.ach_corner' in _AD)
check("im Backend: gespeichert",
      "ach_corner:" in _AD.split("  return {")[1].split("};")[0])
check("im Backend: vier Ecken zur Wahl",
      _AD.split('id="ach_corner"')[1].split("</select>")[0].count(
          "<option") == 4)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
