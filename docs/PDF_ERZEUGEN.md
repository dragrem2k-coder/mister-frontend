# Die Anleitungs-PDF neu erzeugen

`Dragend_Anleitung.pdf` wird aus `anleitung_source.html` erzeugt. Die
HTML-Datei ist die Quelle - Änderungen gehören dorthin, nicht in die
PDF.

```bash
chromium --headless --disable-gpu --no-sandbox --no-pdf-header-footer \
    --print-to-pdf=docs/Dragend_Anleitung.pdf \
    "file://$PWD/docs/anleitung_source.html"
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
häufigsten.
