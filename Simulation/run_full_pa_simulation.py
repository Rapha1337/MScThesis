from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

SIMULATION_DIR = Path(__file__).resolve().parent
ROOT_DIR = SIMULATION_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))
if str(SIMULATION_DIR) not in sys.path:
    sys.path.append(str(SIMULATION_DIR))

from agent_context_export import (  # noqa: E402
    DEFAULT_INPUT_PARAMETERS,
    _LightweightBernMap,
    _build_accessibility_model_from_parameters,
    _install_lightweight_optional_dependency_stubs,
    _json_ready,
    _normalize_input_parameters,
    _student_parameters_from_inputs,
)
from psychological_state import (  # noqa: E402
    BACKEND_CONSTRUCT_RANGES,
    build_psychological_state,
)
from resource_usage import ResourceUsageEngine  # noqa: E402
from run_llm_pa_decision import (  # noqa: E402
    LLM1_MAX_TOKENS,
    LLM2_MAX_TOKENS,
    PA_DECISION_CODEBOOK,
    MODEL_NAME,
    TEMPERATURE,
    TOP_P,
    DIARY_ENTRY_GENERATED_FOR_SIMULATION,
    SUCCESSFUL_PA_DECISION_LABELS,
    UNSUCCESSFUL_PA_DECISION_LABELS,
    activity_performed_for_decision_label,
    load_behavior_probability_prompt,
    load_pa_decision_prompt,
    run_pipeline_for_context,
)
from schedule_model_student import YearPhase  # noqa: E402
from simulation_runner import SimulationRunner  # noqa: E402
from state_assessment import (  # noqa: E402
    ACTIVE_CONSTRUCTS,
    DEFAULT_MAX_TOKENS as STATE_ASSESSMENT_MAX_TOKENS,
    load_state_assessment_prompt,
    run_state_assessment,
)

DEFAULT_OUTPUT_DIR = SIMULATION_DIR / "output" / "full_pa_simulation"
SIMULATION_RUN_MANIFEST_FILENAME = "simulation_run_manifest.json"
RESOURCE_USAGE_FILENAME = "resource_usage.jsonl"
DEPRECATED_DECISION_CATEGORIES: tuple[str, ...] = (
    "app_ignored",
    "postpone_activity",
    "postponed",
    "not_done",
    "done_as_planned",
    "adapted",
    "extra_movement",
)
PSYCHOLOGICAL_SEED_OFFSET = 10_000_019

BEHAVIOR_POLICY_DRY_RUN: dict[str, float] = {
    "do_planned_activity": 0.25,
    "adapt_activity": 0.30,
    "skip_activity": 0.35,
    "extra_activity": 0.10,
}

LLM_HOURLY_FIELDS: tuple[str, ...] = (
    "hour",
    "activity_type",
    "subtype",
    "current_location",
    "active_constraints",
    "energy_level",
    "energy_category",
    "month",
    "season",
    "temperature_c",
    "feels_like_c",
    "humidity_pct",
    "wind_m_s",
    "precipitation_mm",
    "is_wet",
    "sun_frac",
    "is_daylight",
    "snow_cover",
)
LLM_POI_TARGETS: tuple[str, ...] = ("indoor_activity", "outdoor_activity")
GLOBAL_ENVIRONMENT_FIELDS: tuple[str, ...] = (
    "month",
    "season",
    "temperature_c",
    "feels_like_c",
    "humidity_pct",
    "wind_m_s",
    "precipitation_mm",
    "is_wet",
    "sun_frac",
    "is_daylight",
    "snow_cover",
)

PERSONA_INPUT_CLI_TO_INTERNAL: dict[str, str] = {
    "physical_activity_hours_per_week": "fitness_hours_week",
    "social_hours_per_week": "social_hours_week",
    "care_work_hours_per_week": "carework_hours_week",
    "work_hours_per_week": "work_hours_week",
}
PERSONA_INPUT_INTERNAL_TO_METADATA: dict[str, str] = {
    internal_key: cli_key for cli_key, internal_key in PERSONA_INPUT_CLI_TO_INTERNAL.items()
}
POI_DISTANCE_CLI_TO_INTERNAL: dict[str, str] = {
    "workplace_distance_km": "workplace_distance_km",
    "indoor_activity_distance_km": "indoor_activity_distance_km",
    "outdoor_activity_distance_km": "outdoor_activity_distance_km",
}
POI_DISTANCE_INTERNAL_TO_METADATA: dict[str, str] = {
    "workplace_distance_km": "workplace",
    "indoor_activity_distance_km": "indoor_activity",
    "outdoor_activity_distance_km": "outdoor_activity",
}
CLI_OVERRIDE_DESTINATIONS: tuple[str, ...] = tuple(PERSONA_INPUT_CLI_TO_INTERNAL) + tuple(POI_DISTANCE_CLI_TO_INTERNAL)

DAILY_DECISION_LOG_COLUMNS: tuple[str, ...] = (
    "persona_id",
    "day_index",
    "calendar_date",
    "decision_code",
    "decision_label",
    "activity_done",
    "activity_performed",
    "diary_entry_generated_for_simulation",
    "planned_physical_activity",
    "was_physical_activity_planned_today",
    "state_assessment_enabled",
    "state_assessment_mode",
    "previous_diary_entries_count",
    "psychological_construct_values_before_state_assessment",
    "state_assessment_item_scores",
    "state_assessment_mean_scores_raw",
    "state_assessment_mean_scores_normalized",
    "state_assessment_target_values_normalized",
    "psychological_construct_update_strategy",
    "psychological_construct_update_alpha",
    "psychological_construct_update_max_daily_change",
    "psychological_construct_update_delta_proposed",
    "psychological_construct_update_delta_applied",
    "psychological_construct_values_after_smoothed_update",
    "psychological_construct_values_after_state_assessment",
    "behavior_policy_raw",
    "decision_context_has_planned_pa",
    "active_decision_probabilities",
    "sampled_decision_label",
    "sampled_decision_probability",
    "decision_sampling_seed",
    "decision_sampling_random_value",
    "behavior_policy",
    "previous_psychological_constructs",
    "updated_psychological_constructs",
    "diary_entry",
    "rationale_short",
)

LONGITUDINAL_CONSTRUCT_COLUMNS: tuple[str, ...] = (
    "persona_id",
    "day_index",
    "calendar_date",
    "construct",
    "value_before",
    "value_after",
    "delta",
    "decision_label",
    "activity_done",
)


@dataclass
class FullSimulationConfig:
    n_personas: int
    n_days: int
    start_date: date
    base_seed: int
    output_dir: Path
    model: str
    temperature: float
    llm1_max_tokens: int
    llm2_max_tokens: int
    dry_run: bool
    include_full_hourly_context: bool
    state_assessment_max_tokens: int = STATE_ASSESSMENT_MAX_TOKENS
    state_assessment_json_mode: bool = False
    cli_overrides: dict[str, list[float | None]] | None = None
    daily_log_path: Path | None = None
    enable_resource_tracking: bool = True
    enable_codecarbon: bool = False
    verbose_llm_debug: bool = False
    top_p: float = TOP_P
    llm_seed: int | None = None


