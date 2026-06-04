from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
from typing import Any, Mapping, Sequence


ACCESSIBILITY_CATEGORIES: tuple[str, str, str] = (
    "workplace",
    "indoor_activity",
    "outdoor_activity",
)

LOCATION_ANCHORS: tuple[str, str, str, str, str] = (
    "home",
    "workplace",
    "indoor_activity",
    "outdoor_activity",
    "unknown",
)

ACCESSIBLE_TARGET_LOCATIONS: tuple[str, str, str, str] = (
    "home",
    "workplace",
    "indoor_activity",
    "outdoor_activity",
)

DEFAULT_SPEEDS_KMH: dict[str, float] = {
    "walk": 4.8,
    "bike": 15.0,
    "car": 30.0,
}

DEFAULT_SOURCE = "survey_distance_estimate"
HEURISTIC_SOURCE = "home_distance_mean_heuristic"
UNKNOWN_SOURCE = "unknown_current_location"

HOME_ACTIVITY_TYPES = {"sleep", "eat", "downtime", "wake_up", "household", "carework"}
NEUTRAL_EAT_SUBTYPES = {"lunch", "snack"}
NEUTRAL_DOWNTIME_SUBTYPES = {"between_blocks", "open_time"}
WORK_ACTIVITY_TYPE = "work"
PHYSICAL_ACTIVITY_TYPE = "physical_activity"
OUTDOOR_ACTIVITY_HINTS = {
    "outdoor",
    "park",
    "forest",
    "field",
    "training_field",
    "running",
    "walking",
    "hiking",
    "trail",
}


def _validate_speeds(speeds_kmh: Mapping[str, float]) -> dict[str, float]:
    speeds = dict(speeds_kmh)
    missing = set(DEFAULT_SPEEDS_KMH) - set(speeds)
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"Missing speed definitions for: {missing_list}")

    validated: dict[str, float] = {}
    for mode in DEFAULT_SPEEDS_KMH:
        speed = float(speeds[mode])
        if speed <= 0:
            raise ValueError(f"speed_kmh for mode='{mode}' must be > 0")
        validated[mode] = speed
    return validated


def _coerce_activity_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Enum):
        return str(value.value)
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _entry_get(entry: Any, key: str, default: Any = None) -> Any:
    if isinstance(entry, Mapping):
        return entry.get(key, default)
    return getattr(entry, key, default)


def calculate_travel_times_min(
    distance_km: float | None,
    speeds_kmh: Mapping[str, float] | None = None,
) -> dict[str, float | None]:
    """Calculate deterministic travel times from a survey-style distance estimate."""
    speeds = _validate_speeds(speeds_kmh or DEFAULT_SPEEDS_KMH)

    if distance_km is None:
        return {mode: None for mode in speeds}

    distance = float(distance_km)
    if distance < 0:
        raise ValueError("distance_km must be >= 0 or None")

    if distance == 0:
        return {mode: 0.0 for mode in speeds}

    return {
        mode: round(distance / speed_kmh * 60.0, 6)
        for mode, speed_kmh in speeds.items()
    }


def _is_neutral_context_dependent_block(hourly_entry: Any) -> bool:
    activity_type = _coerce_activity_value(_entry_get(hourly_entry, "activity_type"))
    subtype = _coerce_activity_value(_entry_get(hourly_entry, "subtype"))

    if activity_type == "eat" and subtype in NEUTRAL_EAT_SUBTYPES:
        return True
    if activity_type == "downtime" and subtype in NEUTRAL_DOWNTIME_SUBTYPES:
        return True
    return False


def _is_work_like_block(hourly_entry: Any, *, study_location: str | None = None) -> bool:
    return (
        _coerce_activity_value(_entry_get(hourly_entry, "activity_type")) == WORK_ACTIVITY_TYPE
        and infer_current_location(hourly_entry, study_location=study_location) not in {"home", "unknown"}
    )


