from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from accessibility_model import build_accessibility_model
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


def _schedule_summary(schedule: list[dict]) -> tuple:
    activity_counts = Counter(ep["activity_type"] for ep in schedule)
    return (
        tuple(sorted(activity_counts.items())),
        sum(1 for ep in schedule if ep["activity_type"] == "work"),
        sum(1 for ep in schedule if ep["subtype"] == "studying"),
        activity_counts.get("physical_activity", 0),
        activity_counts.get("sleep", 0),
        activity_counts.get("downtime", 0),
    )


def _week_for_phase_without_event_on_weekday(
    runner: SimulationRunner,
    phase: str,
    weekday: int,
) -> int:
    for week in runner.year_structure.weeks:
        if week.phase == phase and not runner._get_active_events_for_day(week.week_index, weekday):
            return week.week_index
    for week in runner.year_structure.weeks:
        if week.phase == phase:
            return week.week_index
    raise AssertionError(f"Expected at least one {phase} week.")


def _budget_hours_by_subtype(items: list) -> Counter:
    hours = Counter()
    for item in items:
        if item.total_hours <= 0:
            continue
        subtype = item.subtype or item.activity_type.value
        hours[subtype] += item.total_hours
    return hours


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


def test_simulation_runner_persists_weekly_daily_budget_distribution() -> None:
    persona = StudentHoursWrapper.from_zve_student_generic(name="distribution_student")
    runner = SimulationRunner(persona, YearPhase.SEMESTER, FakeEnv(), ConstraintManager(), seed=37)

    week_index = _week_for_phase_without_event_on_weekday(runner, "normal", weekday=2)
    weekly_structure = runner._get_weekly_structure_for_week(week_index)
    distribution = weekly_structure.metadata.get("daily_budget_distribution")

    assert isinstance(distribution, dict)
    assert set(distribution) == set(range(7))

    expected_hours = _budget_hours_by_subtype(weekly_structure.budgets)
    distributed_hours = Counter()
    for day_items in distribution.values():
        distributed_hours.update(_budget_hours_by_subtype(day_items))
    assert distributed_hours == expected_hours

    runner._sim_hour = week_index * 7 * 24
    for weekday in range(7):
        runner.get_day_context(weekday=weekday)
        assert weekly_structure.metadata["daily_budget_distribution"] is distribution
        assert runner._get_weekly_structure_for_week(week_index) is weekly_structure


def test_simulation_runner_year_week_phase_and_events_affect_day_episodes() -> None:
    persona = StudentHoursWrapper.from_zve_student_generic(name="year_phase_student")
    accessibility_model = build_accessibility_model(
        workplace_distance_km=3.0,
        indoor_activity_distance_km=1.2,
        outdoor_activity_distance_km=0.6,
    )
    runner = SimulationRunner(
        persona,
        YearPhase.SEMESTER,
        FakeEnv(),
        ConstraintManager(),
        seed=37,
        use_year_structure=True,
        accessibility_model=accessibility_model,
    )

    weekday = 2
    contexts_by_phase = {}
    for phase in ["normal", "high_stress", "holiday"]:
        week_index = _week_for_phase_without_event_on_weekday(runner, phase, weekday)
        runner._sim_hour = week_index * 7 * 24 + weekday * 24
        context = runner.get_day_context()
        assert context["weekday"] == weekday
        assert context["phase"] == phase
        contexts_by_phase[phase] = context

    phase_summaries = {
        phase: _schedule_summary(context["constrained_schedule"])
        for phase, context in contexts_by_phase.items()
    }
    assert len(set(phase_summaries.values())) > 1

    hourly_accessibility = contexts_by_phase["normal"]["hourly_accessibility_24h"]
    assert len(hourly_accessibility) == 24
    assert [entry["hour"] for entry in hourly_accessibility] == [
        episode["hour"] for episode in contexts_by_phase["normal"]["constrained_schedule"]
    ]

    public_holiday_context = _event_context_with_difference(
        runner,
        "public_holiday",
    )
    assert public_holiday_context["normal_schedule"] != public_holiday_context["constrained_schedule"]
    assert any(
        episode["subtype"] == "public_holiday"
        for episode in public_holiday_context["constrained_schedule"]
    )

    illness_context = _event_context_with_difference(
        SimulationRunner(persona, YearPhase.SEMESTER, FakeEnv(), ConstraintManager(), seed=123),
        "illness",
    )
    assert illness_context["normal_schedule"] != illness_context["constrained_schedule"]
    assert any(
        episode["subtype"] in {"illness_recovery", "illness_sleep"}
        for episode in illness_context["constrained_schedule"]
    )


def test_simulation_runner_sanity() -> None:
    run_checks()


if __name__ == "__main__":
    run_checks()
    print("SimulationRunner sanity checks passed.")
