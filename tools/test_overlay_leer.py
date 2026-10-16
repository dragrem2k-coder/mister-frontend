#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Steht nichts im Kasten, verschwindet der Kasten (Build 265).

NUTZERWUNSCH: "ich haette gerne im backend das man alle einstellungen
an und aus schaltbar macht, sodass wenn ich nix beim overlay sehen will
auch kein kasten mehr angezeigt wird."

Ein Kasten mit Rahmen, Schatten und Farbkante, in dem nichts steht, ist
im Stream ein Fleck ohne Aussage.

WAS DABEI LEICHT SCHIEFGEHT, und wogegen dieser Test steht:

  1. NUR DIE SCHALTER ANZUSEHEN waere falsch. Ein Element kann auch
     deshalb leer sein, weil es zu diesem Spiel keine Angabe gibt -
     kein Cover, kein Genre, keine Spielzeit. Geprueft wird deshalb,
     was wirklich SICHTBAR ist.
  2. DEN SPIELTITEL ZU VERGESSEN. Er wird seit Build 254 ueber
     style.display ausgeblendet, nicht ueber die Klasse "hidden" -
     eine Pruefung, die nur auf die Klasse sieht, haelt ihn fuer
     sichtbar und laesst den Kasten ewig stehen.
  3. DIE LISTE DER TEILE VERALTEN ZU LASSEN. Kommt ein neues Element
     in den Kasten und steht nicht in KARTEN_TEILE, zaehlt es nicht
     mit - der Kasten verschwaende dann, obwohl noch etwas drinsteht.
     Dagegen steht Test 1: die Liste wird mit dem Markup verglichen.

Geprueft wird AM ECHTEN SKRIPT in einem Stub-DOM unter node -
dieselbe Machart wie bei der Erfolgs-Wand (Build 255).

Ausfuehren:
    python3 tools/test_overlay_leer.py
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
_OVERLAY = os.path.join(_REPO, "frontend", "stream_overlay.html")
_ADMIN = os.path.join(_REPO, "frontend", "stream_admin.html")
_SERVER = os.path.join(_REPO, "frontend", "stream_server.py")

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


_OV = io.open(_OVERLAY, encoding="utf-8").read()
_AD = io.open(_ADMIN, encoding="utf-8").read()
_SV = io.open(_SERVER, encoding="utf-8").read()

# ---------------------------------------------------------------------------
print("Test 1: die Liste der Teile passt zum Kasten")
# ---------------------------------------------------------------------------
_karte = _OV[_OV.index('<div id="card"'):]
_karte = _karte[:_karte.index('<div id="ra-wall">')]
_ids = re.findall(r'id="([a-z_\-]+)"', _karte)
_teile = re.findall(r"'([a-z_]+)'",
                    _OV.split("const KARTEN_TEILE = [")[1].split("]")[0])
# Was absichtlich NICHT mitzaehlt, und warum.
_AUSGENOMMEN = {
    "cat": "wird seit jeher auf '' gesetzt - ein totes Element",
    "star": "sitzt IN #title und wird mit ihm sichtbar",
    "titletext": "sitzt IN #title",
    "fact_genre": "sitzt IN #facts", "fact_year": "sitzt IN #facts",
    "fact_playtime": "sitzt IN #facts", "fact_ra": "sitzt IN #facts",
    "npname": "sitzt IN #np",
    "card": "ist der Kasten selbst",
}
for _id in sorted(set(_ids)):
    if _id in _AUSGENOMMEN:
        continue
    check("'%s' wird mitgezaehlt" % _id, _id in _teile,
          "steht im Kasten, aber nicht in KARTEN_TEILE - der Kasten "
          "verschwaende, obwohl dieses Element noch etwas zeigt")
for _t in _teile:
    check("'%s' gibt es wirklich" % _t, _t in _ids, str(_ids))

check("der leere Kasten wird ueber eine Klasse ausgeblendet",
      ".card.leer{display:none}" in _OV)
check("und die Klasse wird am Ende von applyState gesetzt",
      "card.classList.toggle('leer', leer);" in _OV)
check("das Aufblitzen entfaellt beim leeren Kasten",
      "if(!leer){" in _OV,
      "eine Animation auf einem unsichtbaren Kasten ist Arbeit fuer "
      "nichts")

