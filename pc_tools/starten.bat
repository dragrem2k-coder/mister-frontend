@echo off
REM ===========================================================
REM  Dragend - Miniaturen: direkt starten, ohne EXE zu bauen
REM
REM  Braucht Python auf dem Rechner. Wer lieber eine einzelne
REM  EXE moechte: bauen.bat doppelklicken.
REM ===========================================================
setlocal
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Python wurde nicht gefunden.
    echo Bitte von https://www.python.org/downloads/ installieren
    echo und dabei "Add python.exe to PATH" ankreuzen.
    pause
    exit /b 1
)

python -c "import paramiko, PIL" >nul 2>&1
if errorlevel 1 (
    echo Fehlende Pakete werden einmalig nachinstalliert ...
    python -m pip install --quiet paramiko pillow
)

python dragend_miniaturen.py
