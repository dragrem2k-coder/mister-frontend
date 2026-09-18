@echo off
REM ===========================================================
REM  Dragend - Miniaturen: die EXE bauen
REM
REM  Doppelklick genuegt. Das Skript prueft, ob Python da ist,
REM  holt die drei benoetigten Pakete und packt danach alles in
REM  eine einzelne Dragend-Miniaturen.exe im Unterordner dist\.
REM
REM  Python gibt es unter https://www.python.org/downloads/
REM  Beim Installieren bitte "Add python.exe to PATH" ankreuzen.
REM ===========================================================
setlocal
cd /d "%~dp0"

echo.
echo === Dragend - Miniaturen: EXE bauen ===
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Python wurde nicht gefunden.
    echo.
    echo Bitte von https://www.python.org/downloads/ installieren
    echo und dabei "Add python.exe to PATH" ankreuzen.
    echo.
    pause
    exit /b 1
)

for /f "delims=" %%v in ('python --version') do echo Gefunden: %%v
echo.

echo [1/3] Pakete holen ...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet paramiko pillow pyinstaller
if errorlevel 1 (
    echo FEHLER beim Installieren der Pakete.
    pause
    exit /b 1
)

echo [2/3] Packen ...
python -m PyInstaller --noconfirm --onefile --windowed ^
    --name Dragend-Miniaturen ^
    --add-data "dragend_kern.py;." ^
    dragend_miniaturen.py
if errorlevel 1 (
    echo FEHLER beim Packen.
    pause
    exit /b 1
)

echo [3/3] Fertig.
echo.
echo Die Datei liegt hier:
echo    %~dp0dist\Dragend-Miniaturen.exe
echo.
echo Sie laeuft eigenstaendig - Python wird danach nicht mehr
echo gebraucht, die Datei kann auf jeden Windows-Rechner.
echo.
pause
