from __future__ import annotations

import json
import os
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from psychological_state import BACKEND_CONSTRUCT_RANGES
from resource_usage import extract_token_usage

SIMULATION_DIR = Path(__file__).resolve().parent
DEFAULT_PROMPT_PATH = SIMULATION_DIR / "AssessmentModel_Prompt.md"
DEFAULT_MODEL_NAME = "gpt-oss-120b"
DEFAULT_MAX_TOKENS = 10000
RETRY_MIN_MAX_TOKENS = 12000
PREVIOUS_DIARY_CONTEXT_WINDOW = 7
PREVIOUS_DIARY_CONTEXT_STRATEGY = "rolling_window_last_7_entries"
JSON_REPAIR_INSTRUCTION = (
    "Your previous State Assessment response was invalid. Return only one complete valid JSON object "
    "parseable by Python json.loads. All property names must be enclosed in double quotes. "
    "Do not use markdown, comments, trailing commas, ellipses, or unquoted keys. "
    "Every active construct must be present in item_scores, and each construct must contain "
    "exactly the required number of item objects with the expected question_id, score, range, "
    "evidence_spans, and reasoning_short fields."
)
PSYCHOLOGICAL_CONSTRUCT_UPDATE_ALPHA = 0.20
PSYCHOLOGICAL_CONSTRUCT_UPDATE_MAX_DAILY_CHANGE = 0.10

CONSTRUCT_ITEM_COUNTS: dict[str, int] = {
    "automaticity": 4,
    "pa_specific_self_control": 3,
    "action_planning": 4,
    "intention": 3,
    "perceived_behavioral_control": 4,
    "attitude_toward_the_behavior": 5,
    "subjective_norm": 6,
    "intrinsic_motivation": 12,
    "motivational_competence": 4,
}
ACTIVE_CONSTRUCTS: tuple[str, ...] = tuple(CONSTRUCT_ITEM_COUNTS)
REMOVED_CONSTRUCTS = frozenset(
    {
        "interest_enjoyment",
        "perceived_competence",
        "perceived_choice",
        "pressure_tension",
    }
)
REQUIRED_PROMPT_PLACEHOLDERS: tuple[str, ...] = (
    "persona_id",
    "day_index",
    "previous_psychological_construct_values",
    "current_decision_label",
    "was_physical_activity_planned_today",
    "planned_physical_activity_summary",
    "current_simulated_diary_entry",
    "previous_diary_entries",
    "previous_diary_entries_summary",
)

_client: Any | None = None


def load_state_assessment_prompt(prompt_path: Path = DEFAULT_PROMPT_PATH) -> str:
    prompt = prompt_path.read_text(encoding="utf-8")
    if not prompt.strip():
        raise ValueError(f"State Assessment prompt is empty: {prompt_path}")
    if "{recommendation_data}" in prompt:
        raise ValueError("State Assessment prompt must not use {recommendation_data}.")
    missing = [
        placeholder
        for placeholder in REQUIRED_PROMPT_PLACEHOLDERS
        if "{" + placeholder + "}" not in prompt
    ]
    if missing:
        raise ValueError(f"State Assessment prompt is missing placeholders: {missing}.")
    return prompt


def _render_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def render_state_assessment_prompt(
    prompt_template: str,
    *,
    persona_id: str,
    day_index: int,
    previous_psychological_construct_values: Mapping[str, Any],
    current_simulated_diary_entry: str,
    previous_diary_entries: Sequence[Mapping[str, Any]],
    current_decision_label: str | None = None,
    was_physical_activity_planned_today: bool | None = None,
    planned_physical_activity_summary: Mapping[str, Any] | None = None,
    previous_diary_entries_summary: str | None,
) -> str:
    values = {
        "persona_id": persona_id,
        "day_index": day_index,
        "previous_psychological_construct_values": previous_psychological_construct_values,
        "current_decision_label": current_decision_label or "unknown",
        "was_physical_activity_planned_today": was_physical_activity_planned_today,
        "planned_physical_activity_summary": planned_physical_activity_summary,
        "current_simulated_diary_entry": current_simulated_diary_entry,
        "previous_diary_entries": list(previous_diary_entries),
        "previous_diary_entries_summary": previous_diary_entries_summary or "Keine Zusammenfassung verfügbar.",
    }
    rendered = prompt_template
    for placeholder, value in values.items():
        rendered = rendered.replace("{" + placeholder + "}", _render_value(value))
    unresolved = [
        placeholder
        for placeholder in REQUIRED_PROMPT_PLACEHOLDERS
        if "{" + placeholder + "}" in rendered
    ]
    if unresolved:
        raise ValueError(f"State Assessment prompt has unresolved placeholders: {unresolved}.")
    if "{recommendation_data}" in rendered:
        raise ValueError("Rendered State Assessment prompt contains {recommendation_data}.")
    return rendered


