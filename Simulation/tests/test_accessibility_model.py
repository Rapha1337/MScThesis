from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import pytest

from accessibility_model import (
    ACCESSIBILITY_CATEGORIES,
    build_accessibility_model,
    calculate_travel_times_min,
    infer_current_location,
)


def _demo_model():
    return build_accessibility_model(
        workplace_distance_km=3.0,
        indoor_activity_distance_km=1.2,
        outdoor_activity_distance_km=0.6,
    )


def test_demo_accessibility_model_contains_all_categories_and_times() -> None:
    model = _demo_model()

    payload = model.to_dict()
    assert set(payload["categories"]) == set(ACCESSIBILITY_CATEGORIES)

    workplace = payload["categories"]["workplace"]
    assert workplace["distance_km"] == 3.0
    assert workplace["travel_times_min"]["walk"] == pytest.approx(37.5)
    assert workplace["travel_times_min"]["bike"] == pytest.approx(12.0)
    assert workplace["travel_times_min"]["car"] == pytest.approx(6.0)

    parsed = json.loads(model.to_json(indent=2))
    assert parsed == payload


def test_none_zero_and_negative_distances() -> None:
    assert calculate_travel_times_min(None) == {"walk": None, "bike": None, "car": None}
    assert calculate_travel_times_min(0) == {"walk": 0.0, "bike": 0.0, "car": 0.0}

    with pytest.raises(ValueError):
        calculate_travel_times_min(-0.1)


def test_home_office_can_be_represented_as_zero_distance_note() -> None:
    model = build_accessibility_model(
        workplace_distance_km=0,
        indoor_activity_distance_km=1.2,
        outdoor_activity_distance_km=0.6,
        workplace_note="home_office",
    )

    workplace = model.get_entry("workplace").to_dict()
    assert workplace["note"] == "home_office"
    assert workplace["travel_times_min"] == {"walk": 0.0, "bike": 0.0, "car": 0.0}


def test_agent_context_accepts_accessibility_model() -> None:
    from agent_context import build_agent_context

    model = _demo_model()
    context = build_agent_context(
        persona_name="demo",
        phase="normal",
        weekday=1,
        world_info={},
        active_constraints=[],
        normal_schedule=[],
        constrained_schedule=[],
        accessibility_model=model,
    )

    assert "accessibility_model" in context
    assert set(context["accessibility_model"]["categories"]) == set(ACCESSIBILITY_CATEGORIES)


def test_access_from_home_returns_survey_distances() -> None:
    model = _demo_model()
    access = model.get_access_from_location("home")

    targets = access["targets"]
    assert targets["home"]["distance_km"] == 0.0
    assert targets["workplace"]["distance_km"] == 3.0
    assert targets["indoor_activity"]["distance_km"] == 1.2
    assert targets["outdoor_activity"]["distance_km"] == 0.6


def test_access_from_workplace_to_home_is_symmetric_survey_distance() -> None:
    model = _demo_model()
    access = model.get_access_from_location("workplace")

    home = access["targets"]["home"]
    assert home["distance_km"] == 3.0
    assert home["travel_times_min"]["walk"] == pytest.approx(37.5)
    assert home["travel_times_min"]["bike"] == pytest.approx(12.0)
    assert home["travel_times_min"]["car"] == pytest.approx(6.0)


def test_non_home_pairwise_distance_uses_mean_distance_heuristic() -> None:
    model = _demo_model()
    access = model.get_access_from_location("workplace")

    indoor = access["targets"]["indoor_activity"]
    assert indoor["distance_km"] == pytest.approx((3.0 + 1.2) / 2.0)
    assert indoor["source"] == "home_distance_mean_heuristic"
    assert indoor["travel_times_min"]["walk"] == pytest.approx(26.25)


def test_same_location_distance_is_zero() -> None:
    model = _demo_model()
    access = model.get_access_from_location("indoor_activity")

    same = access["targets"]["indoor_activity"]
    assert same["distance_km"] == 0.0
    assert same["travel_times_min"] == {"walk": 0.0, "bike": 0.0, "car": 0.0}


def test_none_distances_propagate_to_none_pairwise_travel_times() -> None:
    model = build_accessibility_model(
        workplace_distance_km=3.0,
        indoor_activity_distance_km=None,
        outdoor_activity_distance_km=0.6,
    )

    home_access = model.get_access_from_location("home")
    assert home_access["targets"]["indoor_activity"]["distance_km"] is None
    assert home_access["targets"]["indoor_activity"]["travel_times_min"] == {
        "walk": None,
        "bike": None,
        "car": None,
    }

    workplace_access = model.get_access_from_location("workplace")
    assert workplace_access["targets"]["indoor_activity"]["distance_km"] is None
    assert workplace_access["targets"]["indoor_activity"]["travel_times_min"] == {
        "walk": None,
        "bike": None,
        "car": None,
    }


def test_travel_times_exist_for_all_modes_from_location() -> None:
    model = _demo_model()
    access = model.get_access_from_location("workplace")

    for target in access["targets"].values():
        assert set(target["travel_times_min"]) == {"walk", "bike", "car"}


