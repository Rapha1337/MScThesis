from __future__ import annotations

from pathlib import Path
import random
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from persona_wrappers import StudentHoursWrapper, create_personas
from schedule_model_student import YearPhase, generate_full_day_schedule
from week_variance import summarize_pairwise_week_variance


def generate_week_7x24(persona: StudentHoursWrapper, phase: YearPhase, seed: int, week_index: int = 0) -> list[list[str]]:
    """Generate one week as Monday-Sunday 7x24 activity grid.

    NOTE: The current generator API has no explicit calendar-week argument.
    For demo purposes, `week_index` is used as deterministic seed offset.
    """
    structure = persona.generate_week(phase=phase, seed=seed + (week_index * 10_000))
    grid: list[list[str]] = []

    for weekday in range(7):
        # deterministic day RNG; week_index offset enables within-seed week-to-week variation
        day_rng = random.Random(seed + 100 + weekday + (week_index * 1_000))
        day_schedule = generate_full_day_schedule(structure, weekday, rng=day_rng)
        day_schedule = sorted(day_schedule, key=lambda ep: ep.hour)
        grid.append([ep.activity_type.value for ep in day_schedule])

    return grid


def print_summary(title: str, summary: dict[str, float | int], *, n_personas: int | None = None, base_seed: int | None = None, phase: str | None = None) -> None:
    print(f"\n=== {title} ===")
    if n_personas is not None:
        print(f"Anzahl Personas: {n_personas}")
    if base_seed is not None:
        print(f"Verwendeter base_seed: {base_seed}")
    if phase is not None:
        print(f"Phase: {phase}")
    print(f"Anzahl pairwise comparisons: {summary['n_pairwise_comparisons']}")
    print(f"mean_similarity_percent: {summary['mean_similarity_percent']:.2f}")
    print(f"mean_variance_percent: {summary['mean_variance_percent']:.2f}")
    print(f"min_similarity_percent: {summary['min_similarity_percent']:.2f}")
    print(f"max_similarity_percent: {summary['max_similarity_percent']:.2f}")
    print(f"std_similarity_percent: {summary['std_similarity_percent']:.2f}")
    print(f"std_variance_percent: {summary['std_variance_percent']:.2f}")


def run_demo() -> None:
    # Parameter können hier einfach angepasst werden.
    base_seed = 123
    n_personas = 30
    phase = YearPhase.NORMAL

    student_parameters = StudentHoursWrapper.from_zve_student_generic(name="student_variance_demo")

    # A) Between-seed variance: 30 Personas, gleiche Parameter + Phase, unterschiedliche persona_seeds.
    personas = create_personas(
        n_personas=n_personas,
        base_seed=base_seed,
        phase=phase,
        parameters=student_parameters,
    )
    between_seed_weeks = [
        generate_week_7x24(student_parameters, phase, int(persona["persona_seed"]), week_index=0)
        for persona in personas
    ]
    between_summary = summarize_pairwise_week_variance(between_seed_weeks)

    print_summary(
        "Between-seed variance",
        between_summary,
        n_personas=n_personas,
        base_seed=base_seed,
        phase=phase.value,
    )

    # B) Within-seed variance: eine Persona, mehrere "Kalenderwochen" über week_index.
    persona_seed = int(personas[0]["persona_seed"])
    week_indices = [12, 13, 14, 15, 16]
    within_seed_weeks = [
        generate_week_7x24(student_parameters, phase, persona_seed, week_index=week_idx)
        for week_idx in week_indices
    ]
    within_summary = summarize_pairwise_week_variance(within_seed_weeks)

    print(f"\nWithin-seed Persona-Seed: {persona_seed}")
    print(f"Kalenderwochen (Demo-Index): {week_indices}")
    print_summary("Within-seed variance", within_summary, phase=phase.value)


if __name__ == "__main__":
    run_demo()
