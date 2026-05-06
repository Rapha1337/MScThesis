from __future__ import annotations

import random

from persona_wrappers import StudentHoursWrapper
from schedule_model_student import (
    AcuteIllnessConstraint,
    ActivityType,
    WEEKDAY_NAMES,
    YearPhase,
    distribute_weekly_budgets_to_days,
    generate_full_day_schedule,
    print_weekly_structure,
)


def count_summary(day_schedule):
    counts = {}
    for ep in day_schedule:
        key = ep.subtype or ep.activity_type.value
        counts[key] = counts.get(key, 0) + 1
    return counts


def week_summary(week_schedules):
    total = {}
    for day_schedule in week_schedules.values():
        for key, value in count_summary(day_schedule).items():
            total[key] = total.get(key, 0) + value
    return total


def print_compact_day(weekday, day_schedule):
    counts = count_summary(day_schedule)

    important_keys = [
        "university",
        "paid_work",
        "studying",
        "physical_activity",
        "social_time",
        "illness_recovery",
        "illness_sleep",
        "night_sleep",
        "breakfast",
        "lunch",
        "dinner",
    ]

    parts = []
    for key in important_keys:
        if counts.get(key, 0) > 0:
            parts.append(f"{key}={counts[key]}h")

    print(f"{WEEKDAY_NAMES[weekday]}: " + " | ".join(parts))


def generate_week(structure, seed, constraint=None):
    week_schedules = {}

    for weekday in range(7):
        constraints = [constraint] if constraint is not None else None

        day = generate_full_day_schedule(
            structure,
            weekday,
            rng=random.Random(seed + 100 + weekday),
            constraints=constraints,
        )
        week_schedules[weekday] = day

    return week_schedules


def print_week_comparison(label, normal_week, sick_week):
    print(f"\n=== {label} ===")
    print("\nDay-level comparison:")

    for weekday in range(7):
        print(f"\n{WEEKDAY_NAMES[weekday]}")
        print("normal:")
        print_compact_day(weekday, normal_week[weekday])
        print("illness:")
        print_compact_day(weekday, sick_week[weekday])

    print("\nWeekly summary normal:")
    normal_summary = week_summary(normal_week)
    for key, value in sorted(normal_summary.items()):
        print(f"- {key}: {value}h")

    print("\nWeekly summary illness:")
    sick_summary = week_summary(sick_week)
    for key, value in sorted(sick_summary.items()):
        print(f"- {key}: {value}h")

    print("\nDifference illness - normal:")
    all_keys = sorted(set(normal_summary) | set(sick_summary))
    for key in all_keys:
        diff = sick_summary.get(key, 0) - normal_summary.get(key, 0)
        if diff != 0:
            print(f"- {key}: {diff:+}h")


def main():
    seed = 37

    student = StudentHoursWrapper(
        name="manual_test_student",
        fitness_hours_week=6,
        social_hours_week=8,
        work_hours_week=5,
    )

    structure = student.generate_week(
        phase=YearPhase.SEMESTER,
        seed=seed,
    )

    structure.metadata["daily_budget_distribution"] = distribute_weekly_budgets_to_days(
        structure,
        random.Random(seed + 99),
    )

    print_weekly_structure(structure)

    normal_week = generate_week(
        structure=structure,
        seed=seed,
        constraint=None,
    )

    test_cases = [
        AcuteIllnessConstraint(
            start_weekday=0,
            duration_days=1,
            intensity="low",
            is_active=True,
        ),
        AcuteIllnessConstraint(
            start_weekday=0,
            duration_days=3,
            intensity="low",
            is_active=True,
        ),
        AcuteIllnessConstraint(
            start_weekday=1,
            duration_days=2,
            intensity="mid",
            is_active=True,
        ),
        AcuteIllnessConstraint(
            start_weekday=2,
            duration_days=4,
            intensity="high",
            is_active=True,
        ),
    ]

    for constraint in test_cases:
        sick_week = generate_week(
            structure=structure,
            seed=seed,
            constraint=constraint,
        )

        label = (
            f"illness intensity={constraint.intensity}, "
            f"start={WEEKDAY_NAMES[constraint.start_weekday]}, "
            f"duration={constraint.duration_days} day(s)"
        )

        print_week_comparison(label, normal_week, sick_week)


if __name__ == "__main__":
    main()