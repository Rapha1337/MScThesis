"""Synthetic tests for the final aggregate PA v1.2 analysis."""

import math

import pandas as pd
import pytest

from Analysis.final_empirical_pa_v1_2_analysis import (
    agreement_summary,
    build_report,
    cluster_bootstrap_ci,
    context_pa_summary,
    gee_context_model,
    probability_summary,
    public_simulation_summary,
    software_provenance,
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
