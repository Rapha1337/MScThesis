from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from accessibility_model import build_accessibility_model
from agent_context import build_hourly_context_24h
from constraints.illness import AcuteIllnessConstraint
from constraints.manager import ConstraintManager
from persona_wrappers import StudentHoursWrapper
from schedule_model_student import YearPhase
from simulation_runner import SimulationRunner


class FakeEnvWithHourlyEnvironment:
    def reset(self, seed=None, options=None):
        del options
        return None, {"seed": seed, "hour": 9, "state": "reset"}

    def step(self, action: int = 0):
        return None, 0.0, False, False, {"action": action, "hour": 10, "state": "stepped"}

    def build_hourly_environment_24h(self, start_t: int | None = None):
        del start_t
        return [_environment_entry(hour) for hour in range(24)]


def _schedule_entry(hour: int, *, activity_type: str = "downtime", subtype: str = "open_time") -> dict[str, object]:
    return {
        "hour": hour,
        "activity_type": activity_type,
        "subtype": subtype,
        "flexibility": "flexible",
    }


def _accessibility_entry(hour: int) -> dict[str, object]:
    return {
        "hour": hour,
        "current_location": "home",
        "previous_location": None if hour == 0 else "home",
        "location_changed_from_previous_hour": False,
        "travel_from_previous_location": None
        if hour == 0
        else {
            "origin": "home",
            "destination": "home",
            "distance_km": 0.0,
            "travel_times_min": {"walk": 0.0, "bike": 0.0, "car": 0.0},
            "source": "same_location",
        },
        "accessibility": {
            "current_location": "home",
            "targets": {},
            "heuristic_note": "fixture",
        },
    }


def _energy_entry(hour: int) -> dict[str, object]:
    return {
        "hour": hour,
        "energy_level": 0.6,
        "energy_score": 0.6,
        "energy_category": "medium",
        "energy_effects": {"time_of_day_effect": 0.0},
        "drivers": {"time_of_day_effect": 0.0},
        "active_constraints": [],
    }


def _environment_entry(hour: int) -> dict[str, object]:
    return {
        "hour": hour,
        "month": 1,
        "season": "winter",
        "temperature_c": 1.0,
        "feels_like_c": 0.0,
        "precipitation_mm": 0.0,
        "is_wet": False,
        "weather_condition": "clear_night" if hour < 7 else "overcast",
        "sun_frac": 0.0,
        "is_daylight": False,
        "humidity_pct": 80.0,
        "wind_m_s": 2.0,
        "snow_cover": False,
    }


def _accessibility_model():
    return build_accessibility_model(
        workplace_distance_km=3.0,
        indoor_activity_distance_km=1.2,
        outdoor_activity_distance_km=0.6,
    )


def _runner_context(constraint_manager: ConstraintManager | None = None) -> dict:
    persona = StudentHoursWrapper.from_zve_student_generic(name="hourly_context_student")
    runner = SimulationRunner(
        persona=persona,
        phase=YearPhase.SEMESTER,
        env=FakeEnvWithHourlyEnvironment(),
        constraint_manager=constraint_manager,
        accessibility_model=_accessibility_model(),
        seed=37,
        use_year_structure=False,
    )
    return runner.get_day_context(weekday=1)


def test_simulation_runner_day_context_returns_merged_hourly_context() -> None:
    context = _runner_context()

    assert "persona_profile" in context
    assert context["persona_profile"] == {"source": "pending_cluster_analysis", "data": None}
    assert "hourly_context_24h" in context
    assert len(context["hourly_context_24h"]) == 24
    json.dumps(context)


def test_hourly_context_entries_include_schedule_accessibility_energy_and_environment_fields() -> None:
    context = _runner_context()
    required_fields = {
        "hour",
        "activity_type",
        "subtype",
        "flexibility",
        "current_location",
        "previous_location",
        "location_changed_from_previous_hour",
        "travel_from_previous_location",
        "accessibility_from_current_location",
        "energy_level",
        "energy_score",
        "energy_category",
        "energy_effects",
        "energy_drivers",
        "active_constraints",
        "month",
        "season",
        "temperature_c",
        "feels_like_c",
        "precipitation_mm",
        "is_wet",
        "weather_condition",
        "sun_frac",
        "is_daylight",
        "humidity_pct",
        "wind_m_s",
        "snow_cover",
    }

    assert all(required_fields.issubset(entry) for entry in context["hourly_context_24h"])


def test_build_hourly_context_validates_hour_alignment() -> None:
    schedule = [_schedule_entry(hour) for hour in range(24)]
    accessibility = [_accessibility_entry(hour) for hour in range(24)]
    energy = [_energy_entry(hour) for hour in range(24)]
    environment = [_environment_entry(hour) for hour in range(24)]
    energy[5] = {**energy[5], "hour": 6}

    with pytest.raises(ValueError, match="index=5.*schedule_hour=5.*energy_hour=6"):
        build_hourly_context_24h(schedule, accessibility, energy, environment)


def test_hourly_context_uses_constrained_schedule_not_normal_schedule() -> None:
    illness = AcuteIllnessConstraint(name="flu", intensity="high", start_weekday=1, duration_days=1)
    context = _runner_context(ConstraintManager([illness]))

    changed_hour = next(
        entry["hour"]
        for entry in context["constrained_schedule"]
        if entry != context["normal_schedule"][entry["hour"]]
    )
    hourly_entry = context["hourly_context_24h"][changed_hour]
    constrained_entry = context["constrained_schedule"][changed_hour]
    normal_entry = context["normal_schedule"][changed_hour]

    assert hourly_entry["activity_type"] == constrained_entry["activity_type"]
    assert hourly_entry["subtype"] == constrained_entry["subtype"]
    assert (hourly_entry["activity_type"], hourly_entry["subtype"]) != (
        normal_entry["activity_type"],
        normal_entry["subtype"],
    )
    assert hourly_entry["subtype"] in {"illness_recovery", "illness_sleep"}


def test_hourly_context_environment_fields_exclude_old_mobility_fields() -> None:
    context = _runner_context()
    old_mobility_fields = {
        "home_node",
        "current_node",
        "lat",
        "lon",
        "mobility",
        "is_at_home",
        "minutes_to_nearest_gym_walk",
        "minutes_to_nearest_gym_bike",
        "minutes_to_nearest_pool_walk",
        "minutes_to_nearest_pool_bike",
        "minutes_to_nearest_park_walk",
        "minutes_to_nearest_park_bike",
    }

    assert all(old_mobility_fields.isdisjoint(entry) for entry in context["hourly_context_24h"])
