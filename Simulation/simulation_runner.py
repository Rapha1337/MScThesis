from __future__ import annotations

import random
from dataclasses import replace
from typing import Any, TYPE_CHECKING

from agent_context import build_agent_context
from constraints.manager import ConstraintManager
from constraints.illness import AcuteIllnessConstraint
from energy_model import EnergyModel
from intensity import normalize_intensity
from persona_wrappers import StudentHoursWrapper
from schedule_model_student import (
    ActivityType,
    DayEpisode,
    YearPhase,
    generate_full_day_schedule,
)
from year_structure import YearStructureGenerator

if TYPE_CHECKING:
    from env_time_weather import TimeWeatherEnv


class SimulationRunner:
    def __init__(
        self,
        persona: StudentHoursWrapper,
        phase: YearPhase,
        env: Any,
        constraint_manager: ConstraintManager | None = None,
        seed: int = 37,
        n_weeks: int = 52,
        use_year_structure: bool = True,
    ) -> None:
        self.persona = persona
        self.phase = phase
        self.env = env
        self.constraint_manager = constraint_manager or ConstraintManager()
        self.seed = seed
        self.n_weeks = n_weeks
        self.use_year_structure = use_year_structure

        self._last_world_info: dict[str, object] | None = None
        self.energy_model = EnergyModel()

        self._sim_hour = 0

        self.year_structure = None
        self._weekly_structure_cache: dict[int, Any] = {}
        self._day_schedule_cache: dict[tuple[int, int], list[DayEpisode]] = {}

        if self.use_year_structure:
            self.year_structure = YearStructureGenerator().generate_year(
                persona_id=self.persona.name,
                persona_seed=self.seed,
                parameters=self.persona,
                n_weeks=self.n_weeks,
            )
        else:
            self.weekly_structure = self.persona.generate_week(
                phase=self.phase,
                seed=self.seed,
            )

    def _episode_to_dict(self, episode: DayEpisode) -> dict[str, object]:
        return {
            "hour": episode.hour,
            "activity_type": episode.activity_type.value,
            "subtype": episode.subtype,
            "flexibility": episode.flexibility.value,
        }

    def _derive_time_indices(self) -> tuple[int, int, int]:
        week_index = (self._sim_hour // (7 * 24)) % self.n_weeks
        weekday = (self._sim_hour // 24) % 7
        hour = self._sim_hour % 24
        return int(week_index), int(weekday), int(hour)

    def _get_week_plan(self, week_index: int) -> Any:
        if self.year_structure is None:
            return None
        return self.year_structure.weeks[week_index]

    def _get_event_by_id(self, event_id: str) -> Any | None:
        if self.year_structure is None:
            return None

        for event in self.year_structure.events:
            if getattr(event, "event_id", None) == event_id:
                return event

        return None

    def _event_active_on_day(self, event: Any, week_index: int, weekday: int) -> bool:
        event_start_week = int(getattr(event, "start_week", getattr(event, "week_index", 0)))
        event_start_day = int(getattr(event, "start_day", getattr(event, "weekday", 0)))
        duration_days = int(getattr(event, "duration_days", 1))

        event_start_abs_day = event_start_week * 7 + event_start_day
        event_end_abs_day = event_start_abs_day + duration_days
        current_abs_day = week_index * 7 + weekday

        return event_start_abs_day <= current_abs_day < event_end_abs_day

    def _get_active_events_for_day(self, week_index: int, weekday: int) -> list[Any]:
        if self.year_structure is None:
            return []

        active_events: list[Any] = []

        for event in self.year_structure.events:
            if self._event_active_on_day(event, week_index, weekday):
                active_events.append(event)

        return active_events

    def _illness_intensity_for_constraint(self, intensity: str | None) -> str:
        return str(normalize_intensity(intensity, default="low"))

    def _events_to_constraints(
        self,
        events: list[Any],
        week_index: int,
        weekday: int,
    ) -> list[Any]:
        constraints: list[Any] = []

        for event in events:
            event_type = getattr(event, "event_type", None)

            if event_type != "illness":
                continue

            intensity = self._illness_intensity_for_constraint(
                getattr(event, "intensity", None)
            )

            start_week = int(getattr(event, "start_week", getattr(event, "week_index", week_index)))
            start_day = int(getattr(event, "start_day", getattr(event, "weekday", weekday)))
            duration_days = int(getattr(event, "duration_days", 1))

            constraints.append(
                AcuteIllnessConstraint(
                    name=getattr(event, "event_id", "year_structure_illness"),
                    intensity=intensity,
                    start_weekday=start_day,
                    duration_days=duration_days,
                )
            )

        return constraints

    def _apply_public_holiday_effect(
        self,
        day_schedule: list[DayEpisode],
        active_events: list[Any],
    ) -> list[DayEpisode]:
        has_public_holiday = any(
            getattr(event, "event_type", None) == "public_holiday"
            for event in active_events
        )

        if not has_public_holiday:
            return day_schedule

        work_like_subtypes = {"university", "paid_work", "studying"}
        work_like_activity_values = {"work", "studying"}

        updated_schedule: list[DayEpisode] = []

        for episode in day_schedule:
            activity_value = getattr(episode.activity_type, "value", episode.activity_type)
            is_work_like = (
                str(activity_value) in work_like_activity_values
                or episode.subtype in work_like_subtypes
            )

            if is_work_like:
                updated_schedule.append(
                    replace(
                        episode,
                        activity_type=ActivityType.DOWNTIME,
                        subtype="public_holiday",
                    )
                )
            else:
                updated_schedule.append(episode)

        return updated_schedule

    def _get_weekly_structure_for_week(self, week_index: int) -> Any:
        if not self.use_year_structure:
            return self.weekly_structure

        if week_index in self._weekly_structure_cache:
            return self._weekly_structure_cache[week_index]

        week_plan = self._get_week_plan(week_index)
        phase = YearPhase.coerce(week_plan.phase)

        week_seed = self.seed + week_index * 10_000

        weekly_structure = self.persona.generate_week(
            phase=phase,
            seed=week_seed,
        )

        self._weekly_structure_cache[week_index] = weekly_structure
        return weekly_structure

    def _generate_day_schedule_for_weekday(
        self,
        week_index: int,
        weekday: int,
    ) -> list[DayEpisode]:
        cache_key = (week_index, weekday)

        if cache_key in self._day_schedule_cache:
            return self._day_schedule_cache[cache_key]

        weekly_structure = self._get_weekly_structure_for_week(week_index)
        active_events = self._get_active_events_for_day(week_index, weekday)
        event_constraints = self._events_to_constraints(active_events, week_index, weekday)

        day_seed = self.seed + week_index * 10_000 + weekday

        day_schedule = generate_full_day_schedule(
            weekly_structure,
            weekday,
            rng=random.Random(day_seed),
            constraints=event_constraints,
        )

        day_schedule = self._apply_public_holiday_effect(
            day_schedule,
            active_events,
        )

        day_schedule = self.constraint_manager.apply_constraints(
            day_schedule,
            weekday,
        )

        self._day_schedule_cache[cache_key] = day_schedule
        return day_schedule

    def generate_normal_day(self, weekday: int) -> list[DayEpisode]:
        if not self.use_year_structure:
            return generate_full_day_schedule(
                self.weekly_structure,
                weekday,
                rng=random.Random(self.seed + weekday),
            )

        week_index, _, _ = self._derive_time_indices()
        return self._generate_day_schedule_for_weekday(week_index, weekday)

    def generate_constrained_day(self, weekday: int) -> list[DayEpisode]:
        if not self.use_year_structure:
            normal = self.generate_normal_day(weekday)
            return self.constraint_manager.apply_constraints(normal, weekday)

        week_index, _, _ = self._derive_time_indices()
        return self._generate_day_schedule_for_weekday(week_index, weekday)

    def reset_world(self) -> dict[str, object]:
        _, info = self.env.reset(seed=self.seed)
        self._last_world_info = info
        self._sim_hour = 0
        return info

    def step_world(self, action: int = 0) -> dict[str, object]:
        _, _, _, _, info = self.env.step(action)
        self._last_world_info = info

        delta_hours = int(info.get("delta_hours", 1)) if isinstance(info, dict) else 1
        self._sim_hour += max(delta_hours, 1)

        return info

    def inspect_agent_day_schedule(
        self,
        week_index: int,
        weekday: int,
    ) -> dict[str, object]:
        if self.year_structure is None:
            raise RuntimeError("inspect_agent_day_schedule requires use_year_structure=True.")

        week_plan = self._get_week_plan(week_index)
        active_events = self._get_active_events_for_day(week_index, weekday)
        day_schedule = self._generate_day_schedule_for_weekday(week_index, weekday)

        return {
            "agent_id": self.persona.name,
            "week_index": week_index,
            "weekday": weekday,
            "phase": week_plan.phase,
            "fixed_block_tag": getattr(week_plan, "fixed_block_tag", None),
            "active_event_ids": [
                getattr(event, "event_id", None)
                for event in active_events
            ],
            "active_event_types": [
                getattr(event, "event_type", None)
                for event in active_events
            ],
            "day_schedule": [
                self._episode_to_dict(episode)
                for episode in day_schedule
            ],
        }

    def get_day_context(self, weekday: int) -> dict:
        if self.use_year_structure:
            week_index, _, hour = self._derive_time_indices()
            normal_schedule = self._generate_day_schedule_for_weekday(week_index, weekday)
            constrained_schedule = normal_schedule
            phase = YearPhase.coerce(self._get_week_plan(week_index).phase)
        else:
            normal_schedule = self.generate_normal_day(weekday)
            constrained_schedule = self.generate_constrained_day(weekday)
            phase = self.phase
            world_info = self._last_world_info if self._last_world_info is not None else self.reset_world()
            hour = int(world_info.get("hour", 12)) if isinstance(world_info, dict) else 12

        active_constraints = [
            {
                "name": constraint.name,
                "type": constraint.__class__.__name__,
                "intensity": getattr(constraint, "intensity", None),
            }
            for constraint in self.constraint_manager.get_active_constraints(weekday)
        ]

        world_info = self._last_world_info if self._last_world_info is not None else self.reset_world()

        energy_state = self.energy_model.compute_energy_state(
            hour=hour,
            phase=phase,
            active_constraints=active_constraints,
            constrained_schedule=[self._episode_to_dict(ep) for ep in constrained_schedule],
            seed=self.seed + weekday,
        )

        return build_agent_context(
            persona_name=self.persona.name,
            phase=phase,
            weekday=weekday,
            world_info=world_info,
            active_constraints=active_constraints,
            normal_schedule=[self._episode_to_dict(ep) for ep in normal_schedule],
            constrained_schedule=[self._episode_to_dict(ep) for ep in constrained_schedule],
            energy_state=energy_state,
        )


if __name__ == "__main__":
    from env_time_weather import TimeWeatherEnv

    env = TimeWeatherEnv(month=1)

    persona = StudentHoursWrapper.from_zve_student_generic(
        name="demo_student"
    )

    for test_seed in [37, 123, 222, 333, 444, 555, 777, 999, 1234, 2026]:
        runner = SimulationRunner(
            persona=persona,
            phase=YearPhase.SEMESTER,
            env=env,
            seed=test_seed,
            use_year_structure=True,
        )

        illness_event = next(
            (
                event
                for event in runner.year_structure.events
                if event.event_type == "illness"
            ),
            None,
        )

        if illness_event is not None:
            print(f"Found illness with seed={test_seed}")
            print(
                runner.inspect_agent_day_schedule(
                    week_index=illness_event.start_week,
                    weekday=illness_event.start_day,
                )
            )
            break

    print("YEAR STRUCTURE DEBUG")
    print("====================")

    print("\nExample generated year:")
    print(f"phase_counts: {runner.year_structure.phase_counts}")
    print(f"events: {[event.event_id for event in runner.year_structure.events]}")

    public_holiday_event = next(
        (
            event
            for event in runner.year_structure.events
            if event.event_type == "public_holiday"
        ),
        None,
    )

    illness_event = next(
        (
            event
            for event in runner.year_structure.events
            if event.event_type == "illness"
        ),
        None,
    )

    if public_holiday_event is not None:
        print("\nPUBLIC HOLIDAY DAY")
        print("------------------")
        print(
            runner.inspect_agent_day_schedule(
                week_index=public_holiday_event.start_week,
                weekday=public_holiday_event.start_day,
            )
        )
    else:
        print("\nNo public holiday event found for this seed.")

    if illness_event is not None:
        print("\nILLNESS DAY")
        print("-----------")
        print(
            runner.inspect_agent_day_schedule(
                week_index=illness_event.start_week,
                weekday=illness_event.start_day,
            )
        )
    else:
        print("\nNo illness event found for this seed.")

    print("\nNORMAL DAY")
    print("----------")
    print(
        runner.inspect_agent_day_schedule(
            week_index=10,
            weekday=1,
        )
    )