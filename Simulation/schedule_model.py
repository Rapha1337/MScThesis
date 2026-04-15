from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
import random


class BlockFlexibility(str, Enum):
    FIXED = "fixed"
    FLEXIBLE = "flexible"


class ActivityType(str, Enum):
    WAKE_UP = "wake_up"
    EAT = "eat"
    COMMUTE = "commute"
    WORK = "work"
    DOWNTIME = "downtime"
    HOUSEHOLD = "household"
    CAREWORK = "carework"
    SLEEP = "sleep"
    PHYSICAL_ACTIVITY = "physical_activity"
    SOCIAL_TIME = "social_time"
    RANDOM_APPOINTMENT = "random_appointment"


class YearPhase(str, Enum):
    SEMESTER = "semester"
    EXAM_PHASE = "exam_phase"
    HOLIDAY = "holiday"


@dataclass
class WeeklyBlockTemplate:
    weekday: int
    start_hour: float
    end_hour: float
    activity_type: ActivityType
    flexibility: BlockFlexibility
    subtype: str | None = None
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0 <= self.weekday <= 6:
            raise ValueError("weekday must be between 0 and 6")
        if not 0.0 <= self.start_hour < 24.0:
            raise ValueError("start_hour must be in [0, 24)")
        if not 0.0 < self.end_hour <= 24.0:
            raise ValueError("end_hour must be in (0, 24]")
        if self.start_hour >= self.end_hour:
            raise ValueError("start_hour must be smaller than end_hour")


@dataclass
class WeeklyStructure:
    persona_name: str
    phase: YearPhase
    blocks: list[WeeklyBlockTemplate] = field(default_factory=list)

    def add_block(self, block: WeeklyBlockTemplate) -> None:
        self.blocks.append(block)

    def get_blocks_for_weekday(self, weekday: int) -> list[WeeklyBlockTemplate]:
        if not 0 <= weekday <= 6:
            raise ValueError("weekday must be between 0 and 6")
        day_blocks = [block for block in self.blocks if block.weekday == weekday]
        return sorted(day_blocks, key=lambda block: block.start_hour)

    def get_fixed_blocks(self, weekday: int) -> list[WeeklyBlockTemplate]:
        return [
            block
            for block in self.get_blocks_for_weekday(weekday)
            if block.flexibility == BlockFlexibility.FIXED
        ]

    def get_flexible_blocks(self, weekday: int) -> list[WeeklyBlockTemplate]:
        return [
            block
            for block in self.get_blocks_for_weekday(weekday)
            if block.flexibility == BlockFlexibility.FLEXIBLE
        ]


# ============================================================
# Hilfsfunktionen
# ============================================================

WEEKDAY_NAMES = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}


def hour_to_hhmm(hour: float) -> str:
    h = int(hour)
    m = int(round((hour - h) * 60))
    if m == 60:
        h += 1
        m = 0
    return f"{h:02d}:{m:02d}"


def print_weekly_structure(structure: WeeklyStructure) -> None:
    print(f"\nWeeklyStructure: {structure.persona_name} | phase={structure.phase.value}")

    for weekday in range(7):
        blocks = structure.get_blocks_for_weekday(weekday)
        print(f"\n{WEEKDAY_NAMES[weekday]}:")

        if not blocks:
            print("  - no blocks")
            continue

        for block in blocks:
            start = hour_to_hhmm(block.start_hour)
            end = hour_to_hhmm(block.end_hour)
            subtype = block.subtype if block.subtype is not None else "-"

            print(
                f"  - {start}-{end} | "
                f"{block.activity_type.value} | "
                f"{block.flexibility.value} | "
                f"subtype={subtype}"
            )


def has_time_conflict(
    existing_blocks: list[WeeklyBlockTemplate],
    candidate: WeeklyBlockTemplate,
) -> bool:
    """
    Prüft, ob ein Kandidat zeitlich mit bestehenden Blöcken kollidiert.
    Nur gleicher Wochentag ist relevant.
    """
    for block in existing_blocks:
        if block.weekday != candidate.weekday:
            continue

        overlaps = not (
            candidate.end_hour <= block.start_hour
            or candidate.start_hour >= block.end_hour
        )
        if overlaps:
            return True

    return False


