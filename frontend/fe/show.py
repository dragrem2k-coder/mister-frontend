# -*- coding: utf-8 -*-
"""--show: was drin ist, wie es eingestellt ist, wie schnell es laeuft.

WUNSCH DES NUTZERS: "kann man ein zweites benchmark machen was die
funktionen einstellmoeglichkeiten design und so zeigt auch wie schnell
das scrollen mittlerweile ist? als vorfuehrung quasi?"

DER UNTERSCHIED ZU --bench, und er ist der Grund fuer ein eigenes
Modul: --bench ist ein MESSGERAET. Seine Zahlen sind auf
Vergleichbarkeit gebaut (feste Testbilder, feste Wiederholungen,
Abschnitte A bis J), und sie sind fuer jemanden gedacht, der an diesem
Frontend arbeitet. --show ist ein BERICHT. Er ist fuer jemanden
gedacht, der wissen will, was das Ding kann und ob es schnell ist -
und er soll sich vorlesen lassen, ohne dass man eine Legende braucht.

WAS HIER NICHT HINEINGEHOERT: eine von Hand gepflegte Liste der
Funktionen. So eine Liste ist nach drei Builds falsch, und zwar still.
Alles, was hier steht, wird deshalb aus dem gelesen, was das Frontend
ohnehin schon weiss:

  - die Einstellungen aus fe/menu.py (system_items) - also GENAU die
    Liste, die der Nutzer im Systemmenue sieht, mit den Werten, die
    gerade gelten
  - die Ansichten aus fe/settings.py, die Farbschemata aus fe/menu.py
  - der Bestand und die Kategorien aus dem laufenden Frontend
  - die Masken und Schriften, die auf SEINER Karte liegen
  - die Geschwindigkeit aus derselben Schrittfunktion, die auch
    Abschnitt J des Bench benutzt (fe/bench.py: schritt_funktion) -
    zwei Fassungen desselben Schritts waeren zwei Gelegenheiten,
    auseinanderzulaufen

Ausgegeben wird auf die Konsole und zusaetzlich in eine Datei, genau
wie beim Bench.
"""
import os
import time

SHOW_VERSION = 1

BREITE = 62


def _linie(zeichen="-"):
    return zeichen * BREITE


def _menge(n):
    """Eine Zahl mit Tausenderpunkten - 30278 liest sich schlecht."""
    try:
        return "{:,}".format(int(n)).replace(",", ".")
    except Exception:                                    # noqa: BLE001
        return str(n)


def _zaehlen(node, tiefe=0):
    """Eintraege eines Kategoriebaums zaehlen, Ordner mitgerechnet."""
    if tiefe > 12 or not isinstance(node, dict):
        return 0
    n = len(node.get("items", ()) or ())
    for unter in (node.get("folders", {}) or {}).values():
        n += _zaehlen(unter, tiefe + 1)
    return n


# ---------------------------------------------------------------------------
# DIE ABSCHNITTE
# ---------------------------------------------------------------------------

