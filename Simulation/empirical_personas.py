from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from persona_wrappers import StudentHoursWrapper
from schedule_model_student import (
    ActivityType,
    BlockFlexibility,
    StudentStructureParameters,
    WeeklyActivityBudget,
    WeeklyStructure,
    YearPhase,
    clamp,
)
from year_structure import YearStructureConfig


PSYCHOLOGICAL_COLUMN_MAP: dict[str, str] = {
    "automaticity": "automaticity",
    "pa_specific_self_control": "pa_specific_self_control",
    "action_planning": "action_planning",
    "intention": "intention",
    "perceived_behavioral_control": "perceived_behavioral_control",
    "attitude": "attitude_toward_the_behavior",
    "subjective_norm": "subjective_norm",
    "intrinsic_motivation": "intrinsic_motivation",
    "motivational_competence": "motivational_competence",
}


def _required_float(row: Mapping[str, str], key: str) -> float:
    raw = str(row.get(key, "")).strip()
    if raw == "":
        raise ValueError(f"Missing required value {key!r} in empirical persona row.")
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid numeric value for {key!r}: {raw!r}.") from exc


def _required_int(row: Mapping[str, str], key: str) -> int:
    value = _required_float(row, key)
    if not value.is_integer():
        raise ValueError(f"Expected integer value for {key!r}, got {value!r}.")
    return int(value)


def _bool_value(row: Mapping[str, str], key: str) -> bool:
    return str(row.get(key, "")).strip().lower() in {"true", "1", "yes"}


def _fractional_hours(value: float, rng: random.Random) -> int:
    """Represent fractional weekly hours without systematically rounding them away."""
    base = math.floor(max(0.0, float(value)))
    fraction = max(0.0, float(value)) - base
    return int(base + (1 if rng.random() < fraction else 0))


def _occupation_type(status: str, other: str) -> str:
    status_normalized = status.strip().lower()
    other_normalized = other.strip().lower()
    if status_normalized == "studium":
        return "student"
    if status_normalized in {"angestellt", "selbständig", "selbstaendig"}:
        return "employed"
    if status_normalized in {"arbeitslos", "pensioniert"}:
        return "non_employed"
    if status_normalized in {"ausbildung/lehre", "ausbildung", "lehre"}:
        return "training"
    if "stud" in other_normalized and any(token in other_normalized for token in ("job", "arbeit")):
        return "mixed_study_work"
    return "other"


@dataclass(frozen=True)
class EmpiricalPersonaProfile:
    cluster: int
    participant_id: str
    occupational_status: str
    occupational_status_other: str
    occupation_type: str
    workload_hours_per_week: float
    fitness_hours_week: float
    total_pa_hours_week: float
    holiday_weeks: int
    stress_weeks: int
    normal_weeks: int
    carework_hours_week: float
    social_hours_week: float
    workplace_distance_km: float
    indoor_activity_distance_km: float
    outdoor_activity_distance_km: float
    psychological_constructs: dict[str, float]
    observed_daily_routine: dict[str, float]

    @property
    def persona_id(self) -> str:
        return f"T1_Medoid_C{self.cluster}_{self.participant_id}"

    def to_wrapper(self) -> "EmpiricalPersonaWrapper":
        return EmpiricalPersonaWrapper(
            name=self.persona_id,
            profile=self,
            fitness_hours_week=self.fitness_hours_week,
            social_hours_week=self.social_hours_week,
            work_hours_week=self.workload_hours_per_week,
            carework_hours_week=self.carework_hours_week,
            workplace_distance_km=self.workplace_distance_km,
            indoor_activity_distance_km=self.indoor_activity_distance_km,
            outdoor_activity_distance_km=self.outdoor_activity_distance_km,
            seed_variation=False,
            variation_strength=0.0,
        )

    def metadata(self) -> dict[str, Any]:
        return {
            "source": "AIcoPA T1 primary PAM medoid",
            "cluster": self.cluster,
            "participant_id": self.participant_id,
            "occupational_status": self.occupational_status,
            "occupational_status_other": self.occupational_status_other or None,
            "occupation_type": self.occupation_type,
            "phase_weeks": {
                "normal": self.normal_weeks,
                "high_stress": self.stress_weeks,
                "holiday": self.holiday_weeks,
            },
            "reported_total_pa_hours_per_week": self.total_pa_hours_week,
            "observed_daily_routine_not_used_for_scheduling": dict(self.observed_daily_routine),
        }


