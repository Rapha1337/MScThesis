from __future__ import annotations

from dataclasses import dataclass

from .base import Constraint


@dataclass
class AcuteIllnessConstraint(Constraint):
    duration_days: int
    start_weekday: int = 0
    intensity: str = "low"
    name: str = "acute_illness"
    illness_type: str = "acute_unspecified"
    is_active: bool = True

    def __post_init__(self) -> None:
        Constraint.__init__(self, name=self.name, is_active=self.is_active)
        if self.duration_days < 0:
            raise ValueError("duration_days must be >= 0")
        if not 0 <= self.start_weekday <= 6:
            raise ValueError("start_weekday must be between 0 and 6")
        if self.intensity not in {"low", "mid", "high"}:
            raise ValueError("intensity must be one of: low, mid, high")

    def is_active_on_weekday(self, weekday: int) -> bool:
        if not self.is_active or self.duration_days == 0:
            return False
        if not 0 <= weekday <= 6:
            return False
        end_weekday = min(6, self.start_weekday + self.duration_days - 1)
        return self.start_weekday <= weekday <= end_weekday

    def apply(self, day_schedule: list, weekday: int) -> list:
        from schedule_model_student import ActivityType, DayEpisode
        if not self.is_active_on_weekday(weekday):
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
            if (
                ep.activity_type == ActivityType.WORK and ep.subtype in {"paid_work", "university", "studying"}
            )
            or ep.activity_type == ActivityType.CAREWORK
        ]

        if self.intensity == "low":
            _replace_hours(physical[len(physical) // 2 :], ActivityType.DOWNTIME, "illness_recovery")
            _replace_hours(social[len(social) // 2 :], ActivityType.DOWNTIME, "illness_recovery")
        elif self.intensity == "mid":
            _replace_hours(physical, ActivityType.DOWNTIME, "illness_recovery")
            _replace_hours(social, ActivityType.DOWNTIME, "illness_recovery")
            _replace_hours(work_like[len(work_like) // 2 :], ActivityType.DOWNTIME, "illness_recovery")
        else:
            _replace_hours(physical, ActivityType.DOWNTIME, "illness_recovery")
            _replace_hours(social, ActivityType.DOWNTIME, "illness_recovery")
            _replace_hours(work_like, ActivityType.DOWNTIME, "illness_recovery")

        sleep_targets = 2 if self.intensity == "mid" else 3 if self.intensity == "high" else 0
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
