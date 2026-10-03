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

/* ------------------------------------------------------------------
 * ZEILEN MIT ZWEI SCHRITTWEITEN (Build 225)
 * ------------------------------------------------------------------
 * rechtecke_kopieren() oben kann nur Puffer mit DERSELBEN Schrittweite
 * - Hintergrundkopie und Bildspeicher sind gleich gerastert, dort
 * stimmt das. Zwei Stellen im Zeichenweg sind es nicht:
 *
 *   blit()  - ein dekodiertes Cover liegt dicht gepackt (Breite * 4),
 *             das Ziel hat die Schrittweite des Bildschirms.
 *   text()  - ein fertiger Textstreifen ist genauso dicht gepackt.
 *
 * Beide haben deshalb bis hierher eine Python-Schleife ueber die
 * Bildzeilen gehabt, und beide stehen im Bericht vom 02.10. weit oben:
 * "text 15,56 ms" in der Galerie (8 Aufrufe, 191 Zeichen - also sehr
 * BREITE Zeilen) und "blit 6 bis 12 ms" in jeder Ansicht.
 *
 * Die Pruefungen sind dieselben wie oben, und sie sind der Grund,
 * warum hier ueberhaupt C steht statt eines Einzeilers: eine zu kurze
 * Quelle oder ein zu weit rechts liegendes Ziel darf NICHT ueber das
 * Ende schreiben. Beide Grenzen werden mitgegeben und beide werden
 * geprueft; im Zweifel werden weniger Zeilen kopiert, nie mehr.
 */
int zeilen_kopieren(unsigned char *dst, int dst_stride, int dst_grenze,
                    const unsigned char *src, int src_stride, int src_grenze,
                    int x, int y, int breite, int hoehe)
{
    int r, dst_off, src_off, max_rows;
    if (!dst || !src) return -1;
    if (dst_stride <= 0 || src_stride <= 0) return -1;
    if (breite <= 0 || hoehe <= 0 || x < 0 || y < 0) return -1;

    /* Wie viele Zeilen passen in die Quelle? */
    max_rows = abrunden_div(src_grenze - breite, src_stride) + 1;
    if (max_rows < hoehe) hoehe = max_rows;
    if (hoehe <= 0) return -1;

    /* Und wie viele ins Ziel? */
    dst_off = y * dst_stride + x * 4;
    if (dst_off < 0) return -1;
    max_rows = abrunden_div(dst_grenze - (x * 4) - breite, dst_stride) + 1 - y;
    if (max_rows < hoehe) hoehe = max_rows;
    if (hoehe <= 0) return -1;

    src_off = 0;
    for (r = 0; r < hoehe; r++) {
        memcpy(dst + dst_off, src + src_off, (size_t)breite);
        dst_off += dst_stride;
        src_off += src_stride;
    }
    return 0;
}

/* ------------------------------------------------------------------
 * SCHARF VERKLEINERN (Build 175)
 * ------------------------------------------------------------------
 * Nearest-Neighbor: je Zielpunkt genau EIN Quellpunkt, ohne zu
 * mitteln. Das Ergebnis ist haerter und koerniger als das
 * Flaechenmittel darueber - und genau das ist auf einer Roehre oft
 * das bessere Bild. Pixelkunst bleibt Pixelkunst, statt zu einem
 * weichen Brei zu werden; die Maske der Roehre uebernimmt das
 * Weichzeichnen ohnehin selbst.
 *
 * Es ist ausserdem deutlich billiger: keine Summen, keine Division,
 * nur ein Zugriff je Zielpunkt.
 *
 * Die Quellindizes werden GENAUSO gerechnet wie beim Flaechenmittel
 * (ganzzahlig aus dem Verhaeltnis) - so liegen beide Verfahren auf
 * demselben Raster, und der Umschalter aendert die Bildschaerfe,
 * nicht den Bildausschnitt.
 */
int skalieren_nearest(const unsigned char *pix, int w, int h,
                      int tw, int th, unsigned char *out)
{
    int x, ty;
    int rw, ro;
    enum { MAXZIEL = 4096 };
    static int s_sx[MAXZIEL];

    if (tw <= 0 || th <= 0 || w <= 0 || h <= 0) return -1;
    if (tw > MAXZIEL) return -1;

    rw = w * 4;
    ro = tw * 4;

    /* Quellspalte je Zielspalte einmal vorrechnen - sonst steht
     * dieselbe Division in der inneren Schleife. */
    for (x = 0; x < tw; x++) {
        int sx = (int)((double)(x * w) / (double)tw);
        if (sx >= w) sx = w - 1;
        s_sx[x] = sx * 4;
    }

    for (ty = 0; ty < th; ty++) {
        int sy = (int)((double)(ty * h) / (double)th);
        const unsigned char *zeile;
        unsigned char *ziel;
        if (sy >= h) sy = h - 1;
        zeile = pix + (size_t)sy * (size_t)rw;
        ziel = out + (size_t)ty * (size_t)ro;
        for (x = 0; x < tw; x++) {
            const unsigned char *q = zeile + s_sx[x];
            unsigned char *z = ziel + x * 4;
            z[0] = q[0];
            z[1] = q[1];
            z[2] = q[2];
            z[3] = q[3];
        }
    }
    return 0;
}

