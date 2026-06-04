from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

ROOT_DIR = Path(__file__).resolve().parents[1]
SIMULATION_DIR = Path(__file__).resolve().parent

if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

api_key = os.getenv("UNI_LLM_API_KEY")

if not api_key:
    raise ValueError("UNI_LLM_API_KEY nicht gefunden. Prüfe deine .env-Datei.")

client = OpenAI(
    api_key=api_key,
    base_url="https://gpustack.unibe.ch/v1",
)

DEFAULT_CONTEXT_PATH = SIMULATION_DIR / "output" / "llm_day_contexts.json"
OUTPUT_DIR = SIMULATION_DIR / "output"
COMBINED_OUTPUT_PATH = OUTPUT_DIR / "llm_pa_decisions_all_agents.txt"


SYSTEM_PROMPT = """
Du unterstützt ein agentenbasiertes Modell, indem du einen einzelnen Agenten-Tageskontext evaluierst.

Aufgabe:
Stelle den simulierten Agenten dar und entscheide aus seiner Perspektive, ob er an diesem Tag körperliche Aktivität (PA) durchführen würde oder nicht.

Nutze ausschliesslich den bereitgestellten Tageskontext. Erfinde keine zusätzlichen Termine, Motivationen, Gesundheitszustände, sozialen Ereignisse, Orte, Wetterbedingungen oder Einschränkungen.

Die simulierten Agenten basieren auf Personen, die zum Zeitpunkt der Befragung körperlich inaktiv waren und die WHO-Empfehlungen für körperliche Aktivität nicht erfüllten. Berücksichtige daher, dass PA für diese Agenten nicht als stark etablierte Alltagsgewohnheit angenommen werden soll.

Das bedeutet aber nicht, dass diese Agenten grundsätzlich keine PA durchführen. Auch inaktive Personen können an einzelnen Tagen leichte oder moderate PA ausführen, insbesondere wenn mehrere günstige Kontextbedingungen zusammenkommen, z. B. freie Zeit, ausreichende Energie, geringe Einschränkungen, gute Erreichbarkeit und akzeptable Umweltbedingungen.

Freie Zeit, gute Erreichbarkeit oder hohe Energie führen einzeln nicht automatisch zu PA. Wenn jedoch mehrere dieser Faktoren gleichzeitig günstig sind, kann PA trotz inaktiver Ausgangslage plausibel sein.

Die finale Ausgabe wird später über eine App-Datenbank-Action definiert. In diesem Prompt geht es zunächst darum, die Entscheidungslogik festzulegen.

Input:
Du erhältst einen Tageskontext mit Agenten- und Tagesinformationen sowie hourly_context_24h. hourly_context_24h enthält 24 Einträge, einen pro Stunde des Tages.

Wichtige Felder:
- persona_id: ID des simulierten Agenten
- day_index: Index des simulierten Tages
- phase: Jahresphase, z. B. normal, holiday oder high_stress
- weekday: Wochentag als Zahl
- hour: Stunde des Tages
- activity_type: geplanter Aktivitätstyp in dieser Stunde
- subtype: genauere Beschreibung der Aktivität
- current_location: aktueller Ort des Agenten
- active_constraints: aktive Einschränkungen in dieser Stunde
- energy_level: kontinuierlicher Energiewert zwischen 0 und 1; höhere Werte bedeuten mehr verfügbare Energie
- energy_category: grobe kategoriale Beschreibung desselben Energieniveaus: low, medium oder high
- temperature_c: Temperatur in Grad Celsius
- feels_like_c: gefühlte Temperatur in Grad Celsius
- humidity_pct: Luftfeuchtigkeit in Prozent
- wind_m_s: Windgeschwindigkeit in m/s
- precipitation_mm: Niederschlag in mm
- is_wet: ob nasse Bedingungen vorliegen
- sun_frac: relativer Sonnen-/Lichtanteil
- is_daylight: ob Tageslicht vorhanden ist
- snow_cover: ob Schnee liegt
- poi_accessibility enthält für Indoor- und Outdoor-Aktivitätsmöglichkeiten die Distanz sowie geschätzte Reisezeiten mit verschiedenen Verkehrsmitteln, z. B. walk, bike und car.
Berücksichtige alle angegebenen Verkehrsmittel als mögliche Zugangsoptionen. Nutze nicht automatisch nur die Gehzeit. Wenn ein Aktivitätsort mit dem Fahrrad oder Auto deutlich schneller erreichbar ist als zu Fuss, soll dies als geringere Zugangsbarriere gewertet werden.

Die Reisezeit ist primär als Zugangshürde zu interpretieren. Sie zählt nicht automatisch selbst als PA. Transportbezogene PA kann nur dann als PA gewertet werden, wenn der Kontext nahelegt, dass der Agent die Strecke aktiv zurücklegt, z. B. zu Fuss oder mit dem Fahrrad.

PA-Definition:
PA wird breit verstanden als körperliche Bewegung, die Energieverbrauch erfordert. Dazu können Sport, Training, Spazieren, Gehen, Radfahren oder aktive Fortbewegung zählen, wenn dies im Kontext als relevante Bewegungshandlung sinnvoll ist.

Schlaf, Essen, Arbeit, Universität, Carework oder passive Downtime sollen nicht automatisch als PA interpretiert werden. Transportbezogene Bewegung kann als PA zählen, wenn sie im Kontext sinnvoll als aktive Bewegung verstanden werden kann.

Entscheidungslogik:
Berücksichtige den gesamten Tageskontext:
- Tagesstruktur und freie Zeitfenster
- Aktivitätstypen und Orte
- aktive Einschränkungen
- Energielevel
- Wetter, Tageslicht, Nässe, Schnee und Wind
- Erreichbarkeit von Indoor- und Outdoor-Aktivitätsmöglichkeiten
- dass die simulierten Agenten aus einer inaktiven Zielgruppe stammen

Entscheide nicht mechanisch. Hohe Energie bedeutet nicht automatisch PA. Schlechtes Wetter bedeutet nicht automatisch keine PA. Freie Zeit bedeutet nicht automatisch PA. Gute Erreichbarkeit bedeutet nicht automatisch PA.

Fehlende geplante PA-Slots bedeuten aber auch nicht automatisch, dass keine PA durchgeführt wird. PA kann spontan während freier Zeitfenster, Downtime, Open Time, Between-Blocks-Zeit oder aktiver Fortbewegung entstehen. Berücksichtige solche Zeitfenster als mögliche PA-Gelegenheiten, ohne daraus automatisch PA abzuleiten.

Nenne keine konkrete Aktivitätsart, wenn sie nicht direkt aus dem Kontext ableitbar ist. Falls PA wahrscheinlich ist, beschreibe sie allgemein als leichte, moderate, Indoor-, Outdoor- oder transportbezogene PA.

Erfinde keine konkreten Aktivitätsarten wie Joggen, Home-Workout, Stretching, Gym oder Sportzentrum. Beschreibe PA lediglich Allgemein.

Beispiele:
1. Viel freie Zeit, mittlere bis hohe Energie, gute Erreichbarkeit, keine starken Hindernisse -> PA kann möglich sein, ist bei inaktiven Agenten aber nur dann wahrscheinlich, wenn mehrere Kontextfaktoren zusammen deutlich dafür sprechen.
2. Stark verdichteter Tag, wenig freie Zeit, tiefe Energie, ungünstiger Kontext -> eher keine PA.
3. Gemischter Tag, begrenzte freie Zeit, mittlere Energie, schlechtes Wetter, aber gute Indoor-Erreichbarkeit -> leichte/moderate PA kann sinnvoll sein, muss aber gegen die fehlende etablierte PA-Gewohnheit abgewogen werden.

Antworte kurz und klar.
Verwende keine Tabelle.
Strukturiere die Antwort in maximal drei kurze Abschnitte:
1. Entscheidung
2. Begründung
3. Wichtigste Kontextfaktoren
""".strip()


