from __future__ import annotations

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
    metadata: dict[str, object] = field(default_factory=dict)

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


@dataclass
class StudentStructureParameters:
    """
    Abstrahierte, numerische Strukturparameter für eine generische Student-Persona.
    Alle Werte liegen idealerweise im Bereich 0.0 bis 1.0.

    Die Parameter beschreiben nur Wochenstruktur und Kontext, keine psychologischen Konstrukte.
    """

    name: str = "student_generic"

    # Wie stark ist die Woche insgesamt vorstrukturiert?
    # Beinhaltet sowohl Wiederholbarkeit von Tagen als auch Dichte harter Zeitblöcke.
    schedule_rigidity: float = 0.58

    # Wie stark unterscheiden sich Semester, Prüfungsphase und Ferien?
    phase_variability: float = 0.52

    # Stärke der Uni-Präsenz im Semester
    university_load: float = 0.57

    # Stärke von Nebenjob / Praktikum / Arbeit
    employment_load: float = 0.18

    # Stärke und Regelmäßigkeit der Lernlast, vor allem in der Prüfungsphase
    study_intensity: float = 0.56

    # Wie häufig findet Sport statt?
    sport_frequency: float = 0.52

    # Wie sehr ist Sport ein fixer Strukturanker?
    sport_fixedness: float = 0.42

    # Wie frei / offen sind Abende?
    evening_flexibility: float = 0.67

    # Wie zerstückelt / hybrid sind Tage?
    day_fragmentation: float = 0.44

    # Rate spontaner Termine / Erledigungen / appointments
    random_event_rate: float = 0.18

    # Pendelaufwand
    commute_load: float = 0.2

    # Frequenz von Ortswechseln, z. B. WG <-> Zuhause
    location_switch_frequency: float = 0.22

    # Wie stark ist das Wochenende strukturiert?
    weekend_structure: float = 0.34

    # Wie sozial / beziehungsorientiert ist das Wochenende?
    weekend_social_intensity: float = 0.7


WEEKDAY_NAMES = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def lerp(low: float, high: float, t: float) -> float:
    return low + (high - low) * clamp(t)


def round_to_nonnegative_int(value: float) -> int:
    return max(0, int(round(value)))


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


def add_block_if_possible(structure: WeeklyStructure, candidate: WeeklyBlockTemplate) -> bool:
    if has_time_conflict(structure.blocks, candidate):
        return False
    structure.add_block(candidate)
    return True


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
    max_attempts: int = 25,
) -> WeeklyBlockTemplate | None:
    per_sample_probability = rule.get("per_sample_probability", 1.0)
    if rng.random() >= per_sample_probability:
        return None

    desired_flexibility = rule.get("flexibility", BlockFlexibility.FLEXIBLE)

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
            flexibility=desired_flexibility,
            subtype=rule.get("subtype"),
            notes=rule.get("notes", []),
        )
        if not has_time_conflict(existing_blocks, candidate):
            return candidate
    return None


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
    if rng is None:
        rng = random.Random()

    is_weekend = weekday in [5, 6]
    sleep_start = rng.choice([22, 23])

    if phase == YearPhase.HOLIDAY:
        base_wake_hour = rng.choice([8, 9]) if is_weekend else rng.choice([7, 8])
    else:
        base_wake_hour = rng.choice([8, 9]) if is_weekend else 7

    wake_hour = base_wake_hour
    if first_external_hour is not None:
        latest_reasonable_wake = max(5, first_external_hour - 2)
        wake_hour = min(wake_hour, latest_reasonable_wake)

    return sleep_start, wake_hour


def classify_default_downtime_subtype(
    hour: int,
    occupied_hours: set[int],
    wake_hour: int,
    sleep_start: int,
) -> str:
    later_occupied = [h for h in occupied_hours if h > hour]
    earlier_occupied = [h for h in occupied_hours if h < hour]

    if wake_hour <= hour < min(wake_hour + 2, sleep_start):
        return "morning_free_time"
    if max(wake_hour, sleep_start - 2) <= hour < sleep_start:
        return "evening_wind_down"
    if earlier_occupied and later_occupied:
        return "between_blocks"
    return "open_time"


def is_external_activity(
    activity_type: ActivityType,
    subtype: str | None = None,
) -> bool:
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
    for hour in range(start_hour, end_hour):
        if 0 <= hour < 24 and schedule[hour] is None:
            return hour
    return None


