from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from agent_context_export import (
    build_agent_contexts,
    build_runner_from_agent_context,
    export_day_contexts_to_json,
    generate_day_contexts_for_personas,
)
from persona_wrappers import StudentHoursWrapper
from psychological_state import BACKEND_CONSTRUCT_RANGES, build_psychological_state

INPUT_PARAMETERS = {
    "fitness_hours_week": 6,
    "social_hours_week": 8,
    "work_hours_week": 5,
    "carework_hours_week": 7,
    "workplace_distance_km": 3.0,
    "indoor_activity_distance_km": 1.2,
    "outdoor_activity_distance_km": 0.6,
}


def _payload(day_index: int = 21) -> dict:
    return generate_day_contexts_for_personas(
        n_personas=2,
        base_seed=37,
        day_index=day_index,
        input_parameters=INPUT_PARAMETERS,
    )


def _assert_psychological_state(psychological_state: dict) -> None:
    expected_constructs = set(BACKEND_CONSTRUCT_RANGES)
    legacy_constructs = {
        "habit",
        "attitude",
        "injunctive_norm",
        "descriptive_norm",
        "extrinsic_motivation",
        "volitional_self_control",
    }

    assert set(psychological_state) == {
        "source",
        "reference_group",
        "n",
        "sampling_method",
        "seed",
        "values_normalized",
        "raw_scale_means",
    }
    assert psychological_state["source"] == "T1_students_from_simulated_AIcoPA_dataset"
    assert psychological_state["reference_group"] == "T1_Studierend"
    assert psychological_state["n"] == 64
    assert psychological_state["sampling_method"] == "multivariate_normal"
    assert set(psychological_state["values_normalized"]) == expected_constructs
    assert set(psychological_state["raw_scale_means"]) == expected_constructs
    assert legacy_constructs.isdisjoint(psychological_state["values_normalized"])
    assert legacy_constructs.isdisjoint(psychological_state["raw_scale_means"])

    for construct_name, normalized_value in psychological_state["values_normalized"].items():
        min_value, max_value = BACKEND_CONSTRUCT_RANGES[construct_name]
        assert 0.0 <= normalized_value <= 1.0
        raw_value = psychological_state["raw_scale_means"][construct_name]
        assert min_value <= raw_value <= max_value
        assert raw_value == round(min_value + normalized_value * (max_value - min_value), 2)


def test_build_psychological_state_is_seed_reproducible_and_backend_compatible() -> None:
    state_a = build_psychological_state(seed=123)
    state_b = build_psychological_state(seed=123)
    state_c = build_psychological_state(seed=124)

    assert state_a == state_b
    assert state_a != state_c
    _assert_psychological_state(state_a)


def test_wrapper_input_config_accepts_all_required_parameters() -> None:
    wrapper = StudentHoursWrapper(name="input_config_student", **INPUT_PARAMETERS)

    assert wrapper.schedule_input_parameters() == {
        "fitness_hours_week": 6,
        "social_hours_week": 8,
        "work_hours_week": 5,
        "carework_hours_week": 7,
    }
    assert wrapper.accessibility_input_parameters() == {
        "workplace_distance_km": 3.0,
        "indoor_activity_distance_km": 1.2,
        "outdoor_activity_distance_km": 0.6,
    }
    assert wrapper.input_parameters() == INPUT_PARAMETERS


def test_build_agent_contexts_returns_deterministic_personas() -> None:
    contexts_a = build_agent_contexts(n_personas=3, base_seed=37, input_parameters=INPUT_PARAMETERS)
    contexts_b = build_agent_contexts(n_personas=3, base_seed=37, input_parameters=INPUT_PARAMETERS)

    assert len(contexts_a) == 3
    assert [context["persona_id"] for context in contexts_a] == [
        "StudentPersona_01",
        "StudentPersona_02",
        "StudentPersona_03",
    ]
    assert [context["persona_id"] for context in contexts_a] == [context["persona_id"] for context in contexts_b]
    seeds_a = [context["seed"] for context in contexts_a]
    assert seeds_a == [context["seed"] for context in contexts_b]
    assert len(set(seeds_a)) == len(seeds_a)


