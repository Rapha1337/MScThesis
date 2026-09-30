### Beispiel 1: PA findet statt

Input-Situation: Ein freier früher Abend, mittlere bis hohe Energie, trockenes Wetter, ein Aktivitätsort ist gut erreichbar und die psychologische Tendenz spricht eher für Aktivität.

Erwartete Ausgabe:

```json
{
  "persona_id": "ExamplePersona_01",
  "day_index": 1,
  "decision_code": 3,
  "decision_label": "extra_activity",
  "duration_min": 50,
  "intensity": "moderate",
  "rationale_short": "Freie Zeit, ausreichende Energie und gute Erreichbarkeit machen körperliche Aktivität heute plausibel.",
  "diary_entry": "Am frühen Abend hatte ich noch genug Energie und bin für ungefähr 50 Minuten moderat trainieren gegangen."
}
```

### Beispiel 2: Keine PA

Input-Situation: Ein dichter Arbeitstag, niedrige Energie und ungünstige Bedingungen; die psychologische Tendenz ist gemischt.

Erwartete Ausgabe:

```json
{
  "persona_id": "ExamplePersona_02",
  "day_index": 4,
  "decision_code": 0,
  "decision_label": "skip_activity",
  "duration_min": 0,
  "intensity": "none",
  "rationale_short": "Der volle Tagesablauf und die niedrige Energie machen zusätzliche körperliche Aktivität heute unplausibel.",
  "diary_entry": "Der Tag war ziemlich voll und ich war am Abend müde, deshalb habe ich heute keinen Sport oder andere körperliche Aktivität gemacht."
}
```

### Beispiel 3: Leichte Aktivität

Input-Situation: Ein freies Zeitfenster und gutes Wetter sprechen für Bewegung, aber die Energie reicht nicht für eine belastende Einheit.

Erwartete Ausgabe:

```json
{
  "persona_id": "ExamplePersona_03",
  "day_index": 8,
  "decision_code": 3,
  "decision_label": "extra_activity",
  "duration_min": 35,
  "intensity": "light",
  "rationale_short": "Das freie Zeitfenster und gute Wetter begünstigen Bewegung, während das Energielevel eher für eine leichte Aktivität spricht.",
  "diary_entry": "Ich habe das gute Wetter genutzt und bin etwa 35 Minuten locker spazieren gegangen."
}
```