def _infer_contextual_neutral_location(
    hourly_schedule: Sequence[Any],
    index: int,
    *,
    study_location: str | None = None,
) -> str | None:
    if index <= 0 or index >= len(hourly_schedule) - 1:
        return None

    entry = hourly_schedule[index]
    if not _is_neutral_context_dependent_block(entry):
        return None

    previous_entry = hourly_schedule[index - 1]
    next_entry = hourly_schedule[index + 1]
    if not (
        _is_work_like_block(previous_entry, study_location=study_location)
        and _is_work_like_block(next_entry, study_location=study_location)
    ):
        return None

    previous_location = infer_current_location(previous_entry, study_location=study_location)
    next_location = infer_current_location(next_entry, study_location=study_location)
    if previous_location == next_location and previous_location not in {"home", "unknown"}:
        return previous_location
    return None


def infer_current_location(
    hourly_entry: Any,
    *,
    study_location: str | None = None,
) -> str:
    """
    Infer the coarse current-location anchor for a serialized hourly schedule entry.

    This is intentionally context-serialization logic only; it does not mutate
    DayEpisode. Studying is currently treated as home unless an explicit supported
    study_location anchor is provided. Physical activity defaults to indoor
    activity unless subtype or metadata-like fields contain an outdoor hint.
    """
    activity_type = _coerce_activity_value(_entry_get(hourly_entry, "activity_type"))
    subtype = _coerce_activity_value(_entry_get(hourly_entry, "subtype"))
    metadata = _entry_get(hourly_entry, "metadata", None)

    if activity_type in HOME_ACTIVITY_TYPES:
        return "home"

    if activity_type == WORK_ACTIVITY_TYPE:
        if subtype == "paid_work":
            return "workplace"
        if subtype == "studying":
            if study_location in LOCATION_ANCHORS and study_location != "unknown":
                return str(study_location)
            return "home"
        if subtype in {"university", "school", "workplace"}:
            return "workplace"
        return "workplace"

    if activity_type == PHYSICAL_ACTIVITY_TYPE:
        text_parts = [subtype or ""]
        if isinstance(metadata, Mapping):
            text_parts.extend(str(value) for value in metadata.values())
        elif metadata is not None:
            text_parts.append(str(metadata))
        descriptor = " ".join(text_parts).lower()
        if any(hint in descriptor for hint in OUTDOOR_ACTIVITY_HINTS):
            return "outdoor_activity"
        return "indoor_activity"

    return "unknown"


@dataclass(frozen=True)
class AccessibilityEntry:
    """Stable agent-level accessibility for one survey POI category."""

    category: str
    distance_km: float | None
    travel_times_min: dict[str, float | None] = field(default_factory=dict)
    source: str = DEFAULT_SOURCE
    note: str | None = None

    def __post_init__(self) -> None:
        if self.category not in ACCESSIBILITY_CATEGORIES:
            valid = ", ".join(ACCESSIBILITY_CATEGORIES)
            raise ValueError(f"Unsupported accessibility category '{self.category}'. Expected one of: {valid}")

        if self.distance_km is not None and float(self.distance_km) < 0:
            raise ValueError("distance_km must be >= 0 or None")

        if self.distance_km is not None:
            object.__setattr__(self, "distance_km", float(self.distance_km))

        if not self.travel_times_min:
            object.__setattr__(
                self,
                "travel_times_min",
                calculate_travel_times_min(self.distance_km),
            )

    @classmethod
    def from_distance(
        cls,
        category: str,
        distance_km: float | None,
        *,
        speeds_kmh: Mapping[str, float] | None = None,
        source: str = DEFAULT_SOURCE,
        note: str | None = None,
    ) -> "AccessibilityEntry":
        return cls(
            category=category,
            distance_km=distance_km,
            travel_times_min=calculate_travel_times_min(distance_km, speeds_kmh),
            source=source,
            note=note,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "category": self.category,
            "distance_km": self.distance_km,
            "travel_times_min": dict(self.travel_times_min),
            "source": self.source,
            "note": self.note,
        }