def insert_meals(schedule: list[DayEpisode | None], wake_hour: int) -> None:
    breakfast_hour = find_free_hour_in_window(schedule, wake_hour + 1, min(wake_hour + 3, 24))
    if breakfast_hour is not None:
        schedule[breakfast_hour] = DayEpisode(
            hour=breakfast_hour,
            activity_type=ActivityType.EAT,
            flexibility=BlockFlexibility.FIXED,
            subtype="breakfast",
        )

    lunch_hour = find_free_hour_in_window(schedule, 12, 15)
    if lunch_hour is not None:
        schedule[lunch_hour] = DayEpisode(
            hour=lunch_hour,
            activity_type=ActivityType.EAT,
            flexibility=BlockFlexibility.FIXED,
            subtype="lunch",
        )

    dinner_hour = find_free_hour_in_window(schedule, 18, 21)
    if dinner_hour is not None:
        schedule[dinner_hour] = DayEpisode(
            hour=dinner_hour,
            activity_type=ActivityType.EAT,
            flexibility=BlockFlexibility.FIXED,
            subtype="dinner",
        )


def _insert_commute_segment(
    schedule: list[DayEpisode | None],
    start_hour: int,
    duration: int,
    subtype: str,
) -> None:
    if duration <= 0:
        return
    for hour in range(start_hour, start_hour + duration):
        if 0 <= hour < 24 and schedule[hour] is None:
            schedule[hour] = DayEpisode(
                hour=hour,
                activity_type=ActivityType.COMMUTE,
                flexibility=BlockFlexibility.FIXED,
                subtype=subtype,
            )


def insert_commutes(
    schedule: list[DayEpisode | None],
    weekday_blocks: list[WeeklyBlockTemplate],
    weekly_structure: WeeklyStructure,
) -> None:
    external_blocks = [b for b in weekday_blocks if is_external_activity(b.activity_type, b.subtype)]
    if not external_blocks:
        return

    external_blocks = sorted(external_blocks, key=lambda b: b.start_hour)
    commute_by_subtype = weekly_structure.metadata.get("commute_hours_by_subtype", {})
    default_commute = int(weekly_structure.metadata.get("default_commute_hours", 1))

    first_block = external_blocks[0]
    last_block = external_blocks[-1]

    total_out = int(commute_by_subtype.get(first_block.subtype or "", default_commute))
    out_each_way = max(0, round(total_out / 2))
    total_home = int(commute_by_subtype.get(last_block.subtype or "", default_commute))
    home_each_way = max(0, round(total_home / 2))

    _insert_commute_segment(schedule, first_block.start_hour - out_each_way, out_each_way, "commute_out")
    _insert_commute_segment(schedule, last_block.end_hour, home_each_way, "commute_home")


def generate_full_day_schedule(
    weekly_structure: WeeklyStructure,
    weekday: int,
    rng: random.Random | None = None,
) -> list[DayEpisode]:
    if rng is None:
        rng = random.Random()

    weekday_blocks = weekly_structure.get_blocks_for_weekday(weekday)
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

    for ep in hourly_episodes:
        schedule[ep.hour] = ep

    sleep_hours = list(range(sleep_start, 24)) + list(range(0, wake_hour))
    for hour in sleep_hours:
        if schedule[hour] is None:
            schedule[hour] = DayEpisode(
                hour=hour,
                activity_type=ActivityType.SLEEP,
                flexibility=BlockFlexibility.FIXED,
                subtype="night_sleep",
            )

    if 0 <= wake_hour < 24 and schedule[wake_hour] is None:
        schedule[wake_hour] = DayEpisode(
            hour=wake_hour,
            activity_type=ActivityType.WAKE_UP,
            flexibility=BlockFlexibility.FIXED,
            subtype="morning_wake_up",
        )

    insert_commutes(schedule, weekday_blocks, weekly_structure)
    insert_meals(schedule, wake_hour)

    occupied_hours = {ep.hour for ep in hourly_episodes}
    for hour in range(24):
        if schedule[hour] is None:
            subtype = classify_default_downtime_subtype(hour, occupied_hours, wake_hour, sleep_start)
            schedule[hour] = DayEpisode(
                hour=hour,
                activity_type=ActivityType.DOWNTIME,
                flexibility=BlockFlexibility.FLEXIBLE,
                subtype=subtype,
            )

    return [ep for ep in schedule if ep is not None]


