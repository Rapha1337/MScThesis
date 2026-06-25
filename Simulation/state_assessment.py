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
JSON_REPAIR_INSTRUCTION = (
    "Your previous response was malformed. Return only one complete valid JSON object "
    "parseable by Python json.loads. All property names must be enclosed in double quotes. "
    "Do not use markdown, comments, trailing commas, ellipses, or unquoted keys."
)
PSYCHOLOGICAL_CONSTRUCT_UPDATE_ALPHA = 0.10
PSYCHOLOGICAL_CONSTRUCT_UPDATE_MAX_DAILY_CHANGE = 0.05

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



AUTOMATICITY_PRIOR_SIMILAR_EPISODES_REQUIRED = 2


def _no_item_assessment() -> dict[str, Any]:
    return {
        "items": [],
        "mean_score": None,
    }


def _scale_range(construct: str) -> tuple[float, float]:
    low, high = BACKEND_CONSTRUCT_RANGES[construct]
    return float(low), float(high)


def normalize_construct_scale_score(construct: str, score: Any) -> float | None:
    """Normalize an original questionnaire scale score to [0, 1]."""
    if score is None or isinstance(score, bool) or not isinstance(score, (int, float)):
        return None
    low, high = _scale_range(construct)
    numeric = float(score)
    if numeric < low or numeric > high:
        return None
    return (numeric - low) / (high - low)


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


def _item_scores_for_construct(raw: Any) -> tuple[list[Mapping[str, Any]], float | None, list[str]]:
    reasons: list[str] = []
    if not isinstance(raw, Mapping):
        return [], None, ["missing_or_non_object"]
    items = raw.get("items")
    if not isinstance(items, list):
        reasons.append("items_not_array")
        items = []
    mean = raw.get("mean_score")
    if mean is not None and (isinstance(mean, bool) or not isinstance(mean, (int, float))):
        reasons.append("mean_score_not_number_or_null")
        mean = None
    return [item for item in items if isinstance(item, Mapping)], (float(mean) if mean is not None else None), reasons


