from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

GLOBAL_ENVIRONMENT_FIELDS = {
    "month",
    "season",
    "temperature_c",
    "feels_like_c",
    "humidity_pct",
    "wind_m_s",
    "precipitation_mm",
    "is_wet",
    "sun_frac",
    "is_daylight",
    "snow_cover",
}


def _run_dry_simulation(tmp_path: Path, *, include_full_hourly_context: bool = True):
    from run_full_pa_simulation import FullSimulationConfig, run_full_simulation

    output_dir = tmp_path / "full_pa_dry_run"
    config = FullSimulationConfig(
        n_personas=2,
        n_days=2,
        start_date=date(2026, 1, 1),
        base_seed=137,
        output_dir=output_dir,
        model="gpt-oss-120b",
        temperature=0,
        llm1_max_tokens=2000,
        llm2_max_tokens=1200,
        dry_run=True,
        include_full_hourly_context=include_full_hourly_context,
    )
    return config, run_full_simulation(config)


def test_full_pa_dry_run_two_personas_two_days_creates_four_records(tmp_path: Path) -> None:
    config, trace = _run_dry_simulation(tmp_path)

    assert trace["metadata"]["n_personas"] == 2
    assert trace["metadata"]["n_days"] == 2
    assert trace["metadata"]["n_records"] == 4
    assert len(trace["records"]) == 4
    assert (config.output_dir / "full_simulation_trace.json").exists()
    assert (config.output_dir / "daily_decision_log.csv").exists()
    assert (config.output_dir / "longitudinal_constructs.csv").exists()


def test_full_pa_dry_run_records_include_24_hour_context_when_requested(tmp_path: Path) -> None:
    _, trace = _run_dry_simulation(tmp_path, include_full_hourly_context=True)

    for record in trace["records"]:
        assert len(record["hourly_context_24h"]) == 24
        assert record["context_summary"]["n_hourly_context_entries"] == 24


def test_global_environment_is_shared_across_three_personas_for_two_days(
    tmp_path: Path,
) -> None:
    from run_full_pa_simulation import FullSimulationConfig, run_full_simulation

    config = FullSimulationConfig(
        n_personas=3,
        n_days=2,
        start_date=date(2026, 3, 2),
        base_seed=137,
        output_dir=tmp_path / "shared_environment",
        model="gpt-oss-120b",
        temperature=0,
        llm1_max_tokens=2000,
        llm2_max_tokens=1200,
        dry_run=True,
        include_full_hourly_context=True,
        cli_overrides={"indoor_activity_distance_km": [1.0, 3.0, 8.0]},
    )
    trace = run_full_simulation(config)
    records_by_date: dict[str, list[dict]] = {}
    for record in trace["records"]:
        records_by_date.setdefault(record["calendar_date"], []).append(record)

    assert len(records_by_date) == 2
    for records in records_by_date.values():
        assert len(records) == 3
        for hour in range(24):
            environments = [
                {
                    field: record["hourly_context_24h"][hour][field]
                    for field in GLOBAL_ENVIRONMENT_FIELDS
                }
                for record in records
            ]
            assert environments[1:] == environments[:-1]

    assert any(
        len(
            {
                (
                    record["hourly_context_24h"][hour]["activity_type"],
                    record["hourly_context_24h"][hour]["energy_level"],
                    json.dumps(
                        record["hourly_context_24h"][hour]["poi_accessibility"],
                        sort_keys=True,
                    ),
                )
                for record in records
            }
        )
        > 1
        for records in records_by_date.values()
        for hour in range(24)
    )
    assert {
        record["persona_metadata"]["poi_distances_km"]["indoor_activity"]
        for record in trace["records"]
    } == {1.0, 3.0, 8.0}


