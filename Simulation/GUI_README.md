# PA-Simulation GUI - Benutzerhandbuch

## Übersicht

Die **PA-Simulation GUI** ist eine benutzerfreundliche grafische Oberfläche zum Konfigurieren und Starten der `run_full_pa_simulation.py` Simulation, ohne die Kommandozeile direkt bedienen zu müssen.

## Systemanforderungen

- Python 3.8+
- tkinter (normalerweise mit Python enthalten)
- Alle Abhängigkeiten von `run_full_pa_simulation.py`

## Schnellstart

### Windows
Doppelklick auf `run_gui.bat` im `Simulation/` Verzeichnis.

Oder von der Kommandozeile:
```cmd
cd Simulation
python gui_run_pa_simulation.py
```

### Linux/Mac
Öffne Terminal und führe aus:
```bash
cd Simulation
chmod +x run_gui.sh
./run_gui.sh
```

Oder direkt:
```bash
python3 gui_run_pa_simulation.py
```

## GUI-Sektionen

### 1. **Grundparameter**
- **Anzahl Personas**: Wie viele Personen simuliert werden (1-100)
- **Anzahl Tage**: Wie viele Tage simuliert werden (1-365)
- **Startdatum**: Beginn der Simulation (Format: YYYY-MM-DD)
- **Basis Seed**: Für reproduzierbare Zufallszahlen (0-999999)

### 2. **LLM Parameter**
- **Modell**: Welches LLM-Modell verwendet werden soll
  - Standard: `gpt-4o-mini`
  - Weitere Optionen: `gpt-4`, `gpt-4-turbo`, `claude-3-opus`, etc.
- **Temperature**: Kreativität des Modells (0.0 = deterministisch, 2.0 = sehr kreativ)
  - Empfohlen: 0.7
- **Top P**: Nucleus-Sampling-Parameter (0.0-1.0)
  - Empfohlen: 1.0
- **LLM Seed**: Optional, für deterministisches LLM-Verhalten
- **Max Tokens**: Maximale Anzahl von Tokens pro Anfrage
  - LLM1: für Verhaltensentscheidungen (Standard: 2000)
  - LLM2: für weitere Verarbeitung (Standard: 1500)
  - State Assessment: für Zustandsbewertung (Standard: 1000)

### 3. **Verhaltensparameter** (optional)
Diese Parameter überschreiben die Standardwerte für Personas:
- **PA Stunden pro Woche**: Physische Aktivität (z.B. "4" oder "2,3,4" für verschiedene Personas)
- **Soziale Stunden pro Woche**: Soziale Aktivität
- **Caregiving Stunden pro Woche**: Betreuungsarbeit
- **Arbeitsstunden pro Woche**: Arbeitszeit

Format für mehrere Personas: komma-separierte Werte (z.B. "3,4,5" für 3 Personas)

### 4. **POI Entfernungen** (optional)
Punkte von Interesse Entfernungen in Kilometern:
- **Arbeitsplatz Entfernung**: Entfernung zum Arbeitsplatz
- **Indoor Aktivität Entfernung**: Entfernung zu Indoor-Aktivitäten
- **Outdoor Aktivität Entfernung**: Entfernung zu Outdoor-Aktivitäten

### 5. **Optionen** (Checkboxes)
- **Dry Run Mode**: Testet die Simulation ohne echte LLM-Anfragen
- **Resource Tracking**: Speichert Ressourcennutzung (CPU, Memory, etc.)
- **CodeCarbon Tracking**: Verfolgung des CO₂-Fußabdrucks (optional)
- **Verbose LLM Debug**: Detaillierte Debug-Informationen (sicherheitsbewusst)
- **Include Full Hourly Context**: Detaillierte stündliche Kontextinformationen
- **State Assessment JSON Mode**: JSON-Formatierung für Zustandsbewertung

### 6. **Output Verzeichnis**
- **Output Pfad**: Wo die Ergebnisse gespeichert werden
  - Standard: `output/full_pa_simulation/`
  - Klick "Durchsuchen..." um Verzeichnis zu ändern
  - Klick "Output Ordner öffnen" um Ordner im Explorer/Finder zu öffnen

## Aktionsbuttons

| Button | Funktion |
|--------|----------|
| **▶ Simulation starten** | Startet die Simulation mit aktuellen Einstellungen |
| **Stoppen** | Beendet die laufende Simulation |
| **Output Ordner öffnen** | Öffnet das Output-Verzeichnis |
| **Standardwerte zurücksetzen** | Setzt alle Felder auf Defaults |