def test_current_location_inference_for_example_schedule_entries() -> None:
    assert infer_current_location({"activity_type": "sleep", "subtype": "night_sleep"}) == "home"
    assert infer_current_location({"activity_type": "eat", "subtype": "lunch"}) == "home"
    assert infer_current_location({"activity_type": "downtime", "subtype": "open_time"}) == "home"
    assert infer_current_location({"activity_type": "work", "subtype": "paid_work"}) == "workplace"
    assert infer_current_location({"activity_type": "work", "subtype": "studying"}) == "home"
    assert infer_current_location({"activity_type": "physical_activity", "subtype": "gym"}) == "indoor_activity"
    assert infer_current_location({"activity_type": "physical_activity", "subtype": "outdoor_running"}) == "outdoor_activity"
    assert infer_current_location({"activity_type": "social_time", "subtype": "evening_social"}) == "unknown"


def test_build_hourly_accessibility_serializes_schedule_without_mutation() -> None:
    model = _demo_model()
    schedule = [
        {"hour": 0, "activity_type": "sleep", "subtype": "night_sleep"},
        {"hour": 9, "activity_type": "work", "subtype": "paid_work"},
        {"hour": 18, "activity_type": "physical_activity", "subtype": "gym"},
    ]

    hourly = model.build_hourly_accessibility(schedule)
    assert [entry["current_location"] for entry in hourly] == ["home", "workplace", "indoor_activity"]
    assert hourly[0]["accessibility"]["targets"]["workplace"]["distance_km"] == 3.0
    assert hourly[1]["accessibility"]["targets"]["indoor_activity"]["distance_km"] == pytest.approx(2.1)
    assert hourly[2]["accessibility"]["targets"]["indoor_activity"]["distance_km"] == 0.0
    assert schedule[1] == {"hour": 9, "activity_type": "work", "subtype": "paid_work"}


def _assert_hourly_accessibility_shape(hourly: list[dict[str, object]]) -> None:
    assert len(hourly) == 24
    for index, entry in enumerate(hourly):
        assert "current_location" in entry
        assert "previous_location" in entry
        assert "location_changed_from_previous_hour" in entry
        assert "travel_from_previous_location" in entry
        if index == 0:
            assert entry["previous_location"] is None
            assert entry["location_changed_from_previous_hour"] is False
            assert entry["travel_from_previous_location"] is None
        else:
            assert entry["previous_location"] == hourly[index - 1]["current_location"]
            travel = entry["travel_from_previous_location"]
            assert isinstance(travel, dict)
            assert set(travel["travel_times_min"]) == {"walk", "bike", "car"}


def test_simulation_runner_day_context_builds_hourly_accessibility_from_generated_schedule() -> None:
    from agent_context import build_agent_context
    from persona_wrappers import StudentHoursWrapper
    from schedule_model_student import YearPhase
    from simulation_runner import SimulationRunner

    class FakeEnv:
        def reset(self, seed=None, options=None):
            del options
            return None, {"seed": seed, "hour": 9, "state": "reset"}

        def step(self, action: int = 0):
            return None, 0.0, False, False, {"action": action, "hour": 10, "state": "stepped"}

    model = _demo_model()
    persona = StudentHoursWrapper.from_zve_student_generic(name="accessibility_runner_student")
    runner = SimulationRunner(
        persona=persona,
        phase=YearPhase.SEMESTER,
        env=FakeEnv(),
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

    assert "accessibility_model" in context
    assert "hourly_accessibility_24h" in context
    hourly = context["hourly_accessibility_24h"]
    _assert_hourly_accessibility_shape(hourly)

    assert [entry["hour"] for entry in hourly] == [entry["hour"] for entry in context["constrained_schedule"]]

    has_location_change = any(entry["location_changed_from_previous_hour"] for entry in hourly)
    if not has_location_change:
        deterministic_schedule = [
            {"hour": hour, "activity_type": "sleep", "subtype": "night_sleep"}
            if hour < 8 or hour >= 22
            else {"hour": hour, "activity_type": "work", "subtype": "paid_work"}
            if 9 <= hour < 17
            else {"hour": hour, "activity_type": "downtime", "subtype": "open_time"}
            for hour in range(24)
        ]
        context = build_agent_context(
            persona_name="fixture_student",
            phase="semester",
            weekday=0,
            world_info={"hour": 9},
            active_constraints=[],
            normal_schedule=deterministic_schedule,
            constrained_schedule=deterministic_schedule,
            accessibility_model=model,
        )
        hourly = context["hourly_accessibility_24h"]
        _assert_hourly_accessibility_shape(hourly)
        has_location_change = any(entry["location_changed_from_previous_hour"] for entry in hourly)

    assert has_location_change
    transition = next(entry for entry in hourly if entry["location_changed_from_previous_hour"])
    assert transition["previous_location"] != transition["current_location"]
    assert transition["travel_from_previous_location"] is not None
    assert set(transition["travel_from_previous_location"]["travel_times_min"]) == {"walk", "bike", "car"}