def remove_blocks_by_probability(
    blocks: list[WeeklyBlockTemplate],
    removal_probs_by_subtype: dict[str, float],
    rng: random.Random,
) -> list[WeeklyBlockTemplate]:
    """
    Entfernt Blöcke anhand von subtype-spezifischen Wahrscheinlichkeiten.
    """
    kept_blocks: list[WeeklyBlockTemplate] = []

    for block in blocks:
        if block.subtype in removal_probs_by_subtype:
            p_remove = removal_probs_by_subtype[block.subtype]
            if rng.random() < p_remove:
                continue

        kept_blocks.append(block)

    return kept_blocks


def sample_time_in_window(
    time_window: tuple[float, float],
    duration_range: tuple[float, float],
    rng: random.Random,
    step_minutes: int = 15,
) -> tuple[float, float]:
    """
    Sampelt Start und Endzeit innerhalb eines erlaubten Zeitfensters.
    Zeiten werden auf ein Raster (z.B. 15 Minuten) gerundet.
    """
    window_start, window_end = time_window
    min_duration, max_duration = duration_range

    duration = rng.uniform(min_duration, max_duration)
    duration_steps = round((duration * 60) / step_minutes)
    duration = duration_steps * step_minutes / 60.0

    latest_start = window_end - duration
    if latest_start < window_start:
        raise ValueError("Time window too small for requested duration range.")

    start = rng.uniform(window_start, latest_start)
    start_steps = round((start * 60) / step_minutes)
    start = start_steps * step_minutes / 60.0

    end = start + duration
    return start, end


def sample_flexible_block_from_rule(
    rule: dict,
    existing_blocks: list[WeeklyBlockTemplate],
    rng: random.Random,
    max_attempts: int = 20,
) -> WeeklyBlockTemplate | None:
    """
    Versucht, aus einer Regel genau einen flexiblen Block zu sampeln,
    der nicht mit bestehenden Blöcken kollidiert.
    """
    per_sample_probability = rule.get("per_sample_probability", rule.get("probability", 1.0))

    if rng.random() >= per_sample_probability:
        return None

    for _ in range(max_attempts):
        weekday = rng.choice(rule["allowed_weekdays"])
        start_hour, end_hour = sample_time_in_window(
            time_window=rule["time_window"],
            duration_range=rule["duration_range"],
            rng=rng,
        )

        candidate = WeeklyBlockTemplate(
            weekday=weekday,
            start_hour=start_hour,
            end_hour=end_hour,
            activity_type=rule["activity_type"],
            flexibility=BlockFlexibility.FLEXIBLE,
            subtype=rule.get("subtype"),
            notes=rule.get("notes", []),
        )

        if not has_time_conflict(existing_blocks, candidate):
            return candidate

    return None

def sample_multiple_flexible_blocks_from_rule(
    rule: dict,
    existing_blocks: list[WeeklyBlockTemplate],
    rng: random.Random,
) -> list[WeeklyBlockTemplate]:
    """
    Sampelt mehrere flexible Blöcke aus einer Regel.
    Die Anzahl wird über n_samples_range gesteuert.
    """
    n_min, n_max = rule.get("n_samples_range", (1, 1))
    n_samples = rng.randint(n_min, n_max)

    sampled_blocks: list[WeeklyBlockTemplate] = []

    for _ in range(n_samples):
        block = sample_flexible_block_from_rule(
            rule=rule,
            existing_blocks=existing_blocks + sampled_blocks,
            rng=rng,
        )

        if block is not None:
            sampled_blocks.append(block)

    return sampled_blocks


# ============================================================
# Basis-Wochenstruktur
# ============================================================

student_me_base = WeeklyStructure(
    persona_name="student_me",
    phase=YearPhase.SEMESTER,
)

# Monday
student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=0,
        start_hour=8.0,
        end_hour=16.25,
        activity_type=ActivityType.WORK,
        flexibility=BlockFlexibility.FIXED,
        subtype="university",
    )
)

