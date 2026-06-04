from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from accessibility_model import ACCESSIBILITY_CATEGORIES, build_accessibility_model


def build_demo_model():
    return build_accessibility_model(
        workplace_distance_km=3.0,
        indoor_activity_distance_km=1.2,
        outdoor_activity_distance_km=0.6,
    )


def build_sample_24h_schedule() -> list[dict[str, object]]:
    schedule: list[dict[str, object]] = []
    for hour in range(24):
        if hour < 7 or hour >= 23:
            schedule.append({"hour": hour, "activity_type": "sleep", "subtype": "night_sleep"})
        elif 9 <= hour < 17:
            schedule.append({"hour": hour, "activity_type": "work", "subtype": "paid_work"})
        elif hour == 18:
            schedule.append({"hour": hour, "activity_type": "physical_activity", "subtype": "gym"})
        elif hour == 20:
            schedule.append({"hour": hour, "activity_type": "physical_activity", "subtype": "outdoor_running"})
        elif hour in {7, 12, 19}:
            schedule.append({"hour": hour, "activity_type": "eat", "subtype": "meal"})
        else:
            schedule.append({"hour": hour, "activity_type": "downtime", "subtype": "open_time"})
    return schedule


def run_demo() -> None:
    model = build_demo_model()
    payload = model.to_dict()

    assert set(payload["categories"]) == set(ACCESSIBILITY_CATEGORIES)
    for category in ACCESSIBILITY_CATEGORIES:
        travel_times = payload["categories"][category]["travel_times_min"]
        assert set(travel_times) == {"walk", "bike", "car"}
        assert all(value is not None for value in travel_times.values())

    hourly_accessibility = model.build_hourly_accessibility(build_sample_24h_schedule())
    selected_hours = [
        entry
        for entry in hourly_accessibility
        if entry["hour"] in {6, 10, 18, 20}
    ]

    print("Stable survey-distance accessibility model:")
    print(model.to_json(indent=2))
    print("\nSelected hourly location-aware accessibility examples:")
    print(json.dumps(selected_hours, indent=2, sort_keys=True))


if __name__ == "__main__":
    run_demo()
