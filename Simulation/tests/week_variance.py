from __future__ import annotations

from itertools import combinations
from statistics import mean, pstdev
from typing import Any
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))


def _get_episode_value(ep: Any, key: str) -> Any:
    if isinstance(ep, dict):
        return ep.get(key)
    return getattr(ep, key)


def week_to_7x24_activity_grid(week_structure: Any) -> list[list[str]]:
    """Normalize supported weekly structures to a Monday-Sunday 7x24 activity grid."""
    if (
        isinstance(week_structure, list)
        and len(week_structure) == 7
        and all(isinstance(day, list) and len(day) == 24 for day in week_structure)
    ):
        return [[str(slot) for slot in day] for day in week_structure]

    if isinstance(week_structure, dict) and set(week_structure.keys()) >= set(range(7)):
        grid: list[list[str]] = []

        for weekday in range(7):
            slots = ["unknown"] * 24

            for ep in week_structure[weekday]:
                hour = int(_get_episode_value(ep, "hour"))
                activity = _get_episode_value(ep, "activity_type")
                activity_value = getattr(activity, "value", activity)
                slots[hour] = str(activity_value)

            grid.append(slots)

        return grid

    raise ValueError("Unsupported week structure format for 7x24 normalization")


def compare_week_structures(week_a: Any, week_b: Any) -> dict[str, float | int]:
    grid_a = week_to_7x24_activity_grid(week_a)
    grid_b = week_to_7x24_activity_grid(week_b)
    total_slots = 7 * 24
    matching_slots = sum(1 for d in range(7) for h in range(24) if grid_a[d][h] == grid_b[d][h])
    similarity = matching_slots / total_slots
    variance = 1.0 - similarity
    return {
        "matching_slots": matching_slots,
        "total_slots": total_slots,
        "similarity": similarity,
        "variance": variance,
        "similarity_percent": similarity * 100.0,
        "variance_percent": variance * 100.0,
    }


def summarize_pairwise_week_variance(weeks: list[Any]) -> dict[str, float | int]:
    pair_results = [compare_week_structures(a, b) for a, b in combinations(weeks, 2)]
    similarities = [x["similarity_percent"] for x in pair_results] if pair_results else [100.0]
    variances = [x["variance_percent"] for x in pair_results] if pair_results else [0.0]
    return {
        "n_weeks": len(weeks),
        "n_pairwise_comparisons": len(pair_results),
        "mean_similarity_percent": mean(similarities),
        "mean_variance_percent": mean(variances),
        "min_similarity_percent": min(similarities),
        "max_similarity_percent": max(similarities),
        "std_similarity_percent": pstdev(similarities) if len(similarities) > 1 else 0.0,
        "std_variance_percent": pstdev(variances) if len(variances) > 1 else 0.0,
    }


def _print_summary(title: str, summary: dict[str, float | int]) -> None:
    print(f"\n{title}")
    print("-" * len(title))

    for key, value in summary.items():
        if isinstance(value, float):
            print(f"{key}: {value:.2f}")
        else:
            print(f"{key}: {value}")


def _generate_student_week(
    *,
    persona_seed: int,
    phase: str = "normal",
    week_index: int = 1,
    fitness_hours_week: float = 5.5,
    social_hours_week: float = 10.0,
    work_hours_week: float = 4.5,
) -> dict[int, list[object]]:
    """
    Generate one realised 7-day student week as weekday -> list[DayEpisode].

    week_index is used as deterministic seed offset because the current
    generator API does not yet expose a real calendar-week parameter.
    """

    import random

    from persona_wrappers import StudentHoursWrapper
    from schedule_model_student import YearPhase, generate_full_day_schedule

    phase_value = YearPhase.coerce(phase)

    student = StudentHoursWrapper(
        name="student_variance_demo",
        fitness_hours_week=fitness_hours_week,
        social_hours_week=social_hours_week,
        work_hours_week=work_hours_week,
    )

    effective_week_seed = persona_seed + week_index * 10_000

    weekly_structure = student.generate_week(
        phase=phase_value,
        seed=effective_week_seed,
    )

    full_week: dict[int, list[object]] = {}

    for weekday in range(7):
        day_seed = effective_week_seed + weekday
        day_rng = random.Random(day_seed)
        full_day = generate_full_day_schedule(
            weekly_structure,
            weekday,
            rng=day_rng,
        )
        full_week[weekday] = full_day

    return full_week