@dataclass
class PersonaRuntimeState:
    persona_id: str
    seed: int
    psychological_seed: int
    input_parameters: dict[str, Any]
    poi_distances_km: dict[str, Any]
    selected_schedule_parameters: dict[str, Any]
    runner: SimulationRunner
    psychological_state: dict[str, Any]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a configurable longitudinal PA simulation over personas and consecutive days."
    )
    parser.add_argument("--n-personas", type=int, default=2)
    parser.add_argument("--n-days", type=int, default=2)
    parser.add_argument("--start-date", default="2026-01-01", help="Start date in YYYY-MM-DD format.")
    parser.add_argument("--base-seed", type=int, default=137)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--temperature", type=float, default=TEMPERATURE)
    parser.add_argument("--top-p", dest="top_p", type=float, default=TOP_P)
    parser.add_argument("--llm-seed", type=int, default=None)
    parser.add_argument("--llm1-max-tokens", type=int, default=LLM1_MAX_TOKENS)
    parser.add_argument("--llm2-max-tokens", type=int, default=LLM2_MAX_TOKENS)
    parser.add_argument(
        "--state-assessment-max-tokens",
        type=int,
        default=STATE_ASSESSMENT_MAX_TOKENS,
    )
    parser.add_argument(
        "--state-assessment-json-mode",
        action="store_true",
        help="Opt in to OpenAI-compatible JSON object mode for State Assessment.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--enable-resource-tracking",
        dest="enable_resource_tracking",
        action="store_true",
        default=True,
        help="Write Kai-style resource_usage.jsonl output (default).",
    )
    parser.add_argument(
        "--disable-resource-tracking",
        dest="enable_resource_tracking",
        action="store_false",
        help="Disable resource_usage.jsonl output.",
    )
    parser.add_argument(
        "--enable-codecarbon",
        dest="enable_codecarbon",
        action="store_true",
        default=True,
        help="Enable optional CodeCarbon tracking when codecarbon is installed (default).",
    )
    parser.add_argument(
        "--disable-codecarbon",
        dest="enable_codecarbon",
        action="store_false",
        help="Disable optional CodeCarbon tracking.",
    )
    parser.add_argument(
        "--verbose-llm-debug",
        action="store_true",
        help=(
            "Unsafe debug-only mode: pass through additional LLM diagnostics. "
            "Reasoning content is still redacted."
        ),
    )
    parser.add_argument("--include-full-hourly-context", action="store_true")
    parser.add_argument("--physical-activity-hours-per-week", default=None)
    parser.add_argument("--social-hours-per-week", default=None)
    parser.add_argument("--care-work-hours-per-week", default=None)
    parser.add_argument("--work-hours-per-week", default=None)
    parser.add_argument("--workplace-distance-km", default=None)
    parser.add_argument("--indoor-activity-distance-km", default=None)
    parser.add_argument("--outdoor-activity-distance-km", default=None)
    parser.add_argument("--daily-log-path", type=Path, default=None)
    return parser.parse_args(argv)


def parse_numeric_override_list(value: str | None, n_personas: int) -> list[float | None]:
    """Parse one CLI override as all-persona, per-persona, or missing values.

    A single numeric value is broadcast to every persona. A comma-separated list
    is mapped by position and may be shorter than ``n_personas``; missing
    positions are returned as ``None`` so defaults can be kept.
    """
    if n_personas < 1:
        raise ValueError("n_personas must be >= 1")
    if value is None:
        return [None] * n_personas

    raw_value = str(value).strip()
    if not raw_value:
        raise ValueError("Override values must not be empty.")

    raw_parts = [part.strip() for part in raw_value.split(",")]
    if any(part == "" for part in raw_parts):
        raise ValueError(f"Override list {value!r} contains an empty value.")
    if len(raw_parts) > n_personas:
        raise ValueError(
            f"Override list {value!r} has {len(raw_parts)} values, but --n-personas is {n_personas}."
        )

    parsed: list[float] = []
    for part in raw_parts:
        try:
            number = float(part)
        except ValueError as exc:
            raise ValueError(f"Override value {part!r} is not numeric.") from exc
        if number < 0:
            raise ValueError(f"Override value {part!r} must be non-negative.")
        parsed.append(number)

    if len(parsed) == 1 and "," not in raw_value:
        return [parsed[0]] * n_personas
    return [*parsed, *([None] * (n_personas - len(parsed)))]


def _parse_cli_overrides(args: argparse.Namespace) -> dict[str, list[float | None]]:
    return {
        destination: parse_numeric_override_list(getattr(args, destination, None), int(args.n_personas))
        for destination in CLI_OVERRIDE_DESTINATIONS
    }


def _metadata_input_parameters(input_parameters: Mapping[str, Any]) -> dict[str, Any]:
    return {
        metadata_key: input_parameters[internal_key]
        for internal_key, metadata_key in PERSONA_INPUT_INTERNAL_TO_METADATA.items()
    }


def _metadata_poi_distances(input_parameters: Mapping[str, Any]) -> dict[str, Any]:
    return {
        metadata_key: input_parameters[internal_key]
        for internal_key, metadata_key in POI_DISTANCE_INTERNAL_TO_METADATA.items()
    }