def test_build_agent_contexts_preserves_inputs_and_reports_wiring() -> None:
    contexts = build_agent_contexts(n_personas=1, base_seed=37, input_parameters=INPUT_PARAMETERS)
    context = contexts[0]

    for key, value in INPUT_PARAMETERS.items():
        assert context["input_parameters"][key] == float(value)

    assert context["accessibility_parameters"]["workplace_distance_km"] == 3.0
    assert context["accessibility_parameters"]["indoor_activity_distance_km"] == 1.2
    assert context["accessibility_parameters"]["outdoor_activity_distance_km"] == 0.6
    assert context["accessibility_parameters"]["accessibility_model"]["categories"]["workplace"]["distance_km"] == 3.0
    _assert_psychological_state(context["psychological_state"])
    assert context["generated_persona_summary"]["accessibility_inputs"] == {
        "workplace_distance_km": 3.0,
        "indoor_activity_distance_km": 1.2,
        "outdoor_activity_distance_km": 0.6,
    }
    assert "wired_parameters" in context
    assert "unsupported_or_partially_wired_parameters" in context
    assert "fitness_hours_week" in context["wired_parameters"]
    assert "social_hours_week" in context["wired_parameters"]
    assert "work_hours_week" in context["wired_parameters"]
    assert "carework_hours_week" in context["wired_parameters"]
    assert context["unsupported_or_partially_wired_parameters"] == {}


def test_poi_distance_parameters_are_passed_into_accessibility_model() -> None:
    context = build_agent_contexts(n_personas=1, base_seed=37, input_parameters=INPUT_PARAMETERS)[0]
    context["input_parameters"] = {
        **context["input_parameters"],
        "workplace_distance_km": 99.0,
        "indoor_activity_distance_km": 99.0,
        "outdoor_activity_distance_km": 99.0,
    }
    runner = build_runner_from_agent_context(context)

    assert runner.accessibility_model.get_entry("workplace").distance_km == 3.0
    assert runner.accessibility_model.get_entry("indoor_activity").distance_km == 1.2
    assert runner.accessibility_model.get_entry("outdoor_activity").distance_km == 0.6


def test_hourly_context_reflects_configured_poi_distances() -> None:
    payload = _payload()
    hourly_context = payload["personas"][0]["day_context"]["hourly_context_24h"]

    home_hour = next(entry for entry in hourly_context if entry["current_location"] == "home")
    poi_accessibility = home_hour["poi_accessibility"]

    assert poi_accessibility["workplace"]["distance_km"] == 3.0
    assert poi_accessibility["indoor_activity"]["distance_km"] == 1.2
    assert poi_accessibility["outdoor_activity"]["distance_km"] == 0.6
    assert poi_accessibility["indoor_activity"]["travel_times_min"]["walk"] == 15.0


def test_generate_day_contexts_for_personas_returns_json_serializable_payload() -> None:
    payload = _payload()

    json.dumps(payload)
    assert payload["simulation_metadata"] == {"base_seed": 37, "day_index": 21, "n_personas": 2}
    assert len(payload["personas"]) == 2
    psychological_states = []
    for persona in payload["personas"]:
        assert "agent_context" in persona
        assert "day_context" in persona
        psychological_state = persona["agent_context"]["psychological_state"]
        _assert_psychological_state(psychological_state)
        psychological_states.append(psychological_state["values_normalized"])
        assert "agent_state" not in persona
        assert "agent_state" not in persona["agent_context"]
        assert "hourly_context_24h" in persona["day_context"]
        assert len(persona["day_context"]["hourly_context_24h"]) == 24
        assert "phase" in persona["day_context"]
    assert psychological_states[0] != psychological_states[1]


def test_exported_json_file_can_be_read_back(tmp_path: Path) -> None:
    payload = _payload()
    output_path = export_day_contexts_to_json(payload, tmp_path / "contexts" / "agent_day_contexts.json")

    assert output_path.exists()
    loaded = json.loads(output_path.read_text(encoding="utf-8"))
    assert loaded == payload


def test_day_index_controls_selected_day() -> None:
    day_0 = _payload(day_index=0)
    day_21 = _payload(day_index=21)

    assert day_0["simulation_metadata"]["day_index"] == 0
    assert day_21["simulation_metadata"]["day_index"] == 21
    assert day_0["personas"][0]["day_context"]["weekday"] == 0
    assert day_21["personas"][0]["day_context"]["weekday"] == 0
    assert day_0["personas"][0]["day_context"]["hourly_environment_24h"][0]["month"] == 1
    assert day_21["personas"][0]["day_context"]["hourly_environment_24h"][0]["hour"] == 0
    assert day_0["personas"][0]["day_context"] != day_21["personas"][0]["day_context"]
