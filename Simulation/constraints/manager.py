from __future__ import annotations

from .base import Constraint


class ConstraintManager:
    def __init__(self, constraints: list[Constraint] | None = None) -> None:
        self.constraints: list[Constraint] = constraints[:] if constraints else []

    def add_constraint(self, constraint: Constraint) -> None:
        self.constraints.append(constraint)

    def get_active_constraints(self, weekday: int) -> list[Constraint]:
        return [c for c in self.constraints if c.is_active_on_weekday(weekday)]

    def apply_constraints(self, day_schedule: list, weekday: int) -> list:
        from schedule_model_student import DayEpisode
        constrained = [DayEpisode(ep.hour, ep.activity_type, ep.flexibility, ep.subtype) for ep in day_schedule]
        for constraint in self.get_active_constraints(weekday):
            constrained = constraint.apply(constrained, weekday)
        return constrained
