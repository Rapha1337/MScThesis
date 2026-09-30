"""Empirical PA v1.2 correspondence analysis for the four T1 medoid personas.

This analysis removes observed medoid MVPA from schedule generation. The full
simulation contains no pre-scheduled PA blocks. LLM2 decides whether PA occurs
from the current psychological tendency and day context, and reports duration
and intensity. Moderate plus vigorous simulated minutes are compared directly
with observed T1 MVPA hours/week.

One continuous 90-day trajectory is generated per persona; 7-, 30-, and 90-day
results are nested prefixes.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[1]
SIMULATION = ROOT / "Simulation"
for path in (ROOT, SIMULATION):
    if str(path) not in sys.path:
        sys.path.append(str(path))

from empirical_pa_v1_2 import (  # noqa: E402
    ACTION_PLANNING_BETA,
    ACTION_PLANNING_CALIBRATION_DESCRIPTION,
    ACTION_PLANNING_CALIBRATION_N,
    ACTION_PLANNING_INTERCEPT,
    ACTION_PLANNING_MEAN,
    ACTION_PLANNING_P_VALUE,
    ACTION_PLANNING_R2,
    ACTION_PLANNING_SD,
    ACTION_PLANNING_UNSTANDARDIZED_B,
)
from run_full_pa_simulation import (  # noqa: E402
    LLM1_MAX_TOKENS,
    LLM2_MAX_TOKENS,
    MODEL_NAME,
    STATE_ASSESSMENT_MAX_TOKENS,
    TEMPERATURE,
    TOP_P,
    FullSimulationConfig,
    run_full_simulation,
)
from t1_medoid_pa_validation import (  # noqa: E402
    HORIZONS,
    N_PERSONAS,
    START_DATE,
    DEFAULT_PERSONA_FILE,
    inspect_event_free_seed,
    load_empirical_pa,
    select_event_free_seed,
)

DEFAULT_OUTPUT_DIR = ROOT / "Analysis/results_t1_medoid_pa_validation_v1_2"
VALID_INTENSITIES = {"none", "light", "moderate", "vigorous"}


def daily_rows_from_trace(
    trace: Mapping[str, Any],
    empirical: pd.DataFrame,
) -> pd.DataFrame:
    """Flatten v1.2 trace records and calculate simulated activity dose."""
    lookup = empirical.set_index("persona_id").to_dict("index")
    rows: list[dict[str, Any]] = []

    for record in trace.get("records", []):
        persona_id = str(record["persona_id"])
        if persona_id not in lookup:
            raise ValueError(f"Unexpected persona in trace: {persona_id}")

        if bool(record.get("was_physical_activity_planned_today")):
            raise ValueError(
                "Empirical PA v1.2 trace contains schedule-derived planned PA."
            )
        if record.get("planned_physical_activity") is not None:
            raise ValueError(
                "Empirical PA v1.2 trace contains a planned_physical_activity payload."
            )

        decision = dict(record["pa_decision"])
        decision_label = str(decision["decision_label"])
        duration_min = int(decision.get("duration_min", 0))
        intensity = str(decision.get("intensity", "none")).strip().lower()
        if intensity not in VALID_INTENSITIES:
            raise ValueError(f"Invalid v1.2 intensity {intensity!r}.")
        performed = bool(record["closed_loop_update"]["activity_done"])

        if decision_label == "skip_activity":
            if performed or duration_min != 0 or intensity != "none":
                raise ValueError("Invalid no-activity record in empirical PA v1.2.")
        elif decision_label == "extra_activity":
            if not performed or duration_min <= 0 or intensity == "none":
                raise ValueError("Invalid performed-activity record in empirical PA v1.2.")
        else:
            raise ValueError(
                f"Empirical PA v1.2 received unsupported decision {decision_label!r}."
            )

        mvpa_minutes = (
            float(duration_min) if intensity in {"moderate", "vigorous"} else 0.0
        )
        light_minutes = float(duration_min) if intensity == "light" else 0.0
        total_pa_minutes = float(duration_min) if performed else 0.0
        calibration = record.get("empirical_pa_v1_2") or {}
        metadata = lookup[persona_id]

        rows.append(
            {
                "persona_id": persona_id,
                "cluster": int(metadata["cluster"]),
                "participant_id": str(metadata["participant_id"]),
                "calendar_date": record["calendar_date"],
                "day_index": int(record["day_index"]),
                "week_index": int(record["week_index"]),
                "phase": record["phase"],
                "weekday": int(record["weekday"]),
                "decision_label": decision_label,
                "activity_performed": performed,
                "duration_min": duration_min,
                "intensity": intensity,
                "mvpa_minutes": mvpa_minutes,
                "light_pa_minutes": light_minutes,
                "total_pa_minutes": total_pa_minutes,
                "action_planning_value": calibration.get("action_planning_value"),
                "action_planning_modifier": calibration.get("modifier_beta_times_z"),
                "psychological_constructs_before": json.dumps(
                    record.get("psychological_constructs_before_update", {}),
                    sort_keys=True,
                ),
                "psychological_constructs_after": json.dumps(
                    record.get("psychological_constructs_after_update", {}),
                    sort_keys=True,
                ),
            }
        )

    daily = pd.DataFrame(rows)
    expected_rows = N_PERSONAS * max(HORIZONS)
    if len(daily) != expected_rows:
        raise ValueError(
            f"Expected {expected_rows} persona-days for the 90-day run; found {len(daily)}."
        )
    return daily


def summarize_horizons(
    daily: pd.DataFrame,
    empirical: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate nested-prefix v1.2 outcomes in comparable MVPA units."""
    output: list[dict[str, Any]] = []
    expected_personas = set(empirical["persona_id"])

    for horizon in HORIZONS:
        window = daily[daily["day_index"] < horizon]
        if set(window["persona_id"]) != expected_personas:
            raise ValueError(f"Horizon {horizon} does not contain every persona.")

        for persona_id, group in window.groupby("persona_id", sort=False):
            if len(group) != horizon or group["day_index"].nunique() != horizon:
                raise ValueError(
                    f"{persona_id} must have exactly {horizon} unique days."
                )
            meta = empirical.loc[empirical["persona_id"] == persona_id].iloc[0]
            active = group["activity_performed"].astype(bool)
            active_days = int(active.sum())
            mvpa_minutes = float(group["mvpa_minutes"].sum())
            light_minutes = float(group["light_pa_minutes"].sum())
            total_pa_minutes = float(group["total_pa_minutes"].sum())
            simulated_mvpa_h_week = mvpa_minutes / 60.0 / horizon * 7.0
            simulated_total_pa_h_week = total_pa_minutes / 60.0 / horizon * 7.0
            empirical_mvpa = float(meta["empirical_mvpa_hours_week"])
            error = simulated_mvpa_h_week - empirical_mvpa

            output.append(
                {
                    "horizon_days": int(horizon),
                    "cluster": int(meta["cluster"]),
                    "participant_id": str(meta["participant_id"]),
                    "persona_id": persona_id,
                    "occupation": meta["occupation"],
                    "empirical_mvpa_hours_week": empirical_mvpa,
                    "simulated_mvpa_hours_week": simulated_mvpa_h_week,
                    "mvpa_error_hours_week": error,
                    "absolute_mvpa_error_hours_week": abs(error),
                    "simulated_total_pa_hours_week": simulated_total_pa_h_week,
                    "active_days": active_days,
                    "active_days_per_week": active_days / horizon * 7.0,
                    "active_day_proportion": active_days / horizon,
                    "mean_duration_min_active_day": (
                        float(group.loc[active, "duration_min"].mean())
                        if active_days
                        else 0.0
                    ),
                    "light_minutes": light_minutes,
                    "moderate_minutes": float(
                        group.loc[group["intensity"].eq("moderate"), "duration_min"].sum()
                    ),
                    "vigorous_minutes": float(
                        group.loc[group["intensity"].eq("vigorous"), "duration_min"].sum()
                    ),
                    "normal_days": int(group["phase"].eq("normal").sum()),
                    "high_stress_days": int(group["phase"].eq("high_stress").sum()),
                    "holiday_days": int(group["phase"].eq("holiday").sum()),
                    "decision_count_activity": int(
                        group["decision_label"].eq("extra_activity").sum()
                    ),
                    "decision_count_no_activity": int(
                        group["decision_label"].eq("skip_activity").sum()
                    ),
                }
            )

    summary = pd.DataFrame(output)
    summary["empirical_rank"] = summary.groupby("horizon_days")[
        "empirical_mvpa_hours_week"
    ].rank(method="average", ascending=False)
    summary["simulated_rank"] = summary.groupby("horizon_days")[
        "simulated_mvpa_hours_week"
    ].rank(method="average", ascending=False)
    return summary


