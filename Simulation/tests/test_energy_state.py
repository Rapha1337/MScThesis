from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from constraints.illness import AcuteIllnessConstraint
from constraints.manager import ConstraintManager
from energy_model import EnergyModel
from persona_wrappers import StudentHoursWrapper
from schedule_model_student import YearPhase
from simulation_runner import SimulationRunner


class FakeEnv:
    def reset(self, seed=None, options=None):
        del options
        return None, {"seed": seed, "hour": 10}

    def step(self, action: int = 0):
        return None, 0.0, False, False, {"action": action, "hour": 10}


def _sched(load_hours: int, pa_hours: list[int] | None = None) -> list[dict[str, object]]:
    pa_hours = pa_hours or []
    out = []
    for h in range(24):
        subtype = None
        at = "downtime"
        if h < load_hours:
            at = "work"
            subtype = "studying"
        if h in pa_hours:
            at = "physical_activity"
            subtype = "jogging"
        out.append({"hour": h, "activity_type": at, "subtype": subtype, "flexibility": "flexible"})
    return out


def test_energy_bounds_and_determinism() -> None:
    model = EnergyModel()
    s = _sched(5, [7])
    a = model.compute_energy_state(hour=10, phase=YearPhase.SEMESTER, active_constraints=[], constrained_schedule=s, seed=42)
    b = model.compute_energy_state(hour=10, phase=YearPhase.SEMESTER, active_constraints=[], constrained_schedule=s, seed=42)
    assert 0.0 <= a.energy_level <= 1.0
    assert 0.0 <= a.fatigue_level <= 1.0
    assert a.to_dict() == b.to_dict()


def test_time_of_day_pattern() -> None:
    model = EnergyModel()
    s = _sched(0)
    morning = model.compute_energy_state(hour=10, phase=YearPhase.HOLIDAY, active_constraints=[], constrained_schedule=s, seed=1)
    late_evening = model.compute_energy_state(hour=22, phase=YearPhase.HOLIDAY, active_constraints=[], constrained_schedule=s, seed=1)
    assert morning.energy_level > late_evening.energy_level


def test_phase_illness_and_workload_effects() -> None:
    model = EnergyModel()
    low_load = _sched(2)
    high_load = _sched(8)

    holiday = model.compute_energy_state(hour=10, phase=YearPhase.HOLIDAY, active_constraints=[], constrained_schedule=low_load, seed=3)
    exam = model.compute_energy_state(hour=10, phase=YearPhase.EXAM_PHASE, active_constraints=[], constrained_schedule=low_load, seed=3)
    assert exam.energy_level < holiday.energy_level

    healthy = model.compute_energy_state(hour=10, phase=YearPhase.SEMESTER, active_constraints=[], constrained_schedule=low_load, seed=7)
    ill = model.compute_energy_state(
        hour=10,
        phase=YearPhase.SEMESTER,
        active_constraints=[{"name": "acute_illness", "type": "AcuteIllnessConstraint", "intensity": "high"}],
        constrained_schedule=low_load,
        seed=7,
    )
    assert ill.energy_level < healthy.energy_level

    high = model.compute_energy_state(hour=10, phase=YearPhase.SEMESTER, active_constraints=[], constrained_schedule=high_load, seed=5)
    low = model.compute_energy_state(hour=10, phase=YearPhase.SEMESTER, active_constraints=[], constrained_schedule=low_load, seed=5)
    assert high.energy_level < low.energy_level


def test_schedule_preservation_and_context_integration() -> None:
    persona = StudentHoursWrapper.from_zve_student_generic(name="energy_student")
    illness = AcuteIllnessConstraint(name="flu", intensity="mid", start_weekday=1, duration_days=2)
    runner = SimulationRunner(persona, YearPhase.SEMESTER, FakeEnv(), ConstraintManager([illness]), seed=37)

    normal_before = runner.generate_normal_day(1)
    constrained_before = runner.generate_constrained_day(1)

    context = runner.get_day_context(1)

    normal_after = runner.generate_normal_day(1)
    constrained_after = runner.generate_constrained_day(1)

    assert [(e.hour, e.activity_type, e.subtype) for e in normal_before] == [(e.hour, e.activity_type, e.subtype) for e in normal_after]
    assert [(e.hour, e.activity_type, e.subtype) for e in constrained_before] == [(e.hour, e.activity_type, e.subtype) for e in constrained_after]
    assert "agent_state" in context and "energy" in context["agent_state"]
