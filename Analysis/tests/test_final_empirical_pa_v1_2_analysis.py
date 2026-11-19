"""Synthetic tests for the final aggregate PA v1.2 analysis."""

import math

import pandas as pd
import pytest

from Analysis.final_empirical_pa_v1_2_analysis import (
    _numeric_or_nan,
    agreement_summary,
    build_report,
    cluster_bootstrap_ci,
    context_pa_summary,
    gee_context_model,
    probability_summary,
    public_simulation_summary,
    software_provenance,
)
from Analysis.t1_medoid_pa_validation_v1_2 import (
    daily_rows_from_trace,
    summarize_horizons,
)


def synthetic_daily() -> pd.DataFrame:
    rows = []
    for seed in (14, 96):
        for medoid_index in range(4):
            medoid = f"M{medoid_index + 1}"
            for day in range(12):
                supportive = day % 3 != 0
                prior = 0.35 + medoid_index * 0.05
                contextual = prior + (0.15 if supportive else -0.12)
                effective = contextual if supportive else contextual - 0.05
                rows.append({
                    "seed": seed,
                    "medoid": medoid,
                    "day_index": day,
                    "binary_context_class": "supportive" if supportive else "non_supportive",
                    "activity_performed": int((day + medoid_index + seed) % 4 < (3 if supportive else 1)),
                    "no_downtime": not supportive and day == 0,
                    "behavior_policy_pa_prior": prior,
                    "contextual_pa_probability": contextual,
                    "effective_pa_probability": effective,
                    "context_shift": contextual - prior,
                    "feasibility_shift": effective - contextual,
                    "total_probability_shift": effective - prior,
                })
    return pd.DataFrame(rows)


def test_context_summary_conserves_every_synthetic_observation() -> None:
    daily = synthetic_daily()
    summary = context_pa_summary(daily)
    overall = summary[(summary["seed"] == "all") & (summary["medoid"] == "all")]
    assert overall["person_days"].sum() == len(daily) == 96
    assert overall["pa_days"].sum() == daily["activity_performed"].sum()
    assert overall["no_downtime_days"].sum() == daily["no_downtime"].sum() == 8
    for seed in (14, 96):
        for medoid in ("M1", "M2", "M3", "M4"):
            rows = summary[(summary["seed"] == seed) & (summary["medoid"] == medoid)]
            assert rows["person_days"].sum() == 12
            assert rows["pa_rate_denominator_days"].sum() == 12


def test_fallback_is_excluded_from_context_rate_models_and_probability_means() -> None:
    daily = synthetic_daily()
    daily["technical_fallback"] = False
    fallback_index = daily.index[0]
    daily.loc[fallback_index, "technical_fallback"] = True
    daily.loc[fallback_index, "activity_performed"] = None
    for column in (
        "effective_pa_probability",
        "feasibility_shift",
        "total_probability_shift",
    ):
        daily.loc[fallback_index, column] = math.nan

    context = context_pa_summary(daily)
    all_supportive = context[
        context["seed"].eq("all")
        & context["medoid"].eq("all")
        & context["context"].eq(daily.loc[fallback_index, "binary_context_class"])
    ].iloc[0]
    category_days = int(
        daily["binary_context_class"].eq(daily.loc[fallback_index, "binary_context_class"]).sum()
    )
    assert all_supportive["person_days"] == category_days
    assert all_supportive["pa_rate_denominator_days"] == category_days - 1
    assert all_supportive["technical_fallback_days"] == 1
    assert all_supportive["technical_fallback_proportion"] == pytest.approx(
        1 / category_days
    )

    model = gee_context_model(daily)
    assert set(model["observations"]) == {95}
    assert set(model["technical_fallback_days"]) == {1}
    probabilities = probability_summary(daily)
    all_days = probabilities[
        probabilities["seed"].eq("all") & probabilities["context"].eq("all")
    ].iloc[0]
    assert all_days["person_days"] == 96
    assert all_days["probability_summary_days"] == 95
    assert all_days["technical_fallback_days"] == 1
    assert all_days["mean_effective_pa_probability"] == pytest.approx(
        daily.loc[~daily["technical_fallback"], "effective_pa_probability"].mean()
    )
    assert math.isnan(_numeric_or_nan(None))


