from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

"""
Lightweight diagnostic tests for student schedule generation.

Important:
Plausibility checks in this script are heuristic debugging aids.
They are intentionally simple and should not be interpreted as formal realism validation.

Hard failures:
- technical schedule errors
- weekly budget mismatches in normal cases

Expected overload warnings:
- weekly budget mismatches in the intentionally overloaded stress-test case
"""

import random

from persona_wrappers import StudentHoursWrapper
from schedule_model_student import (
    AcuteIllnessConstraint,
    ActivityType,
    DayEpisode,
    WEEKDAY_NAMES,
    YearPhase,
    distribute_weekly_budgets_to_days,
    generate_full_day_schedule,
    is_active_on_weekday,
    validate_full_day_schedule,
    validate_weekly_budget_consistency,
    validate_weekly_structure,
)

PHASES = [YearPhase.SEMESTER, YearPhase.EXAM_PHASE, YearPhase.HOLIDAY]


def count_activity(
    day_schedule: list[DayEpisode],
    activity_type: ActivityType,
    subtype: str | None = None,
) -> int:
    return sum(
        1
        for ep in day_schedule
        if ep.activity_type == activity_type and (subtype is None or ep.subtype == subtype)
    )


def has_subtype(day_schedule: list[DayEpisode], subtype: str) -> bool:
    return any(ep.subtype == subtype for ep in day_schedule)


