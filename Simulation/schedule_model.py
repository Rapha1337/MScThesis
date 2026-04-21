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
    start_hour: int
    end_hour: int
    activity_type: ActivityType
    flexibility: BlockFlexibility
    subtype: str | None = None
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0 <= self.weekday <= 6:
            raise ValueError("weekday must be between 0 and 6")
        if not 0 <= self.start_hour < 24:
            raise ValueError("start_hour must be in [0, 24)")
        if not 0 < self.end_hour <= 24:
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


@dataclass
class DayEpisode:
    hour: int
    activity_type: ActivityType
    flexibility: BlockFlexibility
    subtype: str | None = None


WEEKDAY_NAMES = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}


def hour_to_hhmm(hour: int) -> str:
    return f"{hour:02d}:00"


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


def print_full_day_schedule(full_day_schedule: list[DayEpisode], weekday: int) -> None:
    print(f"\nFull day schedule for {WEEKDAY_NAMES[weekday]}:")

    for ep in full_day_schedule:
        subtype = ep.subtype if ep.subtype is not None else "-"
        print(
            f"  - {ep.hour:02d}:00 | "
            f"{ep.activity_type.value} | "
            f"{ep.flexibility.value} | "
            f"subtype={subtype}"
        )


def has_time_conflict(
    existing_blocks: list[WeeklyBlockTemplate],
    candidate: WeeklyBlockTemplate,
) -> bool:
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
    kept_blocks: list[WeeklyBlockTemplate] = []

    for block in blocks:
        if block.subtype in removal_probs_by_subtype:
            p_remove = removal_probs_by_subtype[block.subtype]
            if rng.random() < p_remove:
                continue

        kept_blocks.append(block)

    return kept_blocks


def sample_time_in_window(
    time_window: tuple[int, int],
    duration_range: tuple[int, int],
    rng: random.Random,
) -> tuple[int, int]:
    window_start, window_end = time_window
    min_duration, max_duration = duration_range

    duration = rng.randint(min_duration, max_duration)
    latest_start = window_end - duration

    if latest_start < window_start:
        raise ValueError("Time window too small for requested duration range.")

    start = rng.randint(window_start, latest_start)
    end = start + duration
    return start, end


def sample_flexible_block_from_rule(
    rule: dict,
    existing_blocks: list[WeeklyBlockTemplate],
    rng: random.Random,
    max_attempts: int = 20,
) -> WeeklyBlockTemplate | None:
    per_sample_probability = rule.get(
        "per_sample_probability",
        rule.get("probability", 1.0),
    )

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


def _expand_blocks_to_hourly_episodes(
    weekly_structure: WeeklyStructure,
    weekday: int,
) -> list[DayEpisode]:
    blocks = weekly_structure.get_blocks_for_weekday(weekday)

    episodes: list[DayEpisode] = []

    for block in blocks:
        for hour in range(block.start_hour, block.end_hour):
            episodes.append(
                DayEpisode(
                    hour=hour,
                    activity_type=block.activity_type,
                    flexibility=block.flexibility,
                    subtype=block.subtype,
                )
            )

    episodes.sort(key=lambda ep: ep.hour)
    return episodes

def sample_sleep_schedule(
    phase: YearPhase,
    weekday: int,
    first_external_hour: int | None = None,
    rng: random.Random | None = None,
) -> tuple[int, int]:
    """
    Gibt (sleep_start, wake_hour) zurück.
    wake_hour wird an frühe externe Termine angepasst.
    """
    if rng is None:
        rng = random.Random()

    sleep_start = rng.choice([22, 23])
    is_weekend = weekday in [5, 6]

    if phase == YearPhase.HOLIDAY:
        base_wake_hour = rng.choice([8, 9])
    else:
        base_wake_hour = rng.choice([8, 9]) if is_weekend else 7

    wake_hour = base_wake_hour

    if first_external_hour is not None:
        # mindestens 1h vor commute_out und 2h vor erstem externen Block
        latest_reasonable_wake = max(5, first_external_hour - 2)
        wake_hour = min(wake_hour, latest_reasonable_wake)

    return sleep_start, wake_hour