def parse_state_assessment_json(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"State Assessment output is not valid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("State Assessment output must be a top-level JSON object.")
    return payload


def _validate_score(score: Any, construct: str) -> float | None:
    if score is None:
        return None
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise ValueError(f"{construct} item score must be numeric or null.")
    value = float(score)
    low, high = BACKEND_CONSTRUCT_RANGES[construct]
    if not low <= value <= high:
        raise ValueError(
            f"{construct} item score {value} is outside expected range {low:g}-{high:g}."
        )
    return value


def _cap_numeric_item_scores(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return a copy with numeric item scores capped to construct scale bounds."""
    capped_payload = deepcopy(payload)
    item_scores = capped_payload.get("item_scores")
    if not isinstance(item_scores, Mapping):
        return capped_payload

    for construct, construct_payload in item_scores.items():
        if construct not in BACKEND_CONSTRUCT_RANGES or not isinstance(
            construct_payload, Mapping
        ):
            continue
        items = construct_payload.get("items")
        if not isinstance(items, list):
            continue
        low, high = BACKEND_CONSTRUCT_RANGES[construct]
        for item in items:
            if not isinstance(item, dict):
                continue
            score = item.get("score")
            if score is None or isinstance(score, bool) or not isinstance(
                score, (int, float)
            ):
                continue
            if score < low:
                item["score"] = float(low)
            elif score > high:
                item["score"] = float(high)
    return capped_payload


def _find_removed_construct_keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in REMOVED_CONSTRUCTS:
                found.add(str(key))
            found.update(_find_removed_construct_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_find_removed_construct_keys(item))
    return found


def validate_state_assessment_output(
    payload: Mapping[str, Any],
    *,
    expected_persona_id: str,
    expected_day_index: int,
) -> dict[str, Any]:
    payload = _cap_numeric_item_scores(payload)
    removed_anywhere = sorted(_find_removed_construct_keys(payload))
    if removed_anywhere:
        raise ValueError(
            f"State Assessment contains removed construct keys: {removed_anywhere}."
        )
    persona_id = payload.get("persona_id")
    day_index = payload.get("day_index")
    if persona_id != expected_persona_id:
        raise ValueError("State Assessment persona_id does not match the request.")
    if isinstance(day_index, bool) or not isinstance(day_index, int) or day_index != expected_day_index:
        raise ValueError("State Assessment day_index does not match the request.")

    item_scores = payload.get("item_scores")
    if not isinstance(item_scores, Mapping):
        raise ValueError("State Assessment item_scores must be an object.")
    keys = set(item_scores)
    expected = set(ACTIVE_CONSTRUCTS)
    if keys != expected:
        raise ValueError(
            "State Assessment construct keys mismatch. "
            f"Missing: {sorted(expected - keys)}; extra: {sorted(keys - expected)}."
        )

    validated_scores: dict[str, Any] = {}
    mean_scores: dict[str, float | None] = {}
    for construct in ACTIVE_CONSTRUCTS:
        construct_payload = item_scores[construct]
        if not isinstance(construct_payload, Mapping):
            raise ValueError(f"{construct} must be an object.")
        items = construct_payload.get("items")
        if not isinstance(items, list):
            raise ValueError(f"{construct}.items must be a list.")
        expected_count = CONSTRUCT_ITEM_COUNTS[construct]
        if len(items) != expected_count:
            raise ValueError(
                f"{construct}.items must contain exactly {expected_count} items; got {len(items)}."
            )

        low, high = BACKEND_CONSTRUCT_RANGES[construct]
        expected_range = f"{low:g}-{high:g}"
        validated_items: list[dict[str, Any]] = []
        non_null_scores: list[float] = []
        for item in items:
            if not isinstance(item, Mapping):
                raise ValueError(f"{construct} items must be objects.")
            question_id = item.get("question_id")
            if not isinstance(question_id, str) or not question_id:
                raise ValueError(f"{construct} question_id must be a non-empty string.")
            score = _validate_score(item.get("score"), construct)
            if item.get("range") != expected_range:
                raise ValueError(f"{construct} item range must be {expected_range!r}.")
            evidence_spans = item.get("evidence_spans")
            if not isinstance(evidence_spans, list):
                raise ValueError(f"{construct} evidence_spans must be a list.")
            reasoning_short = item.get("reasoning_short")
            if not isinstance(reasoning_short, str):
                raise ValueError(f"{construct} reasoning_short must be a string.")
            if score is not None:
                non_null_scores.append(score)
            validated_items.append(
                {
                    "question_id": question_id,
                    "score": score,
                    "range": expected_range,
                    "evidence_spans": list(evidence_spans),
                    "reasoning_short": reasoning_short,
                }
            )
        recomputed_mean = (
            sum(non_null_scores) / len(non_null_scores) if non_null_scores else None
        )
        mean_scores[construct] = recomputed_mean
        validated_scores[construct] = {
            "items": validated_items,
            "mean_score": recomputed_mean,
        }

    return {
        "persona_id": expected_persona_id,
        "day_index": expected_day_index,
        "item_scores": validated_scores,
        "mean_scores_raw": mean_scores,
    }


def normalize_mean_scores(
    mean_scores_raw: Mapping[str, float | None],
    previous_normalized_values: Mapping[str, Any],
) -> dict[str, float]:
    if set(mean_scores_raw) != set(ACTIVE_CONSTRUCTS):
        raise ValueError("Raw mean scores must contain exactly the nine active constructs.")
    normalized: dict[str, float] = {}
    for construct in ACTIVE_CONSTRUCTS:
        raw_mean = mean_scores_raw[construct]
        if raw_mean is None:
            previous = previous_normalized_values.get(construct)
            if isinstance(previous, bool) or not isinstance(previous, (int, float)):
                raise ValueError(f"Missing previous normalized value for {construct}.")
            normalized[construct] = float(previous)
            continue
        low, high = BACKEND_CONSTRUCT_RANGES[construct]
        if not low <= float(raw_mean) <= high:
            raise ValueError(f"Raw mean for {construct} is outside its expected range.")
        value = (float(raw_mean) - low) / (high - low)
        normalized[construct] = min(1.0, max(0.0, value))
    return normalized


def apply_smoothed_bounded_construct_update(
    previous_values: Mapping[str, float],
    target_values: Mapping[str, float | None],
    raw_target_values: Mapping[str, float | None],
    *,
    alpha: float = PSYCHOLOGICAL_CONSTRUCT_UPDATE_ALPHA,
    max_daily_change: float = PSYCHOLOGICAL_CONSTRUCT_UPDATE_MAX_DAILY_CHANGE,
) -> dict[str, dict[str, float]]:
    """Move constructs deterministically toward assessment targets with a daily bound."""
    proposed_deltas: dict[str, float] = {}
    applied_deltas: dict[str, float] = {}
    updated_values: dict[str, float] = {}
    for construct in ACTIVE_CONSTRUCTS:
        previous = float(previous_values[construct])
        if raw_target_values[construct] is None:
            proposed_delta = 0.0
            applied_delta = 0.0
        else:
            proposed_delta = alpha * (float(target_values[construct]) - previous)
            applied_delta = max(-max_daily_change, min(max_daily_change, proposed_delta))
        proposed_deltas[construct] = proposed_delta
        applied_deltas[construct] = applied_delta
        updated_values[construct] = min(1.0, max(0.0, previous + applied_delta))
    return {
        "delta_proposed": proposed_deltas,
        "delta_applied": applied_deltas,
        "updated_values": updated_values,
    }


def build_dry_run_state_assessment(
    *,
    persona_id: str,
    day_index: int,
    previous_normalized_values: Mapping[str, Any],
) -> dict[str, Any]:
    item_scores: dict[str, Any] = {}
    for construct in ACTIVE_CONSTRUCTS:
        low, high = BACKEND_CONSTRUCT_RANGES[construct]
        normalized = float(previous_normalized_values[construct])
        raw_value = low + normalized * (high - low)
        item_scores[construct] = {
            "items": [
                {
                    "question_id": f"{construct}_q{index}",
                    "score": raw_value,
                    "range": f"{low:g}-{high:g}",
                    "evidence_spans": [],
                    "reasoning_short": "",
                }
                for index in range(1, CONSTRUCT_ITEM_COUNTS[construct] + 1)
            ],
            "mean_score": raw_value,
        }
    return {
        "persona_id": persona_id,
        "day_index": day_index,
        "item_scores": item_scores,
        "metadata": {"mode": "dry_run_mock"},
    }


def _get_client() -> Any:
    global _client
    if _client is None:
        from dotenv import load_dotenv
        from openai import OpenAI

        load_dotenv()
        api_key = os.getenv("UNI_LLM_API_KEY")
        if not api_key:
            raise ValueError("UNI_LLM_API_KEY not found for State Assessment.")
        _client = OpenAI(api_key=api_key, base_url="https://gpustack.unibe.ch/v1")
    return _client


def _extract_content(response: Any) -> str:
    choices = getattr(response, "choices", None)
    if not choices:
        raise RuntimeError("State Assessment response did not contain choices.")
    content = getattr(getattr(choices[0], "message", None), "content", None)
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("State Assessment response did not contain visible JSON content.")
    return content


def _response_finish_reason(response: Any) -> str | None:
    choices = getattr(response, "choices", None)
    return getattr(choices[0], "finish_reason", None) if choices else None


def call_state_assessment_llm(
    rendered_prompt: str,
    *,
    model: str = DEFAULT_MODEL_NAME,
    temperature: float = 0,
    top_p: float = 1,
    llm_seed: int | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    repair_instruction: str | None = None,
    json_mode: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    messages = [
        {
            "role": "system",
            "content": (
                "Return exactly one valid JSON object. Do not use markdown fences, comments, "
                "trailing commas, unquoted keys, or commentary outside the JSON object."
            ),
        },
        {"role": "user", "content": rendered_prompt},
    ]
    if repair_instruction:
        messages.append({"role": "user", "content": repair_instruction})
    response = _get_client().chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        **({"response_format": {"type": "json_object"}} if json_mode else {}),
        **({"seed": int(llm_seed)} if llm_seed is not None else {}),
    )
    return {
        "raw_response": _extract_content(response),
        "finish_reason": _response_finish_reason(response),
        "resource_usage": {
            **extract_token_usage(response),
            "paper_seconds": time.perf_counter() - started,
        },
    }


def _invalid_state_assessment_paths(
    *,
    output_dir: Path,
    persona_id: str,
    attempt: int,
    error_type: str,
) -> tuple[Path, Path]:
    safe_persona_id = "".join(
        character if character.isalnum() or character in "._-" else "_"
        for character in persona_id
    )
    attempt_label = f"attempt_{attempt}"
    raw_path = output_dir / f"state_assessment_{safe_persona_id}_{attempt_label}_raw_invalid.txt"
    metadata_path = output_dir / f"state_assessment_{safe_persona_id}_{attempt_label}_{error_type}.json"
    return raw_path, metadata_path


def _save_invalid_state_assessment(
    *,
    output_dir: Path,
    persona_id: str,
    day_index: int,
    attempt: int,
    raw_response: str,
    error: ValueError,
    error_type: str,
    finish_reason: str | None,
    max_tokens: int,
    model: str,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path, metadata_path = _invalid_state_assessment_paths(
        output_dir=output_dir,
        persona_id=persona_id,
        attempt=attempt,
        error_type=error_type,
    )
    raw_path.write_text(raw_response, encoding="utf-8")
    # Keep legacy parse-error filenames for existing tooling/tests while also
    # writing attempt-numbered files for robust diagnostics.
    if error_type == "parse_error":
        safe_persona_id = "".join(
            character if character.isalnum() or character in "._-" else "_"
            for character in persona_id
        )
        legacy_marker = "" if attempt == 1 else "_retry"
        legacy_raw_path = output_dir / f"state_assessment_{safe_persona_id}{legacy_marker}_raw_invalid.txt"
        legacy_metadata_path = output_dir / f"state_assessment_{safe_persona_id}{legacy_marker}_parse_error.json"
        legacy_raw_path.write_text(raw_response, encoding="utf-8")
    else:
        legacy_metadata_path = None
    decode_error = error.__cause__
    metadata = {
        "persona_id": persona_id,
        "day_index": day_index,
        "attempt": attempt,
        "error_type": error_type,
        "error_message": str(error),
        "parse_error_message": str(error) if error_type == "parse_error" else None,
        "line_number": getattr(decode_error, "lineno", None),
        "column_number": getattr(decode_error, "colno", None),
        "character_position": getattr(decode_error, "pos", None),
        "finish_reason": finish_reason,
        "response_length": len(raw_response),
        "max_tokens": max_tokens,
        "state_assessment_max_tokens": max_tokens,
        "model": model,
        "model_name": model,
        "raw_response_path": str(raw_path),
        "raw_invalid_output_path": str(raw_path),
    }
    metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    metadata_path.write_text(metadata_json, encoding="utf-8")
    if legacy_metadata_path is not None:
        legacy_metadata = dict(metadata)
        legacy_metadata["raw_response_path"] = str(legacy_raw_path)
        legacy_metadata["raw_invalid_output_path"] = str(legacy_raw_path)
        legacy_metadata_path.write_text(
            json.dumps(legacy_metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return raw_path, metadata_path


def _is_item_cardinality_error(error: ValueError) -> bool:
    message = str(error)
    return ".items must contain exactly" in message


def _payload_with_conservative_null_items(payload: Mapping[str, Any]) -> dict[str, Any]:
    patched = deepcopy(payload)
    item_scores = patched.get("item_scores")
    if not isinstance(item_scores, Mapping):
        raise ValueError("Cannot apply item-cardinality fallback without item_scores object.")
    patched_scores = dict(item_scores)
    for construct in ACTIVE_CONSTRUCTS:
        construct_payload = patched_scores.get(construct)
        if not isinstance(construct_payload, Mapping):
            continue
        existing_items = construct_payload.get("items")
        if not isinstance(existing_items, list):
            continue
        expected_count = CONSTRUCT_ITEM_COUNTS[construct]
        if len(existing_items) >= expected_count:
            continue
        low, high = BACKEND_CONSTRUCT_RANGES[construct]
        expected_range = f"{low:g}-{high:g}"
        padded_items = list(existing_items)
        for index in range(len(padded_items) + 1, expected_count + 1):
            padded_items.append(
                {
                    "question_id": f"{construct}_q{index}",
                    "score": None,
                    "range": expected_range,
                    "evidence_spans": [],
                    "reasoning_short": "",
                }
            )
        updated_construct_payload = dict(construct_payload)
        updated_construct_payload["items"] = padded_items
        patched_scores[construct] = updated_construct_payload
    patched["item_scores"] = patched_scores
    return patched

def run_state_assessment(
    *,
    persona_id: str,
    day_index: int,
    previous_normalized_values: Mapping[str, Any],
    current_simulated_diary_entry: str,
    previous_diary_entries: Sequence[Mapping[str, Any]],
    previous_diary_entries_total_available_count: int | None = None,
    current_decision_label: str | None = None,
    was_physical_activity_planned_today: bool | None = None,
    planned_physical_activity_summary: Mapping[str, Any] | None = None,
    previous_diary_entries_summary: str | None = None,
    prompt_template: str | None = None,
    dry_run: bool = False,
    model: str = DEFAULT_MODEL_NAME,
    temperature: float = 0,
    top_p: float = 1,
    llm_seed: int | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    output_dir: Path | None = None,
    json_mode: bool = False,
) -> dict[str, Any]:
    template = prompt_template if prompt_template is not None else load_state_assessment_prompt()
    # The caller is responsible for applying the rolling diary-history window.
    # For backward compatibility, previous_diary_entries_count below means the
    # number of previous entries actually passed to LLM3, not the full retained
    # internal diary history.
    diary_context_entries = [dict(entry) for entry in previous_diary_entries]
    context_count = len(diary_context_entries)
    total_available_count = (
        context_count
        if previous_diary_entries_total_available_count is None
        else int(previous_diary_entries_total_available_count)
    )
    rendered_prompt = render_state_assessment_prompt(
        template,
        persona_id=persona_id,
        day_index=day_index,
        previous_psychological_construct_values=previous_normalized_values,
        current_simulated_diary_entry=current_simulated_diary_entry,
        previous_diary_entries=diary_context_entries,
        current_decision_label=current_decision_label,
        was_physical_activity_planned_today=was_physical_activity_planned_today,
        planned_physical_activity_summary=planned_physical_activity_summary,
        previous_diary_entries_summary=previous_diary_entries_summary,
    )
    fallback_used = False
    fallback_reason: str | None = None
    attempt_count = 1
    if dry_run:
        raw_payload = build_dry_run_state_assessment(
            persona_id=persona_id,
            day_index=day_index,
            previous_normalized_values=previous_normalized_values,
        )
        validated = validate_state_assessment_output(
            raw_payload,
            expected_persona_id=persona_id,
            expected_day_index=day_index,
        )
        resource_usage = {
            "prompt_tokens": 0,
            "response_tokens": 0,
            "tokens_total": 0,
            "token_source": "dry_run",
            "paper_seconds": 0.0,
        }
        mode = "dry_run_mock"
    else:
        invalid_output_dir = output_dir or SIMULATION_DIR / "output"
        last_error: ValueError | None = None
        last_payload: dict[str, Any] | None = None
        last_resource_usage: Mapping[str, Any] = {}
        for attempt_index in range(2):
            attempt_count = attempt_index + 1
            attempt_max_tokens = max_tokens if attempt_index == 0 else max(max_tokens, RETRY_MIN_MAX_TOKENS)
            llm_result = call_state_assessment_llm(
                rendered_prompt,
                model=model,
                temperature=temperature,
                top_p=top_p,
                llm_seed=llm_seed,
                max_tokens=attempt_max_tokens,
                repair_instruction=JSON_REPAIR_INSTRUCTION if attempt_index else None,
                json_mode=json_mode,
            )
            last_resource_usage = llm_result["resource_usage"]
            try:
                raw_payload = parse_state_assessment_json(llm_result["raw_response"])
                last_payload = raw_payload
                validated = validate_state_assessment_output(
                    raw_payload,
                    expected_persona_id=persona_id,
                    expected_day_index=day_index,
                )
                resource_usage = last_resource_usage
                break
            except ValueError as exc:
                last_error = exc
                error_type = "parse_error" if exc.__cause__ is not None else "schema_validation_error"
                _save_invalid_state_assessment(
                    output_dir=invalid_output_dir,
                    persona_id=persona_id,
                    day_index=day_index,
                    attempt=attempt_count,
                    raw_response=llm_result["raw_response"],
                    error=exc,
                    error_type=error_type,
                    finish_reason=llm_result["finish_reason"],
                    max_tokens=attempt_max_tokens,
                    model=model,
                )
        else:
            if last_error is not None and _is_item_cardinality_error(last_error) and last_payload is not None:
                fallback_reason = str(last_error)
                fallback_payload = _payload_with_conservative_null_items(last_payload)
                validated = validate_state_assessment_output(
                    fallback_payload,
                    expected_persona_id=persona_id,
                    expected_day_index=day_index,
                )
                fallback_used = True
                resource_usage = last_resource_usage
            elif last_error is not None:
                raise last_error
            else:
                raise RuntimeError("State Assessment retry loop ended without a result.")
        mode = "llm"
    target_normalized = normalize_mean_scores(
        validated["mean_scores_raw"],
        previous_normalized_values,
    )
    visible_targets: dict[str, float | None] = {
        construct: (
            None
            if validated["mean_scores_raw"][construct] is None
            else target_normalized[construct]
        )
        for construct in ACTIVE_CONSTRUCTS
    }
    update = apply_smoothed_bounded_construct_update(
        previous_normalized_values,
        visible_targets,
        validated["mean_scores_raw"],
    )
    return {
        "state_assessment_enabled": True,
        "state_assessment_mode": mode,
        "state_assessment_item_scores": validated["item_scores"],
        "state_assessment_mean_scores_raw": validated["mean_scores_raw"],
        "state_assessment_mean_scores_normalized": target_normalized,
        "state_assessment_target_values_normalized": visible_targets,
        "psychological_construct_values_before_state_assessment": dict(
            previous_normalized_values
        ),
        "psychological_construct_update_strategy": "smoothed_bounded",
        "psychological_construct_update_alpha": PSYCHOLOGICAL_CONSTRUCT_UPDATE_ALPHA,
        "psychological_construct_update_max_daily_change": (
            PSYCHOLOGICAL_CONSTRUCT_UPDATE_MAX_DAILY_CHANGE
        ),
        "psychological_construct_update_delta_proposed": update["delta_proposed"],
        "psychological_construct_update_delta_applied": update["delta_applied"],
        "psychological_construct_values_after_smoothed_update": update["updated_values"],
        "psychological_construct_values_after_state_assessment": update["updated_values"],
        "previous_diary_entries_total_available_count": total_available_count,
        "previous_diary_entries_context_count": context_count,
        "previous_diary_entries_count": context_count,
        "previous_diary_entries_count_semantics": "entries_actually_passed_to_llm3",
        "previous_diary_entries_context_used": diary_context_entries,
        "previous_diary_entries_context_strategy": PREVIOUS_DIARY_CONTEXT_STRATEGY,
        "state_assessment_fallback_used": fallback_used,
        "state_assessment_fallback_reason": fallback_reason,
        "state_assessment_attempt_count": attempt_count,
        "rendered_prompt": rendered_prompt,
        "_resource_usage": resource_usage,
    }
