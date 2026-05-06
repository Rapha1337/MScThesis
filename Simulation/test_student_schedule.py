from __future__ import annotations

import random

from persona_wrappers import StudentHoursWrapper
from schedule_model_student import (
    YearPhase,
    generate_full_day_schedule,
    print_weekly_structure,
    validate_weekly_budget_consistency,
)


def main() -> None:
    student = StudentHoursWrapper(
        name="student_test",
        fitness_hours_week=6,
        social_hours_week=8,
        work_hours_week=5,
    )

    structure = student.generate_week(phase=YearPhase.SEMESTER, seed=37)
    print_weekly_structure(structure)

    week_schedules: dict[int, list] = {}
    for weekday in range(7):
        week_schedules[weekday] = generate_full_day_schedule(
            structure,
            weekday,
            rng=random.Random(100 + weekday),
        )

    consistency = validate_weekly_budget_consistency(structure, week_schedules)
    print("\nWeekly budget vs scheduled hours:")
    for item in consistency["summary"]:
        print(
            f"- {item['subtype']}: budget={item['budget_hours']}h, "
            f"scheduled={item['scheduled_hours']}h, "
            f"target_days={item['target_days']}, "
            f"actual_days={item['actual_days']}"
        )

    if consistency["warnings"]:
        print("\nWarnings:")
        for warning in consistency["warnings"]:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