# ------------------------------------------------------------
# Mapping von abstrakten Parametern auf phasenspezifische Strukturwerte
# ------------------------------------------------------------

def phase_profile(params: StudentStructureParameters, phase: YearPhase) -> dict[str, float]:
    pv = clamp(params.phase_variability)
    sr = clamp(params.schedule_rigidity)
    si = clamp(params.study_intensity)

    if phase == YearPhase.SEMESTER:
        return {
            "schedule_rigidity": clamp(sr),
            "university_load": clamp(params.university_load),
            "employment_load": clamp(params.employment_load * lerp(1.0, 0.85, pv)),
            "study_intensity": clamp(si * lerp(0.18, 0.40, 1 - pv)),
            "sport_frequency": clamp(params.sport_frequency),
            "evening_flexibility": clamp(params.evening_flexibility * 0.9),
            "random_event_rate": clamp(params.random_event_rate * 0.9),
            "weekend_structure": clamp(params.weekend_structure),
            "weekend_social_intensity": clamp(params.weekend_social_intensity * 0.9),
        }

    if phase == YearPhase.EXAM_PHASE:
        # High phase_variability => exam phase should break away from semester strongly.
        return {
            "schedule_rigidity": clamp(lerp(sr, 0.95, 0.45 + 0.55 * si)),
            "university_load": clamp(params.university_load * (1.0 - 1.0 * pv)),
            "employment_load": clamp(params.employment_load * (1.0 - 0.95 * pv)),
            "study_intensity": clamp(lerp(si, 1.0, 0.55 + 0.45 * pv)),
            "sport_frequency": clamp(params.sport_frequency * lerp(1.0, 0.85, pv)),
            "evening_flexibility": clamp(lerp(params.evening_flexibility, 0.2, 0.45 + 0.55 * pv)),
            "random_event_rate": clamp(params.random_event_rate * 0.55),
            "weekend_structure": clamp(lerp(params.weekend_structure, 0.7, 0.45 + 0.55 * si)),
            "weekend_social_intensity": clamp(params.weekend_social_intensity * lerp(0.85, 0.25, 0.4 + 0.6 * pv)),
        }

    # Holiday: typically much less studying and more open structure.
    return {
        "schedule_rigidity": clamp(sr * (1.0 - 0.8 * pv)),
        "university_load": 0.0,
        "employment_load": clamp(lerp(params.employment_load * 0.85, params.employment_load * 1.15, pv)),
        "study_intensity": clamp(si * (1.0 - 0.98 * pv) * 0.35),
        "sport_frequency": clamp(lerp(params.sport_frequency, params.sport_frequency * 0.8, params.evening_flexibility)),
        "evening_flexibility": clamp(lerp(params.evening_flexibility, 0.95, 0.5 + 0.5 * pv)),
        "random_event_rate": clamp(lerp(params.random_event_rate, 0.55, 0.4 + 0.6 * pv)),
        "weekend_structure": clamp(lerp(params.weekend_structure, 0.25, 0.5 + 0.5 * pv)),
        "weekend_social_intensity": clamp(lerp(params.weekend_social_intensity, 0.9, 0.5 + 0.5 * pv)),
    }


def choose_evenly_spread_weekdays(n_days: int, spread: float, rng: random.Random) -> list[int]:
    n_days = max(0, min(7, n_days))
    if n_days == 0:
        return []

    spread = clamp(spread)
    if spread >= 0.6:
        templates = {
            1: [rng.choice(range(7))],
            2: [1, 3],
            3: [0, 2, 4],
            4: [0, 2, 4, 5],
            5: [0, 1, 2, 4, 5],
            6: [0, 1, 2, 3, 4, 5],
            7: [0, 1, 2, 3, 4, 5, 6],
        }
        return templates[n_days]
    return list(range(n_days))


def choose_days_with_capacity(
    structure: WeeklyStructure,
    candidate_days: list[int],
    target_n_days: int,
) -> list[int]:
    day_free_capacity: list[tuple[int, int]] = []
    for weekday in candidate_days:
        occupied = sum(
            block.end_hour - block.start_hour
            for block in structure.get_blocks_for_weekday(weekday)
        )
        free_capacity = 24 - occupied
        day_free_capacity.append((weekday, free_capacity))
    day_free_capacity.sort(key=lambda item: item[1], reverse=True)
    return [weekday for weekday, _ in day_free_capacity[:target_n_days]]


