from __future__ import annotations

import random
from typing import Any

from agent_state import EnergyState


class EnergyModel:
    """MVP heuristic model for momentary energy without changing schedule structure."""

    def __init__(self, base_energy: float = 0.60) -> None:
        self.base_energy = base_energy

    def compute_energy_state(
        self,
        *,
        hour: int,
        phase: Any,
        active_constraints: list[dict[str, object]] | None,
        constrained_schedule: list[dict[str, object]] | None,
        seed: int,
    ) -> EnergyState:
        time_of_day_component = self._time_of_day_component(hour)
        phase_load_penalty = self._phase_component(phase)
        illness_penalty = self._illness_penalty(active_constraints or [])
        daily_workload_penalty = self._daily_workload_penalty(constrained_schedule or [])
        prior_activity_penalty = self._prior_activity_penalty(constrained_schedule or [], hour)
        noise = self._noise(seed=seed, hour=hour, phase=phase)

        energy = (
            self.base_energy
            + time_of_day_component
            + phase_load_penalty
            - illness_penalty
            - daily_workload_penalty
            - prior_activity_penalty
            + noise
        )
        energy_level = round(self._clamp(energy), 3)
        fatigue_level = round(1.0 - energy_level, 3)

        return EnergyState(
            energy_level=energy_level,
            fatigue_level=fatigue_level,
            energy_category=self._category(energy_level),
            description="Simulated momentary subjective energetic state",
            drivers={
                "time_of_day_component": round(time_of_day_component, 3),
                "phase_load_penalty": round(phase_load_penalty, 3),
                "illness_penalty": round(illness_penalty, 3),
                "daily_workload_penalty": round(daily_workload_penalty, 3),
                "prior_activity_penalty": round(prior_activity_penalty, 3),
                "noise": round(noise, 3),
            },
        )

    def _time_of_day_component(self, hour: int) -> float:
        if 6 <= hour <= 8:
            return -0.08
        if 9 <= hour <= 11:
            return 0.08
        if 13 <= hour <= 14:
            return -0.06
        if 16 <= hour <= 18:
            return 0.04
        if hour >= 21 or hour <= 5:
            return -0.12
        return 0.0

    def _phase_component(self, phase: Any) -> float:
        phase_value = getattr(phase, "value", str(phase)).lower()
        if phase_value == "holiday":
            return 0.05
        if phase_value == "semester":
            return -0.05
        if phase_value == "exam_phase":
            return -0.15
        return 0.0

    def _illness_penalty(self, active_constraints: list[dict[str, object]]) -> float:
        intensity = self._extract_illness_intensity(active_constraints)
        return {"low": 0.10, "mid": 0.25, "high": 0.40}.get(intensity, 0.0)

    def _extract_illness_intensity(self, active_constraints: list[dict[str, object]]) -> str | None:
        for constraint in active_constraints:
            name = str(constraint.get("name", "")).lower()
            ctype = str(constraint.get("type", "")).lower()
            if "illness" not in name and "illness" not in ctype:
                continue
            intensity = constraint.get("intensity")
            if intensity is None:
                continue
            value = str(intensity).lower()
            if value in {"low", "mid", "high"}:
                return value
        return None

    def _daily_workload_penalty(self, schedule: list[dict[str, object]]) -> float:
        load_hours = 0
        for ep in schedule:
            at = str(ep.get("activity_type", "")).lower()
            subtype = str(ep.get("subtype", "")).lower()
            if at == "work" or subtype in {"university", "studying", "paid_work", "work"}:
                load_hours += 1
        if load_hours >= 7:
            return 0.10
        if load_hours >= 4:
            return 0.05
        return 0.0

    def _prior_activity_penalty(self, schedule: list[dict[str, object]], hour: int) -> float:
        prior_pa_hours = sum(
            1
            for ep in schedule
            if int(ep.get("hour", -1)) < hour and str(ep.get("activity_type", "")).lower() == "physical_activity"
        )
        if prior_pa_hours >= 2:
            return 0.10
        if prior_pa_hours >= 1:
            return 0.05
        return 0.0

    def _noise(self, *, seed: int, hour: int, phase: Any) -> float:
        phase_key = getattr(phase, "value", str(phase))
        local_seed = f"energy:{seed}:{hour}:{phase_key}"
        return random.Random(local_seed).uniform(-0.05, 0.05)

    def _category(self, energy_level: float) -> str:
        if energy_level < 0.33:
            return "low"
        if energy_level < 0.66:
            return "medium"
        return "high"

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))