def classify_default_downtime_subtype(
    hour: int,
    occupied_hours: set[int],
    wake_hour: int,
    sleep_start: int,
) -> str:
    """
    Vergibt sinnvollere Subtypen für automatisch gefüllte Downtime-Stunden.
    """
    later_occupied = [h for h in occupied_hours if h > hour]
    earlier_occupied = [h for h in occupied_hours if h < hour]

    # direkt nach dem Aufstehen
    if wake_hour <= hour < min(wake_hour + 2, sleep_start):
        return "morning_free_time"

    # direkt vor dem Schlafen
    if max(wake_hour, sleep_start - 2) <= hour < sleep_start:
        return "evening_wind_down"

    # zwischen zwei belegten Blöcken
    if earlier_occupied and later_occupied:
        return "between_blocks"

    # sonst offene freie Zeit
    return "open_time"

def is_external_activity(
    activity_type: ActivityType,
    subtype: str | None = None,
) -> bool:
    """
    Aktivitäten, für die wir vorerst einen Weg annehmen.

    Wichtige Annahme:
    - studying findet zuhause statt und erzeugt daher keinen commute
    """
    if activity_type == ActivityType.WORK and subtype == "studying":
        return False

    return activity_type in {
        ActivityType.WORK,
        ActivityType.PHYSICAL_ACTIVITY,
        ActivityType.SOCIAL_TIME,
        ActivityType.RANDOM_APPOINTMENT,
    }

def find_free_hour_in_window(
    schedule: list[DayEpisode | None],
    start_hour: int,
    end_hour: int,
) -> int | None:
    """
    Sucht die erste freie Stunde in [start_hour, end_hour).
    """
    for hour in range(start_hour, end_hour):
        if 0 <= hour < 24 and schedule[hour] is None:
            return hour
    return None

def insert_meals(
    schedule: list[DayEpisode | None],
    wake_hour: int,
) -> None:
    """
    Fügt breakfast, lunch und dinner in freie Slots ein.
    """
    # Breakfast: kurz nach wake_up
    breakfast_hour = find_free_hour_in_window(
        schedule,
        wake_hour + 1,
        min(wake_hour + 3, 24),
    )
    if breakfast_hour is not None:
        schedule[breakfast_hour] = DayEpisode(
            hour=breakfast_hour,
            activity_type=ActivityType.EAT,
            flexibility=BlockFlexibility.FIXED,
            subtype="breakfast",
        )

    # Lunch: etwas flexibler zwischen 12 und 15
    lunch_hour = find_free_hour_in_window(schedule, 12, 15)
    if lunch_hour is not None:
        schedule[lunch_hour] = DayEpisode(
            hour=lunch_hour,
            activity_type=ActivityType.EAT,
            flexibility=BlockFlexibility.FIXED,
            subtype="lunch",
        )

    # Dinner: abends
    dinner_hour = find_free_hour_in_window(schedule, 18, 21)
    if dinner_hour is not None:
        schedule[dinner_hour] = DayEpisode(
            hour=dinner_hour,
            activity_type=ActivityType.EAT,
            flexibility=BlockFlexibility.FIXED,
            subtype="dinner",
        )

def insert_commutes(
    schedule: list[DayEpisode | None],
) -> None:
    """
    Fügt eine einfache Pendellogik ein:
    - eine Stunde vor dem ersten externen Block: commute_out
    - eine Stunde nach dem letzten externen Block: commute_home
    Nur wenn die Stunde frei ist.
    """
    occupied_external_hours = [
        ep.hour
        for ep in schedule
        if ep is not None and is_external_activity(ep.activity_type, ep.subtype)
    ]

    if not occupied_external_hours:
        return

    first_external_hour = min(occupied_external_hours)
    last_external_hour = max(occupied_external_hours)

    commute_out_hour = first_external_hour - 1
    if 0 <= commute_out_hour < 24 and schedule[commute_out_hour] is None:
        schedule[commute_out_hour] = DayEpisode(
            hour=commute_out_hour,
            activity_type=ActivityType.COMMUTE,
            flexibility=BlockFlexibility.FIXED,
            subtype="commute_out",
        )

    commute_home_hour = last_external_hour + 1
    if 0 <= commute_home_hour < 24 and schedule[commute_home_hour] is None:
        schedule[commute_home_hour] = DayEpisode(
            hour=commute_home_hour,
            activity_type=ActivityType.COMMUTE,
            flexibility=BlockFlexibility.FIXED,
            subtype="commute_home",
        )

