#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Framebuffer - reine Zeichen-Grundfunktionen, ausgelagert aus
frontend.py (Modularisierung, Git-Branch 'modular-refactor').

WICHTIG (dieselbe Python-Import-Falle wie bei fe/translations.py/
CURRENT_LANG): C_BG/C_TEXT werden als Rueckfallwerte in text()
verwendet, wenn keine Farbe explizit uebergeben wird - und aendern
sich beim Theme-Wechsel (apply_theme() in frontend.py). Ein einfacher
Import wuerde hier ebenfalls eine eingefrorene Kopie erzeugen.

Diesmal ANDERE Loesung als current_lang() (bewusst KEINE Funktions-
Indirektion): text() ist eine sehr heisse Stelle (wird fuer JEDES
einzelne gezeichnete Zeichen aufgerufen) - ein Funktionsaufruf pro
Zeichen nur fuer die Farbe waere unnoetiger Overhead. Stattdessen
haelt dieses Modul C_BG/C_TEXT als EIGENE globale Variablen mit
sinnvollen Standardwerten (identisch zum "dark"-Theme), und
frontend.py schreibt bei jedem Themenwechsel per Modul-qualifiziertem
Zugriff (fe.framebuffer.C_BG = ...) direkt hinein - das ist eine
normale Zuweisung, kein Neu-Binden einer importierten Kopie, wirkt
also sofort auch hier.
"""
import os, sys, mmap, fcntl, time, struct
from fe.log import LOG

FBDEV = "/dev/fb0"
C_BG = (16, 18, 24)          # siehe Modul-Kommentar oben - von
C_TEXT = (220, 224, 232)     # apply_theme() aktuell gehalten

FONT8X8 = bytes.fromhex('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000183c3c1818001800363600000000000036367f367f3636000c3e031e301f0c00006333180c6663001c361c6e3b336e000606030000000000180c0606060c1800060c1818180c060000663cff3c660000000c0c3f0c0c000000000000000c0c060000003f0000000000000000000c0c006030180c060301003e63737b6f673e000c0e0c0c0c0c3f001e33301c06333f001e33301c30331e00383c36337f3078003f031f3030331e001c06031f33331e003f3330180c0c0c001e33331e33331e001e33333e30180e00000c0c00000c0c00000c0c00000c0c06180c0603060c180000003f00003f0000060c1830180c06001e3330180c000c003e637b7b7b031e000c1e33333f3333003f66663e66663f003c66030303663c001f36666666361f007f46161e16467f007f46161e16060f003c66030373667c003333333f333333001e0c0c0c0c0c1e007830303033331e006766361e366667000f06060646667f0063777f7f6b63630063676f7b736363001c36636363361c003f66663e06060f001e3333333b1e38003f66663e366667001e33070e38331e003f2d0c0c0c0c1e003333333333333f0033333333331e0c006363636b7f7763006363361c1c3663003333331e0c0c1e007f6331184c667f001e06060606061e0003060c18306040001e18181818181e00081c36630000000000000000000000ff0c0c18000000000000001e303e336e000706063e66663b0000001e3303331e003830303e33336e0000001e333f031e001c36060f06060f0000006e33333e301f0706366e666667000c000e0c0c0c1e00300030303033331e070666361e3667000e0c0c0c0c0c1e000000337f7f6b630000001f333333330000001e3333331e0000003b66663e060f00006e33333e307800003b6e66060f0000003e031e301f00080c3e0c0c2c18000000333333336e0000003333331e0c000000636b7f7f3600000063361c36630000003333333e301f00003f190c263f00380c0c070c0c38001818180018181800070c0c380c0c07006e3b0000000000000000000000000000')

# NEU (uebernommen von TheRealSutefan): Latin-1-Ergaenzung (0xA0-0xFF,
# gleiches 8x8-Bitmap-Format wie FONT8X8) - damit Umlaute (ä/ö/ü/ß) und
# Akzente in Spielnamen/Texten echt dargestellt werden statt als "?".
FONT_EXTRA = bytes.fromhex('0000000000000000181800181818180018187e03037e18181c36260f06673f000000633e363e630033331e3f0c3f0c0c18181800181818007cc61c36361c331e33000000000000003c4299858599423c3c36367c0000000000cc663366cc00000000003f3030000000000000000000003c429da59da5423c7e000000000000001c36361c0000000018187e1818007e001c30180c3c0000001c3018301c000000180c00000000000000006666663e0603fedbdbded8d8d8000000001818000000000000000018301e080c081c000000001c36361c00000000003366cc66330000c36333bdecf6f303c363337bcc6633f003c463b4dbace6800c000c0603331e0007001c36637f630070001c36637f63001c36003e637f63006e3b003e637f6300631c36637f6363000c0c001e333f33007c36337f333373001e3303331e18301e07003f061e063f0038003f061e063f000c123f061e063f0036003f061e063f0007001e0c0c0c1e0038001e0c0c0c1e000c12001e0c0c1e0033001e0c0c0c1e003f666f6f66663f003f0033373f3b33000e00183c663c18007000183c663c18003c66183c663c18006e3b003e63633e00c3183c66663c180000361c081c3600005c36737b6f361d000e00666666663c007000666666663c003c66006666663c003300333333331e00700066663c1818000f063e66663e060f001e331f331f030307001e303e337e0038001e303e337e007ec33c607c66fc006e3b1e303e337e0033001e303e337e000c0c1e303e337e000000fe30fe33fe0000001e03031e301c07001e333f031e0038001e333f031e007ec33c667e063c0033001e333f031e0007000e0c0c0c1e001c000e0c0c0c1e003e631c1818183c0033000e0c0c0c1e001b0e1b303e331e00001f001f333333000007001e33331e000038001e33331e001e33001e33331e006e3b001e33331e000033001e33331e001818007e0018180000603c767e6e3c060007003333337e000038003333337e001e33003333337e000033003333337e0000380033333e301f0000063e663e060000330033333e301f')

# ----------------------------------------------------------------------------
# FRAMEBUFFER
# ----------------------------------------------------------------------------

ROWCACHE_MAX_ENTRIES = 150  # siehe Framebuffer.rect()/clear() - verhindert
                            # unbegrenztes Cache-Wachstum durch leicht
                            # wechselnde (Farbe, Breite)-Kombinationen
VIGNETTE_ENABLED = True    # dezente Randabdunkelung auf einfarbigen
                            # Flaechen (siehe Framebuffer.clear()) - rein
                            # optisch, kostet dank Zeilen-Cache nichts
                            # beim eigentlichen Zeichnen

class Framebuffer:
    # FBIO_WAITFORVSYNC (siehe linux/fb.h: _IOW('F', 0x20, __u32)) - wartet
    # auf den naechsten vertikalen Bildwechsel der Anzeige-Hardware, BEVOR
    # in den Framebuffer geschrieben wird. Ohne das kann ein Schreibvorgang
    # (egal ob flip() oder flip_rows()) mitten in einem laufenden Scanvorgang
    # der Hardware landen - der Bildschirm zeigt dann fuer einen Sekundenbruch-
    # teil einen Mix aus altem und neuem Bildinhalt ("Tearing"). Sichtbar wird
    # das z.B. als leicht verschobener, "doppelt belichtet" wirkender Text bei
    # der markierten Zeile (Nutzer-Rueckmeldung: Text ueberlappt beim
    # Scrollen). Je groesser der Schreibvorgang (volle Seite vs. einzelne
    # Zeile), desto laenger dauert er und desto wahrscheinlicher ein
    # sichtbarer Treffer mitten im Scan.
    FBIO_WAITFORVSYNC = 0x40044620

    def __init__(self):
        # BUGFIX Teil 2 (Nutzer-Rueckmeldung: "1 von 10 Faellen startet
        # nicht richtig, bleibt im OSD" - siehe frontend_boot.sh fuer
        # Teil 1/die volle Herleitung): selbst mit der grosszuegigeren
        # 120s-Wartezeit in frontend_boot.sh kann es in seltenen Faellen
        # noch vorkommen, dass MiSTer's eigener Uebergang vom OSD zum
        # Framebuffer im exakt falschen Sekundenbruchteil noch nicht
        # ganz abgeschlossen ist, wenn wir hier ankommen - das Oeffnen
        # des Geraets (oder das Lesen seiner Geometrie) schlaegt dann
        # kurzzeitig fehl, obwohl eine Sekunde spaeter alles bereit
        # waere. Bisher fuehrte das zu einem sofortigen, harten Absturz
        # (sauber geloggt, aber das Frontend erschien nie - das alte
        # OSD blieb einfach stehen). Fix: bis zu 5 Versuche mit 0.5s
        # Pause dazwischen (insgesamt max. 2.5s zusaetzliche Wartezeit,
        # nur im Fehlerfall - beim ERSTEN, ueblichen erfolgreichen
        # Versuch entsteht KEINE zusaetzliche Verzoegerung).
        last_error = None
        for attempt in range(5):
            try:
                self._read_geometry()
                self.fd = os.open(FBDEV, os.O_RDWR)
                break
            except OSError as e:
                last_error = e
                LOG("Framebuffer-Oeffnen fehlgeschlagen (Versuch %d/5): %s"
                    % (attempt + 1, e))
                time.sleep(0.5)
        else:
            raise last_error
        self._map()
        self._rowcache = {}
        self._rectcache = {}   # eigener Cache fuer rect() (siehe dort) -
                                # getrennt von _rowcache, damit dessen
                                # Obergrenze nicht die selten wechselnden,
                                # teuren Hintergrundmuster von clear() mitloescht
        self._glyphcache = {}
        self._textcache = {}          # (text, scale, fg, bg) -> Liste von Byte-Zeilen
        self._textcache_order = []
        # BUGFIX (Nutzerwunsch "Scrollen soll butterweich sein" fuehrte zu
        # echten DRAGEND_PROFILE-Logs auf echter Hardware - siehe TEXTCACHE-
        # Zeilen dort): die fruehere Vermutung aus dem Kommentar unten
        # ("ob das an echten Cache-Fehltreffern liegt... laesst sich ohne
        # echte Daten nicht serioes unterscheiden") ist jetzt beantwortet -
        # Verdraengungen wurden auf echter Hardware nachweislich beobachtet
        # (von 0 auf ueber 350 waehrend weniger Minuten aktiven Scrollens
        # durch eine grosse NES-Sammlung angestiegen). 400 Eintraege waren
        # zu knapp: bereits gecachte, kuerzlich gesehene Titel flogen
        # wieder raus, bevor man zu ihnen zurueckscrollte, und mussten
        # unnoetig neu gerendert werden. Auf 2000 angehoben (~60MB bei
        # typischen Labellaengen, siehe Rechnung unten) - grosszuegiger
        # Puffer fuer auch sehr grosse Sammlungen, weiterhin unbedenklich
        # auf einem MiSTer mit ueblicherweise ≥1GB RAM.
        self._TEXTCACHE_LIMIT = 2000  # ~60MB bei typischen Labellaengen
        # NEU (Nutzerwunsch: "noch mehr Performance rausholen" - text()
        # hat bereits einen Ganze-Zeile-Cache, im echten Profiling aber
        # weiterhin 20-100ms je nach Bild). Ob das an echten Cache-
        # Fehltreffern liegt (z.B. weil _TEXTCACHE_LIMIT=400 bei einer
        # grossen Sammlung zu knapp bemessen ist und haeufig gesehene
        # Titel wieder rausfliegen) oder schlicht daran, dass beim
        # Scrollen staendig NEUE, noch nie gezeichnete Titel auftauchen
        # (strukturell kaum vermeidbar), laesst sich ohne echte Daten
        # nicht serioes unterscheiden - hier NUR mitzaehlen (guenstige
        # Zaehler-Erhoehung, kein spuerbarer Zusatzaufwand), Auswertung
        # optional ueber DRAGEND_PROFILE (siehe frontend.py).
        self._textcache_hits = 0
        self._textcache_misses = 0
        self._textcache_evictions = 0
        # None = noch nicht getestet, True/False = Ergebnis des ersten
        # Versuchs. Wird nur EINMAL probiert - unterstuetzt der Treiber es
        # nicht (ENOTTY/EINVAL o.ae.), schalten wir dauerhaft ab, statt bei
        # JEDEM Frame erneut einen fehlschlagenden ioctl-Aufruf zu riskieren.
        self._vsync_supported = None
        # NEU (Nutzerwunsch: "HDMI-Modus muss fluessiger laufen" - der
        # groesste verbliebene Einzelposten war der komplette Puffer-
        # Neuaufbau bei JEDEM Bild, selbst beim reinen Scrollen innerhalb
        # derselben Liste). Zaehler, der bei JEDEM vollstaendigen
        # Neuaufbau (clear() oder eine gleichwertige volle Pufferkopie)
        # hochgezaehlt wird - unabhaengig davon, WELCHE Funktion das
        # ausloest. _draw_page_items_impl() nutzt das, um zuverlaessig zu
        # erkennen, ob seit dem letzten eigenen vollen Neuaufbau
        # ZWISCHENDURCH irgendetwas anderes (Hilfe-Bildschirm, WoT,
        # Bestaetigungsdialog, Attract-Modus, ...) den Puffer ebenfalls
        # komplett neu geschrieben hat - nur dann ist der schnelle,
        # NICHT-loeschende Pfad wirklich sicher.
        self.full_redraw_gen = 0

        # NEUES FEATURE (Nutzerwunsch nach dem Bildschirmspiegel-Test:
        # "die 2-Sekunden-Aktualisierung sieht aus wie Standbilder,
        # geht das fluessiger?") - bewusst NICHT einfach das Intervall
        # verkuerzt (haette bei UNVERAENDERTEM Bildschirm, z.B. wenn
        # man einfach nur im Menue steht, unnoetig oft neu kodiert -
        # dieselbe Verschwendung, die full_redraw_gen oben schon fuer
        # den HDMI-Fast-Path vermeidet). Stattdessen: EIGENER Zaehler,
        # der bei JEDER tatsaechlich sichtbaren Aenderung hochzaehlt
        # (flip() UND flip_rows(), z.B. auch Laufschrift/Puls-Effekte -
        # full_redraw_gen oben zaehlt bewusst NUR bei vollen
        # Neuaufbauten, waere hierfuer also zu grob). Der Bildschirm-
        # spiegel-Hintergrund-Thread (siehe _screen_mirror_loop() in
        # frontend.py) prueft diesen Zaehler haeufiger, kodiert aber
        # nur neu, wenn sich seit dem letzten Schnappschuss wirklich
        # etwas geaendert hat.
        self.flip_gen = 0

    def mark_full_redraw(self):
        """Von JEDEM Code aufzurufen, der den Puffer auf andere Weise als
        clear() komplett neu schreibt (aktuell: die Hintergrundbild-Kopie
        in _draw_page_items_impl()) - haelt full_redraw_gen konsistent,
        egal auf welchem Weg ein voller Neuaufbau passiert ist."""
        self.full_redraw_gen += 1

    def _wait_vsync(self):
        """Wartet, falls moeglich, auf den naechsten vertikalen Bildwechsel -
        siehe FBIO_WAITFORVSYNC oben. Schlaegt der ioctl fehl (Treiber
        unterstuetzt es nicht), wird das dauerhaft vermerkt und nie wieder
        versucht - kostet dann nichts mehr, faellt einfach auf das bisherige
        Verhalten (ohne Vsync-Wartezeit) zurueck."""
        if self._vsync_supported is False:
            return
        try:
            fcntl.ioctl(self.fd, self.FBIO_WAITFORVSYNC, struct.pack("I", 0))
            self._vsync_supported = True
        except (OSError, AttributeError):
            self._vsync_supported = False

    def _read_geometry(self):
        w, h = open("/sys/class/graphics/fb0/virtual_size").read().split(",")
        self.width  = int(w)
        self.height = int(h)
        self.bpp    = int(open("/sys/class/graphics/fb0/bits_per_pixel").read())
        self.stride = int(open("/sys/class/graphics/fb0/stride").read())
        if self.bpp != 32:
            sys.exit("Nur 32bpp wird unterstuetzt, gefunden: %d" % self.bpp)
        self.size = self.stride * self.height

    def _map(self):
        self.mm = mmap.mmap(self.fd, self.size, mmap.MAP_SHARED,
                            mmap.PROT_READ | mmap.PROT_WRITE)
        self.buf = bytearray(self.size)

    def refresh_geometry(self):
        """Nach Rueckkehr aus einem Core neu einlesen - die Aufloesung
        kann sich geaendert haben (z.B. anderer Videomodus)."""
        old = (self.width, self.height, self.stride)
        self._read_geometry()
        if (self.width, self.height, self.stride) != old:
            try:
                self.mm.close()
            except Exception:
                pass
            self._map()
            self._rowcache.clear()

    @staticmethod
    def _vignette_row_variants(rgb, width, stride, levels=12, strength=0.30):
        """Vorberechnet `levels` unterschiedlich dunkle Varianten einer
        vollen Bildzeile in EINER Farbe - Grundlage fuer eine schnelle,
        zeilenbasierte Vignette (siehe clear()). NUR fuer Flaechen mit
        einer einzelnen Fuellfarbe geeignet (kein Bild), da eine ganze
        Zeile hier IMMER dieselbe Farbe hat - genau das macht die
        Kopie so billig (eine Slice-Zuweisung pro Zeile statt Pixel
        fuer Pixel).

        WICHTIG (Performance-Grund): eine echte, pixelgenaue radiale
        Vignette (mit Verlauf auch in X-Richtung, wie bei einem Foto)
        wurde direkt gemessen - ueber 1 Sekunde fuer eine einzelne
        1080p-Flaeche, selbst nur EINMALIG berechnet. Bei bis zu zwei
        Systemwechseln zwischen Hintergrundbildern (BgCache.LIMIT=2)
        haette das zu spuerbaren Haengern beim Navigieren gefuehrt -
        nicht vertretbar. Diese Zeilen-Variante ist rein vertikal
        (oben/unten dunkler, kein staerkerer Effekt in den Ecken) -
        optisch ein etwas einfacherer, aber immer noch deutlich
        hochwertiger wirkender Verlauf, dafuer um Groessenordnungen
        schneller (siehe _apply_vignette_rows())."""
        pad = b"\x00" * (stride - width * 4)
        r, g, b = rgb
        out = []
        for lvl in range(levels):
            f = 1.0 - strength * (lvl / max(1, levels - 1))
            drgb = (int(r * f), int(g * f), int(b * f))
            out.append(Framebuffer.px(drgb) * width + pad)
        return out

    @staticmethod
    def _apply_vignette_rows(out, height, stride, row_variants):
        """Setzt out (bytearray, bereits mit vollem Puffer-Speicher
        allokiert) zeilenweise aus den vorberechneten, unterschiedlich
        dunklen Varianten zusammen - Mitte hell, Rand oben/unten
        dunkler. Aufeinanderfolgende Zeilen mit derselben (quantisierten)
        Helligkeitsstufe werden zu einem Block zusammengefasst und per
        EINER Bytes-Multiplikation (variante * anzahl) statt einzelner
        Zeilen-Kopien geschrieben - deutlich weniger Einzeloperationen."""
        levels = len(row_variants)
        cy = height / 2.0
        y = 0
        while y < height:
            d = abs(y - cy) / cy if cy else 0.0
            lvl = min(levels - 1, int(d * d * (levels - 1)))
            run_start = y
            y += 1
            while y < height:
                d2 = abs(y - cy) / cy if cy else 0.0
                lvl2 = min(levels - 1, int(d2 * d2 * (levels - 1)))
                if lvl2 != lvl:
                    break
                y += 1
            run_len = y - run_start
            off = run_start * stride
            block = row_variants[lvl] * run_len
            out[off:off + len(block)] = block

    @staticmethod
    def _scale_brightness(pix, factor):
        """Skaliert die Helligkeit eines kompletten BGRA-Pixelpuffers
        (siehe blit()) um factor (0.0-1.0+) - per bytes.translate() mit
        vorberechneter 256-Werte-Tabelle, deutlich schneller als eine
        Python-Schleife pro Byte. Der Alpha-Kanal wird zwar mit
        skaliert (translate() kennt keine Kanaele, wirkt gleichmaessig
        auf JEDES Byte), das ist aber unschaedlich: blit() kopiert
        Pixel direkt ohne Alpha-Blending, der Alpha-Wert wird beim
        Zeichnen also nie ausgewertet. Fuer den Logo-Flacker-Effekt
        beim Start (siehe _draw_dragend_logo_boot()) - dieselbe
        Wirkung wie das bisherige dunkel/mittel/voll beim generischen
        D-Pad-Symbol, nur auf ein echtes Bild statt auf einfache
        Rechtecke angewendet."""
        factor = max(0.0, min(1.0, factor))
        lut = bytes(min(255, int(i * factor)) for i in range(256))
        return pix.translate(lut)

    @staticmethod
    def px(rgb):
        r, g, b = rgb
        return bytes((b, g, r, 0))

    @staticmethod
    def _darken(rgb, factor=0.82):
        r, g, b = rgb
        return (int(r*factor), int(g*factor), int(b*factor))

    def clear(self, rgb):
        key = ("bg", rgb, self.width, self.height)
        bg = self._rowcache.get(key)
        if bg is None:
            if VIGNETTE_ENABLED:
                variants = self._vignette_row_variants(rgb, self.width, self.stride)
                bg = bytearray(self.stride * self.height)
                self._apply_vignette_rows(bg, self.height, self.stride, variants)
            else:
                row = self.px(rgb) * self.width
                pad = b"\x00" * (self.stride - self.width * 4)
                bg = (row + pad) * self.height
            self._rowcache[key] = bg
        self.buf[:] = bg
        self.mark_full_redraw()

    def blend_rect(self, x, y, w, h, rgb, alpha):
        """Rechteck mit einer Farbe UEBERBLENDEN statt zu ueberschreiben -
        fuer Glow-/Schatten-Effekte. alpha=0..1 (0=keine Wirkung, 1=wie
        rect()). Kann NICHT gecacht werden (haengt vom vorhandenen
        Bildinhalt ab) - deshalb bewusst nur fuer kleine Bereiche
        (Glow-Ringe, Schatten), nicht fuer grosse Flaechen. Wie bei
        allen anderen Zeichenmethoden: schreibt nie mehr/weniger Bytes
        als der Zielbereich hat, um den Puffer nicht zu verschieben."""
        x = max(0, x); y = max(0, y)
        w = min(w, self.width - x); h = min(h, self.height - y)
        if w <= 0 or h <= 0 or alpha <= 0:
            return
        alpha = min(1.0, alpha)
        nb, ng, nr = rgb[2], rgb[1], rgb[0]  # BGRA-Reihenfolge im Puffer
        buflen = len(self.buf)
        need = w * 4
        for yy in range(y, y + h):
            off = yy * self.stride + x * 4
            end = off + need
            if end > buflen:
                continue
            row = bytearray(self.buf[off:end])
            for i in range(0, need, 4):
                row[i]   = int(row[i]   + (nb - row[i])   * alpha)
                row[i+1] = int(row[i+1] + (ng - row[i+1]) * alpha)
                row[i+2] = int(row[i+2] + (nr - row[i+2]) * alpha)
            if len(row) == need:
                self.buf[off:end] = row

    def blend_border(self, x, y, w, h, rgb, alpha, thickness=2):
        """Nur den RAND eines Rechtecks ueberblenden (vier duenne
        Streifen) statt der ganzen Flaeche - fuer Glow-Ringe deutlich
        billiger als blend_rect() auf die volle Flaeche, da nur der
        Umfang statt die Flaeche skaliert. Fuer KLEINE, bildschirm-
        unabhaengige Bereiche gedacht (z.B. Boxart-Rahmen/Schatten) -
        fuer breite, bildschirmfuellende Streifen (Listenmarkierung auf
        HDMI) stattdessen glow_border_fast() nutzen, siehe dort."""
        t = max(1, thickness)
        self.blend_rect(x, y, w, t, rgb, alpha)                    # oben
        self.blend_rect(x, y + h - t, w, t, rgb, alpha)             # unten
        self.blend_rect(x, y, t, h, rgb, alpha)                     # links
        self.blend_rect(x + w - t, y, t, h, rgb, alpha)             # rechts

    def glow_border_fast(self, x, y, w, h, base_bg, accent, alpha, thickness):
        """Schnelle Glow-Ring-Variante: statt jedes Pixel einzeln mit
        dem VORHANDENEN Bildinhalt zu mischen (blend_border, teuer bei
        breiten Bereichen), wird die Zielfarbe VORAB einmal berechnet
        (Grundfarbe + Akzent bei gegebenem Alpha) und dann ueber das
        normale, gecachte rect() gezeichnet. Auf breiten HDMI-Zeilen
        um ein Vielfaches schneller, weil rect() dieselbe Zeile fuer
        gleiche Breite wiederverwendet statt sie jedes Mal neu
        durchzurechnen. Nimmt an, dass der Hintergrund unter dem Ring
        etwa base_bg entspricht - bei aktivem Hintergrundbild kann die
        Farbe dadurch minimal abweichen, bewusster Kompromiss fuer
        Geschwindigkeit."""
        mixed = tuple(int(bg + (ac - bg) * alpha)
                      for bg, ac in zip(base_bg, accent))
        t = max(1, thickness)
        self.rect(x, y, w, t, mixed)
        self.rect(x, y + h - t, w, t, mixed)
        self.rect(x, y, t, h, mixed)
        self.rect(x + w - t, y, t, h, mixed)

    def blend_rect_fast(self, x, y, w, h, base_bg, color, alpha):
        """Wie blend_rect(), aber mit vorgemischter FESTER Farbe statt
        echter Pixel-fuer-Pixel-Mischung - fuer FLAECHEN (z.B. den
        Boxart-Schatten). Derselbe Trick wie glow_border_fast(): die
        Zielfarbe wird EINMAL berechnet statt pro Pixel, dann ueber
        das gecachte rect() gezeichnet. Wichtig bei groesseren
        Flaechen (z.B. schattenbreite = Cover-Breite) - echtes
        Pixel-Blending kostete hier auf HDMI bei einem Boxart-Schatten
        gemessen ueber 60% der gesamten Zeichenzeit einer Navigation
        (per cProfile bestaetigt), obwohl der Schatten selbst klein
        wirkt. Nimmt an, dass der Untergrund etwa base_bg entspricht -
        bei aktivem Hintergrundbild kann die Farbe dadurch leicht
        abweichen, bewusster Kompromiss fuer Geschwindigkeit."""
        mixed = tuple(int(bg + (c - bg) * alpha)
                      for bg, c in zip(base_bg, color))
        self.rect(x, y, w, h, mixed)

    def rect(self, x, y, w, h, rgb, scanlines=False):
        """scanlines=True: jede 2. Zeile dezent abgedunkelt (Retro-Look) -
        nur fuer reine Hintergrundflaechen, nicht fuer Markierungsbalken."""
        x = max(0, x); y = max(0, y)
        w = min(w, self.width - x); h = min(h, self.height - y)
        if w <= 0 or h <= 0:
            return
        # WICHTIG (Bugfix): _rectcache cacht nach (Farbe, EXAKTER Breite)
        # - bei leicht wechselnden Breiten (z.B. je nach Cover-
        # Seitenverhaeltnis, Glow-Ring-Position, Info-Textlaenge) sammelt
        # sich ueber viele Navigationen hinweg eine WACHSENDE Zahl nie
        # wieder verwendeter Eintraege an, die nie geloescht wird -
        # aehnliches Muster wie der in v1.32 behobene Pulsier-Cache-Bug,
        # nur an anderer Stelle. Per Differenzmessung bestaetigt: das
        # macht sich als spuerbare, mit der Zeit zunehmende Verzoegerung
        # bemerkbar. Einfache, sichere Absicherung: Cache bei
        # Ueberschreiten einer Obergrenze komplett leeren, statt einzelne
        # Eintraege aufwendig zu verwalten (LRU o.ae.) - der haeufige
        # Fall (dieselbe Farbe/Breite ueber mehrere Bilder hinweg, z.B.
        # Equalizer-Balken, Zeilen-Markierungen) bleibt dadurch weiterhin
        # schnell. Eigener Cache (nicht _rowcache), damit das Leeren
        # nicht die selten wechselnden, teuren Hintergrundmuster von
        # clear() mitreisst.
        if len(self._rectcache) > ROWCACHE_MAX_ENTRIES:
            self._rectcache.clear()
        key = (rgb, w)
        row = self._rectcache.get(key)
        if row is None:
            row = self.px(rgb) * w
            self._rectcache[key] = row
        row_dark = None
        if scanlines:
            key2 = (rgb, w, "dark")
            row_dark = self._rectcache.get(key2)
            if row_dark is None:
                row_dark = self.px(self._darken(rgb)) * w
                self._rectcache[key2] = row_dark
        for yy in range(y, y + h):
            off = yy * self.stride + x * 4
            use_row = row_dark if (scanlines and yy % 2) else row
            self.buf[off:off + w * 4] = use_row

    def rect_rounded(self, x, y, w, h, rgb, radius=None):
        """Wie rect(), aber mit abgerundeten Ecken. radius in Pixeln
        (bereits skaliert) - ohne Angabe ein kleiner, dezenter Wert.
        Kostet nur ein paar zusaetzliche, KUERZERE Randzeilen (die
        Eckenrundung), nicht die ganze Flaeche neu - der Mittelteil
        laeuft weiterhin ueber das normale, gecachte rect(). Die
        Einzugstabelle pro Randzeile wird nur einmal pro radius-Wert
        berechnet und mitgecacht, nicht bei jedem Aufruf neu."""
        x = max(0, x); y = max(0, y)
        w = min(w, self.width - x); h = min(h, self.height - y)
        if w <= 0 or h <= 0:
            return
        if radius is None:
            radius = max(1, min(w, h) // 8)
        radius = max(0, min(radius, w // 2, h // 2))
        if radius <= 0:
            self.rect(x, y, w, h, rgb)
            return
        key_ind = ("rounded_indent", radius)
        indents = self._rectcache.get(key_ind)
        if indents is None:
            indents = []
            r2 = radius * radius
            for ry in range(radius):
                dy = radius - ry - 1
                dx = 0
                while dx < radius and (radius - dx - 1) ** 2 + dy * dy <= r2:
                    dx += 1
                indents.append(radius - dx)
            self._rectcache[key_ind] = indents
        # PERFORMANCE-FIX (Nutzerwunsch: "noch mehr Performance rausholen,
        # vor allem HDMI" - echtes Profiling auf echter Hardware zeigte
        # rect_rounded() bei nur 3 Aufrufen pro Bild trotzdem 40-50ms
        # (~15ms PRO Aufruf) - 5-6x teurer als das normale, bereits
        # gecachte rect() (~2.5-3.5ms pro Aufruf). Ursache: die FORM der
        # Rundung (indents) war zwar schon gecacht, aber die
        # eigentlichen PIXEL-ZEILEN dafuer (px * rw) wurden bei JEDEM
        # Aufruf neu berechnet - obwohl sie sich bei gleicher Farbe und
        # gleicher Zeilenbreite nicht aendern. Fix: dieselbe (Farbe,
        # Breite)-Cache-Konvention wie rect() nutzen, im GLEICHEN
        # self._rectcache - Auswahl-Markierung und Cover-Panel-Karte
        # nutzen ueber viele Navigationen hinweg immer wieder dieselben
        # paar (Farbe, Randbreite)-Kombinationen, der Cache greift also
        # praktisch sofort ab dem zweiten Aufruf.
        if len(self._rectcache) > ROWCACHE_MAX_ENTRIES:
            self._rectcache.clear()
        for i, indent in enumerate(indents):
            rw = w - 2 * indent
            if rw <= 0:
                continue
            row_key = (rgb, rw)
            row = self._rectcache.get(row_key)
            if row is None:
                row = self.px(rgb) * rw
                self._rectcache[row_key] = row
            yy_top = y + i
            yy_bot = y + h - 1 - i
            if 0 <= yy_top < self.height:
                off = yy_top * self.stride + (x + indent) * 4
                self.buf[off:off + rw * 4] = row
            if yy_bot != yy_top and 0 <= yy_bot < self.height:
                off = yy_bot * self.stride + (x + indent) * 4
                self.buf[off:off + rw * 4] = row
        mid_top = y + radius
        mid_h = h - 2 * radius
        if mid_h > 0:
            self.rect(x, mid_top, w, mid_h, rgb)

    def _glyph_row(self, bits, scale, fg, bg):
        key = (bits, scale, fg, bg)
        row = self._glyphcache.get(key)
        if row is None:
            f = self.px(fg); b = self.px(bg)
            row = b"".join((f if bits >> i & 1 else b) * scale for i in range(8))
            self._glyphcache[key] = row
        return row

    def text(self, x, y, s, scale=2, fg=None, bg=None):
        if fg is None:
            fg = C_TEXT
        if bg is None:
            bg = C_BG
        cw = 8 * scale
        if y + 8 * scale > self.height or y < 0 or x < 0:
            return
        # Nur so viele Zeichen wie auf den Schirm passen - identischer
        # Abschneidepunkt wie die alte, zeichenweise Fassung (die bei
        # gx + cw > self.width abgebrochen hat), nur vorab statt
        # mitten in der Schleife berechnet.
        maxch = (self.width - x) // cw
        if maxch <= 0:
            return
        if len(s) > maxch:
            s = s[:maxch]
        if not s:
            return
        # Ganze Text-Zeile cachen: Beim Scrollen/Neuzeichnen sind die
        # meisten Labels bereits bekannt (Spieltitel, Menuepunkte usw.)
        # - dann reicht ein fertiger Streifen zum Blitten, statt jedes
        # Mal wieder Buchstabe fuer Buchstabe (und Zeile fuer Zeile pro
        # Buchstabe) zusammenzusetzen. Groesster Hebel bei den reinen
        # Zeichenkosten, siehe Kopfkommentar-Changelog.
        key = (s, scale, fg, bg)
        strip = self._textcache.get(key)
        if strip is None:
            self._textcache_misses += 1
            w4 = len(s) * cw * 4
            rows = [bytearray(w4) for _ in range(8 * scale)]
            for ci, ch in enumerate(s):
                code = ord(ch)
                # NEU (uebernommen von TheRealSutefan - Latin-1-Ergaenzung,
                # gleiches 8x8-Format wie FONT8X8): Umlaute/Akzente (ä/ö/ü/ß
                # usw.) wurden bisher als "?" dargestellt. FONT_EXTRA deckt
                # den Latin-1-Bereich 0xA0-0xFF ab; alles ausserhalb bleibt
                # beim bisherigen "?"-Rueckfall.
                if code <= 127:
                    _fnt, _gi = FONT8X8, code
                elif 0xA0 <= code <= 0xFF:
                    _fnt, _gi = FONT_EXTRA, code - 0xA0
                else:
                    _fnt, _gi = FONT8X8, 0x3F
                xo = ci * cw * 4
                for gy in range(8):
                    grow = self._glyph_row(_fnt[_gi * 8 + gy], scale, fg, bg)
                    for rep in range(scale):
                        rows[gy * scale + rep][xo:xo + cw * 4] = grow
            strip = [bytes(r) for r in rows]
            self._textcache[key] = strip
            self._textcache_order.append(key)
            if len(self._textcache_order) > self._TEXTCACHE_LIMIT:
                self._textcache_evictions += 1
                self._textcache.pop(self._textcache_order.pop(0), None)
        else:
            self._textcache_hits += 1
        w4 = len(strip[0])
        xo = x * 4
        for i, row in enumerate(strip):
            off = (y + i) * self.stride + xo
            self.buf[off:off + w4] = row

    def flip(self):
        # Erst auf den Vertical-Blank warten (falls unterstuetzt), DANN
        # schreiben - vermeidet Tearing bei der grossen Vollbild-Kopie.
        self._wait_vsync()
        # Direkte Slice-Zuweisung: mmap nimmt das bytearray ohne die
        # teure bytes()-Zwischenkopie (auf 1080p ~8 MB pro Frame).
        self.mm[:] = self.buf
        self.flip_gen += 1

    def flip_rows(self, y, h):
        """Nur einen Zeilenbereich auf den Schirm bringen (Laufschrift)."""
        y0 = max(0, y)
        y1 = min(self.height, y + h)
        if y1 <= y0:
            return
        self._wait_vsync()
        off = y0 * self.stride
        end = y1 * self.stride
        self.mm[off:end] = self.buf[off:end]
        self.flip_gen += 1

    def close(self):
        try:
            self.mm.close(); os.close(self.fd)
        except Exception:
            pass