def generate_student_year(
    *,
    persona_seed: int,
    phase: str,
    week_indices: list[int],
) -> list[list[list[str]]]:
    """
    Generate a simulated year as a list of 7x24 week grids.

    With 52 week_indices, the result contains 52 weekly grids.
    """

    year_grids: list[list[list[str]]] = []

    for week_index in week_indices:
        week = _generate_student_week(
            persona_seed=persona_seed,
            phase=phase,
            week_index=week_index,
        )
        year_grids.append(week_to_7x24_activity_grid(week))

    return year_grids




def _event_active_on_day(event: object, week_index: int, weekday: int) -> bool:
    start_abs = int(getattr(event, "start_week")) * 7 + int(getattr(event, "start_day"))
    day_abs = week_index * 7 + weekday
    return start_abs <= day_abs < start_abs + int(getattr(event, "duration_days"))


def _apply_public_holiday_to_day(day_schedule: list[object]) -> list[object]:
    from schedule_model_student import ActivityType, DayEpisode

    adjusted: list[object] = []
    for ep in day_schedule:
        if ep.activity_type == ActivityType.WORK and ep.subtype in {"university", "paid_work", "studying"}:
            adjusted.append(DayEpisode(ep.hour, ActivityType.DOWNTIME, ep.flexibility, "public_holiday"))
        else:
            adjusted.append(ep)
    return adjusted
def generate_realistic_student_year(
    *,
    persona_seed: int,
    year_seed: int | None = None,
    fitness_hours_week: float = 5.5,
    social_hours_week: float = 10.0,
    work_hours_week: float = 4.5,
    n_weeks: int = 52,
) -> dict[str, object]:
    """Generate one realistic student year with mixed phases and sampled events."""
    import random

    from persona_wrappers import StudentHoursWrapper
    from schedule_model_student import YearPhase, generate_full_day_schedule
    from year_structure import YearStructureGenerator

    effective_year_seed = persona_seed if year_seed is None else year_seed
    student = StudentHoursWrapper(
        name="student_realistic_year",
        fitness_hours_week=fitness_hours_week,
        social_hours_week=social_hours_week,
        work_hours_week=work_hours_week,
    )
    generator = YearStructureGenerator()
    year_structure = generator.generate_year(
        persona_id=student.name,
        persona_seed=effective_year_seed,
        parameters=student,
        n_weeks=n_weeks,
    )

    year_grids: list[list[list[str]]] = []
    for week_plan in year_structure.weeks:
        phase_value = YearPhase.coerce(week_plan.phase)
        week_seed = persona_seed + week_plan.week_index * 10_000 + effective_year_seed
        weekly_structure = student.generate_week(phase=phase_value, seed=week_seed)

        full_week: dict[int, list[object]] = {}
        for weekday in range(7):
            day_rng = random.Random(week_seed + weekday)
            active_events = [
                event for event in year_structure.events if _event_active_on_day(event, week_plan.week_index, weekday)
            ]
            illness_constraints = []
            has_public_holiday = False
            for event in active_events:
                if event.event_type == "illness":
                    from constraints.illness import AcuteIllnessConstraint

                    intensity = "mid" if event.intensity == "medium" else str(event.intensity or "low")
                    illness_constraints.append(
                        AcuteIllnessConstraint(
                            duration_days=1,
                            start_weekday=weekday,
                            intensity=intensity,
                        )
                    )
                elif event.event_type == "public_holiday":
                    has_public_holiday = True

            full_day = generate_full_day_schedule(
                weekly_structure,
                weekday,
                rng=day_rng,
                constraints=illness_constraints or None,
            )
            if has_public_holiday:
                full_day = _apply_public_holiday_to_day(full_day)
            full_week[weekday] = full_day
        year_grids.append(week_to_7x24_activity_grid(full_week))

    return {
        "year_grids": year_grids,
        "year_structure": year_structure,
        "phase_counts": dict(year_structure.phase_counts),
        "block_counts": dict(year_structure.metadata.get("block_counts", {})),
        "public_holiday_count": sum(1 for event in year_structure.events if event.event_type == "public_holiday"),
        "illness_event_count": sum(1 for event in year_structure.events if event.event_type == "illness"),
    }