def generate_full_day_schedule(
    weekly_structure: WeeklyStructure,
    weekday: int,
    rng: random.Random | None = None,
) -> list[DayEpisode]:
    """
    Erzeugt einen vollständigen 24h-Tagesplan.

    Reihenfolge:
    1) bestehende Wochenblöcke
    2) Schlaf
    3) Wake-up
    4) Commute
    5) Meals
    6) übrige freie Stunden als Downtime
    """
    if rng is None:
        rng = random.Random()

    hourly_episodes = _expand_blocks_to_hourly_episodes(weekly_structure, weekday)

    external_hours = sorted(
        ep.hour
        for ep in hourly_episodes
        if is_external_activity(ep.activity_type, ep.subtype)
    )
    first_external_hour = external_hours[0] if external_hours else None

    sleep_start, wake_hour = sample_sleep_schedule(
        phase=weekly_structure.phase,
        weekday=weekday,
        first_external_hour=first_external_hour,
        rng=rng,
    )

    schedule: list[DayEpisode | None] = [None] * 24

    # 1) Vorhandene Episoden eintragen
    for ep in hourly_episodes:
        schedule[ep.hour] = ep

    # 2) Schlafstunden eintragen
    sleep_hours = list(range(sleep_start, 24)) + list(range(0, wake_hour))
    for hour in sleep_hours:
        if schedule[hour] is None:
            schedule[hour] = DayEpisode(
                hour=hour,
                activity_type=ActivityType.SLEEP,
                flexibility=BlockFlexibility.FIXED,
                subtype="night_sleep",
            )

    # 3) Wake-up eintragen
    if 0 <= wake_hour < 24 and schedule[wake_hour] is None:
        schedule[wake_hour] = DayEpisode(
            hour=wake_hour,
            activity_type=ActivityType.WAKE_UP,
            flexibility=BlockFlexibility.FIXED,
            subtype="morning_wake_up",
        )

    # 4) Commutes zuerst
    insert_commutes(schedule)

    # 5) Danach Meals
    insert_meals(schedule, wake_hour)

    # 6) Restliche Lücken mit sinnvoller Downtime füllen
    occupied_hours = {ep.hour for ep in hourly_episodes}

    for hour in range(24):
        if schedule[hour] is None:
            subtype = classify_default_downtime_subtype(
                hour=hour,
                occupied_hours=occupied_hours,
                wake_hour=wake_hour,
                sleep_start=sleep_start,
            )

            schedule[hour] = DayEpisode(
                hour=hour,
                activity_type=ActivityType.DOWNTIME,
                flexibility=BlockFlexibility.FLEXIBLE,
                subtype=subtype,
            )

    return [ep for ep in schedule if ep is not None]


# ============================================================
# Basis-Wochenstruktur
# ============================================================

student_me_base = WeeklyStructure(
    persona_name="student_me",
    phase=YearPhase.SEMESTER,
)

student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=0,
        start_hour=8,
        end_hour=16,
        activity_type=ActivityType.WORK,
        flexibility=BlockFlexibility.FIXED,
        subtype="university",
    )
)

student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=1,
        start_hour=9,
        end_hour=12,
        activity_type=ActivityType.WORK,
        flexibility=BlockFlexibility.FIXED,
        subtype="assistant_job",
    )
)
student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=1,
        start_hour=13,
        end_hour=15,
        activity_type=ActivityType.PHYSICAL_ACTIVITY,
        flexibility=BlockFlexibility.FIXED,
        subtype="gym",
    )
)
student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=1,
        start_hour=16,
        end_hour=18,
        activity_type=ActivityType.WORK,
        flexibility=BlockFlexibility.FIXED,
        subtype="assistant_job",
    )
)

student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=2,
        start_hour=13,
        end_hour=15,
        activity_type=ActivityType.PHYSICAL_ACTIVITY,
        flexibility=BlockFlexibility.FIXED,
        subtype="gym",
    )
)

