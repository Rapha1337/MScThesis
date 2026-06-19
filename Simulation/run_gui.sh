#!/bin/bash
# Startet die PA-Simulation GUI auf Linux/Mac

cd "$(dirname "$0")"
python3 gui_run_pa_simulation.py

if [ $? -ne 0 ]; then
    echo ""
    echo "Fehler beim Starten der GUI!"
    echo "Stelle sicher, dass Python installiert ist und du dich im Simulation-Verzeichnis befindest."
fi
