@echo off
TITLE Systemtreff AI Launcher
COLOR 0A
chcp 65001 > nul

echo.
echo  Startet grafische Oberflaeche...
echo.

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [FEHLER] Venv nicht gefunden!
    pause
    exit
)

:: Startet die GUI ohne schwarzes Konsolenfenster im Hintergrund (optional pythonw, hier python für Debugging)
python app.py