/* Damit die Python-Seite pruefen kann, ob sie die passende Fassung
 * gefunden hat. Wird bei jeder inhaltlichen Aenderung hochgezaehlt.
 * 3 = skalieren_nearest() dazugekommen (Build 175).
 * 4 = fremd_zaehlen() dazugekommen (Build 209).
 * 5 = rechtecke_farben() dazugekommen (Build 219).
 *
 * WICHTIG BEI EINEM TEIL-UPDATE, und das ist seit Build 219 anders
 * geloest: bisher verwarf die Python-Seite jede Fassung, deren Nummer
 * nicht GENAU passte - eine alte .so neben einer neuen frontend.py
 * bedeutete also KEIN C mehr, auch nicht fuer das Verkleinern, und das
 * ist auf dem Geraet der Faktor 124. Jetzt gilt eine SPANNE (siehe
 * DRAGEND_LIB_VERSION_MIN in fe/art.py): eine 4er-Fassung wird weiter
 * voll genutzt, nur rechtecke_farben() fehlt dann und die betroffenen
 * Zeichenwege rechnen in Python. Das ist der Unterschied zwischen
 * "etwas langsamer" und "alles langsam". */
int dragend_version(void) { return 6; }

/* ------------------------------------------------------------------
 * FLAECHEN FUELLEN (Build 219)
 * ------------------------------------------------------------------
 * Der Rumpf von fb.rect(), fb.rect_rounded(), rect_rounded_schatten()
 * und karte_mit_schatten() in C. Alle vier tun am Ende dasselbe: sie
 * schreiben ZEILEN EINER FARBE in den Puffer, eine Python-Zuweisung je
 * Bildzeile.
 *
 * WARUM DAS DER NAECHSTE SCHRITT WAR: Abschnitt J des Benchs weist
 * diese vier seit Build 216 gemeinsam als "karten" aus, und auf dem
 * DE10-Nano war das der groesste benannte Posten eines Scrollschritts -
 * 47,0 ms in der Spieleliste (37 % des Schritts), 35,2 in der Galerie,
 * 28,7 auf der Hauptseite. Rund 4,7 ms je Aufruf.
 *
 * DIE SCHNITTSTELLE IST BEWUSST EINE LISTE MIT FARBE JE RECHTECK und
 * nicht "ein Rechteck, eine Farbe": eine abgerundete Ecke besteht aus
 * zwei mal radius Zeilen unterschiedlicher Breite, und eine Karte mit
 * Schatten aus Kartenflaeche UND Schattenstreifen. So wird aus jedem
 * der vier Aufrufe GENAU EIN Sprung nach C, statt eines je Zeile.
 *
 * rechtecke ist eine flache Liste aus je fuenf Werten:
 *     x, y, w, h, farbe
 * farbe sind die vier Bytes eines Bildpunktes in der Reihenfolge des
 * Bildspeichers, als 32-Bit-Wert gelesen (beide Ziele sind
 * little-endian; die Python-Seite baut ihn mit struct aus genau den
 * Bytes, die px() liefert - siehe rechtecke_farben() in fe/art.py).
 *
 * Erst wird die oberste Zeile Punkt fuer Punkt gesetzt, danach werden
 * die restlichen daraus kopiert: memcpy ist schneller als eine
 * Schleife, und es ist genau das, was die Python-Fassung mit ihrem
 * gecachten "row" tut.
 */
