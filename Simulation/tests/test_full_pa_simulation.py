from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))


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


def test_full_pa_dry_run_carries_planned_activity_and_constructs_forward(tmp_path: Path) -> None:
    _, trace = _run_dry_simulation(tmp_path)

    records_by_persona: dict[str, list[dict]] = {}
    for record in trace["records"]:
        records_by_persona.setdefault(record["persona_id"], []).append(record)

    assert set(records_by_persona) == {"StudentPersona_01", "StudentPersona_02"}
    for records in records_by_persona.values():
        records.sort(key=lambda item: item["day_index"])
        day_1, day_2 = records
        assert day_2["planned_activity_for_day"] == day_1["closed_loop_update"][
            "planned_activity_next_day"
        ]
        assert day_2["psychological_constructs_before_update"] == day_1[
            "psychological_constructs_after_update"
        ]


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
        planned_activity=record["planned_activity_for_day"],
    )

    assert pa_input["persona_id"] == compact_context["persona_id"]
    assert pa_input["day_index"] == compact_context["day_index"]
    assert len(pa_input["daily_context"]["hourly_context_24h"]) == 24
