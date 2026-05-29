from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

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


def _inactive_weekday(runner: SimulationRunner, excluded: set[int] | None = None) -> int:
    excluded = excluded or set()
    week_index, _, _ = runner._derive_time_indices()
    for weekday in range(7):
        if weekday in excluded:
            continue
        if not runner._get_active_events_for_day(week_index, weekday):
            return weekday
    raise AssertionError("Expected at least one weekday without active year-structure events.")


def _event_context_with_difference(runner: SimulationRunner, event_type: str) -> dict:
    for event in runner.year_structure.events:
        if event.event_type != event_type:
            continue
        start_abs_day = event.start_week * 7 + event.start_day
        end_abs_day = start_abs_day + event.duration_days
        for abs_day in range(start_abs_day, end_abs_day):
            runner._sim_hour = (abs_day // 7) * 7 * 24
            context = runner.get_day_context(weekday=abs_day % 7)
            if context["normal_schedule"] != context["constrained_schedule"]:
                return context
    raise AssertionError(f"Expected at least one active {event_type} event to change the constrained schedule.")


def run_checks() -> None:
    persona = StudentHoursWrapper.from_zve_student_generic(name="sanity_student")

    # 1) without constraints or active year-structure events, baseline and final schedule match.
    runner_plain = SimulationRunner(persona, YearPhase.SEMESTER, FakeEnv(), ConstraintManager(), seed=37)
    plain_weekday = _inactive_weekday(runner_plain)
    c_plain = runner_plain.get_day_context(weekday=plain_weekday)
    assert c_plain["normal_schedule"] == c_plain["constrained_schedule"]

    # 2) with active external illness, affected day differs and unaffected day stays same.
    illness = AcuteIllnessConstraint(name="flu", intensity="high", start_weekday=2, duration_days=2)
    runner_ill = SimulationRunner(persona, YearPhase.SEMESTER, FakeEnv(), ConstraintManager([illness]), seed=37)
    wed = runner_ill.get_day_context(weekday=2)
    unaffected_weekday = _inactive_weekday(runner_ill, excluded={2, 3})
    unaffected = runner_ill.get_day_context(weekday=unaffected_weekday)
    assert wed["normal_schedule"] != wed["constrained_schedule"]
    assert unaffected["normal_schedule"] == unaffected["constrained_schedule"]

    # 3) year-structure public holidays and illness events still affect only the final schedule.
    public_holiday_context = _event_context_with_difference(
        SimulationRunner(persona, YearPhase.SEMESTER, FakeEnv(), ConstraintManager(), seed=37),
        "public_holiday",
    )
    assert any(ep["subtype"] == "public_holiday" for ep in public_holiday_context["constrained_schedule"])

    illness_context = _event_context_with_difference(
        SimulationRunner(persona, YearPhase.SEMESTER, FakeEnv(), ConstraintManager(), seed=123),
        "illness",
    )
    assert any(ep["subtype"] in {"illness_recovery", "illness_sleep"} for ep in illness_context["constrained_schedule"])
    assert any(constraint["type"] == "AcuteIllnessConstraint" for constraint in illness_context["active_constraints"])

    # 4) same seed same baseline schedule.
    a = SimulationRunner(persona, YearPhase.SEMESTER, FakeEnv(), ConstraintManager(), seed=37)
    b = SimulationRunner(persona, YearPhase.SEMESTER, FakeEnv(), ConstraintManager(), seed=37)
    assert _to_tuple(a.get_day_context(3)["normal_schedule"]) == _to_tuple(b.get_day_context(3)["normal_schedule"])

    # 5) different seeds may differ (non-forced, informational).
    c = SimulationRunner(persona, YearPhase.SEMESTER, FakeEnv(), ConstraintManager(), seed=38)
    diff = _to_tuple(a.get_day_context(3)["normal_schedule"]) != _to_tuple(c.get_day_context(3)["normal_schedule"])
    print(f"Different-seed produced different schedule: {diff}")


def test_simulation_runner_sanity() -> None:
    run_checks()


if __name__ == "__main__":
    run_checks()
    print("SimulationRunner sanity checks passed.")
