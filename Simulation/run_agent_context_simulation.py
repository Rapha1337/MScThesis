from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

SIMULATION_DIR = Path(__file__).resolve().parent
if str(SIMULATION_DIR) not in sys.path:
    sys.path.append(str(SIMULATION_DIR))

from agent_context_export import export_day_contexts_to_json, generate_day_contexts_for_personas

DEFAULT_OUTPUT_PATH = SIMULATION_DIR / "output" / "agent_day_contexts.json"

LLM_HOURLY_FIELDS: tuple[str, ...] = (
    "hour",
    "activity_type",
    "subtype",
    "current_location",
    "active_constraints",
    "energy_level",
    "energy_category",
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


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate persona day contexts for simulation runs as JSON.")
    parser.add_argument("--n-personas", type=int, required=True)
    parser.add_argument("--base-seed", type=int, required=True)
    parser.add_argument("--day-index", type=int, required=True)
    parser.add_argument("--fitness-hours-week", type=float, required=True)
    parser.add_argument("--social-hours-week", type=float, required=True)
    parser.add_argument("--work-hours-week", type=float, required=True)
    parser.add_argument("--carework-hours-week", type=float, required=True)
    parser.add_argument("--workplace-distance-km", type=float, required=True)
    parser.add_argument("--indoor-activity-distance-km", type=float, required=True)
    parser.add_argument("--outdoor-activity-distance-km", type=float, required=True)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args(argv)


def _input_parameters_from_args(args: argparse.Namespace) -> dict[str, float]:
    return {
        "fitness_hours_week": args.fitness_hours_week,
        "social_hours_week": args.social_hours_week,
        "work_hours_week": args.work_hours_week,
        "carework_hours_week": args.carework_hours_week,
        "workplace_distance_km": args.workplace_distance_km,
        "indoor_activity_distance_km": args.indoor_activity_distance_km,
        "outdoor_activity_distance_km": args.outdoor_activity_distance_km,
    }


def _compact_llm_poi_accessibility(hourly_entry: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    source_poi = hourly_entry.get("poi_accessibility")
    if not isinstance(source_poi, Mapping):
        return {target: {"distance_km": None, "travel_times_min": {}} for target in LLM_POI_TARGETS}

    poi_accessibility: dict[str, dict[str, Any]] = {}
    for target in LLM_POI_TARGETS:
        target_payload = source_poi.get(target)
        if not isinstance(target_payload, Mapping):
            poi_accessibility[target] = {"distance_km": None, "travel_times_min": {}}
            continue
        travel_times = target_payload.get("travel_times_min")
        poi_accessibility[target] = {
            "distance_km": target_payload.get("distance_km"),
            "travel_times_min": dict(travel_times) if isinstance(travel_times, Mapping) else {},
        }
    return poi_accessibility


def _llm_hourly_context_entry(hourly_entry: Mapping[str, Any], environment_entry: Mapping[str, Any]) -> dict[str, Any]:
    entry = {field: hourly_entry.get(field) for field in LLM_HOURLY_FIELDS}
    entry["poi_accessibility"] = _compact_llm_poi_accessibility(hourly_entry)

    if "weather_condition" in environment_entry:
        entry["weather_condition"] = environment_entry["weather_condition"]
    elif "weather_condition" in hourly_entry:
        entry["weather_condition"] = hourly_entry["weather_condition"]

    if "absolute_hour" in environment_entry:
        entry["absolute_hour"] = environment_entry["absolute_hour"]
    elif "absolute_hour" in hourly_entry:
        entry["absolute_hour"] = hourly_entry["absolute_hour"]

    return entry


def _build_llm_context(persona_payload: Mapping[str, Any], day_index: int) -> dict[str, Any]:
    day_context = persona_payload["day_context"]
    agent_context = persona_payload.get("agent_context", {})
    hourly_context = list(day_context.get("hourly_context_24h", []))
    hourly_environment = list(day_context.get("hourly_environment_24h", []))

    if len(hourly_context) != 24:
        raise ValueError("day_context.hourly_context_24h must contain exactly 24 entries.")

    llm_hourly_context: list[dict[str, Any]] = []
    for index, hourly_entry in enumerate(hourly_context):
        environment_entry = hourly_environment[index] if index < len(hourly_environment) else {}
        llm_hourly_context.append(_llm_hourly_context_entry(hourly_entry, environment_entry))

    return {
        "persona_id": persona_payload["persona_id"],
        "seed": persona_payload["seed"],
        "day_index": int(day_index),
        "phase": day_context.get("phase"),
        "weekday": day_context.get("weekday"),
        "task_description": (
            "Use the compact 24-hour schedule, energy, weather, daylight, constraints, "
            "location, and POI-accessibility context to reason about this persona's day."
        ),
        "input_parameters": persona_payload.get("input_parameters", {}),
        "selected_schedule_parameters": agent_context.get("schedule_parameters", {}),
        "hourly_context_24h": llm_hourly_context,
    }


def build_llm_ready_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Convert the diagnostic day-context payload into compact LLM-ready JSON."""
    metadata = dict(payload["simulation_metadata"])
    day_index = int(metadata["day_index"])
    return {
        "simulation_metadata": metadata,
        "llm_contexts": [_build_llm_context(persona, day_index) for persona in payload.get("personas", [])],
    }


def _print_summary(payload: dict, output_path: Path, export_succeeded: bool) -> None:
    metadata = payload["simulation_metadata"]
    persona_ids = [str(context["persona_id"]) for context in payload["llm_contexts"]]

    print(f"output path: {output_path}")
    print(f"n personas: {metadata['n_personas']}")
    print(f"base_seed: {metadata['base_seed']}")
    print(f"day_index: {metadata['day_index']}")
    print(f"persona IDs: {', '.join(persona_ids)}")
    for context in payload["llm_contexts"]:
        hourly_count = len(context.get("hourly_context_24h", []))
        print(f"{context['persona_id']} phase: {context.get('phase')}")
        print(f"{context['persona_id']} hourly_context_24h entries: {hourly_count}")
    print(f"JSON export success: {str(export_succeeded).lower()}")


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    diagnostic_payload = generate_day_contexts_for_personas(
        n_personas=args.n_personas,
        base_seed=args.base_seed,
        day_index=args.day_index,
        input_parameters=_input_parameters_from_args(args),
    )
    payload = build_llm_ready_payload(diagnostic_payload)
    output_path = export_day_contexts_to_json(payload, args.output_path)
    json.dumps(payload)
    _print_summary(payload=payload, output_path=output_path, export_succeeded=output_path.exists())


if __name__ == "__main__":
    main()
