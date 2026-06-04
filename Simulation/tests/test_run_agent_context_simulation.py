from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

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
            "hourly_context_24h",
        } == set(context)
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


def test_exported_llm_contexts_do_not_include_diagnostic_arrays(tmp_path: Path) -> None:
    _, payload = _run_cli(tmp_path)

    serialized = json.dumps(payload)
    for context in payload["llm_contexts"]:
        assert DIAGNOSTIC_ARRAYS.isdisjoint(context)
        assert DIAGNOSTIC_ARRAYS.isdisjoint(context["hourly_context_24h"][0])
    assert all(array_name not in serialized for array_name in DIAGNOSTIC_ARRAYS)
