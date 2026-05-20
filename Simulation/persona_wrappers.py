from __future__ import annotations

from dataclasses import dataclass
import random

from schedule_model_student import (
    ActivityType,
    BlockFlexibility,
    StudentStructureParameters,
    WeeklyStructure,
    YearPhase,
    clamp,
    generate_student_week,
)


@dataclass
class StudentHoursWrapper:
    """
    Wrapper for student personas based on interpretable weekly hour parameters.

    This class does not replace StudentStructureParameters. Instead, it translates
    three high-level weekly-hour inputs into the existing abstract parameters used
    by schedule_model_student.py.

    Parameters
    ----------
    fitness_hours_week:
        Weekly hours for sport / physical activity.
    social_hours_week:
        Weekly hours for social contacts / social activities.
    work_hours_week:
        Weekly hours for paid work.

    University and studying are intentionally kept close to the existing
    StudentStructureParameters defaults. Small seed-based variation can be added
    so that different generated students are not identical while preserving the
    same overall ZVE-like baseline structure.
    """

    name: str = "student_generic"
    fitness_hours_week: float = 5.5
    social_hours_week: float = 10.0
    work_hours_week: float = 4.5
    carework_hours_week: float | None = None

    seed_variation: bool = True
    variation_strength: float = 0.06

    @classmethod
    def from_zve_student_generic(cls, name: str = "student_generic") -> "StudentHoursWrapper":
        """
        Create a generic student profile that approximately reproduces the
        existing ZVE-oriented default StudentStructureParameters.
        """
        return cls(
            name=name,
            fitness_hours_week=5.5,
            social_hours_week=10.0,
            work_hours_week=4.5,
        )

    def _rng(self, seed: int | None = None) -> random.Random:
        return random.Random(seed)

    def _jitter(
        self,
        value: float,
        rng: random.Random,
        lower: float = 0.0,
        upper: float = 1.0,
    ) -> float:
        if not self.seed_variation:
            return clamp(value, lower, upper)
        delta = rng.uniform(-self.variation_strength, self.variation_strength)
        return clamp(value + delta, lower, upper)

    def to_structure_parameters(self, seed: int | None = None) -> StudentStructureParameters:
        """
        Convert the hour-based wrapper into the existing StudentStructureParameters.

        The mapping is intentionally conservative:
        - fitness_hours_week mainly changes sport_frequency and sport_fixedness
        - social_hours_week mainly changes evening_flexibility and weekend_social_intensity
        - work_hours_week mainly changes employment_load and slightly increases schedule rigidity
        - university_load and study_intensity remain near the existing student baseline
        """
        rng = self._rng(seed)

        base = StudentStructureParameters(name=self.name)

        # Paid work only: 0-20 h/week maps to 0-1 employment load.
        employment_load = clamp(self.work_hours_week / 20.0)

        # Fitness: about 1.5 h per sport session, max ~7 sessions/week.
        estimated_sport_sessions = self.fitness_hours_week / 1.5
        sport_frequency = clamp(estimated_sport_sessions / 7.0)
        sport_fixedness = clamp(0.25 + 0.55 * clamp(self.fitness_hours_week / 10.0))

        # Social: 0-16 h/week maps from low to high social intensity.
        social_intensity = clamp(self.social_hours_week / 16.0)
        evening_flexibility = clamp(0.45 + 0.45 * social_intensity)
        weekend_social_intensity = clamp(0.35 + 0.60 * social_intensity)

        # More paid work makes the week slightly more rigid, but university/study
        # remain the core of the student structure.
        schedule_rigidity = clamp(base.schedule_rigidity + 0.12 * employment_load)
        day_fragmentation = clamp(base.day_fragmentation + 0.10 * employment_load)

        return StudentStructureParameters(
            name=self.name,
            schedule_rigidity=self._jitter(schedule_rigidity, rng),
            phase_variability=base.phase_variability,
            university_load=self._jitter(base.university_load, rng),
            employment_load=self._jitter(employment_load, rng),
            study_intensity=self._jitter(base.study_intensity, rng),
            sport_frequency=self._jitter(sport_frequency, rng),
            sport_fixedness=self._jitter(sport_fixedness, rng),
            evening_flexibility=self._jitter(evening_flexibility, rng),
            day_fragmentation=self._jitter(day_fragmentation, rng),
            random_event_rate=base.random_event_rate,
            commute_load=base.commute_load,
            location_switch_frequency=base.location_switch_frequency,
            weekend_structure=base.weekend_structure,
            weekend_social_intensity=self._jitter(weekend_social_intensity, rng),
            social_hours_week=self.social_hours_week,
            carework_hours_week=self.carework_hours_week,
        )

    def generate_week(
        self,
        phase: YearPhase,
        seed: int | None = None,
    ) -> WeeklyStructure:
        """
        Generate a weekly structure from the wrapper by first converting it into
        StudentStructureParameters and then using the existing generator.
        """
        params = self.to_structure_parameters(seed=seed)
        rng = self._rng(seed)
        structure = generate_student_week(params=params, phase=phase, rng=rng)
        direct_budget_hours = {
            "physical_activity": int(round(self.fitness_hours_week)),
            "social_time": int(round(self.social_hours_week)),
            "paid_work": int(round(self.work_hours_week)),
        }
        for budget in structure.budgets:
            if budget.subtype in direct_budget_hours:
                budget.total_hours = max(0, direct_budget_hours[budget.subtype])
                if budget.total_hours == 0:
                    budget.target_days = 0
        structure.metadata["input_fitness_hours_week"] = self.fitness_hours_week
        structure.metadata["input_social_hours_week"] = self.social_hours_week
        structure.metadata["input_work_hours_week"] = self.work_hours_week
        return structure

    def summary(self, seed: int | None = None) -> dict[str, object]:
        """Return both the hour inputs and the derived structure parameters."""
        derived = self.to_structure_parameters(seed=seed)
        return {
            "name": self.name,
            "hour_inputs": {
                "fitness_hours_week": self.fitness_hours_week,
                "social_hours_week": self.social_hours_week,
                "work_hours_week": self.work_hours_week,
                "carework_hours_week": self.carework_hours_week,
            },
            "derived_structure_parameters": {
                "schedule_rigidity": derived.schedule_rigidity,
                "phase_variability": derived.phase_variability,
                "university_load": derived.university_load,
                "employment_load": derived.employment_load,
                "study_intensity": derived.study_intensity,
                "sport_frequency": derived.sport_frequency,
                "sport_fixedness": derived.sport_fixedness,
                "evening_flexibility": derived.evening_flexibility,
                "day_fragmentation": derived.day_fragmentation,
                "random_event_rate": derived.random_event_rate,
                "commute_load": derived.commute_load,
                "location_switch_frequency": derived.location_switch_frequency,
                "weekend_structure": derived.weekend_structure,
                "weekend_social_intensity": derived.weekend_social_intensity,
            },
        }


