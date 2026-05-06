from __future__ import annotations

"""
Lightweight diagnostic tests for student schedule generation.

Important: Plausibility checks in this script are heuristic debugging aids.
They are intentionally simple and should not be interpreted as formal realism validation.
"""

import random
import sys

from persona_wrappers import StudentHoursWrapper
from schedule_model_student import (
    ActivityType,
    DayEpisode,
    WEEKDAY_NAMES,
    YearPhase,
    generate_full_day_schedule,
    print_weekly_structure,
    validate_full_day_schedule,
    validate_weekly_budget_consistency,
    validate_weekly_structure,
    distribute_weekly_budgets_to_days,
)

PHASES = [YearPhase.SEMESTER, YearPhase.EXAM_PHASE, YearPhase.HOLIDAY]


def _is_productive(ep: DayEpisode) -> bool:
    return ep.activity_type not in {ActivityType.SLEEP, ActivityType.DOWNTIME}


def _day_checks(
    day_schedule: list[DayEpisode],
    weekday: int,
    phase: YearPhase,
    structure,
) -> tuple[list[str], list[str]]:
    hard_failures: list[str] = []
    warnings: list[str] = []

    # Technical validity (hard failures where requested)
    hours = [ep.hour for ep in day_schedule]
    if len(day_schedule) != 24:
        hard_failures.append(f"{WEEKDAY_NAMES[weekday]}: expected 24 episodes, got {len(day_schedule)}")
    if len(set(hours)) != len(hours):
        hard_failures.append(f"{WEEKDAY_NAMES[weekday]}: duplicate hours detected")
    if any(h < 0 or h > 23 for h in hours):
        hard_failures.append(f"{WEEKDAY_NAMES[weekday]}: hour outside 0-23")
    if set(hours) != set(range(24)):
        hard_failures.append(f"{WEEKDAY_NAMES[weekday]}: not all hours 0-23 present exactly once")

    valid_activity_types = set(ActivityType)
    invalid_types = [ep for ep in day_schedule if ep.activity_type not in valid_activity_types]
    if invalid_types:
        hard_failures.append(f"{WEEKDAY_NAMES[weekday]}: invalid activity_type values present")

    sleep_hours = sum(1 for ep in day_schedule if ep.activity_type == ActivityType.SLEEP)
    if sleep_hours < 5:
        hard_failures.append(f"{WEEKDAY_NAMES[weekday]}: sleep_hours={sleep_hours} < 5")
    elif sleep_hours < 6:
        warnings.append(f"{WEEKDAY_NAMES[weekday]}: sleep_hours={sleep_hours} < 6")

    wake_ups = [ep for ep in day_schedule if ep.activity_type == ActivityType.WAKE_UP]
    if len(wake_ups) > 1:
        warnings.append(f"{WEEKDAY_NAMES[weekday]}: wake_up occurs {len(wake_ups)} times")

    meal_subtypes = {ep.subtype for ep in day_schedule if ep.activity_type == ActivityType.EAT}
    for meal in ("breakfast", "lunch", "dinner"):
        if meal not in meal_subtypes:
            warnings.append(f"{WEEKDAY_NAMES[weekday]}: no {meal}")

    productive_hours = sum(1 for ep in day_schedule if _is_productive(ep))
    if productive_hours > 14:
        warnings.append(f"{WEEKDAY_NAMES[weekday]}: productive_hours={productive_hours} > 14")

    max_streak = 0
    streak = 0
    for ep in sorted(day_schedule, key=lambda e: e.hour):
        if _is_productive(ep):
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    if max_streak > 10:
        warnings.append(f"{WEEKDAY_NAMES[weekday]}: productive_streak={max_streak} > 10")

    for ep in day_schedule:
        if ep.activity_type == ActivityType.PHYSICAL_ACTIVITY and (ep.hour < 5 or ep.hour > 22):
            warnings.append(f"{WEEKDAY_NAMES[weekday]}: physical_activity at {ep.hour:02d}:00")
            break

    if weekday < 5:
        for ep in day_schedule:
            if ep.activity_type == ActivityType.SOCIAL_TIME and ep.hour < 10:
                warnings.append(f"{WEEKDAY_NAMES[weekday]}: social_time before 10:00 on weekday")
                break

    wake_hours = [ep.hour for ep in day_schedule if ep.activity_type == ActivityType.WAKE_UP]
    if wake_hours:
        wake_hour = wake_hours[0]
        daytime_sleep = [ep.hour for ep in day_schedule if ep.activity_type == ActivityType.SLEEP and wake_hour < ep.hour < 18]
        if daytime_sleep:
            warnings.append(f"{WEEKDAY_NAMES[weekday]}: sleep block after wake_up (possible conflict)")

    if all(ep.activity_type != ActivityType.DOWNTIME for ep in day_schedule):
        warnings.append(f"{WEEKDAY_NAMES[weekday]}: no downtime at all")

    if phase == YearPhase.SEMESTER and weekday < 5:
        budget_load = 0
        for b in structure.budgets:
            if (b.subtype or b.activity_type.value) in {"university", "paid_work", "studying"}:
                budget_load += max(0, b.total_hours)
        if budget_load > 0 and productive_hours == 0:
            warnings.append(f"{WEEKDAY_NAMES[weekday]}: no productive activity on semester weekday despite positive core budgets")

    if weekday >= 5 and phase != YearPhase.EXAM_PHASE and productive_hours > 10:
        warnings.append(f"{WEEKDAY_NAMES[weekday]}: weekend productive_hours={productive_hours} > 10")

    return hard_failures, warnings


