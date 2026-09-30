### Beispiel 1: Kontext erhöht eine mittlere psychologische PA-Wahrscheinlichkeit

Input-Situation: `behavior_policy.extra_activity = 0.45`. Freier früher Abend, gute Energie, trockenes Wetter, Aktivitätsort gut erreichbar.

Erwartete Ausgabe:

```json
{
  "persona_id": "ExamplePersona_01",
  "day_index": 1,
  "contextual_pa_probability": 0.58,
  "activity_if_performed": {
    "duration_min": 45,
    "intensity": "moderate",
    "rationale_short": "Freie Zeit, ausreichende Energie und gute Erreichbarkeit erhöhen die Chance auf eine moderate Aktivität gegenüber dem psychologischen Prior.",
    "diary_entry": "Am frühen Abend hatte ich noch genug Energie und bin ungefähr 45 Minuten moderat trainieren gegangen."
  },
  "no_activity_if_skipped": {
    "rationale_short": "Trotz günstiger Bedingungen wurde an diesem Tag keine Aktivität umgesetzt.",
    "diary_entry": "Obwohl der Abend frei war, habe ich heute keinen Sport gemacht und mich stattdessen erholt."
  }
}
```

### Beispiel 2: Günstiger Kontext überschreibt einen niedrigen Prior nicht

Input-Situation: `behavior_policy.extra_activity = 0.25`. Viel freie Zeit und gutes Wetter, aber die psychologische PA-Tendenz ist niedrig.

Erwartete Ausgabe:

```json
{
  "persona_id": "ExamplePersona_02",
  "day_index": 4,
  "contextual_pa_probability": 0.34,
  "activity_if_performed": {
    "duration_min": 30,
    "intensity": "light",
    "rationale_short": "Der günstige Kontext erhöht die niedrige Ausgangswahrscheinlichkeit etwas, rechtfertigt aber keine hohe PA-Wahrscheinlichkeit.",
    "diary_entry": "Am Nachmittag habe ich das gute Wetter für einen lockeren Spaziergang von ungefähr 30 Minuten genutzt."
  },
  "no_activity_if_skipped": {
    "rationale_short": "Die niedrige psychologische PA-Tendenz bleibt trotz freier Zeit und gutem Wetter relevant.",
    "diary_entry": "Ich hatte zwar Zeit, habe mich heute aber nicht zu zusätzlicher Bewegung aufgerafft."
  }
}
```

### Beispiel 3: Barrieren senken einen hohen Prior

Input-Situation: `behavior_policy.extra_activity = 0.72`. Dichter Arbeitstag, niedrige Energie und ungünstiges Wetter.

Erwartete Ausgabe:

```json
{
  "persona_id": "ExamplePersona_03",
  "day_index": 8,
  "contextual_pa_probability": 0.41,
  "activity_if_performed": {
    "duration_min": 25,
    "intensity": "light",
    "rationale_short": "Trotz hoher psychologischer Bereitschaft sprechen Zeitknappheit und niedrige Energie nur für eine kurze leichte Aktivität.",
    "diary_entry": "Am Abend bin ich noch ungefähr 25 Minuten locker spazieren gegangen."
  },
  "no_activity_if_skipped": {
    "rationale_short": "Der volle Tag und die niedrige Energie können die grundsätzlich hohe PA-Tendenz an diesem Tag überwiegen.",
    "diary_entry": "Nach dem langen Tag war ich zu müde und habe heute keine zusätzliche körperliche Aktivität gemacht."
  }
}
```
