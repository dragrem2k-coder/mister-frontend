#!/usr/bin/env python3
"""Standard-Regressionstest fuer das MiSTer Custom Frontend.

Laeuft KOMPLETT OHNE echte MiSTer-Hardware (kein /dev/fb0, keine echten
Eingabegeraete noetig) - dafuer wird NUR die Framebuffer-Klasse durch eine
FakeFramebuffer ersetzt (echter Bildpuffer als bytearray statt mmap auf ein
echtes Geraet, Aufloesung frei waehlbar). InputManager() selbst kommt bereits
von Haus aus mit fehlender Hardware klar (scan_devices() faengt ein
fehlendes /proc/bus/input/devices sauber ab) und muss NICHT ersetzt werden.

WICHTIG (Lehre aus der Vergangenheit, siehe UEBERGABE.md Abschnitt 4):
dieser Test geht bewusst durch den ECHTEN Frontend()-Konstruktor, NICHT nur
mit von Hand gesetzten Attributen - genau das hatte frueher einen
Reihenfolge-Fehler in __init__() monatelang ueberdeckt.

Deckt ab:
  - 2 Aufloesungen: CRT (320x240) und HDMI (1920x1080)
  - Mehrere Navigationspfade: Kategorien-Menue (Seite 0), jede einzelne
    real vorhandene Kategorie auf Seite 1 (verschiedene item_i-Positionen:
    erster/mittlerer/letzter Eintrag, falls vorhanden), Ordner-Navigation
    eine Ebene tief (falls die Kategorie Unterordner hat), sowie ein
    paar Sonderzustaende (Beenden-Bestaetigungsdialog, Attract-Modus-
    Anzeige, RA-Core-Auswahlbildschirm ueber draw_core_choice_screen()
    direkt - genau die Stelle des zuletzt behobenen F11-Bugs).
  - Fuer jede Kombination: self.draw() (bzw. die jeweilige Zeichenfunktion)
    aufrufen und sicherstellen, dass KEINE Ausnahme auftritt.

Gibt am Ende eine Zusammenfassung aus und beendet sich mit Exit-Code 1,
falls mindestens eine Kombination fehlgeschlagen ist.
"""
import sys
import os
import traceback
import importlib.util

FRONTEND_PATH = os.environ.get(
    "FRONTEND_PY", "/home/claude/mister_frontend_git/frontend/frontend.py")

spec = importlib.util.spec_from_file_location("frontend_mod", FRONTEND_PATH)
frontend_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(frontend_mod)

RESOLUTIONS = [
    ("CRT 320x240", 320, 240, 32),
    ("HDMI 1920x1080", 1920, 1080, 32),
]


_FAKE_FB_SIZE = (320, 240)   # von make_frontend() vor jeder Instanziierung gesetzt