# ------------------------------------------------------------
# Aufbau der Wochenstruktur
# ------------------------------------------------------------

def add_university_blocks(
    structure: WeeklyStructure,
    params: StudentStructureParameters,
    p: dict[str, float],
    rng: random.Random,
) -> None:
    rigidity = p["schedule_rigidity"]
    uni_days = round_to_nonnegative_int(lerp(0, 5, p["university_load"] * (0.55 + 0.45 * rigidity)))
    if uni_days <= 0:
        return

    day_spread = lerp(0.35, 1.0, rigidity)
    selected_days = choose_evenly_spread_weekdays(min(5, uni_days), day_spread, rng)
    start_hour = round_to_nonnegative_int(lerp(8, 9, 1 - rigidity))
    hours_per_day = round_to_nonnegative_int(lerp(4, 8, p["university_load"] * (0.45 + 0.55 * rigidity)))
    n_blocks = 2 if hours_per_day >= 5 else 1
    block_duration = max(2, round_to_nonnegative_int(hours_per_day / n_blocks))
    midday_break = 1

    for weekday in selected_days:
        current_start = start_hour
        for _ in range(n_blocks):
            end = min(24, current_start + block_duration)
            add_block_if_possible(
                structure,
                WeeklyBlockTemplate(
                    weekday=weekday,
                    start_hour=current_start,
                    end_hour=end,
                    activity_type=ActivityType.WORK,
                    flexibility=BlockFlexibility.FIXED,
                    subtype="university",
                ),
            )
            current_start = end + midday_break


def add_work_blocks(
    structure: WeeklyStructure,
    params: StudentStructureParameters,
    p: dict[str, float],
    rng: random.Random,
) -> None:
    rigidity = p["schedule_rigidity"]
    work_days = round_to_nonnegative_int(lerp(0, 5, p["employment_load"] * (0.45 + 0.55 * rigidity)))
    if work_days <= 0:
        return

    candidate_days = choose_evenly_spread_weekdays(min(5, work_days), lerp(0.3, 0.95, rigidity), rng)
    candidate_days = choose_days_with_capacity(structure, candidate_days, len(candidate_days))
    start_hour = round_to_nonnegative_int(lerp(8, 9, 1 - rigidity))
    total_hours = round_to_nonnegative_int(lerp(4, 8, p["employment_load"] * (0.45 + 0.55 * rigidity)))
    total_hours = max(3, total_hours)
    split_prob = clamp(0.10 + 0.45 * params.day_fragmentation + 0.15 * (1 - rigidity))
    break_hours = 2

    for weekday in candidate_days:
        split = rng.random() < split_prob and total_hours >= 6
        if split:
            first_hours = max(3, total_hours - 2)
            second_hours = max(1, total_hours - first_hours)
            first_end = min(24, start_hour + first_hours)
            second_start = min(23, first_end + break_hours)
            second_end = min(24, second_start + second_hours)
            add_block_if_possible(
                structure,
                WeeklyBlockTemplate(
                    weekday=weekday,
                    start_hour=start_hour,
                    end_hour=first_end,
                    activity_type=ActivityType.WORK,
                    flexibility=BlockFlexibility.FIXED,
                    subtype="paid_work",
                ),
            )
            add_block_if_possible(
                structure,
                WeeklyBlockTemplate(
                    weekday=weekday,
                    start_hour=second_start,
                    end_hour=second_end,
                    activity_type=ActivityType.WORK,
                    flexibility=BlockFlexibility.FIXED,
                    subtype="paid_work",
                ),
            )
        else:
            end = min(24, start_hour + total_hours)
            add_block_if_possible(
                structure,
                WeeklyBlockTemplate(
                    weekday=weekday,
                    start_hour=start_hour,
                    end_hour=end,
                    activity_type=ActivityType.WORK,
                    flexibility=BlockFlexibility.FIXED,
                    subtype="paid_work",
                ),
            )


