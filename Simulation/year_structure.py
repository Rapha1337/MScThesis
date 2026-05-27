from __future__ import annotations

from dataclasses import asdict, dataclass, field
import random

ALLOWED_PHASES = {"normal", "high_stress", "holiday"}
ALLOWED_INTENSITIES = {"low", "medium", "high"}


@dataclass
class YearStructureConfig:
    n_weeks: int = 52
    strategy: str = "rule_based_stochastic_v1"
    phase_target_ranges: dict[str, tuple[int, int]] = field(
        default_factory=lambda: {
            "normal": (28, 34),
            "high_stress": (6, 10),
            "holiday": (12, 18),
        }
    )
    fixed_phase_blocks: list[dict[str, object]] = field(default_factory=list)
    block_jitter_weeks: int = 1
    allow_phase_adjacency_rules: bool = True

    holiday_block_ranges: dict[str, tuple[int, int]] = field(
        default_factory=lambda: {
            "winter_holiday": (4, 6),
            "summer_holiday": (8, 12),
        }
    )
    holiday_block_placement_windows: dict[str, list[tuple[int, int]]] = field(
        default_factory=lambda: {
            "winter_holiday": [(0, 7), (47, 51)],
            "summer_holiday": [(23, 36)],
        }
    )
    holiday_block_jitter_weeks: int = 1

    illness_enabled: bool = True
    illness_occurrence_prob = 0.80
    illness_episode_count_probs = {
        0: 0.20,
        1: 0.50,
        2: 0.25,
        3: 0.05,
    }
    illness_duration_days_probs: dict[int, float] = field(
        default_factory=lambda: {1: 0.15, 2: 0.30, 3: 0.30, 4: 0.15, 5: 0.10}
    )
    illness_intensity_probs: dict[str, float] = field(
        default_factory=lambda: {"low": 0.55, "medium": 0.35, "high": 0.10}
    )

    public_holidays_enabled: bool = True
    public_holiday_days_range: tuple[int, int] = (9, 13)
    event_default_intensity: dict[str, str] = field(
        default_factory=lambda: {"public_holiday": "low", "illness": "low"}
    )

    seed_namespace: str = "year_structure_v1"
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class ConstraintEvent:
    event_id: str
    event_type: str = "illness"
    persona_id: str = ""
    start_week: int = 0
    start_day: int = 0
    duration_days: int = 1
    intensity: str = "low"
    parameters: dict[str, object] = field(default_factory=dict)
    source: str = "stochastic"
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class WeekPlan:
    week_index: int
    phase: str = "normal"
    fixed_block_tag: str | None = None
    active_event_ids: list[str] = field(default_factory=list)
    constraints_week_view: list[dict[str, object]] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class YearStructure:
    persona_id: str
    persona_seed: int
    n_weeks: int = 52
    weeks: list[WeekPlan] = field(default_factory=list)
    events: list[ConstraintEvent] = field(default_factory=list)
    phase_counts: dict[str, int] = field(
        default_factory=lambda: {"normal": 0, "high_stress": 0, "holiday": 0}
    )
    generation_strategy: str = "rule_based_stochastic_v1"
    config_snapshot: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


