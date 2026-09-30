"""Reproduce the T1 action-planning -> MVPA calibration used by empirical PA v1.2.

The script uses the anonymized prepared T1 input table produced by
`t1_persona_cluster_analysis.R`. It reports the simple OLS requested for the
simulation calibration both in the full available T1 sample and after excluding
all four medoid personas used for the subsequent validation run.

Usage:
    python Analysis/t1_action_planning_mvpa_regression.py
    python Analysis/t1_action_planning_mvpa_regression.py --output path/to/result.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import pandas as pd
import statsmodels.api as sm
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    ROOT
    / "Analysis"
    / "results_t1_persona_clustering"
    / "03_prepared_t1_inputs.csv"
)
DEFAULT_OUTPUT = (
    ROOT
    / "Analysis"
    / "results_t1_persona_clustering"
    / "23_action_planning_mvpa_regression.json"
)
MEDOID_IDS = ("7067", "8153", "8237", "8303")


def load_analysis_sample(path: str | Path = DEFAULT_INPUT) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype={"participant_id": str})
    required = {"participant_id", "action_planning", "pa_mvpa_hours_per_week"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Prepared T1 table is missing columns: {sorted(missing)}")

    sample = frame.loc[
        :,
        ["participant_id", "action_planning", "pa_mvpa_hours_per_week"],
    ].copy()
    sample["participant_id"] = sample["participant_id"].astype(str).str.strip()
    sample["action_planning"] = pd.to_numeric(
        sample["action_planning"], errors="coerce"
    )
    sample["pa_mvpa_hours_per_week"] = pd.to_numeric(
        sample["pa_mvpa_hours_per_week"], errors="coerce"
    )
    sample = sample.dropna(
        subset=["action_planning", "pa_mvpa_hours_per_week"]
    ).reset_index(drop=True)
    return sample


def fit_action_planning_mvpa(frame: pd.DataFrame) -> dict[str, Any]:
    if len(frame) < 3:
        raise ValueError("At least three complete observations are required.")

    x = frame["action_planning"].astype(float)
    y = frame["pa_mvpa_hours_per_week"].astype(float)
    if x.std(ddof=1) <= 0 or y.std(ddof=1) <= 0:
        raise ValueError("Action planning and MVPA must both vary.")

    design = sm.add_constant(x, has_constant="add")
    model = sm.OLS(y, design).fit()
    ci = model.conf_int(alpha=0.05).loc["action_planning"]

    x_z = (x - x.mean()) / x.std(ddof=1)
    y_z = (y - y.mean()) / y.std(ddof=1)
    standardized = sm.OLS(
        y_z,
        sm.add_constant(x_z, has_constant="add"),
    ).fit()

    spearman = spearmanr(x, y)

    return {
        "n": int(len(frame)),
        "intercept": float(model.params["const"]),
        "unstandardized_B": float(model.params["action_planning"]),
        "standard_error_B": float(model.bse["action_planning"]),
        "ci95_B_lower": float(ci.iloc[0]),
        "ci95_B_upper": float(ci.iloc[1]),
        "standardized_beta": float(standardized.params["action_planning"]),
        "p_value": float(model.pvalues["action_planning"]),
        "r_squared": float(model.rsquared),
        "action_planning_mean": float(x.mean()),
        "action_planning_sd": float(x.std(ddof=1)),
        "mvpa_mean_hours_week": float(y.mean()),
        "mvpa_sd_hours_week": float(y.std(ddof=1)),
        "spearman_rho": float(spearman.statistic),
        "spearman_p_value": float(spearman.pvalue),
    }


def run_analysis(
    input_path: str | Path = DEFAULT_INPUT,
) -> dict[str, Any]:
    sample = load_analysis_sample(input_path)
    held_out = sample.loc[~sample["participant_id"].isin(MEDOID_IDS)].copy()

    return {
        "analysis": "simple OLS: T1 MVPA hours/week ~ normalized action planning",
        "source": str(Path(input_path)),
        "medoid_ids": list(MEDOID_IDS),
        "full_sample": fit_action_planning_mvpa(sample),
        "held_out_medoids": fit_action_planning_mvpa(held_out),
        "interpretation_note": (
            "The regression is descriptive/cross-sectional. The standardized beta "
            "is used in empirical PA v1.2 only as a small monotonic simulation "
            "weight, not as a probability, percentage-point effect, causal effect, "
            "or directly estimated daily transition coefficient."
        ),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    result = run_analysis(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
