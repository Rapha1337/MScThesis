from __future__ import annotations

# ---------------------------------------------------------------------
# 1) Imports
# ---------------------------------------------------------------------
from dataclasses import dataclass, field
from enum import Enum
import random



# ---------------------------------------------------------------------
# 2) Enums
# ---------------------------------------------------------------------
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



# ---------------------------------------------------------------------
# 3) Dataclasses
# ---------------------------------------------------------------------
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
class WeeklyActivityBudget:
    activity_type: ActivityType
    subtype: str | None
    total_hours: int
    target_days: int
    flexibility: BlockFlexibility
    preferred_day_type: str = "mixed"
    preferred_weekdays: list[int] | None = None
    preferred_time_window: tuple[int, int] | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class WeeklyStructure:
    # WeeklyStructure is now a high-level budget layer. It stores weekly hour
    # budgets and distribution rules. It should not contain concrete start/end
    # times for the main model. Concrete times are generated only when creating
    # DayEpisode objects.
    persona_name: str
    phase: YearPhase
    blocks: list[WeeklyBlockTemplate] = field(default_factory=list)
    budgets: list[WeeklyActivityBudget] = field(default_factory=list)
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
class AcuteIllnessConstraint:
    duration_days: int
    intensity: str  # "low", "mid", "high"
    start_weekday: int = 0
    is_active: bool = True

    def __post_init__(self) -> None:
        if self.duration_days < 0:
            raise ValueError("duration_days must be >= 0")
        if not 0 <= self.start_weekday <= 6:
            raise ValueError("start_weekday must be between 0 and 6")
        if self.intensity not in {"low", "mid", "high"}:
            raise ValueError("intensity must be one of: low, mid, high")


def is_active_on_weekday(constraint: AcuteIllnessConstraint, weekday: int) -> bool:
    if not constraint.is_active or constraint.duration_days == 0:
        return False
    if not 0 <= weekday <= 6:
        return False
    end_weekday = min(6, constraint.start_weekday + constraint.duration_days - 1)
    return constraint.start_weekday <= weekday <= end_weekday


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

    # Zielwert für soziale Kontakte / soziale Aktivitäten in Stunden pro Woche.
    # Wenn None, verwendet das Modell die bisherige probabilistische Logik.
    social_hours_week: float | None = None



# ---------------------------------------------------------------------
# 4) Constants
# ---------------------------------------------------------------------
WEEKDAY_NAMES = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}



# ---------------------------------------------------------------------
# 5) Generic utilities
# ---------------------------------------------------------------------
def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def lerp(low: float, high: float, t: float) -> float:
    return low + (high - low) * clamp(t)


def round_to_nonnegative_int(value: float) -> int:
    return max(0, int(round(value)))


def hour_to_hhmm(hour: int) -> str:
    return f"{hour:02d}:00"



# ---------------------------------------------------------------------
# 6) Printing helpers
# ---------------------------------------------------------------------
def print_weekly_structure(structure: WeeklyStructure) -> None:
    print(f"\nWeeklyStructure: {structure.persona_name} | phase={structure.phase.value}")

    print("\nWeekly budgets:")
    if not structure.budgets:
        print("  - no budgets")
    for budget in structure.budgets:
        print(
            f"  - {budget.subtype or budget.activity_type.value} | "
            f"total={budget.total_hours}h | "
            f"target_days={budget.target_days} | "
            f"flexibility={budget.flexibility.value} | "
            f"preferred={budget.preferred_day_type}"
        )

    print("\nMetadata:")
    if not structure.metadata:
        print("  - none")
    simple_metadata_keys = {
        "default_commute_hours",
        "commute_hours_by_subtype",
        "input_fitness_hours_week",
        "input_social_hours_week",
        "input_work_hours_week",
    }

    for key in simple_metadata_keys:
        if key in structure.metadata:
            print(f"  - {key}: {structure.metadata[key]}")

    if "daily_budget_distribution" in structure.metadata:
        print("  - daily_budget_distribution: available")
    else:
        print("  - daily_budget_distribution: not generated")

    warnings = structure.metadata.get("daily_schedule_warnings")
    if isinstance(warnings, list):
        print(f"  - daily_schedule_warnings: {len(warnings)} warning(s)")

    already_handled = simple_metadata_keys | {"daily_budget_distribution", "daily_schedule_warnings"}
    for k, v in structure.metadata.items():
        if k in already_handled:
            continue
        if isinstance(v, (str, int, float, bool)) or v is None:
            print(f"  - {k}: {v}")
        elif isinstance(v, dict):
            print(f"  - {k}: <dict with {len(v)} entries>")
        elif isinstance(v, list):
            print(f"  - {k}: <list with {len(v)} entries>")
        else:
            print(f"  - {k}: <{type(v).__name__}>")


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



