from __future__ import annotations

import argparse
import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

SIMULATION_DIR = Path(__file__).resolve().parent
if str(SIMULATION_DIR) not in sys.path:
    sys.path.append(str(SIMULATION_DIR))

from agent_context_export import export_day_contexts_to_json, generate_day_contexts_for_personas
from run_agent_context_simulation import build_llm_ready_payload

DEFAULT_OUTPUT_PATH = SIMULATION_DIR / "output" / "llm_day_contexts_heterogeneous_test.json"
DEFAULT_BASE_SEED = 137
DEFAULT_DAY_INDEX = 21

SPEEDS_KMH: Mapping[str, float] = {"walk": 4.8, "bike": 15.0, "car": 30.0}


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    phase: str
    input_parameters: Mapping[str, float]
    schedule_overrides: Mapping[str, float] = field(default_factory=dict)
    activity_overrides: Mapping[int, tuple[str, str, str, tuple[str, ...]]] = field(default_factory=dict)
    daytime_energy: float = 0.6
    weather: str = "acceptable"
    daylight_end_hour: int = 18
    note: str = ""


SCENARIOS: tuple[ScenarioSpec, ...] = (
    ScenarioSpec(
        name="favourable_pa_context",
        phase="holiday",
        input_parameters={
            "fitness_hours_week": 6.0,
            "social_hours_week": 8.0,
            "work_hours_week": 0.0,
            "carework_hours_week": 0.0,
            "workplace_distance_km": 2.0,
            "indoor_activity_distance_km": 0.8,
            "outdoor_activity_distance_km": 0.5,
        },
        schedule_overrides={"employment_load": 0.0, "university_load": 0.15, "sport_frequency": 0.65},
        activity_overrides={},
        daytime_energy=0.72,
        weather="dry",
        daylight_end_hour=20,
        note="Holiday-like day with multiple open free-time windows, good energy, dry weather, and nearby indoor/outdoor options.",
    ),
    ScenarioSpec(
        name="busy_day_context",
        phase="normal",
        input_parameters={
            "fitness_hours_week": 3.0,
            "social_hours_week": 4.0,
            "work_hours_week": 12.0,
            "carework_hours_week": 6.0,
            "workplace_distance_km": 3.0,
            "indoor_activity_distance_km": 1.5,
            "outdoor_activity_distance_km": 1.0,
        },
        schedule_overrides={"employment_load": 0.7, "university_load": 0.8, "day_fragmentation": 0.8},
        activity_overrides={
            **{hour: ("work", "university", "university", ()) for hour in range(9, 13)},
            **{hour: ("work", "paid_work", "workplace", ()) for hour in range(14, 17)},
            17: ("commute", "return_commute", "in_transit", ()),
            19: ("carework", "carework", "home", ()),
            20: ("carework", "carework", "home", ()),
        },
        daytime_energy=0.56,
        weather="acceptable",
        daylight_end_hour=18,
        note="Normal phase day packed with university, work, and carework blocks, leaving only short free windows.",
    ),
    ScenarioSpec(
        name="negative_pa_context",
        phase="high_stress",
        input_parameters={
            "fitness_hours_week": 1.0,
            "social_hours_week": 2.0,
            "work_hours_week": 16.0,
            "carework_hours_week": 10.0,
            "workplace_distance_km": 6.0,
            "indoor_activity_distance_km": 5.5,
            "outdoor_activity_distance_km": 3.8,
        },
        schedule_overrides={"employment_load": 0.85, "university_load": 0.95, "day_fragmentation": 0.9},
        activity_overrides={
            **{hour: ("work", "university", "university", ("high_stress",)) for hour in range(8, 13)},
            **{hour: ("work", "exam_preparation", "home", ("high_stress",)) for hour in range(14, 19)},
            19: ("carework", "carework", "home", ("high_stress",)),
            20: ("downtime", "recovery_after_stress", "home", ("high_stress",)),
            21: ("downtime", "evening_wind_down", "home", ("high_stress",)),
        },
        daytime_energy=0.28,
        weather="bad_dark",
        daylight_end_hour=16,
        note="High-stress day with low energy, very little free time, wet/dark conditions, and poorer accessibility.",
    ),
    ScenarioSpec(
        name="indoor_opportunity_context",
        phase="normal",
        input_parameters={
            "fitness_hours_week": 4.0,
            "social_hours_week": 6.0,
            "work_hours_week": 4.0,
            "carework_hours_week": 2.0,
            "workplace_distance_km": 2.5,
            "indoor_activity_distance_km": 0.6,
            "outdoor_activity_distance_km": 3.0,
        },
        schedule_overrides={"employment_load": 0.35, "university_load": 0.45, "sport_frequency": 0.45},
        activity_overrides={
            **{hour: ("work", "university", "university", ()) for hour in range(9, 12)},
            **{hour: ("downtime", "open_time", "home", ()) for hour in range(14, 18)},
        },
        daytime_energy=0.58,
        weather="bad_weather",
        daylight_end_hour=18,
        note="Bad outdoor weather but medium energy, usable free time, and a close indoor activity option.",
    ),
    ScenarioSpec(
        name="bike_access_context",
        phase="normal",
        input_parameters={
            "fitness_hours_week": 5.0,
            "social_hours_week": 5.0,
            "work_hours_week": 5.0,
            "carework_hours_week": 0.0,
            "workplace_distance_km": 4.0,
            "indoor_activity_distance_km": 4.8,
            "outdoor_activity_distance_km": 4.2,
        },
        schedule_overrides={"employment_load": 0.4, "university_load": 0.5, "sport_frequency": 0.55},
        activity_overrides={
            **{hour: ("work", "university", "university", ()) for hour in range(9, 12)},
            **{hour: ("downtime", "open_time", "home", ()) for hour in range(15, 19)},
        },
        daytime_energy=0.66,
        weather="acceptable",
        daylight_end_hour=19,
        note="A free afternoon window with acceptable weather and activity locations that are far on foot but much faster by bike.",
    ),
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate five controlled, heterogeneous LLM PA day contexts for evaluation."
    )
    parser.add_argument("--base-seed", type=int, default=DEFAULT_BASE_SEED)
    parser.add_argument("--day-index", type=int, default=DEFAULT_DAY_INDEX)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args(argv)


