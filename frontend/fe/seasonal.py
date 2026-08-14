#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Saisonale Deko (Easter Egg): kleine, rein optische Jahreszeiten-
Anzeige am 24.12./31.12. Ausgelagert aus frontend.py (Modularisierung,
Git-Branch 'modular-refactor'). Komplett eigenstaendig.
"""
import time
from fe.translations import t

def seasonal_decoration():
    """Easter Egg (Nutzerwunsch): kleine, rein optische Jahreszeiten-
    Deko am 24.12. und 31.12. - liefert (text, farbe) oder None an
    jedem anderen Tag. Schaltet sich dadurch von selbst wieder ab,
    kein Freischalt-/Speicherzustand noetig, reiner Datumsvergleich
    bei jedem Zeichnen (vernachlaessigbare Kosten, wie die Uhrzeit in
    der Statuszeile)."""
    lt = time.localtime()
    if lt.tm_mon == 12 and lt.tm_mday == 24:
        return (t("seasonal_xmas"), (210, 70, 70))
    if lt.tm_mon == 12 and lt.tm_mday == 31:
        return (t("seasonal_nye"), (210, 175, 70))
    return None
