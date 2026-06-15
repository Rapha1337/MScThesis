from __future__ import annotations

import argparse
import copy
import csv
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable, Mapping, Sequence

ROOT_DIR = Path(__file__).resolve().parents[1]
SIMULATION_DIR = Path(__file__).resolve().parent

if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))
if str(SIMULATION_DIR) not in sys.path:
    sys.path.append(str(SIMULATION_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from resource_usage import extract_token_usage  # noqa: E402
from run_behavior_probability_estimation import (  # noqa: E402
    DEFAULT_PROMPT_PATH as DEFAULT_BEHAVIOR_PROMPT_PATH,
    load_behavior_probability_prompt,
    run_behavior_probability_estimation,
    validate_behavior_probability_payload,
)

DEFAULT_CONTEXT_PATH = SIMULATION_DIR / "output" / "llm_day_contexts_heterogeneous_test.json"
FALLBACK_CONTEXT_PATH = SIMULATION_DIR / "output" / "llm_day_contexts.json"
DEFAULT_PA_DECISION_PROMPT_PATH = SIMULATION_DIR / "PADecision_Prompt.md"
DEFAULT_PA_DECISION_FEWSHOT_PATH = SIMULATION_DIR / "PADecision_FewShot.md"
OUTPUT_DIR = SIMULATION_DIR / "output"
COMBINED_OUTPUT_PATH = OUTPUT_DIR / "llm_pa_decision_pipeline_all_agents.json"
DAILY_DECISION_LOG_PATH = OUTPUT_DIR / "llm_pa_decision_daily_log.csv"
MODEL_NAME = "gpt-oss-120b"
TEMPERATURE = 0
TOP_P = 1
LLM1_MAX_TOKENS = 2500
LLM2_MAX_TOKENS = 2500

PA_DECISION_CODEBOOK: dict[int, str] = {
    0: "skip_activity",
    1: "do_planned_activity",
    2: "adapt_activity",
    3: "extra_activity",
    4: "app_ignored",
}

SUCCESSFUL_PA_DECISION_LABELS = frozenset(
    {"do_planned_activity", "adapt_activity", "extra_activity"}
)
UNSUCCESSFUL_PA_DECISION_LABELS = frozenset({"skip_activity", "app_ignored"})
APP_IGNORED_DECISION_LABEL = "app_ignored"
ENGAGED_APP_INTERACTION_STATUS = "engaged"
IGNORED_APP_INTERACTION_STATUS = "ignored"
DIARY_ENTRY_GENERATED_FOR_SIMULATION = True

# Keep this alias for callers that imported the old constant name, but use the
# new PA-decision labels everywhere.
DECISION_CODEBOOK = PA_DECISION_CODEBOOK

EXPECTED_PA_DECISION_FIELDS = frozenset(
    {
        "persona_id",
        "day_index",
        "decision_code",
        "decision_label",
        "rationale_short",
        "diary_entry",
    }
)
DETERMINISTIC_PA_DECISION_METADATA_FIELDS = frozenset(
    {
        "app_interaction_status",
        "activity_performed",
        "diary_entry_generated_for_simulation",
    }
)

DAILY_CONTEXT_FIELDS: tuple[str, ...] = (
    "persona_id",
    "seed",
    "day_index",
    "calendar_date",
    "phase",
    "weekday",
    "planned_activity_for_day",
    "hourly_context_24h",
)

RAW_PSYCHOLOGICAL_KEYS = frozenset(
    {
        "psychological_state",
        "values_normalized",
        "raw_scale_means",
    }
)

DAILY_DECISION_LOG_COLUMNS: tuple[str, ...] = (
    "persona_id",
    "day_index",
    "decision_code",
    "decision_label",
    "activity_done",
    "activity_performed",
    "app_interaction_status",
    "diary_entry_generated_for_simulation",
    "planned_activity_for_day",
    "planned_activity_next_day",
    "behavior_policy",
    "previous_psychological_constructs",
    "updated_psychological_constructs",
    "diary_entry",
    "rationale_short",
)

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
        description="Run the end-to-end LLM behavior-policy and PA-decision pipeline."
    )
    parser.add_argument(
        "--context-path",
        type=Path,
        default=default_context_path(),
        help="Path to an exported JSON file containing llm_contexts.",
    )
    parser.add_argument(
        "--behavior-prompt-path",
        type=Path,
        default=DEFAULT_BEHAVIOR_PROMPT_PATH,
        help="Path to the LLM1 behavior probability prompt markdown file.",
    )
    parser.add_argument(
        "--pa-decision-prompt-path",
        type=Path,
        default=DEFAULT_PA_DECISION_PROMPT_PATH,
        help="Path to the LLM2 PA decision prompt markdown file.",
    )
    parser.add_argument(
        "--pa-decision-fewshot-path",
        type=Path,
        default=DEFAULT_PA_DECISION_FEWSHOT_PATH,
        help="Path to the LLM2 PA decision few-shot markdown file.",
    )
    parser.add_argument(
        "--planned-activity-path",
        type=Path,
        default=None,
        help=(
            "Optional JSON file containing planned_activity data. The file may be a single "
            "planned_activity object applied to every persona or a mapping keyed by persona_id."
        ),
    )
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--combined-output-path", type=Path, default=COMBINED_OUTPUT_PATH)
    parser.add_argument(
        "--daily-log-path",
        type=Path,
        default=None,
        help=(
            "Optional CSV path for the closed-loop daily PA decision log. "
            "Defaults to <output-dir>/llm_pa_decision_daily_log.csv."
        ),
    )
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--temperature", type=float, default=TEMPERATURE)
    parser.add_argument("--top-p", dest="top_p", type=float, default=TOP_P)
    parser.add_argument("--llm-seed", type=int, default=None)
    parser.add_argument("--llm1-max-tokens", type=int, default=LLM1_MAX_TOKENS)
    parser.add_argument("--llm2-max-tokens", type=int, default=LLM2_MAX_TOKENS)
    parser.add_argument(
        "--verbose-llm-debug",
        action="store_true",
        help=(
            "Unsafe debug-only mode: print/save additional LLM diagnostics. "
            "Reasoning content is still redacted."
        ),
    )
    return parser.parse_args(argv)


def _safe_persona_id(persona_id: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in persona_id)


def load_all_agent_contexts(context_path: Path) -> list[dict[str, Any]]:
    with context_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    contexts = payload.get("llm_contexts", [])
    if not contexts:
        raise ValueError("Keine llm_contexts in der Kontextdatei gefunden.")
    if not all(isinstance(context, dict) for context in contexts):
        raise ValueError("Alle llm_contexts müssen JSON-Objekte sein.")

    return [dict(context) for context in contexts]


def load_pa_decision_prompt(
    prompt_path: Path = DEFAULT_PA_DECISION_PROMPT_PATH,
    fewshot_path: Path = DEFAULT_PA_DECISION_FEWSHOT_PATH,
) -> str:
    """Load the LLM2 base prompt followed by the few-shot prompt with separators."""
    base_prompt = prompt_path.read_text(encoding="utf-8").strip()
    if not base_prompt:
        raise ValueError(f"PA decision prompt is empty: {prompt_path}")

    fewshot_prompt = fewshot_path.read_text(encoding="utf-8").strip()
    if not fewshot_prompt:
        raise ValueError(f"PA decision few-shot prompt is empty: {fewshot_path}")

    return "\n\n".join(
        (
            "===== PA DECISION BASE PROMPT =====",
            base_prompt,
            "===== PA DECISION FEW-SHOT EXAMPLES =====",
            fewshot_prompt,
        )
    )


def _strip_raw_psychological_fields(value: Any) -> Any:
    """Deep-copy JSON-like values while removing raw psychological-state keys."""
    if isinstance(value, Mapping):
        return {
            str(key): _strip_raw_psychological_fields(item)
            for key, item in value.items()
            if str(key) not in RAW_PSYCHOLOGICAL_KEYS
        }
    if isinstance(value, list):
        return [_strip_raw_psychological_fields(item) for item in value]
    if isinstance(value, tuple):
        return [_strip_raw_psychological_fields(item) for item in value]
    return copy.deepcopy(value)


def _contains_raw_psychological_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in RAW_PSYCHOLOGICAL_KEYS:
                return True
            if _contains_raw_psychological_field(item):
                return True
    elif isinstance(value, list):
        return any(_contains_raw_psychological_field(item) for item in value)
    return False


def prepare_daily_context_for_pa_decision(agent_context: Mapping[str, Any]) -> dict[str, Any]:
    """Build LLM2 daily_context without raw psychological construct data."""
    hourly_context = agent_context.get("hourly_context_24h")
    if not isinstance(hourly_context, list):
        raise ValueError("agent_context must contain hourly_context_24h as a list.")
    if len(hourly_context) != 24:
        raise ValueError("hourly_context_24h must contain exactly 24 entries.")

    daily_context: dict[str, Any] = {}
    for field_name in DAILY_CONTEXT_FIELDS:
        if field_name in agent_context:
            daily_context[field_name] = _strip_raw_psychological_fields(agent_context[field_name])

    # Preserve scenario labels for traceability when controlled test contexts are used,
    # without exposing raw psychological constructs to LLM2.
    if "scenario" in agent_context:
        daily_context["scenario"] = _strip_raw_psychological_fields(agent_context["scenario"])

    if _contains_raw_psychological_field(daily_context):
        raise ValueError("daily_context still contains raw psychological-state fields.")

    return daily_context


def validate_behavior_policy(behavior_policy: Mapping[str, Any]) -> dict[str, float]:
    """Validate an inner behavior_policy dict by reusing LLM1 probability validation."""
    validated = validate_behavior_probability_payload({"probabilities": dict(behavior_policy)})
    return dict(validated["probabilities"])


def build_pa_decision_input(
    agent_context: Mapping[str, Any],
    behavior_policy: Mapping[str, Any],
    planned_activity: Any | None = None,
) -> dict[str, Any]:
    """Build the exact JSON object passed to LLM2."""
    persona_id = agent_context.get("persona_id")
    if not isinstance(persona_id, str) or not persona_id.strip():
        raise ValueError("agent_context must contain a non-empty string persona_id.")

    day_index = agent_context.get("day_index")
    if isinstance(day_index, bool) or not isinstance(day_index, int):
        raise ValueError("agent_context must contain day_index as an integer.")

    return {
        "persona_id": persona_id,
        "day_index": int(day_index),
        "behavior_policy": validate_behavior_policy(behavior_policy),
        "planned_activity": _strip_raw_psychological_fields(planned_activity),
        "daily_context": prepare_daily_context_for_pa_decision(agent_context),
    }


def build_pa_decision_user_prompt(pa_decision_input: Mapping[str, Any]) -> str:
    input_json = json.dumps(pa_decision_input, ensure_ascii=False, separators=(",", ":"))
    return f"""
INPUT:
{input_json}

IMPORTANT:
Use only the provided behavior_policy, daily_context, and planned_activity. Do not infer raw psychological constructs and do not invent app recommendations or planned activities.
Return exactly one valid JSON object in the required PA decision schema.
""".strip()


def parse_pa_decision_json(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM2 PA decision output is not valid JSON: {exc.msg}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("LLM2 PA decision JSON must be a top-level object.")
    return parsed


def _require_non_empty_string(payload: Mapping[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value


def activity_performed_for_decision_label(decision_label: str) -> bool:
    """Return whether the final PA decision includes performed physical activity."""
    return decision_label in SUCCESSFUL_PA_DECISION_LABELS


def app_interaction_status_for_decision_label(decision_label: str) -> str:
    """Return app engagement metadata for a final PA decision label."""
    if decision_label == APP_IGNORED_DECISION_LABEL:
        return IGNORED_APP_INTERACTION_STATUS
    return ENGAGED_APP_INTERACTION_STATUS


def add_pa_decision_metadata(pa_decision: Mapping[str, Any]) -> dict[str, Any]:
    """Attach deterministic trace metadata to a validated PA decision."""
    decision_label = str(pa_decision["decision_label"])
    enriched = dict(pa_decision)
    enriched["app_interaction_status"] = app_interaction_status_for_decision_label(decision_label)
    enriched["activity_performed"] = activity_performed_for_decision_label(decision_label)
    enriched["diary_entry_generated_for_simulation"] = DIARY_ENTRY_GENERATED_FOR_SIMULATION
    return enriched


def validate_pa_decision_output(
    payload: Mapping[str, Any],
    expected_persona_id: str,
    expected_day_index: int,
) -> dict[str, Any]:
    core_payload = {
        key: value
        for key, value in payload.items()
        if key not in DETERMINISTIC_PA_DECISION_METADATA_FIELDS
    }
    actual_fields = set(core_payload)
    if actual_fields != EXPECTED_PA_DECISION_FIELDS:
        missing = sorted(EXPECTED_PA_DECISION_FIELDS - actual_fields)
        extra = sorted(actual_fields - EXPECTED_PA_DECISION_FIELDS)
        raise ValueError(f"PA decision fields mismatch. Missing: {missing}; extra: {extra}.")

    persona_id = _require_non_empty_string(core_payload, "persona_id")
    if persona_id != expected_persona_id:
        raise ValueError(
            f"persona_id must match input persona_id {expected_persona_id!r}; got {persona_id!r}."
        )

    day_index = core_payload["day_index"]
    if isinstance(day_index, bool) or not isinstance(day_index, int):
        raise ValueError("day_index must be an integer.")
    if int(day_index) != int(expected_day_index):
        raise ValueError(
            f"day_index must match input day_index {expected_day_index}; got {day_index}."
        )

    decision_code = core_payload["decision_code"]
    if isinstance(decision_code, bool) or not isinstance(decision_code, int):
        raise ValueError("decision_code must be an integer.")
    if decision_code not in PA_DECISION_CODEBOOK:
        raise ValueError(f"decision_code must be one of {sorted(PA_DECISION_CODEBOOK)}.")

    expected_label = PA_DECISION_CODEBOOK[decision_code]
    if core_payload["decision_label"] != expected_label:
        raise ValueError(
            f"decision_label must be {expected_label!r} for decision_code {decision_code}."
        )

    rationale_short = _require_non_empty_string(core_payload, "rationale_short")
    diary_entry = _require_non_empty_string(core_payload, "diary_entry")

    return add_pa_decision_metadata(
        {
            "persona_id": persona_id,
            "day_index": int(day_index),
            "decision_code": int(decision_code),
            "decision_label": expected_label,
            "rationale_short": rationale_short,
            "diary_entry": diary_entry,
        }
    )


def parse_and_validate_pa_decision(
    raw: str,
    *,
    expected_persona_id: str,
    expected_day_index: int,
) -> dict[str, Any]:
    return validate_pa_decision_output(
        parse_pa_decision_json(raw),
        expected_persona_id=expected_persona_id,
        expected_day_index=expected_day_index,
    )


# Backward-compatible parser names now validate the new PA decision schema when
# explicit expectations are supplied. They are kept to avoid surprising imports.
def parse_llm_decision_json(raw: str) -> dict[str, Any]:
    return parse_pa_decision_json(raw)


def validate_llm_decision_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    persona_id = payload.get("persona_id")
    day_index = payload.get("day_index")
    if not isinstance(persona_id, str) or isinstance(day_index, bool) or not isinstance(day_index, int):
        raise ValueError("payload must include persona_id and day_index for PA decision validation.")
    return validate_pa_decision_output(payload, persona_id, day_index)


def parse_and_validate_llm_decision(raw: str) -> dict[str, Any]:
    payload = parse_pa_decision_json(raw)
    return validate_llm_decision_payload(payload)


def _extract_llm_content(response: Any, persona_id: str) -> str:
    choices = getattr(response, "choices", None)
    if not choices:
        raise RuntimeError(f"LLM2 response for {persona_id} did not contain any choices.")
    message = getattr(choices[0], "message", None)
    if message is None:
        raise RuntimeError(f"LLM2 response for {persona_id} did not contain choices[0].message.")
    content = getattr(message, "content", None)
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(f"LLM2 hat für {persona_id} keine sichtbare JSON-Antwort zurückgegeben.")
    return content


def save_invalid_raw_response(
    persona_id: str,
    raw_response: str,
    output_dir: Path = OUTPUT_DIR,
    *,
    verbose_llm_debug: bool = False,
) -> Path:
    output_path = output_dir / f"llm_pa_decision_{_safe_persona_id(persona_id)}_raw_invalid.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if verbose_llm_debug:
        output_path.write_text(raw_response, encoding="utf-8")
    else:
        output_path.write_text(
            "Invalid LLM2 output redacted by default. Re-run with "
            "--verbose-llm-debug to save full invalid visible content.\n",
            encoding="utf-8",
        )
    return output_path


def _summarize_usage(response: Any) -> str:
    usage = extract_token_usage(response)
    return (
        f"tokens prompt={usage['prompt_tokens']} "
        f"response={usage['response_tokens']} total={usage['tokens_total']} "
        f"source={usage['token_source']}"
    )


def run_pa_decision_llm(
    pa_decision_input: Mapping[str, Any],
    *,
    system_prompt: str,
    model: str = MODEL_NAME,
    temperature: float = TEMPERATURE,
    top_p: float = TOP_P,
    llm_seed: int | None = None,
    max_tokens: int = LLM2_MAX_TOKENS,
    output_dir: Path = OUTPUT_DIR,
    verbose_llm_debug: bool = False,
) -> dict[str, Any]:
    persona_id = str(pa_decision_input["persona_id"])
    day_index = int(pa_decision_input["day_index"])
    user_prompt = build_pa_decision_user_prompt(pa_decision_input)

    print(f"Starte LLM2-PA-Entscheidung für {persona_id} ...", flush=True)
    call_started = time.perf_counter()
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
        top_p=top_p,
        max_tokens=max_tokens,
        # Seed is opt-in because OpenAI-compatible providers vary in support.
        # With no seed, determinism remains best-effort via temperature=0/top_p=1.
        **({"seed": int(llm_seed)} if llm_seed is not None else {}),
    )

    call_seconds = time.perf_counter() - call_started
    print(f"LLM2-PA-Entscheidung für {persona_id} abgeschlossen.", flush=True)
    choices = getattr(response, "choices", None)
    finish_reason = getattr(choices[0], "finish_reason", None) if choices else None
    print(
        f"LLM2 finish_reason for {persona_id}/day {day_index}: {finish_reason!r}",
        flush=True,
    )
    print(f"LLM2 usage for {persona_id}/day {day_index}: {_summarize_usage(response)}", flush=True)
    if verbose_llm_debug:
        print(
            "UNSAFE DEBUG LLM2 response object suppressed; full messages, prompts, "
            "completions, and hidden reasoning are not printed.",
            flush=True,
        )
    content = _extract_llm_content(response, persona_id)

    try:
        result = parse_and_validate_pa_decision(
            content,
            expected_persona_id=persona_id,
            expected_day_index=day_index,
        )
        result["_resource_usage"] = {
            **extract_token_usage(response),
            "paper_seconds": call_seconds,
        }
        return result
    except ValueError as exc:
        debug_path = save_invalid_raw_response(
            persona_id,
            content,
            output_dir=output_dir,
            verbose_llm_debug=verbose_llm_debug,
        )
        raise ValueError(
            f"Ungültiger LLM2-JSON-Output für {persona_id}: {exc}. "
            f"Raw response gespeichert unter: {debug_path}"
        ) from exc


def save_agent_behavior_policy(
    persona_id: str,
    day_index: int,
    behavior_policy: Mapping[str, Any],
    output_dir: Path = OUTPUT_DIR,
) -> Path:
    output_path = output_dir / f"llm_behavior_probability_{_safe_persona_id(persona_id)}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "persona_id": persona_id,
        "day_index": int(day_index),
        "behavior_policy": validate_behavior_policy(behavior_policy),
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def save_agent_pa_decision(
    persona_id: str,
    pa_decision: Mapping[str, Any],
    output_dir: Path = OUTPUT_DIR,
) -> Path:
    output_path = output_dir / f"llm_pa_decision_{_safe_persona_id(persona_id)}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(dict(pa_decision), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def _json_log_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def extract_psychological_construct_values(agent_context: Mapping[str, Any]) -> dict[str, float]:
    """Return normalized psychological construct values from an agent context."""
    psychological_state = agent_context.get("psychological_state")
    if not isinstance(psychological_state, Mapping):
        return {}

    values_normalized = psychological_state.get("values_normalized")
    if not isinstance(values_normalized, Mapping):
        return {}

    constructs: dict[str, float] = {}
    for key, value in values_normalized.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        constructs[str(key)] = float(value)
    return constructs


def update_psychological_constructs_simple(
    previous_constructs: dict[str, float],
    decision_label: str,
    delta_done: float = 0.02,
    delta_no_pa: float = -0.02,
) -> dict[str, float]:
    """Apply a small deterministic placeholder update to psychological constructs.

    Supportive constructs move up after successful PA and down after unsuccessful PA.
    ``pressure_tension`` is inverted because higher values mean more pressure and tension.
    """
    if decision_label in SUCCESSFUL_PA_DECISION_LABELS:
        supportive_delta = delta_done
    elif decision_label in UNSUCCESSFUL_PA_DECISION_LABELS:
        supportive_delta = delta_no_pa
    else:
        supportive_delta = 0.0

    updated: dict[str, float] = {}
    for key, value in previous_constructs.items():
        delta = -supportive_delta if key == "pressure_tension" else supportive_delta
        updated[key] = min(1.0, max(0.0, float(value) + delta))
    return updated


def generate_planned_activity_next_day(decision_label: str) -> dict[str, Any]:
    """Generate a deterministic LLM3-placeholder planned activity for tomorrow."""
    if decision_label in SUCCESSFUL_PA_DECISION_LABELS:
        return {
            "activity_type": "indoor_activity",
            "duration_min": 20,
            "intensity": "moderate",
            "preferred_time_window": [17, 20],
            "description": "20 Minuten intensive Oberkörpereinheit im Gym",
        }

    return {
        "activity_type": "outdoor_activity",
        "duration_min": 15,
        "intensity": "light",
        "preferred_time_window": [14, 17],
        "description": "15 Minuten Spaziergang am Nachmittag",
    }


def write_daily_decision_log_row(
    *,
    log_path: Path,
    persona_id: str,
    day_index: int,
    pa_decision: Mapping[str, Any],
    activity_done: bool,
    planned_activity_for_day: Any | None,
    planned_activity_next_day: Mapping[str, Any],
    behavior_policy: Mapping[str, Any],
    previous_psychological_constructs: Mapping[str, Any],
    updated_psychological_constructs: Mapping[str, Any],
) -> Path:
    """Append one closed-loop PA-decision row to the daily CSV log."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    should_write_header = not log_path.exists() or log_path.stat().st_size == 0

    row = {
        "persona_id": persona_id,
        "day_index": int(day_index),
        "decision_code": int(pa_decision["decision_code"]),
        "decision_label": str(pa_decision["decision_label"]),
        "activity_done": bool(activity_done),
        "activity_performed": bool(pa_decision.get("activity_performed", activity_done)),
        "app_interaction_status": str(
            pa_decision.get(
                "app_interaction_status",
                app_interaction_status_for_decision_label(str(pa_decision["decision_label"])),
            )
        ),
        "diary_entry_generated_for_simulation": bool(
            pa_decision.get(
                "diary_entry_generated_for_simulation",
                DIARY_ENTRY_GENERATED_FOR_SIMULATION,
            )
        ),
        "planned_activity_for_day": _json_log_value(planned_activity_for_day),
        "planned_activity_next_day": _json_log_value(dict(planned_activity_next_day)),
        "behavior_policy": _json_log_value(dict(behavior_policy)),
        "previous_psychological_constructs": _json_log_value(
            dict(previous_psychological_constructs)
        ),
        "updated_psychological_constructs": _json_log_value(dict(updated_psychological_constructs)),
        "diary_entry": str(pa_decision["diary_entry"]),
        "rationale_short": str(pa_decision["rationale_short"]),
    }

    with log_path.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=DAILY_DECISION_LOG_COLUMNS)
        if should_write_header:
            writer.writeheader()
        writer.writerow(row)

    return log_path


def build_closed_loop_update(
    *,
    agent_context: Mapping[str, Any],
    pa_decision: Mapping[str, Any],
    behavior_policy: Mapping[str, Any],
    planned_activity_for_day: Any | None,
    log_path: Path,
) -> dict[str, Any]:
    """Run the simple post-LLM2 closed-loop placeholder and persist its CSV row."""
    persona_id = str(pa_decision["persona_id"])
    day_index = int(pa_decision["day_index"])
    decision_label = str(pa_decision["decision_label"])
    activity_done = activity_performed_for_decision_label(decision_label)
    previous_constructs = extract_psychological_construct_values(agent_context)
    updated_constructs = update_psychological_constructs_simple(
        previous_constructs,
        decision_label,
    )
    planned_activity_next_day = generate_planned_activity_next_day(decision_label)

    write_daily_decision_log_row(
        log_path=log_path,
        persona_id=persona_id,
        day_index=day_index,
        pa_decision=pa_decision,
        activity_done=activity_done,
        planned_activity_for_day=planned_activity_for_day,
        planned_activity_next_day=planned_activity_next_day,
        behavior_policy=behavior_policy,
        previous_psychological_constructs=previous_constructs,
        updated_psychological_constructs=updated_constructs,
    )

    return {
        "activity_done": activity_done,
        "activity_performed": activity_done,
        "app_interaction_status": app_interaction_status_for_decision_label(decision_label),
        "diary_entry_generated_for_simulation": DIARY_ENTRY_GENERATED_FOR_SIMULATION,
        "previous_psychological_constructs": previous_constructs,
        "updated_psychological_constructs": updated_constructs,
        "planned_activity_next_day": planned_activity_next_day,
    }


def _resource_usage_from_payload(payload: Mapping[str, Any], fallback_seconds: float, token_source: str) -> dict[str, Any]:
    usage = payload.get("_resource_usage")
    if not isinstance(usage, Mapping):
        return {
            "prompt_tokens": 0,
            "response_tokens": 0,
            "tokens_total": 0,
            "token_source": token_source,
            "paper_seconds": fallback_seconds,
        }
    return {
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "response_tokens": int(usage.get("response_tokens") or 0),
        "tokens_total": int(usage.get("tokens_total") or 0),
        "token_source": str(usage.get("token_source") or token_source),
        "paper_seconds": float(usage.get("paper_seconds") or fallback_seconds),
    }


def _log_resource_usage(
    resource_tracker: Any | None,
    *,
    paper_id: str,
    stage: str,
    usage: Mapping[str, Any],
) -> None:
    if resource_tracker is None:
        return
    token_source = str(usage.get("token_source") or "unavailable")
    resource_tracker.log_paper(
        paper_id=paper_id,
        stage=stage,
        prompt_tokens=int(usage.get("prompt_tokens") or 0),
        response_tokens=int(usage.get("response_tokens") or 0),
        tokens_total=int(usage.get("tokens_total") or 0),
        prompt_tokens_source=token_source,
        response_tokens_source=token_source,
        embedding_tokens_source="unavailable",
        token_source=token_source,
        paper_seconds=float(usage.get("paper_seconds") or 0.0),
    )


def run_pipeline_for_context(
    agent_context: Mapping[str, Any],
    *,
    behavior_system_prompt: str,
    pa_decision_system_prompt: str,
    planned_activity: Any | None = None,
    model: str = MODEL_NAME,
    temperature: float = TEMPERATURE,
    top_p: float = TOP_P,
    llm_seed: int | None = None,
    llm1_max_tokens: int = LLM1_MAX_TOKENS,
    llm2_max_tokens: int = LLM2_MAX_TOKENS,
    output_dir: Path = OUTPUT_DIR,
    daily_log_path: Path | None = None,
    behavior_runner: Callable[..., Mapping[str, Any]] = run_behavior_probability_estimation,
    pa_decision_runner: Callable[..., Mapping[str, Any]] = run_pa_decision_llm,
    resource_tracker: Any | None = None,
    resource_usage_token_source: str = "unavailable",
    verbose_llm_debug: bool = False,
) -> dict[str, Any]:
    persona_id = str(agent_context.get("persona_id", "unknown_persona"))
    day_index = int(agent_context.get("day_index", 0))

    behavior_started = time.perf_counter()
    behavior_payload = dict(behavior_runner(
        agent_context,
        system_prompt=behavior_system_prompt,
        model=model,
        temperature=temperature,
        top_p=top_p,
        llm_seed=llm_seed,
        max_tokens=llm1_max_tokens,
        output_dir=output_dir,
        verbose_llm_debug=verbose_llm_debug,
    ))
    behavior_seconds = time.perf_counter() - behavior_started
    behavior_usage = _resource_usage_from_payload(
        behavior_payload, behavior_seconds, resource_usage_token_source
    )
    behavior_payload.pop("_resource_usage", None)
    _log_resource_usage(
        resource_tracker,
        paper_id=f"llm1_persona_{persona_id}_day_{day_index}",
        stage="llm1_behavior_probability",
        usage=behavior_usage,
    )
    if "probabilities" in behavior_payload:
        behavior_policy = validate_behavior_policy(behavior_payload["probabilities"])
    else:
        behavior_policy = validate_behavior_policy(behavior_payload)

    behavior_output_path = save_agent_behavior_policy(
        persona_id,
        day_index,
        behavior_policy,
        output_dir=output_dir,
    )

    pa_decision_input = build_pa_decision_input(
        agent_context,
        behavior_policy,
        planned_activity=planned_activity,
    )
    pa_started = time.perf_counter()
    pa_decision = dict(
        pa_decision_runner(
            pa_decision_input,
            system_prompt=pa_decision_system_prompt,
            model=model,
            temperature=temperature,
            top_p=top_p,
            llm_seed=llm_seed,
            max_tokens=llm2_max_tokens,
            output_dir=output_dir,
            verbose_llm_debug=verbose_llm_debug,
        )
    )
    pa_seconds = time.perf_counter() - pa_started
    pa_usage = _resource_usage_from_payload(pa_decision, pa_seconds, resource_usage_token_source)
    pa_decision.pop("_resource_usage", None)
    _log_resource_usage(
        resource_tracker,
        paper_id=f"llm2_persona_{persona_id}_day_{day_index}",
        stage="llm2_pa_decision",
        usage=pa_usage,
    )
    pa_decision = validate_pa_decision_output(
        pa_decision,
        expected_persona_id=persona_id,
        expected_day_index=day_index,
    )

    pa_decision_output_path = save_agent_pa_decision(
        persona_id,
        pa_decision,
        output_dir=output_dir,
    )

    actual_daily_log_path = daily_log_path or output_dir / DAILY_DECISION_LOG_PATH.name
    closed_loop_update = build_closed_loop_update(
        agent_context=agent_context,
        pa_decision=pa_decision,
        behavior_policy=behavior_policy,
        planned_activity_for_day=planned_activity,
        log_path=actual_daily_log_path,
    )

    record: dict[str, Any] = {
        "persona_id": persona_id,
        "day_index": day_index,
        "behavior_policy": behavior_policy,
        "pa_decision": pa_decision,
        "closed_loop_update": closed_loop_update,
        "output_files": {
            "behavior_policy": str(behavior_output_path),
            "pa_decision": str(pa_decision_output_path),
            "daily_decision_log": str(actual_daily_log_path),
        },
    }
    if "scenario" in agent_context:
        record["scenario"] = agent_context["scenario"]
    return record


def load_planned_activities(planned_activity_path: Path | None) -> Any | None:
    if planned_activity_path is None:
        return None
    with planned_activity_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def planned_activity_for_persona(planned_activities: Any | None, persona_id: str) -> Any | None:
    if planned_activities is None:
        return None
    if isinstance(planned_activities, Mapping) and persona_id in planned_activities:
        return planned_activities[persona_id]
    return planned_activities


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.combined_output_path.parent.mkdir(parents=True, exist_ok=True)

    behavior_system_prompt = load_behavior_probability_prompt(args.behavior_prompt_path)
    pa_decision_system_prompt = load_pa_decision_prompt(
        args.pa_decision_prompt_path,
        args.pa_decision_fewshot_path,
    )
    planned_activities = load_planned_activities(args.planned_activity_path)
    agent_contexts = load_all_agent_contexts(args.context_path)
    print(f"{len(agent_contexts)} Agenten-Kontexte geladen.", flush=True)

    records: list[dict[str, Any]] = []
    for index, agent_context in enumerate(agent_contexts):
        persona_id = str(agent_context.get("persona_id", f"agent_{index}"))

        print("\n" + "=" * 80, flush=True)
        print(f"Verarbeite Agent {index + 1}/{len(agent_contexts)}: {persona_id}", flush=True)
        print("=" * 80, flush=True)

        record = run_pipeline_for_context(
            agent_context,
            behavior_system_prompt=behavior_system_prompt,
            pa_decision_system_prompt=pa_decision_system_prompt,
            planned_activity=planned_activity_for_persona(planned_activities, persona_id),
            model=args.model,
            temperature=args.temperature,
            top_p=args.top_p,
            llm_seed=args.llm_seed,
            llm1_max_tokens=args.llm1_max_tokens,
            llm2_max_tokens=args.llm2_max_tokens,
            output_dir=args.output_dir,
            daily_log_path=args.daily_log_path or args.output_dir / DAILY_DECISION_LOG_PATH.name,
            verbose_llm_debug=args.verbose_llm_debug,
        )
        records.append(record)

        print("\nLLM-PA-Pipeline-Ergebnis gespeichert.")
        print(
            "Kurzstatus: "
            f"persona_id={record['persona_id']}, day_index={record['day_index']}, "
            f"decision_label={record['pa_decision']['decision_label']}"
        )
        if args.verbose_llm_debug:
            print("UNSAFE DEBUG validated pipeline record:")
            print(json.dumps(record, ensure_ascii=False, indent=2))

    combined_payload = {
        "metadata": {
            "source_context_file": str(args.context_path),
            "behavior_probability_prompt_file": str(args.behavior_prompt_path),
            "pa_decision_prompt_file": str(args.pa_decision_prompt_path),
            "pa_decision_fewshot_file": str(args.pa_decision_fewshot_path),
            "planned_activity_file": str(args.planned_activity_path) if args.planned_activity_path else None,
            "daily_log_file": str(args.daily_log_path or args.output_dir / DAILY_DECISION_LOG_PATH.name),
            "model": args.model,
            "temperature": args.temperature,
            "top_p": args.top_p,
            "llm_seed": args.llm_seed,
            "llm1_max_tokens": args.llm1_max_tokens,
            "llm2_max_tokens": args.llm2_max_tokens,
            "n_contexts": len(agent_contexts),
        },
        "records": records,
    }
    args.combined_output_path.write_text(
        json.dumps(combined_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\n" + "=" * 80)
    print("Alle LLM-PA-Pipeline-Entscheidungen abgeschlossen.")
    print(f"Gesamtdatei gespeichert unter: {args.combined_output_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
