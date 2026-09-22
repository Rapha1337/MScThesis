from __future__ import annotations

from pathlib import Path
import sys


SIMULATION_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = SIMULATION_DIR.parent
if str(SIMULATION_DIR) not in sys.path:
    sys.path.append(str(SIMULATION_DIR))

from empirical_personas import load_empirical_personas
from psychological_state import build_psychological_state_from_values
from schedule_model_student import YearPhase
from year_structure import YearStructureGenerator


MEDOID_FILE = (
    ROOT_DIR
    / "Analysis"
    / "results_t1_persona_clustering"
    / "11_primary_medoid_personas.csv"
)


def test_primary_medoid_file_loads_four_complete_profiles() -> None:
    profiles = load_empirical_personas(MEDOID_FILE)

    assert [profile.cluster for profile in profiles] == [1, 2, 3, 4]
    assert [profile.participant_id for profile in profiles] == ["7067", "8153", "8237", "8303"]
    assert [profile.occupation_type for profile in profiles] == [
        "student",
        "mixed_study_work",
        "employed",
        "non_employed",
    ]
    assert all(
        profile.normal_weeks + profile.stress_weeks + profile.holiday_weeks == 52
        for profile in profiles
    )


def test_empirical_wrapper_uses_occupation_specific_primary_workload() -> None:
    profiles = load_empirical_personas(MEDOID_FILE)
    student_week = profiles[0].to_wrapper().generate_week(YearPhase.NORMAL, seed=1)
    employed_week = profiles[2].to_wrapper().generate_week(YearPhase.NORMAL, seed=1)
    non_employed_week = profiles[3].to_wrapper().generate_week(YearPhase.NORMAL, seed=1)
    employed_holiday = profiles[2].to_wrapper().generate_week(YearPhase.HOLIDAY, seed=1)

    assert next(b for b in student_week.budgets if b.subtype == "university").total_hours == 40
    assert next(b for b in employed_week.budgets if b.subtype == "paid_work").total_hours == 40
    assert not any(b.activity_type.value == "work" for b in non_employed_week.budgets)
    assert not any(b.activity_type.value == "work" for b in employed_holiday.budgets)


def test_empirical_year_structure_uses_exact_reported_phase_counts() -> None:
    for profile in load_empirical_personas(MEDOID_FILE):
        wrapper = profile.to_wrapper()
        year = YearStructureGenerator(wrapper.year_structure_config()).generate_year(
            persona_id=wrapper.name,
            persona_seed=137,
            parameters=wrapper,
            n_weeks=52,
        )
        assert year.phase_counts == {
            "normal": profile.normal_weeks,
            "high_stress": profile.stress_weeks,
            "holiday": profile.holiday_weeks,
        }


def test_observed_psychological_state_is_not_resampled() -> None:
    profile = load_empirical_personas(MEDOID_FILE)[2]
    state = build_psychological_state_from_values(profile.psychological_constructs)

    assert state["sampling_method"] == "observed_profile"
    assert state["seed"] is None
    assert state["values_normalized"] == {
        key: round(value, 3)
        for key, value in profile.psychological_constructs.items()
    }