def validate_state_assessment_output(
    payload: Mapping[str, Any],
    *,
    expected_persona_id: str,
    expected_day_index: int,
    current_simulated_diary_entry: str,
) -> dict[str, Any]:
    removed_anywhere = sorted(_find_removed_construct_keys(payload))
    if removed_anywhere:
        raise ValueError(f"State Assessment contains removed construct keys: {removed_anywhere}.")
    if payload.get("persona_id") != expected_persona_id:
        raise ValueError("State Assessment persona_id does not match the request.")
    day_index = payload.get("day_index")
    if isinstance(day_index, bool) or not isinstance(day_index, int) or day_index != expected_day_index:
        raise ValueError("State Assessment day_index does not match the request.")

    item_scores_root = payload.get("item_scores")
    if not isinstance(item_scores_root, Mapping):
        raise ValueError("State Assessment item_scores must be an object.")

    accepted: dict[str, Any] = {}
    rejected: dict[str, list[dict[str, Any]]] = {construct: [] for construct in ACTIVE_CONSTRUCTS}
    validation_errors: list[dict[str, Any]] = []

    for construct in ACTIVE_CONSTRUCTS:
        raw = item_scores_root.get(construct)
        items, mean_score, reasons = _item_scores_for_construct(raw)
        low, high = _scale_range(construct)
        expected_count = CONSTRUCT_ITEM_COUNTS[construct]
        valid_item_scores: list[float] = []
        sanitized_items: list[dict[str, Any]] = []

        if len(items) != expected_count:
            reasons.append(f"item_count_not_{expected_count}")
        for index, item in enumerate(items):
            score = item.get("score")
            spans = item.get("evidence_spans")
            reasoning = item.get("reasoning_short")
            item_reasons: list[str] = []
            if score is None:
                pass
            elif isinstance(score, bool) or not isinstance(score, (int, float)) or not low <= float(score) <= high:
                item_reasons.append("score_outside_original_scale_or_bad_type")
            else:
                valid_item_scores.append(float(score))
            if not isinstance(spans, list) or any(not isinstance(span, str) or span not in current_simulated_diary_entry for span in spans):
                item_reasons.append("evidence_spans_must_be_current_diary_substrings")
            if score is None and spans not in ([], None):
                item_reasons.append("null_score_requires_empty_evidence_spans")
            if score is not None and (not isinstance(reasoning, str) or not reasoning.strip()):
                item_reasons.append("scored_item_requires_reasoning")
            sanitized_items.append({
                "question_id": item.get("question_id") or f"{construct}_q{index + 1}",
                "score": (float(score) if isinstance(score, (int, float)) and not isinstance(score, bool) else None),
                "range": item.get("range") or f"{low:g}-{high:g}",
                "evidence_spans": spans if isinstance(spans, list) else [],
                "reasoning_short": reasoning.strip() if isinstance(reasoning, str) else "",
            })
            reasons.extend(item_reasons)

        calculated_mean = (sum(valid_item_scores) / len(valid_item_scores)) if valid_item_scores else None
        if mean_score is not None and (mean_score < low or mean_score > high):
            reasons.append("mean_score_outside_original_scale")
        if mean_score is not None and calculated_mean is not None and abs(mean_score - calculated_mean) > 0.05:
            reasons.append("mean_score_does_not_match_item_scores")
        effective_mean = mean_score if mean_score is not None else calculated_mean
        normalized = normalize_construct_scale_score(construct, effective_mean)
        if reasons or normalized is None:
            accepted[construct] = _no_item_assessment()
            rejected[construct].append({"reason": ";".join(reasons or ["null_or_malformed_assessment"]), "raw": raw})
            validation_errors.append({"construct": construct, "reason": ";".join(reasons or ["null_or_malformed_assessment"])})
        else:
            accepted[construct] = {"items": sanitized_items, "mean_score": effective_mean}

    return {
        "persona_id": expected_persona_id,
        "day_index": expected_day_index,
        "accepted_item_scores": accepted,
        "rejected_item_scores": rejected,
        "rejection_reasons": validation_errors,
    }


def _extract_diary_text(entry: Mapping[str, Any]) -> str:
    text = entry.get("diary_entry") or entry.get("current_simulated_diary_entry") or ""
    return str(text)