def compare_counts(original_day: list[DayEpisode], illness_day: list[DayEpisode]) -> dict[str, int]:
    return {
        "physical_original": count_activity(original_day, ActivityType.PHYSICAL_ACTIVITY),
        "physical_illness": count_activity(illness_day, ActivityType.PHYSICAL_ACTIVITY),
        "social_original": count_activity(original_day, ActivityType.SOCIAL_TIME),
        "social_illness": count_activity(illness_day, ActivityType.SOCIAL_TIME),
        "work_original": count_activity(original_day, ActivityType.WORK),
        "work_illness": count_activity(illness_day, ActivityType.WORK),
        "sleep_original": count_activity(original_day, ActivityType.SLEEP),
        "sleep_illness": count_activity(illness_day, ActivityType.SLEEP),
        "recovery_original": count_activity(original_day, ActivityType.DOWNTIME, "illness_recovery"),
        "recovery_illness": count_activity(illness_day, ActivityType.DOWNTIME, "illness_recovery"),
    }


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

    hours = [ep.hour for ep in day_schedule]

    # Technical validity: hard failures
    if len(day_schedule) != 24:
        hard_failures.append(
            f"{WEEKDAY_NAMES[weekday]}: expected 24 episodes, got {len(day_schedule)}"
        )

    if len(set(hours)) != len(hours):
        hard_failures.append(f"{WEEKDAY_NAMES[weekday]}: duplicate hours detected")

    if any(h < 0 or h > 23 for h in hours):
        hard_failures.append(f"{WEEKDAY_NAMES[weekday]}: hour outside 0-23")

    if set(hours) != set(range(24)):
        hard_failures.append(
            f"{WEEKDAY_NAMES[weekday]}: not all hours 0-23 present exactly once"
        )

    valid_activity_types = set(ActivityType)
    if any(ep.activity_type not in valid_activity_types for ep in day_schedule):
        hard_failures.append(f"{WEEKDAY_NAMES[weekday]}: invalid activity_type values present")

    sleep_hours = sum(1 for ep in day_schedule if ep.activity_type == ActivityType.SLEEP)
    if sleep_hours < 5:
        hard_failures.append(f"{WEEKDAY_NAMES[weekday]}: sleep_hours={sleep_hours} < 5")
    elif sleep_hours < 6:
        warnings.append(f"{WEEKDAY_NAMES[weekday]}: sleep_hours={sleep_hours} < 6")

    # Heuristic plausibility checks: warnings only
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

    if wake_ups:
        wake_hour = wake_ups[0].hour
        daytime_sleep = [
            ep.hour
            for ep in day_schedule
            if ep.activity_type == ActivityType.SLEEP and wake_hour < ep.hour < 18
        ]
        if daytime_sleep:
            warnings.append(f"{WEEKDAY_NAMES[weekday]}: sleep block after wake_up")

    if all(ep.activity_type != ActivityType.DOWNTIME for ep in day_schedule):
        warnings.append(f"{WEEKDAY_NAMES[weekday]}: no downtime at all")

    if phase == YearPhase.SEMESTER and weekday < 5:
        core_budget_hours = 0
        for budget in structure.budgets:
            subtype = budget.subtype or budget.activity_type.value
            if subtype in {"university", "paid_work", "studying"}:
                core_budget_hours += max(0, budget.total_hours)

        if core_budget_hours > 0 and productive_hours == 0:
            warnings.append(
                f"{WEEKDAY_NAMES[weekday]}: no productive activity on semester weekday despite positive core budgets"
            )

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

    weekly_structure_check = validate_weekly_structure(structure)
    warnings.extend([f"{phase.value}: {w}" for w in weekly_structure_check["warnings"]])

    required_metadata_keys = {
        "input_fitness_hours_week",
        "input_social_hours_week",
        "input_work_hours_week",
    }

    for key in required_metadata_keys:
        if key not in structure.metadata:
            hard_failures.append(f"{phase.value}: missing metadata key '{key}'")

    structure.metadata["daily_budget_distribution"] = distribute_weekly_budgets_to_days(
        structure,
        random.Random(base_seed + 99),
    )

    week_schedules: dict[int, list[DayEpisode]] = {}

    for weekday in range(7):
        week_schedules[weekday] = generate_full_day_schedule(
            structure,
            weekday,
            rng=random.Random(base_seed + 100 + weekday),
        )

    consistency = validate_weekly_budget_consistency(structure, week_schedules)

    for consistency_warning in consistency["warnings"]:
        tagged_warning = f"{phase.value}: {consistency_warning}"

        if "budget=" in consistency_warning and "scheduled=" in consistency_warning:
            if treat_budget_mismatch_as_expected_warning:
                expected_overload_warnings.append(tagged_warning)
            else:
                hard_failures.append(tagged_warning)
        else:
            warnings.append(tagged_warning)

    phase_day_warning_start = len(warnings)

    for weekday in range(7):
        # Keep existing model-level validation as additional soft diagnostics.
        model_day_validation = validate_full_day_schedule(week_schedules[weekday])
        warnings.extend(
            [
                f"{phase.value}: {WEEKDAY_NAMES[weekday]}: {w}"
                for w in model_day_validation.get("warnings", [])
            ]
        )

        day_hard_failures, day_warnings = _day_checks(
            week_schedules[weekday],
            weekday,
            phase,
            structure,
        )

        hard_failures.extend([f"{phase.value}: {x}" for x in day_hard_failures])
        warnings.extend([f"{phase.value}: {x}" for x in day_warnings])

    print(f"\nPhase: {phase.value}")
    print(f"Weekly structure: {'OK' if weekly_structure_check['ok'] else 'WARN'}")

    if consistency["ok"]:
        print("Weekly budget consistency: OK")
    elif treat_budget_mismatch_as_expected_warning:
        print("Weekly budget consistency: EXPECTED OVERLOAD WARNINGS")
    else:
        print("Weekly budget consistency: WARN/FAIL")

    print("Weekly budget consistency:")
    for item in consistency["summary"]:
        print(
            f"- {item['subtype']}: "
            f"budget={item['budget_hours']}h, "
            f"scheduled={item['scheduled_hours']}h, "
            f"target_days={item['target_days']}, "
            f"actual_days={item['actual_days']}"
        )

    phase_day_warnings = warnings[phase_day_warning_start:]
    if phase_day_warnings:
        print("Plausibility warnings:")
        for warning in phase_day_warnings[:12]:
            readable_warning = warning.split(": ", 1)[1] if ": " in warning else warning
            print(f"- {readable_warning}")
        if len(phase_day_warnings) > 12:
            print(f"- ... and {len(phase_day_warnings) - 12} more")
    else:
        print("Plausibility warnings: none")

    if expected_overload_warnings:
        print("Expected overload warnings:")
        for warning in expected_overload_warnings:
            print(f"- {warning}")

    return hard_failures, warnings, expected_overload_warnings


