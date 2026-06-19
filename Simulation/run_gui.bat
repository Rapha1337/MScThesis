@echo off
REM Startet die PA-Simulation GUI auf Windows

cd /d "%~dp0"
python gui_run_pa_simulation.py

if errorlevel 1 (
    echo.
    echo Fehler beim Starten der GUI!
    echo Stelle sicher, dass Python installiert ist und du dich im Simulation-Verzeichnis befindest.
    pause
)