def test_start_date_changes_global_month_season_and_daylight(tmp_path: Path) -> None:
    from run_full_pa_simulation import FullSimulationConfig, build_global_environment_by_date

    def environment_for(start_date: date, name: str) -> list[dict]:
        config = FullSimulationConfig(
            n_personas=1,
            n_days=1,
            start_date=start_date,
            base_seed=137,
            output_dir=tmp_path / name,
            model="gpt-oss-120b",
            temperature=0,
            llm1_max_tokens=2000,
            llm2_max_tokens=1200,
            dry_run=True,
            include_full_hourly_context=True,
        )
        return build_global_environment_by_date(config)[start_date.isoformat()]

    january = environment_for(date(2026, 1, 2), "january")
    july = environment_for(date(2026, 7, 2), "july")

    assert {entry["month"] for entry in january} == {1}
    assert {entry["season"] for entry in january} == {"winter"}
    assert {entry["month"] for entry in july} == {7}
    assert {entry["season"] for entry in july} == {"summer"}
    assert sum(entry["is_daylight"] for entry in july) > sum(
        entry["is_daylight"] for entry in january
    )


def test_shared_environment_is_consistent_in_compact_and_trace_exports(
    tmp_path: Path,
) -> None:
    config, _ = _run_dry_simulation(tmp_path)
    compact = json.loads(
        (config.output_dir / "contexts_compact.json").read_text(encoding="utf-8")
    )["llm_contexts"]
    trace = json.loads(
        (config.output_dir / "full_simulation_trace.json").read_text(encoding="utf-8")
    )["records"]

    for exported_contexts in (compact, trace):
        by_date: dict[str, list[dict]] = {}
        for context in exported_contexts:
            by_date.setdefault(context["calendar_date"], []).append(context)
        for contexts in by_date.values():
            for hour in range(24):
                expected = {
                    field: contexts[0]["hourly_context_24h"][hour][field]
                    for field in GLOBAL_ENVIRONMENT_FIELDS
                }
                assert all(
                    {
                        field: context["hourly_context_24h"][hour][field]
                        for field in GLOBAL_ENVIRONMENT_FIELDS
                    }
                    == expected
                    for context in contexts
                )


def test_full_pa_dry_run_derives_daily_plans_and_carries_constructs_forward(tmp_path: Path) -> None:
    _, trace = _run_dry_simulation(tmp_path)

    records_by_persona: dict[str, list[dict]] = {}
    for record in trace["records"]:
        records_by_persona.setdefault(record["persona_id"], []).append(record)

    assert set(records_by_persona) == {"StudentPersona_01", "StudentPersona_02"}
    for records in records_by_persona.values():
        records.sort(key=lambda item: item["day_index"])
        day_1, day_2 = records
        for record in records:
            expected = any(
                entry["activity_type"] == "physical_activity"
                or entry["subtype"] == "physical_activity"
                for entry in record["hourly_context_24h"]
            )
            assert record["was_physical_activity_planned_today"] is expected
            assert (record["planned_physical_activity"] is not None) is expected
            assert "planned_activity_next_day" not in record["closed_loop_update"]
        assert day_2["psychological_constructs_before_update"] == day_1[
            "psychological_constructs_after_update"
        ]


def test_full_pa_dry_run_logs_valid_categories_and_llm2_decision_source(tmp_path: Path) -> None:
    _, trace = _run_dry_simulation(tmp_path)

    for record in trace["records"]:
        assert record["behavior_policy_raw"] == record["behavior_policy"]
        assert record["decision_source"] == "llm2_contextual_decision"
        assert "sampled_decision_label" not in record
        assert "decision_sampling_seed" not in record
        if record["was_physical_activity_planned_today"]:
            assert record["valid_decision_categories"] == [
                "do_planned_activity",
                "adapt_activity",
                "skip_activity",
                "extra_activity",
            ]
        else:
            assert record["valid_decision_categories"] == ["skip_activity", "extra_activity"]
            assert record["pa_decision"]["decision_label"] in {"skip_activity", "extra_activity"}


