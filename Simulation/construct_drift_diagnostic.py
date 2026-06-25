from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping

DECISIONS = ("skip_activity", "do_planned_activity", "adapt_activity", "extra_activity")


def _load_json_cell(value: str) -> Any:
    try:
        return json.loads(value)
    except Exception:
        return None


def _read_closed_loop(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for row in rows:
        row = dict(row)
        row["delta_applied"] = _load_json_cell(row.get("psychological_construct_update_delta_applied", "{}")) or {}
        row["previous"] = _load_json_cell(row.get("previous_psychological_constructs", "{}")) or {}
        row["updated"] = _load_json_cell(row.get("updated_psychological_constructs", "{}")) or {}
        row["planned"] = str(row.get("was_physical_activity_planned_today", "")).lower() == "true"
        out.append(row)
    return out


def summarize_construct_drift(output_dir: Path) -> dict[str, Any]:
    closed_path = output_dir / "pipeline_closed_loop_daily_log.csv"
    if not closed_path.exists():
        raise FileNotFoundError(closed_path)
    rows = _read_closed_loop(closed_path)
    series: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        persona = str(row["persona_id"])
        for construct, previous in row["previous"].items():
            series[(persona, construct)].append({
                "day_index": int(row["day_index"]),
                "previous": float(previous),
                "updated": float(row["updated"].get(construct, previous)),
                "delta": float(row["delta_applied"].get(construct, 0.0)),
                "planned": bool(row["planned"]),
                "decision_label": str(row.get("decision_label", "")),
            })
    persona_results = []
    by_construct: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (persona, construct), items in sorted(series.items()):
        items.sort(key=lambda x: x["day_index"])
        deltas = [x["delta"] for x in items]
        values = [items[0]["previous"], *[x["updated"] for x in items]]
        res = {
            "persona_id": persona,
            "construct": construct,
            "initial_value": values[0],
            "final_value": values[-1],
            "absolute_change": abs(values[-1] - values[0]),
            "mean_daily_applied_delta": mean(deltas) if deltas else 0.0,
            "mean_absolute_daily_applied_delta": mean(abs(d) for d in deltas) if deltas else 0.0,
            "min_value": min(values),
            "max_value": max(values),
            "proportion_negative_updates": sum(d < 0 for d in deltas) / len(deltas) if deltas else 0.0,
            "proportion_zero_updates": sum(d == 0 for d in deltas) / len(deltas) if deltas else 0.0,
            "proportion_positive_updates": sum(d > 0 for d in deltas) / len(deltas) if deltas else 0.0,
            "updates_at_negative_bound": sum(d <= -0.05 + 1e-9 for d in deltas),
            "updates_at_positive_bound": sum(d >= 0.05 - 1e-9 for d in deltas),
        }
        for label, pred in [("planned_pa_days", lambda x: x["planned"]), ("unplanned_pa_days", lambda x: not x["planned"]), *[(d, lambda x, d=d: x["decision_label"] == d) for d in DECISIONS]]:
            subset = [x["delta"] for x in items if pred(x)]
            res[f"{label}_mean_delta"] = mean(subset) if subset else None
            res[f"{label}_negative_updates"] = sum(d < 0 for d in subset)
        persona_results.append(res)
        by_construct[construct].append(res)
    aggregate = []
    for construct, items in sorted(by_construct.items()):
        aggregate.append({"construct": construct, "series_count": len(items), "mean_absolute_change": mean(x["absolute_change"] for x in items), "mean_daily_applied_delta": mean(x["mean_daily_applied_delta"] for x in items)})
    all_series = persona_results
    stability = {f"within_{thr:.2f}": (sum(x["absolute_change"] <= thr for x in all_series) / len(all_series) * 100 if all_series else 0.0) for thr in (0.05, 0.10, 0.20)}
    systematic = [x for x in aggregate if abs(x["mean_daily_applied_delta"]) >= 0.005]
    neg = sum(x["proportion_negative_updates"] for x in all_series)
    pos = sum(x["proportion_positive_updates"] for x in all_series)
    return {"persona_level_results": persona_results, "aggregate_by_construct": aggregate, "stability_percentages": stability, "constructs_with_systematic_directional_drift": systematic, "positive_negative_asymmetry_ratio": (neg / pos if pos else None)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize construct drift from completed PA simulation outputs.")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    summary = summarize_construct_drift(args.output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.json_out:
        args.json_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