def add_study_blocks(
    structure: WeeklyStructure,
    p: dict[str, float],
    rng: random.Random,
) -> None:
    total_study_hours = round_to_nonnegative_int(lerp(0, 28, p["study_intensity"]))
    if total_study_hours <= 0:
        return

    block_size = 2
    n_blocks = max(1, round_to_nonnegative_int(total_study_hours / block_size))
    regularity = clamp(p["study_intensity"])

    if structure.phase == YearPhase.SEMESTER:
        weekend_share = lerp(0.1, 0.45, 1 - regularity)
        evening_bias = lerp(0.45, 0.95, 1 - regularity)
        weekday_blocks = max(0, n_blocks - round_to_nonnegative_int(n_blocks * weekend_share))
        weekend_blocks = n_blocks - weekday_blocks
        weekday_window = (17, 21) if evening_bias >= 0.6 else (10, 18)

        for _ in range(weekday_blocks):
            candidate = sample_flexible_block_from_rule(
                rule={
                    "allowed_weekdays": [0, 1, 2, 3, 4],
                    "time_window": weekday_window,
                    "duration_range": (block_size, block_size),
                    "activity_type": ActivityType.WORK,
                    "subtype": "studying",
                    "per_sample_probability": 1.0,
                    "flexibility": BlockFlexibility.FLEXIBLE,
                },
                existing_blocks=structure.blocks,
                rng=rng,
            )
            if candidate is not None:
                structure.add_block(candidate)

        for _ in range(weekend_blocks):
            candidate = sample_flexible_block_from_rule(
                rule={
                    "allowed_weekdays": [5, 6],
                    "time_window": (10, 18),
                    "duration_range": (block_size, block_size),
                    "activity_type": ActivityType.WORK,
                    "subtype": "studying",
                    "per_sample_probability": 1.0,
                    "flexibility": BlockFlexibility.FLEXIBLE,
                },
                existing_blocks=structure.blocks,
                rng=rng,
            )
            if candidate is not None:
                structure.add_block(candidate)
        return

    if structure.phase == YearPhase.EXAM_PHASE:
        n_days = round_to_nonnegative_int(lerp(4, 6, regularity))
        candidate_days = choose_evenly_spread_weekdays(n_days, 1.0, rng)
        per_day_target = {day: 0 for day in candidate_days}
        for i in range(n_blocks):
            per_day_target[candidate_days[i % len(candidate_days)]] += 1

        for day, count in per_day_target.items():
            for j in range(count):
                candidate = sample_flexible_block_from_rule(
                    rule={
                        "allowed_weekdays": [day],
                        "time_window": (9, 18),
                        "duration_range": (block_size, block_size),
                        "activity_type": ActivityType.WORK,
                        "subtype": "studying",
                        "per_sample_probability": 1.0,
                        "flexibility": BlockFlexibility.FLEXIBLE,
                    },
                    existing_blocks=structure.blocks,
                    rng=random.Random(rng.random() + j),
                )
                if candidate is not None:
                    structure.add_block(candidate)
        return

    # Holiday: studying should be rare and mild by default.
    holiday_blocks = min(n_blocks, 1 + int(p["study_intensity"] > 0.25))
    for _ in range(holiday_blocks):
        candidate = sample_flexible_block_from_rule(
            rule={
                "allowed_weekdays": [2, 4, 5],
                "time_window": (10, 15),
                "duration_range": (block_size, block_size),
                "activity_type": ActivityType.WORK,
                "subtype": "studying",
                "per_sample_probability": clamp(0.25 + 0.35 * p["study_intensity"]),
                "flexibility": BlockFlexibility.FLEXIBLE,
            },
            existing_blocks=structure.blocks,
            rng=rng,
        )
        if candidate is not None:
            structure.add_block(candidate)


def add_sport_blocks(
    structure: WeeklyStructure,
    params: StudentStructureParameters,
    p: dict[str, float],
    rng: random.Random,
) -> None:
    target_days = round_to_nonnegative_int(lerp(0, 7, p["sport_frequency"]))
    if target_days <= 0:
        return

    ordered_days = choose_days_with_capacity(structure, list(range(7)), min(target_days, 7))
    duration = max(1, round_to_nonnegative_int(lerp(1, 2, params.sport_fixedness)))
    flexibility = BlockFlexibility.FIXED if params.sport_fixedness >= 0.5 else BlockFlexibility.FLEXIBLE
    anchor_bias = clamp(0.35 + 0.65 * params.sport_fixedness)
    time_window = (14, 18) if anchor_bias >= 0.5 else (10, 21)

    for weekday in ordered_days:
        candidate = sample_flexible_block_from_rule(
            rule={
                "allowed_weekdays": [weekday],
                "time_window": time_window,
                "duration_range": (duration, duration),
                "activity_type": ActivityType.PHYSICAL_ACTIVITY,
                "subtype": "sport_anchor",
                "per_sample_probability": 1.0,
                "flexibility": flexibility,
            },
            existing_blocks=structure.blocks,
            rng=rng,
        )
        if candidate is not None:
            structure.add_block(candidate)


