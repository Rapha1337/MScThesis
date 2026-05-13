from __future__ import annotations

from constraints.illness import AcuteIllnessConstraint
from constraints.manager import ConstraintManager
from persona_wrappers import StudentHoursWrapper
from schedule_model_student import YearPhase
from simulation_runner import SimulationRunner


class FakeEnv:
    def reset(self, seed=None, options=None):
        del options
        return None, {"seed": seed, "state": "reset"}

    def step(self, action: int = 0):
        return None, 0.0, False, False, {"action": action, "state": "stepped"}


def _to_tuple(schedule: list[dict]) -> tuple:
    return tuple((ep["hour"], ep["activity_type"], ep["subtype"], ep["flexibility"]) for ep in schedule)


def run_checks() -> None:
    persona = StudentHoursWrapper.from_zve_student_generic(name="sanity_student")

    # 1) without constraints unchanged
    runner_plain = SimulationRunner(persona, YearPhase.SEMESTER, FakeEnv(), ConstraintManager(), seed=37)
    c_plain = runner_plain.get_day_context(weekday=1)
    assert c_plain["normal_schedule"] == c_plain["constrained_schedule"]

    # 2) with active illness, affected day differs and unaffected day stays same
    illness = AcuteIllnessConstraint(name="flu", intensity="high", start_weekday=2, duration_days=2)
    runner_ill = SimulationRunner(persona, YearPhase.SEMESTER, FakeEnv(), ConstraintManager([illness]), seed=37)
    wed = runner_ill.get_day_context(weekday=2)
    mon = runner_ill.get_day_context(weekday=0)
    assert wed["normal_schedule"] != wed["constrained_schedule"]
    assert mon["normal_schedule"] == mon["constrained_schedule"]

    # 3) same seed same schedule
    a = SimulationRunner(persona, YearPhase.SEMESTER, FakeEnv(), ConstraintManager(), seed=37)
    b = SimulationRunner(persona, YearPhase.SEMESTER, FakeEnv(), ConstraintManager(), seed=37)
    assert _to_tuple(a.get_day_context(3)["normal_schedule"]) == _to_tuple(b.get_day_context(3)["normal_schedule"])

    # 4) different seeds may differ (non-forced, informational)
    c = SimulationRunner(persona, YearPhase.SEMESTER, FakeEnv(), ConstraintManager(), seed=38)
    diff = _to_tuple(a.get_day_context(3)["normal_schedule"]) != _to_tuple(c.get_day_context(3)["normal_schedule"])
    print(f"Different-seed produced different schedule: {diff}")


if __name__ == "__main__":
    run_checks()
    print("SimulationRunner sanity checks passed.")