def test_t1_flattening_keeps_fallback_outcome_missing_and_skips_observed() -> None:
    records = []
    empirical_rows = []
    for persona in range(4):
        persona_id = f"synthetic_persona_{persona}"
        empirical_rows.append({
            "persona_id": persona_id,
            "cluster": persona,
            "participant_id": f"synthetic_{persona}",
            "occupation": "synthetic",
            "empirical_mvpa_hours_week": 1.0,
            "empirical_total_pa_hours_week": 2.0,
        })
        for day in range(90):
            decision = {
                "decision_label": "skip_activity",
                "duration_min": 0,
                "start_hour": None,
            }
            if day == 2:
                decision.update(
                    technical_fallback=True,
                    decision_origin="technical_validation_fallback",
                    effective_pa_probability=None,
                )
            records.append({
                "persona_id": persona_id,
                "day_index": day,
                "calendar_date": f"2026-01-{day % 28 + 1:02d}",
                "week_index": day // 7,
                "phase": "normal",
                "weekday": day % 7,
                "was_physical_activity_planned_today": False,
                "planned_physical_activity": None,
                "pa_decision": decision,
                "closed_loop_update": {"activity_done": False},
            })
    empirical = pd.DataFrame(empirical_rows)

    daily = daily_rows_from_trace({"records": records}, empirical)

    persona_days = daily[daily["persona_id"].eq("synthetic_persona_0")].sort_values(
        "day_index"
    )
    assert len(daily) == 360
    assert persona_days["technical_fallback"].iloc[:3].tolist() == [False, False, True]
    assert persona_days["activity_performed"].iloc[:2].tolist() == [False, False]
    assert pd.isna(persona_days["activity_performed"].iloc[2])
    assert persona_days["pa_minutes"].iloc[:2].tolist() == [0.0, 0.0]
    assert pd.isna(persona_days["pa_minutes"].iloc[2])
    horizon = summarize_horizons(daily, empirical)
    first_persona = horizon[
        horizon["persona_id"].eq("synthetic_persona_0")
        & horizon["horizon_days"].eq(7)
    ].iloc[0]
    assert first_persona["simulated_days"] == 7
    assert first_persona["pa_rate_denominator_days"] == 6
    assert first_persona["technical_fallback_days"] == 1
    assert first_persona["technical_fallback_proportion"] == pytest.approx(1 / 7)
    assert first_persona["active_days"] == 0


def test_cluster_bootstrap_resamples_complete_medoids_deterministically() -> None:
    daily = synthetic_daily()
    first = cluster_bootstrap_ci(daily, lambda frame: float(frame["context_shift"].mean()))
    second = cluster_bootstrap_ci(daily, lambda frame: float(frame["context_shift"].mean()))
    assert first == second
    low, high, clusters, replicates = first
    assert clusters == 4
    assert replicates == 4**4
    assert low <= daily["context_shift"].mean() <= high


def test_probability_summary_reports_paired_stage_changes() -> None:
    daily = synthetic_daily()
    summary = probability_summary(daily)
    assert len(summary) == 9
    supportive = summary[(summary["seed"] == "all") & (summary["context"] == "supportive")].iloc[0]
    non_supportive = summary[(summary["seed"] == "all") & (summary["context"] == "non_supportive")].iloc[0]
    assert supportive["mean_context_shift"] == pytest.approx(0.15)
    assert supportive["mean_feasibility_shift"] == pytest.approx(0.0)
    assert non_supportive["mean_context_shift"] == pytest.approx(-0.12)
    assert non_supportive["mean_feasibility_shift"] == pytest.approx(-0.05)
    assert all(summary["medoid_clusters"] == 4)


def test_probability_summary_documents_three_contributing_clusters() -> None:
    daily = synthetic_daily()
    keep = ~(
        daily["seed"].eq(14)
        & daily["medoid"].eq("M4")
        & daily["binary_context_class"].eq("non_supportive")
    )
    summary = probability_summary(daily.loc[keep].copy())
    row = summary[(summary["seed"] == 14) & (summary["context"] == "non_supportive")].iloc[0]
    assert row["medoid_clusters"] == 3
    assert row["bootstrap_replicates"] == 3**3


