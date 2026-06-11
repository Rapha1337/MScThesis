from __future__ import annotations

import argparse
import csv
import json
import random
import sys
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
from run_llm_pa_decision import (  # noqa: E402
    LLM1_MAX_TOKENS,
    LLM2_MAX_TOKENS,
    MODEL_NAME,
    TEMPERATURE,
    SUCCESSFUL_PA_DECISION_LABELS,
    load_behavior_probability_prompt,
    load_pa_decision_prompt,
    run_pipeline_for_context,
)
from schedule_model_student import YearPhase  # noqa: E402
from simulation_runner import SimulationRunner  # noqa: E402

DEFAULT_OUTPUT_DIR = SIMULATION_DIR / "output" / "full_pa_simulation"
PSYCHOLOGICAL_SEED_OFFSET = 10_000_019

BEHAVIOR_POLICY_DRY_RUN: dict[str, float] = {
    "do_planned_activity": 0.25,
    "adapt_activity": 0.20,
    "postpone_activity": 0.15,
    "skip_activity": 0.15,
    "extra_activity": 0.10,
    "app_ignored": 0.15,
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

DAILY_DECISION_LOG_COLUMNS: tuple[str, ...] = (
    "persona_id",
    "day_index",
    "calendar_date",
    "decision_code",
    "decision_label",
    "activity_done",
    "planned_activity_for_day",
    "planned_activity_next_day",
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
    daily_log_path: Path | None = None


@dataclass
class PersonaRuntimeState:
    persona_id: str
    seed: int
    psychological_seed: int
    input_parameters: dict[str, Any]
    selected_schedule_parameters: dict[str, Any]
    runner: SimulationRunner
    psychological_state: dict[str, Any]
    planned_activity_for_day: Any | None = None


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
    parser.add_argument("--llm1-max-tokens", type=int, default=LLM1_MAX_TOKENS)
    parser.add_argument("--llm2-max-tokens", type=int, default=LLM2_MAX_TOKENS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--include-full-hourly-context", action="store_true")
    parser.add_argument("--daily-log-path", type=Path, default=None)
    return parser.parse_args(argv)


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
        llm1_max_tokens=int(args.llm1_max_tokens),
        llm2_max_tokens=int(args.llm2_max_tokens),
        dry_run=bool(args.dry_run),
        include_full_hourly_context=bool(args.include_full_hourly_context),
        daily_log_path=Path(args.daily_log_path) if args.daily_log_path else None,
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
    start_month = int(config.start_date.month)
    start_day_offset = min(int(config.start_date.day) - 1, 29)
    horizon_hours = max(24 * 365, 24 * (start_day_offset + config.n_days + 1))

    states: list[PersonaRuntimeState] = []
    for idx in range(config.n_personas):
        persona_seed = rng.randint(0, 2**31 - 1)
        persona_id = f"StudentPersona_{idx + 1:02d}"
        input_parameters = dict(normalized_inputs)
        input_parameters["day_index"] = 0
        persona = _student_parameters_from_inputs(persona_id, input_parameters)
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
                input_parameters=_json_ready(persona.input_parameters()),
                selected_schedule_parameters=_json_ready(_schedule_parameters_payload(persona, persona_seed)),
                runner=runner,
                psychological_state=build_psychological_state(psychological_seed),
            )
        )
    return states


def build_llm_ready_context_for_day(
    state: PersonaRuntimeState,
    *,
    day_index: int,
    calendar_date: date,
    start_day_offset: int,
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

    llm_context = {
        "persona_id": state.persona_id,
        "seed": int(state.seed),
        "day_index": int(day_index),
        "calendar_date": calendar_date.isoformat(),
        "phase": diagnostic_context.get("phase"),
        "weekday": diagnostic_context.get("weekday"),
        "psychological_state": dict(state.psychological_state),
        "hourly_context_24h": [_compact_hourly_entry(entry) for entry in hourly_context],
    }
    return _json_ready(llm_context), _json_ready(diagnostic_context)


def _dry_behavior_runner(agent_context: Mapping[str, Any], **kwargs: Any) -> dict[str, dict[str, float]]:
    del kwargs
    # Assert the longitudinal state machine is feeding constructs into LLM1 input.
    if not _extract_constructs(agent_context.get("psychological_state", {})):
        raise ValueError("Dry-run behavior runner requires psychological constructs.")
    return {"probabilities": dict(BEHAVIOR_POLICY_DRY_RUN)}


def _dry_pa_decision_runner(pa_decision_input: Mapping[str, Any], **kwargs: Any) -> dict[str, Any]:
    del kwargs
    planned_activity = pa_decision_input.get("planned_activity")
    if planned_activity is None:
        decision_code = 1
        decision_label = "done_as_planned"
        rationale = "Dry-run day without a prior plan; simulated successful activity."
        diary = "Dry-run: I completed a simple movement activity today."
    else:
        decision_code = 3
        decision_label = "adapted"
        rationale = "Dry-run day with a carried-over plan; simulated adapted completion."
        diary = "Dry-run: I adapted yesterday's plan and still moved today."

    return {
        "persona_id": str(pa_decision_input["persona_id"]),
        "day_index": int(pa_decision_input["day_index"]),
        "decision_code": decision_code,
        "decision_label": decision_label,
        "rationale_short": rationale,
        "diary_entry": diary,
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
        "planned_activity_for_day": _json_log_value(record.get("planned_activity_for_day")),
        "planned_activity_next_day": _json_log_value(closed_loop.get("planned_activity_next_day")),
        "behavior_policy": _json_log_value(record.get("behavior_policy")),
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
    activity_done = bool(record["closed_loop_update"]["activity_done"])
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
        llm1_max_tokens=config.llm1_max_tokens,
        llm2_max_tokens=config.llm2_max_tokens,
        output_dir=output_dir,
        daily_log_path=pipeline_daily_log_path,
        **kwargs,
    )


def run_full_simulation(config: FullSimulationConfig) -> dict[str, Any]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    daily_log_path = config.daily_log_path or config.output_dir / "daily_decision_log.csv"
    longitudinal_path = config.output_dir / "longitudinal_constructs.csv"
    contexts_compact_path = config.output_dir / "contexts_compact.json"
    persona_metadata_path = config.output_dir / "persona_metadata.json"
    pipeline_daily_log_path = config.output_dir / "pipeline_closed_loop_daily_log.csv"

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
        "llm1_max_tokens": config.llm1_max_tokens,
        "llm2_max_tokens": config.llm2_max_tokens,
        "dry_run": config.dry_run,
        "include_full_hourly_context": config.include_full_hourly_context,
        "daily_log_path": str(daily_log_path),
    }
    _write_json(config.output_dir / "run_config.json", run_config_payload)

    behavior_system_prompt = "DRY RUN BEHAVIOR PROMPT" if config.dry_run else load_behavior_probability_prompt()
    pa_decision_system_prompt = "DRY RUN PA DECISION PROMPT" if config.dry_run else load_pa_decision_prompt()

    persona_states = _build_persona_states(config)
    persona_metadata = {
        "personas": [
            {
                "persona_id": state.persona_id,
                "seed": int(state.seed),
                "psychological_seed": int(state.psychological_seed),
                "input_parameters": dict(state.input_parameters),
                "selected_schedule_parameters": dict(state.selected_schedule_parameters),
            }
            for state in persona_states
        ]
    }
    _write_json(persona_metadata_path, persona_metadata)
    start_day_offset = min(int(config.start_date.day) - 1, 29)
    records: list[dict[str, Any]] = []
    compact_contexts: list[dict[str, Any]] = []

    for state in persona_states:
        for day_index in range(config.n_days):
            calendar_date = config.start_date + timedelta(days=day_index)
            llm_context, _diagnostic_context = build_llm_ready_context_for_day(
                state,
                day_index=day_index,
                calendar_date=calendar_date,
                start_day_offset=start_day_offset,
            )
            compact_contexts.append(llm_context)
            constructs_before = _extract_constructs(state.psychological_state)
            planned_activity_for_day = _json_ready(state.planned_activity_for_day)
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
            )
            closed_loop_update = dict(pipeline_record["closed_loop_update"])
            constructs_after = {
                str(key): round(min(1.0, max(0.0, float(value))), 3)
                for key, value in closed_loop_update["updated_psychological_constructs"].items()
            }
            closed_loop_update["updated_psychological_constructs"] = dict(constructs_after)
            activity_done = bool(closed_loop_update.get("activity_done"))
            decision_label = str(pipeline_record["pa_decision"]["decision_label"])
            if activity_done != (decision_label in SUCCESSFUL_PA_DECISION_LABELS):
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
                "behavior_policy": dict(pipeline_record["behavior_policy"]),
                "planned_activity_for_day": planned_activity_for_day,
                "persona_metadata": {
                    "input_parameters": dict(state.input_parameters),
                    "selected_schedule_parameters": dict(state.selected_schedule_parameters),
                },
                "pa_decision": dict(pipeline_record["pa_decision"]),
                "closed_loop_update": closed_loop_update,
                "psychological_constructs_after_update": constructs_after,
                "context_summary": _context_summary(llm_context),
                "output_files": dict(pipeline_record.get("output_files", {})),
            }
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
            state.planned_activity_for_day = closed_loop_update["planned_activity_next_day"]

    contexts_payload = {
        "simulation_metadata": {
            "n_personas": config.n_personas,
            "n_days": config.n_days,
            "n_contexts": len(compact_contexts),
            "start_date": config.start_date.isoformat(),
            "base_seed": config.base_seed,
            "dry_run": config.dry_run,
            "persona_metadata_file": str(persona_metadata_path),
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