def apply_persona_cli_overrides(
    default_input_parameters: Mapping[str, Any],
    default_poi_distances: Mapping[str, Any],
    args: argparse.Namespace | Mapping[str, list[float | None]] | None,
    persona_index: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply parsed CLI overrides for one zero-based persona index."""
    input_parameters = dict(default_input_parameters)
    poi_distances = dict(default_poi_distances)
    if args is None:
        return input_parameters, poi_distances

    parsed_overrides = (
        args if isinstance(args, Mapping) else _parse_cli_overrides(args)
    )
    for cli_key, internal_key in PERSONA_INPUT_CLI_TO_INTERNAL.items():
        values = parsed_overrides.get(cli_key, [])
        if persona_index < len(values) and values[persona_index] is not None:
            input_parameters[internal_key] = values[persona_index]
    for cli_key, internal_key in POI_DISTANCE_CLI_TO_INTERNAL.items():
        values = parsed_overrides.get(cli_key, [])
        if persona_index < len(values) and values[persona_index] is not None:
            poi_distances[internal_key] = values[persona_index]

    return input_parameters, poi_distances


def _parse_start_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"--start-date must use YYYY-MM-DD format; got {value!r}") from exc


def config_from_args(args: argparse.Namespace) -> FullSimulationConfig:
    if args.n_personas < 1:
        raise ValueError("--n-personas must be >= 1")
    if args.n_days < 1:
        raise ValueError("--n-days must be >= 1")
    return FullSimulationConfig(
        n_personas=int(args.n_personas),
        n_days=int(args.n_days),
        start_date=_parse_start_date(str(args.start_date)),
        base_seed=int(args.base_seed),
        output_dir=Path(args.output_dir),
        model=str(args.model),
        temperature=float(args.temperature),
        top_p=float(args.top_p),
        llm_seed=int(args.llm_seed) if args.llm_seed is not None else None,
        llm1_max_tokens=int(args.llm1_max_tokens),
        llm2_max_tokens=int(args.llm2_max_tokens),
        state_assessment_max_tokens=int(args.state_assessment_max_tokens),
        state_assessment_json_mode=bool(args.state_assessment_json_mode),
        dry_run=bool(args.dry_run),
        include_full_hourly_context=bool(args.include_full_hourly_context),
        cli_overrides=_parse_cli_overrides(args),
        daily_log_path=Path(args.daily_log_path) if args.daily_log_path else None,
        enable_resource_tracking=bool(args.enable_resource_tracking),
        enable_codecarbon=bool(args.enable_codecarbon),
        verbose_llm_debug=bool(args.verbose_llm_debug),
    )


def _psychological_seed_from_persona_seed(persona_seed: int) -> int:
    return int(persona_seed) + PSYCHOLOGICAL_SEED_OFFSET


def _json_log_value(value: Any) -> str:
    return json.dumps(_json_ready(value), ensure_ascii=False, sort_keys=True)


def _compact_llm_poi_accessibility(hourly_entry: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    source_poi = hourly_entry.get("poi_accessibility")
    if not isinstance(source_poi, Mapping):
        return {target: {"distance_km": None, "travel_times_min": {}} for target in LLM_POI_TARGETS}

    compact: dict[str, dict[str, Any]] = {}
    for target in LLM_POI_TARGETS:
        target_payload = source_poi.get(target)
        if not isinstance(target_payload, Mapping):
            compact[target] = {"distance_km": None, "travel_times_min": {}}
            continue
        travel_times = target_payload.get("travel_times_min")
        compact[target] = {
            "distance_km": target_payload.get("distance_km"),
            "travel_times_min": dict(travel_times) if isinstance(travel_times, Mapping) else {},
        }
    return compact


def _compact_hourly_entry(hourly_entry: Mapping[str, Any]) -> dict[str, Any]:
    entry = {field: hourly_entry.get(field) for field in LLM_HOURLY_FIELDS if field in hourly_entry}
    entry["poi_accessibility"] = _compact_llm_poi_accessibility(hourly_entry)
    return entry


def _extract_constructs(psychological_state: Mapping[str, Any]) -> dict[str, float]:
    values = psychological_state.get("values_normalized")
    if not isinstance(values, Mapping):
        return {}
    return {str(key): float(value) for key, value in values.items() if isinstance(value, (int, float)) and not isinstance(value, bool)}


def _raw_scale_mean(construct_name: str, normalized_value: float) -> float:
    low, high = BACKEND_CONSTRUCT_RANGES[construct_name]
    clipped = min(1.0, max(0.0, float(normalized_value)))
    return round(float(low) + clipped * (float(high) - float(low)), 2)


def _psychological_state_with_updated_constructs(
    previous_state: Mapping[str, Any],
    updated_constructs: Mapping[str, Any],
) -> dict[str, Any]:
    state = dict(previous_state)
    rounded = {
        str(key): round(min(1.0, max(0.0, float(value))), 3)
        for key, value in updated_constructs.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }
    state["values_normalized"] = rounded
    state["raw_scale_means"] = {
        key: _raw_scale_mean(key, value)
        for key, value in rounded.items()
        if key in BACKEND_CONSTRUCT_RANGES
    }
    state["last_update"] = {
        "source": "run_full_pa_simulation.closed_loop_placeholder",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    return _json_ready(state)


def _schedule_parameters_payload(persona: Any, seed: int) -> dict[str, Any]:
    schedule_parameters = persona.to_structure_parameters(seed=seed)
    return {
        "name": schedule_parameters.name,
        "schedule_rigidity": schedule_parameters.schedule_rigidity,
        "phase_variability": schedule_parameters.phase_variability,
        "university_load": schedule_parameters.university_load,
        "employment_load": schedule_parameters.employment_load,
        "study_intensity": schedule_parameters.study_intensity,
        "sport_frequency": schedule_parameters.sport_frequency,
        "sport_fixedness": schedule_parameters.sport_fixedness,
        "evening_flexibility": schedule_parameters.evening_flexibility,
        "day_fragmentation": schedule_parameters.day_fragmentation,
        "random_event_rate": schedule_parameters.random_event_rate,
        "commute_load": schedule_parameters.commute_load,
        "location_switch_frequency": schedule_parameters.location_switch_frequency,
        "weekend_structure": schedule_parameters.weekend_structure,
        "weekend_social_intensity": schedule_parameters.weekend_social_intensity,
        "social_hours_week": schedule_parameters.social_hours_week,
        "carework_hours_week": schedule_parameters.carework_hours_week,
    }


def _build_persona_states(config: FullSimulationConfig) -> list[PersonaRuntimeState]:
    _install_lightweight_optional_dependency_stubs()
    from env_time_weather import TimeWeatherEnv

    rng = random.Random(config.base_seed)
    normalized_inputs = _normalize_input_parameters(DEFAULT_INPUT_PARAMETERS)
    default_input_parameters = {
        key: normalized_inputs[key]
        for key in PERSONA_INPUT_INTERNAL_TO_METADATA
    }
    default_poi_distances = {
        key: normalized_inputs[key]
        for key in POI_DISTANCE_INTERNAL_TO_METADATA
    }
    start_month = int(config.start_date.month)
    start_day_offset = min(int(config.start_date.day) - 1, 29)
    horizon_hours = max(24 * 365, 24 * (start_day_offset + config.n_days + 1))

    states: list[PersonaRuntimeState] = []
    for idx in range(config.n_personas):
        persona_seed = rng.randint(0, 2**31 - 1)
        persona_id = f"StudentPersona_{idx + 1:02d}"
        input_parameters, poi_distances = apply_persona_cli_overrides(
            default_input_parameters,
            default_poi_distances,
            config.cli_overrides,
            idx,
        )
        simulation_inputs = {**normalized_inputs, **input_parameters, **poi_distances}
        simulation_inputs["day_index"] = 0
        persona = _student_parameters_from_inputs(persona_id, simulation_inputs)
        accessibility_model = _build_accessibility_model_from_parameters(persona.accessibility_input_parameters())
        env = TimeWeatherEnv(
            month=start_month,
            sample_rate_hours=1,
            horizon_hours=horizon_hours,
            bern_map=_LightweightBernMap(),
        )
        runner = SimulationRunner(
            persona=persona,
            phase=YearPhase.NORMAL,
            env=env,
            seed=persona_seed,
            use_year_structure=True,
            accessibility_model=accessibility_model,
        )
        runner.reset_world()
        psychological_seed = _psychological_seed_from_persona_seed(persona_seed)
        states.append(
            PersonaRuntimeState(
                persona_id=persona_id,
                seed=persona_seed,
                psychological_seed=psychological_seed,
                input_parameters=_json_ready(_metadata_input_parameters(simulation_inputs)),
                poi_distances_km=_json_ready(_metadata_poi_distances(simulation_inputs)),
                selected_schedule_parameters=_json_ready(_schedule_parameters_payload(persona, persona_seed)),
                runner=runner,
                psychological_state=build_psychological_state(psychological_seed),
            )
        )
    return states


def build_global_environment_by_date(
    config: FullSimulationConfig,
) -> dict[str, list[dict[str, Any]]]:
    """Generate the run-level hourly environment exactly once per calendar date."""
    _install_lightweight_optional_dependency_stubs()
    from env_time_weather import TimeWeatherEnv

    start_day_offset = min(int(config.start_date.day) - 1, 29)
    horizon_hours = max(24 * 365, 24 * (start_day_offset + config.n_days + 1))
    environment_by_date: dict[str, list[dict[str, Any]]] = {}

    for day_index in range(config.n_days):
        calendar_date = config.start_date + timedelta(days=day_index)
        env = TimeWeatherEnv(
            month=int(config.start_date.month),
            sample_rate_hours=1,
            horizon_hours=horizon_hours,
            bern_map=_LightweightBernMap(),
        )
        env.reset(seed=config.base_seed + day_index)
        hourly_environment = env.build_hourly_environment_24h(
            start_t=24 * (start_day_offset + day_index)
        )
        environment_by_date[calendar_date.isoformat()] = [
            {
                "hour": int(entry["hour"]),
                **{field: entry[field] for field in GLOBAL_ENVIRONMENT_FIELDS},
            }
            for entry in hourly_environment
        ]

    return _json_ready(environment_by_date)


def _merge_global_environment(
    persona_hourly_context: Sequence[Mapping[str, Any]],
    global_hourly_environment: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if len(persona_hourly_context) != 24 or len(global_hourly_environment) != 24:
        raise ValueError(
            "Persona context and global environment must each contain 24 hourly entries."
        )

    merged: list[dict[str, Any]] = []
    for persona_entry, environment_entry in zip(
        persona_hourly_context, global_hourly_environment, strict=True
    ):
        if persona_entry.get("hour") != environment_entry.get("hour"):
            raise ValueError(
                "Global environment hour does not align with persona hourly context: "
                f"{environment_entry.get('hour')} != {persona_entry.get('hour')}."
            )
        merged.append(
            {
                **dict(persona_entry),
                **{field: environment_entry[field] for field in GLOBAL_ENVIRONMENT_FIELDS},
            }
        )
    return merged


def build_llm_ready_context_for_day(
    state: PersonaRuntimeState,
    *,
    day_index: int,
    calendar_date: date,
    start_day_offset: int,
    global_hourly_environment: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    absolute_day_index = int(start_day_offset) + int(day_index)
    state.runner._sim_hour = absolute_day_index * 24
    diagnostic_context = state.runner.get_day_context()
    hourly_context = list(diagnostic_context.get("hourly_context_24h", []))
    if len(hourly_context) != 24:
        raise ValueError(
            f"Expected 24 hourly context entries for {state.persona_id} day {day_index}; "
            f"got {len(hourly_context)}."
        )

    shared_hourly_context = _merge_global_environment(
        hourly_context,
        global_hourly_environment,
    )
    llm_context = {
        "persona_id": state.persona_id,
        "seed": int(state.seed),
        "day_index": int(day_index),
        "calendar_date": calendar_date.isoformat(),
        "phase": diagnostic_context.get("phase"),
        "weekday": diagnostic_context.get("weekday"),
        "psychological_state": dict(state.psychological_state),
        "hourly_context_24h": [
            _compact_hourly_entry(entry) for entry in shared_hourly_context
        ],
    }
    return _json_ready(llm_context), _json_ready(diagnostic_context)


def planned_physical_activity_from_schedule(
    hourly_context: Sequence[Mapping[str, Any]],
) -> dict[str, Any] | None:
    """Summarize the current day's schedule-derived physical-activity slot."""
    slots = [
        entry
        for entry in hourly_context
        if entry.get("activity_type") == "physical_activity"
        or entry.get("subtype") == "physical_activity"
    ]
    if not slots:
        return None
    hours = sorted(int(entry["hour"]) for entry in slots)
    return {
        "source": "current_day_schedule",
        "activity_type": "physical_activity",
        "scheduled_hours": hours,
        "start_hour": hours[0],
        "end_hour": hours[-1] + 1,
        "duration_min": len(hours) * 60,
        "schedule_entries": [
            {
                key: entry.get(key)
                for key in ("hour", "activity_type", "subtype", "current_location", "active_constraints")
            }
            for entry in slots
        ],
    }


def _dry_behavior_runner(agent_context: Mapping[str, Any], **kwargs: Any) -> dict[str, dict[str, float]]:
    del kwargs
    # Assert the longitudinal state machine is feeding constructs into LLM1 input.
    if not _extract_constructs(agent_context.get("psychological_state", {})):
        raise ValueError("Dry-run behavior runner requires psychological constructs.")
    return {
        "probabilities": dict(BEHAVIOR_POLICY_DRY_RUN),
        "_resource_usage": {
            "prompt_tokens": 0,
            "response_tokens": 0,
            "tokens_total": 0,
            "token_source": "dry_run",
            "paper_seconds": 0.0,
        },
    }


def _dry_pa_decision_runner(pa_decision_input: Mapping[str, Any], **kwargs: Any) -> dict[str, Any]:
    del kwargs
    planned_activity = pa_decision_input.get("planned_physical_activity")
    decision_label = str(pa_decision_input["sampled_decision_label"])
    decision_code = next(
        code for code, codebook_label in PA_DECISION_CODEBOOK.items()
        if codebook_label == decision_label
    )
    if planned_activity is None and decision_label == "skip_activity":
        rationale = "Dry-run day without scheduled PA; no spontaneous activity occurred."
        diary = "Dry-run: I rested instead and did no additional movement today."
    elif planned_activity is None:
        rationale = "Dry-run day without scheduled PA; simulated spontaneous activity."
        diary = "Dry-run: I added some spontaneous movement today."
    elif decision_label == "skip_activity":
        rationale = "Dry-run day with scheduled PA; the planned activity was not performed."
        diary = "Dry-run: I did not do today's scheduled activity."
    elif decision_label == "extra_activity":
        rationale = "Dry-run day with scheduled PA; simulated additional spontaneous activity."
        diary = "Dry-run: I added spontaneous movement beyond today's plan."
    elif decision_label == "adapt_activity":
        rationale = "Dry-run day with scheduled PA; simulated adjusted completion."
        diary = "Dry-run: I adjusted today's scheduled activity and still moved."
    else:
        rationale = "Dry-run day with scheduled PA; simulated completion as planned."
        diary = "Dry-run: I completed today's scheduled activity as planned."

    return {
        "persona_id": str(pa_decision_input["persona_id"]),
        "day_index": int(pa_decision_input["day_index"]),
        "decision_code": decision_code,
        "decision_label": decision_label,
        "rationale_short": rationale,
        "diary_entry": diary,
        "_resource_usage": {
            "prompt_tokens": 0,
            "response_tokens": 0,
            "tokens_total": 0,
            "token_source": "dry_run",
            "paper_seconds": 0.0,
        },
    }


def _context_summary(llm_context: Mapping[str, Any]) -> dict[str, Any]:
    hourly = list(llm_context.get("hourly_context_24h", []))
    wet_hours = sum(1 for entry in hourly if entry.get("is_wet"))
    free_hours = sum(1 for entry in hourly if entry.get("activity_type") == "downtime")
    daylight_hours = sum(1 for entry in hourly if entry.get("is_daylight"))
    energy_values = [
        float(entry["energy_level"])
        for entry in hourly
        if isinstance(entry.get("energy_level"), (int, float)) and not isinstance(entry.get("energy_level"), bool)
    ]
    return {
        "n_hourly_context_entries": len(hourly),
        "n_wet_hours": wet_hours,
        "n_downtime_hours": free_hours,
        "n_daylight_hours": daylight_hours,
        "mean_energy_level": round(sum(energy_values) / len(energy_values), 3) if energy_values else None,
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_ready(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.loads(path.read_text(encoding="utf-8"))
    return path


def _write_daily_log_row(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    should_write_header = not path.exists() or path.stat().st_size == 0
    closed_loop = record["closed_loop_update"]
    pa_decision = record["pa_decision"]
    row = {
        "persona_id": record["persona_id"],
        "day_index": int(record["day_index"]),
        "calendar_date": record["calendar_date"],
        "decision_code": int(pa_decision["decision_code"]),
        "decision_label": str(pa_decision["decision_label"]),
        "activity_done": bool(closed_loop["activity_done"]),
        "activity_performed": bool(closed_loop.get("activity_performed", closed_loop["activity_done"])),
        "diary_entry_generated_for_simulation": bool(
            closed_loop.get(
                "diary_entry_generated_for_simulation",
                DIARY_ENTRY_GENERATED_FOR_SIMULATION,
            )
        ),
        "planned_physical_activity": _json_log_value(record.get("planned_physical_activity")),
        "was_physical_activity_planned_today": bool(
            record.get("was_physical_activity_planned_today")
        ),
        "state_assessment_enabled": bool(record.get("state_assessment_enabled")),
        "state_assessment_mode": str(record.get("state_assessment_mode")),
        "previous_diary_entries_count": int(record.get("previous_diary_entries_count", 0)),
        "psychological_construct_values_before_state_assessment": _json_log_value(
            record.get("psychological_construct_values_before_state_assessment")
        ),
        "state_assessment_item_scores": _json_log_value(
            record.get("state_assessment_item_scores")
        ),
        "state_assessment_mean_scores_raw": _json_log_value(
            record.get("state_assessment_mean_scores_raw")
        ),
        "state_assessment_mean_scores_normalized": _json_log_value(
            record.get("state_assessment_mean_scores_normalized")
        ),
        "state_assessment_target_values_normalized": _json_log_value(
            record.get("state_assessment_target_values_normalized")
        ),
        "psychological_construct_update_strategy": record.get(
            "psychological_construct_update_strategy"
        ),
        "psychological_construct_update_alpha": record.get(
            "psychological_construct_update_alpha"
        ),
        "psychological_construct_update_max_daily_change": record.get(
            "psychological_construct_update_max_daily_change"
        ),
        "psychological_construct_update_delta_proposed": _json_log_value(
            record.get("psychological_construct_update_delta_proposed")
        ),
        "psychological_construct_update_delta_applied": _json_log_value(
            record.get("psychological_construct_update_delta_applied")
        ),
        "psychological_construct_values_after_smoothed_update": _json_log_value(
            record.get("psychological_construct_values_after_smoothed_update")
        ),
        "psychological_construct_values_after_state_assessment": _json_log_value(
            record.get("psychological_construct_values_after_state_assessment")
        ),
        "behavior_policy": _json_log_value(record.get("behavior_policy")),
        "behavior_policy_raw": _json_log_value(record.get("behavior_policy_raw")),
        "decision_context_has_planned_pa": bool(
            record.get("decision_context_has_planned_pa")
        ),
        "active_decision_probabilities": _json_log_value(
            record.get("active_decision_probabilities")
        ),
        "sampled_decision_label": str(record.get("sampled_decision_label")),
        "sampled_decision_probability": float(record["sampled_decision_probability"]),
        "decision_sampling_seed": int(record["decision_sampling_seed"]),
        "decision_sampling_random_value": float(record["decision_sampling_random_value"]),
        "previous_psychological_constructs": _json_log_value(
            record.get("psychological_constructs_before_update")
        ),
        "updated_psychological_constructs": _json_log_value(
            record.get("psychological_constructs_after_update")
        ),
        "diary_entry": str(pa_decision["diary_entry"]),
        "rationale_short": str(pa_decision["rationale_short"]),
    }
    with path.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=DAILY_DECISION_LOG_COLUMNS)
        if should_write_header:
            writer.writeheader()
        writer.writerow(row)


def _write_longitudinal_construct_rows(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    should_write_header = not path.exists() or path.stat().st_size == 0
    before = dict(record.get("psychological_constructs_before_update", {}))
    after = dict(record.get("psychological_constructs_after_update", {}))
    pa_decision = record["pa_decision"]
    activity_done = bool(record["closed_loop_update"].get("activity_performed", record["closed_loop_update"]["activity_done"]))
    with path.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=LONGITUDINAL_CONSTRUCT_COLUMNS)
        if should_write_header:
            writer.writeheader()
        for construct in sorted(before):
            value_before = float(before[construct])
            value_after = float(after.get(construct, value_before))
            writer.writerow(
                {
                    "persona_id": record["persona_id"],
                    "day_index": int(record["day_index"]),
                    "calendar_date": record["calendar_date"],
                    "construct": construct,
                    "value_before": value_before,
                    "value_after": value_after,
                    "delta": value_after - value_before,
                    "decision_label": str(pa_decision["decision_label"]),
                    "activity_done": activity_done,
                }
            )


def _run_pipeline(
    llm_context: Mapping[str, Any],
    *,
    planned_activity_for_day: Any | None,
    config: FullSimulationConfig,
    output_dir: Path,
    pipeline_daily_log_path: Path,
    behavior_system_prompt: str,
    pa_decision_system_prompt: str,
    resource_tracker: ResourceUsageEngine | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if config.dry_run:
        kwargs["behavior_runner"] = _dry_behavior_runner
        kwargs["pa_decision_runner"] = _dry_pa_decision_runner

    return run_pipeline_for_context(
        llm_context,
        behavior_system_prompt=behavior_system_prompt,
        pa_decision_system_prompt=pa_decision_system_prompt,
        planned_activity=planned_activity_for_day,
        model=config.model,
        temperature=config.temperature,
        top_p=config.top_p,
        llm_seed=config.llm_seed,
        llm1_max_tokens=config.llm1_max_tokens,
        llm2_max_tokens=config.llm2_max_tokens,
        output_dir=output_dir,
        daily_log_path=pipeline_daily_log_path,
        resource_tracker=resource_tracker,
        resource_usage_token_source="dry_run" if config.dry_run else "unavailable",
        verbose_llm_debug=config.verbose_llm_debug,
        **kwargs,
    )


def _known_output_files(
    *,
    daily_log_path: Path,
    longitudinal_path: Path,
    contexts_compact_path: Path,
    persona_metadata_path: Path,
    pipeline_daily_log_path: Path,
    resource_usage_path: Path,
    manifest_path: Path,
    output_dir: Path,
) -> dict[str, str]:
    def rel(path: Path) -> str:
        try:
            return str(path.relative_to(output_dir))
        except ValueError:
            return str(path)

    return {
        "full_simulation_trace": "full_simulation_trace.json",
        "daily_decision_log": rel(daily_log_path),
        "longitudinal_constructs": rel(longitudinal_path),
        "contexts_compact": rel(contexts_compact_path),
        "persona_metadata": rel(persona_metadata_path),
        "pipeline_closed_loop_daily_log": rel(pipeline_daily_log_path),
        "resource_usage": rel(resource_usage_path),
        "simulation_run_manifest": rel(manifest_path),
        "run_config": "run_config.json",
    }


def _build_simulation_run_manifest(
    *,
    config: FullSimulationConfig,
    run_id: str,
    run_status: str,
    output_files: Mapping[str, str],
    state_assessment_call_count: int,
    state_assessment_dry_run_count: int,
    error: BaseException | None = None,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_status": run_status,
        "error_type": type(error).__name__ if error is not None else None,
        "error_message": str(error)[:500] if error is not None else None,
        "simulation": {
            "dry_run": config.dry_run,
            "n_personas": config.n_personas,
            "n_days": config.n_days,
            "base_seed": config.base_seed,
            "start_date": config.start_date.isoformat(),
            "temperature": config.temperature,
            "top_p": config.top_p,
            "llm_seed": config.llm_seed,
        },
        "models": {
            "llm1": config.model,
            "llm2": config.model,
            "state_assessment": config.model,
        },
        "psychological_construct_update_strategy": "smoothed_bounded",
        "psychological_construct_update_alpha": 0.20,
        "psychological_construct_update_max_daily_change": 0.10,
        "psychological_construct_update_null_handling": "keep_previous",
        "state_assessment": {
            "state_assessment_enabled": True,
            "state_assessment_prompt_path": str(
                (SIMULATION_DIR / "AssessmentModel_Prompt.md").relative_to(ROOT_DIR)
            ),
            "state_assessment_model_name": config.model,
            "state_assessment_max_tokens": config.state_assessment_max_tokens,
            "state_assessment_json_mode_enabled": config.state_assessment_json_mode,
            "state_assessment_call_count": state_assessment_call_count,
            "state_assessment_dry_run_count": state_assessment_dry_run_count,
            "previous_diary_entries_passed_as_context": True,
            "previous_diary_entry_context_strategy": "all_previous_entries_for_run",
            "active_constructs": list(ACTIVE_CONSTRUCTS),
            "placeholder_next_day_activity_generation_disabled": True,
            "psychological_construct_update_strategy": "smoothed_bounded",
            "psychological_construct_update_alpha": 0.20,
            "psychological_construct_update_max_daily_change": 0.10,
            "psychological_construct_update_null_handling": "keep_previous",
        },
        "decision_schema": {
            "active_categories": [PA_DECISION_CODEBOOK[key] for key in sorted(PA_DECISION_CODEBOOK)],
            "successful_activity_categories": sorted(SUCCESSFUL_PA_DECISION_LABELS),
            "unsuccessful_or_no_activity_categories": sorted(UNSUCCESSFUL_PA_DECISION_LABELS),
            "deprecated_categories": list(DEPRECATED_DECISION_CATEGORIES),
            "app_ignored_active": False,
            "app_specific_output_fields_active": False,
        },
        "prompt_files": {
            "llm1": str((SIMULATION_DIR / "BehaviorProbability_Prompt.md").relative_to(ROOT_DIR)),
            "llm2": str((SIMULATION_DIR / "PADecision_Prompt.md").relative_to(ROOT_DIR)),
            "few_shot": str((SIMULATION_DIR / "PADecision_FewShot.md").relative_to(ROOT_DIR)),
        },
        "output_files": dict(output_files),
        "notes": {"diary_entries_are_simulation_artifacts": True},
    }


def _write_simulation_run_manifest(
    manifest_path: Path,
    *,
    config: FullSimulationConfig,
    run_id: str,
    run_status: str,
    output_files: Mapping[str, str],
    state_assessment_call_count: int,
    state_assessment_dry_run_count: int,
    error: BaseException | None = None,
) -> Path:
    return _write_json(
        manifest_path,
        _build_simulation_run_manifest(
            config=config,
            run_id=run_id,
            run_status=run_status,
            output_files=output_files,
            state_assessment_call_count=state_assessment_call_count,
            state_assessment_dry_run_count=state_assessment_dry_run_count,
            error=error,
        ),
    )


def run_full_simulation(config: FullSimulationConfig) -> dict[str, Any]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    daily_log_path = config.daily_log_path or config.output_dir / "daily_decision_log.csv"
    longitudinal_path = config.output_dir / "longitudinal_constructs.csv"
    contexts_compact_path = config.output_dir / "contexts_compact.json"
    persona_metadata_path = config.output_dir / "persona_metadata.json"
    pipeline_daily_log_path = config.output_dir / "pipeline_closed_loop_daily_log.csv"
    resource_usage_path = config.output_dir / RESOURCE_USAGE_FILENAME
    manifest_path = config.output_dir / SIMULATION_RUN_MANIFEST_FILENAME

    # Avoid appending to stale run outputs for deterministic reruns in the same directory.
    for csv_path in (daily_log_path, longitudinal_path, pipeline_daily_log_path):
        if csv_path.exists():
            csv_path.unlink()

    run_config_payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "n_personas": config.n_personas,
        "n_days": config.n_days,
        "start_date": config.start_date.isoformat(),
        "base_seed": config.base_seed,
        "output_dir": str(config.output_dir),
        "model": config.model,
        "temperature": config.temperature,
        "top_p": config.top_p,
        "llm_seed": config.llm_seed,
        "llm1_max_tokens": config.llm1_max_tokens,
        "llm2_max_tokens": config.llm2_max_tokens,
        "state_assessment_max_tokens": config.state_assessment_max_tokens,
        "state_assessment_json_mode_enabled": config.state_assessment_json_mode,
        "dry_run": config.dry_run,
        "include_full_hourly_context": config.include_full_hourly_context,
        "daily_log_path": str(daily_log_path),
        "resource_usage_path": str(resource_usage_path),
        "simulation_run_manifest_path": str(manifest_path),
        "enable_resource_tracking": config.enable_resource_tracking,
        "enable_codecarbon": config.enable_codecarbon,
    }
    _write_json(config.output_dir / "run_config.json", run_config_payload)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output_files = _known_output_files(
        daily_log_path=daily_log_path,
        longitudinal_path=longitudinal_path,
        contexts_compact_path=contexts_compact_path,
        persona_metadata_path=persona_metadata_path,
        pipeline_daily_log_path=pipeline_daily_log_path,
        resource_usage_path=resource_usage_path,
        manifest_path=manifest_path,
        output_dir=config.output_dir,
    )
    run_status = "success"
    run_error: BaseException | None = None
    trace_payload: dict[str, Any] | None = None
    records: list[dict[str, Any]] = []
    state_assessment_call_count = 0
    state_assessment_dry_run_count = 0
    resource_tracker = ResourceUsageEngine(
        resource_log_path=resource_usage_path,
        enable_tracking=config.enable_resource_tracking,
        enable_codecarbon=config.enable_codecarbon,
        stage="full_pa_simulation",
        run_label=f"full_pa_simulation_{config.n_personas}p_{config.n_days}d",
        run_id=run_id,
    )
    run_started = time.perf_counter()
    resource_tracker.start_run()

    try:
        behavior_system_prompt = "DRY RUN BEHAVIOR PROMPT" if config.dry_run else load_behavior_probability_prompt()
        pa_decision_system_prompt = "DRY RUN PA DECISION PROMPT" if config.dry_run else load_pa_decision_prompt()
        state_assessment_prompt = load_state_assessment_prompt()

        persona_states = _build_persona_states(config)
        global_environment_by_date = build_global_environment_by_date(config)
        persona_metadata = {
            "personas": [
                {
                    "persona_id": state.persona_id,
                    "seed": int(state.seed),
                    "psychological_seed": int(state.psychological_seed),
                    "input_parameters": dict(state.input_parameters),
                    "poi_distances_km": dict(state.poi_distances_km),
                    "selected_schedule_parameters": dict(state.selected_schedule_parameters),
                }
                for state in persona_states
            ]
        }
        _write_json(persona_metadata_path, persona_metadata)
        start_day_offset = min(int(config.start_date.day) - 1, 29)
        compact_contexts: list[dict[str, Any]] = []
        previous_diary_entries_by_persona: dict[str, list[dict[str, Any]]] = {
            state.persona_id: [] for state in persona_states
        }

        for state in persona_states:
            for day_index in range(config.n_days):
                calendar_date = config.start_date + timedelta(days=day_index)
                llm_context, _diagnostic_context = build_llm_ready_context_for_day(
                    state,
                    day_index=day_index,
                    calendar_date=calendar_date,
                    start_day_offset=start_day_offset,
                    global_hourly_environment=global_environment_by_date[
                        calendar_date.isoformat()
                    ],
                )
                compact_contexts.append(llm_context)
                constructs_before = _extract_constructs(state.psychological_state)
                planned_activity_for_day = _json_ready(
                    planned_physical_activity_from_schedule(llm_context["hourly_context_24h"])
                )
                per_day_output_dir = (
                    config.output_dir
                    / "llm_outputs"
                    / state.persona_id
                    / f"day_{day_index:03d}"
                )

                pipeline_record = _run_pipeline(
                    llm_context,
                    planned_activity_for_day=planned_activity_for_day,
                    config=config,
                    output_dir=per_day_output_dir,
                    pipeline_daily_log_path=pipeline_daily_log_path,
                    behavior_system_prompt=behavior_system_prompt,
                    pa_decision_system_prompt=pa_decision_system_prompt,
                    resource_tracker=resource_tracker,
                )
                closed_loop_update = dict(pipeline_record["closed_loop_update"])
                previous_diary_entries = previous_diary_entries_by_persona[state.persona_id]
                assessment = run_state_assessment(
                    persona_id=state.persona_id,
                    day_index=day_index,
                    previous_normalized_values=constructs_before,
                    current_simulated_diary_entry=str(
                        pipeline_record["pa_decision"]["diary_entry"]
                    ),
                    previous_diary_entries=previous_diary_entries,
                    prompt_template=state_assessment_prompt,
                    dry_run=config.dry_run,
                    model=config.model,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    llm_seed=config.llm_seed,
                    max_tokens=config.state_assessment_max_tokens,
                    output_dir=per_day_output_dir,
                    json_mode=config.state_assessment_json_mode,
                )
                state_assessment_call_count += 1
                if assessment["state_assessment_mode"] == "dry_run_mock":
                    state_assessment_dry_run_count += 1
                assessment_usage = dict(assessment.pop("_resource_usage"))
                resource_tracker.log_paper(
                    paper_id=f"state_assessment_persona_{state.persona_id}_day_{day_index}",
                    stage="state_assessment",
                    prompt_tokens=int(assessment_usage.get("prompt_tokens") or 0),
                    response_tokens=int(assessment_usage.get("response_tokens") or 0),
                    tokens_total=int(assessment_usage.get("tokens_total") or 0),
                    prompt_tokens_source=str(
                        assessment_usage.get("token_source") or "unavailable"
                    ),
                    response_tokens_source=str(
                        assessment_usage.get("token_source") or "unavailable"
                    ),
                    embedding_tokens_source="unavailable",
                    token_source=str(assessment_usage.get("token_source") or "unavailable"),
                    paper_seconds=float(assessment_usage.get("paper_seconds") or 0.0),
                )
                assessment_output_path = _write_json(
                    per_day_output_dir / f"state_assessment_{state.persona_id}.json",
                    {
                        key: value
                        for key, value in assessment.items()
                        if key != "rendered_prompt"
                    },
                )
                constructs_after = {
                    str(key): round(float(value), 6)
                    for key, value in assessment[
                        "psychological_construct_values_after_state_assessment"
                    ].items()
                }
                closed_loop_update["updated_psychological_constructs"] = dict(constructs_after)
                closed_loop_update["state_assessment_target_constructs"] = dict(
                    assessment["state_assessment_target_values_normalized"]
                )
                activity_done = bool(closed_loop_update.get("activity_done"))
                decision_label = str(pipeline_record["pa_decision"]["decision_label"])
                if activity_done != activity_performed_for_decision_label(decision_label):
                    raise ValueError("Closed-loop activity_done is inconsistent with the PA decision label.")

                record: dict[str, Any] = {
                    "persona_id": state.persona_id,
                    "seed": int(state.seed),
                    "psychological_seed": int(state.psychological_seed),
                    "day_index": int(day_index),
                    "calendar_date": calendar_date.isoformat(),
                    "phase": llm_context.get("phase"),
                    "weekday": llm_context.get("weekday"),
                    "psychological_constructs_before_update": constructs_before,
                    "state_assessment_enabled": assessment["state_assessment_enabled"],
                    "state_assessment_mode": assessment["state_assessment_mode"],
                    "psychological_construct_values_before_state_assessment": assessment[
                        "psychological_construct_values_before_state_assessment"
                    ],
                    "state_assessment_item_scores": assessment[
                        "state_assessment_item_scores"
                    ],
                    "state_assessment_mean_scores_raw": assessment[
                        "state_assessment_mean_scores_raw"
                    ],
                    "state_assessment_mean_scores_normalized": assessment[
                        "state_assessment_mean_scores_normalized"
                    ],
                    "state_assessment_target_values_normalized": assessment[
                        "state_assessment_target_values_normalized"
                    ],
                    "psychological_construct_update_strategy": assessment[
                        "psychological_construct_update_strategy"
                    ],
                    "psychological_construct_update_alpha": assessment[
                        "psychological_construct_update_alpha"
                    ],
                    "psychological_construct_update_max_daily_change": assessment[
                        "psychological_construct_update_max_daily_change"
                    ],
                    "psychological_construct_update_delta_proposed": assessment[
                        "psychological_construct_update_delta_proposed"
                    ],
                    "psychological_construct_update_delta_applied": assessment[
                        "psychological_construct_update_delta_applied"
                    ],
                    "psychological_construct_values_after_smoothed_update": constructs_after,
                    "psychological_construct_values_after_state_assessment": constructs_after,
                    "previous_diary_entries_count": assessment[
                        "previous_diary_entries_count"
                    ],
                    "previous_diary_entries_context_used": assessment[
                        "previous_diary_entries_context_used"
                    ],
                    "behavior_policy": dict(pipeline_record["behavior_policy"]),
                    "behavior_policy_raw": dict(pipeline_record["behavior_policy_raw"]),
                    "decision_context_has_planned_pa": bool(
                        pipeline_record["decision_context_has_planned_pa"]
                    ),
                    "active_decision_probabilities": dict(
                        pipeline_record["active_decision_probabilities"]
                    ),
                    "sampled_decision_label": pipeline_record["sampled_decision_label"],
                    "sampled_decision_probability": pipeline_record[
                        "sampled_decision_probability"
                    ],
                    "decision_sampling_seed": pipeline_record["decision_sampling_seed"],
                    "decision_sampling_random_value": pipeline_record[
                        "decision_sampling_random_value"
                    ],
                    "planned_physical_activity": planned_activity_for_day,
                    "was_physical_activity_planned_today": planned_activity_for_day is not None,
                    "persona_metadata": {
                        "input_parameters": dict(state.input_parameters),
                        "poi_distances_km": dict(state.poi_distances_km),
                        "selected_schedule_parameters": dict(state.selected_schedule_parameters),
                    },
                    "pa_decision": dict(pipeline_record["pa_decision"]),
                    "closed_loop_update": closed_loop_update,
                    "psychological_constructs_after_update": constructs_after,
                    "context_summary": _context_summary(llm_context),
                    "output_files": dict(pipeline_record.get("output_files", {})),
                }
                record["output_files"]["state_assessment"] = str(assessment_output_path)
                if config.include_full_hourly_context:
                    record["hourly_context_24h"] = llm_context["hourly_context_24h"]

                record = _json_ready(record)
                records.append(record)
                _write_daily_log_row(daily_log_path, record)
                _write_longitudinal_construct_rows(longitudinal_path, record)

                state.psychological_state = _psychological_state_with_updated_constructs(
                    state.psychological_state,
                    constructs_after,
                )
                previous_diary_entries.append(
                    {
                        "day_index": int(day_index),
                        "diary_entry": str(pipeline_record["pa_decision"]["diary_entry"]),
                        "physical_activity_decision": decision_label,
                        "planned_physical_activity": planned_activity_for_day,
                    }
                )

        contexts_payload = {
            "simulation_metadata": {
                "n_personas": config.n_personas,
                "n_days": config.n_days,
                "n_contexts": len(compact_contexts),
                "start_date": config.start_date.isoformat(),
                "base_seed": config.base_seed,
                "dry_run": config.dry_run,
                "persona_metadata_file": str(persona_metadata_path),
                "state_assessment_call_count": state_assessment_call_count,
            },
            "llm_contexts": compact_contexts,
        }
        _write_json(contexts_compact_path, contexts_payload)

        trace_payload = {
            "metadata": {
                "n_personas": config.n_personas,
                "n_days": config.n_days,
                "n_records": len(records),
                "start_date": config.start_date.isoformat(),
                "base_seed": config.base_seed,
                "dry_run": config.dry_run,
                "persona_metadata_file": str(persona_metadata_path),
            },
            "records": records,
        }
        _write_json(config.output_dir / "full_simulation_trace.json", trace_payload)
    except Exception as exc:
        run_status = "failed"
        run_error = exc
        raise
    finally:
        try:
            _write_simulation_run_manifest(
                manifest_path,
                config=config,
                run_id=run_id,
                run_status=run_status,
                output_files=output_files,
                state_assessment_call_count=state_assessment_call_count,
                state_assessment_dry_run_count=state_assessment_dry_run_count,
                error=run_error,
            )
            resource_tracker.stop_run(
                total_runtime_seconds=time.perf_counter() - run_started,
                paper_count=len(records) * 3,
                run_status=run_status,
                error_type=type(run_error).__name__ if run_error is not None else None,
                error_message=str(run_error)[:500] if run_error is not None else None,
                output_files=output_files,
            )
        except Exception as finalization_exc:
            if run_error is None:
                raise
            print(
                "Resource usage/manifest finalization failed after simulation error: "
                f"{type(finalization_exc).__name__}: {finalization_exc}",
                file=sys.stderr,
                flush=True,
            )

    if trace_payload is None:
        raise RuntimeError("full simulation completed without a trace payload")
    return _json_ready(trace_payload)


def main(argv: Sequence[str] | None = None) -> None:
    config = config_from_args(parse_args(argv))
    trace_payload = run_full_simulation(config)
    print(
        json.dumps(
            {
                "output_dir": str(config.output_dir),
                "n_records": trace_payload["metadata"]["n_records"],
                "full_simulation_trace": str(config.output_dir / "full_simulation_trace.json"),
                "daily_decision_log": str(config.daily_log_path or config.output_dir / "daily_decision_log.csv"),
                "longitudinal_constructs": str(config.output_dir / "longitudinal_constructs.csv"),
                "contexts_compact": str(config.output_dir / "contexts_compact.json"),
                "persona_metadata": str(config.output_dir / "persona_metadata.json"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
