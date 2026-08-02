@echo off
REM ============================================================
REM  Stream-Overlay fuer OBS einrichten (Windows-Doppelklick)
REM  Startet obs_setup.py im selben Ordner.
REM ============================================================
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (
    py -3 obs_setup.py %*
    goto ende
)

where python >nul 2>&1
if %errorlevel%==0 (
    python obs_setup.py %*
    goto ende
)

echo.
echo Python 3 wurde nicht gefunden.
echo.
echo Entweder Python installieren (https://www.python.org/downloads/,
echo beim Setup den Haken "Add Python to PATH" setzen) -
echo ODER ganz ohne diese Datei arbeiten:
echo.
echo   In OBS einfach eine Browser-Quelle anlegen mit der URL
echo   http://DEINE-MISTER-IP:8080/
echo.
echo Das funktioniert genauso gut, nur ohne lokale Kopie.
echo.

:ende
echo.
pause
