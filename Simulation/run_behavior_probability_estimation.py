from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

ROOT_DIR = Path(__file__).resolve().parents[1]
SIMULATION_DIR = Path(__file__).resolve().parent

if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))
if str(SIMULATION_DIR) not in sys.path:
    sys.path.append(str(SIMULATION_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_CONTEXT_PATH = SIMULATION_DIR / "output" / "llm_day_contexts_heterogeneous_test.json"
FALLBACK_CONTEXT_PATH = SIMULATION_DIR / "output" / "llm_day_contexts.json"
DEFAULT_PROMPT_PATH = SIMULATION_DIR / "BehaviorProbability_Prompt.md"
OUTPUT_DIR = SIMULATION_DIR / "output"
COMBINED_OUTPUT_PATH = OUTPUT_DIR / "llm_behavior_probabilities_all_agents.json"
MODEL_NAME = "gpt-oss-120b"
TEMPERATURE = 0
MAX_TOKENS = 800
PROBABILITY_SUM_TOLERANCE = 1e-6

BEHAVIOR_PROBABILITY_KEYS: tuple[str, ...] = (
    "do_planned_activity",
    "adapt_activity",
    "postpone_activity",
    "skip_activity",
    "extra_activity",
    "app_ignored",
)
EXPECTED_TOP_LEVEL_FIELDS = frozenset({"probabilities"})
EXPECTED_PROBABILITY_FIELDS = frozenset(BEHAVIOR_PROBABILITY_KEYS)

_client: Any | None = None


def default_context_path() -> Path:
    """Return the preferred exported LLM context path available in Simulation/output."""
    if DEFAULT_CONTEXT_PATH.exists():
        return DEFAULT_CONTEXT_PATH
    return FALLBACK_CONTEXT_PATH


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


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Estimate LLM1 psychological action-tendency probabilities for exported LLM contexts."
    )
    parser.add_argument(
        "--context-path",
        type=Path,
        default=default_context_path(),
        help="Path to an exported JSON file containing llm_contexts.",
    )
    parser.add_argument(
        "--prompt-path",
        type=Path,
        default=DEFAULT_PROMPT_PATH,
        help="Path to the behavior probability prompt markdown file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory for per-persona probability outputs and invalid raw responses.",
    )
    parser.add_argument(
        "--combined-output-path",
        type=Path,
        default=COMBINED_OUTPUT_PATH,
        help="Path for the combined behavior probability output JSON.",
    )
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--temperature", type=float, default=TEMPERATURE)
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    return parser.parse_args(argv)


def load_behavior_probability_prompt(prompt_path: Path = DEFAULT_PROMPT_PATH) -> str:
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    if not prompt:
        raise ValueError(f"Behavior probability prompt is empty: {prompt_path}")
    return prompt


def load_all_agent_contexts(context_path: Path) -> list[dict[str, Any]]:
    with context_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    contexts = payload.get("llm_contexts", [])
    if not contexts:
        raise ValueError("Keine llm_contexts in der Kontextdatei gefunden.")
    if not all(isinstance(context, dict) for context in contexts):
        raise ValueError("Alle llm_contexts müssen JSON-Objekte sein.")

    return [dict(context) for context in contexts]


def extract_psychological_values_normalized(agent_context: Mapping[str, Any]) -> dict[str, float]:
    psychological_state = agent_context.get("psychological_state")
    if not isinstance(psychological_state, Mapping):
        raise ValueError("agent context must contain psychological_state as an object.")

    values_normalized = psychological_state.get("values_normalized")
    if not isinstance(values_normalized, Mapping):
        raise ValueError("psychological_state must contain values_normalized as an object.")

    return {str(key): float(value) for key, value in values_normalized.items()}


def build_behavior_probability_user_prompt(agent_context: Mapping[str, Any]) -> str:
    psychological_values = extract_psychological_values_normalized(agent_context)
    llm1_input: dict[str, Any] = {
        "traceability": {
            "persona_id": agent_context.get("persona_id"),
            "scenario": agent_context.get("scenario"),
            "seed": agent_context.get("seed"),
        },
        "psychological_construct_values_normalized": psychological_values,
    }
    input_json = json.dumps(llm1_input, ensure_ascii=False, separators=(",", ":"))

    return f"""
INPUT:
{input_json}

IMPORTANT:
Use traceability fields only to identify this record. Base the probability estimate only on psychological_construct_values_normalized.
Return exactly one valid JSON object in the required schema.
""".strip()


def parse_behavior_probability_json(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM behavior probability output is not valid JSON: {exc.msg}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("LLM behavior probability JSON must be a top-level object.")
    return parsed


def validate_behavior_probability_payload(
    payload: Mapping[str, Any],
    *,
    sum_tolerance: float = PROBABILITY_SUM_TOLERANCE,
) -> dict[str, dict[str, float]]:
    actual_fields = set(payload)
    if actual_fields != EXPECTED_TOP_LEVEL_FIELDS:
        missing = sorted(EXPECTED_TOP_LEVEL_FIELDS - actual_fields)
        extra = sorted(actual_fields - EXPECTED_TOP_LEVEL_FIELDS)
        raise ValueError(
            f"Behavior probability fields mismatch. Missing: {missing}; extra: {extra}."
        )

    probabilities = payload["probabilities"]
    if not isinstance(probabilities, Mapping):
        raise ValueError("probabilities must be an object.")

    actual_probability_fields = set(probabilities)
    if actual_probability_fields != EXPECTED_PROBABILITY_FIELDS:
        missing = sorted(EXPECTED_PROBABILITY_FIELDS - actual_probability_fields)
        extra = sorted(actual_probability_fields - EXPECTED_PROBABILITY_FIELDS)
        raise ValueError(
            f"Behavior probability keys mismatch. Missing: {missing}; extra: {extra}."
        )

    validated_probabilities: dict[str, float] = {}
    for key in BEHAVIOR_PROBABILITY_KEYS:
        value = probabilities[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{key} must be a numeric probability, not {type(value).__name__}.")

        probability = float(value)
        if not math.isfinite(probability):
            raise ValueError(f"{key} must be finite.")
        if probability < 0.0 or probability > 1.0:
            raise ValueError(f"{key} must be between 0.0 and 1.0.")

        validated_probabilities[key] = probability

    probability_sum = sum(validated_probabilities.values())
    if abs(probability_sum - 1.0) > sum_tolerance:
        raise ValueError(
            f"Behavior probabilities must sum to 1.0 within tolerance {sum_tolerance}; "
            f"got {probability_sum:.12f}."
        )

    return {"probabilities": validated_probabilities}


def parse_and_validate_behavior_probabilities(raw: str) -> dict[str, dict[str, float]]:
    return validate_behavior_probability_payload(parse_behavior_probability_json(raw))


def run_behavior_probability_estimation(
    agent_context: Mapping[str, Any],
    *,
    system_prompt: str,
    model: str = MODEL_NAME,
    temperature: float = TEMPERATURE,
    max_tokens: int = MAX_TOKENS,
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, dict[str, float]]:
    user_prompt = build_behavior_probability_user_prompt(agent_context)
    persona_id = agent_context.get("persona_id", "unknown_persona")
    print(f"Starte LLM1-Wahrscheinlichkeitsschätzung für {persona_id} ...", flush=True)

    response = get_client().chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    print(f"LLM1-Wahrscheinlichkeitsschätzung für {persona_id} abgeschlossen.", flush=True)
    print(response.usage, flush=True)

    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError(f"LLM hat für {persona_id} keine Antwort zurückgegeben.")

    try:
        return parse_and_validate_behavior_probabilities(content)
    except ValueError as exc:
        debug_path = save_invalid_raw_response(str(persona_id), content, output_dir=output_dir)
        raise ValueError(
            f"Ungültiger LLM1-JSON-Output für {persona_id}: {exc}. "
            f"Raw response gespeichert unter: {debug_path}"
        ) from exc


def _safe_persona_id(persona_id: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in persona_id)


def save_invalid_raw_response(persona_id: str, raw_response: str, output_dir: Path = OUTPUT_DIR) -> Path:
    output_path = output_dir / f"llm_behavior_probability_{_safe_persona_id(persona_id)}_raw_invalid.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(raw_response, encoding="utf-8")
    return output_path


def save_agent_behavior_probabilities(
    persona_id: str,
    probabilities: Mapping[str, Any],
    output_dir: Path = OUTPUT_DIR,
) -> Path:
    output_path = output_dir / f"llm_behavior_probability_{_safe_persona_id(persona_id)}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(probabilities, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.combined_output_path.parent.mkdir(parents=True, exist_ok=True)

    system_prompt = load_behavior_probability_prompt(args.prompt_path)
    agent_contexts = load_all_agent_contexts(args.context_path)
    print(f"{len(agent_contexts)} Agenten-Kontexte geladen.", flush=True)

    combined_records: list[dict[str, Any]] = []

    for index, agent_context in enumerate(agent_contexts):
        persona_id = str(agent_context.get("persona_id", f"agent_{index}"))

        print("\n" + "=" * 80, flush=True)
        print(f"Verarbeite Agent {index + 1}/{len(agent_contexts)}: {persona_id}", flush=True)
        print("=" * 80, flush=True)

        try:
            probabilities = run_behavior_probability_estimation(
                agent_context,
                system_prompt=system_prompt,
                model=args.model,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                output_dir=args.output_dir,
            )
        except ValueError as exc:
            raise ValueError(f"Ungültiger LLM1-Input oder Output für {persona_id}: {exc}") from exc

        output_path = save_agent_behavior_probabilities(
            persona_id,
            probabilities,
            output_dir=args.output_dir,
        )

        record: dict[str, Any] = {
            "persona_id": persona_id,
            "seed": agent_context.get("seed"),
            "probabilities": probabilities["probabilities"],
        }
        if "scenario" in agent_context:
            record["scenario"] = agent_context["scenario"]
        combined_records.append(record)

        print("\nLLM1-Verhaltenswahrscheinlichkeiten")
        print("-" * 60)
        print(json.dumps(probabilities, ensure_ascii=False, indent=2))
        print("-" * 60)
        print(f"Gespeichert unter: {output_path}", flush=True)

    combined_payload = {
        "metadata": {
            "source_context_file": str(args.context_path),
            "prompt_file": str(args.prompt_path),
            "model": args.model,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "n_contexts": len(agent_contexts),
        },
        "behavior_probability_estimates": combined_records,
    }
    args.combined_output_path.write_text(
        json.dumps(combined_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\n" + "=" * 80)
    print("Alle LLM1-Verhaltenswahrscheinlichkeiten abgeschlossen.")
    print(f"Gesamtdatei gespeichert unter: {args.combined_output_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