@dataclass
class EmpiricalPersonaWrapper(StudentHoursWrapper):
    """Schedule wrapper for one observed T1 medoid profile."""

    profile: EmpiricalPersonaProfile | None = None

    def _profile(self) -> EmpiricalPersonaProfile:
        if self.profile is None:
            raise ValueError("EmpiricalPersonaWrapper requires an empirical profile.")
        return self.profile

    def _primary_subtype(self) -> str | None:
        occupation_type = self._profile().occupation_type
        if occupation_type == "student":
            return "university"
        if occupation_type == "mixed_study_work":
            return "mixed_study_work"
        if occupation_type == "training":
            return "school"
        if occupation_type == "employed":
            return "paid_work"
        if self.work_hours_week > 0:
            return "workplace"
        return None

    def to_structure_parameters(self, seed: int | None = None) -> StudentStructureParameters:
        del seed
        profile = self._profile()
        load = clamp(self.work_hours_week / 40.0)
        is_student = profile.occupation_type in {"student", "training", "mixed_study_work"}
        is_employed = profile.occupation_type in {"employed", "mixed_study_work"}
        return StudentStructureParameters(
            name=self.name,
            schedule_rigidity=clamp(0.45 + 0.45 * load),
            phase_variability=0.5,
            university_load=load if is_student else 0.0,
            employment_load=load if is_employed else 0.0,
            study_intensity=load if is_student else 0.0,
            sport_frequency=clamp(self.fitness_hours_week / 7.0),
            sport_fixedness=0.5,
            evening_flexibility=clamp(self.social_hours_week / 20.0),
            day_fragmentation=0.4,
            random_event_rate=0.18,
            commute_load=clamp(float(self.workplace_distance_km or 0.0) / 50.0),
            location_switch_frequency=0.2,
            weekend_structure=0.4,
            weekend_social_intensity=clamp(self.social_hours_week / 20.0),
            social_hours_week=self.social_hours_week,
            carework_hours_week=self.carework_hours_week,
        )

    def generate_week(self, phase: YearPhase, seed: int | None = None) -> WeeklyStructure:
        profile = self._profile()
        phase = YearPhase.coerce(phase)
        rng = random.Random(seed)
        structure = WeeklyStructure(
            persona_name=self.name,
            phase=phase,
            metadata={
                "empirical_profile": profile.metadata(),
                "input_fitness_hours_week": self.fitness_hours_week,
                "input_social_hours_week": self.social_hours_week,
                "input_work_hours_week": self.work_hours_week,
            },
        )

        primary_hours = 0 if phase == YearPhase.HOLIDAY else _fractional_hours(self.work_hours_week, rng)
        fitness_hours = _fractional_hours(self.fitness_hours_week, rng)
        social_hours = _fractional_hours(self.social_hours_week, rng)
        carework_hours = _fractional_hours(float(self.carework_hours_week or 0.0), rng)
        primary_subtype = self._primary_subtype()

        if primary_subtype is not None and primary_hours > 0:
            primary_target_days = min(5, max(1, math.ceil(primary_hours / 8)))
            primary_window = (8, 18) if primary_subtype == "paid_work" else (8, 20)
            structure.budgets.append(
                WeeklyActivityBudget(
                    ActivityType.WORK,
                    primary_subtype,
                    primary_hours,
                    primary_target_days,
                    BlockFlexibility.FIXED,
                    "weekday",
                    [0, 1, 2, 3, 4],
                    primary_window,
                    ["Empirical primary workload; omitted during holiday weeks."],
                )
            )

        if fitness_hours > 0:
            structure.budgets.append(
                WeeklyActivityBudget(
                    ActivityType.PHYSICAL_ACTIVITY,
                    "physical_activity",
                    fitness_hours,
                    min(7, max(1, math.ceil(fitness_hours / 2))),
                    BlockFlexibility.FLEXIBLE,
                    "mixed",
                    None,
                    (14, 21),
                    ["Empirical MVPA input."],
                )
            )
        if social_hours > 0:
            structure.budgets.append(
                WeeklyActivityBudget(
                    ActivityType.SOCIAL_TIME,
                    "social_time",
                    social_hours,
                    min(7, max(1, math.ceil(social_hours / 3))),
                    BlockFlexibility.FLEXIBLE,
                    "mixed",
                    None,
                    (10, 23),
                    ["Empirical social-hours input."],
                )
            )
        if carework_hours > 0:
            structure.budgets.append(
                WeeklyActivityBudget(
                    ActivityType.CAREWORK,
                    "carework",
                    carework_hours,
                    min(7, max(1, math.ceil(carework_hours / 2))),
                    BlockFlexibility.FLEXIBLE,
                    "mixed",
                    None,
                    (7, 22),
                    ["Empirical care-work input."],
                )
            )
        return structure

    def year_structure_config(self, n_weeks: int = 52) -> YearStructureConfig:
        profile = self._profile()
        if n_weeks != 52:
            raise ValueError("Empirical T1 phase counts currently require n_weeks=52.")
        return YearStructureConfig(
            n_weeks=n_weeks,
            strategy="empirical_phase_counts_v1_1",
            phase_target_ranges={
                "normal": (profile.normal_weeks, profile.normal_weeks),
                "high_stress": (profile.stress_weeks, profile.stress_weeks),
                "holiday": (profile.holiday_weeks, profile.holiday_weeks),
            },
            holiday_block_ranges={},
            holiday_block_placement_windows={},
            metadata={
                "source": "AIcoPA T1 medoid",
                "cluster": profile.cluster,
                "participant_id": profile.participant_id,
            },
        )