class YearStructureGenerator:
    def __init__(self, config: YearStructureConfig | None = None) -> None:
        self.config = config or YearStructureConfig()
        self._validate_config(self.config)

    def generate_year(
        self,
        persona_id: str,
        persona_seed: int,
        parameters: object,
        n_weeks: int | None = None,
    ) -> YearStructure:
        effective_n_weeks = self.config.n_weeks if n_weeks is None else n_weeks
        if effective_n_weeks < 1:
            raise ValueError("n_weeks must be >= 1")

        weeks = self.build_phase_plan(persona_seed=persona_seed, n_weeks=effective_n_weeks)
        events = self.sample_constraint_events(
            persona_id=persona_id,
            persona_seed=persona_seed,
            n_weeks=effective_n_weeks,
            weeks=weeks,
        )
        weeks = self.attach_events_to_weeks(weeks=weeks, events=events, n_weeks=effective_n_weeks)
        phase_counts = self.compute_phase_counts(weeks)

        if len(weeks) != effective_n_weeks:
            raise ValueError("len(weeks) must equal n_weeks")

        block_counts: dict[str, int] = {}
        for week in weeks:
            tag = week.fixed_block_tag
            if not tag:
                continue
            block_counts[tag] = block_counts.get(tag, 0) + 1

        ys = YearStructure(
            persona_id=persona_id,
            persona_seed=persona_seed,
            n_weeks=effective_n_weeks,
            weeks=weeks,
            events=events,
            phase_counts=phase_counts,
            generation_strategy=self.config.strategy,
            config_snapshot=asdict(self.config),
            metadata={
                "seed_namespace": self.config.seed_namespace,
                "phase_seed": self._subseed(persona_seed, "phase"),
                "event_seed": self._subseed(persona_seed, "events"),
                "parameters_type": type(parameters).__name__,
                "block_counts": block_counts,
            },
        )
        self._validate_year_structure(ys)
        return ys

    def build_phase_plan(self, persona_seed: int, n_weeks: int) -> list[WeekPlan]:
        rng = random.Random(self._subseed(persona_seed, "phase"))

        mins = {k: v[0] for k, v in self.config.phase_target_ranges.items()}
        maxs = {k: v[1] for k, v in self.config.phase_target_ranges.items()}
        weeks = [WeekPlan(week_index=i, phase="normal") for i in range(n_weeks)]
        reserved_holiday_indices = self._reserve_fixed_holiday_blocks(weeks=weeks, n_weeks=n_weeks, rng=rng)

        counts = mins.copy()
        remaining = n_weeks - sum(counts.values())
        if remaining < 0:
            raise ValueError("Sum of minimum phase counts exceeds n_weeks")

        phases = ["normal", "high_stress", "holiday"]
        while remaining > 0:
            candidates = [p for p in phases if counts[p] < maxs[p]]
            if not candidates:
                candidates = phases
            choice = rng.choice(candidates)
            counts[choice] += 1
            remaining -= 1

        counts["holiday"] = max(counts["holiday"], len(reserved_holiday_indices))
        if counts["holiday"] > maxs["holiday"]:
            counts["holiday"] = maxs["holiday"]

        non_holiday_total = n_weeks - counts["holiday"]
        if counts["normal"] + counts["high_stress"] > non_holiday_total:
            overflow = counts["normal"] + counts["high_stress"] - non_holiday_total
            reduce_high = min(overflow, counts["high_stress"] - mins["high_stress"])
            counts["high_stress"] -= max(0, reduce_high)
            overflow -= max(0, reduce_high)
            reduce_normal = min(overflow, counts["normal"] - mins["normal"])
            counts["normal"] -= max(0, reduce_normal)
            overflow -= max(0, reduce_normal)
            if overflow > 0:
                take_from_high = min(overflow, counts["high_stress"])
                counts["high_stress"] -= take_from_high
                overflow -= take_from_high
                counts["normal"] = max(0, counts["normal"] - overflow)

        fill_counts = counts.copy()
        fill_counts["holiday"] = max(0, counts["holiday"] - len(reserved_holiday_indices))

        phase_values: list[str] = []
        for phase in phases:
            phase_values.extend([phase] * fill_counts[phase])
        rng.shuffle(phase_values)

        if self.config.allow_phase_adjacency_rules:
            for _ in range(6):
                changed = False
                for i in range(1, len(phase_values) - 1):
                    if phase_values[i] == "high_stress" and phase_values[i - 1] != "high_stress" and phase_values[i + 1] != "high_stress":
                        j = rng.randrange(len(phase_values))
                        phase_values[i], phase_values[j] = phase_values[j], phase_values[i]
                        changed = True
                if not changed:
                    break

        free_indices = [idx for idx in range(n_weeks) if idx not in reserved_holiday_indices]
        for pos, idx in enumerate(free_indices):
            weeks[idx].phase = phase_values[pos]
        for idx in reserved_holiday_indices:
            weeks[idx].phase = "holiday"
        self._validate_weeks(weeks, n_weeks)
        return weeks

    def _reserve_fixed_holiday_blocks(self, weeks: list[WeekPlan], n_weeks: int, rng: random.Random) -> set[int]:
        reserved: set[int] = set()
        for tag, (min_v, max_v) in self.config.holiday_block_ranges.items():
            block_len = rng.randint(min_v, max_v)
            windows = self.config.holiday_block_placement_windows.get(tag, [(0, n_weeks - 1)])
            start = self._sample_block_start(windows=windows, block_len=block_len, n_weeks=n_weeks, rng=rng)
            if start is None:
                continue
            for idx in range(start, start + block_len):
                weeks[idx].phase = "holiday"
                weeks[idx].fixed_block_tag = tag
                reserved.add(idx)
        return reserved

    def _sample_block_start(
        self,
        windows: list[tuple[int, int]],
        block_len: int,
        n_weeks: int,
        rng: random.Random,
    ) -> int | None:
        valid_starts: list[int] = []
        for start, end in windows:
            lo = max(0, start)
            hi = min(n_weeks - 1, end)
            if hi < lo:
                continue
            latest_start = hi - block_len + 1
            if latest_start < lo:
                continue
            valid_starts.extend(range(lo, latest_start + 1))
        if not valid_starts:
            return None
        return rng.choice(valid_starts)

    def sample_constraint_events(
        self,
        persona_id: str,
        persona_seed: int,
        n_weeks: int,
        weeks: list[WeekPlan],
    ) -> list[ConstraintEvent]:
        del weeks
        rng = random.Random(self._subseed(persona_seed, "events"))
        events: list[ConstraintEvent] = []

        if self.config.illness_enabled and rng.random() <= self.config.illness_occurrence_prob:
            episode_count = int(self._sample_discrete(rng, self.config.illness_episode_count_probs))
            for idx in range(episode_count):
                start_week = rng.randrange(n_weeks)
                start_day = rng.randrange(7)
                duration_days = int(self._sample_discrete(rng, self.config.illness_duration_days_probs))
                intensity = str(self._sample_discrete(rng, self.config.illness_intensity_probs))

                max_days_available = (n_weeks - start_week - 1) * 7 + (7 - start_day)
                event_meta: dict[str, object] = {}
                if duration_days > max_days_available:
                    event_meta["truncated_at_year_end"] = True
                    event_meta["original_duration_days"] = duration_days
                    duration_days = max_days_available
                    event_meta["effective_duration_days"] = duration_days

                events.append(
                    ConstraintEvent(
                        event_id=f"illness_{idx + 1:04d}",
                        event_type="illness",
                        persona_id=persona_id,
                        start_week=start_week,
                        start_day=start_day,
                        duration_days=max(1, duration_days),
                        intensity=intensity,
                        source="stochastic",
                        metadata=event_meta,
                    )
                )

        if self.config.public_holidays_enabled:
            low, high = self.config.public_holiday_days_range
            n_public = rng.randint(low, high)
            used_days: set[tuple[int, int]] = set()
            attempts = 0
            while len(used_days) < n_public and attempts < n_public * 30:
                attempts += 1
                sw = rng.randrange(n_weeks)
                sd = rng.randrange(7)
                if (sw, sd) in used_days:
                    continue
                used_days.add((sw, sd))
            for idx, (sw, sd) in enumerate(sorted(used_days)):
                events.append(
                    ConstraintEvent(
                        event_id=f"public_holiday_{idx + 1:04d}",
                        event_type="public_holiday",
                        persona_id=persona_id,
                        start_week=sw,
                        start_day=sd,
                        duration_days=1,
                        intensity=self.config.event_default_intensity.get("public_holiday", "low"),
                        source="calendar",
                        metadata={"calendar_type": "synthetic_dach_like"},
                    )
                )

        for event in events:
            self._validate_event(event, n_weeks)
        return events

    def attach_events_to_weeks(
        self,
        weeks: list[WeekPlan],
        events: list[ConstraintEvent],
        n_weeks: int,
    ) -> list[WeekPlan]:
        self._validate_weeks(weeks, n_weeks)

        for event in events:
            start_abs_day = event.start_week * 7 + event.start_day
            end_abs_day = start_abs_day + event.duration_days - 1
            start_week = start_abs_day // 7
            end_week = min(n_weeks - 1, end_abs_day // 7)

            for week_idx in range(start_week, end_week + 1):
                week = weeks[week_idx]
                if event.event_id not in week.active_event_ids:
                    week.active_event_ids.append(event.event_id)
                week.constraints_week_view.append(
                    {
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "start_day": event.start_day if week_idx == event.start_week else 0,
                        "duration_days": event.duration_days,
                        "intensity": event.intensity,
                        "source": event.source,
                    }
                )

        return weeks

    def compute_phase_counts(self, weeks: list[WeekPlan]) -> dict[str, int]:
        counts = {"normal": 0, "high_stress": 0, "holiday": 0}
        for week in weeks:
            if week.phase not in counts:
                raise ValueError(f"Invalid phase in week plan: {week.phase}")
            counts[week.phase] += 1
        return counts

    def _validate_config(self, config: YearStructureConfig) -> None:
        if config.n_weeks < 1:
            raise ValueError("n_weeks must be >= 1")
        required = {"normal", "high_stress", "holiday"}
        if set(config.phase_target_ranges.keys()) != required:
            raise ValueError("phase_target_ranges must contain exactly normal, high_stress, holiday")
        for phase, (min_v, max_v) in config.phase_target_ranges.items():
            if phase not in ALLOWED_PHASES:
                raise ValueError(f"Invalid phase in phase_target_ranges: {phase}")
            if not (0 <= min_v <= max_v <= config.n_weeks):
                raise ValueError(f"Invalid range for phase '{phase}': {(min_v, max_v)}")

        for tag, (min_v, max_v) in config.holiday_block_ranges.items():
            if not tag:
                raise ValueError("holiday_block_ranges contains empty tag")
            if not (0 <= min_v <= max_v <= config.n_weeks):
                raise ValueError(f"Invalid holiday block range for '{tag}': {(min_v, max_v)}")

        if config.public_holiday_days_range[0] < 0 or config.public_holiday_days_range[1] < config.public_holiday_days_range[0]:
            raise ValueError("public_holiday_days_range must be valid")

        self._validate_probabilities(config.illness_episode_count_probs, "illness_episode_count_probs")
        self._validate_probabilities(config.illness_duration_days_probs, "illness_duration_days_probs")
        self._validate_probabilities(config.illness_intensity_probs, "illness_intensity_probs")
        if any(k not in ALLOWED_INTENSITIES for k in config.illness_intensity_probs):
            raise ValueError("illness_intensity_probs keys must be low/medium/high")

        for _, intensity in config.event_default_intensity.items():
            if intensity not in ALLOWED_INTENSITIES:
                raise ValueError("event_default_intensity values must be low/medium/high")

    def _validate_probabilities(self, probs: dict[object, float], name: str) -> None:
        if not probs:
            raise ValueError(f"{name} must not be empty")
        total = sum(float(v) for v in probs.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"{name} probabilities must sum to 1.0 (+/-1e-6), got {total}")
        if any(float(v) < 0 for v in probs.values()):
            raise ValueError(f"{name} probabilities must be >= 0")

    def _validate_event(self, event: ConstraintEvent, n_weeks: int) -> None:
        if event.start_week < 0 or event.start_week >= n_weeks:
            raise ValueError("start_week out of bounds")
        if not 0 <= event.start_day <= 6:
            raise ValueError("start_day must be between 0 and 6")
        if event.duration_days < 1:
            raise ValueError("duration_days must be >= 1")
        if event.intensity not in ALLOWED_INTENSITIES:
            raise ValueError("intensity must be canonical: low/medium/high")

    def _validate_weeks(self, weeks: list[WeekPlan], n_weeks: int) -> None:
        if len(weeks) != n_weeks:
            raise ValueError("len(weeks) must equal n_weeks")
        indices = set()
        for week in weeks:
            if week.phase not in ALLOWED_PHASES:
                raise ValueError(f"Invalid phase: {week.phase}")
            if not 0 <= week.week_index < n_weeks:
                raise ValueError("week_index out of range")
            indices.add(week.week_index)
        if len(indices) != n_weeks:
            raise ValueError("weeks must cover each week_index exactly once")

    def _validate_year_structure(self, year: YearStructure) -> None:
        self._validate_weeks(year.weeks, year.n_weeks)
        counts = self.compute_phase_counts(year.weeks)
        if counts != year.phase_counts:
            raise ValueError("phase_counts inconsistent with weeks")
        if sum(year.phase_counts.values()) != year.n_weeks:
            raise ValueError("phase_counts must sum to n_weeks")

    def _sample_discrete(self, rng: random.Random, probs: dict[object, float]) -> object:
        keys = list(probs.keys())
        weights = [float(probs[k]) for k in keys]
        return rng.choices(keys, weights=weights, k=1)[0]

    def _subseed(self, base_seed: int, stream: str) -> int:
        seed_str = f"{self.config.seed_namespace}:{base_seed}:{stream}"
        return sum((idx + 1) * ord(ch) for idx, ch in enumerate(seed_str))
