# Die PDFs neu erzeugen

Es sind vier — zwei Dokumente in zwei Sprachen. Jedes hat eine
HTML-Quelle im selben Ordner. **Änderungen gehören in die HTML-Datei,
nicht in die PDF.**

| PDF | Quelle | Inhalt |
|---|---|---|
| `Dragend_Anleitung.pdf` | `anleitung_source.html` | 5 Seiten: Titel, Tastatur, Joypad, Funktionen, Ansichten & Cover |
| `Dragend_Manual_EN.pdf` | `manual_source_en.html` | dasselbe auf Englisch |
| `Installation_und_Update.pdf` | `installation_source.html` | 4 Seiten: Übersicht, Installation, nach der Installation, Update & Hilfe |
| `Installation_and_Update_EN.pdf` | `installation_source_en.html` | dasselbe auf Englisch |

```bash
CHROME=chromium   # oder der Pfad zu deinem Chromium/Chrome

for p in anleitung_source:Dragend_Anleitung \
         installation_source:Installation_und_Update \
         manual_source_en:Dragend_Manual_EN \
         installation_source_en:Installation_and_Update_EN; do
  "$CHROME" --headless --disable-gpu --no-sandbox --no-pdf-header-footer \
      --print-to-pdf="docs/${p##*:}.pdf" "file://$PWD/docs/${p%%:*}.html"
done
```

## Die vier Dateien hängen zusammen

`installation_source.html` bringt die Gestaltung **nicht** selbst mit —
sie ist eine Kopie des `<style>`-Blocks aus `anleitung_source.html` plus
ein paar eigene Klassen. Die beiden englischen Fassungen sind wiederum
Kopien der deutschen, bei denen **nur die Texte** ausgetauscht wurden:
Klassen, Maße und Bildpfade sind absichtlich Zeichen für Zeichen
gleich.

Wer also das Aussehen ändert, ändert es in **allen vier** Dateien —
sonst sehen die PDFs nicht mehr wie ein Satz aus. Wer einen Text
ändert, muss an die jeweils andere Sprache denken.

## Drei Fallen, die schon zugeschnappt sind

**Nicht wkhtmltopdf.** Die Vorlage arbeitet mit
`@page { size: A4; margin: 0 }` und einer festen Breite von `210mm` pro
Seite. wkhtmltopdf setzt das nicht um — es rendert mit eigener
Ansichtsbreite und schrumpft den Inhalt auf etwa drei Viertel der
Seite, mit einer grossen leeren Fläche darunter. Die Erzeugung meldet
dabei **keinen Fehler**; man sieht es erst in der fertigen Datei.
Chromium hält sich an beides.

**`&shy;` ist unsichtbar, wenn nicht umbrochen wird.** In den
Tastenbeschriftungen steht bei deutschen Komposita `Listen&shy;anfang`
— das ergibt umbrochen „Listen-anfang", sonst „Listenanfang", beides
richtig. Bei englischen Wortpaaren geht das schief: `Top of&shy;list`
wurde zu „Top oflist". Dort gehört ein `<br>` hin, kein `&shy;`.

**Anführungszeichen.** Die deutsche Vorlage benutzt `&bdquo;…&ldquo;`
und `&raquo;…&laquo;`. In der englischen Fassung müssen daraus
`&ldquo;…&rdquo;` werden, sonst stehen dort deutsche Zeichen.

## Bilder

Die Bilder in `_anleitung_assets/` sind Kopien aus `screenshots/` —
`tools/screenshots_bauen.py` erzeugt sie, danach kopieren:

```bash
cp screenshots/preview_1_kategorien.png       docs/_anleitung_assets/shot_categories.png
cp screenshots/preview_5_trophaeenraum.png    docs/_anleitung_assets/shot_trophy.png
cp screenshots/preview_2_spieleliste.png      docs/_anleitung_assets/shot_liste.png
cp screenshots/preview_3_ordner.png           docs/_anleitung_assets/shot_ordner.png
cp screenshots/preview_9_liste_raster.png     docs/_anleitung_assets/shot_raster.png
cp screenshots/preview_10_liste_galerie.png   docs/_anleitung_assets/shot_galerie.png
cp screenshots/preview_7_hauptseite_raster.png docs/_anleitung_assets/shot_kacheln.png
```

## Danach anschauen

Nicht nur erzeugen — **hinsehen**. Am schnellsten geht das so:

```bash
pdftoppm -r 70 -png docs/Dragend_Manual_EN.pdf /tmp/pruef
```

Lohnende Seiten: **2 (Tastatur)** und **3 (Joypad)** — dort steht die
Tastenbelegung, und die ändert sich am häufigsten. Bei der
Installations-PDF **Seite 2**: dort stehen Skriptnamen, und die sind
schon einmal umbenannt worden (`install_frontend.sh` →
`Frontend_Install.sh`), ohne dass die PDF davon etwas mitbekommen hat.