def _base_input_parameters() -> dict[str, float]:
    return {
        "fitness_hours_week": 4.0,
        "social_hours_week": 6.0,
        "work_hours_week": 6.0,
        "carework_hours_week": 2.0,
        "workplace_distance_km": 3.0,
        "indoor_activity_distance_km": 1.2,
        "outdoor_activity_distance_km": 0.8,
    }


def _energy_category(value: float) -> str:
    if value < 0.4:
        return "low"
    if value < 0.7:
        return "medium"
    return "high"


def _travel_times(distance_km: float) -> dict[str, float]:
    return {mode: round(distance_km / speed * 60.0, 1) for mode, speed in SPEEDS_KMH.items()}


def _poi_accessibility(spec: ScenarioSpec) -> dict[str, dict[str, Any]]:
    indoor_distance = float(spec.input_parameters["indoor_activity_distance_km"])
    outdoor_distance = float(spec.input_parameters["outdoor_activity_distance_km"])
    return {
        "indoor_activity": {
            "distance_km": indoor_distance,
            "travel_times_min": _travel_times(indoor_distance),
        },
        "outdoor_activity": {
            "distance_km": outdoor_distance,
            "travel_times_min": _travel_times(outdoor_distance),
        },
    }


def _weather_values(weather: str, hour: int, daylight_end_hour: int) -> dict[str, Any]:
    is_daylight = 8 <= hour <= daylight_end_hour
    if weather == "dry":
        sun_frac = 0.75 if is_daylight else 0.0
        return {
            "temperature_c": 19.0,
            "feels_like_c": 19.0,
            "humidity_pct": 55.0,
            "wind_m_s": 1.8,
            "precipitation_mm": 0.0,
            "is_wet": False,
            "sun_frac": sun_frac,
            "is_daylight": is_daylight,
            "snow_cover": False,
        }
    if weather == "acceptable":
        sun_frac = 0.45 if is_daylight else 0.0
        return {
            "temperature_c": 13.0,
            "feels_like_c": 12.0,
            "humidity_pct": 68.0,
            "wind_m_s": 3.0,
            "precipitation_mm": 0.0,
            "is_wet": False,
            "sun_frac": sun_frac,
            "is_daylight": is_daylight,
            "snow_cover": False,
        }
    if weather == "bad_dark":
        sun_frac = 0.08 if is_daylight else 0.0
        return {
            "temperature_c": 4.0,
            "feels_like_c": -1.0,
            "humidity_pct": 94.0,
            "wind_m_s": 8.0,
            "precipitation_mm": 3.2,
            "is_wet": True,
            "sun_frac": sun_frac,
            "is_daylight": is_daylight,
            "snow_cover": False,
        }
    sun_frac = 0.12 if is_daylight else 0.0
    return {
        "temperature_c": 7.0,
        "feels_like_c": 3.0,
        "humidity_pct": 91.0,
        "wind_m_s": 6.0,
        "precipitation_mm": 2.0,
        "is_wet": True,
        "sun_frac": sun_frac,
        "is_daylight": is_daylight,
        "snow_cover": False,
    }