def _run_phase(
    student: StudentHoursWrapper,
    phase: YearPhase,
    base_seed: int,
    treat_budget_mismatch_as_expected_warning: bool = False,
) -> tuple[list[str], list[str], list[str]]:
    hard_failures: list[str] = []
    warnings: list[str] = []
    expected_overload_warnings: list[str] = []

    structure = student.generate_week(phase=phase, seed=base_seed)

    ws = validate_weekly_structure(structure)
    warnings.extend([f"{phase.value}: {w}" for w in ws["warnings"]])

    metadata_keys = {
        "input_fitness_hours_week",
        "input_social_hours_week",
        "input_work_hours_week",
    }
    for key in metadata_keys:
        if key not in structure.metadata:
            hard_failures.append(f"{phase.value}: missing metadata key '{key}'")

    structure.metadata["daily_budget_distribution"] = distribute_weekly_budgets_to_days(structure, random.Random(base_seed + 99))

    week_schedules: dict[int, list[DayEpisode]] = {}
    for weekday in range(7):
        week_schedules[weekday] = generate_full_day_schedule(structure, weekday, rng=random.Random(base_seed + 100 + weekday))

    consistency = validate_weekly_budget_consistency(structure, week_schedules)
    for w in consistency["warnings"]:
        if "budget=" in w and "scheduled=" in w:
            tagged = f"{phase.value}: {w}"
            if treat_budget_mismatch_as_expected_warning:
                expected_overload_warnings.append(tagged)
            else:
                hard_failures.append(tagged)
        else:
            warnings.append(f"{phase.value}: {w}")

    phase_warning_count_before_days = len(warnings)

    for weekday in range(7):
        _soft = validate_full_day_schedule(week_schedules[weekday])
        day_hard, day_warn = _day_checks(week_schedules[weekday], weekday, phase, structure)
        hard_failures.extend([f"{phase.value}: {x}" for x in day_hard])
        warnings.extend([f"{phase.value}: {x}" for x in day_warn])

    print(f"\nPhase: {phase.value}")
    print(f"Weekly structure: {'OK' if ws['ok'] else 'WARN'}")
    print(f"Weekly budget consistency: {'OK' if consistency['ok'] else 'WARN/FAIL'}")
    print("Weekly budget consistency:")
    for item in consistency["summary"]:
        print(
            f"- {item['subtype']}: budget={item['budget_hours']}h, "
            f"scheduled={item['scheduled_hours']}h, target_days={item['target_days']}, "
            f"actual_days={item['actual_days']}"
        )

    phase_day_warnings = warnings[phase_warning_count_before_days:]
    if phase_day_warnings:
        print("Plausibility warnings:")
        for w in phase_day_warnings[:12]:
            print(f"- {w.split(': ', 1)[1] if ': ' in w else w}")
        if len(phase_day_warnings) > 12:
            print(f"- ... and {len(phase_day_warnings)-12} more")
    else:
        print("Plausibility warnings: none")

    if treat_budget_mismatch_as_expected_warning and expected_overload_warnings:
        print("Expected overload warnings:")
        for w in expected_overload_warnings:
            print(f"- {w}")

    return hard_failures, warnings, expected_overload_warnings


def main() -> None:
    print("=== TEST STUDENT SCHEDULE MODEL ===")

    total_hard_failures: list[str] = []
    total_warnings: list[str] = []
    expected_overload_warnings: list[str] = []

    student = StudentHoursWrapper(name="student_test", fitness_hours_week=6, social_hours_week=8, work_hours_week=5)
    for i, phase in enumerate(PHASES):
        hard, warn, expected = _run_phase(student, phase, base_seed=37 + i * 1000)
        total_hard_failures.extend(hard)
        total_warnings.extend(warn)
        expected_overload_warnings.extend(expected)

    # Edge case: overloaded
    overloaded = StudentHoursWrapper(name="student_overloaded", fitness_hours_week=14, social_hours_week=16, work_hours_week=25)
    print("\n--- Edge case: overloaded student (semester) ---")
    hard, warn, expected = _run_phase(
        overloaded,
        YearPhase.SEMESTER,
        base_seed=9001,
        treat_budget_mismatch_as_expected_warning=True,
    )
    total_hard_failures.extend(hard)
    total_warnings.extend(warn)
    expected_overload_warnings.extend(expected)

    # Edge case: low activity
    low = StudentHoursWrapper(name="student_low_activity", fitness_hours_week=0, social_hours_week=1, work_hours_week=0)
    print("\n--- Edge case: low-activity student (semester) ---")
    hard, warn, expected = _run_phase(low, YearPhase.SEMESTER, base_seed=1234)
    total_hard_failures.extend(hard)
    total_warnings.extend(warn)
    expected_overload_warnings.extend(expected)

    print("\nFinal result:")
    if total_hard_failures:
        print(f"FAIL: {len(total_hard_failures)} hard failure(s).")
        for hf in total_hard_failures[:15]:
            print(f"- {hf}")
        if len(total_hard_failures) > 15:
            print(f"- ... and {len(total_hard_failures)-15} more")
        if total_warnings:
            print(f"WARNING SUMMARY: {len(total_warnings)} plausibility/soft warning(s).")
        raise SystemExit(1)

    print("PASS: no hard failures in normal or technical edge-case checks.")
    print(f"Expected overload warnings: {len(expected_overload_warnings)}")
    print(f"Plausibility warnings: {len(total_warnings)}")


if __name__ == "__main__":
    main()