def _matching_prior_automaticity_occurrences(previous_diary_entries: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    text_markers = ["without thinking", "automatically", "as usual", "routine", "habit"]
    return [entry for entry in previous_diary_entries if any(marker in _extract_diary_text(entry).lower() for marker in text_markers)]


def item_assessment_to_smoothed_construct_update(
    previous_values: Mapping[str, float],
    accepted_item_scores: Mapping[str, Mapping[str, Any]],
    *,
    previous_diary_entries: Sequence[Mapping[str, Any]] = (),
    alpha: float = PSYCHOLOGICAL_CONSTRUCT_UPDATE_ALPHA,
    max_daily_change: float = PSYCHOLOGICAL_CONSTRUCT_UPDATE_MAX_DAILY_CHANGE,
    automaticity_prior_threshold: int = AUTOMATICITY_PRIOR_SIMILAR_EPISODES_REQUIRED,
) -> dict[str, Any]:
    targets: dict[str, float | None] = {}
    proposed: dict[str, float] = {}
    applied: dict[str, float] = {}
    updated: dict[str, float] = {}
    details: dict[str, Any] = {}
    raw_assessment: dict[str, Any] = {}
    scale_means: dict[str, float | None] = {}
    prior_matches = _matching_prior_automaticity_occurrences(previous_diary_entries)

    for construct in ACTIVE_CONSTRUCTS:
        current = float(previous_values[construct])
        assessment = accepted_item_scores.get(construct, _no_item_assessment())
        mean_score = assessment.get("mean_score")
        target = normalize_construct_scale_score(construct, mean_score)
        if construct == "automaticity" and target is not None and len(prior_matches) < automaticity_prior_threshold:
            target = None
        if target is None:
            proposed_delta = 0.0
            applied_delta = 0.0
        else:
            proposed_delta = alpha * (target - current)
            applied_delta = max(-max_daily_change, min(max_daily_change, proposed_delta))
        targets[construct] = target
        scale_means[construct] = mean_score if isinstance(mean_score, (int, float)) and not isinstance(mean_score, bool) else None
        proposed[construct] = proposed_delta
        applied[construct] = applied_delta
        updated[construct] = min(1.0, max(0.0, current + applied_delta))
        raw_assessment[construct] = assessment
        details[construct] = {
            "raw_llm3_item_or_scale_assessment": assessment,
            "construct_scale_mean": scale_means[construct],
            "normalized_target_value": target,
            "current_value": current,
            "proposed_delta": proposed_delta,
            "applied_delta": applied_delta,
            "updated_value": updated[construct],
        }
    gate = {
        "qualifying_previous_diary_evidence_spans": [_extract_diary_text(entry) for entry in prior_matches],
        "qualifying_prior_occurrences": len(prior_matches),
        "repetition_threshold_prior_occurrences": automaticity_prior_threshold,
        "automaticity_update_gate_passed": targets["automaticity"] is not None,
        "gate_basis": "diary_only_explicit_routine_or_automaticity_wording",
    }
    return {"raw_item_or_scale_assessment": raw_assessment, "scale_means": scale_means, "targets_normalized": targets, "delta_proposed": proposed, "delta_applied": applied, "updated_values": updated, "details": details, "automaticity_repetition_gate": gate}


def evidence_to_deterministic_construct_update(previous_values: Mapping[str, float], accepted_evidence: Mapping[str, Mapping[str, Any]], **kwargs: Any) -> dict[str, Any]:
    return item_assessment_to_smoothed_construct_update(previous_values, accepted_evidence, previous_diary_entries=kwargs.get("previous_diary_entries", ()))


def build_dry_run_state_assessment(*, persona_id: str, day_index: int, previous_normalized_values: Mapping[str, Any]) -> dict[str, Any]:
    return {"persona_id": persona_id, "day_index": day_index, "item_scores": {construct: _no_item_assessment() for construct in ACTIVE_CONSTRUCTS}, "metadata": {"mode": "dry_run_mock"}}

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


def _save_invalid_state_assessment(
    *,
    output_dir: Path,
    persona_id: str,
    day_index: int,
    raw_response: str,
    parse_error: ValueError,
    finish_reason: str | None,
    max_tokens: int,
    model: str,
    retry: bool,
) -> tuple[Path, Path]:
    safe_persona_id = "".join(
        character if character.isalnum() or character in "._-" else "_"
        for character in persona_id
    )
    marker = "_retry" if retry else ""
    raw_path = output_dir / f"state_assessment_{safe_persona_id}{marker}_raw_invalid.txt"
    metadata_path = output_dir / f"state_assessment_{safe_persona_id}{marker}_parse_error.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(raw_response, encoding="utf-8")
    decode_error = parse_error.__cause__
    metadata = {
        "persona_id": persona_id,
        "day_index": day_index,
        "parse_error_message": str(parse_error),
        "line_number": getattr(decode_error, "lineno", None),
        "column_number": getattr(decode_error, "colno", None),
        "character_position": getattr(decode_error, "pos", None),
        "finish_reason": finish_reason,
        "response_length": len(raw_response),
        "state_assessment_max_tokens": max_tokens,
        "model_name": model,
        "raw_invalid_output_path": str(raw_path),
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return raw_path, metadata_path


def run_state_assessment(
    *,
    persona_id: str,
    day_index: int,
    previous_normalized_values: Mapping[str, Any],
    current_simulated_diary_entry: str,
    previous_diary_entries: Sequence[Mapping[str, Any]],
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
    rendered_prompt = render_state_assessment_prompt(
        template,
        persona_id=persona_id,
        day_index=day_index,
        previous_psychological_construct_values=previous_normalized_values,
        current_simulated_diary_entry=current_simulated_diary_entry,
        previous_diary_entries=previous_diary_entries,
        current_decision_label=current_decision_label,
        was_physical_activity_planned_today=was_physical_activity_planned_today,
        planned_physical_activity_summary=planned_physical_activity_summary,
        previous_diary_entries_summary=previous_diary_entries_summary,
    )
    if dry_run:
        raw_payload = build_dry_run_state_assessment(
            persona_id=persona_id,
            day_index=day_index,
            previous_normalized_values=previous_normalized_values,
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
        for attempt in range(2):
            attempt_max_tokens = max_tokens if attempt == 0 else max(max_tokens, RETRY_MIN_MAX_TOKENS)
            llm_result = call_state_assessment_llm(
                rendered_prompt,
                model=model,
                temperature=temperature,
                top_p=top_p,
                llm_seed=llm_seed,
                max_tokens=attempt_max_tokens,
                repair_instruction=JSON_REPAIR_INSTRUCTION if attempt else None,
                json_mode=json_mode,
            )
            try:
                raw_payload = parse_state_assessment_json(llm_result["raw_response"])
                resource_usage = llm_result["resource_usage"]
                break
            except ValueError as exc:
                _save_invalid_state_assessment(
                    output_dir=invalid_output_dir,
                    persona_id=persona_id,
                    day_index=day_index,
                    raw_response=llm_result["raw_response"],
                    parse_error=exc,
                    finish_reason=llm_result["finish_reason"],
                    max_tokens=attempt_max_tokens,
                    model=model,
                    retry=bool(attempt),
                )
                if attempt == 1:
                    raise
        mode = "llm"

    try:
        validated = validate_state_assessment_output(
            raw_payload,
            expected_persona_id=persona_id,
            expected_day_index=day_index,
            current_simulated_diary_entry=current_simulated_diary_entry,
        )
    except ValueError as exc:
        validated = {
            "accepted_item_scores": {construct: _no_item_assessment() for construct in ACTIVE_CONSTRUCTS},
            "rejected_item_scores": {construct: [{"reason": "malformed_assessment_response", "raw": raw_payload}] for construct in ACTIVE_CONSTRUCTS},
            "rejection_reasons": [{"construct": "__response__", "reason": str(exc)}],
        }
    update = item_assessment_to_smoothed_construct_update(
        previous_normalized_values,
        validated["accepted_item_scores"],
        previous_diary_entries=previous_diary_entries,
    )
    visible_targets = update["targets_normalized"]
    return {
        "state_assessment_enabled": True,
        "state_assessment_mode": mode,
        "state_assessment_raw_item_or_scale_assessment": validated["accepted_item_scores"],
        "state_assessment_validation": {
            "accepted_item_scores": validated["accepted_item_scores"],
            "rejected_item_scores": validated["rejected_item_scores"],
            "rejection_reasons": validated["rejection_reasons"],
        },
        "state_assessment_target_values_normalized": visible_targets,
        "psychological_construct_values_before_state_assessment": dict(
            previous_normalized_values
        ),
        "state_assessment_construct_scale_means": update["scale_means"],
        "psychological_construct_update_strategy": "questionnaire_scale_target_smoothed_bounded",
        "psychological_construct_update_alpha": PSYCHOLOGICAL_CONSTRUCT_UPDATE_ALPHA,
        "psychological_construct_update_max_daily_change": (
            PSYCHOLOGICAL_CONSTRUCT_UPDATE_MAX_DAILY_CHANGE
        ),
        "psychological_construct_update_delta_proposed": update["delta_proposed"],
        "psychological_construct_update_delta_applied": update["delta_applied"],
        "psychological_construct_update_details": update["details"],
        "state_assessment_automaticity_repetition_gate": update["automaticity_repetition_gate"],
        "psychological_construct_values_after_state_assessment": update["updated_values"],
        "previous_diary_entries_count": len(previous_diary_entries),
        "previous_diary_entries_context_used": [dict(entry) for entry in previous_diary_entries],
        "previous_diary_entries_context_strategy": "all_previous_entries_for_run",
        "rendered_prompt": rendered_prompt,
        "_resource_usage": resource_usage,
    }
