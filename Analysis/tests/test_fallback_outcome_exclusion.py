import json

import pandas as pd
import pytest

from Analysis import final_h1_h4_analysis as h1h4
from Analysis.empirical_context_binary_v1_2 import is_technical_fallback
from Analysis import plot_empirical_pa_v1_2_manuscript_figures as manuscript_figures


def _decision_rows() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "scenario": "Supportive",
            "planned": False,
            "context_class": "Supportive",
            "decision_label": "skip_activity",
            "activity_performed_bool": False,
            "technical_fallback_bool": False,
            "week_index": 0,
        },
        {
            "scenario": "Supportive",
            "planned": False,
            "context_class": "Supportive",
            "decision_label": "skip_activity",
            "activity_performed_bool": pd.NA,
            "technical_fallback_bool": True,
            "week_index": 0,
        },
        {
            "scenario": "Hindering",
            "planned": False,
            "context_class": "Hindering",
            "decision_label": "skip_activity",
            "activity_performed_bool": False,
            "technical_fallback_bool": False,
            "week_index": 0,
        },
        {
            "scenario": "Hindering",
            "planned": False,
            "context_class": "Hindering",
            "decision_label": "extra_activity",
            "activity_performed_bool": True,
            "technical_fallback_bool": False,
            "week_index": 0,
        },
    ])


def test_h3_tables_use_evaluable_days_and_report_fallback_quality() -> None:
    frame = _decision_rows()
    table = h1h4.tabulate_decisions(frame, ["scenario"])
    supportive = table.loc[table["scenario"].eq("Supportive")].iloc[0]
    assert supportive["n_days"] == 2
    assert supportive["analysis_days"] == 1
    assert supportive["technical_fallback_days"] == 1
    assert supportive["technical_fallback_proportion"] == pytest.approx(0.5)
    assert supportive["skip_activity_n"] == 1
    assert supportive["skip_activity_pct"] == 100
    intervals = h1h4.add_proportion_confidence_intervals(table)
    assert intervals.loc[
        intervals["scenario"].eq("Supportive"), "skip_activity_ci_lower_pct"
    ].iloc[0] == pytest.approx(20.655, abs=0.001)

    difference = h1h4.rate_difference(
        frame,
        "Supportive",
        "Hindering",
        lambda rows: ~rows["planned"],
        "extra_activity",
        "unplanned",
    )
    assert difference["n_a"] == 1
    assert difference["simulated_days_a"] == 2
    assert difference["technical_fallback_days_a"] == 1
    assert difference["rate_a_pct"] == 0
    assert difference["n_b"] == 2
    assert difference["rate_b_pct"] == 50


def test_h3_and_h4_inferential_paths_exclude_fallbacks(monkeypatch) -> None:
    seen = []

    def capture(frame, *args, **kwargs):
        seen.append(frame.copy())
        analysis = args[-1] if args else kwargs.get("analysis", "synthetic")
        return {"analysis": analysis, "p_value": float("nan")}

    def capture_posthoc(frame, *args, **kwargs):
        seen.append(frame.copy())
        return pd.DataFrame()

    monkeypatch.setattr(h1h4, "paired_weekly_binary_test", capture)
    monkeypatch.setattr(h1h4, "one_way_binary_anova", capture)
    monkeypatch.setattr(h1h4, "pairwise_binary_posthoc", capture_posthoc)

    planned_rows = _decision_rows().copy()
    planned_rows.loc[planned_rows.index[0], "planned"] = True
    planned_rows.loc[planned_rows.index[1], "planned"] = True
    h1h4.calculate_h3_h4_inferential_tests(planned_rows)

    assert seen
    assert all(not frame["technical_fallback_bool"].any() for frame in seen)