## Output-Fenster

Das Ausgabefenster zeigt:
- Kommandozeile, die ausgeführt wird
- Live-Fortschritt der Simulation
- Fehler und Warnungen
- Abschlussmeldung mit Exit-Code

## Typische Workflows

### Schnelle Test-Simulation
1. Setze **Anzahl Personas** auf 2
2. Setze **Anzahl Tage** auf 1
3. Aktiviere **Dry Run Mode**
4. Klick "Simulation starten"

### Vollständige Simulation (produktiv)
1. Stelle **Anzahl Personas** auf gewünschte Anzahl (z.B. 10)
2. Stelle **Anzahl Tage** auf gewünschte Anzahl (z.B. 365)
3. Deaktiviere **Dry Run Mode**
4. Aktiviere **Resource Tracking** wenn gewünscht
5. Stelle **Modell** auf gewünschtes LLM
6. Wähle **Output Verzeichnis**
7. Klick "Simulation starten"

### Mit benutzerdefinierten Verhaltensparametern
1. Geben Sie unter **Verhaltensparameter** Werte ein
   - z.B. PA Hours: "3,4,5" für 3 Personas mit unterschiedlichen Aktivitätsleveln
2. Geben Sie **POI Entfernungen** ein (optional)
3. Klick "Simulation starten"

## Fehlerbehebung

### "Fehler beim Starten der GUI"
- Stelle sicher, dass Python installiert ist
- Überprüfe, dass tkinter verfügbar ist: `python -m tkinter`
- Führe das Skript aus dem `Simulation/` Verzeichnis aus

### Simulation endet sofort mit Fehler
- Überprüfe die Output-Fenster für Fehlermeldungen
- Validiere alle Eingabewerte (Daten, Zahlen, etc.)
- Stelle sicher, dass das Output-Verzeichnis zugänglich ist
- Überprüfe LLM-Konfiguration und API-Schlüssel

### "Modell nicht gefunden"
- Überprüfe, dass der LLM-Provider konfiguriert ist
- Stelle sicher, dass API-Schlüssel gesetzt sind (z.B. OPENAI_API_KEY)

### Timeout oder sehr lange Laufzeit
- Dies ist normal für große Simulationen (viele Personas/Tage)
- Starten Sie mit kleineren Zahlen zum Testen
- Deaktivieren Sie optionale Features (CodeCarbon, verbose debug)

## Eingabeformate

### Daten (Start-Datum)
Format: `YYYY-MM-DD` (z.B. `2026-01-15`)

### Zahlen (überall)
- Komma für Dezimalzahlen erlaubt (z.B. `0.7` oder `0,7`)
- Negative Zahlen werden abgelehnt

### Listen (Verhaltensparameter, POI-Entfernungen)
- Einzelwert: `4` - wird für alle Personas verwendet
- Mehrere Werte: `3,4,5` - ein Wert pro Persona
- Leer: Standard-Werte werden verwendet

## Fortgeschrittene Optionen

### State Assessment JSON Mode
Aktivieren, wenn OpenAI-kompatibles JSON-Objekt-Mode erwünscht ist.

### Verbose LLM Debug
Zeigt erweiterte Debug-Informationen (mit Sicherheitsaudit). Vorsicht: Kann sensible Informationen enthalten.

### CodeCarbon Tracking
Erfordert `codecarbon` Paket:
```bash
pip install codecarbon
```

## Konfigurationsspeicherung

Die GUI speichert die Konfiguration nicht automatisch. Um diese für später zu speichern:
1. Notiere die Einstellungen manuell
2. Oder verwende Kommandozeilenschnittstelle direkt mit gespeicherten Argumenten

## Command-Line Alternative

Du kannst die Simulation auch direkt von der Kommandozeile ausführen:
```bash
python -m Simulation.run_full_pa_simulation \
  --n-personas 5 \
  --n-days 30 \
  --start-date 2026-01-01 \
  --model gpt-4o-mini \
  --temperature 0.7
```

Die GUI generiert diese Befehle automatisch und zeigt sie im Output-Fenster.

## Support & Dokumentation

Für weitere Informationen siehe:
- [run_full_pa_simulation.py](run_full_pa_simulation.py) - Hauptskript mit Dokumentation
- Simulation/[README.md](../README.md) - Projekt-Dokumentation

---

**Version**: 1.0  
**Erstellt für**: PA-Simulation Masterarbeit  
**Letzte Aktualisierung**: 2026-06-19