student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=3,
        start_hour=9,
        end_hour=12,
        activity_type=ActivityType.WORK,
        flexibility=BlockFlexibility.FIXED,
        subtype="assistant_job",
    )
)
student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=3,
        start_hour=13,
        end_hour=15,
        activity_type=ActivityType.PHYSICAL_ACTIVITY,
        flexibility=BlockFlexibility.FIXED,
        subtype="gym",
    )
)
student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=3,
        start_hour=16,
        end_hour=18,
        activity_type=ActivityType.WORK,
        flexibility=BlockFlexibility.FIXED,
        subtype="assistant_job",
    )
)

student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=4,
        start_hour=7,
        end_hour=9,
        activity_type=ActivityType.PHYSICAL_ACTIVITY,
        flexibility=BlockFlexibility.FIXED,
        subtype="training",
    )
)
student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=4,
        start_hour=9,
        end_hour=17,
        activity_type=ActivityType.WORK,
        flexibility=BlockFlexibility.FIXED,
        subtype="fitness_coach",
    )
)

student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=5,
        start_hour=13,
        end_hour=15,
        activity_type=ActivityType.PHYSICAL_ACTIVITY,
        flexibility=BlockFlexibility.FIXED,
        subtype="gym",
    )
)

student_me_base.add_block(
    WeeklyBlockTemplate(
        weekday=6,
        start_hour=12,
        end_hour=14,
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
                "time_window": (18, 23),
                "duration_range": (1, 3),
            },
            {
                "activity_type": ActivityType.RANDOM_APPOINTMENT,
                "subtype": "appointment",
                "n_samples_range": (0, 2),
                "per_sample_probability": 0.5,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "time_window": (8, 18),
                "duration_range": (1, 2),
            },
            {
                "activity_type": ActivityType.DOWNTIME,
                "subtype": "passive_recovery",
                "n_samples_range": (0, 2),
                "per_sample_probability": 0.5,
                "allowed_weekdays": [5, 6],
                "time_window": (14, 20),
                "duration_range": (1, 3),
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
                "time_window": (9, 17),
                "duration_range": (2, 4),
            },
            {
                "activity_type": ActivityType.SOCIAL_TIME,
                "subtype": "reduced_social",
                "n_samples_range": (0, 1),
                "per_sample_probability": 0.3,
                "allowed_weekdays": [5, 6],
                "time_window": (18, 22),
                "duration_range": (1, 2),
            },
            {
                "activity_type": ActivityType.DOWNTIME,
                "subtype": "exam_recovery",
                "n_samples_range": (0, 2),
                "per_sample_probability": 0.5,
                "allowed_weekdays": [5, 6],
                "time_window": (14, 20),
                "duration_range": (1, 2),
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
                "time_window": (12, 20),
                "duration_range": (1, 3),
            },
            {
                "activity_type": ActivityType.SOCIAL_TIME,
                "subtype": "holiday_social",
                "n_samples_range": (1, 3),
                "per_sample_probability": 0.75,
                "allowed_weekdays": [3, 4, 5, 6],
                "time_window": (17, 23),
                "duration_range": (2, 4),
            },
            {
                "activity_type": ActivityType.RANDOM_APPOINTMENT,
                "subtype": "errand_or_visit",
                "n_samples_range": (0, 2),
                "per_sample_probability": 0.5,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "time_window": (10, 17),
                "duration_range": (1, 2),
            },
        ],
    },
}


def generate_weekly_structure_for_phase(
    base_structure: WeeklyStructure,
    phase: YearPhase,
    rng: random.Random | None = None,
) -> WeeklyStructure:
    if rng is None:
        rng = random.Random()

    structure = deepcopy(base_structure)
    structure.phase = phase

    phase_rules = PHASE_RULES[phase]

    structure.blocks = remove_blocks_by_probability(
        blocks=structure.blocks,
        removal_probs_by_subtype=phase_rules["removal_probs_by_subtype"],
        rng=rng,
    )

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

if __name__ == "__main__":
    for phase in [YearPhase.SEMESTER, YearPhase.EXAM_PHASE, YearPhase.HOLIDAY]:
        print(f"\n=== {phase.value.upper()} FULL DAY SCHEDULES ===")

        structure = generate_weekly_structure_for_phase(
            student_me_base,
            phase,
            rng=random.Random(random.randint(0, 10000)),
        )

        for weekday in range(7):
            full_day = generate_full_day_schedule(
                structure,
                weekday,
                rng=random.Random(random.randint(0, 10000)),
            )
            print_full_day_schedule(full_day, weekday)