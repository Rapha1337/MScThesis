from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from energy_model import EnergyModel
from persona_wrappers import StudentHoursWrapper, StudentWrapper, create_personas
from schedule_model_student import YearPhase
from week_variance import compare_week_structures, summarize_pairwise_week_variance


def _sched(load_hours: int) -> list[dict[str, object]]:
    return [{"hour": h, "activity_type": "work" if h < load_hours else "downtime", "subtype": "studying" if h < load_hours else None} for h in range(24)]


def test_energy_effect_signs_and_phase_aliases() -> None:
    model = EnergyModel()
    normal = model.compute_energy_state(hour=10, phase="normal", active_constraints=[], constrained_schedule=_sched(2), seed=7)
    stress = model.compute_energy_state(hour=10, phase="high_stress", active_constraints=[], constrained_schedule=_sched(2), seed=7)
    holiday = model.compute_energy_state(hour=10, phase="holiday", active_constraints=[], constrained_schedule=_sched(2), seed=7)
    alias_semester = model.compute_energy_state(hour=10, phase="semester", active_constraints=[], constrained_schedule=_sched(2), seed=7)
    alias_exam = model.compute_energy_state(hour=10, phase="exam_phase", active_constraints=[], constrained_schedule=_sched(2), seed=7)

    assert stress.energy_level < normal.energy_level
    assert holiday.energy_level > normal.energy_level
    assert alias_semester.energy_level == normal.energy_level
    assert alias_exam.energy_level == stress.energy_level

    ill_low = model.compute_energy_state(hour=10, phase="normal", active_constraints=[{"name": "acute_illness", "intensity": "low"}], constrained_schedule=_sched(2), seed=9)
    ill_high = model.compute_energy_state(hour=10, phase="normal", active_constraints=[{"name": "acute_illness", "intensity": "high"}], constrained_schedule=_sched(2), seed=9)
    assert ill_high.energy_level < ill_low.energy_level
    assert "illness_effect" in ill_high.drivers


def test_student_wrapper_deterministic_persona_seeds() -> None:
    params = StudentHoursWrapper.from_zve_student_generic()
    a = StudentWrapper(parameters=params, base_seed=123).create_personas(n_personas=30, phase=YearPhase.NORMAL)
    b = StudentWrapper(parameters=params, base_seed=123).create_personas(n_personas=30, phase=YearPhase.NORMAL)
    c = create_personas(n_personas=30, base_seed=124, phase="normal", parameters=params)

    assert len(a) == 30
    assert [x["persona_seed"] for x in a] == [x["persona_seed"] for x in b]
    assert [x["persona_seed"] for x in a] != [x["persona_seed"] for x in c]


def test_week_comparison_extremes_and_partial() -> None:
    week_a = [["sleep"] * 24 for _ in range(7)]
    week_b = [["sleep"] * 24 for _ in range(7)]
    week_c = [["work"] * 24 for _ in range(7)]
    week_d = [["sleep" if h < 12 else "work" for h in range(24)] for _ in range(7)]

    same = compare_week_structures(week_a, week_b)
    diff = compare_week_structures(week_a, week_c)
    partial = compare_week_structures(week_a, week_d)

    assert same["similarity_percent"] == 100.0 and same["variance_percent"] == 0.0
    assert diff["similarity_percent"] == 0.0 and diff["variance_percent"] == 100.0
    assert partial["matching_slots"] == 84

    summary = summarize_pairwise_week_variance([week_a, week_b, week_d])
    assert summary["n_weeks"] == 3
    assert summary["n_pairwise_comparisons"] == 3
