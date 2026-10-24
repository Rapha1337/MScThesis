### Beispiel 1: Keine verfügbare Freizeit erzwingt keine fiktive PA-Option

Input-Situation: `behavior_policy.extra_activity = 0.68`, `behavior_policy.skip_activity = 0.32`. Der Tageskontext enthält 24 Stunden mit Studium, Arbeit, Pendeln, Schlaf und Haushalt, aber keinen zusammenhängenden `downtime`-Block. Die psychologische PA-Tendenz ist hoch, die Durchführung ist strukturell nicht möglich. Die spätere effektive PA-Wahrscheinlichkeit wird im Code wegen fehlender Downtime auf 0 gesetzt.

Erwartete Ausgabe:

```json
{
  "persona_id": "ExamplePersona_01",
  "day_index": 1,
  "contextual_pa_probability": 0.22,
  "activity_if_performed": null,
  "no_activity_if_skipped": {
    "rationale_short": "Obwohl die psychologische PA-Tendenz hoch ist, enthält der Tag kein freies zusammenhängendes Zeitfenster für zusätzliche körperliche Aktivität.",
    "diary_entry": "Zwischen Terminen, Pendeln und Haushalt blieb heute kein freies Zeitfenster für zusätzliche körperliche Aktivität."
  }
}
```

### Beispiel 2: Unterstützender Kontext bleibt stochastisch

Input-Situation: `behavior_policy.extra_activity = 0.45`, `behavior_policy.skip_activity = 0.55`. Es gibt einen zusammenhängenden `downtime`-Block von 17:00 bis 19:00, mittlere bis gute Energie, trockenes Wetter und gute Erreichbarkeit. Der Kontext unterstützt PA, ersetzt aber den psychologischen Prior nicht.

Erwartete Ausgabe:

```json
{
  "persona_id": "ExamplePersona_02",
  "day_index": 4,
  "contextual_pa_probability": 0.57,
  "activity_if_performed": {
    "start_hour": 17,
    "duration_min": 45,
    "activity_option": null,
    "rationale_short": "Freie Zeit, ausreichende Energie und gute Erreichbarkeit erhöhen die PA-Wahrscheinlichkeit moderat gegenüber dem Prior.",
    "diary_entry": "Am frühen Abend habe ich das freie Zeitfenster genutzt und war ungefähr 45 Minuten körperlich aktiv."
  },
  "no_activity_if_skipped": {
    "rationale_short": "Der freie Abend ermöglicht PA, erklärt aber nicht, warum sie heute ausbleibt.",
    "diary_entry": "Der Abend war frei, und ich habe heute keine zusätzliche körperliche Aktivität gemacht."
  }
}
```

### Beispiel 3: Barrieren senken einen hohen psychologischen Prior

Input-Situation: `behavior_policy.extra_activity = 0.74`, `behavior_policy.skip_activity = 0.26`. Die Person hat eine hohe psychologische PA-Tendenz. Der Tageskontext enthält nur einen `downtime`-Block von 20:00 bis 21:00, niedrige Energie, nasses Wetter und schlechte Erreichbarkeit des Aktivitätsorts. PA bleibt möglich, aber nur kurz und weniger wahrscheinlich.

Erwartete Ausgabe:

```json
{
  "persona_id": "ExamplePersona_03",
  "day_index": 8,
  "contextual_pa_probability": 0.39,
  "activity_if_performed": {
    "start_hour": 20,
    "duration_min": 30,
    "activity_option": null,
    "rationale_short": "Der hohe psychologische Prior bleibt relevant, wird aber durch niedrige Energie, späte freie Zeit, Regen und ungünstige Erreichbarkeit deutlich abgeschwächt.",
    "diary_entry": "Nach dem langen Tag war ich am Abend etwa 30 Minuten körperlich aktiv."
  },
  "no_activity_if_skipped": {
    "rationale_short": "Die Barrieren können die grundsätzlich hohe PA-Tendenz an diesem Tag überwiegen.",
    "diary_entry": "Nach dem langen Tag war es am Abend nass, und ich habe keine zusätzliche körperliche Aktivität gemacht."
  }
}
```