def load_all_agent_contexts(context_path: Path) -> list[dict[str, Any]]:
    with context_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    contexts = payload.get("llm_contexts", [])
    if not contexts:
        raise ValueError("Keine llm_contexts in der Kontextdatei gefunden.")

    cleaned_contexts: list[dict[str, Any]] = []

    for context in contexts:
        agent_context = dict(context)

        # Diese Felder sollen später aus dem Export entfernt werden.
        # Für den LLM-Test entfernen wir sie bereits hier.
        agent_context.pop("input_parameters", None)
        agent_context.pop("selected_schedule_parameters", None)

        cleaned_contexts.append(agent_context)

    return cleaned_contexts


def build_user_prompt(agent_context: dict[str, Any]) -> str:
    context_json = json.dumps(
        agent_context,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return f"""
TAGESKONTEXT:
{context_json}

AUFGABE:
Entscheide aus der Perspektive dieses Agenten, ob er an diesem Tag PA durchführen würde oder nicht.

Begründe deine Entscheidung anhand des Tageskontexts.

Wichtig:
Fehlende geplante PA-Slots bedeuten nicht automatisch, dass keine PA durchgeführt wird. Prüfe freie Zeitfenster, Downtime, Open Time, Between-Blocks-Zeit und aktive Fortbewegung aktiv als mögliche PA-Gelegenheiten.

Antworte kurz und klar.
Verwende keine Tabelle.
Strukturiere die Antwort in maximal drei kurze Abschnitte:
1. Entscheidung
2. Begründung
3. Wichtigste Kontextfaktoren
""".strip()


def run_llm_decision(agent_context: dict[str, Any]) -> str:
    user_prompt = build_user_prompt(agent_context)

    persona_id = agent_context.get("persona_id", "unknown_persona")
    print(f"Starte LLM-Call für {persona_id} ...", flush=True)

    response = client.chat.completions.create(
        model="gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=0,
        max_tokens=1200,
    )

    print(f"LLM-Call für {persona_id} abgeschlossen.", flush=True)
    print(response.usage, flush=True)

    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError(f"LLM hat für {persona_id} keine Antwort zurückgegeben.")

    return content


def save_agent_decision(persona_id: str, decision: str) -> Path:
    output_path = OUTPUT_DIR / f"llm_pa_decision_{persona_id}.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(decision, encoding="utf-8")
    return output_path


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    agent_contexts = load_all_agent_contexts(DEFAULT_CONTEXT_PATH)
    print(f"{len(agent_contexts)} Agenten-Kontexte geladen.", flush=True)

    combined_outputs: list[str] = []

    for index, agent_context in enumerate(agent_contexts):
        persona_id = str(agent_context.get("persona_id", f"agent_{index}"))

        print("\n" + "=" * 80, flush=True)
        print(f"Verarbeite Agent {index + 1}/{len(agent_contexts)}: {persona_id}", flush=True)
        print("=" * 80, flush=True)

        decision = run_llm_decision(agent_context)
        output_path = save_agent_decision(persona_id, decision)

        combined_outputs.append(
            f"{'=' * 80}\n"
            f"Agent: {persona_id}\n"
            f"{'=' * 80}\n"
            f"{decision}\n"
        )

        print("\nLLM-Entscheidung")
        print("-" * 60)
        print(decision)
        print("-" * 60)
        print(f"Gespeichert unter: {output_path}", flush=True)

    COMBINED_OUTPUT_PATH.write_text("\n\n".join(combined_outputs), encoding="utf-8")

    print("\n" + "=" * 80)
    print("Alle LLM-Entscheidungen abgeschlossen.")
    print(f"Gesamtdatei gespeichert unter: {COMBINED_OUTPUT_PATH}")
    print("=" * 80)


if __name__ == "__main__":
    main()