def _kopf(b, fe, S, A, fm):
    b("=" * BREITE)
    b(" Dragend - was drin ist, wie es steht, wie schnell es laeuft")
    b("=" * BREITE)
    try:
        import json
        hier = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(hier, "LATEST_BUILD.json")) as f:
            b(" Build      : %s" % json.load(f).get("build_id", "?"))
    except Exception:                                    # noqa: BLE001
        pass
    b(" Zeit       : %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    try:
        u = os.uname()
        b(" System     : %s %s (%s)" % (u.sysname, u.release, u.machine))
    except Exception:                                    # noqa: BLE001
        pass
    fbo = getattr(fe, "fb", None)
    if fbo is not None:
        b(" Anzeige    : %dx%d" % (fbo.width, fbo.height))
    try:
        if A._LIB is not None:
            b(" C-Modul    : libdragend Version %d"
              % A._LIB.dragend_version())
        else:
            b(" C-Modul    : nicht geladen - alles rechnet in Python")
    except Exception:                                    # noqa: BLE001
        pass
    b("")


def _abschnitt_bestand(b, fe):
    b(_linie())
    b(" DEINE SAMMLUNG")
    b(_linie())
    kats = list(getattr(fe, "cats", ()) or ())
    gesamt = 0
    zeilen = []
    for name, node in kats:
        n = _zaehlen(node)
        gesamt += n
        if n:
            zeilen.append((n, name))
    b("   %s Spiele in %d Kategorien" % (_menge(gesamt), len(zeilen)))
    b("")
    zeilen.sort(reverse=True)
    # Die groessten zehn, und dann eine Zeile fuer den Rest - eine
    # Liste aus 24 Zeilen liest niemand.
    for n, name in zeilen[:10]:
        b("   %-34s %9s" % (name[:34], _menge(n)))
    if len(zeilen) > 10:
        rest = sum(n for n, _ in zeilen[10:])
        b("   %-34s %9s" % ("... und %d weitere" % (len(zeilen) - 10),
                            _menge(rest)))
    b("")


def _abschnitt_aussehen(b, fe, S, MENU, MASKEN, SCHRIFTEN):
    b(_linie())
    b(" WIE ES AUSSEHEN KANN")
    b(_linie())
    try:
        namen = MENU.THEME_NAMES_DE
        b("   Farbschemata : %d  (%s)"
          % (len(namen), ", ".join(list(namen.values())[:6])))
    except Exception:                                    # noqa: BLE001
        pass
    try:
        b("   Ansichten    : %s" % ", ".join(S.ANSICHTEN))
    except Exception:                                    # noqa: BLE001
        pass
    # Masken und Schriften liegen auf SEINER Karte - wir liefern keine
    # mit. Gezaehlt wird, was da ist.
    try:
        n = MASKEN.BAUM.zaehlen(MASKEN.MASKEN_DIR, ".txt")
        p = len(MASKEN.preset_masken())
        b("   Lochmasken   : %d aus %s%s"
          % (n, MASKEN.MASKEN_DIR,
             " (davon %d als Preset empfohlen)" % p if p else ""))
        from fe.translations import t as _t
        b("                  Modus: %s"
          % ", ".join(_t("masken_modus_" + m) for m in MASKEN.MODI))
    except Exception:                                    # noqa: BLE001
        pass
    try:
        n = SCHRIFTEN.BAUM.zaehlen(SCHRIFTEN.SCHRIFTEN_DIR, ".pf")
        b("   Schriften    : %d aus %s"
          % (n, SCHRIFTEN.SCHRIFTEN_DIR))
    except Exception:                                    # noqa: BLE001
        pass
    b("")
    b("   Mitgeliefert wird davon nichts: Masken und Schriften liegen")
    b("   auf deiner Karte, wir lesen sie nur.")
    b("")


def _einstellungen(b, MENU):
    """GENAU die Liste aus dem Systemmenue - mit den Werten von jetzt.

    Von Hand gepflegt waere sie nach drei Builds falsch. So ist sie es
    nie: was im Menue steht, steht hier."""
    b(_linie())
    b(" WAS SICH EINSTELLEN LAESST (und wie es gerade steht)")
    b(_linie())
    try:
        baum = MENU.system_items()
    except Exception as e:                               # noqa: BLE001
        b("   -- nicht lesbar (%s)" % type(e).__name__)
        b("")
        return
    n = [0]

    def _zeig(knoten, tiefe=0):
        if tiefe > 4 or not isinstance(knoten, dict):
            return
        for name, unter in sorted((knoten.get("folders", {}) or {}).items()):
            b("")
            b("   " + "  " * tiefe + "[ %s ]" % name)
            _zeig(unter, tiefe + 1)
        for e in (knoten.get("items", ()) or ()):
            try:
                text = str(e[0])
            except Exception:                            # noqa: BLE001
                continue
            n[0] += 1
            # Die Beschriftung im Menue sagt "Wert -> was passiert".
            # Hier interessiert der Wert, nicht die Taste.
            text = text.split(" -> ")[0]
            b("   " + "  " * tiefe + "- " + text[:BREITE - 6 - 2 * tiefe])

    _zeig(baum)
    b("")
    b("   %d Einstellungen und Aktionen im Systemmenue." % n[0])
    b("")


def _tempo(b, fe, S, BENCH, schritte=20):
    """WIE SCHNELL - in ms und in Schritten je Sekunde.

    Gemessen mit DERSELBEN Schrittfunktion wie Abschnitt J des Bench
    (fe/bench.py: schritt_funktion/fenster_spanne). Zwei Fassungen
    desselben Schritts waeren zwei Gelegenheiten auseinanderzulaufen -
    und genau daran ist Abschnitt J in Build 218 schon einmal
    gescheitert."""
    b(_linie())
    b(" WIE SCHNELL ES SCROLLT")
    b(_linie())
    fbo = getattr(fe, "fb", None)
    if fbo is None or not hasattr(fe, "ansicht_setzen"):
        b("   -- kein Framebuffer, uebersprungen")
        b("")
        return
    b("   Ein Scrollschritt, alles warm, %d Schritte je Ansicht."
      % schritte)
    b("   'Schritte/s' ist das, was beim Gedrueckthalten ankommt.")
    b("")
    b("   %-22s %10s %12s" % ("", "je Schritt", "Schritte/s"))

    merk_page = getattr(fe, "page", 0)
    merk_cat = getattr(fe, "cat_i", 0)
    merk_item = getattr(fe, "item_i", 0)
    try:
        kat_i, kat_n, kat_name = BENCH._groesste_kategorie(fe)
        for seite, name in ((0, "Hauptseite"), (1, "Spieleliste")):
            fe.page = seite
            if seite == 1:
                if kat_i is None:
                    continue
                fe.cat_i = kat_i
                fe.nav_path = []
            for ansicht in S.ANSICHTEN:
                try:
                    if seite == 0:
                        fe.ansicht_haupt_setzen(ansicht)
                    else:
                        fe.ansicht_setzen(ansicht)
                except Exception:                        # noqa: BLE001
                    continue
                schritt = BENCH.schritt_funktion(fe, seite)
                try:
                    # Zweimal warmlaufen: beim ersten Durchgang werden
                    # Miniaturen gerechnet, erst beim zweiten liegt
                    # alles im RAM. Ohne das misst dieser Abschnitt das
                    # Rechnen von Covern.
                    for _r in range(2):
                        for i in range(schritte):
                            schritt(i)
                except Exception:                        # noqa: BLE001
                    b("   %-22s -- uebersprungen" % (name + " " + ansicht))
                    continue
                fenster = BENCH.fenster_spanne(fe, seite)
                t0 = time.monotonic()
                for i in range(schritte):
                    schritt(i % fenster)
                ms = (time.monotonic() - t0) * 1000.0 / schritte
                b("   %-22s %7.1f ms %9.0f" % (name + " " + ansicht, ms,
                                               1000.0 / max(0.01, ms)))
        if kat_i is not None:
            b("")
            b("   gemessen in: %s (%s Eintraege)" % (kat_name,
                                                     _menge(kat_n)))
    finally:
        fe.page = merk_page
        fe.cat_i = merk_cat
        fe.item_i = merk_item
    b("")
    b("   Zum Einordnen: ein Bild braucht bei 60 Hz 16,7 ms. Was")
    b("   darunter liegt, laeuft fluessig; was darueber liegt, merkt")
    b("   man beim Gedrueckthalten - und genau daran wird gearbeitet.")
    b("")


def _wo(b, S, MASKEN, SCHRIFTEN):
    b(_linie())
    b(" WO WAS LIEGT")
    b(_linie())
    import fe.paths as P
    da = [p for p in P.GAMES_BASES if os.path.isdir(p)]
    b("   Spiele       : %s" % (", ".join(da) if da else "-"))
    b("   Lochmasken   : %s" % MASKEN.MASKEN_DIR)
    b("   Presets      : %s" % MASKEN.PRESETS_DIR)
    b("   Schriften    : %s" % SCHRIFTEN.SCHRIFTEN_DIR)
    b("   Einstellungen: /media/fat/frontend/")
    b("")
    b("   Geschrieben wird ausschliesslich unter")
    b("   /media/fat/frontend/ - MiSTers eigene Ordner werden gelesen")
    b("   und nicht angefasst.")
    b("")


def lauf(fe, fm, A, S, MENU, MASKEN, SCHRIFTEN, BENCH, startdauer=None,
         log=None):
    """Den ganzen Bericht bauen und als Text zurueckgeben."""
    zeilen = []

    def b(text=""):
        zeilen.append(text)
        print(text)

    _kopf(b, fe, S, A, fm)
    if startdauer is not None:
        print_ = "   Start bis Kategorien bereit: %.1f s" % startdauer
        b(_linie())
        b(" START")
        b(_linie())
        b(print_)
        b("")
    _abschnitt_bestand(b, fe)
    _abschnitt_aussehen(b, fe, S, MENU, MASKEN, SCHRIFTEN)
    _einstellungen(b, MENU)
    _tempo(b, fe, S, BENCH)
    _wo(b, S, MASKEN, SCHRIFTEN)
    b("=" * BREITE)
    b(" Ende. Nichts auf der Karte wurde veraendert.")
    b("=" * BREITE)
    if log:
        log("--show durchgelaufen (%d Zeilen)" % len(zeilen))
    return "\n".join(zeilen) + "\n"
