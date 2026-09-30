from __future__ import annotations

import math
import random
from typing import Any, Mapping

DECISION_SAMPLING_SEED_OFFSET = 20_000_033

EXPECTED_CONTEXTUAL_FIELDS = frozenset(
    {
        "persona_id",
        "day_index",
        "contextual_pa_probability",
        "activity_if_performed",
        "no_activity_if_skipped",
    }
)
EXPECTED_ACTIVITY_BRANCH_FIELDS = frozenset(
    {"duration_min", "rationale_short", "diary_entry"}
)
EXPECTED_SKIP_BRANCH_FIELDS = frozenset({"rationale_short", "diary_entry"})


def _non_empty_string(mapping: Mapping[str, Any], field: str) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string.")
    return value.strip()


def validate_contextual_assessment(
    payload: Mapping[str, Any],
    *,
    expected_persona_id: str,
    expected_day_index: int,
) -> dict[str, Any]:
    """Validate LLM2's contextual probability assessment before sampling."""
    actual_fields = set(payload)
    if actual_fields != EXPECTED_CONTEXTUAL_FIELDS:
        missing = sorted(EXPECTED_CONTEXTUAL_FIELDS - actual_fields)
        extra = sorted(actual_fields - EXPECTED_CONTEXTUAL_FIELDS)
        raise ValueError(
            f"Empirical v1.2 contextual fields mismatch. Missing: {missing}; extra: {extra}."
        )

    persona_id = _non_empty_string(payload, "persona_id")
    if persona_id != expected_persona_id:
        raise ValueError(
            f"persona_id must match input persona_id {expected_persona_id!r}; got {persona_id!r}."
        )

    day_index = payload["day_index"]
    if isinstance(day_index, bool) or not isinstance(day_index, int):
        raise ValueError("day_index must be an integer.")
    if int(day_index) != int(expected_day_index):
        raise ValueError(
            f"day_index must match input day_index {expected_day_index}; got {day_index}."
        )

    raw_probability = payload["contextual_pa_probability"]
    if isinstance(raw_probability, bool) or not isinstance(raw_probability, (int, float)):
        raise ValueError("contextual_pa_probability must be numeric.")
    probability = float(raw_probability)
    if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
        raise ValueError("contextual_pa_probability must be finite and within [0, 1].")

    activity = payload["activity_if_performed"]
    if not isinstance(activity, Mapping):
        raise ValueError("activity_if_performed must be an object.")
    if set(activity) != EXPECTED_ACTIVITY_BRANCH_FIELDS:
        missing = sorted(EXPECTED_ACTIVITY_BRANCH_FIELDS - set(activity))
        extra = sorted(set(activity) - EXPECTED_ACTIVITY_BRANCH_FIELDS)
        raise ValueError(
            f"activity_if_performed fields mismatch. Missing: {missing}; extra: {extra}."
        )

    raw_duration = activity["duration_min"]
    if isinstance(raw_duration, bool) or not isinstance(raw_duration, (int, float)):
        raise ValueError("activity_if_performed.duration_min must be numeric.")
    duration_float = float(raw_duration)
    if not math.isfinite(duration_float) or not duration_float.is_integer():
        raise ValueError("activity_if_performed.duration_min must be a finite whole number.")
    duration_min = int(duration_float)
    if not 1 <= duration_min <= 240:
        raise ValueError("activity_if_performed.duration_min must be between 1 and 240.")

    activity_rationale = _non_empty_string(activity, "rationale_short")
    activity_diary = _non_empty_string(activity, "diary_entry")

    skipped = payload["no_activity_if_skipped"]
    if not isinstance(skipped, Mapping):
        raise ValueError("no_activity_if_skipped must be an object.")
    if set(skipped) != EXPECTED_SKIP_BRANCH_FIELDS:
        missing = sorted(EXPECTED_SKIP_BRANCH_FIELDS - set(skipped))
        extra = sorted(set(skipped) - EXPECTED_SKIP_BRANCH_FIELDS)
        raise ValueError(
            f"no_activity_if_skipped fields mismatch. Missing: {missing}; extra: {extra}."
        )

    return {
        "persona_id": persona_id,
        "day_index": int(day_index),
        "contextual_pa_probability": probability,
        "activity_if_performed": {
            "duration_min": duration_min,
            "rationale_short": activity_rationale,
            "diary_entry": activity_diary,
        },
        "no_activity_if_skipped": {
            "rationale_short": _non_empty_string(skipped, "rationale_short"),
            "diary_entry": _non_empty_string(skipped, "diary_entry"),
        },
    }


def sampling_seed(pa_decision_input: Mapping[str, Any]) -> int:
    """Return a deterministic per-persona/day sampling seed."""
    daily_context = pa_decision_input.get("daily_context")
    if not isinstance(daily_context, Mapping):
        raise ValueError("Empirical v1.2 sampling requires daily_context.")
    seed = daily_context.get("seed")
    day_index = pa_decision_input.get("day_index")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("daily_context must contain seed as an integer for v1.2 sampling.")
    if isinstance(day_index, bool) or not isinstance(day_index, int):
        raise ValueError("pa_decision_input must contain day_index as an integer.")
    return int(seed) + DECISION_SAMPLING_SEED_OFFSET + int(day_index)


def sample_final_decision(
    assessment: Mapping[str, Any],
    *,
    pa_decision_input: Mapping[str, Any],
) -> dict[str, Any]:
    """Sample a reproducible final binary PA outcome from contextual probability."""
    persona_id = str(pa_decision_input["persona_id"])
    day_index = int(pa_decision_input["day_index"])
    validated = validate_contextual_assessment(
        assessment,
        expected_persona_id=persona_id,
        expected_day_index=day_index,
    )
    probability = float(validated["contextual_pa_probability"])
    seed = sampling_seed(pa_decision_input)
    random_value = random.Random(seed).random()
    performed = random_value < probability

    if performed:
        branch = validated["activity_if_performed"]
        decision = {
            "persona_id": persona_id,
            "day_index": day_index,
            "decision_code": 3,
            "decision_label": "extra_activity",
            "duration_min": int(branch["duration_min"]),
            "rationale_short": str(branch["rationale_short"]),
            "diary_entry": str(branch["diary_entry"]),
        }
        sampled_probability = probability
    else:
        branch = validated["no_activity_if_skipped"]
        decision = {
            "persona_id": persona_id,
            "day_index": day_index,
            "decision_code": 0,
            "decision_label": "skip_activity",
            "duration_min": 0,
            "rationale_short": str(branch["rationale_short"]),
            "diary_entry": str(branch["diary_entry"]),
        }
        sampled_probability = 1.0 - probability

    prior = float(pa_decision_input.get("behavior_policy", {}).get("extra_activity", 0.0))
    return {
        **decision,
        "contextual_pa_probability": probability,
        "behavior_policy_pa_prior": prior,
        "decision_sampling_seed": seed,
        "decision_sampling_random_value": random_value,
        "sampled_decision_label": decision["decision_label"],
        "sampled_decision_probability": sampled_probability,
        "llm2_contextual_assessment": validated,
    }
