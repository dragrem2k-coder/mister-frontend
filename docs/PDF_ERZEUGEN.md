# Die PDFs neu erzeugen

Es gibt zwei, und beide haben eine HTML-Quelle im selben Ordner.
Änderungen gehören in die HTML-Datei, nicht in die PDF.

| PDF | Quelle | Inhalt |
|---|---|---|
| `Dragend_Anleitung.pdf` | `anleitung_source.html` | 5 Seiten: Titel, Tastatur, Joypad, Funktionen, Ansichten & Cover |
| `Installation_und_Update.pdf` | `installation_source.html` | 4 Seiten: Übersicht, Installation, nach der Installation, Update & Hilfe |

```bash
chromium --headless --disable-gpu --no-sandbox --no-pdf-header-footer \
    --print-to-pdf=docs/Dragend_Anleitung.pdf \
    "file://$PWD/docs/anleitung_source.html"

chromium --headless --disable-gpu --no-sandbox --no-pdf-header-footer \
    --print-to-pdf=docs/Installation_und_Update.pdf \
    "file://$PWD/docs/installation_source.html"
```

`installation_source.html` bringt die Gestaltung **nicht** selbst mit -
sie ist eine Kopie des `<style>`-Blocks aus `anleitung_source.html` plus
ein paar eigene Klassen. Wer das Aussehen grundlegend ändert, ändert es
in beiden Dateien, sonst sehen die zwei PDFs nicht mehr wie ein Paar
aus.

Die Bilder in `_anleitung_assets/` sind Kopien aus `screenshots/` -
`tools/screenshots_bauen.py` erzeugt sie, danach kopieren:

```bash
cp screenshots/preview_1_kategorien.png    docs/_anleitung_assets/shot_categories.png
cp screenshots/preview_5_trophaeenraum.png docs/_anleitung_assets/shot_trophy.png
cp screenshots/preview_2_spieleliste.png   docs/_anleitung_assets/shot_liste.png
cp screenshots/preview_9_liste_raster.png  docs/_anleitung_assets/shot_raster.png
cp screenshots/preview_10_liste_galerie.png docs/_anleitung_assets/shot_galerie.png
cp screenshots/preview_7_hauptseite_raster.png docs/_anleitung_assets/shot_kacheln.png
```

**Warum ausdrücklich Chromium und nicht wkhtmltopdf:** die Vorlage
arbeitet mit `@page { size: A4; margin: 0 }` und einer festen Breite von
`210mm` pro Seite. wkhtmltopdf setzt das nicht um - es rendert mit einer
eigenen Ansichtsbreite und schrumpft den Inhalt auf etwa drei Viertel
der Seite zusammen, mit einer großen leeren Fläche darunter. Das sieht
man erst, wenn man die erzeugte Datei tatsächlich anschaut; die
Erzeugung selbst meldet keinen Fehler. Chromium hält sich an beides und
liefert exakt dasselbe Layout wie die bisherigen Fassungen.

Nach dem Erzeugen bitte einmal Seite 2 (Tastatur) und Seite 3 (Joypad)
ansehen - dort steht die Tastenbelegung, und genau die ändert sich am
häufigsten. Bei der Installations-PDF lohnt der Blick auf Seite 2: dort
stehen Skriptnamen, und die sind schon einmal umbenannt worden
(`install_frontend.sh` -> `Frontend_Install.sh`), ohne dass die PDF
davon etwas mitbekommen hat.
