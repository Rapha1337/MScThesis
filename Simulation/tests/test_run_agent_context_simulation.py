from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from psychological_state import BACKEND_CONSTRUCT_RANGES
from run_agent_context_simulation import main


EXPECTED_HOURLY_FIELDS = {
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
    "poi_accessibility",
}

DIAGNOSTIC_ARRAYS = {
    "hourly_energy_24h",
    "hourly_environment_24h",
    "hourly_accessibility_24h",
}


def _assert_psychological_state(psychological_state: dict) -> None:
    expected_constructs = set(BACKEND_CONSTRUCT_RANGES)
    legacy_constructs = {
        "habit",
        "attitude",
        "injunctive_norm",
        "descriptive_norm",
        "extrinsic_motivation",
        "volitional_self_control",
    }

    assert set(psychological_state) == {
        "source",
        "reference_group",
        "n",
        "sampling_method",
        "seed",
        "values_normalized",
        "raw_scale_means",
    }
    assert psychological_state["source"] == "T1_students_from_simulated_AIcoPA_dataset"
    assert psychological_state["reference_group"] == "T1_Studierend"
    assert psychological_state["n"] == 64
    assert psychological_state["sampling_method"] == "multivariate_normal"
    assert set(psychological_state["values_normalized"]) == expected_constructs
    assert set(psychological_state["raw_scale_means"]) == expected_constructs
    assert legacy_constructs.isdisjoint(psychological_state["values_normalized"])
    assert legacy_constructs.isdisjoint(psychological_state["raw_scale_means"])

    for construct_name, normalized_value in psychological_state["values_normalized"].items():
        min_value, max_value = BACKEND_CONSTRUCT_RANGES[construct_name]
        assert 0.0 <= normalized_value <= 1.0
        raw_value = psychological_state["raw_scale_means"][construct_name]
        assert min_value <= raw_value <= max_value
        assert raw_value == round(min_value + normalized_value * (max_value - min_value), 2)


def _run_cli(tmp_path: Path) -> tuple[Path, dict]:
    output_path = tmp_path / "agent_day_contexts.json"

    main(
        [
            "--n-personas",
            "2",
            "--base-seed",
            "37",
            "--day-index",
            "21",
            "--fitness-hours-week",
            "6",
            "--social-hours-week",
            "8",
            "--work-hours-week",
            "5",
            "--carework-hours-week",
            "7",
            "--workplace-distance-km",
            "3.0",
            "--indoor-activity-distance-km",
            "1.2",
            "--outdoor-activity-distance-km",
            "0.6",
            "--output-path",
            str(output_path),
        ]
    )

    return output_path, json.loads(output_path.read_text(encoding="utf-8"))


def test_run_agent_context_simulation_smoke(tmp_path: Path, capsys) -> None:
    output_path, payload = _run_cli(tmp_path)

    captured = capsys.readouterr()

    assert output_path.exists()
    assert set(payload) == {"simulation_metadata", "llm_contexts"}
    assert payload["simulation_metadata"] == {"base_seed": 37, "day_index": 21, "n_personas": 2}
    assert len(payload["llm_contexts"]) == 2
    for context in payload["llm_contexts"]:
        assert len(context["hourly_context_24h"]) == 24
    json.dumps(payload)
    assert "JSON export success: true" in captured.out


def test_exported_llm_contexts_include_compact_hourly_demo_fields(tmp_path: Path) -> None:
    _, payload = _run_cli(tmp_path)

    psychological_states = []
    for context in payload["llm_contexts"]:
        assert {
            "persona_id",
            "seed",
            "day_index",
            "phase",
            "weekday",
            "task_description",
            "input_parameters",
            "selected_schedule_parameters",
            "psychological_state",
            "hourly_context_24h",
        } == set(context)
        _assert_psychological_state(context["psychological_state"])
        psychological_states.append(context["psychological_state"]["values_normalized"])
        assert "action_plan" not in context
        assert len(context["hourly_context_24h"]) == 24
        for hourly_entry in context["hourly_context_24h"]:
            assert EXPECTED_HOURLY_FIELDS.issubset(hourly_entry)
            assert isinstance(hourly_entry["active_constraints"], list)
            assert hourly_entry["activity_type"] is not None
            assert hourly_entry["current_location"] is not None
            assert hourly_entry["energy_category"] in {"low", "medium", "high"}
            assert isinstance(hourly_entry["is_daylight"], bool)

            poi_accessibility = hourly_entry["poi_accessibility"]
            assert set(poi_accessibility) == {"indoor_activity", "outdoor_activity"}
            assert "distance_km" in poi_accessibility["indoor_activity"]
            assert "travel_times_min" in poi_accessibility["indoor_activity"]
            assert "distance_km" in poi_accessibility["outdoor_activity"]
            assert "travel_times_min" in poi_accessibility["outdoor_activity"]
    assert psychological_states[0] != psychological_states[1]


def test_exported_llm_contexts_do_not_include_diagnostic_arrays(tmp_path: Path) -> None:
    _, payload = _run_cli(tmp_path)

    serialized = json.dumps(payload)
    for context in payload["llm_contexts"]:
        assert DIAGNOSTIC_ARRAYS.isdisjoint(context)
        assert DIAGNOSTIC_ARRAYS.isdisjoint(context["hourly_context_24h"][0])
    assert all(array_name not in serialized for array_name in DIAGNOSTIC_ARRAYS)
