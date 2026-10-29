"""Synthetic regression checks; never load research inputs or live outputs."""

from copy import deepcopy

import pytest

from Analysis.empirical_context_binary_v1_2 import (
    binary_class, classify_records, load_run, summarize, wilson,
)
from Analysis.final_h1_h4_analysis import classify_record


def synthetic_day(day=0, *, downtime=True, illness=None):
    hours = [{"hour": h, "activity_type": "downtime" if downtime and h in (17, 18) else "other",
              "feels_like_c": 20, "is_wet": False, "wind_m_s": 3,
              "energy_category": "high",
              "poi_accessibility": {"indoor_activity": {"travel_times_min": {
                  "walk": 10, "bike": 12, "car": 40}}},
              "active_constraints": []} for h in range(24)]
    if illness:
        hours[8]["active_constraints"] = [{"type": "AcuteIllnessConstraint", "intensity": illness}]
    record = {"persona_id": "synthetic_a", "day_index": day,
              "calendar_date": f"2026-01-{day+1:02d}", "phase": "normal",
              "was_physical_activity_planned_today": False, "planned_physical_activity": None,
              "pa_decision": {"decision_label": "skip_activity", "duration_min": 0,
                              "contextual_pa_probability": 0.37, "effective_pa_probability": 0.37,
                              "sampled_decision_probability": 0.63,
                              "decision_sampling_random_value": 0.81},
              "closed_loop_update": {"activity_done": False}}
    context = {k: record[k] for k in ("persona_id", "day_index", "calendar_date")}
    context["hourly_context_24h"] = hours
    return record, context


def classify(record, context):
    return classify_records([record], [context], 14, {"synthetic_a": "M1"})[0]


@pytest.mark.parametrize("score,expected", [(2, "supportive"), (1, "supportive"),
    (0, "non_supportive"), (-1, "non_supportive"), (-2, "non_supportive")])
def test_binary_threshold(score, expected):
    assert binary_class(score) == expected


@pytest.mark.parametrize("score", [None, float("nan"), float("inf"), -float("inf"), "1", True, {}, []])
def test_invalid_scores_reported(score):
    with pytest.raises(ValueError, match="final_context_score"):
        binary_class(score)


def test_no_downtime_retained_in_primary_denominator():
    record, context = synthetic_day(downtime=False)
    result = classify(record, context)
    assert result["final_context_score"] == -2
    assert result["binary_context_class"] == "non_supportive"
    totals = summarize([result])
    row = next(r for r in totals if r["seed"] == "all" and r["classification"] == "binary"
               and r["category"] == "non_supportive")
    assert (row["days"], row["pa_days"], row["no_downtime_days"]) == (1, 0, 1)


@pytest.mark.parametrize("illness,score,old", [("low", 0, "mixed_neutral"),
    ("medium", -2, "hindering"), ("high", -2, "hindering")])
def test_illness_overrides_unchanged(illness, score, old):
    record, context = synthetic_day(illness=illness)
    result = classify(record, context)
    original = classify_record({**record, "hourly_context_24h": context["hourly_context_24h"]})
    assert result["final_context_score"] == original["final_context_score"] == score
    assert result["context_class"] == old
    assert result["binary_context_class"] == "non_supportive"


def test_source_decisions_probabilities_duration_and_scores_unchanged():
    pairs = [synthetic_day(i, downtime=i != 1) for i in range(3)]
    pairs[2][0]["pa_decision"].update(decision_label="extra_activity", duration_min=45)
    pairs[2][0]["closed_loop_update"]["activity_done"] = True
    records, contexts = map(list, zip(*pairs))
    before = deepcopy((records, contexts))
    rows = classify_records(records, contexts, 14, {"synthetic_a": "M1"})
    assert (records, contexts) == before
    assert len(rows) == len(records) == 3
    assert [r["day_index"] for r in rows] == [0, 1, 2]
    for row, record, context in zip(rows, records, contexts):
        assert row["source_pa_decision"] == record["pa_decision"]
        original = classify_record({**record, "hourly_context_24h": context["hourly_context_24h"]})
        for k in ("weather_score", "energy_score", "accessibility_score", "time_score", "final_context_score"):
            assert row[k] == original[k] or (row[k] != row[k] and original[k] != original[k])
    for scheme in ("old", "binary"):
        group = [r for r in summarize(rows) if r["seed"] == "all" and r["classification"] == scheme]
        assert sum(r["days"] for r in group) == 3
        assert sum(r["pa_days"] for r in group) == 1