def _correlation(
    x: pd.Series,
    y: pd.Series,
    method: str,
) -> tuple[float, float]:
    if x.nunique(dropna=True) < 2 or y.nunique(dropna=True) < 2:
        return math.nan, math.nan
    result = spearmanr(x, y) if method == "spearman" else pearsonr(x, y)
    return float(result.statistic), float(result.pvalue)


def calculate_correlations(summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    metrics = (
        ("simulated_mvpa_hours_week", "spearman", "primary"),
        ("simulated_mvpa_hours_week", "pearson", "secondary_descriptive"),
        ("active_days_per_week", "spearman", "secondary_descriptive"),
        ("simulated_total_pa_hours_week", "spearman", "secondary_descriptive"),
    )
    for horizon, group in summary.groupby("horizon_days", sort=True):
        for metric, method, role in metrics:
            complete = group[["empirical_mvpa_hours_week", metric]].dropna()
            coefficient, pvalue = _correlation(
                complete.iloc[:, 0], complete.iloc[:, 1], method
            )
            rows.append(
                {
                    "horizon_days": int(horizon),
                    "n_personas": len(complete),
                    "empirical_variable": "empirical_mvpa_hours_week",
                    "simulated_variable": metric,
                    "method": method,
                    "analysis_stage": "post_decision_v1_2",
                    "role": role,
                    "coefficient": coefficient,
                    "exploratory_p_value": pvalue,
                }
            )
    return pd.DataFrame(rows)


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None or pd.isna(value):
        return "NA"
    if isinstance(value, (float, int)):
        return f"{float(value):.{digits}f}"
    return str(value)


def _markdown_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    for values in frame.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(_fmt(value) for value in values) + " |")
    return "\n".join(lines)


