from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT_DIR = Path(__file__).resolve().parents[1]
SIMULATION_DIR = Path(__file__).resolve().parent

if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))
if str(SIMULATION_DIR) not in sys.path:
    sys.path.append(str(SIMULATION_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from psychological_state import build_default_psychological_state

DEFAULT_CONTEXT_PATH = SIMULATION_DIR / "output" / "llm_day_contexts_heterogeneous_test.json"
OUTPUT_DIR = SIMULATION_DIR / "output"
COMBINED_OUTPUT_PATH = OUTPUT_DIR / "llm_app_decisions_all_agents.json"
MODEL_NAME = "gpt-oss-120b"
TEMPERATURE = 0
MAX_TOKENS = 1200

DECISION_CODEBOOK: dict[int, str] = {
    0: "not_completed",
    1: "completed_as_planned",
    2: "postponed",
    3: "adapted_completed",
    4: "extra_movement",
    5: "app_ignored",
}

DECISION_CODE_DESCRIPTIONS_DE: dict[int, str] = {
    0: "nicht gemacht",
    1: "wie geplant gemacht",
    2: "verschoben gemacht",
    3: "angepasst gemacht",
    4: "extra Bewegung gemacht",
    5: "App ignoriert",
}

EXPECTED_DECISION_FIELDS = frozenset(
    {
        "decision_code",
        "decision_label",
        "diary_entry",
        "rationale_short",
        "main_context_factors",
    }
)

_client: Any | None = None


def decision_codebook_prompt_text() -> str:
    """Build the German prompt codebook from DECISION_CODEBOOK."""
    return "\n".join(
        f"{code} = {DECISION_CODE_DESCRIPTIONS_DE[code]} ({label})"
        for code, label in DECISION_CODEBOOK.items()
    )


SYSTEM_PROMPT = f"""
Du unterstützt ein agentenbasiertes Modell, indem du einen einzelnen app-nahen Agenten-Tageskontext evaluierst.

Aufgabe:
Nutze ausschliesslich den bereitgestellten Agenten-/Tageskontext, hourly_context_24h und psychological_state. Gib genau eine app-nahe Entscheidung als valides JSON zurück.

Decision-Codebook:
{decision_codebook_prompt_text()}

Kontextregeln:
- Die simulierten Agenten stammen aus einer inaktiven Zielgruppe und erfüllten zu Baseline die WHO-Empfehlungen für körperliche Aktivität nicht.
- Körperliche Aktivität ist daher nicht als stark etablierte Alltagsgewohnheit anzunehmen.
- Inaktive Personen können trotzdem an einzelnen Tagen leichte oder moderate körperliche Aktivität ausführen, wenn mehrere günstige Kontextfaktoren zusammenkommen.
- Berücksichtige Tagesstruktur, freie Zeitfenster, Energie, Einschränkungen, Wetter, Tageslicht, Nässe, Schnee, Wind und Erreichbarkeit von Indoor-/Outdoor-PA-Möglichkeiten.
- psychological_state kann die Entscheidung informieren: höhere Intention, perceived behavioral control, Planung, intrinsische Motivation, Kompetenz, Wahlfreiheit oder Habit können PA wahrscheinlicher machen, aber niemals mechanisch oder allein entscheidend.
- energy_level beschreibt verfügbare körperliche oder mentale Ressource, nicht Motivation.
- phase darf nicht als direkte Motivation interpretiert werden. Holiday oder high_stress nur über Tagesstruktur, freie Zeit und Belastung verstehen.
- Berücksichtige bei poi_accessibility walk, bike und car als mögliche Zugangsoptionen. Auto zählt nicht als PA. Bike oder Gehen zählen nur dann als transportbezogene PA, wenn aktive Fortbewegung im Kontext plausibel ist.
- Erfinde keine konkreten Aktivitätsarten wie Joggen, Spaziergang, Home-Workout, Stretching, Gym, Sportzentrum oder Fahrradtour, ausser sie sind explizit im Kontext enthalten.
- Verwende stattdessen allgemeine Kategorien wie leichte PA, moderate PA, Indoor-PA, Outdoor-PA oder transportbezogene PA.
- Der diary_entry soll kurz, natürlich und in Ich-Perspektive sein.
- Der diary_entry darf keine neuen Fakten erfinden.

Output-Regeln:
- Antworte ausschliesslich mit validem JSON.
- Keine Markdown-Fences.
- Kein zusätzlicher Text vor oder nach dem JSON.
- Wähle genau einen decision_code aus dem Codebook.
- decision_label muss exakt dem Label aus dem Codebook entsprechen.
- Verwende exakt diese fünf Felder: decision_code, decision_label, diary_entry, rationale_short, main_context_factors.

JSON-Format:
{{
  "decision_code": 0,
  "decision_label": "{DECISION_CODEBOOK[0]}",
  "diary_entry": "...",
  "rationale_short": "...",
  "main_context_factors": ["...", "..."]
}}
""".strip()


def get_client() -> Any:
    """Create the OpenAI-compatible client lazily for real LLM calls only."""
    global _client
    if _client is None:
        from dotenv import load_dotenv
        from openai import OpenAI

        load_dotenv()
        api_key = os.getenv("UNI_LLM_API_KEY")
        if not api_key:
            raise ValueError("UNI_LLM_API_KEY nicht gefunden. Prüfe deine .env-Datei.")
        _client = OpenAI(
            api_key=api_key,
            base_url="https://gpustack.unibe.ch/v1",
        )
    return _client


def prepare_agent_context_for_llm(context: Mapping[str, Any]) -> dict[str, Any]:
    """Return a cleaned LLM input context without mutating the source mapping."""
    agent_context = copy.deepcopy(dict(context))
    agent_context.pop("input_parameters", None)
    agent_context.pop("selected_schedule_parameters", None)
    agent_context.pop("action_plan", None)

    if "psychological_state" not in agent_context:
        # Legacy fallback for older exported context files without psychological_state.
        agent_context["psychological_state"] = build_default_psychological_state()

    return agent_context


def load_all_agent_contexts(context_path: Path) -> list[dict[str, Any]]:
    with context_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    contexts = payload.get("llm_contexts", [])
    if not contexts:
        raise ValueError("Keine llm_contexts in der Kontextdatei gefunden.")

    return [prepare_agent_context_for_llm(context) for context in contexts]


def build_user_prompt(agent_context: Mapping[str, Any]) -> str:
    context_json = json.dumps(
        agent_context,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return f"""
TAGESKONTEXT:
{context_json}

AUFGABE:
Bewerte diesen Tageskontext aus der Ich-Perspektive des Agenten und gib genau ein valides JSON-Objekt im geforderten Format zurück.
""".strip()


def parse_llm_decision_json(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM output is not valid JSON: {exc.msg}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("LLM decision JSON must be a top-level object.")
    return parsed


def _require_non_empty_string(payload: Mapping[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value


def validate_llm_decision_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    actual_fields = set(payload)
    if actual_fields != EXPECTED_DECISION_FIELDS:
        missing = sorted(EXPECTED_DECISION_FIELDS - actual_fields)
        extra = sorted(actual_fields - EXPECTED_DECISION_FIELDS)
        raise ValueError(f"LLM decision fields mismatch. Missing: {missing}; extra: {extra}.")

    decision_code = payload["decision_code"]
    if not isinstance(decision_code, int) or isinstance(decision_code, bool):
        raise ValueError("decision_code must be an integer.")
    if decision_code not in DECISION_CODEBOOK:
        raise ValueError(f"decision_code must be one of {sorted(DECISION_CODEBOOK)}.")

    expected_label = DECISION_CODEBOOK[decision_code]
    if payload["decision_label"] != expected_label:
        raise ValueError(
            f"decision_label must be {expected_label!r} for decision_code {decision_code}."
        )

    diary_entry = _require_non_empty_string(payload, "diary_entry")
    rationale_short = _require_non_empty_string(payload, "rationale_short")

    main_context_factors = payload["main_context_factors"]
    if not isinstance(main_context_factors, list):
        raise ValueError("main_context_factors must be a list.")
    if not all(isinstance(factor, str) for factor in main_context_factors):
        raise ValueError("main_context_factors must only contain strings.")

    return {
        "decision_code": decision_code,
        "decision_label": expected_label,
        "diary_entry": diary_entry,
        "rationale_short": rationale_short,
        "main_context_factors": list(main_context_factors),
    }


def parse_and_validate_llm_decision(raw: str) -> dict[str, Any]:
    return validate_llm_decision_payload(parse_llm_decision_json(raw))


def run_llm_decision(agent_context: Mapping[str, Any]) -> dict[str, Any]:
    prepared_context = prepare_agent_context_for_llm(agent_context)
    user_prompt = build_user_prompt(prepared_context)

    persona_id = prepared_context.get("persona_id", "unknown_persona")
    print(f"Starte LLM-Call für {persona_id} ...", flush=True)

    response = get_client().chat.completions.create(
        model=MODEL_NAME,
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
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )

    print(f"LLM-Call für {persona_id} abgeschlossen.", flush=True)
    print(response.usage, flush=True)

    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError(f"LLM hat für {persona_id} keine Antwort zurückgegeben.")

    try:
        return parse_and_validate_llm_decision(content)
    except ValueError as exc:
        debug_path = save_invalid_raw_response(str(persona_id), content)
        raise ValueError(
            f"Ungültiger LLM-JSON-Output für {persona_id}: {exc}. Raw response gespeichert unter: {debug_path}"
        ) from exc


def _safe_persona_id(persona_id: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in persona_id)


def save_invalid_raw_response(persona_id: str, raw_response: str) -> Path:
    output_path = OUTPUT_DIR / f"llm_app_decision_{_safe_persona_id(persona_id)}_raw_invalid.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(raw_response, encoding="utf-8")
    return output_path


def save_agent_decision(persona_id: str, decision: Mapping[str, Any]) -> Path:
    output_path = OUTPUT_DIR / f"llm_app_decision_{_safe_persona_id(persona_id)}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    agent_contexts = load_all_agent_contexts(DEFAULT_CONTEXT_PATH)
    print(f"{len(agent_contexts)} Agenten-Kontexte geladen.", flush=True)

    combined_decisions: list[dict[str, Any]] = []

    for index, agent_context in enumerate(agent_contexts):
        persona_id = str(agent_context.get("persona_id", f"agent_{index}"))

        print("\n" + "=" * 80, flush=True)
        print(f"Verarbeite Agent {index + 1}/{len(agent_contexts)}: {persona_id}", flush=True)
        print("=" * 80, flush=True)

        decision = run_llm_decision(agent_context)
        output_path = save_agent_decision(persona_id, decision)

        decision_record: dict[str, Any] = {
            "persona_id": persona_id,
            "decision": decision,
        }
        if "scenario" in agent_context:
            decision_record["scenario"] = agent_context["scenario"]
        combined_decisions.append(decision_record)

        print("\nLLM-App-Entscheidung")
        print("-" * 60)
        print(json.dumps(decision, ensure_ascii=False, indent=2))
        print("-" * 60)
        print(f"Gespeichert unter: {output_path}", flush=True)

    combined_payload = {
        "metadata": {
            "source_context_file": str(DEFAULT_CONTEXT_PATH),
            "model": MODEL_NAME,
            "temperature": TEMPERATURE,
            "n_contexts": len(agent_contexts),
        },
        "decisions": combined_decisions,
    }
    COMBINED_OUTPUT_PATH.write_text(
        json.dumps(combined_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\n" + "=" * 80)
    print("Alle LLM-App-Entscheidungen abgeschlossen.")
    print(f"Gesamtdatei gespeichert unter: {COMBINED_OUTPUT_PATH}")
    print("=" * 80)


if __name__ == "__main__":
    main()
