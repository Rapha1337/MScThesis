### Beispiel 1: Geplante PA, günstige Tendenzen und günstiger Kontext

Input enthält eine geplante PA, hohe Tendenzen für `do_planned_activity`, mittlere bis hohe Energie am späten Nachmittag, trockenes Wetter und erreichbare Aktivitätsorte. `valid_decision_categories` enthält alle vier Kategorien.

Output:

```json
{
  "persona_id": "ExamplePersona_01",
  "day_index": 1,
  "decision_code": 1,
  "decision_label": "do_planned_activity",
  "rationale_short": "Die psychologischen Tendenzen sprechen für die geplante Aktivität, und der Tageskontext bietet genug Energie, freie Zeit und keine relevanten Wetter- oder Zugangshürden.",
  "diary_entry": "Ich hatte heute das Gefühl, dass die Bewegung gut in den Tag passt. Nach den Verpflichtungen war noch genug Energie da, deshalb habe ich die geplante Einheit wie vorgesehen gemacht."
}
```

### Beispiel 2: Geplante PA, Barrieren im Kontext

Input enthält eine geplante PA, aber der Tageskontext zeigt niedrige Energie, viele Verpflichtungen und nasses Wetter. `valid_decision_categories` enthält alle vier Kategorien.

Output:

```json
{
  "persona_id": "ExamplePersona_02",
  "day_index": 2,
  "decision_code": 2,
  "decision_label": "adapt_activity",
  "rationale_short": "Obwohl die psychologischen Tendenzen Bewegung unterstützen, sprechen niedrige Energie und ungünstige Kontextbedingungen eher für eine reduzierte, angepasste Umsetzung.",
  "diary_entry": "Ich wollte mich eigentlich bewegen, aber der Tag war voller als gedacht und ich fühlte mich nicht ganz fit. Deshalb habe ich die Aktivität kürzer und ruhiger gemacht, statt sie komplett ausfallen zu lassen."
}
```

### Beispiel 3: Keine geplante PA, günstiger Kontext für spontane Bewegung

Input enthält keine geplante PA. `valid_decision_categories` enthält nur `skip_activity` und `extra_activity`. Der Kontext zeigt freie Tageslichtstunden, gute Energie und gut erreichbare Outdoor-Aktivitätsorte.

Output:

```json
{
  "persona_id": "ExamplePersona_03",
  "day_index": 3,
  "decision_code": 3,
  "decision_label": "extra_activity",
  "rationale_short": "Obwohl keine PA geplant war, machen freie Zeit, gute Energie und ein günstiger Kontext spontane Bewegung plausibel.",
  "diary_entry": "Ich hatte unerwartet etwas Luft und fühlte mich ziemlich wach. Deshalb bin ich spontan noch rausgegangen und habe mich ein bisschen bewegt."
}
```

### Beispiel 4: Keine geplante PA, keine zusätzliche Bewegung

Input enthält keine geplante PA. `valid_decision_categories` enthält nur `skip_activity` und `extra_activity`. Der Kontext zeigt wenig freie Zeit, geringe Energie oder ungünstige Bedingungen.

Output:

```json
{
  "persona_id": "ExamplePersona_04",
  "day_index": 4,
  "decision_code": 0,
  "decision_label": "skip_activity",
  "rationale_short": "Ohne geplante PA und bei wenig günstigen Kontextbedingungen ist keine zusätzliche spontane Bewegung plausibel.",
  "diary_entry": "Heute habe ich keine zusätzliche Bewegung eingebaut. Der Tag war schon dicht genug, und ich habe die freie Zeit eher zum Ausruhen genutzt."
}
```