# ---------------------------------------------------------------------
# 13) Legacy block-based weekly scheduling helpers
# Kept temporarily for backwards compatibility, not used by the new
# budget-based pipeline.
# ---------------------------------------------------------------------
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


def _add_schedule_warning(structure: WeeklyStructure, warning: str) -> None:
    warnings = structure.metadata.setdefault("daily_schedule_warnings", [])
    warnings.append(warning)


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



# ---------------------------------------------------------------------
# 8) Weekly budget distribution
# ---------------------------------------------------------------------
def _preferred_days_for_budget(budget: WeeklyActivityBudget) -> list[int]:
    if budget.preferred_weekdays:
        return budget.preferred_weekdays
    if budget.preferred_day_type == "weekday":
        return [0, 1, 2, 3, 4]
    if budget.preferred_day_type == "weekend":
        return [5, 6]
    return [0, 1, 2, 3, 4, 5, 6]


def select_weekdays_for_budget(
    budget: WeeklyActivityBudget,
    rng: random.Random,
) -> list[int]:
    target_days = max(0, min(7, budget.target_days))
    if target_days == 0:
        return []
    preferred = [d for d in (budget.preferred_weekdays or []) if 0 <= d <= 6]
    day_pool: list[int]
    if budget.preferred_day_type == "weekday":
        day_pool = [0, 1, 2, 3, 4]
    elif budget.preferred_day_type == "weekend":
        day_pool = [5, 6]
        if target_days > 2:
            day_pool = [5, 6, 4]
    else:
        day_pool = [0, 1, 2, 3, 4, 5, 6]
    ordered: list[int] = []
    for day in preferred + day_pool:
        if day not in ordered:
            ordered.append(day)
    remaining = [d for d in range(7) if d not in ordered]
    rng.shuffle(remaining)
    ordered.extend(remaining)
    return ordered[:target_days]


def split_hours_across_days(total_hours: int, day_count: int, rng: random.Random) -> list[int]:
    total = max(0, total_hours)
    if day_count <= 0 or total <= 0:
        return []
    base = total // day_count
    remainder = total % day_count
    allocations = [base] * day_count
    for idx in rng.sample(range(day_count), remainder):
        allocations[idx] += 1
    return allocations


