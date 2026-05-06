from __future__ import annotations

import random

from persona_wrappers import StudentHoursWrapper
from schedule_model_student import (
    YearPhase,
    generate_full_day_schedule,
    print_weekly_structure,
    validate_full_day_schedule,
    validate_weekly_structure,
)


def main() -> None:
    student = StudentHoursWrapper(
        name="student_test",
        fitness_hours_week=12,
        social_hours_week=4,
        work_hours_week=16,
    )

    for phase in [YearPhase.SEMESTER, YearPhase.EXAM_PHASE, YearPhase.HOLIDAY]:
        print(f"\n=== {phase.value} ===")
        structure = student.generate_week(phase=phase, seed=37)
        print_weekly_structure(structure)
        print("weekly_validation:", validate_weekly_structure(structure))

        for weekday in [0, 5]:  # Monday and Saturday
            schedule = generate_full_day_schedule(structure, weekday, rng=random.Random(100 + weekday))
            result = validate_full_day_schedule(schedule)
            print(f"day_validation weekday={weekday}:", result)


if __name__ == "__main__":
    main()