def compare_year_structures(
    year_a: list[list[list[str]]],
    year_b: list[list[list[str]]],
) -> dict[str, float | int]:
    """
    Compare two simulated years.

    A year consists of multiple 7x24 week grids.
    With 52 weeks, total slots = 52 * 7 * 24 = 8736.
    """

    if len(year_a) != len(year_b):
        raise ValueError("Both years must contain the same number of weeks.")

    total_slots = len(year_a) * 7 * 24
    matching_slots = 0

    for week_idx in range(len(year_a)):
        for day_idx in range(7):
            for hour_idx in range(24):
                if year_a[week_idx][day_idx][hour_idx] == year_b[week_idx][day_idx][hour_idx]:
                    matching_slots += 1

    similarity = matching_slots / total_slots
    variance = 1.0 - similarity

    return {
        "matching_slots": matching_slots,
        "total_slots": total_slots,
        "similarity": similarity,
        "variance": variance,
        "similarity_percent": similarity * 100.0,
        "variance_percent": variance * 100.0,
    }


def summarize_pairwise_year_variance(
    years: list[list[list[list[str]]]],
) -> dict[str, float | int]:
    """Pairwise comparison summary for multiple simulated years."""

    pair_results = [
        compare_year_structures(year_a, year_b)
        for year_a, year_b in combinations(years, 2)
    ]

    similarities = [x["similarity_percent"] for x in pair_results] if pair_results else [100.0]
    variances = [x["variance_percent"] for x in pair_results] if pair_results else [0.0]

    return {
        "n_years": len(years),
        "n_pairwise_comparisons": len(pair_results),
        "mean_similarity_percent": mean(similarities),
        "mean_variance_percent": mean(variances),
        "min_similarity_percent": min(similarities),
        "max_similarity_percent": max(similarities),
        "std_similarity_percent": pstdev(similarities) if len(similarities) > 1 else 0.0,
        "std_variance_percent": pstdev(variances) if len(variances) > 1 else 0.0,
    }


def run_between_seed_year_variance(
    *,
    n_personas: int = 200,
    base_seed: int = 123,
    phase: str = "normal",
    week_indices: list[int] | None = None,
) -> dict[str, float | int]:
    """
    Between-seed year variance:
    Same parameters and phase, but different persona seeds.
    Each persona is represented by 52 simulated weeks.
    """

    import random

    if week_indices is None:
        week_indices = list(range(1, 53))

    rng = random.Random(base_seed)
    persona_seeds = [rng.randint(0, 2**31 - 1) for _ in range(n_personas)]

    years = [
        generate_student_year(
            persona_seed=persona_seed,
            phase=phase,
            week_indices=week_indices,
        )
        for persona_seed in persona_seeds
    ]

    summary = summarize_pairwise_year_variance(years)
    summary["n_personas"] = n_personas
    summary["n_weeks_per_persona"] = len(week_indices)
    summary["base_seed"] = base_seed
    return summary


def run_between_agent_realistic_year_variance(
    *,
    n_agents: int = 200,
    base_seed: int = 123,
    n_weeks: int = 52,
) -> dict[str, object]:
    """Between-agent variance for realistic mixed-phase years."""
    import random

    rng = random.Random(base_seed)
    agent_seeds = [rng.randint(0, 2**31 - 1) for _ in range(n_agents)]

    generated_years = [
        generate_realistic_student_year(persona_seed=seed, year_seed=seed, n_weeks=n_weeks)
        for seed in agent_seeds
    ]
    years = [x["year_grids"] for x in generated_years]
    phase_counts = [x["phase_counts"] for x in generated_years]
    block_counts = [x.get("block_counts", {}) for x in generated_years]
    public_holiday_counts = [int(x.get("public_holiday_count", 0)) for x in generated_years]
    illness_event_counts = [int(x["illness_event_count"]) for x in generated_years]

    summary = summarize_pairwise_year_variance(years)
    summary["n_agents"] = n_agents
    summary["n_weeks_per_agent"] = n_weeks
    summary["base_seed"] = base_seed
    summary["example_phase_counts"] = phase_counts[0] if phase_counts else {}
    summary["example_block_counts"] = block_counts[0] if block_counts else {}
    summary["example_public_holiday_count"] = public_holiday_counts[0] if public_holiday_counts else 0
    summary["example_illness_event_count"] = illness_event_counts[0] if illness_event_counts else 0
    summary["mean_public_holiday_count"] = mean(public_holiday_counts) if public_holiday_counts else 0.0
    summary["mean_illness_event_count"] = mean(illness_event_counts) if illness_event_counts else 0.0
    summary["max_illness_event_count"] = max(illness_event_counts) if illness_event_counts else 0
    return summary


