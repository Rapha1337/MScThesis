"""Checks use invented values; no empirical input is distributed."""
import pandas as pd
import pytest
from Analysis.t1_action_planning_mvpa_regression import fit_action_planning_mvpa

def test_synthetic_linear_association():
    frame = pd.DataFrame({"action_planning": [0.1, 0.2, 0.4, 0.8], "pa_mvpa_hours_per_week": [1.2, 1.4, 1.8, 2.6]})
    result = fit_action_planning_mvpa(frame)
    assert result["n"] == 4
    assert result["unstandardized_B"] == pytest.approx(2.0)
    assert result["intercept"] == pytest.approx(1.0)

def test_requires_variation():
    with pytest.raises(ValueError, match="vary"):
        fit_action_planning_mvpa(pd.DataFrame({"action_planning": [0.5, 0.5, 0.5], "pa_mvpa_hours_per_week": [1, 2, 3]}))
