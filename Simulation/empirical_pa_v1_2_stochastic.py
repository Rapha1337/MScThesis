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
    {"start_hour", "duration_min", "activity_option", "rationale_short", "diary_entry"}
)
EXPECTED_SKIP_BRANCH_FIELDS = frozenset({"rationale_short", "diary_entry"})
PA_OPTIONS = ("indoor_activity", "outdoor_activity")
NO_DOWNTIME_REASON = "no_downtime_block_available"
INVALID_TIME_ALLOCATION_REASON = "activity_does_not_fit_downtime_block"
NO_DOWNTIME_RATIONALE = (
    "Physical activity was not performed because the day contained no available "
    "downtime block for it."
)
NO_DOWNTIME_DIARY_ENTRY = (
    "Der Tagesplan enthielt heute kein freies Zeitfenster für zusätzliche "
    "körperliche Aktivität, deshalb fand keine PA statt."
)


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
    validated_activity: dict[str, Any] | None
    if activity is None:
        validated_activity = None
    else:
        if not isinstance(activity, Mapping):
            raise ValueError("activity_if_performed must be an object or null.")
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

        raw_start_hour = activity["start_hour"]
        if isinstance(raw_start_hour, bool) or not isinstance(raw_start_hour, (int, float)):
            raise ValueError("activity_if_performed.start_hour must be numeric.")
        start_hour_float = float(raw_start_hour)
        if not math.isfinite(start_hour_float) or not start_hour_float.is_integer():
            raise ValueError("activity_if_performed.start_hour must be a finite whole number.")
        start_hour = int(start_hour_float)
        if not 0 <= start_hour <= 23:
            raise ValueError("activity_if_performed.start_hour must be between 0 and 23.")

        activity_option = activity["activity_option"]
        if activity_option is not None and activity_option not in PA_OPTIONS:
            raise ValueError("activity_if_performed.activity_option must be indoor_activity, outdoor_activity, or null.")

        validated_activity = {
            "start_hour": start_hour,
            "duration_min": duration_min,
            "activity_option": activity_option,
            "rationale_short": _non_empty_string(activity, "rationale_short"),
            "diary_entry": _non_empty_string(activity, "diary_entry"),
        }

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
        "activity_if_performed": validated_activity,
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


def downtime_blocks(hourly_context_24h: Any) -> list[dict[str, int]]:
    """Return maximal contiguous downtime blocks as half-open hour ranges."""
    if not isinstance(hourly_context_24h, list) or len(hourly_context_24h) != 24:
        raise ValueError("daily_context.hourly_context_24h must contain exactly 24 entries.")

    hours: list[int] = []
    for index, entry in enumerate(hourly_context_24h):
        if not isinstance(entry, Mapping):
            raise ValueError(
                "daily_context.hourly_context_24h entries must be objects; "
                f"entry {index} is invalid."
            )
        hour = entry.get("hour")
        if isinstance(hour, bool) or not isinstance(hour, int):
            raise ValueError(
                "daily_context.hourly_context_24h entries must contain integer "
                f"hour values; entry {index} has {hour!r}."
            )
        hours.append(hour)

    expected_hours = list(range(24))
    duplicate_hours = sorted({hour for hour in hours if hours.count(hour) > 1})
    if duplicate_hours:
        raise ValueError(
            "daily_context.hourly_context_24h contains duplicate hour values: "
            f"{duplicate_hours}."
        )
    missing_hours = sorted(set(expected_hours) - set(hours))
    unexpected_hours = sorted(set(hours) - set(expected_hours))
    if missing_hours or unexpected_hours:
        raise ValueError(
            "daily_context.hourly_context_24h hour values must be exactly 0..23; "
            f"missing={missing_hours}, unexpected={unexpected_hours}."
        )
    if hours != expected_hours:
        raise ValueError(
            "daily_context.hourly_context_24h hour values must be in chronological "
            "order 0..23."
        )

    blocks: list[dict[str, int]] = []
    block_start: int | None = None
    for hour, entry in enumerate(hourly_context_24h):
        is_downtime = isinstance(entry, Mapping) and entry.get("activity_type") == "downtime"
        if is_downtime and block_start is None:
            block_start = hour
        elif not is_downtime and block_start is not None:
            blocks.append({
                "start_hour": block_start,
                "end_hour": hour,
                "duration_min": (hour - block_start) * 60,
            })
            block_start = None
    if block_start is not None:
        blocks.append({
            "start_hour": block_start,
            "end_hour": 24,
            "duration_min": (24 - block_start) * 60,
        })
    return blocks


