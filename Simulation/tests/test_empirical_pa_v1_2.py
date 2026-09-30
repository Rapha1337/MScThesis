from __future__ import annotations

import math
from pathlib import Path
import sys

import pytest

SIMULATION_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = SIMULATION_DIR.parent
if str(SIMULATION_DIR) not in sys.path:
    sys.path.append(str(SIMULATION_DIR))

from empirical_pa_v1_2 import (
    ACTION_PLANNING_BETA,
    ACTION_PLANNING_CALIBRATION_N,
    ACTION_PLANNING_INTERCEPT,
    ACTION_PLANNING_MEAN,
    ACTION_PLANNING_P_VALUE,
    ACTION_PLANNING_R2,
    ACTION_PLANNING_SD,
    ACTION_PLANNING_UNSTANDARDIZED_B,
    action_planning_modifier,
    calibrate_unplanned_behavior_policy,
    neutralize_action_planning_for_llm1,
)
from empirical_personas import load_empirical_personas
from schedule_model_student import YearPhase


MEDOID_FILE = (
    ROOT_DIR
    / "Analysis"
    / "results_t1_persona_clustering"
    / "11_primary_medoid_personas.csv"
)


def test_held_out_action_planning_calibration_is_frozen() -> None:
    assert ACTION_PLANNING_CALIBRATION_N == 143
    assert ACTION_PLANNING_BETA == pytest.approx(0.16164280788232943)
    assert ACTION_PLANNING_UNSTANDARDIZED_B == pytest.approx(2.617587892858344)
    assert ACTION_PLANNING_INTERCEPT == pytest.approx(1.848723999570791)
    assert ACTION_PLANNING_MEAN == pytest.approx(0.39195804195804196)
    assert ACTION_PLANNING_SD == pytest.approx(0.27518561915130735)
    assert ACTION_PLANNING_P_VALUE == pytest.approx(0.05376746550106626)
    assert ACTION_PLANNING_R2 == pytest.approx(0.026128397340083626)


def test_medoid_action_planning_modifiers_are_small_and_ordered() -> None:
    modifiers = {
        "C1": action_planning_modifier(0.30),
        "C2": action_planning_modifier(0.40),
        "C3": action_planning_modifier(0.65),
        "C4": action_planning_modifier(0.00),
    }

    assert modifiers["C3"] > modifiers["C2"] > modifiers["C1"] > modifiers["C4"]
    assert modifiers["C1"] == pytest.approx(-0.0540157446)
    assert modifiers["C2"] == pytest.approx(0.0047238104)
    assert modifiers["C3"] == pytest.approx(0.1515726977)
    assert modifiers["C4"] == pytest.approx(-0.2302344093)


def test_llm1_action_planning_is_neutralized_without_mutating_original() -> None:
    context = {
        "psychological_state": {
            "values_normalized": {
                "automaticity": 0.2,
                "action_planning": 0.9,
            }
        }
    }

    transformed = neutralize_action_planning_for_llm1(context)

    assert context["psychological_state"]["values_normalized"]["action_planning"] == 0.9
    assert transformed["psychological_state"]["values_normalized"]["action_planning"] == pytest.approx(
        ACTION_PLANNING_MEAN
    )
    assert transformed["psychological_state"]["values_normalized"]["automaticity"] == 0.2


def test_empirical_calibration_only_tilts_unplanned_activity_propensity() -> None:
    base = {
        "do_planned_activity": 0.25,
        "adapt_activity": 0.25,
        "skip_activity": 0.40,
        "extra_activity": 0.10,
    }

    low, _ = calibrate_unplanned_behavior_policy(base, action_planning=0.0)
    neutral, _ = calibrate_unplanned_behavior_policy(base, action_planning=ACTION_PLANNING_MEAN)
    high, _ = calibrate_unplanned_behavior_policy(base, action_planning=0.65)

    for policy in (low, neutral, high):
        assert math.isclose(sum(policy.values()), 1.0, abs_tol=1e-12)
        assert policy["do_planned_activity"] == 0.0
        assert policy["adapt_activity"] == 0.0

    assert low["extra_activity"] < neutral["extra_activity"] < high["extra_activity"]


def test_empirical_v1_2_wrapper_removes_pa_budget_but_retains_observed_mvpa_metadata() -> None:
    profile = load_empirical_personas(MEDOID_FILE)[0]
    wrapper = profile.to_wrapper(include_pa_schedule=False)
    week = wrapper.generate_week(YearPhase.NORMAL, seed=1)

    assert wrapper.fitness_hours_week == 0.0
    assert not any(budget.activity_type.value == "physical_activity" for budget in week.budgets)
    assert profile.metadata()["reported_mvpa_hours_per_week"] == pytest.approx(
        profile.fitness_hours_week
    )


def test_v1_2_behavior_prompt_neutralizes_action_planning_and_disables_plan_labels() -> None:
    prompt = (
        SIMULATION_DIR / "BehaviorProbability_EmpiricalV1_2_Prompt.md"
    ).read_text(encoding="utf-8")

    assert "action_planning hier deshalb als neutral" in prompt
    assert "do_planned_activity = 0.0" in prompt
    assert "adapt_activity = 0.0" in prompt
    assert "skip_activity und extra_activity müssen zusammen 1.0 ergeben" in prompt
