#!/usr/bin/env python
"""Final descriptive H1-H4 analysis for the MSc thesis ABM simulation.

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

The analysis is descriptive only. No inferential tests are performed.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


DECISION_CATEGORIES = [
    "do_planned_activity",
    "adapt_activity",
    "skip_activity",
    "extra_activity",
]

CONTEXT_ORDER = ["supportive", "mixed_neutral", "hindering"]

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


def write_figures(
    figures_dir: Path,
    h1_summary_metrics: pd.DataFrame | None,
    h2_construct_summary: pd.DataFrame | None,
    scenario_decisions_by_daytype: pd.DataFrame,
    h3_unplanned_by_context: pd.DataFrame,
    h4_planned_by_scenario: pd.DataFrame,
    h4_planned_by_context: pd.DataFrame,
    construct_trajectories_summary: pd.DataFrame,
) -> None:
    if h1_summary_metrics is not None:
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
            if variable in set(h1_summary_metrics["variable"])
        ]
        if available and "pearson_r" in h1_summary_metrics.columns:
            plot_df = (
                h1_summary_metrics[h1_summary_metrics["variable"].isin(available)]
                .set_index("variable")
                .loc[available]
                .reset_index()
            )
            ax = plot_df.plot(
                x="variable",
                y="pearson_r",
                kind="bar",
                legend=False,
                figsize=(11, 6),
            )
            ax.set_title("H1: monthly simulation-reference correlations")
            ax.set_xlabel("Weather variable")
            ax.set_ylabel("Pearson r")
            ax.tick_params(axis="x", rotation=30)
            fig = ax.get_figure()
            fig.tight_layout()
            fig.savefig(figures_dir / "figure_h1_weather_correlations.png", dpi=180)
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
                "action_planning": "Action planning",
                "automaticity": "Automaticity",
                "attitude_toward_the_behavior": "Attitude toward the behavior",
                "pa_specific_self_control": "PA-specific self-control",
                "intention": "Intention",
                "perceived_behavioral_control": "Perceived behavioral control",
                "subjective_norm": "Subjective norm",
                "motivational_competence": "Motivational competence",
                "intrinsic_motivation": "Intrinsic motivation",
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

            ax = plot_df.plot(
                x="construct_label",
                y=sd_col,
                kind="bar",
                legend=False,
                figsize=(11, 6),
            )
            ax.set_title("")
            ax.set_xlabel("Construct")
            ax.set_ylabel("Population SD")
            ax.tick_params(axis="x", rotation=30)
            fig = ax.get_figure()
            fig.tight_layout()
            fig.savefig(
                figures_dir / "figure_h2_construct_heterogeneity.png",
                dpi=180,
                bbox_inches="tight",
            )
            plt.close(fig)

    plot_table = scenario_decisions_by_daytype.copy()
    plot_table["day_type"] = np.where(plot_table["planned"], "planned days", "unplanned days")
    plot_table["scenario_day_type"] = plot_table["scenario"] + " – " + plot_table["day_type"]
    decision_counts = plot_table.set_index("scenario_day_type")[
        [f"{category}_n" for category in DECISION_CATEGORIES]
    ]
    decision_counts.columns = DECISION_CATEGORIES
    ax = decision_counts.plot(kind="bar", figsize=(12, 6))
    ax.set_title("H3/H4: decision categories by scenario and day type")
    ax.set_xlabel("Scenario and day type")
    ax.set_ylabel("Number of days")
    ax.tick_params(axis="x", rotation=25)
    fig = ax.get_figure()
    fig.tight_layout()
    fig.savefig(figures_dir / "figure_decision_categories_by_scenario_daytype.png", dpi=180)
    plt.close(fig)

    h3_plot = h3_unplanned_by_context.set_index("context_class").reindex(CONTEXT_ORDER)
    available_cols = [
        column
        for column in ["skip_activity_pct", "extra_activity_pct"]
        if column in h3_plot.columns
    ]
    ax = h3_plot[available_cols].plot(kind="bar", figsize=(10, 6))
    ax.set_title("H3: decisions on unplanned days by realized context")
    ax.set_xlabel("Resolved daily context class")
    ax.set_ylabel("Percentage of unplanned days")
    ax.tick_params(axis="x", rotation=20)
    fig = ax.get_figure()
    fig.tight_layout()
    fig.savefig(figures_dir / "figure_h3_unplanned_decisions_by_context.png", dpi=180)
    plt.close(fig)

    h4_plot = h4_planned_by_scenario.set_index("scenario")[
        [f"{category}_pct" for category in DECISION_CATEGORIES]
    ]
    h4_plot.columns = DECISION_CATEGORIES
    ax = h4_plot.plot(kind="bar", figsize=(10, 6))
    ax.set_title("H4: planned-day decision categories by structural scenario")
    ax.set_xlabel("Scenario")
    ax.set_ylabel("Percentage of planned days")
    ax.tick_params(axis="x", rotation=0)
    fig = ax.get_figure()
    fig.tight_layout()
    fig.savefig(figures_dir / "figure_h4_planned_decisions_by_scenario.png", dpi=180)
    plt.close(fig)

    h4_context_plot = h4_planned_by_context.set_index("context_class").reindex(CONTEXT_ORDER)
    ax = h4_context_plot[
        [f"{category}_pct" for category in DECISION_CATEGORIES]
    ].plot(kind="bar", figsize=(11, 6))
    ax.set_title("H4: decision categories on planned days by realized context")
    ax.set_xlabel("Resolved daily context class")
    ax.set_ylabel("Percentage of planned days")
    ax.tick_params(axis="x", rotation=20)
    fig = ax.get_figure()
    fig.tight_layout()
    fig.savefig(figures_dir / "figure_h4_planned_decisions_by_context.png", dpi=180)
    plt.close(fig)

    construct_end = construct_trajectories_summary.pivot(
        index="construct",
        columns="scenario",
        values="end",
    )
    ax = construct_end.plot(kind="bar", figsize=(12, 6))
    ax.set_title("Final psychological construct values by scenario")
    ax.set_xlabel("Construct")
    ax.set_ylabel("Normalized final value")
    ax.set_ylim(0, 1)
    ax.tick_params(axis="x", rotation=30)
    fig = ax.get_figure()
    fig.tight_layout()
    fig.savefig(figures_dir / "figure_construct_final_values_by_scenario.png", dpi=180)
    plt.close(fig)


def write_docs(
    docs_dir: Path,
    data_audit: pd.DataFrame,
    h1_summary_metrics: pd.DataFrame | None,
    h2_similarity: pd.DataFrame | None,
    h2_phase_counts: pd.DataFrame | None,
    h3_unplanned_by_scenario: pd.DataFrame,
    h3_unplanned_by_context: pd.DataFrame,
    h4_planned_by_scenario: pd.DataFrame,
    h4_planned_by_context: pd.DataFrame,
    effects_structural: pd.DataFrame,
    construct_trajectories_summary: pd.DataFrame,
) -> None:
    analysis_plan = """# Final analysis plan for H1-H4

