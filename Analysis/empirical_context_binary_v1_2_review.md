# Prüfnotiz: binäre Kontextklassifikation (29.10.2026)

Implementiert als separate **Auswertungsentscheidung** für bestehende empirische
PA-v1.2-Läufe. `final_context_score > 0` ergibt `supportive`, andernfalls
`non_supportive`. Score 0 bleibt ausdrücklich non_supportive. Die bestehende
Funktion `Analysis.final_h1_h4_analysis.classify_record` berechnet sämtliche
Dimensionen und Overrides unverändert. Die alte dreistufige MA-Auswertung bleibt
erhalten. Es wurden keine Simulationen oder LLM-Aufrufe gestartet.

Neue Dateien:

- `Analysis/empirical_context_binary_v1_2.py`: validiert bestehende Runs, verbindet
  Trace und Stundenkontexte eindeutig und erstellt aggregierte Gegenüberstellungen.
- `Analysis/tests/test_empirical_context_binary_v1_2.py`: synthetische Regressionstests.
- Diese Prüfnotiz mit Reproduktionsbefehl und Testergebnissen.

Die bereits vor Arbeitsbeginn unversionierten Dateien
`Analysis/seed_screen_context_v1_2.py` und
`Analysis/tests/test_seed_screen_context_v1_2.py` wurden nicht bearbeitet.
Keine Änderungen an Simulation, Prompts, Sampling oder MA-Routine.
Nichts gestaged, committed oder gepusht.

Reproduktion aus dem Repository-Stammverzeichnis (neues Zielverzeichnis verwenden):

```powershell
python Analysis/empirical_context_binary_v1_2.py `
  --seed14-dir Simulation/output/live_90d_real_medoids_20261014_225252 `
  --seed96-dir Simulation/output/live_90d_context_stress_seed96_20261015_161827 `
  --output-dir Analysis/outputs/empirical_context_binary_v1_2_final_20261029
```

Ergebnisdateien im lokal ignorierten Zielverzeichnis:

- `report.md`: alte/neue Klassifikation, Tage, PA-Tage, PA-Anteile, deskriptive
  95%-Wilson-Intervalle und Tage ohne Downtime, insgesamt, pro Seed und für jede
  Kombination aus Seed und Medoid (M1–M4).
- `summary.csv`: dieselben Aggregate mit ungerundeten Anteilen und Intervallen.
- `provenance.json`: SHA-256-Prüfsummen der fünf gelesenen Quelldateien je Run,
  der MA-Routine und der neuen Auswertung; Quelldateien vor/nach Auswertung identisch.

Alle **720** Persona-Tage bleiben enthalten (360 je Seed, 90 je Medoid/Seed).
Insgesamt 389 PA-Tage in beiden Klassifikationen. Alt: supportive 260/176,
neutral 313/206, hindering 147/7 (Tage/PA-Tage). Neu: supportive 474/317,
non_supportive 246/72. Alle 131 Tage ohne Downtime sind enthalten und
non_supportive (Seed 14: 72; Seed 96: 59). Keine fehlenden/ungültigen finalen Scores.
Die Gruppensummen wurden zusätzlich gegen 720/360/90 geprüft.

Gezielte synthetische Prüfung:

```powershell
python -m pytest Analysis/tests/test_empirical_context_binary_v1_2.py Analysis/tests/test_seed_screen_context_v1_2.py -q
```

**31 bestanden**: 27 neue Tests plus 4 bestehende synthetische Kontext-Tests.
Abgedeckt sind die fünf Score-Grenzfälle, ungültige/fehlende Scores, alle drei
Krankheitsstärken, Tage ohne Downtime im primären Nenner, unveränderte
Entscheidungspayloads einschliesslich Wahrscheinlichkeiten und Dauer,
unveränderte Dimensionen, fehlerhafte Joins und Stundenkontexte, vollständige
Runs sowie ein Durchlauf mit **720 ausschliesslich synthetischen Beobachtungen**.
Dieser prüft auch unveränderte Quellen, Aggregate ohne Persona-Kennungen und
das Verweigern eines versehentlichen Überschreibens vorhandener Ergebnisse.

Ein anfänglich zu breit gestarteter Lauf `python -m pytest Analysis/tests -q`
ergab 50 bestanden und 2 Fehler in bestehenden T1-Regressionsprüfungen:
`test_prepared_t1_regression_reproduces_frozen_full_and_held_out_estimates` und
`test_medoid_ids_are_excluded_only_from_held_out_calibration`. Beide scheiterten
vor dem Einlesen an der fehlenden Datei `03_prepared_t1_inputs.csv`. Für diese
Aufgabe wurden keine T1-Rohdaten zu Tests bereitgestellt; die gezielte Prüfung
verwendet ausschliesslich synthetische Daten.

Wilson-Intervalle sind rein deskriptiv: Abhängigkeiten wiederholter Tage,
zeitlicher Feedbackverlauf, Auswahl von nur vier Medoids und mögliche Seed-Auswahl
werden nicht modelliert. Eine Bevölkerungsinferenz oder kausale Wirkung der neuen
Klassifikation ist daraus nicht ableitbar. Der Laufordner von Seed 96 bezeichnet
ihn als Kontext-Stresstest. Die neue supportive-Gruppe enthält zusätzlich Score +1;
sie ist deshalb nicht direkt mit der alten supportive-Gruppe gleichzusetzen.
Leere Kategorien werden mit 0 Tagen und undefiniertem Anteil/Intervall ausgewiesen.

Keine Tagesdatensätze, T1-Kennungen oder privaten Entscheidungstexte werden
exportiert. Die Ergebnisse bleiben lokal ignoriert; es wurden keine privaten
Simulationsoutputs zur Versionskontrolle hinzugefügt.
