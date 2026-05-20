from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EnergyState:
    """Time-varying subjective energetic state; intentionally not a hard constraint."""

    energy_level: float
    energy_category: str
    description: str
    drivers: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        return {
            "energy_level": self.energy_level,
            "energy_category": self.energy_category,
            "description": self.description,
            "drivers": dict(self.drivers),
        }
