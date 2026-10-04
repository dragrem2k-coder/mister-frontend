#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Warum haengt das Betreten einer GEMISCHTEN Kategorie? (Build 239)

DER ANLASS ist eine Meldung vom Geraet, und sie ist ungewoehnlich
praezise, weil sie FUENF Kategorien nennt und keine sechste:

    "wenn ich in die kategorie weiterspielen gehe haengt er am anfang
     ganz schoen bis das frontend wahrscheinlich die covers dort
     geladen hat. RA-Erfolgsjaeger genauso. bei sammlung und 2026
     entdeckt sowie kurzweilige spiele genauso."

Weiterspielen, RA-Erfolgsjaeger, Sammlung, 2026 entdeckt, Kurzweilige
Spiele. Nicht SNES, nicht Mega Drive, nicht einer der 19 anderen
Systemordner - und der Nutzer hat 30278 Spiele, die Systemordner sind
also die GROESSEREN. Mehr Eintraege koennen es demnach nicht sein.

WAS DIESE FUENF UNTERSCHEIDET, ist eine einzige Eigenschaft: ihre
Eintraege kommen aus VERSCHIEDENEN SYSTEMEN. SNES ist SNES. In
"Weiterspielen" steht ein SNES-Spiel neben einem PSX-Spiel neben einem
Amiga-Spiel.

UND GENAU DARAN HAENGT DER COVER-ZUGRIFF. Beide Namensverzeichnisse
werden JE SYSTEM aufgebaut, beim ersten Fehltreffer fuer dieses System:

    _art_index(basis, syskey)   ein os.listdir je Cover-Ordner
    _docs_index(syskey)         ein os.listdir je Fremdordner x
                                DOCS_UNTERORDNER (zehn Namen)

Fuer eine Systemkategorie passiert das EINMAL. Fuer eine gemischte
Kategorie passiert es fuer JEDES System, das im ersten Fenster
vorkommt - und zwar alles in dem einen Moment, in dem die Seite zum
ersten Mal gezeichnet wird. Auf dem Geraet des Nutzers kostet ein
einzelnes os.listdir ueber einen Cover-Ordner laut Abschnitt H rund
167 ms.

DIESES WERKZEUG ZAEHLT NUR. Es behauptet keine Millisekunden - die
stehen auf dem Geraet, nicht hier. Es sagt, WIE VIELE
Verzeichnisdurchlaeufe das Betreten einer Kategorie ausloest, einmal
fuer eine Systemkategorie und einmal fuer eine gemischte. Die Zahl mal
167 ms ist die Wartezeit, die der Nutzer beschreibt.

Ausfuehren:
    python3 tools/diag_kategorie_betreten.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.art as ART          # noqa: E402

_uhr = time.perf_counter      # der Pruefstand friert monotonic() ein

# So sieht eine gemischte Kategorie beim Nutzer aus: zwoelf Systeme,
# bunt gemischt, wie "Weiterspielen" sie nach einem Monat Spielen hat.
SYSTEME = ("SNES", "Genesis", "NES", "PSX", "Amiga", "GBA",
           "TurboGrafx16", "N64", "MegaCD", "C64", "Saturn", "SMS")

# Das Geraet des Nutzers: ein os.listdir ueber einen Cover-Ordner mit
# 7700 Dateien kostete dort gemessene 167 ms (Abschnitt H, Build 152).
MS_JE_LISTDIR = 167.0


def _items(gemischt, anzahl=60):
    """Eintraege wie in einer Kategorie - aus einem System oder aus
    zwoelf."""
    aus = []
    for i in range(anzahl):
        sk = SYSTEME[i % len(SYSTEME)] if gemischt else "SNES"
        aus.append(("Spiel %03d" % i, "game",
                    ("/f/%s/%d.rom" % (sk, i), ".rom", sk, None, None)))
    return aus