def activity_fits_downtime_block(
    *,
    start_hour: int,
    duration_min: int,
    available_blocks: list[Mapping[str, int]],
) -> bool:
    """Return whether the activity is fully contained in one downtime block."""
    if duration_min <= 0 or start_hour < 0 or start_hour > 23:
        return False
    activity_start_min = start_hour * 60
    activity_end_min = activity_start_min + duration_min
    for block in available_blocks:
        block_start_min = int(block["start_hour"]) * 60
        block_end_min = int(block["end_hour"]) * 60
        if block_start_min <= activity_start_min and activity_end_min <= block_end_min:
            return True
    return False


def availability_trace(
    assessment: Mapping[str, Any],
    *,
    pa_decision_input: Mapping[str, Any],
) -> dict[str, Any]:
    """Build deterministic downtime-availability metadata for empirical v1.2."""
    daily_context = pa_decision_input.get("daily_context")
    if not isinstance(daily_context, Mapping):
        raise ValueError("Empirical v1.2 availability requires daily_context.")
    blocks = downtime_blocks(daily_context.get("hourly_context_24h"))
    activity = assessment.get("activity_if_performed")
    if activity is None:
        start_hour = None
        duration_min = None
        fits = False
    else:
        if not isinstance(activity, Mapping):
            raise ValueError("activity_if_performed must be an object or null.")
        start_hour = int(activity["start_hour"])
        duration_min = int(activity["duration_min"])
        fits = activity_fits_downtime_block(
            start_hour=start_hour,
            duration_min=duration_min,
            available_blocks=blocks,
        )
    if not blocks:
        reason = NO_DOWNTIME_REASON
    elif not fits:
        reason = INVALID_TIME_ALLOCATION_REASON
    else:
        reason = None
    return {
        "available_downtime_blocks": blocks,
        "requested_start_hour": start_hour,
        "requested_duration_min": duration_min,
        "time_allocation_feasible": fits,
        "infeasibility_reason": reason,
    }


