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
    assert a.to_dict() == b.to_dict()


def test_medium_illness_intensity_is_canonical() -> None:
    illness = AcuteIllnessConstraint(name="flu", intensity="medium", start_weekday=0, duration_days=1)
    assert illness.intensity == "medium"


def test_legacy_mid_illness_alias_normalizes_to_medium() -> None:
    illness = AcuteIllnessConstraint(name="flu", intensity="mid", start_weekday=0, duration_days=1)
    assert illness.intensity == "medium"


def test_energy_model_treats_legacy_mid_as_medium() -> None:
    model = EnergyModel()
    schedule = _sched(2)
    medium = model.compute_energy_state(
        hour=10,
        phase=YearPhase.SEMESTER,
        active_constraints=[_illness_constraint("medium")],
        constrained_schedule=schedule,
        seed=17,
    )
    legacy_mid = model.compute_energy_state(
        hour=10,
        phase=YearPhase.SEMESTER,
        active_constraints=[_illness_constraint("mid")],
        constrained_schedule=schedule,
        seed=17,
    )
    assert medium.to_dict() == legacy_mid.to_dict()


def test_runner_context_outputs_medium_for_legacy_mid_constraint() -> None:
    persona = StudentHoursWrapper.from_zve_student_generic(name="energy_student")
    illness = AcuteIllnessConstraint(name="flu", intensity="mid", start_weekday=1, duration_days=2)
    runner = SimulationRunner(persona, YearPhase.SEMESTER, FakeEnv(), ConstraintManager([illness]), seed=37)

    context = runner.get_day_context(1)

    assert context["active_constraints"][0]["intensity"] == "medium"


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


def test_favorable_normal_situation_can_reach_high_energy() -> None:
    model = EnergyModel()
    low_load = _sched(0)
    candidate_levels = [
        model.compute_energy_state(
            hour=10,
            phase=YearPhase.SEMESTER,
            active_constraints=[],
            constrained_schedule=low_load,
            seed=seed,
        ).energy_level
        for seed in range(500)
    ]
    assert max(candidate_levels) > 0.70


def test_phase_ordering_normal_holiday_high_stress() -> None:
    model = EnergyModel()
    low_load = _sched(0)

    model._stochastic_effect = lambda **_: 0.0  # type: ignore[method-assign]
    normal = model.compute_energy_state(hour=10, phase=YearPhase.SEMESTER, active_constraints=[], constrained_schedule=low_load, seed=11)
    holiday = model.compute_energy_state(hour=10, phase=YearPhase.HOLIDAY, active_constraints=[], constrained_schedule=low_load, seed=11)
    high_stress = model.compute_energy_state(hour=10, phase=YearPhase.EXAM_PHASE, active_constraints=[], constrained_schedule=low_load, seed=11)

    assert high_stress.energy_level < normal.energy_level
    assert holiday.energy_level > normal.energy_level


def test_high_illness_remains_strong_energy_penalty() -> None:
    model = EnergyModel()
    low_load = _sched(0)
    healthy = model.compute_energy_state(hour=10, phase=YearPhase.SEMESTER, active_constraints=[], constrained_schedule=low_load, seed=9)
    ill_high = model.compute_energy_state(
        hour=10,
        phase=YearPhase.SEMESTER,
        active_constraints=[_illness_constraint("high")],
        constrained_schedule=low_load,
        seed=9,
    )
    assert healthy.energy_level - ill_high.energy_level >= 0.35


def test_schedule_preservation_and_context_integration() -> None:
    persona = StudentHoursWrapper.from_zve_student_generic(name="energy_student")
    illness = AcuteIllnessConstraint(name="flu", intensity="medium", start_weekday=1, duration_days=2)
    runner = SimulationRunner(persona, YearPhase.SEMESTER, FakeEnv(), ConstraintManager([illness]), seed=37)

    normal_before = runner.generate_normal_day(1)
    constrained_before = runner.generate_constrained_day(1)

    context = runner.get_day_context(1)

    normal_after = runner.generate_normal_day(1)
    constrained_after = runner.generate_constrained_day(1)

    assert [(e.hour, e.activity_type, e.subtype) for e in normal_before] == [(e.hour, e.activity_type, e.subtype) for e in normal_after]
    assert [(e.hour, e.activity_type, e.subtype) for e in constrained_before] == [(e.hour, e.activity_type, e.subtype) for e in constrained_after]
    assert "agent_state" in context and "energy" in context["agent_state"]


def _illness_constraint(intensity: str) -> dict[str, object]:
    return {
        "name": "acute_illness",
        "type": "AcuteIllnessConstraint",
        "intensity": intensity,
    }


