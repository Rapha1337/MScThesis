from __future__ import annotations

from pathlib import Path
import sys

SIMULATION_DIR = Path(__file__).resolve().parents[1]
if str(SIMULATION_DIR) not in sys.path:
    sys.path.append(str(SIMULATION_DIR))

from persona_wrappers import StudentHoursWrapper, create_personas
from schedule_model_student import YearPhase


def print_persona_batch(title: str, personas: list[dict[str, object]]) -> None:
    print(f"\n{title}")
    print("-" * len(title))

    for persona in personas:
        wrapper = persona["wrapper"]
        weekly_structure = persona["weekly_structure"]

        print(f"Persona {persona['persona_index']}")
        print(f"  persona_seed: {persona['persona_seed']}")
        print(f"  phase: {persona['phase']}")
        print(f"  input_fitness_hours_week: {wrapper.fitness_hours_week}")
        print(f"  input_social_hours_week: {wrapper.social_hours_week}")
        print(f"  input_work_hours_week: {wrapper.work_hours_week}")
        print(f"  input_carework_hours_week: {wrapper.carework_hours_week}")
        print(f"  weekly_structure_persona_name: {weekly_structure.persona_name}")


def extract_persona_seeds(personas: list[dict[str, object]]) -> list[int]:
    return [int(persona["persona_seed"]) for persona in personas]


def main() -> None:
    print("STUDENT WRAPPER DEMO")
    print("====================")
    print("Demonstrating deterministic and reproducible student persona generation.")

    n_personas = 5
    phase = YearPhase.NORMAL

    student_parameters = StudentHoursWrapper(
        name="student_wrapper_demo",
        fitness_hours_week=5.5,
        social_hours_week=10.0,
        work_hours_week=4.5,
        carework_hours_week=7.0,
    )

    print("\nINPUT PARAMETERS")
    print("----------------")
    print(f"fitness_hours_week: {student_parameters.fitness_hours_week}")
    print(f"social_hours_week: {student_parameters.social_hours_week}")
    print(f"work_hours_week: {student_parameters.work_hours_week}")
    print(f"carework_hours_week: {student_parameters.carework_hours_week}")
    print(f"n_personas: {n_personas}")
    print(f"phase: {phase.value}")

    personas_seed_123_a = create_personas(
        n_personas=n_personas,
        base_seed=123,
        phase=phase,
        parameters=student_parameters,
    )

    personas_seed_123_b = create_personas(
        n_personas=n_personas,
        base_seed=123,
        phase=phase,
        parameters=student_parameters,
    )

    personas_seed_999 = create_personas(
        n_personas=n_personas,
        base_seed=999,
        phase=phase,
        parameters=student_parameters,
    )

    print_persona_batch("PERSONAS WITH BASE_SEED = 123", personas_seed_123_a)

    seeds_123_a = extract_persona_seeds(personas_seed_123_a)
    seeds_123_b = extract_persona_seeds(personas_seed_123_b)
    seeds_999 = extract_persona_seeds(personas_seed_999)

    print("\nREPRODUCIBILITY CHECK")
    print("---------------------")
    print(f"Seeds from first run with base_seed=123:  {seeds_123_a}")
    print(f"Seeds from second run with base_seed=123: {seeds_123_b}")
    print(f"Seeds from run with base_seed=999:        {seeds_999}")

    print("\nRESULT")
    print("------")
    print(f"Same base_seed produces identical persona seeds: {seeds_123_a == seeds_123_b}")
    print(f"Different base_seed produces different persona seeds: {seeds_123_a != seeds_999}")

    print("\nTAKE-AWAY")
    print("---------")
    print("Same inputs + same base_seed -> same personas.")
    print("Same inputs + different base_seed -> different personas.")
    print("n_personas controls how many reproducible personas are generated.")


if __name__ == "__main__":
    main()