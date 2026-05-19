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


def _illness_constraint(intensity: str) -> list[dict[str, object]]:
    return [{"name": "acute_illness", "type": "AcuteIllnessConstraint", "intensity": intensity}]


def _print_energy_example(
    *,
    title: str,
    context_lines: list[str],
    energy_state,
    interpretation: str,
) -> None:
    print(f"{title}")
    print("Context:")
    for line in context_lines:
        print(f"  {line}")

    print("\nEnergyState:")
    print(f"  energy_level: {energy_state.energy_level:.3f}")
    print(f"  fatigue_level: {energy_state.fatigue_level:.3f}")
    print(f"  category: {energy_state.energy_category}")

    print("\nDrivers:")
    for key in [
        "time_of_day_component",
        "phase_load_penalty",
        "illness_penalty",
        "daily_workload_penalty",
        "prior_activity_penalty",
        "noise",
    ]:
        print(f"  {key}: {energy_state.drivers[key]:.3f}")

    print("\nInterpretation:")
    print(f"  {interpretation}")
    print()


def demo_energy_state_examples() -> None:
    seed = 42
    model = EnergyModel()

    print("=== ENERGY STATE DEMO EXAMPLES ===\n")

    # Example A: Normal semester day, no illness
    example_a = model.compute_energy_state(
        hour=10,
        phase=YearPhase.SEMESTER,
        active_constraints=[],
        constrained_schedule=_sched(load_hours=5),
        seed=seed,
    )
    _print_energy_example(
        title="Example A: Normal semester morning",
        context_lines=[
            "phase: semester",
            "hour: 10",
            "illness: none",
            "workload: medium",
            "prior PA: no",
        ],
        energy_state=example_a,
        interpretation="Morning increases energy, while semester phase slightly reduces it.",
    )

    # Example B: Semester with mid illness
    example_b = model.compute_energy_state(
        hour=10,
        phase=YearPhase.SEMESTER,
        active_constraints=_illness_constraint("mid"),
        constrained_schedule=_sched(load_hours=5),
        seed=seed,
    )
    _print_energy_example(
        title="Example B: Semester day with mid illness",
        context_lines=[
            "phase: semester",
            "hour: 10",
            "illness: mid",
            "workload: medium",
            "prior PA: no",
        ],
        energy_state=example_b,
        interpretation="Energy is lower because illness adds a substantial penalty.",
    )

    # Example C: Exam phase with high workload
    example_c = model.compute_energy_state(
        hour=14,
        phase=YearPhase.EXAM_PHASE,
        active_constraints=[],
        constrained_schedule=_sched(load_hours=8),
        seed=seed,
    )
    _print_energy_example(
        title="Example C: Exam phase midday load",
        context_lines=[
            "phase: exam_phase",
            "hour: 14",
            "illness: none",
            "workload: high",
            "prior PA: no",
        ],
        energy_state=example_c,
        interpretation="Energy is lower because exam phase and workload increase load.",
    )

    # Example D: Holiday, low workload
    example_d = model.compute_energy_state(
        hour=10,
        phase=YearPhase.HOLIDAY,
        active_constraints=[],
        constrained_schedule=_sched(load_hours=1),
        seed=seed,
    )
    _print_energy_example(
        title="Example D: Holiday morning, low load",
        context_lines=[
            "phase: holiday",
            "hour: 10",
            "illness: none",
            "workload: low",
            "prior PA: no",
        ],
        energy_state=example_d,
        interpretation="Energy is higher because phase load is low and morning component is positive.",
    )

    # Example E: Evening after earlier physical activity
    example_e = model.compute_energy_state(
        hour=21,
        phase=YearPhase.SEMESTER,
        active_constraints=[],
        constrained_schedule=_sched(load_hours=4, pa_hours=[8, 17]),
        seed=seed,
    )
    _print_energy_example(
        title="Example E: Evening after prior physical activity",
        context_lines=[
            "phase: semester",
            "hour: 21",
            "illness: none",
            "workload: medium",
            "prior PA: yes (2h earlier today)",
        ],
        energy_state=example_e,
        interpretation="Energy is lower because of evening time and prior PA penalty.",
    )


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
        active_constraints=_illness_constraint("high"),
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


def test_demo_energy_state_examples_runs(capsys) -> None:
    demo_energy_state_examples()
    captured = capsys.readouterr()
    assert "ENERGY STATE DEMO EXAMPLES" in captured.out
    assert "Example A" in captured.out
    assert "EnergyState" in captured.out


if __name__ == "__main__":
    demo_energy_state_examples()