def build_report(
    seed: Mapping[str, Any],
    summary: pd.DataFrame,
    correlations: pd.DataFrame,
) -> str:
    primary = correlations[
        (correlations["role"] == "primary")
        & (correlations["method"] == "spearman")
    ].sort_values("horizon_days")

    lines = [
        "# Empirical T1 medoid PA correspondence analysis v1.2",
        "",
        "## Design",
        "",
        (
            f"One continuous 90-day simulation starts {START_DATE.isoformat()}. "
            "The 7-, 30-, and 90-day analyses are nested prefixes."
        ),
        "",
        (
            f"Base seed {seed['selected_base_seed']} was selected without examining "
            "any PA outcome or correlation. The first seven dates must remain in each "
            "persona's modal annual phase and contain no acute schedule-altering event."
        ),
        "",
        (
            "Observed medoid T1 MVPA is validation-only in v1.2. It is retained for "
            "the final comparison but is not passed into schedule generation, LLM1, "
            "or LLM2. Therefore there is no input-informed scheduler PA baseline."
        ),
        "",
        "## Action-planning calibration",
        "",
        ACTION_PLANNING_CALIBRATION_DESCRIPTION,
        "",
        (
            f"Held-out calibration: n={ACTION_PLANNING_CALIBRATION_N}, "
            f"standardized beta={ACTION_PLANNING_BETA:.3f}, "
            f"B={ACTION_PLANNING_UNSTANDARDIZED_B:.3f} h/week per 0-1 AP unit, "
            f"p={ACTION_PLANNING_P_VALUE:.3f}, R2={ACTION_PLANNING_R2:.3f}. "
            f"Action-planning mean={ACTION_PLANNING_MEAN:.3f}, "
            f"SD={ACTION_PLANNING_SD:.3f}."
        ),
        "",
        (
            "The standardized beta is used only as a small monotonic weighting of "
            "unplanned PA propensity. It is not interpreted as a probability, a "
            "percentage-point effect, or a causal coefficient. Individual action "
            "planning is neutralized before LLM1 and reintroduced once through this "
            "calibration to avoid double counting."
        ),
        "",
        "## Primary outcome",
        "",
        (
            "LLM2 reports duration and intensity for each performed activity. "
            "Simulated MVPA equals moderate plus vigorous minutes, normalized to "
            "hours/week. Light activity does not count toward simulated MVPA."
        ),
        "",
        "| horizon | Spearman empirical vs simulated MVPA | Pearson empirical vs simulated MVPA |",
        "|---:|---:|---:|",
    ]

    for horizon in HORIZONS:
        subset = correlations[correlations["horizon_days"].eq(horizon)]
        spear = subset[
            subset["simulated_variable"].eq("simulated_mvpa_hours_week")
            & subset["method"].eq("spearman")
        ].iloc[0]["coefficient"]
        pear = subset[
            subset["simulated_variable"].eq("simulated_mvpa_hours_week")
            & subset["method"].eq("pearson")
        ].iloc[0]["coefficient"]
        lines.append(f"| {horizon} | {_fmt(spear)} | {_fmt(pear)} |")

    lines += [
        "",
        (
            "All correlations are descriptive/exploratory with n=4 and should not be "
            "treated as inferential validation evidence."
        ),
        "",
        "## Persona-level correspondence",
        "",
    ]
    display = summary[
        [
            "horizon_days",
            "cluster",
            "participant_id",
            "empirical_mvpa_hours_week",
            "simulated_mvpa_hours_week",
            "mvpa_error_hours_week",
            "active_days_per_week",
            "mean_duration_min_active_day",
            "normal_days",
            "high_stress_days",
            "holiday_days",
        ]
    ]
    lines.append(_markdown_table(display))

    lines += [
        "",
        "## Limitations",
        "",
        (
            "The four medoids are a deliberately small descriptive sample. T1 MVPA is "
            "self-reported baseline behavior, whereas the simulation evolves over time. "
            "LLM-generated duration and intensity are structured simulation outputs, not "
            "objective activity measurements. The action-planning calibration is a model "
            "mapping choice informed by the T1 association rather than a directly "
            "estimated daily transition probability. The cross-sectional T1 coefficient "
            "is applied to evolving simulated action-planning states, which is an explicit "
            "longitudinal model assumption."
        ),
        "",
    ]
    return "\n".join(lines)