# Tuesday
student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=1,
        start_hour=9.0,
        end_hour=12.0,
        activity_type=ActivityType.WORK,
        flexibility=BlockFlexibility.FIXED,
        subtype="assistant_job",
    )
)
student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=1,
        start_hour=13.0,
        end_hour=15.25,
        activity_type=ActivityType.PHYSICAL_ACTIVITY,
        flexibility=BlockFlexibility.FIXED,
        subtype="gym",
    )
)
student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=1,
        start_hour=16.0,
        end_hour=18.0,
        activity_type=ActivityType.WORK,
        flexibility=BlockFlexibility.FIXED,
        subtype="assistant_job",
    )
)

# Wednesday
student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=2,
        start_hour=13.0,
        end_hour=15.25,
        activity_type=ActivityType.PHYSICAL_ACTIVITY,
        flexibility=BlockFlexibility.FIXED,
        subtype="gym",
    )
)

# Thursday
student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=3,
        start_hour=9.0,
        end_hour=12.0,
        activity_type=ActivityType.WORK,
        flexibility=BlockFlexibility.FIXED,
        subtype="assistant_job",
    )
)
student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=3,
        start_hour=13.0,
        end_hour=15.25,
        activity_type=ActivityType.PHYSICAL_ACTIVITY,
        flexibility=BlockFlexibility.FIXED,
        subtype="gym",
    )
)
student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=3,
        start_hour=16.0,
        end_hour=18.0,
        activity_type=ActivityType.WORK,
        flexibility=BlockFlexibility.FIXED,
        subtype="assistant_job",
    )
)

# Friday
student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=4,
        start_hour=7.0,
        end_hour=9.0,
        activity_type=ActivityType.PHYSICAL_ACTIVITY,
        flexibility=BlockFlexibility.FIXED,
        subtype="training",
    )
)
student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=4,
        start_hour=9.0,
        end_hour=17.0,
        activity_type=ActivityType.WORK,
        flexibility=BlockFlexibility.FIXED,
        subtype="fitness_coach",
    )
)

# Saturday
student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=5,
        start_hour=13.0,
        end_hour=15.25,
        activity_type=ActivityType.PHYSICAL_ACTIVITY,
        flexibility=BlockFlexibility.FIXED,
        subtype="gym",
    )
)

# Sunday
student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=6,
        start_hour=12.0,
        end_hour=14.0,
        activity_type=ActivityType.PHYSICAL_ACTIVITY,
        flexibility=BlockFlexibility.FIXED,
        subtype="training",
    )
)


# ============================================================
# Phasenregeln
# ============================================================

