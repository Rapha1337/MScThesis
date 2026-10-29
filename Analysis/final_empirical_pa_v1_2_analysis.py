"""Final read-only analysis of the existing empirical PA v1.2 runs.

The script reuses the binary context classifier and the v1.2 validation flattener.
It never calls an LLM or simulation routine and exports aggregates under M1-M4 only.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import itertools
import json
import math
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

ANALYSIS_DIR = Path(__file__).resolve().parent
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.append(str(ANALYSIS_DIR))

try:
    from .empirical_context_binary_v1_2 import (
        binary_class,
        classify_records,
        load_run,
        wilson,
    )
    from .t1_medoid_pa_validation_v1_2 import daily_rows_from_trace
except ImportError:  # Direct script invocation.
    from empirical_context_binary_v1_2 import (
        binary_class,
        classify_records,
        load_run,
        wilson,
    )
    from t1_medoid_pa_validation_v1_2 import daily_rows_from_trace


SOURCE_FILES = (
    "run_config.json",
    "simulation_run_manifest.json",
    "full_simulation_trace.json",
    "contexts_compact.json",
    "daily_decision_log.csv",
    "persona_metadata.json",
)
CONTEXT_ORDER = ("supportive", "non_supportive")
STAGE_COLUMNS = (
    "behavior_policy_pa_prior",
    "contextual_pa_probability",
    "effective_pa_probability",
)
REFERENCE_SOFTWARE_VERSIONS = {
    "statsmodels": "0.14.6",
    "scipy": "1.13.1",
    "numpy": "1.26.4",
    "pandas": "2.2.2",
}


def source_hashes(root: Path) -> dict[str, str]:
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in SOURCE_FILES}


def software_provenance() -> dict[str, Any]:
    actual = {
        "python": platform.python_version(),
        **{name: importlib.metadata.version(name) for name in REFERENCE_SOFTWARE_VERSIONS},
    }
    deviations = {
        name: {"reference": expected, "actual": actual[name]}
        for name, expected in REFERENCE_SOFTWARE_VERSIONS.items()
        if actual[name] != expected
    }
    return {
        "actual": actual,
        "reference_analysis_packages": REFERENCE_SOFTWARE_VERSIONS,
        "deviations_from_reference": deviations,
    }


def git_provenance() -> dict[str, Any]:
    repository = ANALYSIS_DIR.parent
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return {"git_commit": None, "git_worktree_dirty": None}
    return {"git_commit": commit, "git_worktree_dirty": dirty}


def _metadata_frame(root: Path) -> pd.DataFrame:
    payload = json.loads((root / "persona_metadata.json").read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for item in payload["personas"]:
        profile = item["profile_metadata"]
        rows.append(
            {
                "persona_id": item["persona_id"],
                "cluster": int(profile["cluster"]),
                "participant_id": str(profile["participant_id"]),
                "occupation": profile["occupational_status"],
                "empirical_mvpa_hours_week": float(profile["reported_mvpa_hours_per_week"]),
                "empirical_total_pa_hours_week": float(profile["reported_total_pa_hours_per_week"]),
            }
        )
    frame = pd.DataFrame(rows)
    if len(frame) != 4 or frame["persona_id"].nunique() != 4:
        raise ValueError("Expected exactly four unique medoid metadata records")
    return frame


def load_analysis_data(roots: dict[int, Path]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    runs = {seed: load_run(root, seed) for seed, root in roots.items()}
    personas = sorted({record["persona_id"] for record in runs[14][0]})
    if set(personas) != {record["persona_id"] for record in runs[96][0]}:
        raise ValueError("The two runs do not contain the same four medoids")
    aliases = {persona: f"M{index + 1}" for index, persona in enumerate(personas)}

    daily_frames: list[pd.DataFrame] = []
    agreement_frames: list[pd.DataFrame] = []
    reference: pd.DataFrame | None = None

    for seed, root in roots.items():
        records, contexts = runs[seed]
        empirical = _metadata_frame(root)
        current_reference = empirical.set_index("persona_id")[[
            "cluster", "empirical_mvpa_hours_week", "empirical_total_pa_hours_week"
        ]].sort_index()
        if reference is not None and not current_reference.equals(reference):
            raise ValueError("T1 reference metadata differ between seeds")
        reference = current_reference

        # Existing v1.2 validation logic validates decisions/durations and computes PA dose.
        validation = daily_rows_from_trace({"records": records}, empirical)
        validation_lookup = validation.set_index(["persona_id", "day_index"])
        classified = classify_records(records, contexts, seed, aliases)
        rows: list[dict[str, Any]] = []
        for result, record in zip(classified, records, strict=True):
            persona_id = str(record["persona_id"])
            day_index = int(record["day_index"])
            validated = validation_lookup.loc[(persona_id, day_index)]
            decision = record["pa_decision"]
            performed = bool(result["activity_performed"])
            if performed != bool(validated["activity_performed"]):
                raise ValueError("Context and validation routines disagree on PA outcome")
            if int(decision["duration_min"]) != int(validated["duration_min"]):
                raise ValueError("Context and validation routines disagree on PA duration")
            row = {
                "seed": int(seed),
                "medoid": aliases[persona_id],
                "day_index": day_index,
                "binary_context_class": result["binary_context_class"],
                "final_context_score": float(result["final_context_score"]),
                "no_downtime": int(result["downtime_length"]) == 0,
                "activity_performed": int(performed),
                "duration_min": int(validated["duration_min"]),
                "pa_minutes": float(validated["pa_minutes"]),
                "behavior_policy_pa_prior": float(decision["behavior_policy_pa_prior"]),
                "contextual_pa_probability": float(decision["contextual_pa_probability"]),
                "effective_pa_probability": float(decision["effective_pa_probability"]),
            }
            row["context_shift"] = row["contextual_pa_probability"] - row["behavior_policy_pa_prior"]
            row["feasibility_shift"] = row["effective_pa_probability"] - row["contextual_pa_probability"]
            row["total_probability_shift"] = row["effective_pa_probability"] - row["behavior_policy_pa_prior"]
            rows.append(row)
        seed_daily = pd.DataFrame(rows)
        daily_frames.append(seed_daily)

        for persona_id, group in validation.groupby("persona_id", sort=True):
            meta = empirical.loc[empirical["persona_id"].eq(persona_id)].iloc[0]
            active = group["activity_performed"].astype(bool)
            agreement_frames.append(pd.DataFrame([{
                "seed": int(seed),
                "medoid": aliases[persona_id],
                "t1_mvpa_hours_week": float(meta["empirical_mvpa_hours_week"]),
                "t1_total_pa_hours_week": float(meta["empirical_total_pa_hours_week"]),
                "simulated_pa_hours_week": float(group["pa_minutes"].sum()) / 60 / 90 * 7,
                "pa_days": int(active.sum()),
                "mean_duration_min_pa_day": float(group.loc[active, "duration_min"].mean()),
            }]))

    daily = pd.concat(daily_frames, ignore_index=True)
    agreement = pd.concat(agreement_frames, ignore_index=True)
    if len(daily) != 720 or daily[["seed", "medoid", "day_index"]].duplicated().any():
        raise ValueError("Expected exactly 720 unique seed-medoid-days")
    if daily[list(STAGE_COLUMNS)].isna().any().any():
        raise ValueError("Missing PA probability in source trace")
    if set(daily["binary_context_class"]) != set(CONTEXT_ORDER):
        raise ValueError("Expected both binary context categories")
    if sum(daily["no_downtime"]) != 131:
        raise ValueError("Expected 131 no-downtime days in the two fixed runs")
    if daily.loc[daily["no_downtime"], "binary_context_class"].ne("non_supportive").any():
        raise ValueError("A no-downtime day was not retained as non_supportive")
    return daily, agreement, aliases


def context_pa_summary(daily: pd.DataFrame) -> pd.DataFrame:
    groups: list[tuple[str | int, str, pd.DataFrame]] = [("all", "all", daily)]
    for seed in sorted(daily["seed"].unique()):
        seed_frame = daily[daily["seed"].eq(seed)]
        groups.append((int(seed), "all", seed_frame))
        groups.extend(
            (int(seed), medoid, seed_frame[seed_frame["medoid"].eq(medoid)])
            for medoid in sorted(seed_frame["medoid"].unique())
        )
    rows: list[dict[str, Any]] = []
    for seed, medoid, frame in groups:
        for context in CONTEXT_ORDER:
            subset = frame[frame["binary_context_class"].eq(context)]
            n = len(subset)
            pa_days = int(subset["activity_performed"].sum())
            low, high = wilson(pa_days, n)
            rows.append({
                "seed": seed,
                "medoid": medoid,
                "context": context,
                "person_days": n,
                "pa_days": pa_days,
                "pa_proportion": pa_days / n if n else math.nan,
                "wilson95_low": low,
                "wilson95_high": high,
                "no_downtime_days": int(subset["no_downtime"].sum()),
            })
    return pd.DataFrame(rows)


def gee_context_model(daily: pd.DataFrame) -> pd.DataFrame:
    data = daily.copy()
    data["seed"] = data["seed"].astype(str)
    data["seed_medoid"] = data["seed"] + "_" + data["medoid"]
    formula = 'activity_performed ~ C(binary_context_class, Treatment(reference="non_supportive")) + C(seed)'
    specifications = (
        ("primary_medoid_cluster_bias_reduced", "medoid", "bias_reduced"),
        ("sensitivity_seed_medoid_cluster_robust", "seed_medoid", "robust"),
    )
    rows: list[dict[str, Any]] = []
    for label, group_column, covariance in specifications:
        model = smf.gee(
            formula,
            groups=group_column,
            data=data,
            family=sm.families.Binomial(),
            cov_struct=sm.cov_struct.Exchangeable(),
        )
        fit = model.fit(cov_type=covariance)
        clusters = int(data[group_column].nunique())
        degrees_freedom = clusters - 1
        critical = float(stats.t.ppf(0.975, degrees_freedom))
        for term, interpretation in (
            ('C(binary_context_class, Treatment(reference="non_supportive"))[T.supportive]', "supportive_vs_non_supportive"),
            ("C(seed)[T.96]", "seed96_vs_seed14"),
        ):
            estimate = float(fit.params[term])
            standard_error = float(fit.bse[term])
            statistic = estimate / standard_error
            rows.append({
                "model": label,
                "clusters": clusters,
                "degrees_freedom": degrees_freedom,
                "observations": len(data),
                "contrast": interpretation,
                "log_odds": estimate,
                "standard_error": standard_error,
                "odds_ratio": math.exp(estimate),
                "ci95_low": math.exp(estimate - critical * standard_error),
                "ci95_high": math.exp(estimate + critical * standard_error),
                "exploratory_p_value": float(2 * stats.t.sf(abs(statistic), degrees_freedom)),
                "working_correlation": float(fit.cov_struct.dep_params),
            })
    return pd.DataFrame(rows)


def cluster_bootstrap_ci(
    frame: pd.DataFrame,
    statistic: Callable[[pd.DataFrame], float],
) -> tuple[float, float, int, int]:
    medoids = sorted(frame["medoid"].unique())
    if not medoids:
        return math.nan, math.nan, 0, 0
    values: list[float] = []
    for sample in itertools.product(medoids, repeat=len(medoids)):
        resampled = pd.concat([frame[frame["medoid"].eq(medoid)] for medoid in sample], ignore_index=True)
        value = statistic(resampled)
        if math.isfinite(value):
            values.append(float(value))
    low, high = np.quantile(values, [0.025, 0.975])
    return float(low), float(high), len(medoids), len(values)


def cluster_bootstrap_mean_cis(
    frame: pd.DataFrame,
    metrics: tuple[str, ...],
) -> tuple[dict[str, tuple[float, float]], int, int]:
    """Exhaustive cluster bootstrap for several complete-valued means at once."""
    medoids = sorted(frame["medoid"].unique())
    if not medoids:
        return {metric: (math.nan, math.nan) for metric in metrics}, 0, 0
    sums = {medoid: frame.loc[frame["medoid"].eq(medoid), list(metrics)].sum().to_numpy(float) for medoid in medoids}
    counts = {medoid: int(frame["medoid"].eq(medoid).sum()) for medoid in medoids}
    values: list[np.ndarray] = []
    for sample in itertools.product(medoids, repeat=len(medoids)):
        total = sum((sums[medoid] for medoid in sample), start=np.zeros(len(metrics)))
        count = sum(counts[medoid] for medoid in sample)
        if count:
            values.append(total / count)
    quantiles = np.quantile(np.vstack(values), [0.025, 0.975], axis=0)
    intervals = {
        metric: (float(quantiles[0, index]), float(quantiles[1, index]))
        for index, metric in enumerate(metrics)
    }
    return intervals, len(medoids), len(values)


def probability_summary(daily: pd.DataFrame) -> pd.DataFrame:
    groups: list[tuple[str | int, str, pd.DataFrame]] = [("all", "all", daily)]
    groups.extend(("all", context, daily[daily["binary_context_class"].eq(context)]) for context in CONTEXT_ORDER)
    for seed in sorted(daily["seed"].unique()):
        seed_frame = daily[daily["seed"].eq(seed)]
        groups.append((int(seed), "all", seed_frame))
        groups.extend((int(seed), context, seed_frame[seed_frame["binary_context_class"].eq(context)]) for context in CONTEXT_ORDER)

    metrics = (
        "behavior_policy_pa_prior",
        "contextual_pa_probability",
        "effective_pa_probability",
        "context_shift",
        "feasibility_shift",
        "total_probability_shift",
    )
    rows: list[dict[str, Any]] = []
    for seed, context, frame in groups:
        row: dict[str, Any] = {"seed": seed, "context": context, "person_days": len(frame)}
        intervals, clusters, replicates = cluster_bootstrap_mean_cis(frame, metrics)
        for metric in metrics:
            row[f"mean_{metric}"] = float(frame[metric].mean())
            low, high = intervals[metric]
            row[f"ci95_low_{metric}"] = low
            row[f"ci95_high_{metric}"] = high
        row["medoid_clusters"] = clusters
        row["bootstrap_replicates"] = replicates
        rows.append(row)
    return pd.DataFrame(rows)


def agreement_summary(agreement: pd.DataFrame) -> pd.DataFrame:
    groups: list[tuple[str | int, pd.DataFrame]] = [
        (int(seed), group.copy()) for seed, group in agreement.groupby("seed", sort=True)
    ]
    averaged = agreement.groupby("medoid", as_index=False).agg(
        t1_mvpa_hours_week=("t1_mvpa_hours_week", "first"),
        t1_total_pa_hours_week=("t1_total_pa_hours_week", "first"),
        simulated_pa_hours_week=("simulated_pa_hours_week", "mean"),
    )
    groups.append(("seed_mean", averaged))
    rows: list[dict[str, Any]] = []
    for seed, frame in groups:
        for reference, column in (
            ("T1_MVPA", "t1_mvpa_hours_week"),
            ("T1_total_PA", "t1_total_pa_hours_week"),
        ):
            errors = frame["simulated_pa_hours_week"] - frame[column]
            n = len(errors)
            half = stats.t.ppf(0.975, n - 1) * errors.std(ddof=1) / math.sqrt(n)
            correlation = stats.spearmanr(frame[column], frame["simulated_pa_hours_week"]).statistic
            rows.append({
                "seed": seed,
                "reference": reference,
                "medoids": n,
                "mean_bias_hours_week": float(errors.mean()),
                "bias_ci95_low": float(errors.mean() - half),
                "bias_ci95_high": float(errors.mean() + half),
                "mae_hours_week": float(errors.abs().mean()),
                "rmse_hours_week": float(np.sqrt(np.mean(np.square(errors)))),
                "spearman_rho": float(correlation),
            })
    return pd.DataFrame(rows)


def public_simulation_summary(agreement: pd.DataFrame) -> pd.DataFrame:
    """Aggregate simulated PA without exporting medoid-level or T1 reference values."""
    rows: list[dict[str, Any]] = []
    for seed, frame in agreement.groupby("seed", sort=True):
        pa_days = int(frame["pa_days"].sum())
        weighted_duration = float(
            np.average(frame["mean_duration_min_pa_day"], weights=frame["pa_days"])
        )
        rows.append({
            "seed": int(seed),
            "medoids": int(frame["medoid"].nunique()),
            "mean_simulated_pa_hours_week": float(frame["simulated_pa_hours_week"].mean()),
            "sd_simulated_pa_hours_week": float(frame["simulated_pa_hours_week"].std(ddof=1)),
            "total_pa_days": pa_days,
            "mean_duration_min_pa_day": weighted_duration,
        })
    return pd.DataFrame(rows)


def _save_context_figure(summary: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True)
    colors = {"supportive": "#2a7f62", "non_supportive": "#b05a47"}
    for axis, seed in zip(axes, (14, 96), strict=True):
        seed_rows = summary[summary["seed"].eq(seed)]
        for index, context in enumerate(CONTEXT_ORDER):
            overall = seed_rows[(seed_rows["medoid"].eq("all")) & seed_rows["context"].eq(context)].iloc[0]
            axis.errorbar(
                index,
                overall["pa_proportion"],
                yerr=[[overall["pa_proportion"] - overall["wilson95_low"]], [overall["wilson95_high"] - overall["pa_proportion"]]],
                fmt="o", color=colors[context], capsize=4, markersize=7, label="Seed aggregate" if index == 0 else None,
            )
            persona_rows = seed_rows[(seed_rows["medoid"].ne("all")) & seed_rows["context"].eq(context)]
            offsets = np.linspace(-0.12, 0.12, len(persona_rows))
            axis.scatter(index + offsets, persona_rows["pa_proportion"], color=colors[context], alpha=0.55, s=28)
        axis.set_title(f"Seed {seed}")
        axis.set_xticks((0, 1), ("Unterstützend", "Nicht unterstützend"))
        axis.set_ylim(-0.03, 1.03)
        axis.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("PA-Anteil pro Personentag")
    fig.suptitle("PA nach binärem Tageskontext\nGrosse Punkte: Seed-Aggregat mit 95%-Wilson-KI; kleine Punkte: Medoids")
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _save_probability_figure(summary: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.8), sharey=True)
    stages = list(STAGE_COLUMNS)
    labels = ("Psychologischer Prior", "Kontextuell", "Effektiv")
    colors = {"supportive": "#2a7f62", "non_supportive": "#b05a47"}
    for axis, seed in zip(axes, ("all", 14, 96), strict=True):
        for context in CONTEXT_ORDER:
            row = summary[(summary["seed"].eq(seed)) & summary["context"].eq(context)].iloc[0]
            means = [row[f"mean_{stage}"] for stage in stages]
            lows = [row[f"ci95_low_{stage}"] for stage in stages]
            highs = [row[f"ci95_high_{stage}"] for stage in stages]
            context_label = "unterstützend" if context == "supportive" else "nicht unterstützend"
            axis.errorbar(range(3), means, yerr=[np.array(means) - lows, np.array(highs) - means],
                          marker="o", capsize=3, color=colors[context], label=context_label)
        axis.set_title("Beide Seeds" if seed == "all" else f"Seed {seed}")
        axis.set_xticks(range(3), labels, rotation=20, ha="right")
        axis.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("Mittlere PA-Wahrscheinlichkeit")
    axes[-1].legend(frameon=False)
    fig.suptitle("Wahrscheinlichkeitsverlauf nach Kontext\n95%-Medoid-Cluster-Bootstrap-Intervalle")
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _save_agreement_figure(agreement_stats: pd.DataFrame, path: Path) -> None:
    """Plot aggregate agreement statistics without exposing individual T1 values."""
    combined = agreement_stats[agreement_stats["seed"].eq("seed_mean")].copy()
    combined["reference_label"] = combined["reference"].map({
        "T1_MVPA": "T1-MVPA",
        "T1_total_PA": "T1-Gesamt-PA",
    })
    x = np.arange(len(combined))
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.8))
    bias = combined["mean_bias_hours_week"].to_numpy(float)
    axes[0].errorbar(
        x,
        bias,
        yerr=[
            bias - combined["bias_ci95_low"].to_numpy(float),
            combined["bias_ci95_high"].to_numpy(float) - bias,
        ],
        fmt="o",
        color="#345995",
        capsize=4,
    )
    axes[0].axhline(0, color="black", linewidth=0.8, linestyle="--")
    axes[0].set_xticks(x, combined["reference_label"])
    axes[0].set_ylabel("Mittlerer Bias (h/Woche)")
    axes[0].set_title("Bias mit 95%-t-Intervall")
    width = 0.34
    axes[1].bar(x - width / 2, combined["mae_hours_week"], width, label="MAE", color="#2a7f62")
    axes[1].bar(x + width / 2, combined["rmse_hours_week"], width, label="RMSE", color="#b05a47")
    axes[1].set_xticks(x, combined["reference_label"])
    axes[1].set_ylabel("Fehler (h/Woche)")
    axes[1].set_title("Aggregierte Fehlermaße")
    axes[1].legend(frameon=False)
    for axis in axes:
        axis.grid(axis="y", alpha=0.25)
    fig.suptitle("Aggregierte deskriptive T1-Übereinstimmung (vier Medoids, Mittel über Seeds)")
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    if isinstance(value, (float, np.floating)):
        return f"{value:.{digits}f}"
    return str(value)


def markdown_table(frame: pd.DataFrame, columns: list[str], labels: list[str], digits: int = 3) -> str:
    lines = ["| " + " | ".join(labels) + " |", "|" + "|".join("---" for _ in labels) + "|"]
    for values in frame[columns].itertuples(index=False, name=None):
        lines.append("| " + " | ".join(_fmt(value, digits) for value in values) + " |")
    return "\n".join(lines)


def build_report(
    context: pd.DataFrame,
    gee: pd.DataFrame,
    probabilities: pd.DataFrame,
    public_simulation: pd.DataFrame,
    agreement_stats: pd.DataFrame,
) -> str:
    overall = context[(context["seed"].eq("all")) & context["medoid"].eq("all")]
    context_model = gee[(gee["model"].eq("primary_medoid_cluster_bias_reduced")) & gee["contrast"].eq("supportive_vs_non_supportive")].iloc[0]
    probability_display = probabilities[[
        "seed", "context", "person_days", "mean_behavior_policy_pa_prior",
        "mean_contextual_pa_probability", "mean_effective_pa_probability",
        "mean_context_shift", "mean_feasibility_shift", "mean_total_probability_shift",
    ]]
    lines = [
        "# Finale empirische PA-v1.2-Ergebnisse: Seeds 14 und 96",
        "",
        "## Umfang und Methoden",
        "",
        "Dies ist eine Read-only-Auswertung von zwei vorhandenen 90-Tage-Runs mit vier T1-Medoid-Personas. "
        "Alle 720 Personentage bleiben enthalten, darunter 131 Tage ohne Downtime. Die binäre Kontextklasse "
        "ist eine Auswertungsentscheidung: finaler Kontextscore > 0 ist supportive, Score <= 0 ist "
        "non_supportive. Simulationsmechanismus, Wahrscheinlichkeiten, Entscheidungen, Dauern und "
        "Kontextklassifikator bleiben unverändert.",
        "",
        "Tagesanteile erhalten deskriptive 95%-Wilson-Intervalle. Das primäre Kontextmodell ist ein "
        "logistisches GEE mit austauschbarer Arbeitskorrelation, Medoid-Clustern, Seed-Adjustierung, "
        "bias-reduzierter Sandwich-Kovarianz und einer Small-Cluster-t-Referenz mit df = Cluster - 1. "
        "Ein robustes, nach Seed-Medoid geclustertes GEE dient als Sensitivitätsanalyse. Intervalle der "
        "Wahrscheinlichkeitsstufen beruhen auf einem exhaustiven Medoid-Cluster-Bootstrap. Dabei werden nur "
        "die Medoid-Cluster resampelt, die zum jeweiligen Teilvergleich tatsächlich beitragen: Seed 14 / "
        "non_supportive umfasst drei Cluster und 3^3 = 27 mögliche Resamples; Vergleiche mit vier beitragenden "
        "Medoids umfassen 4^4 = 256 Resamples. Die resultierenden Perzentilintervalle sind wegen dieser sehr "
        "kleinen Clusterzahl explorativ und beanspruchen keine zuverlässig kalibrierte nominale 95%-Abdeckung. "
        "T1-Biasintervalle "
        "sind t-Intervalle über vier gepaarte Medoid-Differenzen. Bei nur vier Medoids ist jede Inferenz explorativ.",
        "",
        "## PA-Häufigkeit nach binärem Kontext",
        "",
        markdown_table(overall, ["context", "person_days", "pa_days", "pa_proportion", "wilson95_low", "wilson95_high", "no_downtime_days"],
                       ["Kontext", "Tage", "PA-Tage", "PA-Anteil", "Wilson unten", "Wilson oben", "Ohne Downtime"]),
        "",
        f"Das seed-adjustierte primäre GEE schätzt für supportive gegenüber non_supportive Tagen eine Odds Ratio "
        f"von {context_model['odds_ratio']:.2f} (95%-KI {context_model['ci95_low']:.2f}–"
        f"{context_model['ci95_high']:.2f}, exploratives p={context_model['exploratory_p_value']:.3f}). "
        "Die sehr kleine Zahl unabhängiger Medoid-Cluster begrenzt die Verlässlichkeit dieses Intervalls.",
        "",
        "Vollständige Kontextzahlen pro Seed und Medoid stehen in `tables/01_context_pa.csv`, die "
        "Modellschätzungen in `tables/02_context_gee.csv`.",
        "",
        "![PA frequency by context](figures/01_context_pa.png)",
        "",
        "## Verlauf der PA-Wahrscheinlichkeit",
        "",
        markdown_table(probability_display, list(probability_display.columns),
                       ["Seed", "Kontext", "Tage", "Prior", "Kontextuell", "Effektiv", "Kontext-Prior", "Effektiv-kontextuell", "Effektiv-Prior"]),
        "",
        "Die kontextuelle Stufe trennt supportive von non_supportive Tagen. Die effektive Stufe berücksichtigt "
        "zusätzlich die strukturelle Durchführbarkeit; ihre Reduktion konzentriert sich auf non_supportive Tage, "
        "einschliesslich der erhaltenen Beobachtungen ohne Downtime. Cluster-Bootstrap-Intervalle für jeden "
        "Mittelwert und jede Veränderung stehen in `tables/03_probability_pathway.csv`. Die Spalten "
        "`medoid_clusters` und `bootstrap_replicates` dokumentieren die beitragenden Cluster und den jeweiligen "
        "exhaustiven Resampling-Raum.",
        "",
        "![Probability pathway](figures/02_probability_pathway.png)",
        "",
        "## Übereinstimmung mit empirischer T1-PA",
        "",
        "Ausgeführte Simulationsminuten werden mit der vorhandenen v1.2-Validierungsfunktion auf Stunden pro "
        "Woche normiert. Der deskriptive Vergleich erfolgt sowohl mit T1-MVPA als auch T1-Gesamt-PA, weil der "
        "Simulationsoutput keine zusätzliche Intensitätsklassifikation enthält.",
        "",
        "Individuelle T1-Referenzwerte und medoidspezifische Differenzen werden ausschließlich intern berechnet "
        "und nicht exportiert. Die folgende Simulationstabelle ist über alle vier Medoids je Seed aggregiert.",
        "",
        markdown_table(public_simulation, list(public_simulation.columns),
                       ["Seed", "Medoids", "Mittlere simulierte h/W", "SD simulierte h/W", "PA-Tage", "Mittlere Dauer min"]),
        "",
        markdown_table(agreement_stats, list(agreement_stats.columns),
                       ["Seed", "Referenz", "M", "Mittlerer Bias", "Bias-KI unten", "Bias-KI oben", "MAE", "RMSE", "Spearman rho"]),
        "",
        "Die T1-Abbildung zeigt ausschließlich die über vier Medoids und beide Seeds aggregierten Kennzahlen. "
        "Spearman rho bleibt in der Ergebnistabelle dokumentiert.",
        "",
        "![Aggregated T1 agreement](figures/03_t1_agreement.png)",
        "",
        "## Grenzen der Interpretation",
        "",
        "Die vier Medoids sind ausgewählte Fälle und keine zufällige Bevölkerungsstichprobe. Seed 96 ist als "
        "Kontext-Stresslauf bezeichnet; die Seeds sind daher keine unabhängigen Replikationen. Wilson-Intervalle "
        "modellieren keine zeitliche Abhängigkeit und sind rein deskriptiv. Alle 131 Tage ohne Downtime liegen "
        "strukturell in non_supportive und weisen keine ausgeführte PA auf; der Kontextkontrast trennt deshalb "
        "psychologisch-umweltbezogenen Kontext nicht von fehlender zeitlicher Durchführbarkeit. Wiederholte Beobachtungen werden im "
        "GEE und Cluster-Bootstrap berücksichtigt. Vier Cluster liegen unter dem Bereich, in dem Sandwich-Inferenz "
        "üblicherweise verlässlich ist. T1-Werte sind querschnittliche Selbstberichte, während sich simuliertes "
        "Verhalten über 90 Tage entwickelt. Übereinstimmung mit MVPA ist keine Messäquivalenz, da die simulierte "
        "Dauer keine Intensitätskennzeichnung besitzt. Korrelationen mit n=4 sind deskriptiv und dürfen nicht über "
        "Signifikanztests interpretiert werden.",
        "",
        "Es werden keine Personenkennungen, individuellen T1-Referenzwerte, medoidspezifischen T1-Differenzen, "
        "Tagesdatensätze, Tagebuchtexte oder psychologischen Rohverläufe exportiert.",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed14-dir", type=Path, required=True)
    parser.add_argument("--seed96-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite {args.output_dir}")
    roots = {14: args.seed14_dir, 96: args.seed96_dir}
    before = {str(seed): source_hashes(root) for seed, root in roots.items()}
    daily, agreement, aliases = load_analysis_data(roots)
    context = context_pa_summary(daily)
    gee = gee_context_model(daily)
    probabilities = probability_summary(daily)
    agreement_stats = agreement_summary(agreement)
    public_simulation = public_simulation_summary(agreement)
    after = {str(seed): source_hashes(root) for seed, root in roots.items()}
    if before != after:
        raise RuntimeError("A source file changed during analysis")

    tables = args.output_dir / "tables"
    figures = args.output_dir / "figures"
    tables.mkdir(parents=True)
    figures.mkdir()
    context.to_csv(tables / "01_context_pa.csv", index=False)
    gee.to_csv(tables / "02_context_gee.csv", index=False)
    probabilities.to_csv(tables / "03_probability_pathway.csv", index=False)
    public_simulation.to_csv(tables / "04_t1_agreement_by_seed_medoid.csv", index=False)
    agreement_stats.to_csv(tables / "05_t1_agreement_summary.csv", index=False)
    _save_context_figure(context, figures / "01_context_pa.png")
    _save_probability_figure(probabilities, figures / "02_probability_pathway.png")
    _save_agreement_figure(agreement_stats, figures / "03_t1_agreement.png")
    (args.output_dir / "report.md").write_text(
        build_report(context, gee, probabilities, public_simulation, agreement_stats), encoding="utf-8"
    )
    analysis_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    provenance = {
        "analysis": "final_empirical_pa_v1_2",
        "observations": len(daily),
        "seeds": [14, 96],
        "medoid_aliases": sorted(aliases.values()),
        "no_downtime_days": int(daily["no_downtime"].sum()),
        "llm_calls": 0,
        "simulation_runs": 0,
        "sources_unchanged": True,
        "source_sha256": before,
        "software": software_provenance(),
        "code_reference": {
            **git_provenance(),
            "analysis_sha256": analysis_hash,
        },
        "analysis_sha256": analysis_hash,
        "binary_classifier_sha256": hashlib.sha256(Path(__file__).with_name("empirical_context_binary_v1_2.py").read_bytes()).hexdigest(),
        "validation_routine_sha256": hashlib.sha256(Path(__file__).with_name("t1_medoid_pa_validation_v1_2.py").read_bytes()).hexdigest(),
        "exported_person_identifiers": False,
        "exported_individual_t1_values": False,
    }
    (args.output_dir / "provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote final aggregate analysis for {len(daily)} person-days to {args.output_dir}")


if __name__ == "__main__":
    main()