def run_within_seed_week_variance(
    *,
    persona_seed: int = 12345,
    phase: str = "normal",
    week_indices: list[int] | None = None,
) -> dict[str, float | int]:
    """
    Within-seed week variance:
    Same persona seed and phase, but 52 different week indices.
    The 52 weeks are compared pairwise.
    """

    if week_indices is None:
        week_indices = list(range(1, 53))

    weeks = [
        _generate_student_week(
            persona_seed=persona_seed,
            phase=phase,
            week_index=week_index,
        )
        for week_index in week_indices
    ]

    summary = summarize_pairwise_week_variance(weeks)
    summary["persona_seed"] = persona_seed
    summary["n_week_indices"] = len(week_indices)
    return summary


def run_within_agent_realistic_year_variance(
    *,
    persona_seed: int = 12345,
    n_years: int = 20,
    base_year_seed: int = 222,
    n_weeks: int = 52,
) -> dict[str, object]:
    """Within-agent variance across multiple realistic year realizations."""
    import random

    rng = random.Random(base_year_seed)
    year_seeds = [rng.randint(0, 2**31 - 1) for _ in range(n_years)]
    generated_years = [
        generate_realistic_student_year(persona_seed=persona_seed, year_seed=ys, n_weeks=n_weeks)
        for ys in year_seeds
    ]
    years = [x["year_grids"] for x in generated_years]
    phase_counts = [x["phase_counts"] for x in generated_years]
    block_counts = [x.get("block_counts", {}) for x in generated_years]
    public_holiday_counts = [int(x.get("public_holiday_count", 0)) for x in generated_years]
    illness_event_counts = [int(x.get("illness_event_count", 0)) for x in generated_years]

    summary = summarize_pairwise_year_variance(years)
    summary["persona_seed"] = persona_seed
    summary["n_years"] = n_years
    summary["base_year_seed"] = base_year_seed
    summary["n_weeks_per_year"] = n_weeks
    summary["example_phase_counts"] = phase_counts[0] if phase_counts else {}
    summary["example_block_counts"] = block_counts[0] if block_counts else {}
    summary["example_public_holiday_count"] = public_holiday_counts[0] if public_holiday_counts else 0
    summary["example_illness_event_count"] = illness_event_counts[0] if illness_event_counts else 0
    summary["mean_public_holiday_count"] = mean(public_holiday_counts) if public_holiday_counts else 0.0
    summary["mean_illness_event_count"] = mean(illness_event_counts) if illness_event_counts else 0.0
    return summary


def main() -> None:
    print("YEAR-BASED WEEK VARIANCE DEMO")
    print("=============================")
    print("Comparing generated student structures by phase.")
    print("Between-seed: 200 personas, each with 52 weeks.")
    print("Within-seed: one persona, 52 weeks compared pairwise.")

    phases = ["normal", "high_stress", "holiday"]
    week_indices = list(range(1, 53))

    n_personas = 200
    between_base_seed = 123
    within_persona_seed = 12345

    print("\nCONFIGURATION")
    print("-------------")
    print(f"phases: {phases}")
    print(f"n_weeks: {len(week_indices)}")
    print(f"between_seed_n_personas: {n_personas}")

    for phase in phases:
        print(f"\n\nPHASE: {phase.upper()}")
        print("=" * (7 + len(phase)))

        between_summary = run_between_seed_year_variance(
            n_personas=n_personas,
            base_seed=between_base_seed,
            phase=phase,
            week_indices=week_indices,
        )
        _print_summary("BETWEEN-SEED YEAR VARIANCE", between_summary)

        within_summary = run_within_seed_week_variance(
            persona_seed=within_persona_seed,
            phase=phase,
            week_indices=week_indices,
        )
        _print_summary("WITHIN-SEED WEEK VARIANCE", within_summary)


if __name__ == "__main__":
    main()
