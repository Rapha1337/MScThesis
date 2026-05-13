from __future__ import annotations

from pathlib import Path
import random
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from persona_wrappers import StudentHoursWrapper
from schedule_model_student import DayEpisode, WEEKDAY_NAMES, YearPhase, generate_full_day_schedule

PERSONA_NAME = "student_average"
FITNESS_HOURS_WEEK = 6
SOCIAL_HOURS_WEEK = 8
WORK_HOURS_WEEK = 5
CAREWORK_HOURS_WEEK = None
PHASE = YearPhase.SEMESTER
SEED_A = 34
SEED_B = 38


def episode_signature(ep: DayEpisode) -> tuple[str, str | None]:
    return ep.activity_type.value, ep.subtype


def generate_week_days(
    persona: StudentHoursWrapper,
    phase: YearPhase,
    seed: int,
) -> dict[int, list[DayEpisode]]:
    structure = persona.generate_week(phase=phase, seed=seed)
    week_days: dict[int, list[DayEpisode]] = {}

    for weekday in range(7):
        day_rng = random.Random(seed + 100 + weekday)
        day_schedule = generate_full_day_schedule(structure, weekday, rng=day_rng)
        assert len(day_schedule) == 24, f"{WEEKDAY_NAMES[weekday]} expected 24 slots"
        week_days[weekday] = sorted(day_schedule, key=lambda ep: ep.hour)

    return week_days


def compare_day_schedules(day_a: list[DayEpisode], day_b: list[DayEpisode]) -> dict[str, float | int]:
    assert len(day_a) == 24 and len(day_b) == 24, "Each day must have 24 hourly slots"

    differing_slots = 0
    for ep_a, ep_b in zip(day_a, day_b):
        if episode_signature(ep_a) != episode_signature(ep_b):
            differing_slots += 1

    same_slots = 24 - differing_slots
    percent_difference = (differing_slots / 24) * 100.0
    assert 0.0 <= percent_difference <= 100.0

    return {
        "total_slots": 24,
        "differing_slots": differing_slots,
        "same_slots": same_slots,
        "percent_difference": percent_difference,
    }


def compare_week_schedules(
    week_a: dict[int, list[DayEpisode]],
    week_b: dict[int, list[DayEpisode]],
) -> dict[str, object]:
    per_day: dict[int, dict[str, float | int]] = {}
    total_differing = 0

    for weekday in range(7):
        day_result = compare_day_schedules(week_a[weekday], week_b[weekday])
        per_day[weekday] = day_result
        total_differing += int(day_result["differing_slots"])

    total_slots = 7 * 24
    total_same = total_slots - total_differing
    weekly_percent = (total_differing / total_slots) * 100.0

    assert total_slots == 168, "Weekly comparison must cover 168 hourly slots"
    assert 0.0 <= weekly_percent <= 100.0

    return {
        "per_day": per_day,
        "total_slots": total_slots,
        "total_differing_slots": total_differing,
        "total_same_slots": total_same,
        "weekly_percent_difference": weekly_percent,
    }


def print_seed_variance_report(result: dict[str, object]) -> None:
    print("=== SEED VARIANCE ANALYSIS ===\n")
    print(f"Persona: {result['persona_name']}")
    print(f"Phase: {result['phase']}")
    print(f"Seed A: {result['seed_a']}")
    print(f"Seed B: {result['seed_b']}")
    print(f"Same input parameters: {result['same_input_parameters']}\n")

    print("Day-level variance:")
    per_day = result["per_day"]
    assert isinstance(per_day, dict)

    for weekday in range(7):
        day_data = per_day[weekday]
        print(
            f"{WEEKDAY_NAMES[weekday]}: {day_data['percent_difference']:.1f}% "
            f"({day_data['differing_slots']} / 24 different hourly slots)"
        )

    print("\nWeekly variance:")
    print(
        f"{result['weekly_percent_difference']:.1f}% "
        f"({result['total_differing_slots']} / {result['total_slots']} different hourly slots)"
    )
    print(f"Same hourly slots: {result['total_same_slots']} / {result['total_slots']}")


def run_seed_variance_analysis() -> dict[str, object]:
    persona_a = StudentHoursWrapper(
        name=PERSONA_NAME,
        fitness_hours_week=FITNESS_HOURS_WEEK,
        social_hours_week=SOCIAL_HOURS_WEEK,
        work_hours_week=WORK_HOURS_WEEK,
        carework_hours_week=CAREWORK_HOURS_WEEK,
    )
    persona_b = StudentHoursWrapper(
        name=PERSONA_NAME,
        fitness_hours_week=FITNESS_HOURS_WEEK,
        social_hours_week=SOCIAL_HOURS_WEEK,
        work_hours_week=WORK_HOURS_WEEK,
        carework_hours_week=CAREWORK_HOURS_WEEK,
    )

    week_a = generate_week_days(persona_a, PHASE, SEED_A)
    week_b = generate_week_days(persona_b, PHASE, SEED_B)
    comparison = compare_week_schedules(week_a, week_b)

    result = {
        "persona_name": PERSONA_NAME,
        "phase": PHASE.value,
        "seed_a": SEED_A,
        "seed_b": SEED_B,
        "same_input_parameters": True,
        **comparison,
    }

    print_seed_variance_report(result)

    same_seed_week_a = generate_week_days(persona_a, PHASE, SEED_A)
    same_seed_week_b = generate_week_days(persona_b, PHASE, SEED_A)
    same_seed_comparison = compare_week_schedules(same_seed_week_a, same_seed_week_b)
    assert same_seed_comparison["weekly_percent_difference"] == 0.0, (
        "Same-seed comparison should produce 0% variance"
    )

    result["same_seed_weekly_percent_difference"] = same_seed_comparison[
        "weekly_percent_difference"
    ]
    return result


if __name__ == "__main__":
    run_seed_variance_analysis()
