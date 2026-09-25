"""Modulare Aufteilung von frontend.py - Paket-Init.

WICHTIG: Dies ist ein SEPARATER, experimenteller Zweig
(Git-Branch 'modular-refactor', eigener Ordner frontend_modular/).
Der bestehende, produktiv genutzte Stand in frontend/frontend.py
bleibt davon komplett unberuehrt.
"""

# ---------------------------------------------------------------------------
# PAKET-VERSION (Build 186)
# ---------------------------------------------------------------------------
# WARUM ES DAS GIBT - der Anlass, in einer Zeile:
#
#     AttributeError: 'ArtCache' object has no attribute 'warten_vergessen'
#
# Auf dem Geraet eines Nutzers lag frontend.py aus Build 184 neben einem
# fe/art.py, das aelter war als Build 180. Die Methode kam mit 180 dazu.
# Der Absturz kam nicht beim Start, sondern Stunden spaeter beim ersten
# Druck auf eine Pfeiltaste - und sah aus wie ein Kernel- oder
# Anzeigeproblem. Eine Stunde Fehlersuche an der voellig falschen Stelle.
#
# Ursache war nicht der Installer (der kopiert fe/*.py mit), sondern ein
# von Hand eingespieltes Teil-ZIP. Das laesst sich nicht verbieten - also
# soll es wenigstens SOFORT auffallen.
#
# REGEL: Wer in fe/ etwas ergaenzt, das frontend.py braucht, erhoeht
# diese Zahl UND die Mindestanforderung in frontend.py. Die Zahl ist
# nicht die Build-Nummer - sie zaehlt nur, wenn sich die Schnittstelle
# zwischen frontend.py und diesem Paket aendert.
PAKET_VERSION = 1