def contextual_flexibility_trace(
    *, pa_decision_input: Mapping[str, Any], activity: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Describe context evidence without inferring a prior PA intention."""
    daily_context = pa_decision_input.get("daily_context", {})
    hourly = daily_context.get("hourly_context_24h")
    blocks = downtime_blocks(hourly)
    barriers: list[dict[str, Any]] = []
    options: dict[str, dict[str, Any]] = {}
    if not blocks:
        barriers.append({"category": "no_downtime", "evidence": {"available_downtime_blocks": 0}})
        for option in PA_OPTIONS:
            options[option] = {"status": "unavailable", "evidence": {"reason": NO_DOWNTIME_REASON}}
        return {
            "adaptation_reference": "none_no_preplanned_pa",
            "contextual_barriers": barriers,
            "available_pa_options": options,
        }

    reference_hour = (
        int(activity["start_hour"]) if activity is not None
        else max(blocks, key=lambda block: block["duration_min"])["start_hour"]
    )
    block = next(block for block in blocks if block["start_hour"] <= reference_hour < block["end_hour"])
    remaining_from_reference_min = (block["end_hour"] - reference_hour) * 60
    minutes_before_start = (
        (reference_hour - block["start_hour"]) * 60 if activity is not None else None
    )
    minutes_after_activity = (
        remaining_from_reference_min - int(activity["duration_min"])
        if activity is not None else None
    )
    entry = hourly[reference_hour]
    if remaining_from_reference_min <= 60:
        barriers.append({"category": "time", "evidence": {
            "block_duration_min": block["duration_min"],
            "remaining_from_reference_min": remaining_from_reference_min,
            "reference_hour": reference_hour,
        }})
    if entry.get("is_wet") is True or _positive_number(entry.get("precipitation_mm")):
        barriers.append({"category": "weather", "evidence": {
            "reference_hour": reference_hour,
            "is_wet": entry.get("is_wet"),
            "precipitation_mm": entry.get("precipitation_mm"),
        }})
    if entry.get("energy_category") == "low":
        barriers.append({"category": "energy", "evidence": {"reference_hour": reference_hour, "energy_category": "low"}})
    constraints = entry.get("active_constraints")
    physical_constraints = [
        constraint for constraint in constraints
        if isinstance(constraint, Mapping)
        and "illness" in f"{constraint.get('type', '')} {constraint.get('name', '')}".lower()
    ] if isinstance(constraints, list) else []
    if physical_constraints:
        barriers.append({"category": "physical_constraint", "evidence": {
            "reference_hour": reference_hour, "active_constraints": physical_constraints,
        }})

    accessibility = entry.get("poi_accessibility")
    for option in PA_OPTIONS:
        target = accessibility.get(option) if isinstance(accessibility, Mapping) else None
        distance = target.get("distance_km") if isinstance(target, Mapping) else None
        times = target.get("travel_times_min") if isinstance(target, Mapping) else None
        walk_min = times.get("walk") if isinstance(times, Mapping) else None
        evidence = {
            "basis": "poi_anchor_distance_and_walk_time",
            "reference_hour": reference_hour,
            "current_location": entry.get("current_location"),
            "distance_km": distance if _nonnegative_number(distance) else None,
            "walk_travel_time_min": walk_min if _nonnegative_number(walk_min) else None,
            "block_duration_min": block["duration_min"],
            "remaining_from_reference_min": remaining_from_reference_min,
            "minutes_before_start": minutes_before_start,
            "minutes_after_activity": minutes_after_activity,
            "is_wet": entry.get("is_wet") if isinstance(entry.get("is_wet"), bool) else None,
            "temperature_c": entry.get("temperature_c") if isinstance(entry.get("temperature_c"), (int, float)) else None,
            "wind_m_s": entry.get("wind_m_s") if _nonnegative_number(entry.get("wind_m_s")) else None,
        }
        if entry.get("current_location") in (None, "unknown") or not _nonnegative_number(distance) or not _nonnegative_number(walk_min):
            status = "unknown"
        else:
            round_trip = 2 * float(walk_min)
            evidence["round_trip_walk_min"] = round_trip
            if activity is None:
                travel_fits = None
                status = "limited" if round_trip >= remaining_from_reference_min else "supported"
            else:
                # start_hour is PA onset; travel needs separate time before and after PA.
                travel_fits = (
                    float(walk_min) <= minutes_before_start
                    and float(walk_min) <= minutes_after_activity
                )
                status = "supported" if travel_fits else "limited"
            evidence["travel_fits_around_activity"] = travel_fits
            if (travel_fits is False or (activity is None and round_trip >= remaining_from_reference_min)) and walk_min > 0:
                barriers.append({"category": "distance", "evidence": {
                    "option": option, "distance_km": distance,
                    "round_trip_walk_min": round_trip,
                    "remaining_from_reference_min": remaining_from_reference_min,
                }})
        if option == "outdoor_activity" and any(item["category"] == "weather" for item in barriers) and status == "supported":
            status = "limited"
        options[option] = {"status": status, "evidence": evidence}

    return {
        "adaptation_reference": "none_no_preplanned_pa",
        "contextual_barriers": barriers,
        "available_pa_options": options,
    }


def _nonnegative_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def _positive_number(value: Any) -> bool:
    return _nonnegative_number(value) and value > 0


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
    time_trace = availability_trace(validated, pa_decision_input=pa_decision_input)
    if time_trace["infeasibility_reason"] == NO_DOWNTIME_REASON and validated["activity_if_performed"] is not None:
        raise ValueError("activity_if_performed must be null when no downtime block is available.")
    if time_trace["infeasibility_reason"] == INVALID_TIME_ALLOCATION_REASON:
        raise ValueError(
            "activity_if_performed.start_hour/duration_min does not fit an available "
            "downtime block."
        )
    flexibility = contextual_flexibility_trace(
        pa_decision_input=pa_decision_input, activity=validated["activity_if_performed"],
    )
    effective_probability = probability if time_trace["time_allocation_feasible"] else 0.0
    seed = sampling_seed(pa_decision_input)
    random_value = random.Random(seed).random()
    performed = random_value < effective_probability

    if performed:
        branch = validated["activity_if_performed"]
        proposed_option = branch["activity_option"]
        option_status = (
            flexibility["available_pa_options"][proposed_option]["status"]
            if proposed_option is not None else "unknown"
        )
        option_evidence = (
            flexibility["available_pa_options"][proposed_option]["evidence"]
            if proposed_option is not None else {}
        )
        used_option = (
            proposed_option
            if option_status in {"supported", "limited"}
            and option_evidence.get("travel_fits_around_activity") is True
            else None
        )
        decision = {
            "persona_id": persona_id,
            "day_index": day_index,
            "decision_code": 3,
            "decision_label": "extra_activity",
            "start_hour": int(branch["start_hour"]),
            "duration_min": int(branch["duration_min"]),
            "rationale_short": str(branch["rationale_short"]),
            "diary_entry": str(branch["diary_entry"]),
        }
        sampled_probability = effective_probability
    else:
        used_option = None
        branch = validated["no_activity_if_skipped"]
        reason = time_trace["infeasibility_reason"]
        rationale = str(branch["rationale_short"])
        diary_entry = str(branch["diary_entry"])
        if reason == NO_DOWNTIME_REASON:
            rationale = NO_DOWNTIME_RATIONALE
            diary_entry = NO_DOWNTIME_DIARY_ENTRY
        decision = {
            "persona_id": persona_id,
            "day_index": day_index,
            "decision_code": 0,
            "decision_label": "skip_activity",
            "start_hour": None,
            "duration_min": 0,
            "rationale_short": rationale,
            "diary_entry": diary_entry,
        }
        sampled_probability = 1.0 - effective_probability

    prior = float(pa_decision_input.get("behavior_policy", {}).get("extra_activity", 0.0))
    barrier_categories = list(dict.fromkeys(
        item["category"] for item in flexibility["contextual_barriers"]
    ))
    potentially_mitigated_barriers = (
        ["weather"]
        if used_option == "indoor_activity" and "weather" in barrier_categories
        else []
    )
    contextual_response = {
        "activity_performed": performed,
        "used_option": used_option,
        "option_support_status": option_status if performed else None,
        "barriers_present": barrier_categories,
        "potentially_mitigated_barriers": potentially_mitigated_barriers,
        "adaptation_reference": "none_no_preplanned_pa",
    }
    return {
        **decision,
        "contextual_pa_probability": probability,
        "effective_pa_probability": effective_probability,
        "behavior_policy_pa_prior": prior,
        "decision_sampling_seed": seed,
        "decision_sampling_random_value": random_value,
        "sampled_decision_label": decision["decision_label"],
        "sampled_decision_probability": sampled_probability,
        "llm2_contextual_assessment": {**validated, "contextual_flexibility": flexibility},
        "contextual_response": contextual_response,
        "pa_time_allocation": time_trace,
    }