def test_full_pa_dry_run_assesses_state_after_each_diary_with_history(tmp_path: Path) -> None:
    from run_full_pa_simulation import FullSimulationConfig, run_full_simulation

    config = FullSimulationConfig(
        n_personas=1,
        n_days=3,
        start_date=date(2026, 1, 1),
        base_seed=137,
        output_dir=tmp_path / "assessment_history",
        model="gpt-oss-120b",
        temperature=0,
        llm1_max_tokens=2000,
        llm2_max_tokens=1200,
        dry_run=True,
        include_full_hourly_context=True,
    )
    trace = run_full_simulation(config)
    records = trace["records"]

    assert [record["previous_diary_entries_count"] for record in records] == [0, 1, 2]
    assert all(record["state_assessment_enabled"] for record in records)
    assert all(record["state_assessment_mode"] == "dry_run_mock" for record in records)
    for day_index, record in enumerate(records):
        history = record["previous_diary_entries_context_used"]
        assert [entry["day_index"] for entry in history] == list(range(day_index))
        assert all(entry["day_index"] < day_index for entry in history)
        assert record["psychological_construct_values_before_state_assessment"] == record[
            "psychological_construct_values_after_state_assessment"
        ]

    manifest = json.loads(
        (config.output_dir / "simulation_run_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["state_assessment"]["state_assessment_call_count"] == 3
    assert manifest["state_assessment"]["state_assessment_dry_run_count"] == 3
    assert manifest["state_assessment"][
        "placeholder_next_day_activity_generation_disabled"
    ] is True
    assert manifest["state_assessment"]["state_assessment_max_tokens"] == 10000
    assert manifest["state_assessment"]["state_assessment_json_mode_enabled"] is False
    run_config = json.loads((config.output_dir / "run_config.json").read_text(encoding="utf-8"))
    assert run_config["state_assessment_max_tokens"] == 10000
    assert run_config["state_assessment_json_mode_enabled"] is False


def test_state_assessment_max_tokens_cli_defaults_to_10000() -> None:
    from run_full_pa_simulation import config_from_args, parse_args

    args = parse_args([])
    assert args.state_assessment_max_tokens == 10000
    assert config_from_args(args).state_assessment_max_tokens == 10000
    assert args.state_assessment_json_mode is False
    assert config_from_args(args).state_assessment_json_mode is False


def test_state_assessment_json_mode_cli_is_opt_in_and_recorded(tmp_path: Path) -> None:
    from run_full_pa_simulation import config_from_args, parse_args, run_full_simulation

    args = parse_args([
        "--state-assessment-json-mode",
        "--dry-run",
        "--n-personas",
        "1",
        "--n-days",
        "1",
        "--output-dir",
        str(tmp_path),
        "--disable-resource-tracking",
    ])
    assert args.state_assessment_json_mode is True
    config = config_from_args(args)
    assert config.state_assessment_json_mode is True

    run_full_simulation(config)

    manifest = json.loads((tmp_path / "simulation_run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["state_assessment"]["state_assessment_json_mode_enabled"] is True


def test_full_pa_dry_run_outputs_valid_json_and_csv_rows(tmp_path: Path) -> None:
    config, trace = _run_dry_simulation(tmp_path)

    for filename in ("run_config.json", "full_simulation_trace.json", "contexts_compact.json"):
        with (config.output_dir / filename).open("r", encoding="utf-8") as file:
            json.load(file)

    with (config.output_dir / "daily_decision_log.csv").open("r", encoding="utf-8", newline="") as file:
        daily_rows = list(csv.DictReader(file))
    assert len(daily_rows) == 4
    assert daily_rows[0]["calendar_date"] == "2026-01-01"

    with (config.output_dir / "longitudinal_constructs.csv").open("r", encoding="utf-8", newline="") as file:
        construct_rows = list(csv.DictReader(file))
    assert len(construct_rows) == 4 * len(trace["records"][0]["psychological_constructs_before_update"])



def test_full_pa_dry_run_compact_context_excludes_llm2_metadata(tmp_path: Path) -> None:
    config, _ = _run_dry_simulation(tmp_path)
    compact_payload = json.loads((config.output_dir / "contexts_compact.json").read_text(encoding="utf-8"))

    assert compact_payload["llm_contexts"]
    for context in compact_payload["llm_contexts"]:
        assert "task_description" not in context
        assert "input_parameters" not in context
        assert "selected_schedule_parameters" not in context
        assert len(context["hourly_context_24h"]) == 24


def test_full_pa_dry_run_preserves_persona_metadata_separately(tmp_path: Path) -> None:
    config, trace = _run_dry_simulation(tmp_path)
    metadata_payload = json.loads((config.output_dir / "persona_metadata.json").read_text(encoding="utf-8"))

    assert trace["metadata"]["persona_metadata_file"] == str(config.output_dir / "persona_metadata.json")
    assert len(metadata_payload["personas"]) == 2
    assert "input_parameters" in metadata_payload["personas"][0]
    assert "selected_schedule_parameters" in metadata_payload["personas"][0]

def test_existing_single_day_pa_decision_input_builder_still_accepts_contexts(tmp_path: Path) -> None:
    from run_llm_pa_decision import build_pa_decision_input

    _, trace = _run_dry_simulation(tmp_path)
    record = trace["records"][0]
    context_path = tmp_path / "contexts.json"
    compact_context = json.loads(
        (tmp_path / "full_pa_dry_run" / "contexts_compact.json").read_text(encoding="utf-8")
    )["llm_contexts"][0]
    context_path.write_text(json.dumps({"llm_contexts": [compact_context]}), encoding="utf-8")

    pa_input = build_pa_decision_input(
        compact_context,
        record["behavior_policy"],
        planned_activity=record["planned_physical_activity"],
    )

    assert pa_input["persona_id"] == compact_context["persona_id"]
    assert pa_input["day_index"] == compact_context["day_index"]
    assert len(pa_input["daily_context"]["hourly_context_24h"]) == 24


def test_full_pa_without_overrides_uses_default_persona_values(tmp_path: Path) -> None:
    from agent_context_export import DEFAULT_INPUT_PARAMETERS

    config, trace = _run_dry_simulation(tmp_path)
    metadata_payload = json.loads((config.output_dir / "persona_metadata.json").read_text(encoding="utf-8"))

    for persona in metadata_payload["personas"]:
        assert persona["input_parameters"] == {
            "physical_activity_hours_per_week": DEFAULT_INPUT_PARAMETERS["fitness_hours_week"],
            "social_hours_per_week": DEFAULT_INPUT_PARAMETERS["social_hours_week"],
            "care_work_hours_per_week": DEFAULT_INPUT_PARAMETERS["carework_hours_week"],
            "work_hours_per_week": DEFAULT_INPUT_PARAMETERS["work_hours_week"],
        }
        assert persona["poi_distances_km"] == {
            "workplace": DEFAULT_INPUT_PARAMETERS["workplace_distance_km"],
            "indoor_activity": DEFAULT_INPUT_PARAMETERS["indoor_activity_distance_km"],
            "outdoor_activity": DEFAULT_INPUT_PARAMETERS["outdoor_activity_distance_km"],
        }
    assert trace["records"][0]["persona_metadata"]["input_parameters"] == metadata_payload["personas"][0]["input_parameters"]


def test_full_pa_single_value_override_applies_to_all_personas(tmp_path: Path) -> None:
    from run_full_pa_simulation import config_from_args, parse_args, run_full_simulation

    args = parse_args([
        "--n-personas", "2",
        "--n-days", "1",
        "--output-dir", str(tmp_path / "single_override"),
        "--social-hours-per-week", "8",
        "--dry-run",
    ])
    config = config_from_args(args)
    run_full_simulation(config)
    metadata_payload = json.loads((config.output_dir / "persona_metadata.json").read_text(encoding="utf-8"))

    assert [p["input_parameters"]["social_hours_per_week"] for p in metadata_payload["personas"]] == [8.0, 8.0]


def test_full_pa_comma_separated_override_maps_by_persona(tmp_path: Path) -> None:
    from run_full_pa_simulation import config_from_args, parse_args, run_full_simulation

    args = parse_args([
        "--n-personas", "2",
        "--n-days", "1",
        "--output-dir", str(tmp_path / "per_persona_override"),
        "--social-hours-per-week", "8,3",
        "--dry-run",
    ])
    config = config_from_args(args)
    run_full_simulation(config)
    metadata_payload = json.loads((config.output_dir / "persona_metadata.json").read_text(encoding="utf-8"))

    assert [p["input_parameters"]["social_hours_per_week"] for p in metadata_payload["personas"]] == [8.0, 3.0]


def test_full_pa_partial_comma_list_keeps_defaults_for_remaining_personas(tmp_path: Path) -> None:
    from agent_context_export import DEFAULT_INPUT_PARAMETERS
    from run_full_pa_simulation import config_from_args, parse_args, run_full_simulation

    args = parse_args([
        "--n-personas", "3",
        "--n-days", "1",
        "--output-dir", str(tmp_path / "partial_override"),
        "--social-hours-per-week", "8,3",
        "--dry-run",
    ])
    config = config_from_args(args)
    run_full_simulation(config)
    metadata_payload = json.loads((config.output_dir / "persona_metadata.json").read_text(encoding="utf-8"))

    assert [p["input_parameters"]["social_hours_per_week"] for p in metadata_payload["personas"]] == [
        8.0,
        3.0,
        DEFAULT_INPUT_PARAMETERS["social_hours_week"],
    ]


def test_full_pa_too_many_override_values_raise_clear_error() -> None:
    import pytest
    from run_full_pa_simulation import config_from_args, parse_args

    args = parse_args([
        "--n-personas", "2",
        "--social-hours-per-week", "8,3,1",
    ])
    with pytest.raises(ValueError, match="has 3 values, but --n-personas is 2"):
        config_from_args(args)


def test_full_pa_negative_hour_and_distance_overrides_raise_clear_errors() -> None:
    import pytest
    from run_full_pa_simulation import config_from_args, parse_args

    negative_hours = parse_args(["--work-hours-per-week", "-1"])
    with pytest.raises(ValueError, match="must be non-negative"):
        config_from_args(negative_hours)

    negative_distance = parse_args(["--workplace-distance-km", "-0.5"])
    with pytest.raises(ValueError, match="must be non-negative"):
        config_from_args(negative_distance)


def test_full_pa_overrides_appear_in_persona_metadata_and_trace(tmp_path: Path) -> None:
    from run_full_pa_simulation import config_from_args, parse_args, run_full_simulation

    args = parse_args([
        "--n-personas", "2",
        "--n-days", "1",
        "--output-dir", str(tmp_path / "metadata_override"),
        "--physical-activity-hours-per-week", "4,1",
        "--social-hours-per-week", "8,3",
        "--care-work-hours-per-week", "0,4",
        "--work-hours-per-week", "25,35",
        "--workplace-distance-km", "3.0,8.0",
        "--indoor-activity-distance-km", "1.2,4.5",
        "--outdoor-activity-distance-km", "0.6,1.8",
        "--dry-run",
    ])
    config = config_from_args(args)
    trace = run_full_simulation(config)
    metadata_payload = json.loads((config.output_dir / "persona_metadata.json").read_text(encoding="utf-8"))

    assert metadata_payload["personas"][0]["input_parameters"] == {
        "physical_activity_hours_per_week": 4.0,
        "social_hours_per_week": 8.0,
        "care_work_hours_per_week": 0.0,
        "work_hours_per_week": 25.0,
    }
    assert metadata_payload["personas"][1]["input_parameters"] == {
        "physical_activity_hours_per_week": 1.0,
        "social_hours_per_week": 3.0,
        "care_work_hours_per_week": 4.0,
        "work_hours_per_week": 35.0,
    }
    assert metadata_payload["personas"][1]["poi_distances_km"] == {
        "workplace": 8.0,
        "indoor_activity": 4.5,
        "outdoor_activity": 1.8,
    }
    assert trace["records"][0]["persona_metadata"]["input_parameters"] == metadata_payload["personas"][0]["input_parameters"]
    assert trace["records"][1]["persona_metadata"]["poi_distances_km"] == metadata_payload["personas"][1]["poi_distances_km"]


def test_full_pa_llm2_input_still_excludes_raw_metadata_after_overrides(tmp_path: Path) -> None:
    from run_full_pa_simulation import config_from_args, parse_args, run_full_simulation
    from run_llm_pa_decision import build_pa_decision_input

    args = parse_args([
        "--n-personas", "1",
        "--n-days", "1",
        "--output-dir", str(tmp_path / "llm2_override"),
        "--social-hours-per-week", "8",
        "--dry-run",
    ])
    config = config_from_args(args)
    trace = run_full_simulation(config)
    compact_context = json.loads((config.output_dir / "contexts_compact.json").read_text(encoding="utf-8"))["llm_contexts"][0]
    pa_input = build_pa_decision_input(
        compact_context,
        trace["records"][0]["behavior_policy"],
        planned_activity=trace["records"][0]["planned_physical_activity"],
    )

    serialized_pa_input = json.dumps(pa_input)
    assert "task_description" not in serialized_pa_input
    assert "input_parameters" not in serialized_pa_input
    assert "selected_schedule_parameters" not in serialized_pa_input


def test_full_simulation_passes_current_decision_and_planned_pa_to_state_assessment(
    tmp_path: Path, monkeypatch
) -> None:
    import state_assessment
    import run_full_pa_simulation as module
    from run_full_pa_simulation import FullSimulationConfig, run_full_simulation

    captured: list[dict] = []
    original = state_assessment.run_state_assessment

    def capturing_state_assessment(**kwargs):
        captured.append(dict(kwargs))
        return original(**kwargs)

    monkeypatch.setattr(module, "run_state_assessment", capturing_state_assessment)
    config = FullSimulationConfig(
        n_personas=1,
        n_days=2,
        start_date=date(2026, 1, 1),
        base_seed=137,
        output_dir=tmp_path / "state_assessment_wiring",
        model="gpt-oss-120b",
        temperature=0,
        llm1_max_tokens=2000,
        llm2_max_tokens=1200,
        dry_run=True,
        include_full_hourly_context=False,
    )

    trace = run_full_simulation(config)

    assert len(captured) == len(trace["records"])
    for call, record in zip(captured, trace["records"], strict=True):
        assert call["current_decision_label"] == record["pa_decision"]["decision_label"]
        assert call["was_physical_activity_planned_today"] is (
            record["planned_physical_activity"] is not None
        )
        assert call["planned_physical_activity_summary"] == record["planned_physical_activity"]


def test_planned_physical_activity_summary_preserves_contiguous_block() -> None:
    from run_full_pa_simulation import planned_physical_activity_from_schedule

    hourly = [{"hour": hour, "activity_type": "downtime", "current_location": "home"} for hour in range(24)]
    for hour in (10, 11):
        hourly[hour].update({"activity_type": "physical_activity", "subtype": "gym", "current_location": "indoor_activity"})

    planned = planned_physical_activity_from_schedule(hourly)

    assert planned["is_contiguous"] is True
    assert planned["scheduled_hours"] == [10, 11]
    assert len(planned["blocks"]) == 1
    assert planned["blocks"][0]["scheduled_hours"] == [10, 11]


def test_planned_physical_activity_summary_preserves_non_contiguous_blocks() -> None:
    from run_full_pa_simulation import planned_physical_activity_from_schedule

    hourly = [{"hour": hour, "activity_type": "downtime", "current_location": "home"} for hour in range(24)]
    hourly[8].update({"activity_type": "physical_activity", "subtype": "run", "current_location": "outdoor_activity"})
    hourly[18].update({"activity_type": "physical_activity", "subtype": "gym", "current_location": "indoor_activity"})

    planned = planned_physical_activity_from_schedule(hourly)

    assert planned["is_contiguous"] is False
    assert planned["scheduled_hours"] == [8, 18]
    assert [block["scheduled_hours"] for block in planned["blocks"]] == [[8], [18]]
    assert planned["planned_target_locations"] == ["indoor_activity", "outdoor_activity"]


def test_planned_physical_activity_summary_preserves_mixed_targets_in_one_block() -> None:
    from run_full_pa_simulation import planned_physical_activity_from_schedule

    hourly = [{"hour": hour, "activity_type": "downtime", "current_location": "home"} for hour in range(24)]
    hourly[14].update({"activity_type": "physical_activity", "subtype": "run", "current_location": "outdoor_activity"})
    hourly[15].update({"activity_type": "physical_activity", "subtype": "gym", "current_location": "indoor_activity"})

    planned = planned_physical_activity_from_schedule(hourly)

    assert planned["is_contiguous"] is True
    assert planned["planned_target_locations"] == ["indoor_activity", "outdoor_activity"]
    assert planned["blocks"][0]["planned_target_locations"] == ["indoor_activity", "outdoor_activity"]

def test_closed_loop_pipeline_log_removed_from_outputs_and_trace_points_to_daily_log(tmp_path: Path) -> None:
    config, trace = _run_dry_simulation(tmp_path)
    manifest = json.loads((config.output_dir / "simulation_run_manifest.json").read_text(encoding="utf-8"))
    trace_file_payload = json.loads((config.output_dir / "full_simulation_trace.json").read_text(encoding="utf-8"))

    assert not (config.output_dir / "pipeline_closed_loop_daily_log.csv").exists()
    assert "pipeline_closed_loop_daily_log" not in manifest["output_files"]
    assert "pipeline_closed_loop_daily_log.csv" not in manifest["output_files"].values()
    assert "pipeline_closed_loop_daily_log" not in trace_file_payload["metadata"]["output_files"]
    assert trace_file_payload["metadata"]["output_files"]["daily_decision_log"] == "daily_decision_log.csv"
    for record in trace["records"]:
        assert record["output_files"]["daily_decision_log"].endswith("daily_decision_log.csv")
        assert "pipeline_closed_loop_daily_log.csv" not in record["output_files"]["daily_decision_log"]


def test_llm2_planned_pa_context_in_trace_matches_original_pa_hours(tmp_path: Path) -> None:
    _, trace = _run_dry_simulation(tmp_path)
    planned_records = [record for record in trace["records"] if record["was_physical_activity_planned_today"]]
    unplanned_records = [record for record in trace["records"] if not record["was_physical_activity_planned_today"]]
    assert planned_records
    assert unplanned_records

    weather_and_energy_fields = {
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
    }
    required_fields = weather_and_energy_fields | {
        "hour",
        "activity_type",
        "current_location",
        "planned_destination",
        "decision_status",
        "active_constraints",
        "poi_accessibility",
    }

    for record in planned_records:
        transformed_rows = record["llm2_planned_pa_context"]
        original_pa_hours = [
            entry
            for entry in record["hourly_context_24h"]
            if entry["activity_type"] == "physical_activity"
            or entry.get("subtype") == "physical_activity"
        ]
        assert transformed_rows
        assert len(transformed_rows) == len(original_pa_hours)
        for transformed, original in zip(transformed_rows, original_pa_hours):
            assert required_fields <= set(transformed)
            assert transformed["activity_type"] == "planned_physical_activity"
            assert transformed["decision_status"] == "not_yet_realized"
            assert transformed["planned_destination"] == original["current_location"]
            for field in weather_and_energy_fields:
                assert transformed[field] == original[field]

    for record in unplanned_records:
        assert record["llm2_planned_pa_context"] == []


def test_manifest_construct_update_parameters_match_runtime_records(tmp_path: Path) -> None:
    from state_assessment import (
        PSYCHOLOGICAL_CONSTRUCT_UPDATE_ALPHA,
        PSYCHOLOGICAL_CONSTRUCT_UPDATE_MAX_DAILY_CHANGE,
    )

    config, trace = _run_dry_simulation(tmp_path)
    manifest = json.loads((config.output_dir / "simulation_run_manifest.json").read_text(encoding="utf-8"))

    assert manifest["psychological_construct_update_alpha"] == PSYCHOLOGICAL_CONSTRUCT_UPDATE_ALPHA
    assert (
        manifest["psychological_construct_update_max_daily_change"]
        == PSYCHOLOGICAL_CONSTRUCT_UPDATE_MAX_DAILY_CHANGE
    )
    assert (
        manifest["state_assessment"]["psychological_construct_update_alpha"]
        == manifest["psychological_construct_update_alpha"]
    )
    assert (
        manifest["state_assessment"]["psychological_construct_update_max_daily_change"]
        == manifest["psychological_construct_update_max_daily_change"]
    )
    for record in trace["records"]:
        assert record["psychological_construct_update_alpha"] == manifest["psychological_construct_update_alpha"]
        assert (
            record["psychological_construct_update_max_daily_change"]
            == manifest["psychological_construct_update_max_daily_change"]
        )