## Fixed analysis decisions

1. Edge-case rules are applied:
   - Unplanned days without a downtime window are classified as `hindering`.
   - If the location immediately before planned PA is unknown, the last preceding hour with known accessibility is used.

2. H3 and H4 report all decision categories:
   - H3: unplanned days; all categories are reported, with `skip_activity` and `extra_activity` as the valid categories.
   - H4: planned PA days; `do_planned_activity`, `adapt_activity`, `skip_activity`, and `extra_activity` are reported.

3. The analysis is descriptive:
   - No p-values or confirmatory inferential tests are used.
   - Results are interpreted through frequencies, proportions, descriptive effect sizes, and visual patterns.
   - This is appropriate because the simulated annual trajectories are not independent empirical observations.

## H1

Weather validation is summarized using correlations, MAE, RMSE, bias, and interval coverage from the final H1 output tables.

## H2

Agent heterogeneity is summarized using schedule similarity, phase distributions, and heterogeneity in initial psychological constructs from the final H2 output tables.

## H3

Unit of analysis: unplanned days.

Main descriptive comparisons:
- Structural scenario: Supportive versus Hindering
- Realized daily context: supportive, mixed/neutral, hindering
- Scenario × realized context

## H4

Unit of analysis: planned PA days.

Decision categories:
- do planned activity
- adapt activity
- skip activity
- extra activity

Main descriptive comparisons:
- Structural scenario: Supportive versus Hindering
- Realized daily context
- Simulation phase
"""

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

    h1_text = "H1 summary table not available."
    if h1_summary_metrics is not None:
        selected_vars = [
            "temperature_mean_c",
            "temperature_daily_max_mean_c",
            "temperature_daily_min_mean_c",
            "precipitation_total_mm",
            "sunshine_hours",
            "wind_m_s",
            "snow_cover_days",
        ]
        available = [
            variable
            for variable in selected_vars
            if variable in set(h1_summary_metrics["variable"])
        ]
        h1_cols = [
            column
            for column in ["variable", "pearson_r", "mae", "rmse", "mean_bias_sim_minus_ref"]
            if column in h1_summary_metrics.columns
        ]
        h1_text = table_to_markdown(
            h1_summary_metrics[h1_summary_metrics["variable"].isin(available)][h1_cols],
            float_fmt="{:.3f}",
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

    results_summary = f"""# Final descriptive H1-H4 results summary

## Data audit

{table_to_markdown(data_audit, float_fmt="{:.1f}")}

## H1: Weather plausibility

{h1_text}

Interpretation: H1 is evaluated descriptively by checking whether generated weather patterns reproduce the expected seasonal structure.

## H2: Agent heterogeneity

Schedule similarity:

{h2_similarity_text}

Phase distribution:

{h2_phase_text}

Interpretation: H2 is evaluated descriptively by checking whether the ABM produces heterogeneous, but still plausible, agent routines and psychological starting states.

## H3: Decision categories on unplanned days

### Structural scenario comparison

