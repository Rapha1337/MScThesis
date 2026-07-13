#!/usr/bin/env python
"""Final descriptive and inferential H1-H4 analysis for the MSc thesis ABM simulation.

This script intentionally performs the final calculations in the repository,
rather than relying on any ad-hoc calculations made in a chat session.

It expects:
- final H1 output folder with tables/h1_summary_metrics.csv
- final H2 output folder with tables/schedule_similarity_overall_summary.csv etc.
- complete Supportive annual scenario folder or zip
- complete Hindering annual scenario folder or zip

Example PowerShell call from the repository root:

python Analysis/final_h1_h4_analysis.py `
  --h1-dir Analysis/outputs/h1_weather_final `
  --h2-dir Analysis/outputs/h2_agent_heterogeneity_final `
  --supportive Simulation/output/365x1_SupportiveScenario`
  --hindering Simulation/output/365x1_HinderingScenario`
  --output-dir Analysis/outputs/final_h1_h4 `
  --overwrite

The analysis reports descriptive statistics, confidence intervals, effect sizes,
and inferential tests requested for the thesis results.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import zipfile
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint


DECISION_CATEGORIES = [
    "do_planned_activity",
    "adapt_activity",
    "skip_activity",
    "extra_activity",
]

CONTEXT_ORDER = ["supportive", "mixed_neutral", "hindering"]
CONTEXT_DISPLAY = {
    "supportive": "supportive",
    "mixed_neutral": "neutral",
    "hindering": "hindering",
}
ALPHA = 0.05

H1_REQUIRED_TABLES = [
    "h1_summary_metrics.csv",
]

H2_REQUIRED_TABLES = [
    "schedule_similarity_overall_summary.csv",
    "phase_week_count_summary.csv",
    "construct_heterogeneity_summary.csv",
]


@dataclass
class ScenarioData:
    name: str
    root: Path
    daily: pd.DataFrame
    longitudinal: pd.DataFrame
    trace: dict[str, Any]
    run_config: dict[str, Any]
    manifest: dict[str, Any]
    persona_metadata: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the final descriptive H1-H4 analysis for the ABM thesis."
    )
    parser.add_argument(
        "--h1-dir",
        type=Path,
        required=True,
        help="Final H1 output directory, containing a tables/ subfolder.",
    )
    parser.add_argument(
        "--h2-dir",
        type=Path,
        required=True,
        help="Final H2 output directory, containing a tables/ subfolder.",
    )
    parser.add_argument(
        "--supportive",
        type=Path,
        required=True,
        help="Complete supportive annual scenario folder or zip.",
    )
    parser.add_argument(
        "--hindering",
        type=Path,
        required=True,
        help="Complete hindering annual scenario folder or zip.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("Analysis") / "outputs" / "final_h1_h4",
        help="Directory for final tables, figures, manifest, and summaries.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Delete the output directory if it already exists.",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def parse_bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


def prepare_output_dir(output_dir: Path, overwrite: bool) -> tuple[Path, Path, Path, Path]:
    if output_dir.exists() and overwrite:
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    docs_dir = output_dir / "docs"
    work_dir = output_dir / "_extracted_inputs"

    for folder in [tables_dir, figures_dir, docs_dir, work_dir]:
        folder.mkdir(parents=True, exist_ok=True)

    return tables_dir, figures_dir, docs_dir, work_dir


def find_folder_with_file(root: Path, filename: str) -> Path:
    candidates = [path.parent for path in root.rglob(filename)]
    if not candidates:
        raise FileNotFoundError(f"Could not find {filename!r} below {root}")
    # Prefer the shallowest match, which is usually the scenario root.
    return sorted(candidates, key=lambda p: len(p.parts))[0]


def resolve_dir_or_zip(path: Path, work_dir: Path, required_file: str) -> Path:
    """Return a directory containing required_file.

    If path is a zip archive, it is extracted into work_dir first.
    """
    if path.is_dir():
        if (path / required_file).exists():
            return path
        return find_folder_with_file(path, required_file)

    if path.suffix.lower() == ".zip":
        extract_dir = work_dir / path.stem
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path) as archive:
            archive.extractall(extract_dir)
        return find_folder_with_file(extract_dir, required_file)

    raise FileNotFoundError(f"Input path is neither a directory nor a zip file: {path}")


def load_scenario(name: str, input_path: Path, work_dir: Path) -> ScenarioData:
    root = resolve_dir_or_zip(input_path, work_dir / name.lower(), "daily_decision_log.csv")

    required_files = [
        "daily_decision_log.csv",
        "longitudinal_constructs.csv",
        "full_simulation_trace.json",
        "run_config.json",
        "simulation_run_manifest.json",
        "persona_metadata.json",
    ]
    missing = [filename for filename in required_files if not (root / filename).exists()]
    if missing:
        raise FileNotFoundError(f"{name} scenario is missing required files: {missing}")

    daily = pd.read_csv(root / "daily_decision_log.csv")
    daily["calendar_date"] = pd.to_datetime(daily["calendar_date"])
    daily["planned"] = parse_bool_series(daily["was_physical_activity_planned_today"])
    if "activity_performed" in daily.columns:
        daily["activity_performed_bool"] = parse_bool_series(daily["activity_performed"])
    else:
        daily["activity_performed_bool"] = daily["decision_label"].isin(
            ["do_planned_activity", "adapt_activity", "extra_activity"]
        )

    return ScenarioData(
        name=name,
        root=root,
        daily=daily,
        longitudinal=pd.read_csv(root / "longitudinal_constructs.csv"),
        trace=read_json(root / "full_simulation_trace.json"),
        run_config=read_json(root / "run_config.json"),
        manifest=read_json(root / "simulation_run_manifest.json"),
        persona_metadata=read_json(root / "persona_metadata.json"),
    )


def validate_scenario(scenario: ScenarioData) -> dict[str, Any]:
    daily = scenario.daily
    day_indices = set(int(value) for value in daily["day_index"])
    expected = set(range(365))
    missing = sorted(expected - day_indices)
    extra = sorted(day_indices - expected)
    duplicates = int(daily.duplicated(["persona_id", "day_index"]).sum())
    trace_records = len(scenario.trace.get("records", []))

    return {
        "scenario": scenario.name,
        "root": str(scenario.root),
        "daily_rows": int(len(daily)),
        "trace_records": int(trace_records),
        "missing_day_indices": json.dumps(missing),
        "extra_day_indices": json.dumps(extra),
        "duplicate_persona_days": duplicates,
        "run_status": scenario.manifest.get("run_status"),
        "complete_365_day_run": (
            len(daily) == 365
            and trace_records == 365
            and not missing
            and not extra
            and duplicates == 0
            and scenario.manifest.get("run_status") == "success"
        ),
    }


def activity_hours_from_trace(trace: Mapping[str, Any]) -> tuple[float, int]:
    total_min = 0.0
    days_with_planned = 0
    for record in trace.get("records", []):
        planned = record.get("planned_physical_activity")
        if planned:
            days_with_planned += 1
            total_min += float(planned.get("duration_min") or 0)
    return total_min / 60.0, days_with_planned


def hourly_weather_score(hour: Mapping[str, Any]) -> int:
    feels = hour.get("feels_like_c")
    components = [1 if feels is not None and 15 <= float(feels) <= 27 else -1]

    wet = bool(hour.get("is_wet")) or float(hour.get("precipitation_mm") or 0) > 0
    components.append(-1 if wet else 1)
    components.append(-1 if bool(hour.get("snow_cover")) else 1)

    wind = float(hour.get("wind_m_s") or 0)
    components.append(1 if wind < 5 else (0 if wind < 7 else -1))

    if any(value == -1 for value in components):
        return -1
    if all(value == 1 for value in components):
        return 1
    return 0


def accessibility_score(hour: Mapping[str, Any], target: str | None = None) -> float:
    accessibility = hour.get("poi_accessibility") or {}
    if target and target in accessibility:
        targets = [target]
    else:
        targets = [
            key for key in ("indoor_activity", "outdoor_activity")
            if key in accessibility
        ]

    scores: list[float] = []
    for key in targets:
        times = (accessibility.get(key) or {}).get("travel_times_min") or {}
        values = [
            float(times[mode])
            for mode in ("walk", "bike", "car")
            if mode in times and times[mode] is not None
        ]
        if len(values) < 3:
            scores.append(np.nan)
        elif sum(value <= 15 for value in values) >= 2:
            scores.append(1)
        elif sum(value >= 30 for value in values) >= 2:
            scores.append(-1)
        else:
            scores.append(0)

    valid = [value for value in scores if not pd.isna(value)]
    return max(valid) if valid else np.nan


def longest_downtime(hours: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    runs: list[list[Mapping[str, Any]]] = []
    current: list[Mapping[str, Any]] = []

    for hour in hours:
        if hour.get("activity_type") == "downtime":
            if current and hour["hour"] == current[-1]["hour"] + 1:
                current.append(hour)
            else:
                if current:
                    runs.append(current)
                current = [hour]
        else:
            if current:
                runs.append(current)
                current = []

    if current:
        runs.append(current)

    return max(runs, key=lambda run: (len(run), -int(run[0]["hour"]))) if runs else []


def daily_illness(hours: Iterable[Mapping[str, Any]]) -> str | None:
    rank = {"low": 1, "medium": 2, "high": 3}
    levels: list[str] = []

    for hour in hours:
        for constraint in hour.get("active_constraints") or []:
            if (
                isinstance(constraint, dict)
                and constraint.get("type") == "AcuteIllnessConstraint"
            ):
                levels.append(str(constraint.get("intensity")))

    return max(levels, key=lambda level: rank.get(level, 0)) if levels else None


def classify_from_score(score: float) -> str:
    if pd.isna(score):
        return "not_classifiable"
    if score >= 2:
        return "supportive"
    if score <= -2:
        return "hindering"
    return "mixed_neutral"


def classify_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Classify one day using the final H3/H4 context rules.

    Edge-case rules:
    - no downtime window on unplanned days => hindering
    - unknown pre-PA accessibility => last previous hour with known accessibility
    """
    hours = sorted(record["hourly_context_24h"], key=lambda item: int(item["hour"]))
    by_hour = {int(hour["hour"]): hour for hour in hours}

    planned = bool(record["was_physical_activity_planned_today"])
    weather = np.nan
    energy = np.nan
    access = np.nan
    downtime_length = np.nan
    edge_case_rule: str | None = None

    if planned:
        weather_blocks: list[float] = []
        energy_blocks: list[float] = []
        access_blocks: list[float] = []

        for block in (record.get("planned_physical_activity") or {}).get("blocks") or []:
            scheduled = [int(value) for value in (block.get("scheduled_hours") or [])]
            if not scheduled:
                continue

            previous_hour = min(scheduled) - 1
            block_hours = ([previous_hour] if previous_hour in by_hour else []) + scheduled

            if block_hours:
                weather_blocks.append(
                    min(hourly_weather_score(by_hour[index]) for index in block_hours if index in by_hour)
                )

            if previous_hour in by_hour:
                energy_blocks.append(
                    {"low": -1, "medium": 0, "high": 1}.get(
                        by_hour[previous_hour].get("energy_category"),
                        np.nan,
                    )
                )
                access_blocks.append(
                    accessibility_score(
                        by_hour[previous_hour],
                        block.get("planned_target_location"),
                    )
                )

        if weather_blocks:
            weather = min(weather_blocks)
        valid_energy = [value for value in energy_blocks if not pd.isna(value)]
        valid_access = [value for value in access_blocks if not pd.isna(value)]
        if valid_energy:
            energy = min(valid_energy)
        if valid_access:
            access = min(valid_access)

        if pd.isna(access):
            recovered_scores: list[float] = []
            for block in (record.get("planned_physical_activity") or {}).get("blocks") or []:
                scheduled = [int(value) for value in (block.get("scheduled_hours") or [])]
                if not scheduled:
                    continue

                previous_hour = min(scheduled) - 1
                target = block.get("planned_target_location")

                for index in range(previous_hour, -1, -1):
                    if index in by_hour:
                        candidate = accessibility_score(by_hour[index], target)
                        if not pd.isna(candidate):
                            recovered_scores.append(candidate)
                            break

            if recovered_scores:
                access = min(recovered_scores)
                edge_case_rule = "last_known_pre_pa_accessibility"

    else:
        downtime = longest_downtime(hours)
        downtime_length = len(downtime)

        if downtime:
            weather = min(hourly_weather_score(hour) for hour in downtime)
            energy_values = [
                {"low": -1, "medium": 0, "high": 1}.get(
                    hour.get("energy_category"),
                    np.nan,
                )
                for hour in downtime
            ]
            energy_values = [value for value in energy_values if not pd.isna(value)]
            if energy_values:
                energy = int(round(float(np.median(energy_values))))
            access = accessibility_score(downtime[0])
        else:
            edge_case_rule = "no_downtime_classified_hindering"

    obligation_hours = sum(
        1
        for hour in hours
        if hour.get("activity_type") in ("work", "carework")
        or hour.get("subtype") in ("paid_work", "university", "studying", "carework")
    )
    time_score = 1 if obligation_hours <= 4 else (0 if obligation_hours <= 7 else -1)

    components = [weather, energy, access, time_score]
    base_score = np.nan if any(pd.isna(value) for value in components) else sum(components)

    illness = daily_illness(hours)
    final_score = base_score
    if edge_case_rule == "no_downtime_classified_hindering":
        final_score = -2
    elif illness == "low" and not pd.isna(final_score):
        final_score = min(final_score, 0)
    elif illness in ("medium", "high"):
        final_score = -2

    return {
        "day_index": int(record["day_index"]),
        "calendar_date": record["calendar_date"],
        "phase": record.get("phase"),
        "planned": planned,
        "decision_label": record["pa_decision"]["decision_label"],
        "weather_score": weather,
        "energy_score": energy,
        "accessibility_score": access,
        "time_score": time_score,
        "obligation_hours": obligation_hours,
        "base_score": base_score,
        "illness": illness,
        "final_context_score": final_score,
        "context_class": classify_from_score(final_score),
        "downtime_length": downtime_length,
        "edge_case_rule": edge_case_rule,
    }