def write_analysis_outputs(
    output_dir: Path,
    seed: Mapping[str, Any],
    trace: Mapping[str, Any],
    persona_file: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    empirical = load_empirical_pa(persona_file)
    daily = daily_rows_from_trace(trace, empirical)
    summary = summarize_horizons(daily, empirical)
    correlations = calculate_correlations(summary)

    (output_dir / "01_seed_selection.json").write_text(
        json.dumps(seed, indent=2), encoding="utf-8"
    )
    empirical.to_csv(output_dir / "02_persona_empirical_pa.csv", index=False)
    daily.to_csv(output_dir / "03_daily_simulated_pa_v1_2.csv", index=False)
    summary.to_csv(output_dir / "04_horizon_persona_summary_v1_2.csv", index=False)
    correlations.to_csv(output_dir / "05_horizon_correlations_v1_2.csv", index=False)
    (output_dir / "06_validation_report_v1_2.md").write_text(
        build_report(seed, summary, correlations),
        encoding="utf-8",
    )
    calibration = {
        "description": ACTION_PLANNING_CALIBRATION_DESCRIPTION,
        "n": ACTION_PLANNING_CALIBRATION_N,
        "standardized_beta": ACTION_PLANNING_BETA,
        "unstandardized_B": ACTION_PLANNING_UNSTANDARDIZED_B,
        "intercept": ACTION_PLANNING_INTERCEPT,
        "action_planning_mean": ACTION_PLANNING_MEAN,
        "action_planning_sd": ACTION_PLANNING_SD,
        "p_value": ACTION_PLANNING_P_VALUE,
        "r_squared": ACTION_PLANNING_R2,
        "medoid_personas_excluded_from_calibration": ["7067", "8153", "8237", "8303"],
    }
    (output_dir / "07_action_planning_calibration.json").write_text(
        json.dumps(calibration, indent=2),
        encoding="utf-8",
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--persona-input-file", type=Path, default=DEFAULT_PERSONA_FILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--base-seed", type=int)
    parser.add_argument("--max-seed", type=int, default=100_000)
    parser.add_argument("--seed-only", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--disable-resource-tracking", action="store_true")
    parser.add_argument("--disable-codecarbon", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.base_seed is not None:
        seed = inspect_event_free_seed(
            args.base_seed,
            args.persona_input_file,
            include_pa_schedule=False,
        )
        seed["selection_mode"] = "explicit_override"
    else:
        seed = select_event_free_seed(
            args.persona_input_file,
            max_seed=args.max_seed,
            include_pa_schedule=False,
        )
        seed["selection_mode"] = "lowest_valid_ascending_search"

    seed["pa_schedule_in_seed_check"] = False
    if not seed["valid"]:
        raise ValueError(
            "The requested seed does not satisfy the representative event-free criterion."
        )

    (args.output_dir / "01_seed_selection.json").write_text(
        json.dumps(seed, indent=2), encoding="utf-8"
    )
    if args.seed_only:
        print(json.dumps(seed, indent=2))
        return

    simulation_dir = args.output_dir / "simulation"
    trace_path = simulation_dir / "full_simulation_trace.json"

    if args.analyze_only:
        if not trace_path.is_file():
            raise FileNotFoundError(f"Existing v1.2 trace not found: {trace_path}")
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
    else:
        config = FullSimulationConfig(
            n_personas=N_PERSONAS,
            n_days=90,
            start_date=START_DATE,
            base_seed=int(seed["selected_base_seed"]),
            output_dir=simulation_dir,
            model=args.model,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            llm_seed=None,
            llm1_max_tokens=LLM1_MAX_TOKENS,
            llm2_max_tokens=LLM2_MAX_TOKENS,
            state_assessment_max_tokens=STATE_ASSESSMENT_MAX_TOKENS,
            state_assessment_json_mode=False,
            dry_run=args.dry_run,
            include_full_hourly_context=False,
            enable_resource_tracking=not args.disable_resource_tracking,
            enable_codecarbon=not args.disable_codecarbon,
            resume=args.resume,
            persona_input_file=args.persona_input_file,
            empirical_pa_v1_2=True,
        )
        trace = run_full_simulation(config)

    write_analysis_outputs(
        args.output_dir,
        seed,
        trace,
        args.persona_input_file,
    )
    run_config = {
        "study": "T1 empirical medoid PA validation v1.2",
        "model_version": "empirical_pa_v1_2",
        "start_date": START_DATE.isoformat(),
        "n_days": 90,
        "nested_horizons_days": list(HORIZONS),
        "n_personas": N_PERSONAS,
        "base_seed": seed["selected_base_seed"],
        "persona_seeds": seed["derived_persona_seeds"],
        "persona_input_file": str(args.persona_input_file),
        "simulation_output_dir": str(simulation_dir),
        "dry_run": args.dry_run,
        "resume": args.resume,
        "observed_t1_mvpa_role": "validation_only",
        "pa_schedule_generation": "disabled",
        "primary_empirical_metric": "pa_mvpa_hours_per_week",
        "primary_simulated_metric": "simulated_mvpa_hours_week",
        "action_planning_standardized_beta": ACTION_PLANNING_BETA,
        "action_planning_calibration_n": ACTION_PLANNING_CALIBRATION_N,
    }
    (args.output_dir / "run_config.json").write_text(
        json.dumps(run_config, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(run_config, indent=2))


if __name__ == "__main__":
    main()