@dataclass(frozen=True)
class AccessibilityModel:
    """
    Lightweight LLM-context accessibility model based on survey distance estimates.

    Survey distances are interpreted as home-based anchor distances:
    home -> workplace, home -> indoor_activity, and home -> outdoor_activity.
    Because LimeSurvey does not provide true POI-to-POI distances, distances
    between non-home anchors are deterministic heuristic approximations.
    The legacy OSM/BernMap MobilityModel is intentionally not used here.
    """

    entries: dict[str, AccessibilityEntry]
    speeds_kmh: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_SPEEDS_KMH))

    def __post_init__(self) -> None:
        object.__setattr__(self, "speeds_kmh", _validate_speeds(self.speeds_kmh))

        missing = set(ACCESSIBILITY_CATEGORIES) - set(self.entries)
        extra = set(self.entries) - set(ACCESSIBILITY_CATEGORIES)
        if missing or extra:
            parts: list[str] = []
            if missing:
                parts.append(f"missing={sorted(missing)}")
            if extra:
                parts.append(f"extra={sorted(extra)}")
            raise ValueError("AccessibilityModel must contain exactly the supported categories: " + ", ".join(parts))

        for category, entry in self.entries.items():
            if entry.category != category:
                raise ValueError(f"Entry key '{category}' does not match entry category '{entry.category}'")

    def get_entry(self, category: str) -> AccessibilityEntry:
        if category not in self.entries:
            valid = ", ".join(ACCESSIBILITY_CATEGORIES)
            raise KeyError(f"Unknown accessibility category '{category}'. Expected one of: {valid}")
        return self.entries[category]

    def get_home_distance_km(self, location: str) -> float | None:
        """Return the survey-estimated home-to-anchor distance for a location."""
        if location == "home":
            return 0.0
        if location in ACCESSIBILITY_CATEGORIES:
            return self.entries[location].distance_km
        if location == "unknown":
            return None
        valid = ", ".join(LOCATION_ANCHORS)
        raise ValueError(f"Unsupported location anchor '{location}'. Expected one of: {valid}")

    def get_pairwise_distance_km(self, origin: str, destination: str) -> tuple[float | None, str]:
        """
        Estimate pairwise distance between two coarse location anchors.

        Known home-based survey distances are used symmetrically. Missing
        non-home pairwise distances are approximated as the mean of each anchor's
        distance from home. This is a deterministic heuristic, not real routing.
        """
        if origin not in LOCATION_ANCHORS:
            valid = ", ".join(LOCATION_ANCHORS)
            raise ValueError(f"Unsupported origin location '{origin}'. Expected one of: {valid}")
        if destination not in LOCATION_ANCHORS:
            valid = ", ".join(LOCATION_ANCHORS)
            raise ValueError(f"Unsupported destination location '{destination}'. Expected one of: {valid}")

        if origin == "unknown" or destination == "unknown":
            return None, UNKNOWN_SOURCE
        if origin == destination:
            return 0.0, "same_location"

        origin_home_distance = self.get_home_distance_km(origin)
        destination_home_distance = self.get_home_distance_km(destination)

        if origin == "home" or destination == "home":
            distance = destination_home_distance if origin == "home" else origin_home_distance
            return distance, DEFAULT_SOURCE

        if origin_home_distance is None or destination_home_distance is None:
            return None, HEURISTIC_SOURCE

        return round((origin_home_distance + destination_home_distance) / 2.0, 6), HEURISTIC_SOURCE

    def get_access_from_location(self, current_location: str) -> dict[str, object]:
        """
        Build location-aware access values from the current location anchor.

        The output includes distances/travel times to home and the three POI
        anchors. Non-home-to-non-home distances use the documented mean-distance
        heuristic because only home-based LimeSurvey distances are available.
        """
        if current_location not in LOCATION_ANCHORS:
            valid = ", ".join(LOCATION_ANCHORS)
            raise ValueError(f"Unsupported current_location '{current_location}'. Expected one of: {valid}")

        targets: dict[str, dict[str, object]] = {}
        for destination in ACCESSIBLE_TARGET_LOCATIONS:
            distance_km, source = self.get_pairwise_distance_km(current_location, destination)
            targets[destination] = {
                "location": destination,
                "distance_km": distance_km,
                "travel_times_min": calculate_travel_times_min(distance_km, self.speeds_kmh),
                "source": source,
            }

        return {
            "current_location": current_location,
            "targets": targets,
            "heuristic_note": (
                "Survey distances are treated as home-based. Non-home pairwise "
                "distances use the mean of both locations' home distances because "
                "true POI-to-POI distances are not available."
            ),
        }

    def build_hourly_accessibility(
        self,
        hourly_schedule: Sequence[Any],
        *,
        study_location: str | None = None,
    ) -> list[dict[str, object]]:
        """Serialize hourly location-aware accessibility for schedule entries."""
        hourly_context: list[dict[str, object]] = []
        previous_location: str | None = None
        inferred_locations = [
            _infer_contextual_neutral_location(hourly_schedule, index, study_location=study_location)
            or infer_current_location(entry, study_location=study_location)
            for index, entry in enumerate(hourly_schedule)
        ]

        for index, entry in enumerate(hourly_schedule):
            hour = _entry_get(entry, "hour", None)
            current_location = inferred_locations[index]

            if index == 0:
                location_changed = False
                travel_from_previous_location = None
            else:
                location_changed = previous_location != current_location
                distance_km, source = self.get_pairwise_distance_km(
                    previous_location or "unknown",
                    current_location,
                )
                travel_from_previous_location = {
                    "origin": previous_location,
                    "destination": current_location,
                    "distance_km": distance_km,
                    "travel_times_min": calculate_travel_times_min(distance_km, self.speeds_kmh),
                    "source": source,
                }

            hourly_context.append(
                {
                    "hour": hour,
                    "current_location": current_location,
                    "previous_location": previous_location,
                    "location_changed_from_previous_hour": location_changed,
                    "travel_from_previous_location": travel_from_previous_location,
                    "accessibility": self.get_access_from_location(current_location),
                }
            )
            previous_location = current_location

        return hourly_context

    def to_dict(self) -> dict[str, object]:
        return {
            "categories": {
                category: self.entries[category].to_dict()
                for category in ACCESSIBILITY_CATEGORIES
            },
            "location_anchors": list(LOCATION_ANCHORS),
            "speeds_kmh": dict(self.speeds_kmh),
        }

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


AccessibilityProfile = AccessibilityModel


def build_accessibility_model(
    workplace_distance_km: float | None,
    indoor_activity_distance_km: float | None,
    outdoor_activity_distance_km: float | None,
    speeds_kmh: Mapping[str, float] | None = None,
    *,
    workplace_note: str | None = None,
    indoor_activity_note: str | None = None,
    outdoor_activity_note: str | None = None,
) -> AccessibilityModel:
    """Build the three-category accessibility model from LimeSurvey-style distances."""
    speeds = _validate_speeds(speeds_kmh or DEFAULT_SPEEDS_KMH)
    distances = {
        "workplace": workplace_distance_km,
        "indoor_activity": indoor_activity_distance_km,
        "outdoor_activity": outdoor_activity_distance_km,
    }
    notes = {
        "workplace": workplace_note,
        "indoor_activity": indoor_activity_note,
        "outdoor_activity": outdoor_activity_note,
    }

    entries = {
        category: AccessibilityEntry.from_distance(
            category,
            distance,
            speeds_kmh=speeds,
            note=notes[category],
        )
        for category, distance in distances.items()
    }

    return AccessibilityModel(entries=entries, speeds_kmh=speeds)