def main() -> None:
    print("=== TEST STUDENT SCHEDULE MODEL ===")

    total_hard_failures: list[str] = []
    total_warnings: list[str] = []
    total_expected_overload_warnings: list[str] = []

    # Normal student: these phases should pass without hard failures.
    normal_student = StudentHoursWrapper(
        name="student_test",
        fitness_hours_week=6,
        social_hours_week=8,
        work_hours_week=5,
    )

    for i, phase in enumerate(PHASES):
        hard_failures, warnings, expected_overload_warnings = _run_phase(
            normal_student,
            phase,
            base_seed=37 + i * 1000,
        )
        total_hard_failures.extend(hard_failures)
        total_warnings.extend(warnings)
        total_expected_overload_warnings.extend(expected_overload_warnings)

    # Edge case: overloaded student.
    # Budget mismatches are expected here and should not fail the whole script.
    overloaded_student = StudentHoursWrapper(
        name="student_overloaded",
        fitness_hours_week=14,
        social_hours_week=16,
        work_hours_week=25,
    )

    print("\n--- Edge case: overloaded student (semester) ---")
    hard_failures, warnings, expected_overload_warnings = _run_phase(
        overloaded_student,
        YearPhase.SEMESTER,
        base_seed=9001,
        treat_budget_mismatch_as_expected_warning=True,
    )
    total_hard_failures.extend(hard_failures)
    total_warnings.extend(warnings)
    total_expected_overload_warnings.extend(expected_overload_warnings)

    # Edge case: low activity should still technically pass.
    low_activity_student = StudentHoursWrapper(
        name="student_low_activity",
        fitness_hours_week=0,
        social_hours_week=1,
        work_hours_week=0,
    )

    print("\n--- Edge case: low-activity student (semester) ---")
    hard_failures, warnings, expected_overload_warnings = _run_phase(
        low_activity_student,
        YearPhase.SEMESTER,
        base_seed=1234,
    )
    total_hard_failures.extend(hard_failures)
    total_warnings.extend(warnings)
    total_expected_overload_warnings.extend(expected_overload_warnings)

    # Edge case: explicit carework budget should be generated and scheduled.
    carework_student = StudentHoursWrapper(
        name="carework_student",
        fitness_hours_week=6,
        social_hours_week=8,
        work_hours_week=5,
        carework_hours_week=3,
    )

    print("\n--- Edge case: carework student (semester) ---")
    carework_structure = carework_student.generate_week(phase=YearPhase.SEMESTER, seed=3210)
    carework_budget = next((b for b in carework_structure.budgets if b.subtype == "carework"), None)
    if carework_budget is None:
        total_hard_failures.append("semester: carework_student missing carework budget")
    elif carework_budget.total_hours != 3:
        total_hard_failures.append(
            f"semester: carework_student carework budget total={carework_budget.total_hours} expected=3"
        )

    hard_failures, warnings, expected_overload_warnings = _run_phase(
        carework_student,
        YearPhase.SEMESTER,
        base_seed=3210,
    )
    total_hard_failures.extend(hard_failures)
    total_warnings.extend(warnings)
    total_expected_overload_warnings.extend(expected_overload_warnings)

    carework_structure.metadata["daily_budget_distribution"] = distribute_weekly_budgets_to_days(
        carework_structure,
        random.Random(3210 + 99),
    )
    carework_week = {
        weekday: generate_full_day_schedule(
            carework_structure,
            weekday,
            rng=random.Random(3210 + 100 + weekday),
        )
        for weekday in range(7)
    }
    carework_hours_scheduled = sum(
        1
        for day_eps in carework_week.values()
        for ep in day_eps
        if ep.activity_type == ActivityType.CAREWORK and ep.subtype == "carework"
    )
    if abs(carework_hours_scheduled - 3) > 1:
        total_hard_failures.append(
            f"semester: carework_student scheduled carework={carework_hours_scheduled} expected approx 3"
        )

    # Edge case: explicit zero carework should keep no-carework behavior.
    zero_carework_student = StudentHoursWrapper(
        name="student_zero_carework",
        fitness_hours_week=0,
        social_hours_week=1,
        work_hours_week=0,
        carework_hours_week=0,
    )

    print("\n--- Edge case: zero-carework student (semester) ---")
    zero_carework_structure = zero_carework_student.generate_week(phase=YearPhase.SEMESTER, seed=4321)
    if any(b.subtype == "carework" for b in zero_carework_structure.budgets):
        total_hard_failures.append("semester: zero-carework student should not have carework budget")

    hard_failures, warnings, expected_overload_warnings = _run_phase(
        zero_carework_student,
        YearPhase.SEMESTER,
        base_seed=4321,
    )
    total_hard_failures.extend(hard_failures)
    total_warnings.extend(warnings)
    total_expected_overload_warnings.extend(expected_overload_warnings)

    print("\n--- Constraint test: acute illness ---")
    constraint_student = StudentHoursWrapper(
        name="student_test",
        fitness_hours_week=6,
        social_hours_week=8,
        work_hours_week=5,
    )
    base_seed = 2026
    constraint_structure = constraint_student.generate_week(phase=YearPhase.SEMESTER, seed=base_seed)
    constraint_structure.metadata["daily_budget_distribution"] = distribute_weekly_budgets_to_days(
        constraint_structure,
        random.Random(base_seed + 99),
    )
    base_week = {
        weekday: generate_full_day_schedule(
            constraint_structure,
            weekday,
            rng=random.Random(base_seed + 100 + weekday),
        )
        for weekday in range(7)
    }

    def _record_constraint_result(label: str, ok: bool, failure: str) -> None:
        if ok:
            print(f"{label}: OK")
        else:
            print(f"{label}: FAIL")
            total_hard_failures.append(failure)

    low_constraint = AcuteIllnessConstraint(start_weekday=0, duration_days=1, intensity="low")
    low_day = generate_full_day_schedule(
        constraint_structure,
        0,
        rng=random.Random(base_seed + 100),
        constraints=[low_constraint],
    )
    low_cmp = compare_counts(base_week[0], low_day)
    low_valid = validate_full_day_schedule(low_day)["ok"]
    low_ok = (
        low_valid
        and low_cmp["physical_illness"] <= low_cmp["physical_original"]
        and low_cmp["social_illness"] <= low_cmp["social_original"]
        and (
            low_cmp["work_original"] == 0
            or low_cmp["work_illness"] > 0
        )
    )
    _record_constraint_result("low illness", low_ok, "acute illness low: constraint behavior mismatch")

    medium_constraint = AcuteIllnessConstraint(start_weekday=0, duration_days=1, intensity="medium")
    medium_day = generate_full_day_schedule(
        constraint_structure,
        0,
        rng=random.Random(base_seed + 100),
        constraints=[medium_constraint],
    )
    medium_cmp = compare_counts(base_week[0], medium_day)
    medium_valid = validate_full_day_schedule(medium_day)["ok"]
    medium_ok = (
        medium_valid
        and medium_cmp["physical_illness"] == 0
        and medium_cmp["social_illness"] == 0
        and (medium_cmp["work_original"] == 0 or medium_cmp["work_illness"] < medium_cmp["work_original"])
        and (
            medium_cmp["sleep_illness"] >= medium_cmp["sleep_original"]
            or medium_cmp["recovery_illness"] > medium_cmp["recovery_original"]
        )
    )
    _record_constraint_result("medium illness", medium_ok, "acute illness medium: constraint behavior mismatch")

    high_constraint = AcuteIllnessConstraint(start_weekday=0, duration_days=1, intensity="high")
    high_day = generate_full_day_schedule(
        constraint_structure,
        0,
        rng=random.Random(base_seed + 100),
        constraints=[high_constraint],
    )
    high_cmp = compare_counts(base_week[0], high_day)
    had_meal = any(ep.activity_type == ActivityType.EAT for ep in base_week[0])
    has_meal = any(ep.activity_type == ActivityType.EAT for ep in high_day)
    high_valid = validate_full_day_schedule(high_day)["ok"]
    high_ok = (
        high_valid
        and high_cmp["physical_illness"] == 0
        and high_cmp["social_illness"] == 0
        and high_cmp["work_illness"] == 0
        and (
            has_subtype(high_day, "illness_recovery")
            or has_subtype(high_day, "illness_sleep")
        )
        and ((not had_meal) or has_meal)
    )
    _record_constraint_result("high illness", high_ok, "acute illness high: constraint behavior mismatch")

    duration_constraint = AcuteIllnessConstraint(start_weekday=1, duration_days=2, intensity="high")
    duration_days = {
        weekday: generate_full_day_schedule(
            constraint_structure,
            weekday,
            rng=random.Random(base_seed + 100 + weekday),
            constraints=[duration_constraint],
        )
        for weekday in (0, 1, 2, 3)
    }
    duration_ok = (
        not has_subtype(duration_days[0], "illness_recovery")
        and not has_subtype(duration_days[0], "illness_sleep")
        and (
            has_subtype(duration_days[1], "illness_recovery")
            or has_subtype(duration_days[1], "illness_sleep")
        )
        and (
            has_subtype(duration_days[2], "illness_recovery")
            or has_subtype(duration_days[2], "illness_sleep")
        )
        and not has_subtype(duration_days[3], "illness_recovery")
        and not has_subtype(duration_days[3], "illness_sleep")
    )
    _record_constraint_result("duration logic", duration_ok, "acute illness duration logic mismatch")

    print("\nFinal result:")

    if total_hard_failures:
        print(f"FAIL: {len(total_hard_failures)} hard failure(s).")
        for failure in total_hard_failures[:15]:
            print(f"- {failure}")
        if len(total_hard_failures) > 15:
            print(f"- ... and {len(total_hard_failures) - 15} more")

        if total_expected_overload_warnings:
            print(f"Expected overload warnings: {len(total_expected_overload_warnings)}")

        if total_warnings:
            print(f"WARNING SUMMARY: {len(total_warnings)} plausibility/soft warning(s).")

        raise SystemExit(1)

    print("PASS: no hard failures in normal or technical edge-case checks.")
    print(f"Expected overload warnings: {len(total_expected_overload_warnings)}")
    print(f"Plausibility warnings: {len(total_warnings)}")


if __name__ == "__main__":
    main()