def test_gee_uses_cluster_aware_primary_and_sensitivity_models() -> None:
    result = gee_context_model(synthetic_daily())
    assert set(result["model"]) == {
        "primary_medoid_cluster_bias_reduced",
        "sensitivity_seed_medoid_cluster_robust",
    }
    assert set(result["contrast"]) == {"supportive_vs_non_supportive", "seed96_vs_seed14"}
    assert set(result.loc[result["model"].str.startswith("primary"), "clusters"]) == {4}
    assert set(result.loc[result["model"].str.startswith("sensitivity"), "clusters"]) == {8}
    assert result[["odds_ratio", "ci95_low", "ci95_high"]].map(math.isfinite).all().all()


def test_agreement_averages_seeds_before_combined_inference() -> None:
    rows = []
    for seed, offset in ((14, 0.0), (96, 0.4)):
        for index in range(4):
            rows.append({
                "seed": seed,
                "medoid": f"M{index + 1}",
                "t1_mvpa_hours_week": 1.0 + index,
                "t1_total_pa_hours_week": 2.0 + index,
                "simulated_pa_hours_week": 1.2 + index + offset,
            })
    result = agreement_summary(pd.DataFrame(rows))
    combined = result[(result["seed"] == "seed_mean") & (result["reference"] == "T1_MVPA")].iloc[0]
    assert combined["medoids"] == 4
    assert combined["mean_bias_hours_week"] == pytest.approx(0.4)
    assert combined["mae_hours_week"] == pytest.approx(0.4)
    assert combined["spearman_rho"] == pytest.approx(1.0)


def test_public_t1_exports_are_aggregate_and_non_reconstructive() -> None:
    rows = []
    for seed, offset in ((14, 0.0), (96, 0.4)):
        for index in range(4):
            rows.append({
                "seed": seed,
                "medoid": f"M{index + 1}",
                "t1_mvpa_hours_week": 1.0 + index,
                "t1_total_pa_hours_week": 2.0 + index,
                "simulated_pa_hours_week": 1.2 + index + offset,
                "pa_days": 10 + index,
                "mean_duration_min_pa_day": 30.0 + index,
            })
    agreement = pd.DataFrame(rows)
    public = public_simulation_summary(agreement)
    stats = agreement_summary(agreement)
    report = build_report(
        context_pa_summary(synthetic_daily()),
        gee_context_model(synthetic_daily()),
        probability_summary(synthetic_daily()),
        public,
        stats,
    )
    forbidden_columns = {
        "medoid",
        "t1_mvpa_hours_week",
        "t1_total_pa_hours_week",
        "error_vs_t1_mvpa",
        "error_vs_t1_total_pa",
    }
    assert len(public) == 2
    assert forbidden_columns.isdisjoint(public.columns)
    assert "T1-MVPA h/W" not in report
    assert "T1-Gesamt-PA h/W" not in report
    assert "Fehler vs. MVPA" not in report
    assert "Fehler vs. Gesamt" not in report


def test_software_provenance_reports_actual_versions_and_deviations() -> None:
    provenance = software_provenance()
    assert set(provenance["actual"]) == {"python", "statsmodels", "scipy", "numpy", "pandas"}
    assert all(provenance["actual"].values())
    for package, expected in provenance["reference_analysis_packages"].items():
        actual = provenance["actual"][package]
        if actual == expected:
            assert package not in provenance["deviations_from_reference"]
        else:
            assert provenance["deviations_from_reference"][package] == {
                "reference": expected,
                "actual": actual,
            }


def test_aggregate_tables_contain_aliases_only() -> None:
    daily = synthetic_daily()
    context = context_pa_summary(daily)
    probabilities = probability_summary(daily)
    combined = "\n".join((context.to_csv(index=False), probabilities.to_csv(index=False)))
    assert "persona_id" not in combined
    assert "participant_id" not in combined
    assert "T1_Medoid" not in combined