int rechtecke_farben(unsigned char *dst, int stride, int hoehe, int grenze,
                     const int *rechtecke, int anzahl)
{
    int i;
    if (!dst || stride <= 0 || anzahl < 0 || !rechtecke) return -1;
    for (i = 0; i < anzahl; i++) {
        int x = rechtecke[i * 5 + 0];
        int y = rechtecke[i * 5 + 1];
        int w = rechtecke[i * 5 + 2];
        int h = rechtecke[i * 5 + 3];
        unsigned int farbe = (unsigned int)rechtecke[i * 5 + 4];
        int need = w * 4;
        int y0, y1, max_rows, off, r, j;
        unsigned char *erste;

        if (x < 0 || y < 0 || need <= 0 || h <= 0) continue;
        y0 = y;
        y1 = (y + h) < hoehe ? (y + h) : hoehe;
        if (y1 <= y0) continue;
        /* Dieselbe Schranke wie in rechtecke_kopieren(): die letzte
         * Zeile, die noch VOLLSTAENDIG in den Puffer passt. */
        max_rows = abrunden_div(grenze - (x * 4) - need, stride) + 1;
        if (max_rows < y1) y1 = (max_rows > y0) ? max_rows : y0;
        if (y1 <= y0) continue;
        off = y0 * stride + x * 4;
        erste = dst + off;
        /* DIE OBERSTE ZEILE, UND DIE IST DER HEIKLE TEIL (Build 220).
         *
         * Hier stand zuerst eine Schleife, die den Farbwert Punkt fuer
         * Punkt schrieb - bei 700 Punkten also 700 Aufrufe von memcpy
         * mit vier Byte. Das ist fuer ein hohes Rechteck gleichgueltig
         * (danach folgen 899 grosse Kopien), aber seit Build 220 kommen
         * die ECKENZEILEN der abgerundeten Kaesten gebuendelt hier an -
         * und das sind rund 200 Rechtecke von je EINER Zeile. Dann
         * besteht die ganze Arbeit aus diesen Vier-Byte-Schreibvorgaengen,
         * und die Python-Fassung war mit ihrer fertig gecachten Zeile
         * schneller.
         *
         * Jetzt wird verdoppelt: vier Byte setzen, dann das Gesetzte
         * hinter sich selbst kopieren, und das immer weiter. Aus 700
         * Aufrufen werden zehn, und der letzte kopiert nur den Rest.
         * Ueber memcpy und nicht ueber einen uint32-Zeiger, weil die
         * Ausrichtung an stride und x haengt und ein unausgerichteter
         * Zugriff auf ARM nicht ueberall harmlos ist. */
        memcpy(erste, &farbe, 4);
        {
            int gesetzt = 1;                 /* in Punkten */
            while (gesetzt < w) {
                int n = (gesetzt <= w - gesetzt) ? gesetzt : (w - gesetzt);
                memcpy(erste + gesetzt * 4, erste, (size_t)n * 4);
                gesetzt += n;
            }
        }
        (void)j;
        /* Und der Rest als Kopie davon. */
        off += stride;
        for (r = y0 + 1; r < y1; r++) {
            memcpy(dst + off, erste, (size_t)need);
            off += stride;
        }
    }
    return 0;
}

/* ------------------------------------------------------------------
 * WAS HIER BEWUSST NICHT STEHT: DER BILDWAECHTER (Build 209)
 * ------------------------------------------------------------------
 * Der Waechter vergleicht seit Build 209 ganze ZEILEN statt acht
 * einzelner Bildpunkte (siehe _waechter_pruefen() in
 * fe/framebuffer.py). Ich hatte ihn zuerst hierher geholt, in der
 * Annahme, 20 Proben mal 7680 Byte seien in Python zu teuer.
 *
 * Die Messung sagt etwas anderes, und sie hat gewonnen:
 *
 *     gleich         C 0.0158 ms   Python 0.0126 ms
 *     spaeter Fund   C 0.0110 ms   Python 0.0110 ms
 *
 * Python ist sogar minimal SCHNELLER. Der Grund ist einfach und ich
 * hatte ihn uebersehen: ein Schnittvergleich auf einem bytearray
 * (mm[a:b] != soll[c:d]) IST bereits ein memcmp, und eine Zuweisung
 * ist ein memcpy - der Python-Rahmen faellt genau einmal je Probe an,
 * nicht je Byte. Zu holen war hier also nie etwas, und die
 * ctypes-Aufrufkosten fressen den Rest.
 *
 * Deshalb steht der Waechter in Python, in EINER Fassung, ohne
 * Rueckfall und ohne zwei Wege, die auseinanderlaufen koennen.
 *
 * Teuer war nur, was Python WIRKLICH je Bildpunkt anfassen muss -
 * und das ist der Zaehler gleich darunter.
 */

/* ------------------------------------------------------------------
 * FREMDE AUSGABE ZAEHLEN (Build 209)
 * ------------------------------------------------------------------
 * Der Rumpf von frontend.py::_fremdausgabe_zaehlen_py(): Bildpunkte,
 * die auf dem SCHIRM hell sind, im gezeichneten Bild aber dunkel.
 *
 * Die Richtung ist wichtig und keine Bequemlichkeit: ein blosser
 * Unterschied zwischen mm und buf entsteht auch mitten in einem
 * eigenen Bildaufbau, dann ist das Helle aber in buf. Wer nur auf
 * "ungleich" prueft, baut sich daraus ein Flackern - siehe Build 151.
 *
 * Nur der Gruenkanal (Byte 1 von 4) wird angesehen: der Prompt ist
 * weisser Text, und ein Kanal spart zwei Drittel der Arbeit. Genau
 * so macht es die Python-Fassung auch, und tools/test_c_modul.py
 * vergleicht beide.
 *
 * Rueckgabe: Zahl der Treffer, -1 bei unsinnigen Argumenten.
 */
int fremd_zaehlen(const unsigned char *mm, const unsigned char *buf,
                  int stride, int zeilen, int breite4, int hell, int dunkel)
{
    int y, x, treffer = 0;
    if (!mm || !buf || stride <= 0 || zeilen < 0 || breite4 < 0) return -1;
    for (y = 0; y < zeilen; y++) {
        const unsigned char *s = mm + (size_t)y * stride;
        const unsigned char *g = buf + (size_t)y * stride;
        if (memcmp(s, g, (size_t)breite4) == 0) continue;
        for (x = 1; x < breite4; x += 4) {
            if (s[x] > hell && g[x] <= dunkel) treffer++;
        }
    }
    return treffer;
}