def add_evening_social_blocks(
    structure: WeeklyStructure,
    params: StudentStructureParameters,
    p: dict[str, float],
    rng: random.Random,
) -> None:
    social_prob = clamp(lerp(0.15, 0.75, p["evening_flexibility"] * p["weekend_social_intensity"]))
    duration = max(1, round_to_nonnegative_int(lerp(1, 3, p["weekend_social_intensity"])))
    candidate_days = [4, 5, 6] if p["weekend_structure"] < 0.65 else [5, 6]

    for weekday in candidate_days:
        if rng.random() > social_prob:
            continue
        candidate = sample_flexible_block_from_rule(
            rule={
                "allowed_weekdays": [weekday],
                "time_window": (19, 23),
                "duration_range": (duration, duration),
                "activity_type": ActivityType.SOCIAL_TIME,
                "subtype": "evening_social",
                "per_sample_probability": 1.0,
                "flexibility": BlockFlexibility.FLEXIBLE,
            },
            existing_blocks=structure.blocks,
            rng=rng,
        )
        if candidate is not None:
            structure.add_block(candidate)

    family_dinner_prob = clamp(0.15 + 0.55 * params.location_switch_frequency + 0.25 * p["weekend_structure"])
    if rng.random() < family_dinner_prob:
        add_block_if_possible(
            structure,
            WeeklyBlockTemplate(
                weekday=6,
                start_hour=18,
                end_hour=20,
                activity_type=ActivityType.SOCIAL_TIME,
                flexibility=BlockFlexibility.FIXED,
                subtype="family_dinner",
            ),
        )


def add_random_appointments(
    structure: WeeklyStructure,
    p: dict[str, float],
    params: StudentStructureParameters,
    rng: random.Random,
) -> None:
    probability = clamp(lerp(0.0, 0.8, p["random_event_rate"]))
    duration = 1 if params.day_fragmentation < 0.5 else 2
    n_appointments = 1 + int(params.day_fragmentation > 0.55) + int(params.day_fragmentation > 0.85)

    for _ in range(n_appointments):
        candidate = sample_flexible_block_from_rule(
            rule={
                "allowed_weekdays": [0, 1, 2, 3, 4, 5],
                "time_window": (9, 18),
                "duration_range": (duration, duration),
                "activity_type": ActivityType.RANDOM_APPOINTMENT,
                "subtype": "appointment",
                "per_sample_probability": probability,
                "flexibility": BlockFlexibility.FLEXIBLE,
            },
            existing_blocks=structure.blocks,
            rng=rng,
        )
        if candidate is not None:
            structure.add_block(candidate)


def add_evening_routine(
    structure: WeeklyStructure,
    p: dict[str, float],
) -> None:
    routine_strength = clamp(1.0 - p["evening_flexibility"])
    if routine_strength < 0.45:
        return

    for weekday in range(5):
        add_block_if_possible(
            structure,
            WeeklyBlockTemplate(
                weekday=weekday,
                start_hour=18,
                end_hour=19,
                activity_type=ActivityType.DOWNTIME,
                flexibility=BlockFlexibility.FIXED,
                subtype="evening_routine",
            ),
        )


def add_location_switch_blocks(
    structure: WeeklyStructure,
    params: StudentStructureParameters,
) -> None:
    if clamp(params.location_switch_frequency) < 0.45:
        return

    if structure.phase in {YearPhase.SEMESTER, YearPhase.EXAM_PHASE}:
        add_block_if_possible(
            structure,
            WeeklyBlockTemplate(
                weekday=4,
                start_hour=15,
                end_hour=17,
                activity_type=ActivityType.COMMUTE,
                flexibility=BlockFlexibility.FIXED,
                subtype="location_switch_home",
            ),
        )
        add_block_if_possible(
            structure,
            WeeklyBlockTemplate(
                weekday=6,
                start_hour=20,
                end_hour=23,
                activity_type=ActivityType.COMMUTE,
                flexibility=BlockFlexibility.FIXED,
                subtype="location_switch_back",
            ),
        )