@dataclass
class StudentWrapper:
    """Factory wrapper for deterministic persona generation with per-persona seeds."""

    parameters: StudentHoursWrapper
    base_seed: int = 123

    def create_personas(self, n_personas: int = 30, phase: YearPhase | str = YearPhase.NORMAL) -> list[dict[str, object]]:
        phase_value = YearPhase.coerce(phase)
        rng = random.Random(self.base_seed)
        personas: list[dict[str, object]] = []
        for idx in range(n_personas):
            persona_seed = rng.randint(0, 2**31 - 1)
            structure = self.parameters.generate_week(phase=phase_value, seed=persona_seed)
            personas.append(
                {
                    "persona_index": idx,
                    "persona_seed": persona_seed,
                    "phase": phase_value.value,
                    "wrapper": self.parameters,
                    "weekly_structure": structure,
                }
            )
        return personas


def create_personas(
    n_personas: int = 30,
    base_seed: int = 123,
    phase: YearPhase | str = YearPhase.NORMAL,
    parameters: StudentHoursWrapper | None = None,
) -> list[dict[str, object]]:
    """Backward-compatible convenience API for deterministic persona batches."""
    wrapper = StudentWrapper(parameters=parameters or StudentHoursWrapper.from_zve_student_generic(), base_seed=base_seed)
    return wrapper.create_personas(n_personas=n_personas, phase=phase)

if __name__ == "__main__":
    from schedule_model_student import (
        print_weekly_structure,
        generate_full_day_schedule,
        print_full_day_schedule,
        validate_full_day_schedule,
    )

    BASE_SEED = 37

    student = StudentHoursWrapper(
        name="carework_test_student",
        fitness_hours_week=6,
        social_hours_week=8,
        work_hours_week=5,
        carework_hours_week=7,
    )

    for phase in [YearPhase.NORMAL, YearPhase.HIGH_STRESS, YearPhase.HOLIDAY]:
        print(f"\n=== {student.name} | {phase.value.upper()} ===")

        structure = student.generate_week(
            phase=phase,
            seed=BASE_SEED,
        )

        print_weekly_structure(structure)

        for weekday in [0, 5]:
            day_rng = random.Random(BASE_SEED + weekday)
            full_day = generate_full_day_schedule(structure, weekday, rng=day_rng)
            print_full_day_schedule(full_day, weekday)