def distribute_weekly_budgets_to_days(
    structure: WeeklyStructure,
    rng: random.Random | None = None,
) -> dict[int, list[WeeklyActivityBudget]]:
    if rng is None:
        rng = random.Random()

    distribution: dict[int, list[WeeklyActivityBudget]] = {d: [] for d in range(7)}
    heavy_subtypes = {"university", "paid_work", "studying", "physical_activity"}
    heavy_load_by_day: dict[int, int] = {d: 0 for d in range(7)}

    budget_order = {"university": 0, "paid_work": 1, "physical_activity": 2, "studying": 3, "social_time": 4}
    budgets = sorted(structure.budgets, key=lambda b: budget_order.get(b.subtype or b.activity_type.value, 99))

    for budget in budgets:
        if budget.total_hours <= 0 or budget.target_days <= 0:
            continue

        subtype = budget.subtype or budget.activity_type.value
        candidate_days = _preferred_days_for_budget(budget)
        candidate_days = [d for d in candidate_days if 0 <= d <= 6]
        if not candidate_days:
            candidate_days = list(range(7))

        if subtype == "social_time":
            ordered_candidates = sorted(candidate_days, key=lambda d: (0 if d >= 5 else 1, heavy_load_by_day[d], d))
        else:
            ordered_candidates = sorted(candidate_days, key=lambda d: (heavy_load_by_day[d], d))

        selected_days = ordered_candidates[: max(0, min(7, budget.target_days))]
        allocations = split_hours_across_days(budget.total_hours, len(selected_days), rng)

        for day, day_hours in zip(selected_days, allocations):
            if day_hours <= 0:
                continue
            distribution[day].append(
                WeeklyActivityBudget(
                    activity_type=budget.activity_type,
                    subtype=budget.subtype,
                    total_hours=day_hours,
                    target_days=1,
                    flexibility=budget.flexibility,
                    preferred_day_type=budget.preferred_day_type,
                    preferred_weekdays=[day],
                    preferred_time_window=budget.preferred_time_window,
                    notes=list(budget.notes),
                )
            )
            if subtype in heavy_subtypes:
                heavy_load_by_day[day] += day_hours

    structure.metadata["daily_budget_distribution"] = distribution
    return distribution



# ---------------------------------------------------------------------
# 9) Daily schedule generation
# ---------------------------------------------------------------------
def _activity_window(subtype: str, phase: YearPhase, weekday: int) -> tuple[int, int]:
    if subtype == "university":
        return (8, 16)
    if subtype == "paid_work":
        return (8, 17)
    if subtype == "studying":
        return (17, 21) if phase == YearPhase.SEMESTER else (9, 18)
    if subtype == "physical_activity":
        return (15, 21)
    if subtype == "social_time":
        if weekday >= 5:
            return (14, 23)
        return (18, 23)
    return (9, 21)




def _fallback_windows_for_subtype(subtype: str, phase: YearPhase, weekday: int) -> list[tuple[int, int]]:
    if subtype == "paid_work":
        return [(8, 17), (9, 18), (13, 21)]
    if subtype == "university":
        return [(8, 16), (9, 17)]
    if subtype == "studying":
        if phase == YearPhase.SEMESTER:
            return [(17, 21), (10, 18), (19, 22)]
        if phase == YearPhase.EXAM_PHASE:
            return [(9, 18), (13, 21), (18, 22)]
        return [(10, 18), (19, 22)]
    if subtype == "physical_activity":
        return [(15, 21), (10, 21)]
    if subtype == "social_time":
        primary = (14, 23) if weekday >= 5 else (18, 23)
        return [primary, (10, 23)]
    return [_activity_window(subtype, phase, weekday)]


def _try_place_contiguous(
    schedule: list[DayEpisode | None],
    duration: int,
    window: tuple[int, int],
    activity_type: ActivityType,
    flexibility: BlockFlexibility,
    subtype: str,
    rng: random.Random,
) -> int:
    start_min, end_max = window
    latest_start = max(start_min, end_max - duration)
    starts = list(range(start_min, latest_start + 1))
    rng.shuffle(starts)
    for start in starts:
        if all(0 <= h < 24 and schedule[h] is None for h in range(start, start + duration)):
            for h in range(start, start + duration):
                schedule[h] = DayEpisode(h, activity_type, flexibility, subtype)
            return duration
    return 0

