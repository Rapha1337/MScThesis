from __future__ import annotations

import math
import csv
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


SYNTHETIC_PERSONA_COLUMNS = (
    "cluster",
    "participant_id",
    "complete_required_simulation_inputs",
    "normal_weeks_raw",
    "stress_weeks",
    "holiday_weeks",
    "occupational_status",
    "occupational_status_other",
    "workload_hours_per_week",
    "pa_mvpa_hours_per_week",
    "pa_total_hours_per_week",
    "care_work_hours_per_week",
    "social_hours_per_week",
    "workplace_distance_km",
    "indoor_activity_distance_km",
    "outdoor_activity_distance_km",
    "automaticity",
    "pa_specific_self_control",
    "action_planning",
    "intention",
    "perceived_behavioral_control",
    "attitude",
    "subjective_norm",
    "intrinsic_motivation",
    "motivational_competence",
    "wake_time_minutes",
    "work_start_time_minutes",
    "work_end_time_minutes",
    "break_duration_minutes",
    "leisure_duration_minutes",
    "bed_time_minutes",
)


def write_synthetic_persona_csv(tmp_path: Path, rows: list[dict[str, object]]) -> Path:
    path = tmp_path / "synthetic_medoid_personas.csv"
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=SYNTHETIC_PERSONA_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def synthetic_persona_row(
    cluster: int = 1,
    *,
    participant_id: str = "synthetic_p1",
    mvpa_hours: float = 2.5,
    total_pa_hours: float = 4.0,
    action_planning: float = 0.4,
) -> dict[str, object]:
    return {
        "cluster": cluster,
        "participant_id": participant_id,
        "complete_required_simulation_inputs": "true",
        "normal_weeks_raw": 32,
        "stress_weeks": 12,
        "holiday_weeks": 8,
        "occupational_status": "Studium",
        "occupational_status_other": "",
        "workload_hours_per_week": 28.0,
        "pa_mvpa_hours_per_week": mvpa_hours,
        "pa_total_hours_per_week": total_pa_hours,
        "care_work_hours_per_week": 2.0,
        "social_hours_per_week": 8.0,
        "workplace_distance_km": 3.0,
        "indoor_activity_distance_km": 1.5,
        "outdoor_activity_distance_km": 0.8,
        "automaticity": 0.45,
        "pa_specific_self_control": 0.55,
        "action_planning": action_planning,
        "intention": 0.60,
        "perceived_behavioral_control": 0.50,
        "attitude": 0.70,
        "subjective_norm": 0.35,
        "intrinsic_motivation": 0.65,
        "motivational_competence": 0.52,
        "wake_time_minutes": 420,
        "work_start_time_minutes": 540,
        "work_end_time_minutes": 1020,
        "break_duration_minutes": 45,
        "leisure_duration_minutes": 240,
        "bed_time_minutes": 1380,
    }


def test_held_out_action_planning_calibration_is_frozen() -> None:
    assert ACTION_PLANNING_CALIBRATION_N == 148
    assert ACTION_PLANNING_BETA == pytest.approx(0.10728499572967862)
    assert ACTION_PLANNING_UNSTANDARDIZED_B == pytest.approx(1.9774300552445538)
    assert ACTION_PLANNING_INTERCEPT == pytest.approx(2.27298841765128)
    assert ACTION_PLANNING_MEAN == pytest.approx(0.3898648648648649)
    assert ACTION_PLANNING_SD == pytest.approx(0.2737966534941716)
    assert ACTION_PLANNING_P_VALUE == pytest.approx(0.19433507322993454)
    assert ACTION_PLANNING_R2 == pytest.approx(0.011510070308717202)


def test_action_planning_modifier_is_centered_signed_and_monotonic() -> None:
    # Freely chosen synthetic offsets, unrelated to any participant profile.
    synthetic_offsets = (-0.18, -0.07, 0.0, 0.09, 0.21)
    modifiers = [
        action_planning_modifier(ACTION_PLANNING_MEAN + offset)
        for offset in synthetic_offsets
    ]

    assert ACTION_PLANNING_BETA > 0
    assert modifiers[2] == pytest.approx(0.0, abs=1e-12)
    assert all(modifier < 0 for modifier in modifiers[:2])
    assert all(modifier > 0 for modifier in modifiers[3:])
    assert all(lower < upper for lower, upper in zip(modifiers, modifiers[1:]))


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


def test_empirical_v1_2_wrapper_removes_pa_budget_but_retains_observed_mvpa_metadata(
    tmp_path: Path,
) -> None:
    persona_file = write_synthetic_persona_csv(
        tmp_path,
        [synthetic_persona_row(mvpa_hours=2.5, total_pa_hours=4.0)],
    )
    profile = load_empirical_personas(persona_file)[0]
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
