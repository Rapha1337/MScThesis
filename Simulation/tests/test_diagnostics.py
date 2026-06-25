from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))


def test_llm1_repeatability_comparison_stats() -> None:
    from llm1_repeatability_diagnostic import compare_probability_outputs

    results = [
        {"serialized_input_hash": "same", "raw_output_hash": "a", "parsed_policy": {"do_planned_activity": 0.2, "adapt_activity": 0.3, "skip_activity": 0.4, "extra_activity": 0.1}},
        {"serialized_input_hash": "same", "raw_output_hash": "b", "parsed_policy": {"do_planned_activity": 0.25, "adapt_activity": 0.25, "skip_activity": 0.4, "extra_activity": 0.1}},
    ]
    summary = compare_probability_outputs(results)
    assert summary["input_hashes_identical"] is True
    assert summary["raw_output_hashes_identical"] is False
    assert summary["parsed_policies_identical"] is False
    assert summary["category_statistics"]["do_planned_activity"]["maximum_absolute_difference"] == 0.04999999999999999


def test_construct_drift_summary_reads_closed_loop_log(tmp_path: Path) -> None:
    from construct_drift_diagnostic import summarize_construct_drift

    path = tmp_path / "pipeline_closed_loop_daily_log.csv"
    fields = ["persona_id", "day_index", "decision_label", "was_physical_activity_planned_today", "previous_psychological_constructs", "updated_psychological_constructs", "psychological_construct_update_delta_applied"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerow({"persona_id": "p1", "day_index": 0, "decision_label": "skip_activity", "was_physical_activity_planned_today": "False", "previous_psychological_constructs": '{"intention": 0.5}', "updated_psychological_constructs": '{"intention": 0.45}', "psychological_construct_update_delta_applied": '{"intention": -0.05}'})
        writer.writerow({"persona_id": "p1", "day_index": 1, "decision_label": "do_planned_activity", "was_physical_activity_planned_today": "True", "previous_psychological_constructs": '{"intention": 0.45}', "updated_psychological_constructs": '{"intention": 0.47}', "psychological_construct_update_delta_applied": '{"intention": 0.02}'})
    summary = summarize_construct_drift(tmp_path)
    result = summary["persona_level_results"][0]
    assert result["construct"] == "intention"
    assert result["initial_value"] == 0.5
    assert result["final_value"] == 0.47
    assert result["updates_at_negative_bound"] == 1
    assert summary["stability_percentages"]["within_0.05"] == 100.0
