/* ===========================================================================
 * libdragend - die beiden Bildrechnungen des Frontends in C
 *
 * WICHTIGSTE REGEL DIESER DATEI:
 *
 *     Die Ergebnisse muessen BITGENAU denen von
 *     fe/art.py::_verkleinern_flaechenmittel() und ::_hochskalieren()
 *     entsprechen. Nicht "sieht gleich aus" - Byte fuer Byte.
 *
 * Der Miniaturen-Zwischenspeicher verlangt, dass eine gespeicherte
 * Miniatur bit-identisch zu einer frisch berechneten ist. Laufen die
 * Fassungen auseinander, liegen zweierlei Bilder unter demselben
 * Schluessel und niemand merkt es - beide sehen fuer sich richtig aus.
 * tools/test_c_modul.py vergleicht deshalb ueber Zufallsbilder.
 *
 * Drei Fallstricke, an denen eine naive Uebersetzung scheitert:
 *
 *   1. Die Gruppengrenzen entstehen in Python ueber FLIESSKOMMA
 *      (int(x * w / tw)), nicht ueber Ganzzahldivision. x*w/tw ist
 *      NICHT dasselbe wie (x*w)/tw bei ganzen Zahlen. Hier wird
 *      deshalb genauso in double gerechnet und danach abgeschnitten.
 *
 *   2. Der schnelle Weg ("schmal", hoechstens zwei Quellspalten je
 *      Zielspalte) zaehlt bei einer Ein-Pixel-Gruppe denselben Wert
 *      DOPPELT und verdoppelt dafuer den Teiler. Das Ergebnis ist
 *      dasselbe wie beim allgemeinen Weg - aber nur, wenn man es
 *      genauso macht.
 *
 *   3. Beim Verkleinern wird der Alphakanal NICHT geschrieben. Python
 *      legt einen genullten Puffer an und fuellt nur die Kanaele 0..2,
 *      Alpha bleibt also 0. Beim Vergroessern dagegen werden alle vier
 *      Bytes kopiert.
 *
 * Keine Abhaengigkeiten ausser <string.h> (memset/memcpy).
 * Uebersetzen: siehe bauen.sh
 * ===========================================================================
 */
#include <string.h>

/* Rueckgabe: 0 = ok, -1 = unsinnige Masse (dann faellt Python zurueck) */
int skalieren_flaechenmittel(const unsigned char *pix, int w, int h,
                             int tw, int th, unsigned char *out)
{
    int x, y, ty, k;
    int rw, ro;
    int schmal = 1;
    int *a_von, *a_bis, *gewicht;
    unsigned int *acc;
    static int puffer_zu_klein = 0;

    /* Arbeitsspeicher auf dem Stapel waere bei 1920 Zielspalten
     * grenzwertig - stattdessen feste Obergrenzen. Groesser als das
     * wird im Frontend nie angefragt (groesster Kasten: Bildschirm-
     * breite). Passt es doch nicht, wird -1 gemeldet und Python
     * rechnet es selbst. */
    enum { MAXZIEL = 4096 };
    static int s_von[MAXZIEL], s_bis[MAXZIEL], s_gew[MAXZIEL];
    static unsigned int s_acc[3 * MAXZIEL];

    if (tw <= 0 || th <= 0 || w <= 0 || h <= 0) return -1;
    if (tw > MAXZIEL) { puffer_zu_klein++; return -1; }

    a_von = s_von; a_bis = s_bis; gewicht = s_gew; acc = s_acc;
    rw = w * 4;
    ro = tw * 4;

    /* Quell-Spaltenbereich je Zielspalte - genau wie in Python, ueber
     * Fliesskomma. */
    for (x = 0; x < tw; x++) {
        int av = (int)((double)(x * w) / (double)tw);
        int bv = (int)((double)((x + 1) * w) / (double)tw);
        if (bv < av + 1) bv = av + 1;
        if (bv > w) bv = w;          /* Sicherheitsnetz gegen Ueberlauf */
        a_von[x] = av;
        a_bis[x] = bv;
        if (bv - av > 2) schmal = 0;
    }
    for (x = 0; x < tw; x++) {
        int n = a_bis[x] - a_von[x];
        /* Beim schmalen Weg zaehlt eine Ein-Pixel-Gruppe doppelt. */
        gewicht[x] = (schmal && n == 1) ? 2 : n;
    }

    memset(out, 0, (size_t)tw * (size_t)th * 4);

    for (ty = 0; ty < th; ty++) {
        int y0 = (int)((double)(ty * h) / (double)th);
        int y1 = (int)((double)((ty + 1) * h) / (double)th);
        int n;
        unsigned char *zeile;

        if (y1 < y0 + 1) y1 = y0 + 1;
        if (y1 > h) y1 = h;
        n = y1 - y0;

        memset(acc, 0, sizeof(unsigned int) * 3 * (size_t)tw);

        for (y = y0; y < y1; y++) {
            const unsigned char *row = pix + (size_t)y * (size_t)rw;
            if (schmal) {
                for (x = 0; x < tw; x++) {
                    const unsigned char *p = row + (size_t)a_von[x] * 4;
                    const unsigned char *q = row + (size_t)(a_bis[x] - 1) * 4;
                    acc[x]          += (unsigned int)p[0] + q[0];
                    acc[tw + x]     += (unsigned int)p[1] + q[1];
                    acc[2 * tw + x] += (unsigned int)p[2] + q[2];
                }
            } else {
                for (x = 0; x < tw; x++) {
                    const unsigned char *p = row + (size_t)a_von[x] * 4;
                    int cnt = a_bis[x] - a_von[x];
                    unsigned int s0 = 0, s1 = 0, s2 = 0;
                    int i;
                    for (i = 0; i < cnt; i++, p += 4) {
                        s0 += p[0]; s1 += p[1]; s2 += p[2];
                    }
                    acc[x]          += s0;
                    acc[tw + x]     += s1;
                    acc[2 * tw + x] += s2;
                }
            }
        }

        zeile = out + (size_t)ty * (size_t)ro;
        for (k = 0; k < 3; k++) {
            unsigned int *sp = acc + (size_t)k * (size_t)tw;
            for (x = 0; x < tw; x++) {
                unsigned int teiler = (unsigned int)(gewicht[x] * n);
                zeile[x * 4 + k] = (unsigned char)(sp[x] / teiler);
            }
        }
    }
    (void)puffer_zu_klein;
    return 0;
}

