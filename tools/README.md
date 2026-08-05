# tools/

Entwickler-Werkzeuge, die NICHT auf den MiSTer deployt werden (analog zu
`PC-Tools/`, aber fuer reine Test-/Diagnose-Skripte statt Endnutzer-Tools).

## regression_test.py

Standard-Regressionstest fuer `frontend/frontend.py`. Laeuft auf jedem PC mit
Python 3, OHNE echte MiSTer-Hardware (kein `/dev/fb0`, keine echten
Eingabegeraete noetig) - ersetzt nur die hardwarenahen Teile der
`Framebuffer`-Klasse durch eine Attrappe, geht aber bewusst durch den ECHTEN
`Frontend()`-Konstruktor (siehe Kommentar im Skript, Grund: ein frueherer
Reihenfolge-Fehler in `__init__()` blieb monatelang unentdeckt, weil jeder
damalige Test das betroffene Attribut von Hand vorher gesetzt hatte).

Testet 2 Aufloesungen (CRT 320x240, HDMI 1920x1080) x jede tatsaechlich
vorhandene Kategorie (aus `fe.cats`, skaliert automatisch mit der echten
Spielebibliothek) x mehrere Navigationspositionen/Sonderzustaende
(Beenden-Dialog, Attract-Modus, RA-Core-Auswahlbildschirm inkl. Abbruch).

Ausfuehren:
```
python3 tools/regression_test.py
```
Optional anderen Pfad zu `frontend.py` angeben:
```
FRONTEND_PY=/pfad/zu/frontend.py python3 tools/regression_test.py
```

Prueft NUR, dass `draw()`/verwandte Zeichenfunktionen ohne Ausnahme
durchlaufen (Abdeckung von Strukturfehlern, Index-/Attributfehlern,
Konstruktor-Reihenfolge). Prueft NICHT das tatsaechliche visuelle Ergebnis,
Eingabeverarbeitung oder Core-Start - das bleibt ein Test auf echter
Hardware.
