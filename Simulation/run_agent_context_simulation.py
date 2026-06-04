from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

SIMULATION_DIR = Path(__file__).resolve().parent
if str(SIMULATION_DIR) not in sys.path:
    sys.path.append(str(SIMULATION_DIR))

from agent_context_export import export_day_contexts_to_json, generate_day_contexts_for_personas

DEFAULT_OUTPUT_PATH = SIMULATION_DIR / "output" / "agent_day_contexts.json"


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


def _print_summary(payload: dict, output_path: Path, export_succeeded: bool) -> None:
    metadata = payload["simulation_metadata"]
    persona_ids = [str(persona["persona_id"]) for persona in payload["personas"]]

    print(f"output path: {output_path}")
    print(f"n personas: {metadata['n_personas']}")
    print(f"base_seed: {metadata['base_seed']}")
    print(f"day_index: {metadata['day_index']}")
    print(f"persona IDs: {', '.join(persona_ids)}")
    for persona in payload["personas"]:
        day_context = persona["day_context"]
        hourly_count = len(day_context.get("hourly_context_24h", []))
        print(f"{persona['persona_id']} phase: {day_context.get('phase')}")
        print(f"{persona['persona_id']} hourly_context_24h entries: {hourly_count}")
    print(f"JSON export success: {str(export_succeeded).lower()}")


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    payload = generate_day_contexts_for_personas(
        n_personas=args.n_personas,
        base_seed=args.base_seed,
        day_index=args.day_index,
        input_parameters=_input_parameters_from_args(args),
    )
    output_path = export_day_contexts_to_json(payload, args.output_path)
    json.dumps(payload)
    _print_summary(payload=payload, output_path=output_path, export_succeeded=output_path.exists())


if __name__ == "__main__":
    main()