{table_to_markdown(h3_unplanned_by_scenario[["scenario", "n_days", "do_planned_activity_n", "do_planned_activity_pct", "adapt_activity_n", "adapt_activity_pct", "skip_activity_n", "skip_activity_pct", "extra_activity_n", "extra_activity_pct"]], float_fmt="{:.1f}")}

Extra activity was more frequent in the Supportive Scenario than in the Hindering Scenario:
- Supportive: {h3_supportive["extra_activity_n"]:.0f}/{h3_supportive["n_days"]:.0f} = {h3_supportive["extra_activity_pct"]:.1f}%
- Hindering: {h3_hindering["extra_activity_n"]:.0f}/{h3_hindering["n_days"]:.0f} = {h3_hindering["extra_activity_pct"]:.1f}%

### Realized daily context

{table_to_markdown(h3_unplanned_by_context[["context_class", "n_days", "skip_activity_n", "skip_activity_pct", "extra_activity_n", "extra_activity_pct"]].sort_values("context_class"), float_fmt="{:.1f}")}

## H4: Decision categories on planned PA days

### Structural scenario comparison

{table_to_markdown(h4_planned_by_scenario[["scenario", "n_days", "do_planned_activity_n", "do_planned_activity_pct", "adapt_activity_n", "adapt_activity_pct", "skip_activity_n", "skip_activity_pct", "extra_activity_n", "extra_activity_pct"]], float_fmt="{:.1f}")}

Adaptations were more frequent in the Hindering Scenario:
- Supportive: {h4_supportive["adapt_activity_n"]:.0f}/{h4_supportive["n_days"]:.0f} = {h4_supportive["adapt_activity_pct"]:.1f}%
- Hindering: {h4_hindering["adapt_activity_n"]:.0f}/{h4_hindering["n_days"]:.0f} = {h4_hindering["adapt_activity_pct"]:.1f}%

`skip_activity` did not occur on planned PA days in either scenario.

### Realized daily context

{table_to_markdown(h4_planned_by_context[["context_class", "n_days", "do_planned_activity_n", "do_planned_activity_pct", "adapt_activity_n", "adapt_activity_pct", "skip_activity_n", "skip_activity_pct", "extra_activity_n", "extra_activity_pct"]].sort_values("context_class"), float_fmt="{:.1f}")}

## Descriptive structural effect sizes

{table_to_markdown(effects_structural, float_fmt="{:.2f}")}

## Psychological construct trajectories in H3/H4 scenarios

{table_to_markdown(construct_trajectories_summary[["scenario", "construct", "start", "end", "change"]].sort_values(["construct", "scenario"]), float_fmt="{:.3f}")}

## Overall descriptive conclusion

- H1: descriptively supported.
- H2: descriptively supported.
- H3: descriptively supported; extra activity was more common under supportive structural and realized contexts.
- H4: partially supported; hindering conditions increased `adapt_activity`, but complete skipping of planned PA did not occur.
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

    h2_similarity = load_optional_table(args.h2_dir, "tables/schedule_similarity_overall_summary.csv")
    h2_phase_counts = load_optional_table(args.h2_dir, "tables/phase_week_count_summary.csv")
    h2_construct_summary = load_optional_table(args.h2_dir, "tables/construct_heterogeneity_summary.csv")
    h2_phase_activity = load_optional_table(args.h2_dir, "tables/phase_activity_summary.csv")

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

    if h2_similarity is not None:
        h2_similarity.to_csv(tables_dir / "h2_schedule_similarity_overall.csv", index=False)
    if h2_phase_counts is not None:
        h2_phase_counts.to_csv(tables_dir / "h2_phase_week_counts.csv", index=False)
    if h2_construct_summary is not None:
        h2_construct_summary.to_csv(tables_dir / "h2_construct_heterogeneity_summary.csv", index=False)
    if h2_phase_activity is not None:
        h2_phase_activity.to_csv(tables_dir / "h2_phase_activity_summary.csv", index=False)

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

    write_figures(
        figures_dir=figures_dir,
        h1_summary_metrics=h1_summary_metrics,
        h2_construct_summary=h2_construct_summary,
        scenario_decisions_by_daytype=scenario_decisions_by_daytype,
        h3_unplanned_by_context=h3_unplanned_by_context,
        h4_planned_by_scenario=h4_planned_by_scenario,
        h4_planned_by_context=h4_planned_by_context,
        construct_trajectories_summary=construct_trajectories_summary,
    )
    copy_source_figures(args.h1_dir, args.h2_dir, figures_dir)

    write_docs(
        docs_dir=docs_dir,
        data_audit=data_audit,
        h1_summary_metrics=h1_summary_metrics,
        h2_similarity=h2_similarity,
        h2_phase_counts=h2_phase_counts,
        h3_unplanned_by_scenario=h3_unplanned_by_scenario,
        h3_unplanned_by_context=h3_unplanned_by_context,
        h4_planned_by_scenario=h4_planned_by_scenario,
        h4_planned_by_context=h4_planned_by_context,
        effects_structural=effects_structural,
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
            "analysis_type": "descriptive",
            "inferential_tests": False,
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

    print("Final descriptive H1-H4 analysis completed.")
    print(f"Output directory: {args.output_dir}")
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