@pytest.mark.parametrize(
    ("decision_fields", "expected_fallback"),
    [
        ({}, False),
        (
            {
                "technical_fallback": True,
                "decision_origin": "technical_validation_fallback",
            },
            True,
        ),
    ],
)
def test_historical_and_marked_run_loading(tmp_path, decision_fields, expected_fallback):
    scenario_dir = tmp_path / "scenario"
    scenario_dir.mkdir()
    decision = {"decision_label": "skip_activity", **decision_fields}
    pd.DataFrame([{
        "persona_id": "synthetic_persona",
        "day_index": 0,
        "calendar_date": "2026-01-01",
        "was_physical_activity_planned_today": False,
        "decision_label": "skip_activity",
        "activity_performed": False,
    }]).to_csv(scenario_dir / "daily_decision_log.csv", index=False)
    pd.DataFrame(columns=["construct", "day_index"]).to_csv(
        scenario_dir / "longitudinal_constructs.csv", index=False
    )
    (scenario_dir / "full_simulation_trace.json").write_text(
        json.dumps({
            "records": [{
                "persona_id": "synthetic_persona",
                "day_index": 0,
                "pa_decision": decision,
            }]
        }),
        encoding="utf-8",
    )
    for filename, payload in (
        ("run_config.json", {}),
        ("simulation_run_manifest.json", {}),
        ("persona_metadata.json", {}),
    ):
        (scenario_dir / filename).write_text(
            json.dumps(payload), encoding="utf-8"
        )

    loaded = h1h4.load_scenario("synthetic", scenario_dir, tmp_path)
    assert loaded.daily["technical_fallback_bool"].tolist() == [expected_fallback]
    assert is_technical_fallback(decision) is expected_fallback
    if expected_fallback:
        assert pd.isna(loaded.daily["activity_performed_bool"].iloc[0])
    else:
        assert not loaded.daily["activity_performed_bool"].iloc[0]


def test_context_and_probability_figures_accept_fallback_denominators(
    tmp_path, monkeypatch
):
    context_rows = []
    for seed in (14, 96):
        for medoid in ("all", "M1", "M2", "M3", "M4"):
            for category in ("supportive", "non_supportive"):
                total = 90
                fallback = 1
                denominator = total - fallback
                context_rows.append({
                    "seed": seed,
                    "medoid": medoid,
                    "context": category,
                    "person_days": total,
                    "pa_rate_denominator_days": denominator,
                    "pa_days": 40,
                    "pa_proportion": 40 / denominator,
                    "wilson95_low": 0.3,
                    "wilson95_high": 0.6,
                    "technical_fallback_days": fallback,
                    "technical_fallback_proportion": fallback / total,
                })
    for medoid in ("all",):
        for category in ("supportive", "non_supportive"):
            context_rows.append({
                "seed": "all",
                "medoid": medoid,
                "context": category,
                "person_days": 180,
                "pa_rate_denominator_days": 178,
                "pa_days": 80,
                "pa_proportion": 80 / 178,
                "wilson95_low": 0.35,
                "wilson95_high": 0.55,
                "technical_fallback_days": 2,
                "technical_fallback_proportion": 2 / 180,
            })
    probability_rows = []
    for seed in ("all", 14, 96):
        for context in ("all", "supportive", "non_supportive"):
            total = 180 if context == "all" else 90
            fallback = 2 if context == "all" else 1
            row = {
                "seed": seed,
                "context": context,
                "person_days": total,
                "probability_summary_days": total - fallback,
                "technical_fallback_days": fallback,
                "technical_fallback_proportion": fallback / total,
            }
            for column, value in (
                ("behavior_policy_pa_prior", 0.4),
                ("contextual_pa_probability", 0.5),
                ("effective_pa_probability", 0.3),
            ):
                row[f"mean_{column}"] = value
                row[f"ci95_low_{column}"] = value - 0.1
                row[f"ci95_high_{column}"] = value + 0.1
            probability_rows.append(row)

    monkeypatch.setattr(manuscript_figures, "OUT", tmp_path, raising=False)
    manuscript_figures.fig6(pd.DataFrame(context_rows))
    manuscript_figures.fig7(pd.DataFrame(probability_rows))

    assert (tmp_path / "Figure_6_PA_by_Context.png").is_file()
    assert (tmp_path / "Figure_7_Probability_Pathway.png").is_file()