/* Ganzzahliges Vergroessern (Nearest-Neighbor). Hier werden ALLE VIER
 * Bytes kopiert, Alpha eingeschlossen - anders als oben. */
int hochskalieren(const unsigned char *pix, int w, int h, int scale,
                  unsigned char *out)
{
    int x, y, rep;
    int sw, row_out;

    if (w <= 0 || h <= 0 || scale <= 0) return -1;
    sw = w * scale;
    row_out = sw * 4;

    for (y = 0; y < h; y++) {
        const unsigned char *src = pix + (size_t)y * (size_t)w * 4;
        unsigned char *erste = out + (size_t)y * (size_t)scale
                                   * (size_t)row_out;
        unsigned char *schreib = erste;
        for (x = 0; x < w; x++) {
            const unsigned char *p = src + (size_t)x * 4;
            for (rep = 0; rep < scale; rep++) {
                schreib[0] = p[0]; schreib[1] = p[1];
                schreib[2] = p[2]; schreib[3] = p[3];
                schreib += 4;
            }
        }
        /* Die fertige Zeile scale-mal untereinander. */
        for (rep = 1; rep < scale; rep++)
            memcpy(erste + (size_t)rep * (size_t)row_out, erste,
                   (size_t)row_out);
    }
    return 0;
}


/* Mehrere Rechtecke zeilenweise von einem Puffer in einen anderen
 * kopieren - die C-Fassung von _restore_spuren() in frontend.py.
 *
 * WARUM: im Profillauf auf dem Geraet war das mit 9-12 ms der groesste
 * verbliebene Python-Posten eines Seitenaufbaus (der selbst 43-66 ms
 * dauert). Es sind achtzehn schmale Rechtecke, jedes ueber mehrere
 * Zeilen, und jede einzelne Zeile war eine eigene Slice-Zuweisung mit
 * allem Python-Vorlauf drumherum. Die Arbeit selbst ist ein memcpy je
 * Zeile - hier bleibt davon genau das uebrig.
 *
 * ACHTUNG, die Begrenzungsrechnung muss WORTGLEICH zur Python-Fassung
 * sein, sonst wird an anderer Stelle abgeschnitten:
 *
 *     max_rows = (grenze - (x * 4) - need) // stride + 1
 *
 * Python teilt mit ABRUNDEN (Richtung minus unendlich), C schneidet zur
 * Null hin ab. Bei negativem Zaehler - genau der Notfall, den diese
 * Zeile abfangen soll - kaemen sonst unterschiedliche Ergebnisse heraus
 * und C wuerde eine Zeile kopieren, die Python verwirft. Deshalb wird
 * hier von Hand abgerundet.
 *
 * rechtecke ist eine flache Liste aus je vier Werten: x, y, w, h.
 */
static int abrunden_div(int zaehler, int nenner)
{
    int q = zaehler / nenner;
    if ((zaehler % nenner != 0) && ((zaehler < 0) != (nenner < 0))) q--;
    return q;
}

int rechtecke_kopieren(const unsigned char *src, unsigned char *dst,
                       int stride, int hoehe, int grenze,
                       const int *rechtecke, int anzahl)
{
    int i;
    if (!src || !dst || stride <= 0 || anzahl < 0) return -1;
    for (i = 0; i < anzahl; i++) {
        int x = rechtecke[i * 4 + 0];
        int y = rechtecke[i * 4 + 1];
        int w = rechtecke[i * 4 + 2];
        int h = rechtecke[i * 4 + 3];
        int need = w * 4;
        int y0, y1, max_rows, off, r;

        if (x < 0 || need <= 0) continue;
        y0 = y > 0 ? y : 0;
        y1 = (y + h) < hoehe ? (y + h) : hoehe;
        if (y1 <= y0) continue;
        max_rows = abrunden_div(grenze - (x * 4) - need, stride) + 1;
        if (max_rows < y1) y1 = (max_rows > y0) ? max_rows : y0;
        if (y1 <= y0) continue;
        off = y0 * stride + x * 4;
        for (r = 0; r < y1 - y0; r++) {
            memcpy(dst + off, src + off, (size_t)need);
            off += stride;
        }
    }
    return 0;
}

/* Damit die Python-Seite pruefen kann, ob sie die passende Fassung
 * gefunden hat. Wird bei jeder inhaltlichen Aenderung hochgezaehlt. */
int dragend_version(void) { return 2; }