def _default_activity(hour: int) -> tuple[str, str, str, tuple[str, ...]]:
    if hour <= 6 or hour >= 22:
        return "sleep", "night_sleep", "home", ()
    if hour == 7:
        return "wake_up", "morning_wake_up", "home", ()
    if hour == 8:
        return "eat", "breakfast", "home", ()
    if hour == 12:
        return "eat", "lunch", "home", ()
    if hour == 18:
        return "eat", "dinner", "home", ()
    if hour in {20, 21}:
        return "downtime", "evening_wind_down", "home", ()
    return "downtime", "open_time", "home", ()


def _apply_scenario(context: Mapping[str, Any], spec: ScenarioSpec, index: int, day_index: int) -> dict[str, Any]:
    scenario_context = copy.deepcopy(dict(context))
    scenario_context["persona_id"] = f"ScenarioPersona_{index:02d}_{spec.name}"
    scenario_context["scenario"] = spec.name
    scenario_context["day_index"] = int(day_index)
    scenario_context["phase"] = spec.phase
    scenario_context["input_parameters"] = dict(spec.input_parameters, day_index=int(day_index))

    selected_schedule_parameters = dict(scenario_context.get("selected_schedule_parameters", {}))
    selected_schedule_parameters.update(spec.schedule_overrides)
    scenario_context["selected_schedule_parameters"] = selected_schedule_parameters

    poi_accessibility = _poi_accessibility(spec)
    updated_hourly_context: list[dict[str, Any]] = []
    for raw_hourly_entry in scenario_context["hourly_context_24h"]:
        hourly_entry = dict(raw_hourly_entry)
        hour = int(hourly_entry["hour"])
        activity_type, subtype, location, constraints = spec.activity_overrides.get(hour, _default_activity(hour))

        if activity_type == "sleep":
            energy_level = min(spec.daytime_energy, 0.5)
        elif activity_type == "wake_up":
            energy_level = max(0.25, spec.daytime_energy - 0.08)
        elif activity_type == "eat":
            energy_level = max(0.3, spec.daytime_energy - 0.03)
        else:
            energy_level = spec.daytime_energy

        hourly_entry.update(
            {
                "activity_type": activity_type,
                "subtype": subtype,
                "current_location": location,
                "active_constraints": list(constraints),
                "energy_level": round(energy_level, 3),
                "energy_category": _energy_category(energy_level),
                "poi_accessibility": copy.deepcopy(poi_accessibility),
            }
        )
        hourly_entry.update(_weather_values(spec.weather, hour, spec.daylight_end_hour))
        updated_hourly_context.append(hourly_entry)

    scenario_context["hourly_context_24h"] = updated_hourly_context
    return scenario_context


def build_heterogeneous_llm_payload(base_seed: int, day_index: int) -> dict[str, Any]:
    diagnostic_payload = generate_day_contexts_for_personas(
        n_personas=len(SCENARIOS),
        base_seed=base_seed,
        day_index=day_index,
        input_parameters=_base_input_parameters(),
    )
    base_payload = build_llm_ready_payload(diagnostic_payload)

    contexts = [
        _apply_scenario(context, scenario, index, day_index)
        for index, (context, scenario) in enumerate(zip(base_payload["llm_contexts"], SCENARIOS), start=1)
    ]

    return {
        "simulation_metadata": {
            **dict(base_payload["simulation_metadata"]),
            "n_personas": len(contexts),
            "controlled_scenario_coverage": [scenario.name for scenario in SCENARIOS],
        },
        "llm_contexts": contexts,
    }


def _print_summary(payload: Mapping[str, Any], output_path: Path) -> None:
    print(f"output path: {output_path}")
    print(f"n contexts: {len(payload['llm_contexts'])}")
    print("scenarios:")
    for context in payload["llm_contexts"]:
        free_hours = sum(1 for hour in context["hourly_context_24h"] if hour["activity_type"] == "downtime")
        wet_hours = sum(1 for hour in context["hourly_context_24h"] if hour["is_wet"])
        print(
            f"- {context['scenario']}: phase={context['phase']}, "
            f"free/downtime_hours={free_hours}, wet_hours={wet_hours}"
        )
    print(
        "Runner command: python Simulation/run_heterogeneous_llm_contexts.py "
        "--output-path Simulation/output/llm_day_contexts_heterogeneous_test.json"
    )


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    payload = build_heterogeneous_llm_payload(base_seed=args.base_seed, day_index=args.day_index)
    output_path = export_day_contexts_to_json(payload, args.output_path)
    json.dumps(payload)
    _print_summary(payload, output_path)


if __name__ == "__main__":
    main()