def place_activity_in_day(
    schedule: list[DayEpisode | None],
    budget: WeeklyActivityBudget,
    weekday: int,
    phase: YearPhase,
    rng: random.Random,
) -> int:
    duration = max(0, budget.total_hours)
    if duration <= 0:
        return 0

    subtype = budget.subtype or budget.activity_type.value
    windows = _fallback_windows_for_subtype(subtype, phase, weekday)
    preferred = budget.preferred_time_window
    if preferred is not None and preferred not in windows:
        windows = [preferred] + windows

    # 1) Try to place full duration contiguously in primary/fallback windows.
    for window in windows:
        placed = _try_place_contiguous(
            schedule,
            duration,
            window,
            budget.activity_type,
            budget.flexibility,
            subtype,
            rng,
        )
        if placed == duration:
            return placed

    # 2) Studying is allowed to split into smaller chunks in free non-sleep hours.
    if subtype == "studying":
        placed = 0
        candidate_hours: list[int] = []
        for start, end in windows + [(9, 22)]:
            for h in range(max(0, start), min(24, end)):
                if h not in candidate_hours:
                    candidate_hours.append(h)
        for h in candidate_hours:
            if placed >= duration:
                break
            ep = schedule[h]
            if ep is None:
                schedule[h] = DayEpisode(h, budget.activity_type, budget.flexibility, subtype)
                placed += 1
        return placed

    # 3) Partial fallback for all other subtypes.
    placed = 0
    for start, end in windows:
        for h in range(max(0, start), min(24, end)):
            if placed >= duration:
                break
            if schedule[h] is None:
                schedule[h] = DayEpisode(h, budget.activity_type, budget.flexibility, subtype)
                placed += 1
        if placed >= duration:
            break
    return placed

def _placement_priority(budget: WeeklyActivityBudget) -> int:
    subtype = budget.subtype or budget.activity_type.value

    priority = {
        "university": 0,
        "paid_work": 1,
        "physical_activity": 2,
        "studying": 3,
        "social_time": 4,
    }

    return priority.get(subtype, 99)



