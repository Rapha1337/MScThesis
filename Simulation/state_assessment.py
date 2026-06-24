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



AUTOMATICITY_PRIOR_SIMILAR_EPISODES_REQUIRED = 2
FORBIDDEN_LLM3_EVIDENCE_FIELDS = frozenset({
    "direction", "strength", "evidence_strength", "deterministic_target_offset",
    "delta", "update_amount", "fixed_offset", "offset", "item_scores", "items",
    "scale_mean", "mean_score",
})


def _no_evidence() -> dict[str, Any]:
    return {
        "evidence_present": False,
        "target_value_normalized": None,
        "evidence_span": None,
        "reasoning_short": "",
    }


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


def _find_forbidden_numeric_assessment_keys(value: Any, path: str = "") -> list[str]:
    forbidden = {
        "item_scores", "items", "mean_score", "mean_scores", "mean_scores_raw",
        "mean_scores_normalized", "target_values", "construct_updates", "updates",
        "score", "raw_scale_construct_means", "normalized_construct_targets",
        "evidence_strength", "deterministic_target_offset",
        "delta", "update_amount", "fixed_offset", "offset", "scale_mean",
    }
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            child = f"{path}.{key}" if path else str(key)
            if str(key) in forbidden:
                found.append(child)
            found.extend(_find_forbidden_numeric_assessment_keys(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_find_forbidden_numeric_assessment_keys(item, f"{path}[{index}]"))
    return found


def _span_has_construct_support(construct: str, span: str) -> bool:
    text = span.lower()
    checks = {
        "automaticity": ["without thinking", "automatically", "as usual", "routine", "like every", "found myself"],
        "pa_specific_self_control": ["wanted to stay", "temptation", "resisted", "overcome", "overcame", "wanted to skip", "but went", "but I went".lower()],
        "action_planning": ["planned", "plan", "packed", "prepared", "at ", "after work", "in the morning", "where", "when", "how"],
        "intention": ["determined", "decided", "intended", "committed", "would go", "would exercise", "was going to"],
        "perceived_behavioral_control": ["capable", "able to", "under my control", "beyond my control", "not feel capable", "could manage", "could not manage"],
        "attitude_toward_the_behavior": ["worthwhile", "beneficial", "pleasant", "unpleasant", "boring", "valuable", "harmful", "good for me"],
        "subjective_norm": ["encouraged", "expected me", "pressure", "pressured", "approved", "disapproved", "training partner"],
        "intrinsic_motivation": ["enjoyed", "fun", "pleasure", "interesting", "satisfying", "liked"],
        "motivational_competence": ["motivate myself", "motivation", "get started effectively", "mobilize myself", "managed to get started"],
    }
    return any(marker in text for marker in checks[construct])


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
    forbidden_keys = _find_forbidden_numeric_assessment_keys(payload)
    if forbidden_keys:
        raise ValueError(f"State Assessment returned forbidden scoring/target keys: {forbidden_keys}.")
    if payload.get("persona_id") != expected_persona_id:
        raise ValueError("State Assessment persona_id does not match the request.")
    day_index = payload.get("day_index")
    if isinstance(day_index, bool) or not isinstance(day_index, int) or day_index != expected_day_index:
        raise ValueError("State Assessment day_index does not match the request.")

    evidence_root = payload.get("construct_evidence")
    if not isinstance(evidence_root, Mapping):
        raise ValueError("State Assessment construct_evidence must be an object.")

    accepted: dict[str, Any] = {}
    rejected: dict[str, list[dict[str, Any]]] = {construct: [] for construct in ACTIVE_CONSTRUCTS}
    validation_errors: list[dict[str, Any]] = []
    span_to_constructs: dict[str, list[str]] = {}

    for construct in ACTIVE_CONSTRUCTS:
        raw = evidence_root.get(construct)
        if not isinstance(raw, Mapping):
            accepted[construct] = _no_evidence()
            rejected[construct].append({"reason": "missing_or_non_object", "raw": raw})
            continue
        present = raw.get("evidence_present")
        target = raw.get("target_value_normalized")
        span = raw.get("evidence_span")
        reasoning = raw.get("reasoning_short")
        reasons: list[str] = []
        forbidden_present = sorted(str(k) for k in raw if str(k) in FORBIDDEN_LLM3_EVIDENCE_FIELDS)
        if forbidden_present:
            reasons.append("forbidden_evidence_fields:" + ",".join(forbidden_present))
        if not isinstance(present, bool):
            reasons.append("evidence_present_not_boolean")
        if present is False:
            if target is not None or span is not None or reasoning != "":
                reasons.append("absent_evidence_must_use_null_span_target_and_empty_reasoning")
        elif present is True:
            if isinstance(target, bool) or not isinstance(target, (int, float)) or not 0 <= float(target) <= 1:
                reasons.append("target_value_normalized_not_in_0_1")
            if not isinstance(span, str) or not span or span not in current_simulated_diary_entry:
                reasons.append("span_not_exact_current_diary_substring")
            elif not _span_has_construct_support(construct, span):
                reasons.append("span_lacks_construct_specific_support")
            if not isinstance(reasoning, str) or not reasoning.strip():
                reasons.append("missing_reasoning")
        else:
            reasons.append("invalid_evidence_present")
        if reasons:
            accepted[construct] = _no_evidence()
            rejected[construct].append({"reason": ";".join(reasons), "raw": dict(raw)})
            validation_errors.append({"construct": construct, "reason": ";".join(reasons)})
            continue
        if present:
            entry = {
                "evidence_present": True,
                "target_value_normalized": float(target),
                "evidence_span": span,
                "reasoning_short": reasoning.strip(),
            }
            accepted[construct] = entry
            span_to_constructs.setdefault(span, []).append(construct)  # type: ignore[arg-type]
        else:
            accepted[construct] = _no_evidence()

    duplicate_conflicts: list[dict[str, Any]] = []
    for span, constructs in span_to_constructs.items():
        if len(constructs) < 2:
            continue
        reasonings = [accepted[c]["reasoning_short"].strip().lower() for c in constructs]
        has_distinct_explanations = len(set(reasonings)) == len(reasonings) and all(len(r) >= 12 for r in reasonings)
        has_distinct_clauses = any(marker in span.lower() for marker in [" but ", " and ", ";", ","])
        all_constructs_supported = all(_span_has_construct_support(c, span) for c in constructs)
        if not (has_distinct_explanations and has_distinct_clauses and all_constructs_supported):
            conflict = {"evidence_span": span, "constructs": constructs, "reason": "ambiguous_duplicate_span"}
            duplicate_conflicts.append(conflict)
            for construct in constructs:
                rejected[construct].append({"reason": "ambiguous_duplicate_span", "raw": accepted[construct]})
                accepted[construct] = _no_evidence()

    return {
        "persona_id": expected_persona_id,
        "day_index": expected_day_index,
        "accepted_evidence": accepted,
        "rejected_evidence": rejected,
        "rejection_reasons": validation_errors,
        "duplicate_span_conflicts": duplicate_conflicts,
    }


def _extract_diary_text(entry: Mapping[str, Any]) -> str:
    text = entry.get("diary_entry") or entry.get("current_simulated_diary_entry") or ""
    return str(text)


def _matching_prior_automaticity_occurrences(previous_diary_entries: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [entry for entry in previous_diary_entries if _span_has_construct_support("automaticity", _extract_diary_text(entry))]

def evidence_to_deterministic_construct_update(
    previous_values: Mapping[str, float],
    accepted_evidence: Mapping[str, Mapping[str, Any]],
    *,
    previous_diary_entries: Sequence[Mapping[str, Any]] = (),
    current_decision_label: str | None = None,
    was_physical_activity_planned_today: bool | None = None,
    planned_physical_activity_summary: Mapping[str, Any] | None = None,
    alpha: float = PSYCHOLOGICAL_CONSTRUCT_UPDATE_ALPHA,
    max_daily_change: float = PSYCHOLOGICAL_CONSTRUCT_UPDATE_MAX_DAILY_CHANGE,
    automaticity_prior_threshold: int = AUTOMATICITY_PRIOR_SIMILAR_EPISODES_REQUIRED,
) -> dict[str, Any]:
    del current_decision_label, was_physical_activity_planned_today, planned_physical_activity_summary
    targets: dict[str, float | None] = {}
    proposed: dict[str, float] = {}
    applied: dict[str, float] = {}
    updated: dict[str, float] = {}
    details: dict[str, Any] = {}
    prior_matches = _matching_prior_automaticity_occurrences(previous_diary_entries)

    current_auto = accepted_evidence.get("automaticity", _no_evidence())
    auto_gate_passed = bool(current_auto.get("evidence_present")) and len(prior_matches) >= automaticity_prior_threshold

    for construct in ACTIVE_CONSTRUCTS:
        current = float(previous_values[construct])
        ev = accepted_evidence.get(construct, _no_evidence())
        effective_target = ev.get("target_value_normalized") if ev.get("evidence_present") else None
        if construct == "automaticity" and ev.get("evidence_present") and not auto_gate_passed:
            effective_target = None
        if effective_target is None or isinstance(effective_target, bool) or not isinstance(effective_target, (int, float)) or not 0 <= float(effective_target) <= 1:
            target = None
            proposed_delta = 0.0
            applied_delta = 0.0
        else:
            target = float(effective_target)
            proposed_delta = alpha * (target - current)
            applied_delta = max(-max_daily_change, min(max_daily_change, proposed_delta))
        targets[construct] = target
        proposed[construct] = proposed_delta
        applied[construct] = applied_delta
        updated[construct] = min(1.0, max(0.0, current + applied_delta))
        details[construct] = {
            "current_value": current,
            "target_value_normalized": target,
            "proposed_delta": proposed_delta,
            "applied_delta": applied_delta,
            "updated_value": updated[construct],
        }
    gate = {
        "current_automaticity_evidence_span": current_auto.get("evidence_span") if current_auto.get("evidence_present") else None,
        "qualifying_previous_diary_evidence_spans": [_extract_diary_text(entry) for entry in prior_matches],
        "qualifying_prior_occurrences": len(prior_matches),
        "repetition_threshold_prior_occurrences": automaticity_prior_threshold,
        "automaticity_update_gate_passed": auto_gate_passed,
        "gate_basis": "diary_only_explicit_routine_or_automaticity_wording",
    }
    return {"targets_normalized": targets, "delta_proposed": proposed, "delta_applied": applied, "updated_values": updated, "details": details, "automaticity_repetition_gate": gate}

def build_dry_run_state_assessment(*, persona_id: str, day_index: int, previous_normalized_values: Mapping[str, Any]) -> dict[str, Any]:
    return {"persona_id": persona_id, "day_index": day_index, "construct_evidence": {construct: _no_evidence() for construct in ACTIVE_CONSTRUCTS}, "metadata": {"mode": "dry_run_mock"}}

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

    validated = validate_state_assessment_output(
        raw_payload,
        expected_persona_id=persona_id,
        expected_day_index=day_index,
        current_simulated_diary_entry=current_simulated_diary_entry,
    )
    update = evidence_to_deterministic_construct_update(
        previous_normalized_values,
        validated["accepted_evidence"],
        previous_diary_entries=previous_diary_entries,
        current_decision_label=current_decision_label,
        was_physical_activity_planned_today=was_physical_activity_planned_today,
        planned_physical_activity_summary=planned_physical_activity_summary,
    )
    visible_targets = update["targets_normalized"]
    return {
        "state_assessment_enabled": True,
        "state_assessment_mode": mode,
        "state_assessment_construct_evidence": validated["accepted_evidence"],
        "state_assessment_validation": {
            "accepted_evidence": validated["accepted_evidence"],
            "rejected_evidence": validated["rejected_evidence"],
            "rejection_reasons": validated["rejection_reasons"],
            "duplicate_span_conflicts": validated["duplicate_span_conflicts"],
        },
        "state_assessment_target_values_normalized": visible_targets,
        "psychological_construct_values_before_state_assessment": dict(
            previous_normalized_values
        ),
        "psychological_construct_update_strategy": "continuous_target_smoothed_bounded",
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
