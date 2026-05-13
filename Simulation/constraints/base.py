from __future__ import annotations

from abc import ABC, abstractmethod


class Constraint(ABC):
    def __init__(self, name: str, is_active: bool = True) -> None:
        self.name = name
        self.is_active = is_active

    @abstractmethod
    def is_active_on_weekday(self, weekday: int) -> bool:
        """Return whether this constraint should be applied on the given weekday."""

    @abstractmethod
    def apply(self, day_schedule: list, weekday: int) -> list:
        """Return a constrained copy of the schedule without mutating input."""
