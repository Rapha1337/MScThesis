from __future__ import annotations

import random
from typing import Any, TYPE_CHECKING

from agent_context import build_agent_context
from constraints.manager import ConstraintManager
from energy_model import EnergyModel
from persona_wrappers import StudentHoursWrapper
from schedule_model_student import DayEpisode, YearPhase, generate_full_day_schedule

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
    ) -> None:
        self.persona = persona
        self.phase = phase
        self.env = env
        self.constraint_manager = constraint_manager or ConstraintManager()
        self.seed = seed
        self.weekly_structure = self.persona.generate_week(phase=self.phase, seed=self.seed)
        self._last_world_info: dict[str, object] | None = None
        self.energy_model = EnergyModel()

    def _episode_to_dict(self, episode: DayEpisode) -> dict[str, object]:
        return {
            "hour": episode.hour,
            "activity_type": episode.activity_type.value,
            "subtype": episode.subtype,
            "flexibility": episode.flexibility.value,
        }

    def generate_normal_day(self, weekday: int) -> list[DayEpisode]:
        return generate_full_day_schedule(
            self.weekly_structure,
            weekday,
            rng=random.Random(self.seed + weekday),
        )

    def generate_constrained_day(self, weekday: int) -> list[DayEpisode]:
        normal = self.generate_normal_day(weekday)
        return self.constraint_manager.apply_constraints(normal, weekday)

    def reset_world(self) -> dict[str, object]:
        _, info = self.env.reset(seed=self.seed)
        self._last_world_info = info
        return info

    def step_world(self, action: int = 0) -> dict[str, object]:
        _, _, _, _, info = self.env.step(action)
        self._last_world_info = info
        return info

    def get_day_context(self, weekday: int) -> dict:
        normal_schedule = self.generate_normal_day(weekday)
        constrained_schedule = self.generate_constrained_day(weekday)
        active_constraints = [
            {
                "name": constraint.name,
                "type": constraint.__class__.__name__,
                "intensity": getattr(constraint, "intensity", None),
            }
            for constraint in self.constraint_manager.get_active_constraints(weekday)
        ]

        world_info = self._last_world_info if self._last_world_info is not None else self.reset_world()
        hour = int(world_info.get("hour", 12)) if isinstance(world_info, dict) else 12
        energy_state = self.energy_model.compute_energy_state(
            hour=hour,
            phase=self.phase,
            active_constraints=active_constraints,
            constrained_schedule=[self._episode_to_dict(ep) for ep in constrained_schedule],
            seed=self.seed + weekday,
        )

        return build_agent_context(
            persona_name=self.persona.name,
            phase=self.phase,
            weekday=weekday,
            world_info=world_info,
            active_constraints=active_constraints,
            normal_schedule=[self._episode_to_dict(ep) for ep in normal_schedule],
            constrained_schedule=[self._episode_to_dict(ep) for ep in constrained_schedule],
            energy_state=energy_state,
        )


if __name__ == "__main__":
    from env_time_weather import TimeWeatherEnv
    from constraints.illness import AcuteIllnessConstraint

    env = TimeWeatherEnv(month=1)

    persona = StudentHoursWrapper.from_zve_student_generic(
        name="demo_student"
    )

    illness = AcuteIllnessConstraint(
        name="acute_cold",
        intensity="mid",
        start_weekday=2,
        duration_days=2,
    )

    manager = ConstraintManager([illness])

    runner = SimulationRunner(
        persona=persona,
        phase=YearPhase.SEMESTER,
        env=env,
        constraint_manager=manager,
        seed=37,
    )

    context = runner.get_day_context(weekday=2)
    print(context)