def _zaehlen(fe, items, ansicht="liste", warmlauf=0):
    """Eine Kategorie betreten und mitschreiben, was dabei das
    Dateisystem anfaesst."""
    _, node, _ = fe.cats[0]
    node["folders"] = {}
    node["items"] = items
    node.pop("_display_items_cache", None)

    # ALLES leeren, was sich zwischen zwei Laeufen merken koennte - wir
    # wollen das BETRETEN messen, also den kalten Fall, nicht den
    # zweiten Besuch.
    #
    # DER ERSTE ENTWURF HAT HIER ZU WENIG GELEERT und daraufhin das
    # Gegenteil gemessen: der gemischte Lauf kam auf EIN os.listdir,
    # weil _thumb_fehlt noch voll war und deshalb gar nicht erst nach
    # einem Cover gesucht wurde. Eine Messung, die den zweiten Lauf
    # begünstigt, misst die Reihenfolge der Laeufe, nicht die Sache.
    ART._art_index_cache.clear()
    ART._docs_index_cache.clear()
    ART._thumb_fehlt.clear()
    ART._quell_stat.clear()
    ART._jpg_nachgezogen.clear()
    ART.quelldaten_vergessen()
    ART.negativ_vergessen()

    # DER RUHEMOMENT VOR DEM BETRETEN: so viele Leerlauf-Ticks, wie der
    # Nutzer braucht, um eine Kategorie auszusuchen. Gezaehlt wird
    # danach - es geht ja darum, was beim BETRETEN noch uebrig ist.
    if warmlauf:
        fe.page = 0
        fe.cat_i = 0
        fe._warmlauf_fertig_fuer = None
        for _ in range(warmlauf):
            if not fe._warmlauf_tick():
                break

    konto = {"listdir": 0, "pfade": [], "stat": 0}
    echt_listdir = os.listdir
    echt_stat = os.stat

    def _ld(pfad, *a, **k):
        konto["listdir"] += 1
        konto["pfade"].append(str(pfad))
        return echt_listdir(pfad, *a, **k)

    def _st(pfad, *a, **k):
        konto["stat"] += 1
        return echt_stat(pfad, *a, **k)

    os.listdir = _ld
    os.stat = _st
    try:
        fe.page = 1
        fe.cat_i = 0
        fe.nav_path = []
        fe.item_i = 0
        fe.scroll = 0
        fe.ansicht_setzen(ansicht)
        t0 = _uhr()
        fe._force_full_redraw = True
        fe.draw()
        ms = (_uhr() - t0) * 1000.0
    finally:
        os.listdir = echt_listdir
        os.stat = echt_stat
    konto["ms"] = ms
    konto["art_index"] = len(ART._art_index_cache)
    konto["docs_index"] = len(ART._docs_index_cache)
    return konto


def main():
    H.set_screen(1920, 1080)
    fe = H.make_frontend(page=1)

    print("=" * 70)
    print(" Was kostet das BETRETEN einer Kategorie? - %dx%d"
          % (fe.fb.width, fe.fb.height))
    print("=" * 70)
    print(" Gezaehlt wird, was der erste Seitenaufbau am Dateisystem")
    print(" anfasst. Die Millisekunden hier sind die des Containers mit")
    print(" warmem Verzeichnis-Zwischenspeicher und sagen nichts ueber")
    print(" das Geraet; die ZAHL der Durchlaeufe sagt alles.")
    print("")

    for ansicht in ("liste", "raster", "galerie"):
        print(" ANSICHT %s" % ansicht.upper())
        for gemischt, warm, name in (
                (False, 0, "ein System (wie SNES)"),
                (True, 0, "zwoelf Systeme, sofort betreten"),
                (True, 20, "zwoelf Systeme, nach Ruhemoment")):
            try:
                k = _zaehlen(fe, _items(gemischt), ansicht, warm)
            except Exception as e:                       # noqa: BLE001
                print("   %-38s -- uebersprungen (%s)"
                      % (name, type(e).__name__))
                continue
            print("   %-38s" % name)
            print("      %4d os.listdir, %5d os.stat, %6.2f ms"
                  % (k["listdir"], k["stat"], k["ms"]))
            print("      Namensverzeichnisse gebaut: %d Cover, %d Fremd"
                  % (k["art_index"], k["docs_index"]))
            print("      auf dem Geraet: %d x %.0f ms = %.1f s nur fuer"
                  " die Verzeichnisse"
                  % (k["listdir"], MS_JE_LISTDIR,
                     k["listdir"] * MS_JE_LISTDIR / 1000.0))
        print("")

    print("=" * 70)
    print(" Zu lesen als: beide Faelle zeigen dieselbe Seite mit")
    print(" derselben Zahl von Eintraegen. Steht beim gemischten Fall")
    print(" ein Vielfaches an Durchlaeufen, ist die Ursache gefunden -")
    print(" und sie ist nicht die Zahl der Spiele, sondern die Zahl der")
    print(" SYSTEME im ersten Fenster. Dagegen hilft kein schnelleres")
    print(" Zeichnen, sondern nur, die Verzeichnisse nicht genau in dem")
    print(" Moment zu bauen, in dem der Nutzer auf das Bild wartet.")
    print("=" * 70)


if __name__ == "__main__":
    main()