def classify_scenario(scenario: ScenarioData) -> pd.DataFrame:
    rows = [classify_record(record) for record in scenario.trace["records"]]
    context = pd.DataFrame(rows)
    context["scenario"] = scenario.name
    return context


def scenario_daily_with_context(scenario: ScenarioData, context: pd.DataFrame) -> pd.DataFrame:
    daily = scenario.daily.copy()
    daily["scenario"] = scenario.name
    return daily.merge(
        context[
            [
                "scenario",
                "day_index",
                "phase",
                "context_class",
                "final_context_score",
                "edge_case_rule",
                "obligation_hours",
            ]
        ],
        on=["scenario", "day_index"],
        how="left",
    )


def tabulate_decisions(frame: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for group_values, group in frame.groupby(group_cols, dropna=False):
        if not isinstance(group_values, tuple):
            group_values = (group_values,)

        row = {column: value for column, value in zip(group_cols, group_values)}
        row["n_days"] = len(group)

        for category in DECISION_CATEGORIES:
            n = int((group["decision_label"] == category).sum())
            row[f"{category}_n"] = n
            row[f"{category}_pct"] = 100 * n / len(group) if len(group) else np.nan

        row["activity_performed_n"] = int(group["activity_performed_bool"].sum())
        row["activity_performed_pct"] = (
            100 * row["activity_performed_n"] / len(group)
            if len(group)
            else np.nan
        )

        rows.append(row)

    return pd.DataFrame(rows)


def decision_policy_diagnostics(scenario: ScenarioData) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    records_by_day = {int(record["day_index"]): record for record in scenario.trace["records"]}

    for _, row in scenario.daily.iterrows():
        policy = json.loads(row["behavior_policy"])
        valid = json.loads(row["valid_decision_categories"])
        ranked = sorted(
            [
                (category, float(policy.get(category, np.nan)))
                for category in valid
            ],
            key=lambda item: item[1],
            reverse=True,
        )

        rows.append(
            {
                "scenario": scenario.name,
                "day_index": int(row["day_index"]),
                "calendar_date": row["calendar_date"].date().isoformat(),
                "phase": records_by_day[int(row["day_index"])].get("phase"),
                "planned": bool(row["planned"]),
                "decision_label": row["decision_label"],
                "llm1_top_valid": ranked[0][0] if ranked else None,
                "llm1_top_probability": ranked[0][1] if ranked else np.nan,
                "llm1_second_probability": ranked[1][1] if len(ranked) > 1 else np.nan,
                "llm1_margin": ranked[0][1] - ranked[1][1] if len(ranked) > 1 else np.nan,
                "llm2_override": row["decision_label"] != ranked[0][0] if ranked else False,
            }
        )

    return pd.DataFrame(rows)


def rate_difference(
    df: pd.DataFrame,
    scenario_a: str,
    scenario_b: str,
    day_filter: Callable[[pd.DataFrame], pd.Series],
    outcome: str,
    day_label: str,
) -> dict[str, Any]:
    a = df[(df["scenario"] == scenario_a) & day_filter(df)]
    b = df[(df["scenario"] == scenario_b) & day_filter(df)]

    pa = (a["decision_label"] == outcome).mean() if len(a) else np.nan
    pb = (b["decision_label"] == outcome).mean() if len(b) else np.nan

    return {
        "comparison": f"{scenario_b} minus {scenario_a}",
        "day_set": day_label,
        "outcome": outcome,
        "n_a": int(len(a)),
        "rate_a_pct": 100 * pa,
        "n_b": int(len(b)),
        "rate_b_pct": 100 * pb,
        "risk_difference_percentage_points": 100 * (pb - pa),
        "risk_ratio": (pb / pa) if pa > 0 else np.inf,
    }


def construct_summary(scenario: ScenarioData) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for construct, group in scenario.longitudinal.groupby("construct"):
        group = group.sort_values("day_index")
        rows.append(
            {
                "scenario": scenario.name,
                "construct": construct,
                "start": float(group.iloc[0]["value_before"]),
                "end": float(group.iloc[-1]["value_after"]),
                "change": float(group.iloc[-1]["value_after"] - group.iloc[0]["value_before"]),
                "min": float(group["value_after"].min()),
                "max": float(group["value_after"].max()),
                "changed_days": int((group["delta"].abs() > 1e-12).sum()),
            }
        )

    return pd.DataFrame(rows)


def load_optional_table(base_dir: Path, relative_path: str) -> pd.DataFrame | None:
    path = base_dir / relative_path
    if path.exists():
        return pd.read_csv(path)
    return None


def table_to_markdown(df: pd.DataFrame, float_fmt: str = "{:.2f}") -> str:
    def fmt(value: Any) -> str:
        if isinstance(value, (float, np.floating)):
            if np.isinf(value):
                return "inf"
            if pd.isna(value):
                return ""
            return float_fmt.format(float(value))
        return str(value)

    return df.map(fmt).to_markdown(index=False)



def p_value_to_stars(p_value: float | None) -> str:
    if p_value is None or pd.isna(p_value):
        return ""
    if p_value < 0.001:
        return "***"
    if p_value < 0.01:
        return "**"
    if p_value < 0.05:
        return "*"
    return "ns"


def format_p_value(p_value: Any) -> str:
    if p_value is None or pd.isna(p_value):
        return ""
    value = float(p_value)
    return "< .001" if value < 0.001 else f"= {value:.3f}"


def prepare_inferential_table_for_markdown(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    result = df.copy()
    for column in [
        "p_value",
        "p_raw",
        "p_adjusted",
        "pearson_p",
        "spearman_p",
        "selected_p",
    ]:
        if column in result.columns:
            result[column] = result[column].map(format_p_value)
    return result


def add_proportion_confidence_intervals(
    table: pd.DataFrame,
    alpha: float = ALPHA,
) -> pd.DataFrame:
    """Add Wilson 95% confidence intervals for every decision proportion."""
    result = table.copy()
    for category in DECISION_CATEGORIES:
        lower_values: list[float] = []
        upper_values: list[float] = []
        for _, row in result.iterrows():
            count = int(row[f"{category}_n"])
            n_days = int(row["n_days"])
            if n_days <= 0:
                lower_values.append(np.nan)
                upper_values.append(np.nan)
                continue
            lower, upper = proportion_confint(
                count=count,
                nobs=n_days,
                alpha=alpha,
                method="wilson",
            )
            lower_values.append(float(np.clip(100 * float(lower), 0, 100)))
            upper_values.append(float(np.clip(100 * float(upper), 0, 100)))
        result[f"{category}_ci_lower_pct"] = lower_values
        result[f"{category}_ci_upper_pct"] = upper_values
    return result


def fisher_correlation_ci(
    coefficient: float,
    n: int,
    alpha: float = ALPHA,
) -> tuple[float, float]:
    if n <= 3 or pd.isna(coefficient):
        return np.nan, np.nan
    clipped = float(np.clip(coefficient, -0.999999999, 0.999999999))
    z_value = np.arctanh(clipped)
    standard_error = 1 / math.sqrt(n - 3)
    z_critical = stats.norm.ppf(1 - alpha / 2)
    return (
        float(np.tanh(z_value - z_critical * standard_error)),
        float(np.tanh(z_value + z_critical * standard_error)),
    )


def bootstrap_spearman_ci(
    x: np.ndarray,
    y: np.ndarray,
    seed: int,
    repetitions: int = 5000,
    alpha: float = ALPHA,
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(x)
    coefficients: list[float] = []
    for _ in range(repetitions):
        indices = rng.integers(0, n, size=n)
        sampled_x = x[indices]
        sampled_y = y[indices]
        if np.unique(sampled_x).size < 2 or np.unique(sampled_y).size < 2:
            continue
        coefficient = stats.spearmanr(sampled_x, sampled_y).statistic
        if not pd.isna(coefficient):
            coefficients.append(float(coefficient))
    if not coefficients:
        return np.nan, np.nan
    return (
        float(np.quantile(coefficients, alpha / 2)),
        float(np.quantile(coefficients, 1 - alpha / 2)),
    )


def calculate_h1_correlation_inference(
    monthly_climate_comparison: pd.DataFrame | None,
) -> pd.DataFrame:
    """Calculate normality checks, Pearson/Spearman tests, p values, and CIs."""
    if monthly_climate_comparison is None:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for variable, group in monthly_climate_comparison.groupby("variable"):
        paired = group[["reference_value", "simulated_mean"]].dropna()
        x = paired["reference_value"].astype(float).to_numpy()
        y = paired["simulated_mean"].astype(float).to_numpy()
        n = len(paired)
        if n < 3:
            continue

        reference_constant = np.unique(x).size < 2
        simulated_constant = np.unique(y).size < 2
        shapiro_reference_p = (
            np.nan if reference_constant else float(stats.shapiro(x).pvalue)
        )
        shapiro_simulated_p = (
            np.nan if simulated_constant else float(stats.shapiro(y).pvalue)
        )

        if reference_constant or simulated_constant:
            pearson_r = np.nan
            pearson_p = np.nan
            pearson_ci_lower = np.nan
            pearson_ci_upper = np.nan
            spearman_rho = np.nan
            spearman_p = np.nan
            spearman_ci_lower = np.nan
            spearman_ci_upper = np.nan
        else:
            pearson_result = stats.pearsonr(x, y)
            pearson_r = float(pearson_result.statistic)
            pearson_p = float(pearson_result.pvalue)
            pearson_ci_lower, pearson_ci_upper = fisher_correlation_ci(pearson_r, n)

            spearman_result = stats.spearmanr(x, y)
            spearman_rho = float(spearman_result.statistic)
            spearman_p = float(spearman_result.pvalue)
            spearman_ci_lower, spearman_ci_upper = bootstrap_spearman_ci(
                x,
                y,
                seed=3263 + len(rows),
            )

        pearson_assumptions_met = (
            not reference_constant
            and not simulated_constant
            and shapiro_reference_p >= ALPHA
            and shapiro_simulated_p >= ALPHA
        )
        if reference_constant or simulated_constant:
            selected_test = "Not estimable (constant input)"
            selected_coefficient = np.nan
            selected_p = np.nan
            selected_ci_lower = np.nan
            selected_ci_upper = np.nan
        else:
            selected_test = "Pearson" if pearson_assumptions_met else "Spearman"
            selected_coefficient = pearson_r if pearson_assumptions_met else spearman_rho
            selected_p = pearson_p if pearson_assumptions_met else spearman_p
            selected_ci_lower = (
                pearson_ci_lower if pearson_assumptions_met else spearman_ci_lower
            )
            selected_ci_upper = (
                pearson_ci_upper if pearson_assumptions_met else spearman_ci_upper
            )

        rows.append(
            {
                "variable": variable,
                "n_months": n,
                "shapiro_reference_p": shapiro_reference_p,
                "shapiro_simulated_p": shapiro_simulated_p,
                "pearson_assumptions_met": pearson_assumptions_met,
                "pearson_r": pearson_r,
                "pearson_p": pearson_p,
                "pearson_ci_lower": pearson_ci_lower,
                "pearson_ci_upper": pearson_ci_upper,
                "spearman_rho": spearman_rho,
                "spearman_p": spearman_p,
                "spearman_ci_lower": spearman_ci_lower,
                "spearman_ci_upper": spearman_ci_upper,
                "selected_test": selected_test,
                "selected_coefficient": selected_coefficient,
                "selected_p": selected_p,
                "selected_ci_lower": selected_ci_lower,
                "selected_ci_upper": selected_ci_upper,
                "significance": p_value_to_stars(selected_p),
            }
        )

    return pd.DataFrame(rows)


def calculate_h2_construct_sd_intervals(
    initial_constructs: pd.DataFrame | None,
    h2_construct_summary: pd.DataFrame | None,
    repetitions: int = 5000,
    alpha: float = ALPHA,
) -> pd.DataFrame:
    """Bootstrap 95% CIs for the population SD of each initial construct."""
    if initial_constructs is None or h2_construct_summary is None:
        return pd.DataFrame()

    rng = np.random.default_rng(3263)
    rows: list[dict[str, Any]] = []
    for _, summary_row in h2_construct_summary.iterrows():
        construct = str(summary_row["construct"])
        if construct not in initial_constructs.columns:
            continue
        values = initial_constructs[construct].dropna().astype(float).to_numpy()
        n = len(values)
        if n < 2:
            continue
        sample_indices = rng.integers(0, n, size=(repetitions, n))
        bootstrap_values = values[sample_indices]
        bootstrap_sd = np.std(bootstrap_values, axis=1, ddof=0)
        rows.append(
            {
                "construct": construct,
                "n": n,
                "population_sd": float(np.std(values, ddof=0)),
                "sd_ci_lower": float(np.quantile(bootstrap_sd, alpha / 2)),
                "sd_ci_upper": float(np.quantile(bootstrap_sd, 1 - alpha / 2)),
                "bootstrap_repetitions": repetitions,
            }
        )
    return pd.DataFrame(rows)


def calculate_h2_construct_mixed_effects(
    initial_constructs: pd.DataFrame | None,
) -> pd.DataFrame:
    """Estimate between-agent heterogeneity with a random-intercept model.

    Model:
        construct_value ~ C(construct) + (1 | agent)

    The fixed construct effect accounts for systematic differences in mean
    levels between the nine constructs. The random intercept estimates the
    remaining between-agent variance in the agents' average psychological
    construct levels.

    The random-intercept model is fitted with maximum likelihood and compared
    with a fixed-effects-only OLS model. Because the null hypothesis places the
    variance component on the boundary at zero, the primary p value uses the
    conventional 50:50 mixture correction: 0.5 * P(chi-square_1 >= LRT).
    """
    if initial_constructs is None or initial_constructs.empty:
        return pd.DataFrame()

    constructs = [
        "automaticity",
        "pa_specific_self_control",
        "action_planning",
        "intention",
        "perceived_behavioral_control",
        "attitude_toward_the_behavior",
        "subjective_norm",
        "intrinsic_motivation",
        "motivational_competence",
    ]
    missing_constructs = [
        construct for construct in constructs
        if construct not in initial_constructs.columns
    ]
    if missing_constructs:
        return pd.DataFrame(
            [
                {
                    "analysis": "H2_between_agent_heterogeneity",
                    "model": "Linear mixed-effects model",
                    "error": f"Missing construct columns: {missing_constructs}",
                }
            ]
        )

    working = initial_constructs.copy()

    # Prefer an identifier that is unique across all base seeds.
    if "unique_agent_id" in working.columns:
        agent_id_column = "unique_agent_id"
    elif "persona_seed" in working.columns:
        agent_id_column = "persona_seed"
    elif "psychological_seed" in working.columns:
        agent_id_column = "psychological_seed"
    elif {"base_seed", "persona_index"}.issubset(working.columns):
        agent_id_column = "_agent_id"
        working[agent_id_column] = (
            working["base_seed"].astype(str)
            + "_"
            + working["persona_index"].astype(str)
        )
    elif "persona_id" in working.columns and working["persona_id"].is_unique:
        agent_id_column = "persona_id"
    else:
        return pd.DataFrame(
            [
                {
                    "analysis": "H2_between_agent_heterogeneity",
                    "model": "Linear mixed-effects model",
                    "error": "No unique agent identifier could be determined.",
                }
            ]
        )

    working = working[[agent_id_column, *constructs]].dropna().copy()
    if working.empty or working[agent_id_column].nunique() < 2:
        return pd.DataFrame()

    long_data = working.melt(
        id_vars=[agent_id_column],
        value_vars=constructs,
        var_name="construct",
        value_name="construct_value",
    )
    long_data[agent_id_column] = long_data[agent_id_column].astype(str)
    long_data["construct"] = pd.Categorical(
        long_data["construct"],
        categories=constructs,
        ordered=True,
    )

    fixed_formula = "construct_value ~ C(construct)"
    fixed_only_result = smf.ols(fixed_formula, data=long_data).fit()

    mixed_result = None
    optimizer_used = None
    selected_fit_warnings: list[str] = []
    fit_errors: list[str] = []
    for optimizer in ("bfgs", "powell", "nm", "cg"):
        try:
            model = smf.mixedlm(
                fixed_formula,
                data=long_data,
                groups=long_data[agent_id_column],
                re_formula="1",
            )
            with warnings.catch_warnings(record=True) as caught_warnings:
                warnings.simplefilter("always")
                candidate = model.fit(
                    reml=False,
                    method=optimizer,
                    maxiter=5000,
                    disp=False,
                )
            if np.isfinite(candidate.llf):
                mixed_result = candidate
                optimizer_used = optimizer
                selected_fit_warnings = [
                    str(item.message) for item in caught_warnings
                ]
                break
        except Exception as exc:
            fit_errors.append(f"{optimizer}: {exc}")

    if mixed_result is None:
        return pd.DataFrame(
            [
                {
                    "analysis": "H2_between_agent_heterogeneity",
                    "model": "Linear mixed-effects model",
                    "error": "; ".join(fit_errors) or "Model fitting failed.",
                }
            ]
        )

    random_intercept_variance = float(mixed_result.cov_re.iloc[0, 0])
    random_intercept_variance = max(random_intercept_variance, 0.0)
    random_intercept_sd = math.sqrt(random_intercept_variance)
    residual_variance = float(mixed_result.scale)
    variance_total = random_intercept_variance + residual_variance
    icc = (
        random_intercept_variance / variance_total
        if variance_total > 0
        else np.nan
    )

    likelihood_ratio = max(
        0.0,
        2.0 * (float(mixed_result.llf) - float(fixed_only_result.llf)),
    )
    standard_chi_square_p = float(stats.chi2.sf(likelihood_ratio, df=1))
    boundary_corrected_p = (
        0.5 * standard_chi_square_p
        if likelihood_ratio > 0
        else 1.0
    )

    return pd.DataFrame(
        [
            {
                "analysis": "H2_between_agent_heterogeneity",
                "model": "construct_value ~ C(construct) + (1 | agent)",
                "fixed_effect": "construct",
                "random_effect": "agent random intercept",
                "agent_id_column": agent_id_column,
                "n_agents": int(working[agent_id_column].nunique()),
                "n_constructs": len(constructs),
                "n_observations": int(len(long_data)),
                "random_intercept_variance": random_intercept_variance,
                "random_intercept_sd": random_intercept_sd,
                "residual_variance": residual_variance,
                "icc": float(icc),
                "mixed_model_log_likelihood": float(mixed_result.llf),
                "fixed_only_log_likelihood": float(fixed_only_result.llf),
                "likelihood_ratio_chi2": likelihood_ratio,
                "degrees_of_freedom": 1,
                "p_value": boundary_corrected_p,
                "standard_chi_square_p_value": standard_chi_square_p,
                "significance": p_value_to_stars(boundary_corrected_p),
                "converged": bool(mixed_result.converged),
                "optimizer": optimizer_used,
                "fit_warnings": "; ".join(selected_fit_warnings),
                "inference_note": (
                    "Primary p value uses the 50:50 boundary correction for "
                    "testing a variance component against zero."
                ),
            }
        ]
    )

def binary_outcome_values(frame: pd.DataFrame, outcome: str) -> np.ndarray:
    if outcome == "planned":
        return frame["planned"].astype(float).to_numpy()
    return (frame["decision_label"] == outcome).astype(float).to_numpy()


def welch_degrees_of_freedom(
    variance_a: float,
    n_a: int,
    variance_b: float,
    n_b: int,
) -> float:
    numerator = (variance_a / n_a + variance_b / n_b) ** 2
    denominator = 0.0
    if n_a > 1:
        denominator += (variance_a / n_a) ** 2 / (n_a - 1)
    if n_b > 1:
        denominator += (variance_b / n_b) ** 2 / (n_b - 1)
    return numerator / denominator if denominator > 0 else np.nan


def paired_weekly_binary_test(
    frame: pd.DataFrame,
    group_col: str,
    group_a: str,
    group_b: str,
    outcome: str,
    analysis: str,
    alpha: float = ALPHA,
) -> dict[str, Any]:
    """Paired t test on weekly outcome rates across the two scenarios.

    Only complete 7-day weeks are included so that a final partial week does
    not receive the same weight as a complete week.
    """
    working = frame.copy()
    day_values = working["day_index"].astype(int)
    min_day = int(day_values.min())
    total_days = int(day_values.max()) - min_day + 1
    full_weeks = total_days // 7
    working["calendar_week_index"] = ((day_values - min_day) // 7).astype(int)
    working = working[working["calendar_week_index"] < full_weeks].copy()
    if outcome == "planned":
        working["outcome_binary"] = working["planned"].astype(float)
    else:
        working["outcome_binary"] = (
            working["decision_label"] == outcome
        ).astype(float)

    weekly = working.pivot_table(
        index="calendar_week_index",
        columns=group_col,
        values="outcome_binary",
        aggfunc="mean",
    )
    if group_a not in weekly.columns or group_b not in weekly.columns:
        return {
            "analysis": analysis,
            "test": "Paired-samples t test on weekly rates",
            "outcome": outcome,
            "group_a": group_a,
            "group_b": group_b,
            "n_pairs": 0,
            "mean_a_pct": np.nan,
            "mean_b_pct": np.nan,
            "mean_difference_a_minus_b_pp": np.nan,
            "statistic": np.nan,
            "degrees_of_freedom": np.nan,
            "p_value": np.nan,
            "cohens_dz": np.nan,
            "ci_lower_pp": np.nan,
            "ci_upper_pp": np.nan,
            "significance": "not estimable",
        }

    paired = weekly[[group_a, group_b]].dropna()
    values_a = paired[group_a].astype(float).to_numpy()
    values_b = paired[group_b].astype(float).to_numpy()
    differences = values_a - values_b
    n_pairs = len(differences)
    if n_pairs < 2 or np.std(differences, ddof=1) == 0:
        return {
            "analysis": analysis,
            "test": "Paired-samples t test on weekly rates",
            "outcome": outcome,
            "group_a": group_a,
            "group_b": group_b,
            "n_pairs": n_pairs,
            "mean_a_pct": 100 * float(np.mean(values_a)) if n_pairs else np.nan,
            "mean_b_pct": 100 * float(np.mean(values_b)) if n_pairs else np.nan,
            "mean_difference_a_minus_b_pp": 100 * float(np.mean(differences)) if n_pairs else np.nan,
            "statistic": np.nan,
            "degrees_of_freedom": max(n_pairs - 1, 0),
            "p_value": np.nan,
            "cohens_dz": np.nan,
            "ci_lower_pp": np.nan,
            "ci_upper_pp": np.nan,
            "significance": "not estimable",
        }

    test_result = stats.ttest_rel(values_a, values_b)
    mean_difference = float(np.mean(differences))
    standard_error = float(stats.sem(differences))
    degrees_of_freedom = n_pairs - 1
    critical = stats.t.ppf(1 - alpha / 2, degrees_of_freedom)
    cohens_dz = mean_difference / float(np.std(differences, ddof=1))

    return {
        "analysis": analysis,
        "test": "Paired-samples t test on weekly rates",
        "outcome": outcome,
        "group_a": group_a,
        "group_b": group_b,
        "n_pairs": n_pairs,
        "mean_a_pct": 100 * float(np.mean(values_a)),
        "mean_b_pct": 100 * float(np.mean(values_b)),
        "mean_difference_a_minus_b_pp": 100 * mean_difference,
        "statistic": float(test_result.statistic),
        "degrees_of_freedom": float(degrees_of_freedom),
        "p_value": float(test_result.pvalue),
        "cohens_dz": float(cohens_dz),
        "ci_lower_pp": 100 * float(mean_difference - critical * standard_error),
        "ci_upper_pp": 100 * float(mean_difference + critical * standard_error),
        "significance": p_value_to_stars(float(test_result.pvalue)),
    }


def two_group_binary_test(
    frame: pd.DataFrame,
    group_col: str,
    group_a: str,
    group_b: str,
    outcome: str,
    analysis: str,
    alpha: float = ALPHA,
) -> dict[str, Any]:
    values_a = binary_outcome_values(frame[frame[group_col] == group_a], outcome)
    values_b = binary_outcome_values(frame[frame[group_col] == group_b], outcome)
    n_a = len(values_a)
    n_b = len(values_b)

    mean_a = float(np.mean(values_a)) if n_a else np.nan
    mean_b = float(np.mean(values_b)) if n_b else np.nan
    variance_a = float(np.var(values_a, ddof=1)) if n_a > 1 else np.nan
    variance_b = float(np.var(values_b, ddof=1)) if n_b > 1 else np.nan

    if n_a < 2 or n_b < 2 or (
        np.nanstd(values_a) == 0 and np.nanstd(values_b) == 0
    ):
        return {
            "analysis": analysis,
            "test": "Welch independent-samples t test",
            "outcome": outcome,
            "group_a": group_a,
            "group_b": group_b,
            "n_a": n_a,
            "n_b": n_b,
            "mean_a_pct": 100 * mean_a,
            "mean_b_pct": 100 * mean_b,
            "mean_difference_a_minus_b_pp": 100 * (mean_a - mean_b),
            "statistic": np.nan,
            "degrees_of_freedom": np.nan,
            "p_value": np.nan,
            "cohens_d": np.nan,
            "ci_lower_pp": np.nan,
            "ci_upper_pp": np.nan,
            "significance": "not estimable",
        }

    test_result = stats.ttest_ind(values_a, values_b, equal_var=False)
    degrees_of_freedom = welch_degrees_of_freedom(
        variance_a,
        n_a,
        variance_b,
        n_b,
    )
    difference = mean_a - mean_b
    standard_error = math.sqrt(variance_a / n_a + variance_b / n_b)
    critical = stats.t.ppf(1 - alpha / 2, degrees_of_freedom)

    pooled_variance = (
        ((n_a - 1) * variance_a + (n_b - 1) * variance_b)
        / (n_a + n_b - 2)
    )
    pooled_sd = math.sqrt(pooled_variance) if pooled_variance > 0 else np.nan
    cohens_d = difference / pooled_sd if pooled_sd and not pd.isna(pooled_sd) else np.nan

    return {
        "analysis": analysis,
        "test": "Welch independent-samples t test",
        "outcome": outcome,
        "group_a": group_a,
        "group_b": group_b,
        "n_a": n_a,
        "n_b": n_b,
        "mean_a_pct": 100 * mean_a,
        "mean_b_pct": 100 * mean_b,
        "mean_difference_a_minus_b_pp": 100 * difference,
        "statistic": float(test_result.statistic),
        "degrees_of_freedom": float(degrees_of_freedom),
        "p_value": float(test_result.pvalue),
        "cohens_d": float(cohens_d) if not pd.isna(cohens_d) else np.nan,
        "ci_lower_pp": 100 * float(difference - critical * standard_error),
        "ci_upper_pp": 100 * float(difference + critical * standard_error),
        "significance": p_value_to_stars(float(test_result.pvalue)),
    }


def one_way_binary_anova(
    frame: pd.DataFrame,
    group_col: str,
    group_order: list[str],
    outcome: str,
    analysis: str,
) -> dict[str, Any]:
    groups: list[np.ndarray] = []
    valid_labels: list[str] = []
    for label in group_order:
        values = binary_outcome_values(frame[frame[group_col] == label], outcome)
        if len(values):
            groups.append(values)
            valid_labels.append(label)

    all_values = np.concatenate(groups) if groups else np.array([])
    if len(groups) < 2 or len(all_values) == 0 or np.std(all_values) == 0:
        return {
            "analysis": analysis,
            "test": "One-way ANOVA",
            "outcome": outcome,
            "groups": ";".join(valid_labels),
            "n_total": len(all_values),
            "statistic": np.nan,
            "df_between": max(len(groups) - 1, 0),
            "df_within": max(len(all_values) - len(groups), 0),
            "p_value": np.nan,
            "eta_squared": np.nan,
            "omega_squared": np.nan,
            "significance": "not estimable",
        }

    result = stats.f_oneway(*groups)
    grand_mean = float(np.mean(all_values))
    ss_between = sum(len(values) * (float(np.mean(values)) - grand_mean) ** 2 for values in groups)
    ss_within = sum(float(np.sum((values - float(np.mean(values))) ** 2)) for values in groups)
    ss_total = ss_between + ss_within
    df_between = len(groups) - 1
    df_within = len(all_values) - len(groups)
    ms_within = ss_within / df_within if df_within > 0 else np.nan
    eta_squared = ss_between / ss_total if ss_total > 0 else np.nan
    omega_squared = (
        (ss_between - df_between * ms_within) / (ss_total + ms_within)
        if ss_total > 0 and not pd.isna(ms_within)
        else np.nan
    )

    return {
        "analysis": analysis,
        "test": "One-way ANOVA",
        "outcome": outcome,
        "groups": ";".join(valid_labels),
        "n_total": len(all_values),
        "statistic": float(result.statistic),
        "df_between": df_between,
        "df_within": df_within,
        "p_value": float(result.pvalue),
        "eta_squared": float(eta_squared),
        "omega_squared": float(omega_squared),
        "significance": p_value_to_stars(float(result.pvalue)),
    }


def pairwise_binary_posthoc(
    frame: pd.DataFrame,
    group_col: str,
    group_order: list[str],
    outcome: str,
    analysis: str,
    alpha: float = ALPHA,
) -> pd.DataFrame:
    from itertools import combinations

    raw_rows: list[dict[str, Any]] = []
    for group_a, group_b in combinations(group_order, 2):
        values_a = binary_outcome_values(frame[frame[group_col] == group_a], outcome)
        values_b = binary_outcome_values(frame[frame[group_col] == group_b], outcome)
        if len(values_a) < 2 or len(values_b) < 2:
            continue

        mean_a = float(np.mean(values_a))
        mean_b = float(np.mean(values_b))
        variance_a = float(np.var(values_a, ddof=1))
        variance_b = float(np.var(values_b, ddof=1))
        difference = mean_a - mean_b

        if np.std(values_a) == 0 and np.std(values_b) == 0:
            statistic = np.nan
            p_raw = np.nan
            df = np.nan
            standard_error = np.nan
            cohens_d = np.nan
        else:
            result = stats.ttest_ind(values_a, values_b, equal_var=False)
            statistic = float(result.statistic)
            p_raw = float(result.pvalue)
            df = welch_degrees_of_freedom(
                variance_a,
                len(values_a),
                variance_b,
                len(values_b),
            )
            standard_error = math.sqrt(
                variance_a / len(values_a) + variance_b / len(values_b)
            )
            pooled_variance = (
                ((len(values_a) - 1) * variance_a + (len(values_b) - 1) * variance_b)
                / (len(values_a) + len(values_b) - 2)
            )
            pooled_sd = math.sqrt(pooled_variance) if pooled_variance > 0 else np.nan
            cohens_d = difference / pooled_sd if pooled_sd and not pd.isna(pooled_sd) else np.nan

        raw_rows.append(
            {
                "analysis": analysis,
                "test": "Pairwise Welch t test with Bonferroni correction",
                "outcome": outcome,
                "group_a": group_a,
                "group_b": group_b,
                "n_a": len(values_a),
                "n_b": len(values_b),
                "mean_a_pct": 100 * mean_a,
                "mean_b_pct": 100 * mean_b,
                "mean_difference_a_minus_b_pp": 100 * difference,
                "statistic": statistic,
                "degrees_of_freedom": df,
                "p_raw": p_raw,
                "standard_error": standard_error,
                "cohens_d": cohens_d,
            }
        )

    result_df = pd.DataFrame(raw_rows)
    if result_df.empty:
        return result_df

    valid_mask = result_df["p_raw"].notna()
    result_df["p_adjusted"] = np.nan
    result_df.loc[valid_mask, "p_adjusted"] = multipletests(
        result_df.loc[valid_mask, "p_raw"].to_numpy(),
        alpha=alpha,
        method="bonferroni",
    )[1]

    number_of_comparisons = max(int(valid_mask.sum()), 1)
    adjusted_alpha = alpha / number_of_comparisons
    ci_lowers: list[float] = []
    ci_uppers: list[float] = []
    for _, row in result_df.iterrows():
        if pd.isna(row["standard_error"]) or pd.isna(row["degrees_of_freedom"]):
            ci_lowers.append(np.nan)
            ci_uppers.append(np.nan)
            continue
        critical = stats.t.ppf(
            1 - adjusted_alpha / 2,
            float(row["degrees_of_freedom"]),
        )
        difference = float(row["mean_difference_a_minus_b_pp"]) / 100
        ci_lowers.append(100 * (difference - critical * float(row["standard_error"])))
        ci_uppers.append(100 * (difference + critical * float(row["standard_error"])))

    result_df["bonferroni_ci_lower_pp"] = ci_lowers
    result_df["bonferroni_ci_upper_pp"] = ci_uppers
    result_df["significance"] = result_df["p_adjusted"].map(p_value_to_stars)
    return result_df.drop(columns=["standard_error"])


def calculate_h3_h4_inferential_tests(
    scenario_day_all: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    unplanned = scenario_day_all[~scenario_day_all["planned"]].copy()
    planned = scenario_day_all[scenario_day_all["planned"]].copy()

    tests = [
        paired_weekly_binary_test(
            planned,
            "scenario",
            "Supportive",
            "Hindering",
            "do_planned_activity",
            "H3_planned_do_by_scenario",
        ),
        paired_weekly_binary_test(
            unplanned,
            "scenario",
            "Supportive",
            "Hindering",
            "extra_activity",
            "H3_unplanned_extra_by_scenario",
        ),
        paired_weekly_binary_test(
            planned,
            "scenario",
            "Supportive",
            "Hindering",
            "adapt_activity",
            "H4_planned_adapt_by_scenario",
        ),
        paired_weekly_binary_test(
            scenario_day_all,
            "scenario",
            "Supportive",
            "Hindering",
            "planned",
            "Exploratory_planned_PA_days_by_scenario",
        ),
        one_way_binary_anova(
            planned,
            "context_class",
            CONTEXT_ORDER,
            "do_planned_activity",
            "H3_planned_do_by_context",
        ),
        one_way_binary_anova(
            unplanned,
            "context_class",
            CONTEXT_ORDER,
            "extra_activity",
            "H3_unplanned_extra_by_context",
        ),
        one_way_binary_anova(
            planned,
            "context_class",
            CONTEXT_ORDER,
            "adapt_activity",
            "H4_planned_adapt_by_context",
        ),
        one_way_binary_anova(
            planned,
            "context_class",
            CONTEXT_ORDER,
            "skip_activity",
            "H4_planned_skip_by_context",
        ),
    ]

    posthoc_frames = [
        pairwise_binary_posthoc(
            planned,
            "context_class",
            CONTEXT_ORDER,
            "do_planned_activity",
            "H3_planned_do_by_context",
        ),
        pairwise_binary_posthoc(
            unplanned,
            "context_class",
            CONTEXT_ORDER,
            "extra_activity",
            "H3_unplanned_extra_by_context",
        ),
        pairwise_binary_posthoc(
            planned,
            "context_class",
            CONTEXT_ORDER,
            "adapt_activity",
            "H4_planned_adapt_by_context",
        ),
    ]
    tests_df = pd.DataFrame(tests)
    non_empty = [frame for frame in posthoc_frames if not frame.empty]
    posthoc = pd.concat(non_empty, ignore_index=True) if non_empty else pd.DataFrame()
    if not posthoc.empty and not tests_df.empty:
        significant_omnibus = set(
            tests_df.loc[
                tests_df["p_value"].notna() & (tests_df["p_value"] < ALPHA),
                "analysis",
            ]
        )
        posthoc = posthoc[posthoc["analysis"].isin(significant_omnibus)].copy()
    return tests_df, posthoc


def add_significance_brackets(
    ax: plt.Axes,
    x_by_group: dict[str, float],
    posthoc: pd.DataFrame,
    inferential_tests: pd.DataFrame,
    analysis_name: str,
    starting_y: float | None = None,
    step: float = 8.0,
) -> None:
    if posthoc.empty or inferential_tests.empty:
        return
    omnibus = inferential_tests[inferential_tests["analysis"] == analysis_name]
    if (
        omnibus.empty
        or pd.isna(omnibus.iloc[0]["p_value"])
        or float(omnibus.iloc[0]["p_value"]) >= ALPHA
    ):
        return
    subset = posthoc[
        (posthoc["analysis"] == analysis_name)
        & (posthoc["p_adjusted"].notna())
        & (posthoc["p_adjusted"] < ALPHA)
    ].copy()
    if subset.empty:
        return

    comparisons: list[dict[str, Any]] = []
    for _, row in subset.iterrows():
        group_a = str(row["group_a"])
        group_b = str(row["group_b"])
        if group_a not in x_by_group or group_b not in x_by_group:
            continue
        x1 = float(x_by_group[group_a])
        x2 = float(x_by_group[group_b])
        comparisons.append(
            {
                "x1": min(x1, x2),
                "x2": max(x1, x2),
                "span": abs(x2 - x1),
                "p_adjusted": float(row["p_adjusted"]),
            }
        )
    if not comparisons:
        return

    if starting_y is None:
        patch_tops = [patch.get_height() for patch in ax.patches]
        starting_y = (max(patch_tops) if patch_tops else 0.0) + 4.0

    y = float(starting_y)
    for comparison in sorted(
        comparisons,
        key=lambda item: (item["span"], item["x1"], item["x2"]),
    ):
        x1 = comparison["x1"]
        x2 = comparison["x2"]
        ax.plot(
            [x1, x1, x2, x2],
            [y, y + 1.5, y + 1.5, y],
            linewidth=1.0,
            color="black",
        )
        ax.text(
            (x1 + x2) / 2,
            y + 1.8,
            p_value_to_stars(comparison["p_adjusted"]),
            ha="center",
            va="bottom",
            fontsize=10,
        )
        y += step
    ax.set_ylim(0, max(ax.get_ylim()[1], y + 2))


def write_figures(
    figures_dir: Path,
    h1_correlation_inference: pd.DataFrame,
    h2_construct_summary: pd.DataFrame | None,
    h2_construct_sd_intervals: pd.DataFrame,
    scenario_decisions_by_daytype: pd.DataFrame,
    h3_unplanned_by_context: pd.DataFrame,
    h4_planned_by_scenario: pd.DataFrame,
    h4_planned_by_context: pd.DataFrame,
    construct_trajectories_summary: pd.DataFrame,
    inferential_tests: pd.DataFrame,
    pairwise_posthoc: pd.DataFrame,
) -> None:
    if not h1_correlation_inference.empty:
        selected_vars = [
            "temperature_mean_c",
            "temperature_daily_max_mean_c",
            "temperature_daily_min_mean_c",
            "precipitation_total_mm",
            "precip_days_ge_1mm",
            "sunshine_hours",
            "wind_m_s",
            "snow_cover_days",
        ]
        available = [
            variable
            for variable in selected_vars
            if variable in set(h1_correlation_inference["variable"])
        ]
        if available and "selected_coefficient" in h1_correlation_inference.columns:
            plot_df = (
                h1_correlation_inference[
                    h1_correlation_inference["variable"].isin(available)
                ]
                .set_index("variable")
                .loc[available]
                .reset_index()
            )
            ax = plot_df.plot(
                x="variable",
                y="selected_coefficient",
                kind="bar",
                legend=False,
                figsize=(11, 6),
            )
            ax.set_title("")
            ax.set_xlabel("Weather variable")
            ax.set_ylabel("Correlation coefficient")
            ax.tick_params(axis="x", rotation=30)
            ax.grid(axis="y", alpha=0.25)
            ax.set_axisbelow(True)
            fig = ax.get_figure()
            fig.tight_layout()
            fig.savefig(figures_dir / "figure_h1_weather_correlations.png", dpi=300)
            plt.close(fig)

    if h2_construct_summary is not None:
        sd_col = (
            "population_sd"
            if "population_sd" in h2_construct_summary.columns
            else "sd"
            if "sd" in h2_construct_summary.columns
            else None
        )
        if sd_col is not None:
            construct_label_map = {
                "action_planning": "Action\nplanning",
                "automaticity": "Automaticity",
                "attitude_toward_the_behavior": "Attitude\ntoward the\nbehavior",
                "pa_specific_self_control": "PA-specific\nself-control",
                "intention": "Intention",
                "perceived_behavioral_control": "Perceived\nbehavioral\ncontrol",
                "subjective_norm": "Subjective\nnorm",
                "motivational_competence": "Motivational\ncompetence",
                "intrinsic_motivation": "Intrinsic\nmotivation",
            }

            plot_df = h2_construct_summary.sort_values(
                sd_col,
                ascending=False,
            ).copy()
            plot_df["construct_label"] = (
                plot_df["construct"]
                .map(construct_label_map)
                .fillna(plot_df["construct"])
            )
            if not h2_construct_sd_intervals.empty:
                plot_df = plot_df.merge(
                    h2_construct_sd_intervals[
                        ["construct", "sd_ci_lower", "sd_ci_upper"]
                    ],
                    on="construct",
                    how="left",
                )

            fig, ax = plt.subplots(figsize=(12.0, 5.4))
            x = np.arange(len(plot_df))
            values = plot_df[sd_col].astype(float).to_numpy()
            yerr = None
            if {"sd_ci_lower", "sd_ci_upper"}.issubset(plot_df.columns):
                yerr = np.vstack(
                    [
                        values - plot_df["sd_ci_lower"].astype(float).to_numpy(),
                        plot_df["sd_ci_upper"].astype(float).to_numpy() - values,
                    ]
                )
            ax.bar(
                x,
                values,
                yerr=yerr,
                capsize=3 if yerr is not None else 0,
            )
            ax.set_xticks(x)
            ax.set_xticklabels(plot_df["construct_label"], fontsize=9)
            ax.set_xlabel("Construct")
            ax.set_ylabel("SD")
            ax.set_ylim(0, 1)
            ax.set_yticks(np.arange(0, 1.01, 0.2))
            ax.grid(axis="y", alpha=0.25)
            ax.set_axisbelow(True)
            fig.tight_layout()
            fig.savefig(
                figures_dir / "figure_h2_construct_heterogeneity.png",
                dpi=300,
                bbox_inches="tight",
            )
            plt.close(fig)

    plot_table = scenario_decisions_by_daytype.copy()
    plot_table["day_type"] = np.where(
        plot_table["planned"],
        "planned days",
        "unplanned days",
    )
    plot_table["scenario_day_type"] = (
        plot_table["scenario"] + " – " + plot_table["day_type"]
    )
    decision_counts = plot_table.set_index("scenario_day_type")[
        [f"{category}_n" for category in DECISION_CATEGORIES]
    ]
    decision_counts.columns = DECISION_CATEGORIES
    ax = decision_counts.plot(kind="bar", figsize=(12, 6))
    ax.set_title("")
    ax.set_xlabel("Scenario and day type")
    ax.set_ylabel("Number of days")
    ax.tick_params(axis="x", rotation=25)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.14),
        ncol=2,
        frameon=False,
    )
    fig = ax.get_figure()
    fig.tight_layout()
    fig.savefig(
        figures_dir / "figure_decision_categories_by_scenario_daytype.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)

    # H3 figure: unplanned days by realized daily context.
    h3_plot = h3_unplanned_by_context.set_index("context_class").reindex(CONTEXT_ORDER)
    x = np.arange(len(CONTEXT_ORDER))
    width = 0.32
    fig, ax = plt.subplots(figsize=(10.0, 5.6))
    h3_specs = [
        ("skip_activity", "Skip Activity", -width / 2),
        ("extra_activity", "Extra Activity", width / 2),
    ]
    for category, label, offset in h3_specs:
        values = h3_plot[f"{category}_pct"].astype(float).to_numpy()
        lower = h3_plot[f"{category}_ci_lower_pct"].astype(float).to_numpy()
        upper = h3_plot[f"{category}_ci_upper_pct"].astype(float).to_numpy()
        yerr = np.vstack([values - lower, upper - values])
        ax.bar(
            x + offset,
            values,
            width,
            label=label,
            yerr=yerr,
            capsize=3,
        )
    ax.set_xticks(x)
    ax.set_xticklabels([CONTEXT_DISPLAY[value] for value in CONTEXT_ORDER])
    ax.set_xlabel("Classified Daily Context")
    ax.set_ylabel("Percentage of days with no planned PA [%]")
    ax.set_ylim(0, 100)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2, frameon=False)
    extra_x = {
        group: float(x[index] + width / 2)
        for index, group in enumerate(CONTEXT_ORDER)
    }
    h3_start_y = max(
        float(np.nanmax(h3_plot["skip_activity_ci_upper_pct"].astype(float).to_numpy())),
        float(np.nanmax(h3_plot["extra_activity_ci_upper_pct"].astype(float).to_numpy())),
    ) + 4.0
    add_significance_brackets(
        ax,
        extra_x,
        pairwise_posthoc,
        inferential_tests,
        "H3_unplanned_extra_by_context",
        starting_y=h3_start_y,
    )
    fig.tight_layout()
    fig.savefig(
        figures_dir / "figure_h3_unplanned_decisions_by_context.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)

    # H4 structural scenario figure.
    h4_plot = h4_planned_by_scenario.set_index("scenario")
    scenario_order = ["Supportive", "Hindering"]
    h4_plot = h4_plot.reindex(scenario_order)
    x = np.arange(len(scenario_order))
    width = 0.32
    fig, ax = plt.subplots(figsize=(8.5, 5.4))
    h4_scenario_specs = [
        ("do_planned_activity", "Do Planned Activity", -width / 2),
        ("adapt_activity", "Adapt Activity", width / 2),
    ]
    for category, label, offset in h4_scenario_specs:
        values = h4_plot[f"{category}_pct"].astype(float).to_numpy()
        lower = h4_plot[f"{category}_ci_lower_pct"].astype(float).to_numpy()
        upper = h4_plot[f"{category}_ci_upper_pct"].astype(float).to_numpy()
        yerr = np.vstack([values - lower, upper - values])
        ax.bar(
            x + offset,
            values,
            width,
            label=label,
            yerr=yerr,
            capsize=3,
        )
    ax.set_xticks(x)
    ax.set_xticklabels([value.lower() for value in scenario_order])
    ax.set_xlabel("Structural Scenario")
    ax.set_ylabel("Percentage of days with planned PA [%]")
    ax.set_ylim(0, 100)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(
        figures_dir / "figure_h4_planned_decisions_by_scenario.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)

    # H4 figure: planned days by realized daily context.
    h4_context_plot = h4_planned_by_context.set_index("context_class").reindex(CONTEXT_ORDER)
    x = np.arange(len(CONTEXT_ORDER))
    width = 0.32
    fig, ax = plt.subplots(figsize=(10.0, 5.6))
    h4_context_specs = [
        ("do_planned_activity", "Do Planned Activity", -width / 2),
        ("adapt_activity", "Adapt Activity", width / 2),
    ]
    for category, label, offset in h4_context_specs:
        values = h4_context_plot[f"{category}_pct"].astype(float).to_numpy()
        lower = h4_context_plot[f"{category}_ci_lower_pct"].astype(float).to_numpy()
        upper = h4_context_plot[f"{category}_ci_upper_pct"].astype(float).to_numpy()
        yerr = np.vstack([values - lower, upper - values])
        ax.bar(
            x + offset,
            values,
            width,
            label=label,
            yerr=yerr,
            capsize=3,
        )
    ax.set_xticks(x)
    ax.set_xticklabels([CONTEXT_DISPLAY[value] for value in CONTEXT_ORDER])
    ax.set_xlabel("Classified Daily Context")
    ax.set_ylabel("Percentage of days with planned PA [%]")
    ax.set_ylim(0, 100)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2, frameon=False)
    adapt_x = {
        group: float(x[index] + width / 2)
        for index, group in enumerate(CONTEXT_ORDER)
    }
    h4_start_y = max(
        float(np.nanmax(h4_context_plot["do_planned_activity_ci_upper_pct"].astype(float).to_numpy())),
        float(np.nanmax(h4_context_plot["adapt_activity_ci_upper_pct"].astype(float).to_numpy())),
    ) + 4.0
    add_significance_brackets(
        ax,
        adapt_x,
        pairwise_posthoc,
        inferential_tests,
        "H4_planned_adapt_by_context",
        starting_y=h4_start_y,
    )
    fig.tight_layout()
    fig.savefig(
        figures_dir / "figure_h4_planned_decisions_by_context.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)

    construct_end = construct_trajectories_summary.pivot(
        index="construct",
        columns="scenario",
        values="end",
    )
    ax = construct_end.plot(kind="bar", figsize=(12, 6))
    ax.set_title("")
    ax.set_xlabel("Construct")
    ax.set_ylabel("Normalized final value")
    ax.set_ylim(0, 1)
    ax.tick_params(axis="x", rotation=30)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2, frameon=False)
    fig = ax.get_figure()
    fig.tight_layout()
    fig.savefig(
        figures_dir / "figure_construct_final_values_by_scenario.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)

def write_docs(
    docs_dir: Path,
    data_audit: pd.DataFrame,
    h1_summary_metrics: pd.DataFrame | None,
    h1_correlation_inference: pd.DataFrame,
    h2_similarity: pd.DataFrame | None,
    h2_phase_counts: pd.DataFrame | None,
    h2_construct_sd_intervals: pd.DataFrame,
    h2_construct_mixed_effects: pd.DataFrame,
    h3_unplanned_by_scenario: pd.DataFrame,
    h3_unplanned_by_context: pd.DataFrame,
    h4_planned_by_scenario: pd.DataFrame,
    h4_planned_by_context: pd.DataFrame,
    effects_structural: pd.DataFrame,
    inferential_tests: pd.DataFrame,
    pairwise_posthoc: pd.DataFrame,
    construct_trajectories_summary: pd.DataFrame,
) -> None:
    analysis_plan = """# Final analysis plan for H1-H4

## Fixed analysis decisions

1. Edge-case rules are applied:
   - Unplanned days without a downtime window are classified as `hindering`.
   - If the location immediately before planned PA is unknown, the last preceding hour with known accessibility is used.

2. H3 and H4 report all decision categories:
   - H3: planned and unplanned days are analysed separately.
   - H4: planned PA days are analysed using adaptation and skipping as hindering-consistent outcomes.

3. Statistical reporting includes:
   - descriptive frequencies and percentages;
   - 95% Wilson confidence intervals for proportions;
   - Pearson or Spearman correlations for H1, selected after Shapiro-Wilk checks;
   - paired-samples t tests on complete calendar-week rates for two-scenario comparisons;
   - one-way ANOVA for the three realised context classes;
   - Bonferroni-adjusted pairwise Welch t tests after a significant omnibus ANOVA;
   - effect sizes (Cohen's d, eta squared, and omega squared);
   - a linear mixed-effects model testing between-agent variation after accounting for systematic differences between constructs.

4. Significance notation in figures:
   - * p < .05
   - ** p < .01
   - *** p < .001
"""

    h1_text = (
        table_to_markdown(h1_correlation_inference, float_fmt="{:.3f}")
        if not h1_correlation_inference.empty
        else "H1 inferential table not available."
    )
    h2_similarity_text = (
        table_to_markdown(h2_similarity, float_fmt="{:.2f}")
        if h2_similarity is not None
        else "H2 schedule similarity table not available."
    )
    h2_phase_text = (
        table_to_markdown(h2_phase_counts, float_fmt="{:.2f}")
        if h2_phase_counts is not None
        else "H2 phase table not available."
    )
    h2_ci_text = (
        table_to_markdown(h2_construct_sd_intervals, float_fmt="{:.3f}")
        if not h2_construct_sd_intervals.empty
        else "H2 construct SD confidence intervals not available."
    )
    h2_mixed_effects_text = (
        table_to_markdown(
            prepare_inferential_table_for_markdown(h2_construct_mixed_effects),
            float_fmt="{:.4f}",
        )
        if not h2_construct_mixed_effects.empty
        else "H2 linear mixed-effects model not available."
    )
    inferential_text = (
        table_to_markdown(
            prepare_inferential_table_for_markdown(inferential_tests),
            float_fmt="{:.4f}",
        )
        if not inferential_tests.empty
        else "Inferential tests not available."
    )
    posthoc_text = (
        table_to_markdown(
            prepare_inferential_table_for_markdown(pairwise_posthoc),
            float_fmt="{:.4f}",
        )
        if not pairwise_posthoc.empty
        else "Pairwise post-hoc tests not available."
    )

    results_summary = f"""# Final H1-H4 results summary

## Data audit

{table_to_markdown(data_audit, float_fmt="{:.1f}")}

## H1: Environmental conditions

{h1_text}

## H2: Agent heterogeneity

Schedule similarity:

{h2_similarity_text}

Phase distribution:

{h2_phase_text}

Construct SD confidence intervals:

{h2_ci_text}

Linear mixed-effects model:

{h2_mixed_effects_text}

## H3: Decisions on unplanned days

Structural scenario comparison:

{table_to_markdown(h3_unplanned_by_scenario, float_fmt="{:.2f}")}

Realised daily context:

{table_to_markdown(h3_unplanned_by_context, float_fmt="{:.2f}")}

## H4: Decisions on planned PA days

Structural scenario comparison:

{table_to_markdown(h4_planned_by_scenario, float_fmt="{:.2f}")}

Realised daily context:

{table_to_markdown(h4_planned_by_context, float_fmt="{:.2f}")}

## Structural effect sizes

{table_to_markdown(effects_structural, float_fmt="{:.3f}")}

## Inferential tests

{inferential_text}

## Bonferroni-adjusted post-hoc tests

{posthoc_text}

## Psychological construct trajectories

{table_to_markdown(construct_trajectories_summary, float_fmt="{:.3f}")}
"""

    (docs_dir / "analysis_plan.md").write_text(analysis_plan, encoding="utf-8")
    (docs_dir / "results_summary.md").write_text(results_summary, encoding="utf-8")



def write_combined_weather_comparison_figure(
    h1_dir: Path,
    target_path: Path,
) -> bool:
    """Write one compact H1 weather figure with temperature and precipitation.

    The output is a two-panel figure:
    - left: simulated versus reference temperature values (mean, daily maximum,
      daily minimum) in a single axis;
    - right: simulated versus reference total monthly precipitation with the 95%
      simulation interval.

    This layout is intended for the manuscript where temperature and
    precipitation should be shown side by side in a compact format.
    """
    data_path = h1_dir / "data" / "monthly_climate_comparison.csv"
    if not data_path.exists():
        return False

    monthly = pd.read_csv(data_path)
    required_columns = {
        "variable",
        "month",
        "month_label",
        "reference_value",
        "simulated_mean",
    }
    if not required_columns.issubset(monthly.columns):
        return False

    temp_specs = [
        ("temperature_mean_c", "Mean"),
        ("temperature_daily_max_mean_c", "Daily maximum"),
        ("temperature_daily_min_mean_c", "Daily minimum"),
    ]
    precip_var = "precipitation_total_mm"

    fig, (ax_temp, ax_precip) = plt.subplots(
        1,
        2,
        figsize=(12.5, 4.6),
        gridspec_kw={"width_ratios": [1.25, 1.0]},
        constrained_layout=True,
    )

    x_positions: np.ndarray | None = None
    month_labels: list[str] | None = None

    for idx, (variable, label) in enumerate(temp_specs):
        plot_df = monthly[monthly["variable"] == variable].sort_values("month")
        if plot_df.empty:
            plt.close(fig)
            return False

        x = np.arange(len(plot_df))
        if x_positions is None:
            x_positions = x
            month_labels = plot_df["month_label"].astype(str).tolist()

        line_color = f"C{idx}"
        ax_temp.plot(
            x,
            plot_df["reference_value"].astype(float),
            marker="o",
            markersize=3.8,
            linewidth=1.6,
            linestyle="-",
            color=line_color,
            label=f"{label} reference",
        )
        ax_temp.plot(
            x,
            plot_df["simulated_mean"].astype(float),
            marker="s",
            markersize=3.8,
            linewidth=1.6,
            linestyle="--",
            color=line_color,
            label=f"{label} simulated",
        )

    precip_df = monthly[monthly["variable"] == precip_var].sort_values("month")
    if precip_df.empty:
        plt.close(fig)
        return False

    if not {"simulated_p025", "simulated_p975"}.issubset(precip_df.columns):
        plt.close(fig)
        return False

    x = np.arange(len(precip_df))
    ax_precip.fill_between(
        x,
        precip_df["simulated_p025"].astype(float),
        precip_df["simulated_p975"].astype(float),
        alpha=0.18,
        label="95% simulation interval",
    )
    ax_precip.plot(
        x,
        precip_df["reference_value"].astype(float),
        marker="o",
        markersize=3.8,
        linewidth=1.6,
        linestyle="-",
        label="Reference",
    )
    ax_precip.plot(
        x,
        precip_df["simulated_mean"].astype(float),
        marker="s",
        markersize=3.8,
        linewidth=1.6,
        linestyle="-",
        label="Simulated mean",
    )

    if x_positions is not None and month_labels is not None:
        ax_temp.set_xticks(x_positions)
        ax_temp.set_xticklabels(month_labels)
        ax_precip.set_xticks(x_positions)
        ax_precip.set_xticklabels(month_labels)

    ax_temp.set_title("Temperature", fontsize=11)
    ax_temp.set_ylabel("Temperature (°C)")
    ax_temp.set_ylim(-5, 30)
    ax_temp.set_yticks(np.arange(-5, 31, 5))
    ax_temp.grid(True, alpha=0.25)
    ax_temp.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
        ncol=3,
        frameon=False,
        fontsize=8,
        handlelength=2.0,
        columnspacing=1.4,
    )

    ax_precip.set_title("Total precipitation", fontsize=11)
    ax_precip.set_ylabel("Precipitation (mm)")
    ax_precip.grid(True, alpha=0.25)
    ax_precip.legend(loc="upper left", frameon=False, fontsize=8)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return True

def copy_source_figures(h1_dir: Path, h2_dir: Path, figures_dir: Path) -> None:
    source_dir = figures_dir / "source_figures_h1_h2"
    source_dir.mkdir(parents=True, exist_ok=True)

    candidates = [
        h2_dir / "figures" / "construct_heatmap.png",
        h2_dir / "figures" / "annual_schedule_similarity_distribution.png",
    ]

    for path in candidates:
        if path.exists():
            shutil.copy2(path, source_dir / path.name)

    # Generate one compact combined H1 figure for the manuscript.
    write_combined_weather_comparison_figure(
        h1_dir,
        source_dir / "weather_monthly_comparison.png",
    )


def main() -> None:
    args = parse_args()
    tables_dir, figures_dir, docs_dir, work_dir = prepare_output_dir(
        args.output_dir,
        overwrite=args.overwrite,
    )

    supportive = load_scenario("Supportive", args.supportive, work_dir)
    hindering = load_scenario("Hindering", args.hindering, work_dir)

    scenario_audit = pd.DataFrame(
        [validate_scenario(supportive), validate_scenario(hindering)]
    )

    if not scenario_audit["complete_365_day_run"].all():
        raise ValueError(
            "At least one H3/H4 scenario is not a complete 365-day successful run. "
            f"See audit:\n{scenario_audit.to_string(index=False)}"
        )

    h1_tables_dir = args.h1_dir / "tables"
    h2_tables_dir = args.h2_dir / "tables"

    h1_summary_metrics = load_optional_table(args.h1_dir, "tables/h1_summary_metrics.csv")
    h1_interval_coverage = load_optional_table(args.h1_dir, "tables/h1_interval_coverage.csv")
    h1_annual_summary = load_optional_table(args.h1_dir, "tables/h1_annual_summary.csv")
    h1_monthly_comparison = load_optional_table(args.h1_dir, "data/monthly_climate_comparison.csv")

    h2_similarity = load_optional_table(args.h2_dir, "tables/schedule_similarity_overall_summary.csv")
    h2_phase_counts = load_optional_table(args.h2_dir, "tables/phase_week_count_summary.csv")
    h2_construct_summary = load_optional_table(args.h2_dir, "tables/construct_heterogeneity_summary.csv")
    h2_phase_activity = load_optional_table(args.h2_dir, "tables/phase_activity_summary.csv")
    h2_initial_constructs = load_optional_table(args.h2_dir, "data/initial_psychological_constructs.csv")

    h1_status = "complete" if h1_summary_metrics is not None else "missing h1_summary_metrics.csv"
    h2_status = (
        "complete"
        if h2_similarity is not None and h2_phase_counts is not None and h2_construct_summary is not None
        else "missing one or more required H2 tables"
    )

    supportive_context = classify_scenario(supportive)
    hindering_context = classify_scenario(hindering)
    context_all = pd.concat([supportive_context, hindering_context], ignore_index=True)

    scenario_day_all = pd.concat(
        [
            scenario_daily_with_context(supportive, supportive_context),
            scenario_daily_with_context(hindering, hindering_context),
        ],
        ignore_index=True,
    )

    diagnostics_all = pd.concat(
        [
            decision_policy_diagnostics(supportive),
            decision_policy_diagnostics(hindering),
        ],
        ignore_index=True,
    )

    scenario_decisions_by_daytype = tabulate_decisions(scenario_day_all, ["scenario", "planned"])
    h3_unplanned_by_scenario = tabulate_decisions(
        scenario_day_all[~scenario_day_all["planned"]],
        ["scenario"],
    )
    h3_unplanned_by_context = tabulate_decisions(
        scenario_day_all[~scenario_day_all["planned"]],
        ["context_class"],
    )
    h3_unplanned_by_scenario_context = tabulate_decisions(
        scenario_day_all[~scenario_day_all["planned"]],
        ["scenario", "context_class"],
    )
    h4_planned_by_scenario = tabulate_decisions(
        scenario_day_all[scenario_day_all["planned"]],
        ["scenario"],
    )
    h4_planned_by_context = tabulate_decisions(
        scenario_day_all[scenario_day_all["planned"]],
        ["context_class"],
    )
    h4_planned_by_scenario_context = tabulate_decisions(
        scenario_day_all[scenario_day_all["planned"]],
        ["scenario", "context_class"],
    )
    phase_decisions = tabulate_decisions(
        scenario_day_all,
        ["scenario", "phase", "planned"],
    )

    scenario_decisions_by_daytype = add_proportion_confidence_intervals(
        scenario_decisions_by_daytype
    )
    h3_unplanned_by_scenario = add_proportion_confidence_intervals(
        h3_unplanned_by_scenario
    )
    h3_unplanned_by_context = add_proportion_confidence_intervals(
        h3_unplanned_by_context
    )
    h3_unplanned_by_scenario_context = add_proportion_confidence_intervals(
        h3_unplanned_by_scenario_context
    )
    h4_planned_by_scenario = add_proportion_confidence_intervals(
        h4_planned_by_scenario
    )
    h4_planned_by_context = add_proportion_confidence_intervals(
        h4_planned_by_context
    )
    h4_planned_by_scenario_context = add_proportion_confidence_intervals(
        h4_planned_by_scenario_context
    )
    phase_decisions = add_proportion_confidence_intervals(phase_decisions)

    h1_correlation_inference = calculate_h1_correlation_inference(
        h1_monthly_comparison
    )
    h2_construct_sd_intervals = calculate_h2_construct_sd_intervals(
        h2_initial_constructs,
        h2_construct_summary,
    )
    h2_construct_mixed_effects = calculate_h2_construct_mixed_effects(h2_initial_constructs)
    inferential_tests, pairwise_posthoc = calculate_h3_h4_inferential_tests(
        scenario_day_all
    )

    effects_structural = pd.DataFrame(
        [
            rate_difference(
                scenario_day_all,
                "Supportive",
                "Hindering",
                lambda frame: ~frame["planned"],
                "extra_activity",
                "unplanned",
            ),
            rate_difference(
                scenario_day_all,
                "Supportive",
                "Hindering",
                lambda frame: ~frame["planned"],
                "skip_activity",
                "unplanned",
            ),
            rate_difference(
                scenario_day_all,
                "Supportive",
                "Hindering",
                lambda frame: frame["planned"],
                "do_planned_activity",
                "planned",
            ),
            rate_difference(
                scenario_day_all,
                "Supportive",
                "Hindering",
                lambda frame: frame["planned"],
                "adapt_activity",
                "planned",
            ),
            rate_difference(
                scenario_day_all,
                "Supportive",
                "Hindering",
                lambda frame: frame["planned"],
                "skip_activity",
                "planned",
            ),
        ]
    )

    construct_trajectories_summary = pd.concat(
        [construct_summary(supportive), construct_summary(hindering)],
        ignore_index=True,
    )

    supportive_hours, supportive_planned_days = activity_hours_from_trace(supportive.trace)
    hindering_hours, hindering_planned_days = activity_hours_from_trace(hindering.trace)

    data_audit = pd.DataFrame(
        [
            {
                "component": "H1 weather validation",
                "source": str(args.h1_dir),
                "status": h1_status,
                "rows_or_units": (
                    f"{len(h1_annual_summary)} simulated years"
                    if h1_annual_summary is not None
                    else "not available"
                ),
                "notes": "Final H1 output folder.",
            },
            {
                "component": "H2 agent heterogeneity",
                "source": str(args.h2_dir),
                "status": h2_status,
                "rows_or_units": "200 agent realizations",
                "notes": "Final H2 output folder.",
            },
            {
                "component": "Supportive scenario",
                "source": str(supportive.root),
                "status": "complete",
                "rows_or_units": f"{len(supportive.daily)} days / {len(supportive.trace['records'])} trace records",
                "notes": f"{supportive_planned_days} planned PA days, {supportive_hours:.1f} planned PA hours.",
            },
            {
                "component": "Hindering scenario",
                "source": str(hindering.root),
                "status": "complete",
                "rows_or_units": f"{len(hindering.daily)} days / {len(hindering.trace['records'])} trace records",
                "notes": f"{hindering_planned_days} planned PA days, {hindering_hours:.1f} planned PA hours.",
            },
        ]
    )

    # Save all tables.
    data_audit.to_csv(tables_dir / "data_audit.csv", index=False)
    scenario_audit.to_csv(tables_dir / "scenario_integrity_audit.csv", index=False)

    if h1_summary_metrics is not None:
        h1_summary_metrics.to_csv(tables_dir / "h1_summary_metrics.csv", index=False)
    if h1_interval_coverage is not None:
        h1_interval_coverage.to_csv(tables_dir / "h1_interval_coverage.csv", index=False)
    if h1_annual_summary is not None:
        h1_annual_summary.to_csv(tables_dir / "h1_annual_summary.csv", index=False)
    if not h1_correlation_inference.empty:
        h1_correlation_inference.to_csv(
            tables_dir / "h1_correlation_inference.csv",
            index=False,
        )

    if h2_similarity is not None:
        h2_similarity.to_csv(tables_dir / "h2_schedule_similarity_overall.csv", index=False)
    if h2_phase_counts is not None:
        h2_phase_counts.to_csv(tables_dir / "h2_phase_week_counts.csv", index=False)
    if h2_construct_summary is not None:
        h2_construct_summary.to_csv(tables_dir / "h2_construct_heterogeneity_summary.csv", index=False)
    if h2_phase_activity is not None:
        h2_phase_activity.to_csv(tables_dir / "h2_phase_activity_summary.csv", index=False)
    if not h2_construct_sd_intervals.empty:
        h2_construct_sd_intervals.to_csv(
            tables_dir / "h2_construct_sd_confidence_intervals.csv",
            index=False,
        )
    if not h2_construct_mixed_effects.empty:
        h2_construct_mixed_effects.to_csv(
            tables_dir / "h2_construct_mixed_effects.csv",
            index=False,
        )

    scenario_day_all.to_csv(tables_dir / "h3_h4_daily_analysis_dataset.csv", index=False)
    context_all.to_csv(tables_dir / "h3_h4_daily_context_classification.csv", index=False)
    diagnostics_all.to_csv(tables_dir / "llm2_decision_diagnostics.csv", index=False)
    scenario_decisions_by_daytype.to_csv(tables_dir / "scenario_decisions_by_daytype.csv", index=False)
    h3_unplanned_by_scenario.to_csv(tables_dir / "h3_unplanned_decisions_by_scenario.csv", index=False)
    h3_unplanned_by_context.to_csv(tables_dir / "h3_unplanned_decisions_by_context.csv", index=False)
    h3_unplanned_by_scenario_context.to_csv(tables_dir / "h3_unplanned_decisions_by_scenario_context.csv", index=False)
    h4_planned_by_scenario.to_csv(tables_dir / "h4_planned_decisions_by_scenario.csv", index=False)
    h4_planned_by_context.to_csv(tables_dir / "h4_planned_decisions_by_context.csv", index=False)
    h4_planned_by_scenario_context.to_csv(tables_dir / "h4_planned_decisions_by_scenario_context.csv", index=False)
    phase_decisions.to_csv(tables_dir / "phase_decisions_all_categories.csv", index=False)
    effects_structural.to_csv(tables_dir / "descriptive_effect_sizes_structural_scenarios.csv", index=False)
    construct_trajectories_summary.to_csv(tables_dir / "construct_trajectories_summary_h3_h4.csv", index=False)
    inferential_tests.to_csv(
        tables_dir / "inferential_tests_h3_h4.csv",
        index=False,
    )
    pairwise_posthoc.to_csv(
        tables_dir / "pairwise_posthoc_h3_h4.csv",
        index=False,
    )

    write_figures(
        figures_dir=figures_dir,
        h1_correlation_inference=h1_correlation_inference,
        h2_construct_summary=h2_construct_summary,
        h2_construct_sd_intervals=h2_construct_sd_intervals,
        scenario_decisions_by_daytype=scenario_decisions_by_daytype,
        h3_unplanned_by_context=h3_unplanned_by_context,
        h4_planned_by_scenario=h4_planned_by_scenario,
        h4_planned_by_context=h4_planned_by_context,
        construct_trajectories_summary=construct_trajectories_summary,
        inferential_tests=inferential_tests,
        pairwise_posthoc=pairwise_posthoc,
    )
    copy_source_figures(args.h1_dir, args.h2_dir, figures_dir)

    write_docs(
        docs_dir=docs_dir,
        data_audit=data_audit,
        h1_summary_metrics=h1_summary_metrics,
        h1_correlation_inference=h1_correlation_inference,
        h2_similarity=h2_similarity,
        h2_phase_counts=h2_phase_counts,
        h2_construct_sd_intervals=h2_construct_sd_intervals,
        h2_construct_mixed_effects=h2_construct_mixed_effects,
        h3_unplanned_by_scenario=h3_unplanned_by_scenario,
        h3_unplanned_by_context=h3_unplanned_by_context,
        h4_planned_by_scenario=h4_planned_by_scenario,
        h4_planned_by_context=h4_planned_by_context,
        effects_structural=effects_structural,
        inferential_tests=inferential_tests,
        pairwise_posthoc=pairwise_posthoc,
        construct_trajectories_summary=construct_trajectories_summary,
    )

    h3_supportive = h3_unplanned_by_scenario[
        h3_unplanned_by_scenario["scenario"] == "Supportive"
    ].iloc[0]
    h3_hindering = h3_unplanned_by_scenario[
        h3_unplanned_by_scenario["scenario"] == "Hindering"
    ].iloc[0]
    h4_supportive = h4_planned_by_scenario[
        h4_planned_by_scenario["scenario"] == "Supportive"
    ].iloc[0]
    h4_hindering = h4_planned_by_scenario[
        h4_planned_by_scenario["scenario"] == "Hindering"
    ].iloc[0]

    manifest = {
        "analysis_decisions": {
            "edge_case_rules": True,
            "report_all_decision_categories_for_h3_h4": True,
            "analysis_type": "descriptive_and_inferential",
            "inferential_tests": True,
            "confidence_interval_level": 0.95,
            "multiple_comparison_correction": "Bonferroni",
            "h2_inferential_model": "construct_value ~ C(construct) + (1 | agent)",
            "h2_variance_component_test": "boundary-corrected likelihood-ratio test",
        },
        "input_sources": {
            "h1_dir": str(args.h1_dir),
            "h2_dir": str(args.h2_dir),
            "supportive": str(args.supportive),
            "hindering": str(args.hindering),
        },
        "integrity": data_audit.to_dict("records"),
        "core_results": {
            "h3_extra_supportive_unplanned_pct": float(h3_supportive["extra_activity_pct"]),
            "h3_extra_hindering_unplanned_pct": float(h3_hindering["extra_activity_pct"]),
            "h4_adapt_supportive_planned_pct": float(h4_supportive["adapt_activity_pct"]),
            "h4_adapt_hindering_planned_pct": float(h4_hindering["adapt_activity_pct"]),
            "h4_skip_supportive_planned_pct": float(h4_supportive["skip_activity_pct"]),
            "h4_skip_hindering_planned_pct": float(h4_hindering["skip_activity_pct"]),
        },
        "output_files": {
            "tables": str(tables_dir),
            "figures": str(figures_dir),
            "docs": str(docs_dir),
        },
    }
    (args.output_dir / "analysis_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Final descriptive and inferential H1-H4 analysis completed.")
    print(f"Output directory: {args.output_dir}")
    if not h2_construct_mixed_effects.empty and "error" not in h2_construct_mixed_effects.columns:
        h2_model_row = h2_construct_mixed_effects.iloc[0]
        print(
            "H2 mixed-effects model: "
            f"agent variance={h2_model_row['random_intercept_variance']:.6f}, "
            f"agent SD={h2_model_row['random_intercept_sd']:.3f}, "
            f"LRT chi2(1)={h2_model_row['likelihood_ratio_chi2']:.2f}, "
            f"p={h2_model_row['p_value']:.3g}"
        )
    print(
        "H3 extra_activity on unplanned days: "
        f"Supportive={h3_supportive['extra_activity_pct']:.1f}%, "
        f"Hindering={h3_hindering['extra_activity_pct']:.1f}%"
    )
    print(
        "H4 adapt_activity on planned PA days: "
        f"Supportive={h4_supportive['adapt_activity_pct']:.1f}%, "
        f"Hindering={h4_hindering['adapt_activity_pct']:.1f}%"
    )


if __name__ == "__main__":
    main()
