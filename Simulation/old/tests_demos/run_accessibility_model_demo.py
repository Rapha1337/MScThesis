from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from accessibility_model import ACCESSIBILITY_CATEGORIES, build_accessibility_model
from persona_wrappers import StudentHoursWrapper
from schedule_model_student import YearPhase
from simulation_runner import SimulationRunner


class DemoEnv:
    def reset(self, seed=None, options=None):
        del options
        return None, {"seed": seed, "hour": 9, "state": "reset"}

    def step(self, action: int = 0):
        return None, 0.0, False, False, {"action": action, "hour": 10, "state": "stepped"}


def build_demo_model():
    return build_accessibility_model(
        workplace_distance_km=3.0,
        indoor_activity_distance_km=1.2,
        outdoor_activity_distance_km=0.6,
    )


def _selected_hours_with_transition(hourly_accessibility: list[dict[str, object]]) -> set[int]:
    selected_hours = {6, 10, 18, 20}
    for entry in hourly_accessibility:
        if entry["location_changed_from_previous_hour"]:
            hour = entry.get("hour")
            if isinstance(hour, int):
                selected_hours.update({max(0, hour - 1), hour})
            break
    return selected_hours


def run_demo() -> None:
    model = build_demo_model()
    payload = model.to_dict()

    assert set(payload["categories"]) == set(ACCESSIBILITY_CATEGORIES)
    for category in ACCESSIBILITY_CATEGORIES:
        travel_times = payload["categories"][category]["travel_times_min"]
        assert set(travel_times) == {"walk", "bike", "car"}
        assert all(value is not None for value in travel_times.values())

    persona = StudentHoursWrapper.from_zve_student_generic(name="accessibility_demo_student")
    runner = SimulationRunner(
        persona=persona,
        phase=YearPhase.SEMESTER,
        env=DemoEnv(),
        seed=37,
        use_year_structure=True,
        accessibility_model=model,
    )

    contexts = [runner.get_day_context(weekday=weekday) for weekday in range(7)]
    context = next(
        (candidate for candidate in contexts if any(
            entry["location_changed_from_previous_hour"]
            for entry in candidate["hourly_accessibility_24h"]
        )),
        contexts[0],
    )
    hourly_accessibility = context["hourly_accessibility_24h"]
    selected_hours = [
        entry
        for entry in hourly_accessibility
        if entry["hour"] in _selected_hours_with_transition(hourly_accessibility)
    ]

    transitions = [
        {
            "hour": entry["hour"],
            "from": entry["previous_location"],
            "to": entry["current_location"],
            "travel_from_previous_location": entry["travel_from_previous_location"],
        }
        for entry in hourly_accessibility
        if entry["location_changed_from_previous_hour"]
    ]

    print("Stable survey-distance accessibility model:")
    print(model.to_json(indent=2))
    print("\nSelected hourly location-aware accessibility from SimulationRunner day context:")
    print(json.dumps(selected_hours, indent=2, sort_keys=True))
    print("\nLocation transitions in generated/constrained SimulationRunner schedule:")
    print(json.dumps(transitions, indent=2, sort_keys=True))


if __name__ == "__main__":
    run_demo()