def _fake_fb_init(self, bpp=32):
    """Ersetzt NUR den hardwarenahen Teil von Framebuffer.__init__()
    (Geraet oeffnen/mmap/Geometrie aus /sys lesen) durch eine harmlose
    Attrappe. WICHTIG: patcht bewusst nur die __init__-METHODE auf der
    bestehenden, echten Framebuffer-KLASSE (nicht den Klassennamen im
    Modul selbst) - die eigenen Zeichen-Methoden (clear(), rect(),
    text(), flip() usw.) rufen intern teils 'Framebuffer.px(...)' als
    global aufgeloesten Klassennamen auf; wuerde man stattdessen den
    Namen 'Framebuffer' im Modul durch eine Fake-Klasse/-Funktion
    ersetzen, wuerden genau diese internen Aufrufe brechen. Alle
    Zeichen-Methoden bleiben dadurch die ECHTEN, unveraenderten
    Methoden - sie arbeiten ohnehin nur auf self.buf/self.stride/
    self.width/self.height, nie direkt auf einem echten Geraet."""
    width, height = _FAKE_FB_SIZE
    self.width = width
    self.height = height
    self.bpp = bpp
    self.stride = width * (bpp // 8)
    self.size = self.stride * self.height
    self.fd = -1                       # kein echtes Geraet
    self.mm = bytearray(self.size)      # normales bytearray statt mmap
    self.buf = bytearray(self.size)
    self._rowcache = {}
    self._rectcache = {}
    self._glyphcache = {}
    self._textcache = {}
    self._textcache_order = []
    self._TEXTCACHE_LIMIT = 400
    self._vsync_supported = False       # ioctl erst gar nicht versuchen


def _fake_fb_refresh_geometry(self):
    pass   # keine echte Geraete-Geometrie zum Neueinlesen vorhanden


def _fake_fb_close(self):
    pass


def _patch_framebuffer_class():
    """Patcht die hardwarenahen Methoden EINMAL fuer den kompletten
    Testlauf (nicht nur waehrend der Konstruktion) - draw()-Folgen
    koennen refresh_geometry()/close() an mehreren Stellen ausloesen,
    nicht nur im Konstruktor."""
    fb_cls = frontend_mod.Framebuffer
    fb_cls.__init__ = _fake_fb_init
    fb_cls.refresh_geometry = _fake_fb_refresh_geometry
    fb_cls.close = _fake_fb_close


def make_frontend(width, height):
    """Baut ein echtes Frontend()-Objekt (voller Konstruktor!) mit
    gefakter Framebuffer-Aufloesung."""
    global _FAKE_FB_SIZE
    _FAKE_FB_SIZE = (width, height)
    return frontend_mod.Frontend()


def run_case(results, label, fn):
    try:
        fn()
        results.append((label, True, None))
    except Exception:
        results.append((label, False, traceback.format_exc()))


def main():
    _patch_framebuffer_class()
    all_results = []
    for res_label, w, h, bpp in RESOLUTIONS:
        print("=== Aufloesung: %s ===" % res_label)
        fe = make_frontend(w, h)

        # --- Seite 0: Kategorien-Menue ---
        run_case(all_results, "%s | Kategorien-Menue" % res_label,
                  lambda fe=fe: fe.draw())

        # --- Jede real vorhandene Kategorie auf Seite 1 ---
        for cat_i, (name, node, syskey) in enumerate(fe.cats):
            fe.page = 1
            fe.cat_i = cat_i
            fe.nav_path = []
            fe._nav_position_stack = []
            fe.scroll = 0
            items = fe._display_items()

            positions = sorted(set(
                p for p in (0, len(items) // 2, len(items) - 1)
                if 0 <= p < len(items)))
            if not positions:
                positions = [0]   # leere Kategorie - trotzdem einmal zeichnen

            for pos in positions:
                fe.item_i = pos
                run_case(
                    all_results,
                    "%s | Kategorie '%s' (%d Eintraege) | Position %d"
                    % (res_label, name, len(items), pos),
                    lambda fe=fe: fe.draw())

            # --- Eine Ordnerebene tiefer, falls vorhanden ---
            folder_entry = next(
                ((label, arg) for label, kind, arg in items if kind == "folder"),
                None)
            if folder_entry:
                label, folder_name = folder_entry
                fe.nav_path = [folder_name]
                fe.item_i = 0
                fe.scroll = 0
                run_case(
                    all_results,
                    "%s | Kategorie '%s' -> Unterordner '%s'"
                    % (res_label, name, label),
                    lambda fe=fe: fe.draw())
                fe.nav_path = []

        # --- Sonderzustaende ---
        fe.page = 0
        fe.cat_i = 0
        run_case(all_results, "%s | Beenden-Bestaetigung" % res_label,
                  lambda fe=fe: (setattr(fe, "confirm_quit", True),
                                 fe.draw(), setattr(fe, "confirm_quit", False)))

        run_case(all_results, "%s | Attract-Modus-Anzeige" % res_label,
                  lambda fe=fe: fe.draw_attract() if hasattr(fe, "draw_attract")
                  else None)

        # --- RA-Core-Auswahlbildschirm direkt (Stelle des zuletzt
        # behobenen F11-Bugs) - kann hier nur EINMALIG durchlaufen und
        # sofort mit einer simulierten "back"-Aktion verlassen werden,
        # da die Methode selbst blockierend auf Eingaben wartet.
        class _FakeInputOnce:
            def __init__(self, action):
                self._action = action
                self._used = False

            def read_action(self, timeout=None):
                if not self._used:
                    self._used = True
                    return self._action
                return "back"

        real_inp = fe.inp
        fe.inp = _FakeInputOnce("back")

        def _core_choice(fe=fe):
            result = fe.draw_core_choice_screen("nes", "Testspiel")
            assert result is None, (
                "draw_core_choice_screen() sollte bei 'back' None liefern")
            # Genau der Fix vom letzten Mal: nach dem Abbruch muss ein
            # normaler draw() das Hauptmenue wieder korrekt herstellen -
            # hier nur sichergestellt, dass draw() an dieser Stelle
            # weiterhin fehlerfrei durchlaeuft (die Kontrollfluss-Stelle
            # selbst liegt in der Hauptschleife und wird durch den
            # Quelltextvergleich mit _enter_category() abgesichert, siehe
            # Commit-Nachricht).
            fe.draw()

        run_case(all_results,
                  "%s | RA-Core-Auswahlbildschirm + Abbruch (F11-Bugfix-Stelle)"
                  % res_label,
                  _core_choice)
        fe.inp = real_inp

        fe.fb.close()

    # --- Zusammenfassung ---
    failed = [r for r in all_results if not r[1]]
    print("")
    print("=" * 70)
    print("Ergebnis: %d/%d Kombinationen bestanden"
          % (len(all_results) - len(failed), len(all_results)))
    if failed:
        print("")
        print("FEHLGESCHLAGEN:")
        for label, ok, tb in failed:
            print("-" * 70)
            print(label)
            print(tb)
        sys.exit(1)
    else:
        print("Alle Kombinationen erfolgreich.")
        sys.exit(0)


if __name__ == "__main__":
    main()