def test_missing_score_from_original_classifier_fails_explicitly():
    record, context = synthetic_day()
    for hour in context["hourly_context_24h"]:
        hour["poi_accessibility"] = {}
    with pytest.raises(ValueError, match="Seed 14, M1, day 0: Missing or invalid final_context_score"):
        classify(record, context)


@pytest.mark.parametrize("case", ["duplicate_record", "duplicate_context", "missing_context", "wrong_date", "missing_hour"])
def test_invalid_joins_rejected(case):
    record, context = synthetic_day()
    records, contexts = [record], [context]
    if case == "duplicate_record": records.append(record)
    if case == "duplicate_context": contexts.append(context)
    if case == "missing_context": contexts.clear()
    if case == "wrong_date": context["calendar_date"] = "2026-02-01"
    if case == "missing_hour": context["hourly_context_24h"].pop()
    with pytest.raises(ValueError):
        classify_records(records, contexts, 14, {"synthetic_a": "M1"})


def test_wilson_known_reference_and_empty_category():
    assert wilson(5, 10) == pytest.approx((0.2365930905, 0.7634069095))
    assert wilson(0, 0) == (None, None)


def test_synthetic_run_validation(tmp_path):
    import json
    records, contexts = [], []
    for persona in range(4):
        for day in range(90):
            record, context = synthetic_day()
            for row in (record, context):
                row.update(persona_id=f"synthetic_{persona}", day_index=day)
            records.append(record)
            contexts.append(context)
    payloads = {"run_config.json": dict(base_seed=14, n_days=90, n_personas=4, empirical_pa_v1_2=True),
                "simulation_run_manifest.json": {"run_status": "success"},
                "full_simulation_trace.json": {"records": records},
                "contexts_compact.json": {"llm_contexts": contexts}}
    for name, payload in payloads.items():
        (tmp_path/name).write_text(json.dumps(payload), encoding="utf-8")
    assert len(load_run(tmp_path, 14)[0]) == 360
    with pytest.raises(ValueError):
        load_run(tmp_path, 96)
    records[-1]["day_index"] = 0
    (tmp_path/"full_simulation_trace.json").write_text(json.dumps({"records": records}), encoding="utf-8")
    with pytest.raises(ValueError, match="unique days"):
        load_run(tmp_path, 14)


def test_end_to_end_720_synthetic_observations(tmp_path, monkeypatch):
    import csv
    import json
    import sys
    from Analysis.empirical_context_binary_v1_2 import main, source_hashes

    roots = {}
    for seed in (14, 96):
        root = tmp_path / str(seed)
        root.mkdir()
        roots[seed] = root
        records, contexts = [], []
        for persona in range(4):
            for day in range(90):
                record, context = synthetic_day(downtime=day % 2 == 0)
                for row in (record, context):
                    row.update(persona_id=f"synthetic_private_{persona}", day_index=day)
                records.append(record)
                contexts.append(context)
        payloads = {"run_config.json": dict(base_seed=seed, n_days=90, n_personas=4, empirical_pa_v1_2=True),
                    "simulation_run_manifest.json": {"run_status": "success"},
                    "full_simulation_trace.json": {"records": records},
                    "contexts_compact.json": {"llm_contexts": contexts}}
        for name, payload in payloads.items():
            (root/name).write_text(json.dumps(payload), encoding="utf-8")
        (root/"daily_decision_log.csv").write_text("synthetic,unchanged\n", encoding="utf-8")
    before = {seed: source_hashes(root) for seed, root in roots.items()}
    output = tmp_path / "aggregates"
    monkeypatch.setattr(sys, "argv", ["analysis", "--seed14-dir", str(roots[14]),
        "--seed96-dir", str(roots[96]), "--output-dir", str(output)])
    main()
    assert before == {seed: source_hashes(root) for seed, root in roots.items()}
    table = list(csv.DictReader((output/"summary.csv").open(encoding="utf-8")))
    for scheme in ("old", "binary"):
        group = [r for r in table if r["seed"] == "all" and r["classification"] == scheme]
        assert sum(int(r["days"]) for r in group) == 720
        assert sum(int(r["no_downtime_days"]) for r in group) == 360
    assert all("synthetic_private" not in file.read_text(encoding="utf-8") for file in output.iterdir())
    with pytest.raises(FileExistsError):
        main()