def build_commute_metadata(params: StudentStructureParameters) -> dict[str, object]:
    uni_total = round_to_nonnegative_int(lerp(0, 4, params.commute_load))
    work_total = round_to_nonnegative_int(lerp(0, 2, params.commute_load * 0.7))
    social_total = round_to_nonnegative_int(lerp(0, 2, params.commute_load * 0.5))
    sport_total = round_to_nonnegative_int(lerp(0, 2, params.commute_load * 0.5))
    appointment_total = round_to_nonnegative_int(lerp(0, 2, params.commute_load * 0.6))

    return {
        "default_commute_hours": max(1, work_total),
        "commute_hours_by_subtype": {
            "university": uni_total,
            "paid_work": max(1, work_total),
            "sport_anchor": max(1, sport_total),
            "evening_social": max(1, social_total),
            "family_dinner": max(1, social_total),
            "appointment": max(1, appointment_total),
        },
    }


def generate_student_week(
    params: StudentStructureParameters,
    phase: YearPhase,
    rng: random.Random | None = None,
) -> WeeklyStructure:
    if rng is None:
        rng = random.Random()

    p = phase_profile(params, phase)
    structure = WeeklyStructure(
        persona_name=params.name,
        phase=phase,
        metadata=build_commute_metadata(params),
    )

    add_university_blocks(structure, params, p, rng)
    add_work_blocks(structure, params, p, rng)
    add_study_blocks(structure, p, rng)
    add_sport_blocks(structure, params, p, rng)
    add_evening_social_blocks(structure, params, p, rng)
    add_random_appointments(structure, p, params, rng)
    add_evening_routine(structure, p)
    add_location_switch_blocks(structure, params)

    return structure


def summarize_parameters(params: StudentStructureParameters) -> dict[str, object]:
    return {
        "name": params.name,
        "schedule_rigidity": params.schedule_rigidity,
        "study_intensity": params.study_intensity,
                "phase_variability": params.phase_variability,
        "university_load": params.university_load,
        "employment_load": params.employment_load,
                        "sport_frequency": params.sport_frequency,
        "sport_fixedness": params.sport_fixedness,
        "evening_flexibility": params.evening_flexibility,
        "day_fragmentation": params.day_fragmentation,
        "random_event_rate": params.random_event_rate,
        "commute_load": params.commute_load,
        "location_switch_frequency": params.location_switch_frequency,
        "weekend_structure": params.weekend_structure,
        "weekend_social_intensity": params.weekend_social_intensity,
    }


if __name__ == "__main__":
    BASE_SEED = 37

    student_params = StudentStructureParameters(
        name="student_average",
        schedule_rigidity=0.62,
        study_intensity=0.56,
        phase_variability=0.52,
        university_load=0.70,
        employment_load=0.22,
        sport_frequency=0.52,
        sport_fixedness=0.42,
        evening_flexibility=0.67,
        day_fragmentation=0.44,
        random_event_rate=0.18,
        commute_load=0.20,
        location_switch_frequency=0.22,
        weekend_structure=0.34,
        weekend_social_intensity=0.74,
    )

    print("\n=== PARAMETER SUMMARY ===")
    for key, value in summarize_parameters(student_params).items():
        print(f"- {key}: {value}")

    for phase in [YearPhase.SEMESTER, YearPhase.EXAM_PHASE, YearPhase.HOLIDAY]:
        print(f"\n=== {student_params.name} | {phase.value.upper()} ===")
        week_rng = random.Random(BASE_SEED + hash(student_params.name + phase.value) % 10000)
        structure = generate_student_week(student_params, phase, rng=week_rng)
        print_weekly_structure(structure)

        for weekday in range(7):
            day_seed = BASE_SEED + weekday + hash(student_params.name + phase.value) % 10000
            day_rng = random.Random(day_seed)
            full_day = generate_full_day_schedule(structure, weekday, rng=day_rng)
            print_full_day_schedule(full_day, weekday)
