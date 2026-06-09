from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from psychological_state import DEFAULT_PSYCHOLOGICAL_STATE
from run_agent_context_simulation import LLM_HOURLY_FIELDS
from run_heterogeneous_llm_contexts import main

EXPECTED_SCENARIOS = [
    "favourable_pa_context",
    "busy_day_context",
    "negative_pa_context",
    "indoor_opportunity_context",
    "bike_access_context",
]

EXPECTED_HOURLY_FIELDS = set(LLM_HOURLY_FIELDS) | {"poi_accessibility"}


def _assert_psychological_state(psychological_state: dict) -> None:
    expected_constructs = set(DEFAULT_PSYCHOLOGICAL_STATE["values_normalized"])
    assert set(psychological_state) == {"source", "n", "values_normalized", "raw_scale_means"}
    assert psychological_state["source"] == "T1_students_mean_from_simulated_AIcoPA_dataset"
    assert psychological_state["n"] == 64
    assert set(psychological_state["values_normalized"]) == expected_constructs
    assert set(psychological_state["raw_scale_means"]) == expected_constructs


def test_heterogeneous_llm_context_export_smoke(tmp_path: Path, capsys) -> None:
    output_path = tmp_path / "llm_day_contexts_heterogeneous_test.json"

    main(["--output-path", str(output_path)])

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    captured = capsys.readouterr()

    assert set(payload) == {"simulation_metadata", "llm_contexts"}
    assert payload["simulation_metadata"]["n_personas"] == 5
    assert [context["scenario"] for context in payload["llm_contexts"]] == EXPECTED_SCENARIOS
    assert "Runner command: python Simulation/run_heterogeneous_llm_contexts.py" in captured.out

    for context in payload["llm_contexts"]:
        _assert_psychological_state(context["psychological_state"])
        assert context["scenario"] in EXPECTED_SCENARIOS
        assert "action_plan" not in context
        assert len(context["hourly_context_24h"]) == 24
        for hourly_entry in context["hourly_context_24h"]:
            assert set(hourly_entry) == EXPECTED_HOURLY_FIELDS


def test_heterogeneous_scenarios_cover_requested_conditions(tmp_path: Path) -> None:
    output_path = tmp_path / "llm_day_contexts_heterogeneous_test.json"
    main(["--output-path", str(output_path)])
    contexts = {
        context["scenario"]: context
        for context in json.loads(output_path.read_text(encoding="utf-8"))["llm_contexts"]
    }

    favourable = contexts["favourable_pa_context"]
    assert favourable["phase"] == "holiday"
    assert _count_free_hours(favourable) >= 8
    assert _count_wet_hours(favourable) == 0
    assert _max_walk_time(favourable, "outdoor_activity") <= 10
    assert _max_walk_time(favourable, "indoor_activity") <= 15
    assert _daytime_energy_categories(favourable) <= {"medium", "high"}
    assert _daytime_energy_categories(favourable)

    busy = contexts["busy_day_context"]
    assert busy["phase"] == "normal"
    assert {"university", "paid_work", "carework"}.issubset(_subtypes(busy))
    assert _count_free_hours(busy) <= 3
    assert _daytime_energy_categories(busy) == {"medium"}

    negative = contexts["negative_pa_context"]
    assert negative["phase"] == "high_stress"
    assert _count_free_hours(negative) <= 3
    assert _daytime_energy_categories(negative) == {"low"}
    assert _count_wet_hours(negative) == 24
    assert _max_walk_time(negative, "indoor_activity") > 60

    indoor = contexts["indoor_opportunity_context"]
    assert _count_wet_hours(indoor) == 24
    assert _count_free_hours(indoor) >= 4
    assert _max_walk_time(indoor, "indoor_activity") <= 10
    assert _max_walk_time(indoor, "outdoor_activity") >= 30

    bike = contexts["bike_access_context"]
    assert _count_free_hours(bike) >= 4
    assert _count_wet_hours(bike) == 0
    assert _max_walk_time(bike, "outdoor_activity") > 45
    assert _max_bike_time(bike, "outdoor_activity") < 20


def _count_free_hours(context: dict) -> int:
    return sum(1 for hour in context["hourly_context_24h"] if hour["activity_type"] == "downtime")


def _count_wet_hours(context: dict) -> int:
    return sum(1 for hour in context["hourly_context_24h"] if hour["is_wet"])


def _subtypes(context: dict) -> set[str]:
    return {hour["subtype"] for hour in context["hourly_context_24h"]}


def _daytime_energy_categories(context: dict) -> set[str]:
    return {
        hour["energy_category"]
        for hour in context["hourly_context_24h"]
        if hour["activity_type"] not in {"sleep", "wake_up", "eat"}
    }


def _max_walk_time(context: dict, target: str) -> float:
    return max(
        hour["poi_accessibility"][target]["travel_times_min"]["walk"]
        for hour in context["hourly_context_24h"]
    )


def _max_bike_time(context: dict, target: str) -> float:
    return max(
        hour["poi_accessibility"][target]["travel_times_min"]["bike"]
        for hour in context["hourly_context_24h"]
    )
