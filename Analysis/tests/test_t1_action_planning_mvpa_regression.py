from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_DIR = ROOT / "Analysis"
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))

import t1_action_planning_mvpa_regression as regression


def test_prepared_t1_regression_reproduces_frozen_full_and_held_out_estimates() -> None:
    result = regression.run_analysis()

    full = result["full_sample"]
    assert full["n"] == 147
    assert full["unstandardized_B"] == pytest.approx(2.6449, abs=5e-4)
    assert full["standardized_beta"] == pytest.approx(0.1648, abs=5e-4)
    assert full["p_value"] == pytest.approx(0.0461, abs=5e-4)
    assert full["r_squared"] == pytest.approx(0.0272, abs=5e-4)

    held_out = result["held_out_medoids"]
    assert held_out["n"] == 143
    assert held_out["unstandardized_B"] == pytest.approx(2.6175879, abs=5e-6)
    assert held_out["standardized_beta"] == pytest.approx(0.1616428, abs=5e-6)
    assert held_out["intercept"] == pytest.approx(1.8487240, abs=5e-6)
    assert held_out["action_planning_mean"] == pytest.approx(0.3919580, abs=5e-6)
    assert held_out["action_planning_sd"] == pytest.approx(0.2751856, abs=5e-6)
    assert held_out["p_value"] == pytest.approx(0.0537675, abs=5e-6)
    assert held_out["r_squared"] == pytest.approx(0.0261284, abs=5e-6)


def test_medoid_ids_are_excluded_only_from_held_out_calibration() -> None:
    sample = regression.load_analysis_sample()
    medoid_ids = set(regression.MEDOID_IDS)

    assert medoid_ids <= set(sample["participant_id"])
    held_out = sample.loc[~sample["participant_id"].isin(regression.MEDOID_IDS)]
    assert medoid_ids.isdisjoint(set(held_out["participant_id"]))
    assert len(sample) - len(held_out) == 4
