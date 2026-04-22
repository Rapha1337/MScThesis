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
    Numerische, nicht-psychologische Stellschrauben für eine generische
    Studenten-Persona.

    Alle Parameter sollen beschreiben, wie die Wochenstruktur aussieht,
    nicht warum jemand sich so verhält.
    """

    name: str = "student_generic"

    # ------------------------------------------------------------
    # 1) Semester / Prüfungsphase / Ferien
    # ------------------------------------------------------------
    university_presence_days_semester: int = 2
    university_blocks_per_uni_day: int = 2
    university_block_duration_hours: int = 3
    university_midday_break_hours: int = 1
    university_start_hour: int = 8
    university_day_spread: float = 1.0  # 0 = kompakt, 1 = stärker über die Woche verteilt

    # Commute
    commute_hours_per_uni_day: float = 2.0  # round-trip in hours

    # ------------------------------------------------------------
    # 2) Arbeit / Nebenjob
    # ------------------------------------------------------------
    employment_days_per_week_semester: float = 3.0
    employment_days_per_week_exam_phase: float = 0.0
    employment_days_per_week_holiday: float = 4.0

    employment_hours_per_day: float = 6.0
    split_workday_probability: float = 0.5
    workday_start_hour: int = 8
    workday_mid_break_hours: int = 2
    workday_second_block_hours: float = 2.0

    # ------------------------------------------------------------
    # 3) Lernen außerhalb fixer Uni-Blöcke
    # ------------------------------------------------------------
    study_hours_per_week_semester: float = 2.0
    study_hours_per_week_exam_phase: float = 24.0
    study_hours_per_week_holiday: float = 0.0

    study_block_size_hours: float = 2.0
    study_evening_bias_semester: float = 0.8  # 1.0 = fast nur abends im Semester
    study_weekend_share_semester: float = 0.3
    study_weekend_share_exam_phase: float = 0.3

    # ------------------------------------------------------------
    # 4) Sport / Training
    # ------------------------------------------------------------
    sport_days_per_week_semester: float = 5.0
    sport_days_per_week_exam_phase: float = 5.0
    sport_days_per_week_holiday: float = 5.0

    sport_duration_hours: float = 1.5
    sport_fixedness: float = 0.8  # >0.5 => eher fixed, sonst eher flexible
    sport_anchor_bias: float = 0.8  # 1.0 = Sport als sehr stabiler Anker

    # ------------------------------------------------------------
    # 5) Soziales / Abende / Wochenende
    # ------------------------------------------------------------
    evening_social_probability_semester: float = 0.4
    evening_social_probability_exam_phase: float = 0.15
    evening_social_probability_holiday: float = 0.6

    evening_social_duration_hours: float = 2.0
    weekend_structure: float = 0.4  # 0 = offen, 1 = stark strukturiert
    sunday_family_dinner_probability: float = 0.0

    # ------------------------------------------------------------
    # 6) Variabilität / Fragmentierung
    # ------------------------------------------------------------
    random_appointment_rate_semester: float = 0.3
    random_appointment_rate_exam_phase: float = 0.1
    random_appointment_rate_holiday: float = 0.4

    random_appointment_duration_hours: float = 1.5
    evening_routine_strength: float = 0.3
    day_fragmentation: float = 0.5  # höhere Werte => mehr hybride Tage / mehr Blöcke


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


def add_fixed_block_if_possible(
    structure: WeeklyStructure,
    candidate: WeeklyBlockTemplate,
) -> bool:
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
    max_attempts: int = 20,
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

    sleep_start = rng.choice([22, 23])
    is_weekend = weekday in [5, 6]

    if phase == YearPhase.HOLIDAY:
        base_wake_hour = rng.choice([8, 9])
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


def insert_meals(
    schedule: list[DayEpisode | None],
    wake_hour: int,
) -> None:
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
    reverse: bool = False,
) -> None:
    if duration <= 0:
        return

    if reverse:
        hours = list(range(start_hour - duration + 1, start_hour + 1))
    else:
        hours = list(range(start_hour, start_hour + duration))

    for hour in hours:
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

    commute_total = int(commute_by_subtype.get(first_block.subtype or "", default_commute))
    commute_each_way = max(1, round(commute_total / 2)) if commute_total > 0 else 0

    _insert_commute_segment(
        schedule=schedule,
        start_hour=first_block.start_hour - commute_each_way,
        duration=commute_each_way,
        subtype="commute_out",
        reverse=False,
    )

    commute_total_home = int(commute_by_subtype.get(last_block.subtype or "", default_commute))
    commute_each_way_home = max(1, round(commute_total_home / 2)) if commute_total_home > 0 else 0

    _insert_commute_segment(
        schedule=schedule,
        start_hour=last_block.end_hour,
        duration=commute_each_way_home,
        subtype="commute_home",
        reverse=False,
    )


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
# Parameter helpers
# ============================================================

def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def round_to_nonnegative_int(value: float) -> int:
    return max(0, int(round(value)))


def choose_evenly_spread_weekdays(n_days: int, spread: float, rng: random.Random) -> list[int]:
    """
    0 -> eher kompakt am Wochenanfang
    1 -> eher über die Woche verteilt
    """
    n_days = max(0, min(7, n_days))
    if n_days == 0:
        return []

    compact_pool = list(range(7))
    spread_templates = {
        1: [rng.choice(range(7))],
        2: [1, 3],
        3: [0, 2, 4],
        4: [0, 2, 4, 5],
        5: [0, 1, 2, 4, 5],
        6: [0, 1, 2, 3, 4, 5],
        7: [0, 1, 2, 3, 4, 5, 6],
    }

    if spread >= 0.5:
        chosen = spread_templates[n_days]
    else:
        chosen = compact_pool[:n_days]

    return sorted(chosen)


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


def phase_specific_value(
    phase: YearPhase,
    semester_value: float,
    exam_value: float,
    holiday_value: float,
) -> float:
    if phase == YearPhase.SEMESTER:
        return semester_value
    if phase == YearPhase.EXAM_PHASE:
        return exam_value
    return holiday_value


# ============================================================
# Generische parametrische Student-Woche
# ============================================================

def add_university_blocks(
    structure: WeeklyStructure,
    params: StudentStructureParameters,
    rng: random.Random,
) -> None:
    if structure.phase != YearPhase.SEMESTER:
        return

    n_uni_days = round_to_nonnegative_int(params.university_presence_days_semester)
    uni_days = choose_evenly_spread_weekdays(
        n_uni_days,
        spread=clamp(params.university_day_spread, 0.0, 1.0),
        rng=rng,
    )

    for weekday in uni_days:
        start = params.university_start_hour
        n_blocks = max(1, round_to_nonnegative_int(params.university_blocks_per_uni_day))
        duration = max(1, round_to_nonnegative_int(params.university_block_duration_hours))
        midday_break = max(0, round_to_nonnegative_int(params.university_midday_break_hours))

        for i in range(n_blocks):
            block_start = start + i * (duration + midday_break)
            block_end = block_start + duration
            add_fixed_block_if_possible(
                structure,
                WeeklyBlockTemplate(
                    weekday=weekday,
                    start_hour=block_start,
                    end_hour=min(block_end, 24),
                    activity_type=ActivityType.WORK,
                    flexibility=BlockFlexibility.FIXED,
                    subtype="university",
                ),
            )


def add_work_blocks(
    structure: WeeklyStructure,
    params: StudentStructureParameters,
    rng: random.Random,
) -> None:
    target_days = round_to_nonnegative_int(
        phase_specific_value(
            structure.phase,
            params.employment_days_per_week_semester,
            params.employment_days_per_week_exam_phase,
            params.employment_days_per_week_holiday,
        )
    )
    if target_days <= 0:
        return

    candidate_days = list(range(5))  # Mo-Fr
    workdays = choose_evenly_spread_weekdays(
        n_days=min(target_days, 5),
        spread=0.7,
        rng=rng,
    )
    workdays = [d for d in workdays if d in candidate_days]

    total_hours = max(1.0, phase_specific_value(
        structure.phase,
        params.employment_hours_per_day,
        params.employment_hours_per_day,
        params.employment_hours_per_day,
    ))
    first_block_hours = max(1, round_to_nonnegative_int(total_hours - params.workday_second_block_hours))
    second_block_hours = max(1, round_to_nonnegative_int(params.workday_second_block_hours))
    midday_break = max(1, round_to_nonnegative_int(params.workday_mid_break_hours))

    effective_split_probability = clamp(
        params.split_workday_probability * (0.6 + 0.8 * clamp(params.day_fragmentation, 0.0, 1.0)),
        0.0,
        1.0,
    )

    for weekday in workdays:
        split = rng.random() < effective_split_probability

        if split:
            first_start = params.workday_start_hour
            first_end = min(24, first_start + first_block_hours)
            second_start = min(23, first_end + midday_break)
            second_end = min(24, second_start + second_block_hours)

            add_fixed_block_if_possible(
                structure,
                WeeklyBlockTemplate(
                    weekday=weekday,
                    start_hour=first_start,
                    end_hour=first_end,
                    activity_type=ActivityType.WORK,
                    flexibility=BlockFlexibility.FIXED,
                    subtype="paid_work",
                ),
            )
            add_fixed_block_if_possible(
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
            start = params.workday_start_hour
            end = min(24, start + round_to_nonnegative_int(total_hours))
            add_fixed_block_if_possible(
                structure,
                WeeklyBlockTemplate(
                    weekday=weekday,
                    start_hour=start,
                    end_hour=end,
                    activity_type=ActivityType.WORK,
                    flexibility=BlockFlexibility.FIXED,
                    subtype="paid_work",
                ),
            )


def add_study_blocks(
    structure: WeeklyStructure,
    params: StudentStructureParameters,
    rng: random.Random,
) -> None:
    total_study_hours = phase_specific_value(
        structure.phase,
        params.study_hours_per_week_semester,
        params.study_hours_per_week_exam_phase,
        params.study_hours_per_week_holiday,
    )
    if total_study_hours <= 0:
        return

    block_size = max(1, round_to_nonnegative_int(params.study_block_size_hours))
    n_blocks = max(1, round_to_nonnegative_int(total_study_hours / block_size))

    if structure.phase == YearPhase.SEMESTER:
        weekend_share = clamp(params.study_weekend_share_semester, 0.0, 1.0)
        evening_bias = clamp(params.study_evening_bias_semester, 0.0, 1.0)
        weekday_window = (17, 21) if evening_bias >= 0.5 else (10, 18)

        weekend_blocks = round_to_nonnegative_int(n_blocks * weekend_share)
        weekday_blocks = max(0, n_blocks - weekend_blocks)

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

    # Prüfungsphase / Ferien: homogener über die Woche verteilen
    if structure.phase == YearPhase.EXAM_PHASE:
        candidate_days = choose_evenly_spread_weekdays(min(6, max(4, n_blocks)), spread=1.0, rng=rng)
        per_day_target = {day: 0 for day in candidate_days}
        for i in range(n_blocks):
            per_day_target[candidate_days[i % len(candidate_days)]] += 1

        base_window = (9, 18)
        for day, count in per_day_target.items():
            for j in range(count):
                candidate = sample_flexible_block_from_rule(
                    rule={
                        "allowed_weekdays": [day],
                        "time_window": base_window,
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

    # Holiday: falls überhaupt Lernblöcke vorkommen, eher locker und selten
    for _ in range(n_blocks):
        candidate = sample_flexible_block_from_rule(
            rule={
                "allowed_weekdays": [0, 1, 2, 3, 4, 5],
                "time_window": (10, 16),
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


def add_sport_blocks(
    structure: WeeklyStructure,
    params: StudentStructureParameters,
    rng: random.Random,
) -> None:
    target_n_days = round_to_nonnegative_int(
        phase_specific_value(
            structure.phase,
            params.sport_days_per_week_semester,
            params.sport_days_per_week_exam_phase,
            params.sport_days_per_week_holiday,
        )
    )
    if target_n_days <= 0:
        return

    ordered_days = choose_days_with_capacity(structure, list(range(7)), min(target_n_days, 7))
    duration = max(1, round_to_nonnegative_int(params.sport_duration_hours))
    flexibility = (
        BlockFlexibility.FIXED
        if params.sport_fixedness >= 0.5
        else BlockFlexibility.FLEXIBLE
    )

    time_window = (14, 18) if params.sport_anchor_bias >= 0.5 else (10, 21)

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
    rng: random.Random,
) -> None:
    probability = phase_specific_value(
        structure.phase,
        params.evening_social_probability_semester,
        params.evening_social_probability_exam_phase,
        params.evening_social_probability_holiday,
    )
    probability = clamp(probability, 0.0, 1.0)
    duration = max(1, round_to_nonnegative_int(params.evening_social_duration_hours))

    candidate_days = [4, 5, 6]
    if params.weekend_structure >= 0.6:
        candidate_days = [5, 6]

    for weekday in candidate_days:
        if rng.random() > probability:
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

    if rng.random() < clamp(params.sunday_family_dinner_probability, 0.0, 1.0):
        add_fixed_block_if_possible(
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
    params: StudentStructureParameters,
    rng: random.Random,
) -> None:
    probability = clamp(
        phase_specific_value(
            structure.phase,
            params.random_appointment_rate_semester,
            params.random_appointment_rate_exam_phase,
            params.random_appointment_rate_holiday,
        ),
        0.0,
        1.0,
    )
    duration = max(1, round_to_nonnegative_int(params.random_appointment_duration_hours))
    fragmentation = clamp(params.day_fragmentation, 0.0, 1.0)
    n_appointments = 1 + int(fragmentation > 0.55) + int(fragmentation > 0.85)

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
    params: StudentStructureParameters,
) -> None:
    probability = clamp(params.evening_routine_strength, 0.0, 1.0)
    if probability < 0.5:
        return

    for weekday in range(5):
        add_fixed_block_if_possible(
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


def generate_student_week(
    params: StudentStructureParameters,
    phase: YearPhase,
    rng: random.Random | None = None,
) -> WeeklyStructure:
    """
    Eine generische Studenten-Persona, deren Wochenstruktur ausschließlich
    durch numerische Strukturparameter beeinflusst wird.
    """
    if rng is None:
        rng = random.Random()

    structure = WeeklyStructure(
        persona_name=params.name,
        phase=phase,
        metadata={
            "default_commute_hours": 1,
            "commute_hours_by_subtype": {
                "university": int(round(params.commute_hours_per_uni_day)),
                "paid_work": 1,
                "sport_anchor": 1,
                "evening_social": 1,
                "family_dinner": 1,
                "appointment": 1,
            },
        },
    )

    add_university_blocks(structure, params, rng)
    add_work_blocks(structure, params, rng)
    add_study_blocks(structure, params, rng)
    add_sport_blocks(structure, params, rng)
    add_evening_social_blocks(structure, params, rng)
    add_random_appointments(structure, params, rng)
    add_evening_routine(structure, params)

    return structure


def summarize_parameters(params: StudentStructureParameters) -> dict[str, object]:
    return {
        "name": params.name,
        "university_presence_days_semester": params.university_presence_days_semester,
        "commute_hours_per_uni_day": params.commute_hours_per_uni_day,
        "employment_days_per_week": {
            "semester": params.employment_days_per_week_semester,
            "exam_phase": params.employment_days_per_week_exam_phase,
            "holiday": params.employment_days_per_week_holiday,
        },
        "study_hours_per_week": {
            "semester": params.study_hours_per_week_semester,
            "exam_phase": params.study_hours_per_week_exam_phase,
            "holiday": params.study_hours_per_week_holiday,
        },
        "sport_days_per_week": {
            "semester": params.sport_days_per_week_semester,
            "exam_phase": params.sport_days_per_week_exam_phase,
            "holiday": params.sport_days_per_week_holiday,
        },
        "split_workday_probability": params.split_workday_probability,
        "weekend_structure": params.weekend_structure,
        "day_fragmentation": params.day_fragmentation,
        "effective_exam_distribution": "more_even",
        "commute_model": "phase-aware subtype-based",
    }


if __name__ == "__main__":
    BASE_SEED = 37

    student_params = StudentStructureParameters(
        name="student_generic_tunable",
        university_presence_days_semester=2,
        university_blocks_per_uni_day=2,
        university_block_duration_hours=3,
        commute_hours_per_uni_day=2.0,
        employment_days_per_week_semester=3,
        employment_days_per_week_exam_phase=0,
        employment_days_per_week_holiday=4,
        employment_hours_per_day=6,
        split_workday_probability=0.8,
        study_hours_per_week_semester=2,
        study_hours_per_week_exam_phase=18,
        study_hours_per_week_holiday=0,
        sport_days_per_week_semester=6,
        sport_days_per_week_exam_phase=6,
        sport_days_per_week_holiday=6,
        sport_duration_hours=2,
        sport_fixedness=0.9,
        sport_anchor_bias=0.9,
        evening_social_probability_semester=0.5,
        evening_social_probability_exam_phase=0.2,
        evening_social_probability_holiday=0.7,
        weekend_structure=0.4,
        sunday_family_dinner_probability=1.0,
        random_appointment_rate_semester=0.3,
        random_appointment_rate_exam_phase=0.1,
        random_appointment_rate_holiday=0.5,
        evening_routine_strength=0.6,
        day_fragmentation=0.8,
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