# ---------------------------------------------------------------------------
print()
print("Test 2: die neuen Schalter gibt es ueberall")
# ---------------------------------------------------------------------------
for _name, _wo in (("show_brand", "die Ueberschrift"),
                   ("show_year", "das Jahr")):
    check("%s: Vorgabe im Server" % _name,
          '"%s": True' % _name in _SV, _wo)
    check("%s: Kaestchen im Backend" % _name,
          'id="%s"' % _name in _AD)
    check("%s: wird geladen" % _name,
          '$("%s").checked = c.%s!==false;' % (_name, _name) in _AD)
    check("%s: wird gespeichert" % _name,
          "%s:$(\"%s\").checked" % (_name, _name) in _AD)
    check("%s: wird im Overlay beachtet" % _name,
          "cfg.%s" % _name in _OV)
check("das Jahr haengt NICHT mehr am Genre",
      "cfg.show_genre!==false && !!s.year" not in _OV,
      "wer nur das Jahr wollte, hatte vorher Pech")

# ---------------------------------------------------------------------------
print()
print("Test 3: am echten Skript - der Kasten verschwindet und kommt wieder")
# ---------------------------------------------------------------------------
_node = shutil.which("node") or shutil.which("nodejs")
PROBE = r"""'use strict';
const fs = require('fs');
class Knoten {
  constructor(tag, id){ this.tag=tag; this.id=id||''; this.cls=new Set();
    this.style={}; this.kids=[]; this._text=''; this.src='';
    const self=this;
    this.classList={ add:c=>self.cls.add(c), remove:c=>self.cls.delete(c),
      contains:c=>self.cls.has(c),
      toggle:(c,an)=>{ if(an===undefined) an=!self.cls.has(c);
                       if(an) self.cls.add(c); else self.cls.delete(c);} };
  }
  // DIE BROWSER-REGEL, auf die es hier ankommt: textContent liefert
  // den Text des Elements UND aller Kinder. #title enthaelt den Stern
  // und den Titeltext als eigene Spans - wer nur den eigenen Text
  // ansieht, haelt den Kasten faelschlich fuer leer. Genau daran ist
  // dieser Test beim ersten Anlauf haengengeblieben, und der Fehler
  // lag in der Attrappe, nicht im Overlay.
  get textContent(){
    return this._text + this.kids.map(k => k.textContent).join('');
  }
  set textContent(v){ this._text = String(v); this.kids = []; }
  get className(){ return [...this.cls].join(' '); }
  set className(v){ this.cls=new Set(String(v).split(/\s+/).filter(Boolean)); }
  getAttribute(n){ return n==='src' ? (this.src||null) : null; }
  setAttribute(){} removeAttribute(n){ if(n==='src') this.src=''; }
  appendChild(k){ this.kids.push(k); return k; }
  set innerHTML(v){ this.kids=[]; }
  get offsetWidth(){ return 10; }
  getBoundingClientRect(){ return {height:100}; }
  get scrollHeight(){ return 100; } get clientHeight(){ return 100; }
}
const K = {};
const hole = id => K[id] || (K[id] = new Knoten('div', id));
// Die Verschachtelung aus dem Markup nachbilden - nur die, die fuer
// die Textzusammenfassung zaehlt.
[['title', ['star', 'titletext']],
 ['facts', ['fact_genre', 'fact_year', 'fact_playtime', 'fact_ra']],
 ['np', ['npname']]].forEach(([elternId, kinder]) => {
  const eltern = hole(elternId);
  kinder.forEach(k => eltern.kids.push(hole(k)));
});
hole('star')._text = '\u2605';
global.document = {
  getElementById: hole,
  documentElement: {style:{setProperty:()=>{}}},
  createElement: t => new Knoten(t, '')
};
global.getComputedStyle = () => ({rowGap:'3px'});
global.performance = {now:()=>0};
global.requestAnimationFrame = f => 1;
global.cancelAnimationFrame = () => {};
let hoerer = {};
global.EventSource = class { constructor(){} addEventListener(n,f){hoerer[n]=f;}
                             close(){} };
const html = fs.readFileSync(process.argv[2], 'utf8');
const js = html.split('<script>')[1].split('</script>')[0];
const api = new Function(js +
  '\n;return {applyConfig, applyState, kartenLeer};')();

let fehler = 0;
function pruef(label, bed, hinweis){
  console.log((bed ? 'OK   ' : 'FEHL ') + label + (hinweis ? '  <- '+hinweis : ''));
  if(!bed) fehler++;
}
const LEER = () => K['card'].cls.has('leer');

// 1. Alles an, volles Spiel -> der Kasten steht.
api.applyConfig({title:'Dragend'});
api.applyState({category:'SNES', system:'SNES', syskey:'SNES',
                name:'Super Mario World', art_name:'Super Mario World',
                genre:'Jump&Run', year:'1990', playtime:'1h',
                ra_progress:'3/70', list:['a','b'], list_index:0,
                nowplaying:'Musik'});
pruef('voller Zustand: der Kasten steht', !LEER());

// 2. Alles aus, nichts im Zustand -> der Kasten verschwindet.
api.applyConfig({title:'', show_brand:false, show_boxart:false,
                 show_system:false, show_name:false, show_genre:false,
                 show_year:false, show_playtime:false, show_ra:false,
                 show_favorite:false, show_list:false,
                 show_nowplaying:false});
api.applyState({category:'', system:'', syskey:'', name:'', art_name:'',
                list:[], list_index:0, nowplaying:''});
pruef('alles abgeschaltet: der Kasten ist weg', LEER(),
      'genau der Nutzerwunsch');

// 3. EIN Schalter zurueck -> der Kasten kommt wieder.
api.applyConfig({title:'', show_brand:false, show_boxart:false,
                 show_system:false, show_name:true, show_genre:false,
                 show_year:false, show_playtime:false, show_ra:false,
                 show_favorite:false, show_list:false,
                 show_nowplaying:false});
api.applyState({category:'', system:'', syskey:'', name:'Zelda',
                art_name:'Zelda', list:[], list_index:0, nowplaying:''});
pruef('ein einziger sichtbarer Titel genuegt', !LEER(),
      'der Kasten darf nur verschwinden, wenn WIRKLICH nichts bleibt');

// 4. Alles AN, aber das Spiel hat zu nichts Angaben -> trotzdem leer.
api.applyConfig({title:'', show_brand:false, show_name:false});
api.applyState({category:'', system:'', syskey:'', name:'', art_name:'',
                genre:'', year:'', playtime:'', ra_progress:'',
                list:[], list_index:0, nowplaying:''});
pruef('ohne Angaben ist er auch bei gesetzten Schaltern leer', LEER(),
      'die Schalter allein anzusehen waere die falsche Pruefung');

// 5. Die Ueberschrift allein haelt den Kasten.
api.applyConfig({title:'Dragend', show_brand:true, show_name:false});
api.applyState({category:'', system:'', syskey:'', name:'', art_name:'',
                list:[], list_index:0, nowplaying:''});
pruef('die Ueberschrift allein haelt ihn', !LEER());
api.applyConfig({title:'Dragend', show_brand:false, show_name:false});
api.applyState({category:'', system:'', syskey:'', name:'', art_name:'',
                list:[], list_index:0, nowplaying:''});
pruef('abgeschaltete Ueberschrift haelt ihn nicht', LEER());

// 6. Jahr getrennt vom Genre.
api.applyConfig({title:'', show_brand:false, show_name:false,
                 show_genre:true, show_year:false});
api.applyState({category:'', system:'', syskey:'', name:'', art_name:'',
                genre:'Jump&Run', year:'1990', list:[], list_index:0});
pruef('Genre an, Jahr aus: Genre bleibt sichtbar',
      !K['fact_genre'].cls.has('hidden'));
pruef('und das Jahr ist weg', K['fact_year'].cls.has('hidden'),
      'eigener Schalter seit Build 265');
process.exit(fehler ? 1 : 0);
"""
if _node:
    _tmp = tempfile.mkdtemp(prefix="overlay_leer_")
    try:
        _p = os.path.join(_tmp, "probe.js")
        io.open(_p, "w", encoding="utf-8").write(PROBE)
        _r = subprocess.run([_node, _p, _OVERLAY],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for _z in _r.stdout.decode("utf-8", "replace").strip().split("\n"):
            if not _z.strip():
                continue
            check(_z[5:].split("  <- ")[0], _z.startswith("OK"),
                  _z.split("  <- ")[1] if "  <- " in _z else "")
        if _r.returncode not in (0, 1):
            check("die Probe laeuft ueberhaupt", False,
                  _r.stderr.decode("utf-8", "replace").strip()[:400])
    finally:
        shutil.rmtree(_tmp, ignore_errors=True)
else:
    print("  --   node fehlt, Stub-DOM-Probe uebersprungen")

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
