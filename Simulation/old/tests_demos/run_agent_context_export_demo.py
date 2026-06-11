from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from agent_context_export import export_day_contexts_to_json, generate_day_contexts_for_personas


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate demo persona day contexts as JSON.")
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
    parser.add_argument("--output-path", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_parameters = {
        "fitness_hours_week": args.fitness_hours_week,
        "social_hours_week": args.social_hours_week,
        "work_hours_week": args.work_hours_week,
        "carework_hours_week": args.carework_hours_week,
        "workplace_distance_km": args.workplace_distance_km,
        "indoor_activity_distance_km": args.indoor_activity_distance_km,
        "outdoor_activity_distance_km": args.outdoor_activity_distance_km,
    }

    payload = generate_day_contexts_for_personas(
        n_personas=args.n_personas,
        base_seed=args.base_seed,
        day_index=args.day_index,
        input_parameters=input_parameters,
    )
    output_path = export_day_contexts_to_json(payload, args.output_path)
    json.dumps(payload)

    persona_ids = [persona["persona_id"] for persona in payload["personas"]]
    print(f"output path: {output_path}")
    print(f"n personas: {payload['simulation_metadata']['n_personas']}")
    print(f"persona IDs: {', '.join(persona_ids)}")
    print(f"day_index: {payload['simulation_metadata']['day_index']}")
    for persona in payload["personas"]:
        day_context = persona["day_context"]
        agent_context = persona["agent_context"]
        hourly_count = len(day_context.get("hourly_context_24h", []))
        print(f"{persona['persona_id']} phase: {day_context.get('phase')}")
        print(f"{persona['persona_id']} hourly_context_24h entries: {hourly_count}")
        print(f"{persona['persona_id']} wired parameters: {agent_context.get('wired_parameters', {})}")
        print(
            f"{persona['persona_id']} unsupported_or_partially_wired_parameters: "
            f"{agent_context.get('unsupported_or_partially_wired_parameters', {})}"
        )
    print("JSON serialization succeeded: true")


if __name__ == "__main__":
    main()