PHASE_RULES = {
    YearPhase.SEMESTER: {
    "removal_probs_by_subtype": {},
    "flexible_additions": [
        {
            "activity_type": ActivityType.SOCIAL_TIME,
            "subtype": "evening_social",
            "n_samples_range": (0, 2),
            "per_sample_probability": 0.6,
            "allowed_weekdays": [4, 5, 6],
            "time_window": (18.0, 23.0),
            "duration_range": (1.5, 3.5),
        },
        {
            "activity_type": ActivityType.RANDOM_APPOINTMENT,
            "subtype": "appointment",
            "n_samples_range": (0, 2),
            "per_sample_probability": 0.5,
            "allowed_weekdays": [0, 1, 2, 3, 4],
            "time_window": (8.0, 18.0),
            "duration_range": (0.5, 1.5),
        },
        {
            "activity_type": ActivityType.DOWNTIME,
            "subtype": "passive_recovery",
            "n_samples_range": (0, 2),
            "per_sample_probability": 0.5,
            "allowed_weekdays": [5, 6],
            "time_window": (14.0, 20.0),
            "duration_range": (1.0, 2.5),
        },
    ],
},
    YearPhase.EXAM_PHASE: {
    "removal_probs_by_subtype": {
        "university": 1.0,
        "fitness_coach": 0.0,
    },
    "flexible_additions": [
        {
            "activity_type": ActivityType.WORK,
            "subtype": "studying",
            "n_samples_range": (2, 4),
            "per_sample_probability": 0.9,
            "allowed_weekdays": [0, 1, 2, 3, 4],
            "time_window": (9.0, 17.0),
            "duration_range": (2.0, 4.0),
        },
        {
            "activity_type": ActivityType.SOCIAL_TIME,
            "subtype": "reduced_social",
            "n_samples_range": (0, 1),
            "per_sample_probability": 0.3,
            "allowed_weekdays": [5, 6],
            "time_window": (18.0, 22.0),
            "duration_range": (1.0, 2.0),
        },
        {
            "activity_type": ActivityType.DOWNTIME,
            "subtype": "exam_recovery",
            "n_samples_range": (0, 2),
            "per_sample_probability": 0.5,
            "allowed_weekdays": [5, 6],
            "time_window": (14.0, 20.0),
            "duration_range": (1.0, 2.5),
        },
    ],
},
    YearPhase.HOLIDAY: {
    "removal_probs_by_subtype": {
        "university": 1.0,
        "assistant_job": 0.9,
    },
    "flexible_additions": [
        {
            "activity_type": ActivityType.DOWNTIME,
            "subtype": "free_time",
            "n_samples_range": (2, 4),
            "per_sample_probability": 0.85,
            "allowed_weekdays": [0, 1, 2, 3, 4, 5, 6],
            "time_window": (12.0, 20.0),
            "duration_range": (1.0, 3.0),
        },
        {
            "activity_type": ActivityType.SOCIAL_TIME,
            "subtype": "holiday_social",
            "n_samples_range": (1, 3),
            "per_sample_probability": 0.75,
            "allowed_weekdays": [3, 4, 5, 6],
            "time_window": (17.0, 23.0),
            "duration_range": (1.5, 4.0),
        },
        {
            "activity_type": ActivityType.RANDOM_APPOINTMENT,
            "subtype": "errand_or_visit",
            "n_samples_range": (0, 2),
            "per_sample_probability": 0.5,
            "allowed_weekdays": [0, 1, 2, 3, 4],
            "time_window": (10.0, 17.0),
            "duration_range": (0.5, 2.0),
        },
    ],
},
}


def generate_weekly_structure_for_phase(
    base_structure: WeeklyStructure,
    phase: YearPhase,
    rng: random.Random | None = None,
) -> WeeklyStructure:
    """
    Erzeugt aus einer Basis-Wochenstruktur eine konkrete Wochenstruktur
    für eine Jahresphase anhand von Regeln und Wahrscheinlichkeiten.
    """
    if rng is None:
        rng = random.Random()

    structure = deepcopy(base_structure)
    structure.phase = phase

    phase_rules = PHASE_RULES[phase]

    # 1. Bestehende Blöcke probabilistisch entfernen
    structure.blocks = remove_blocks_by_probability(
        blocks=structure.blocks,
        removal_probs_by_subtype=phase_rules["removal_probs_by_subtype"],
        rng=rng,
    )

    # 2. Zusätzliche flexible Blöcke sampeln
    existing_blocks = list(structure.blocks)

    for rule in phase_rules["flexible_additions"]:
        sampled_blocks = sample_multiple_flexible_blocks_from_rule(
            rule=rule,
            existing_blocks=existing_blocks,
            rng=rng,
        )

        for block in sampled_blocks:
            structure.add_block(block)
            existing_blocks.append(block)

    return structure


# ============================================================
# Beispiel
# ============================================================

if __name__ == "__main__":
    rng = random.Random(random.randint(0, 10000))

    print("\n--- BASE ---")
    print_weekly_structure(student_me_base)

    print("\n--- SEMESTER SAMPLE ---")
    semester_structure = generate_weekly_structure_for_phase(
        student_me_base,
        YearPhase.SEMESTER,
        rng=random.Random(random.randint(0, 10000)),
    )
    print_weekly_structure(semester_structure)

    print("\n--- EXAM SAMPLE ---")
    exam_structure = generate_weekly_structure_for_phase(
        student_me_base,
        YearPhase.EXAM_PHASE,
        rng=random.Random(random.randint(0, 10000)),
    )
    print_weekly_structure(exam_structure)

    print("\n--- HOLIDAY SAMPLE ---")
    holiday_structure = generate_weekly_structure_for_phase(
        student_me_base,
        YearPhase.HOLIDAY,
        rng=random.Random(random.randint(0, 10000)),
    )
    print_weekly_structure(holiday_structure)