def _print_energy_example(
    title: str,
    *,
    hour: int,
    phase: YearPhase,
    illness: str,
    workload: str,
    prior_pa: str,
    energy,
    interpretation: str,
) -> None:
    print(f"\n{title}")
    print("Context:")
    print(f"  phase: {phase.value}")
    print(f"  hour: {hour}")
    print(f"  illness: {illness}")
    print(f"  workload: {workload}")
    print(f"  prior PA: {prior_pa}")

    print("\nEnergyState:")
    print(f"  energy_level: {energy.energy_level}")
    print(f"  category: {energy.energy_category}")

    print("\nDrivers:")
    for key, value in energy.drivers.items():
        print(f"  {key}: {value}")

    print("\nInterpretation:")
    print(f"  {interpretation}")


def demo_energy_state_examples() -> None:
    model = EnergyModel()
    seed = 42

    print("=== ENERGY STATE DEMO EXAMPLES ===")

    energy_a = model.compute_energy_state(
        hour=10,
        phase=YearPhase.SEMESTER,
        active_constraints=[],
        constrained_schedule=_sched(5),
        seed=seed,
    )
    _print_energy_example(
        "Example A: Normal semester morning",
        hour=10,
        phase=YearPhase.SEMESTER,
        illness="none",
        workload="medium",
        prior_pa="no",
        energy=energy_a,
        interpretation="Morning increases energy, while semester phase and medium workload slightly reduce it.",
    )

    energy_b = model.compute_energy_state(
        hour=10,
        phase=YearPhase.SEMESTER,
        active_constraints=[_illness_constraint("medium")],
        constrained_schedule=_sched(5),
        seed=seed,
    )
    _print_energy_example(
        "Example B: Semester morning with medium illness",
        hour=10,
        phase=YearPhase.SEMESTER,
        illness="medium",
        workload="medium",
        prior_pa="no",
        energy=energy_b,
        interpretation="Energy is lower because medium illness adds a substantial penalty.",
    )

    energy_c = model.compute_energy_state(
        hour=14,
        phase=YearPhase.EXAM_PHASE,
        active_constraints=[],
        constrained_schedule=_sched(8),
        seed=seed,
    )
    _print_energy_example(
        "Example C: Exam phase with high workload",
        hour=14,
        phase=YearPhase.EXAM_PHASE,
        illness="none",
        workload="high",
        prior_pa="no",
        energy=energy_c,
        interpretation="Energy is reduced by exam phase, high workload and the early-afternoon dip.",
    )

    energy_d = model.compute_energy_state(
        hour=10,
        phase=YearPhase.HOLIDAY,
        active_constraints=[],
        constrained_schedule=_sched(1),
        seed=seed,
    )
    _print_energy_example(
        "Example D: Holiday morning",
        hour=10,
        phase=YearPhase.HOLIDAY,
        illness="none",
        workload="low",
        prior_pa="no",
        energy=energy_d,
        interpretation="Energy is higher because holiday has low phase load and morning has a positive component.",
    )

    energy_e = model.compute_energy_state(
        hour=21,
        phase=YearPhase.SEMESTER,
        active_constraints=[],
        constrained_schedule=_sched(4, pa_hours=[17, 18]),
        seed=seed,
    )
    _print_energy_example(
        "Example E: Evening after prior physical activity",
        hour=21,
        phase=YearPhase.SEMESTER,
        illness="none",
        workload="medium",
        prior_pa="yes, 2 hours",
        energy=energy_e,
        interpretation="Energy is lower because of late evening time and prior physical activity earlier that day.",
    )

    energy_f = model.compute_energy_state(
        hour=22,
        phase=YearPhase.EXAM_PHASE,
        active_constraints=[],
        constrained_schedule=_sched(8, pa_hours=[18]),
        seed=seed,
    )
    _print_energy_example(
        "Example F: High-stress evening after a demanding day",
        hour=22,
        phase=YearPhase.EXAM_PHASE,
        illness="none",
        workload="high",
        prior_pa="yes, 1 hour",
        energy=energy_f,
        interpretation=(
            "Energy is low because high_stress, high workload, late evening "
            "and prior physical activity all reduce energy."
        )
    )


def test_demo_energy_state_examples_runs(capsys) -> None:
    demo_energy_state_examples()
    captured = capsys.readouterr()
    assert "ENERGY STATE DEMO EXAMPLES" in captured.out
    assert "Example A" in captured.out
    assert "EnergyState" in captured.out


if __name__ == "__main__":
    demo_energy_state_examples()