def load_empirical_personas(path: str | Path) -> list[EmpiricalPersonaProfile]:
    input_path = Path(path)
    if not input_path.is_file():
        raise FileNotFoundError(f"Empirical persona input file not found: {input_path}")

    with input_path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError(f"Empirical persona input file is empty: {input_path}")

    profiles: list[EmpiricalPersonaProfile] = []
    for row in rows:
        if not _bool_value(row, "complete_required_simulation_inputs"):
            raise ValueError(
                f"Participant {row.get('participant_id')!r} lacks required simulation inputs."
            )
        normal_weeks = _required_int(row, "normal_weeks_raw")
        stress_weeks = _required_int(row, "stress_weeks")
        holiday_weeks = _required_int(row, "holiday_weeks")
        if normal_weeks + stress_weeks + holiday_weeks != 52:
            raise ValueError(
                f"Phase weeks for participant {row.get('participant_id')!r} do not sum to 52."
            )

        constructs = {
            backend_name: _required_float(row, csv_name)
            for csv_name, backend_name in PSYCHOLOGICAL_COLUMN_MAP.items()
        }
        invalid_constructs = {
            name: value for name, value in constructs.items() if not 0.0 <= value <= 1.0
        }
        if invalid_constructs:
            raise ValueError(
                f"Psychological values must be normalized to [0, 1]: {invalid_constructs}"
            )

        status = str(row.get("occupational_status", "")).strip()
        other = str(row.get("occupational_status_other", "")).strip()
        profile = EmpiricalPersonaProfile(
            cluster=_required_int(row, "cluster"),
            participant_id=str(row.get("participant_id", "")).strip(),
            occupational_status=status,
            occupational_status_other=other,
            occupation_type=_occupation_type(status, other),
            workload_hours_per_week=_required_float(row, "workload_hours_per_week"),
            fitness_hours_week=_required_float(row, "pa_mvpa_hours_per_week"),
            total_pa_hours_week=_required_float(row, "pa_total_hours_per_week"),
            holiday_weeks=holiday_weeks,
            stress_weeks=stress_weeks,
            normal_weeks=normal_weeks,
            carework_hours_week=_required_float(row, "care_work_hours_per_week"),
            social_hours_week=_required_float(row, "social_hours_per_week"),
            workplace_distance_km=_required_float(row, "workplace_distance_km"),
            indoor_activity_distance_km=_required_float(row, "indoor_activity_distance_km"),
            outdoor_activity_distance_km=_required_float(row, "outdoor_activity_distance_km"),
            psychological_constructs=constructs,
            observed_daily_routine={
                key: _required_float(row, key)
                for key in (
                    "wake_time_minutes",
                    "work_start_time_minutes",
                    "work_end_time_minutes",
                    "break_duration_minutes",
                    "leisure_duration_minutes",
                    "bed_time_minutes",
                )
            },
        )
        profiles.append(profile)

    profiles.sort(key=lambda profile: profile.cluster)
    clusters = [profile.cluster for profile in profiles]
    if len(set(clusters)) != len(clusters):
        raise ValueError(f"Cluster identifiers must be unique, got {clusters!r}.")
    return profiles
