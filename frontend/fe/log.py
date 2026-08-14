#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logging - ausgelagert aus frontend.py (Modularisierung, Git-Branch
'modular-refactor'). Bewusst als eigenes, winziges Modul OHNE jede
Abhaengigkeit zum restlichen Code (nur os/time) - wird von mehreren
anderen ausgelagerten Modulen gebraucht (z.B. fe/framebuffer.py) und
haette sonst einen Zirkelbezug zu frontend.py selbst ausgeloest.
"""
import os, time

LOGFILE = "/tmp/frontend.log"
LOG_MAX_BYTES = 512 * 1024      # ab dieser Groesse wird gekuerzt
LOG_KEEP_BYTES = 256 * 1024     # so viel vom Ende bleibt erhalten
_log_call_count = 0

def _trim_log_if_needed():
    """Log-Datei kuerzen, falls sie zu gross geworden ist - behaelt nur
    das juengste Ende. Wird nicht bei jedem LOG()-Aufruf geprueft
    (Dateigroesse abfragen kostet Zeit), sondern nur gelegentlich -
    das Log waechst nicht so schnell, dass es dazwischen aus dem
    Ruder laeuft."""
    try:
        size = os.path.getsize(LOGFILE)
    except OSError:
        return
    if size <= LOG_MAX_BYTES:
        return
    try:
        with open(LOGFILE, "rb") as f:
            f.seek(-LOG_KEEP_BYTES, os.SEEK_END)
            tail = f.read()
        # Am ersten Zeilenumbruch abschneiden, damit keine abgeschnittene
        # Zeile am Anfang des gekuerzten Logs steht.
        nl = tail.find(b"\n")
        if nl >= 0:
            tail = tail[nl + 1:]
        with open(LOGFILE, "wb") as f:
            f.write(("--- Log gekuerzt (war > %d KB) ---\n"
                     % (LOG_MAX_BYTES // 1024)).encode())
            f.write(tail)
    except OSError:
        pass

def LOG(msg):
    global _log_call_count
    try:
        _log_call_count += 1
        if _log_call_count % 50 == 0:
            _trim_log_if_needed()
        with open(LOGFILE, "a") as f:
            f.write("%s  %s\n" % (time.strftime("%H:%M:%S"), msg))
    except OSError:
        pass