# ---------------------------------------------------------------------
# 10) Constraint logic
# ---------------------------------------------------------------------
def apply_acute_illness_constraint(
    day_schedule: list[DayEpisode],
    constraint: AcuteIllnessConstraint,
    weekday: int,
) -> list[DayEpisode]:
    if not is_active_on_weekday(constraint, weekday):
        return [DayEpisode(ep.hour, ep.activity_type, ep.flexibility, ep.subtype) for ep in day_schedule]

    updated = [DayEpisode(ep.hour, ep.activity_type, ep.flexibility, ep.subtype) for ep in day_schedule]
    by_hour = {ep.hour: ep for ep in updated}

    def _replace_hours(hours: list[int], activity_type: ActivityType, subtype: str) -> None:
        for h in hours:
            ep = by_hour[h]
            by_hour[h] = DayEpisode(h, activity_type, ep.flexibility, subtype)

    physical = [ep.hour for ep in updated if ep.activity_type == ActivityType.PHYSICAL_ACTIVITY]
    social = [ep.hour for ep in updated if ep.activity_type == ActivityType.SOCIAL_TIME]
    work_like = [
        ep.hour
        for ep in updated
        if ep.activity_type == ActivityType.WORK and ep.subtype in {"paid_work", "university", "studying"}
    ]

    if constraint.intensity == "low":
        _replace_hours(physical[len(physical) // 2 :], ActivityType.DOWNTIME, "illness_recovery")
        _replace_hours(social[len(social) // 2 :], ActivityType.DOWNTIME, "illness_recovery")
    elif constraint.intensity == "mid":
        _replace_hours(physical, ActivityType.DOWNTIME, "illness_recovery")
        _replace_hours(social, ActivityType.DOWNTIME, "illness_recovery")
        _replace_hours(work_like[len(work_like) // 2 :], ActivityType.DOWNTIME, "illness_recovery")
    else:  # high
        _replace_hours(physical, ActivityType.DOWNTIME, "illness_recovery")
        _replace_hours(social, ActivityType.DOWNTIME, "illness_recovery")
        _replace_hours(work_like, ActivityType.DOWNTIME, "illness_recovery")

    sleep_targets = 2 if constraint.intensity == "mid" else 3 if constraint.intensity == "high" else 0
    if sleep_targets > 0:
        preferred_sleep_hours = [22, 21, 20, 7, 6, 5]
        converted = 0
        for h in preferred_sleep_hours:
            if converted >= sleep_targets:
                break
            ep = by_hour.get(h)
            if ep is None:
                continue
            if ep.activity_type == ActivityType.EAT:
                continue
            if ep.activity_type == ActivityType.WAKE_UP:
                continue
            if ep.activity_type == ActivityType.DOWNTIME:
                by_hour[h] = DayEpisode(h, ActivityType.SLEEP, ep.flexibility, "illness_sleep")
                converted += 1

    return [by_hour[h] for h in range(24)]


def generate_full_day_schedule(
    weekly_structure: WeeklyStructure,
    weekday: int,
    rng: random.Random | None = None,
    constraints: list[AcuteIllnessConstraint] | None = None,
) -> list[DayEpisode]:
    # This function turns the selected daily budget items into concrete hourly activities.
    if rng is None:
        rng = random.Random()

    schedule: list[DayEpisode | None] = [None] * 24

    sleep_start, wake_hour = sample_sleep_schedule(
        weekly_structure.phase,
        weekday,
        None,
        rng,
    )

    for h in list(range(sleep_start, 24)) + list(range(0, wake_hour)):
        schedule[h] = DayEpisode(
            h,
            ActivityType.SLEEP,
            BlockFlexibility.FIXED,
            "night_sleep",
        )

    if schedule[wake_hour] is None:
        schedule[wake_hour] = DayEpisode(
            wake_hour,
            ActivityType.WAKE_UP,
            BlockFlexibility.FIXED,
            "morning_wake_up",
        )

    # Meals are inserted before activities as soft anchors.
    # They only occupy free slots and do not overwrite fixed activities.
    insert_meals(schedule, wake_hour)

    distribution = weekly_structure.metadata.get("daily_budget_distribution")
    if not isinstance(distribution, dict):
        distribution = distribute_weekly_budgets_to_days(weekly_structure, rng)

    daily_items = distribution.get(weekday, [])
    sorted_items = sorted(daily_items, key=_placement_priority)

    for budget in sorted_items:
        placed = place_activity_in_day(
            schedule,
            budget,
            weekday,
            weekly_structure.phase,
            rng,
        )

        if placed < budget.total_hours:
            _add_schedule_warning(
                weekly_structure,
                f"{WEEKDAY_NAMES[weekday]}:{budget.subtype or budget.activity_type.value} "
                f"requested={budget.total_hours}h placed={placed}h",
            )

    occupied = {
        ep.hour
        for ep in schedule
        if ep is not None
        and ep.activity_type not in {ActivityType.SLEEP, ActivityType.DOWNTIME}
    }

    for h in range(24):
        if schedule[h] is None:
            schedule[h] = DayEpisode(
                h,
                ActivityType.DOWNTIME,
                BlockFlexibility.FLEXIBLE,
                classify_default_downtime_subtype(
                    h,
                    occupied,
                    wake_hour,
                    sleep_start,
                ),
            )

    day_schedule = [ep for ep in schedule if ep is not None]

    if constraints:
        for constraint in constraints:
            day_schedule = apply_acute_illness_constraint(day_schedule, constraint, weekday)

    return day_schedule

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
    """
    Add social blocks.

    If params.social_hours_week is set, social time is scheduled as an
    approximate weekly hour target. If it is None, the original probabilistic
    social-time logic is used.
    """

    if params.social_hours_week is not None:
        target_hours = max(0, round_to_nonnegative_int(params.social_hours_week))
        remaining_hours = target_hours

        candidate_windows = [
            (4, 19, 23),  # Friday evening
            (5, 14, 18),  # Saturday afternoon
            (5, 19, 23),  # Saturday evening
            (6, 14, 18),  # Sunday afternoon
            (6, 18, 22),  # Sunday evening
            (3, 19, 22),  # Thursday evening
            (2, 19, 22),  # Wednesday evening
            (1, 19, 22),  # Tuesday evening
            (0, 19, 22),  # Monday evening
        ]

        for weekday, window_start, window_end in candidate_windows:
            if remaining_hours <= 0:
                break

            max_duration = min(3, remaining_hours, window_end - window_start)
            if max_duration <= 0:
                continue

            duration = max_duration
            start_hour = window_start
            end_hour = start_hour + duration

            candidate = WeeklyBlockTemplate(
                weekday=weekday,
                start_hour=start_hour,
                end_hour=end_hour,
                activity_type=ActivityType.SOCIAL_TIME,
                flexibility=BlockFlexibility.FLEXIBLE,
                subtype="social_hours_target",
            )

            if add_block_if_possible(structure, candidate):
                remaining_hours -= duration

        return

    # Original logic
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



# ---------------------------------------------------------------------
# 7) Weekly budget generation
# ---------------------------------------------------------------------
def generate_student_week(
    params: StudentStructureParameters,
    phase: YearPhase,
    rng: random.Random | None = None,
) -> WeeklyStructure:
    if rng is None:
        rng = random.Random()

    p = phase_profile(params, phase)
    # Pipeline architecture:
    # - WeeklyStructure stores planned high-level weekly budgets.
    # - daily_budget_distribution maps these weekly budgets to selected weekdays.
    # - generate_full_day_schedule turns day-level budgets into realised hourly DayEpisodes.
    # - Constraints (e.g., AcuteIllnessConstraint) modify DayEpisodes, not weekly budgets.
    structure = WeeklyStructure(persona_name=params.name, phase=phase, metadata=build_commute_metadata(params))

    work_h = round_to_nonnegative_int(lerp(0, 20, p["employment_load"]))
    fit_h = round_to_nonnegative_int(lerp(0, 14, p["sport_frequency"]))
    social_h = round_to_nonnegative_int(params.social_hours_week if params.social_hours_week is not None else lerp(2, 10, p["weekend_social_intensity"]))
    uni_h = 0 if phase == YearPhase.HOLIDAY else round_to_nonnegative_int(lerp(8, 22, p["university_load"]))
    study_h = round_to_nonnegative_int(lerp(2, 24, p["study_intensity"]))
    if phase == YearPhase.SEMESTER:
        study_h = max(3, int(study_h * 0.45))
    elif phase == YearPhase.EXAM_PHASE:
        study_h = max(8, int(study_h * 1.0))
        uni_h = int(uni_h * 0.45)
        work_h = int(work_h * 0.9)
        social_h = int(social_h * 0.75)
        fit_h = int(fit_h * 0.9)
    else:
        study_h = int(study_h * 0.2)
        uni_h = 0

    def _td(hours: int, expr: int) -> int:
        return 0 if hours <= 0 else expr

    structure.budgets = [
        WeeklyActivityBudget(ActivityType.WORK, "paid_work", work_h, _td(work_h, min(5, max(0, (work_h + 5)//6))), BlockFlexibility.FIXED, "weekday", [0,1,2,3,4], (8,18)),
        WeeklyActivityBudget(ActivityType.PHYSICAL_ACTIVITY, "physical_activity", fit_h, _td(fit_h, min(7, max(0, (fit_h + 2)//3))), BlockFlexibility.FIXED if params.sport_fixedness > 0.5 else BlockFlexibility.FLEXIBLE, "mixed", None, (14,21)),
        WeeklyActivityBudget(ActivityType.SOCIAL_TIME, "social_time", social_h, _td(social_h, min(4, max(0, (social_h + 1)//3))), BlockFlexibility.FLEXIBLE, "weekend", [4,5,6], (18,23)),
        WeeklyActivityBudget(ActivityType.WORK, "university", uni_h, _td(uni_h, min(5, max(0, (uni_h + 4)//6))), BlockFlexibility.FIXED, "weekday", [0,1,2,3,4], (8,16)),
        WeeklyActivityBudget(ActivityType.WORK, "studying", study_h, _td(study_h, min(6, max(0, (study_h + 2)//4))), BlockFlexibility.FLEXIBLE, "weekday", None, (10,21)),
    ]

    return structure




# ---------------------------------------------------------------------
# 11) Validation helpers
# ---------------------------------------------------------------------
def validate_weekly_structure(structure: WeeklyStructure) -> dict[str, object]:
    warnings: list[str] = []
    total_budget_hours = sum(max(0, b.total_hours) for b in structure.budgets)
    for b in structure.budgets:
        if b.total_hours < 0:
            warnings.append(f"Negative hours in {b.subtype or b.activity_type.value}")
        if b.target_days < 0 or b.target_days > 7:
            warnings.append(f"Invalid target_days in {b.subtype or b.activity_type.value}")
        if b.total_hours == 0 and b.target_days > 0:
            warnings.append(f"{b.subtype or b.activity_type.value} has target_days>0 but total_hours=0")
    if total_budget_hours > 112:
        warnings.append(f"Total weekly budget too high: {total_budget_hours}h")
    return {"ok": len(warnings) == 0, "warnings": warnings, "total_budget_hours": total_budget_hours}


def validate_full_day_schedule(day_schedule: list[DayEpisode]) -> dict[str, object]:
    warnings: list[str] = []
    hours = [ep.hour for ep in day_schedule]
    if len(day_schedule) != 24:
        warnings.append("Schedule does not contain exactly 24 episodes")
    if len(set(hours)) != len(hours):
        warnings.append("Duplicate hours detected")
    sleep_hours = sum(1 for ep in day_schedule if ep.activity_type == ActivityType.SLEEP)
    occupied_hours = sum(1 for ep in day_schedule if ep.activity_type != ActivityType.SLEEP)
    productive_hours = sum(1 for ep in day_schedule if ep.activity_type not in {ActivityType.SLEEP, ActivityType.DOWNTIME})
    meal_subtypes = {ep.subtype for ep in day_schedule if ep.activity_type == ActivityType.EAT}
    if sleep_hours < 6:
        warnings.append("Less than 6 hours sleep")
    if productive_hours > 14:
        warnings.append("More than 14 non-sleep productive hours")
    if "lunch" not in meal_subtypes:
        warnings.append("No lunch was placed")
    if "dinner" not in meal_subtypes:
        warnings.append("No dinner was placed")
    streak = 0
    max_streak = 0
    for ep in sorted(day_schedule, key=lambda x: x.hour):
        if ep.activity_type not in {ActivityType.SLEEP, ActivityType.DOWNTIME}:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    if max_streak > 10:
        warnings.append("More than 10 consecutive non-sleep, non-downtime hours")
    return {"ok": len(warnings) == 0, "warnings": warnings, "sleep_hours": sleep_hours, "occupied_hours": occupied_hours}


def validate_weekly_budget_consistency(
    structure: WeeklyStructure,
    week_schedules: dict[int, list[DayEpisode]],
) -> dict[str, object]:
    summary: list[dict[str, object]] = []
    warnings: list[str] = []
    for budget in structure.budgets:
        subtype = budget.subtype or budget.activity_type.value
        scheduled_hours = 0
        active_days = 0
        for weekday in range(7):
            day_eps = week_schedules.get(weekday, [])
            day_hours = sum(1 for ep in day_eps if (ep.subtype or ep.activity_type.value) == subtype)
            scheduled_hours += day_hours
            if day_hours > 0:
                active_days += 1
        if abs(scheduled_hours - budget.total_hours) > 1:
            warnings.append(f"{subtype}: budget={budget.total_hours}h scheduled={scheduled_hours}h")
        if budget.target_days > 0 and abs(active_days - budget.target_days) > 1:
            warnings.append(f"{subtype}: target_days={budget.target_days} actual_days={active_days}")
        summary.append(
            {
                "subtype": subtype,
                "budget_hours": budget.total_hours,
                "scheduled_hours": scheduled_hours,
                "target_days": budget.target_days,
                "actual_days": active_days,
            }
        )
    return {"ok": len(warnings) == 0, "warnings": warnings, "summary": summary}



# ---------------------------------------------------------------------
# 12) Parameter summaries / demo main
# ---------------------------------------------------------------------
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
