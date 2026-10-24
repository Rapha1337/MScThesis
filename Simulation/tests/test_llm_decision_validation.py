from __future__ import annotations

import importlib
import json
from pathlib import Path
import re
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))


BEHAVIOR_POLICY = {
    "do_planned_activity": 0.25,
    "adapt_activity": 0.30,
    "skip_activity": 0.35,
    "extra_activity": 0.10,
}

EXPECTED_LLM3_CODEBOOK_ITEMS = {
    "automaticity_q1": "Habit1: The decision to be physically active occurs automatically.",
    "automaticity_q2": "Habit2: The decision to be physically active occurs without consciously remembering it.",
    "automaticity_q3": "Habit3: The decision to be physically active occurs without thinking about it.",
    "automaticity_q4": "Habit4: Initiation of the decision to be physically active occurs before conscious awareness.",
    "pa_specific_self_control_q1": "VolSelf1: Tendency to carry out planned physical activity.",
    "pa_specific_self_control_q2": "VolSelf2: Ability to keep the intention to be active in mind without being easily distracted.",
    "pa_specific_self_control_q3": "VolSelf3: Discipline in implementing the intention to become more physically active.",
    "action_planning_q1": "ActionPlan1: Having a plan for which type of physical activity to perform.",
    "action_planning_q2": "ActionPlan2: Having a plan for where to perform physical activity.",
    "action_planning_q3": "ActionPlan3: Having a plan for which days of the week to perform physical activity.",
    "action_planning_q4": "ActionPlan4: Having a plan for how long to perform physical activity.",
    "intention_q1": "Intention1: Perceived likelihood of being physically active.",
    "intention_q2": "Intention2: Intended effort to be physically active.",
    "intention_q3": "Intention3: Intention or plan to be physically active.",
    "perceived_behavioral_control_q1": "Control1: Perceived possibility of being physically active on many days during the coming week.",
    "perceived_behavioral_control_q2": "Control2: Perceived feasibility of being physically active if desired.",
    "perceived_behavioral_control_q3": "Control3: Perceived amount of personal control over being physically active.",
    "perceived_behavioral_control_q4": "Control4: Perception that being physically active mainly depends on oneself.",
    "attitude_toward_the_behavior_q1": "Att1: Harmful versus beneficial.",
    "attitude_toward_the_behavior_q2": "Att2: Unpleasant versus pleasant.",
    "attitude_toward_the_behavior_q3": "Att3: Bad versus good.",
    "attitude_toward_the_behavior_q4": "Att4: Useless versus valuable.",
    "attitude_toward_the_behavior_q5": "Att5: Unenjoyable versus enjoyable.",
    "subjective_norm_q1": "Norm1: Perceived expectations of important others regarding being physically active.",
    "subjective_norm_q2": "Norm2: Perception that regular physical activity is expected from oneself.",
    "subjective_norm_q3": "Norm3: Perceived support from valued others for being physically active.",
    "subjective_norm_q4": "Norm4: Perception that most important others are physically active.",
    "subjective_norm_q5": "Norm5: Perception that valued others are physically active.",
    "subjective_norm_q6": "Norm6: Perception that similar others are physically active.",
    "motivational_competence_q1": "MotivComp1: Ability to choose a suitable physical activity from different options.",
    "motivational_competence_q2": "MotivComp2: Ability to recognize whether an activity fits one's personal preferences and needs.",
    "motivational_competence_q3": "MotivComp3: Clarity about which activity characteristics are personally important for enjoyment.",
    "motivational_competence_q4": "MotivComp4: Ability to understand and distinguish characteristics of different physical activities.",
}


def _hourly_context() -> list[dict]:
    return [
        {
            "hour": hour,
            "activity_type": "downtime",
            "subtype": "open_time",
            "current_location": "home",
            "active_constraints": [],
            "energy_level": 0.6,
            "energy_category": "medium",
            "temperature_c": 12.0,
            "feels_like_c": 12.0,
            "humidity_pct": 70.0,
            "wind_m_s": 1.0,
            "precipitation_mm": 0.0,
            "is_wet": False,
            "sun_frac": 0.5,
            "is_daylight": 8 <= hour <= 18,
            "snow_cover": False,
            "poi_accessibility": {
                "indoor_activity": {
                    "distance_km": 1.2,
                    "travel_times_min": {"walk": 15.0, "bike": 4.8, "car": 2.4},
                },
                "outdoor_activity": {
                    "distance_km": 0.6,
                    "travel_times_min": {"walk": 7.5, "bike": 2.4, "car": 1.2},
                },
            },
        }
        for hour in range(24)
    ]


def test_llm3_prompt_contains_t1_codebook_item_meanings_for_eight_constructs() -> None:
    from state_assessment import load_state_assessment_prompt

    prompt = load_state_assessment_prompt()

    assert "## T1-Codebuch-Itembedeutungen" in prompt
    assert len(EXPECTED_LLM3_CODEBOOK_ITEMS) == 33
    for question_id, codebook_meaning in EXPECTED_LLM3_CODEBOOK_ITEMS.items():
        assert f"`{question_id}`" in prompt
        assert codebook_meaning in prompt

    assert "Bewerte automatische Initiierung körperlicher Aktivität" in prompt
    assert "Ohne Hinweise auf andere Personen verwende `score = null`" in prompt
    assert "fehlende Freizeit ≠ niedrige PA-spezifische Selbstkontrolle" in prompt
    assert "Subjective Norm benötigt Hinweise auf andere Personen" in prompt


def test_llm3_prompt_keeps_intrinsic_motivation_operationalization_unchanged() -> None:
    from state_assessment import load_state_assessment_prompt

    prompt = load_state_assessment_prompt()

    assert "Intrinsic Motivation [0-4]: Question 1-12" in prompt
    assert "* **Intrinsic Motivation**: Freude, Vergnügen, wahrgenommene Handlungsfreiheit und Kompetenz, wenig/kein Druck oder Anspannung" in prompt
    assert '"intrinsic_motivation": {' in prompt
    assert "IntVer1" not in prompt
    assert "pressure_tension" not in prompt


def test_llm3_prompt_change_does_not_change_schema_scales_or_update_parameters() -> None:
    from psychological_state import BACKEND_CONSTRUCT_RANGES
    from state_assessment import (
        ACTIVE_CONSTRUCTS,
        CONSTRUCT_ITEM_COUNTS,
        PSYCHOLOGICAL_CONSTRUCT_UPDATE_ALPHA,
        PSYCHOLOGICAL_CONSTRUCT_UPDATE_MAX_DAILY_CHANGE,
    )

    assert ACTIVE_CONSTRUCTS == (
        "automaticity",
        "pa_specific_self_control",
        "action_planning",
        "intention",
        "perceived_behavioral_control",
        "attitude_toward_the_behavior",
        "subjective_norm",
        "intrinsic_motivation",
        "motivational_competence",
    )
    assert CONSTRUCT_ITEM_COUNTS == {
        "automaticity": 4,
        "pa_specific_self_control": 3,
        "action_planning": 4,
        "intention": 3,
        "perceived_behavioral_control": 4,
        "attitude_toward_the_behavior": 5,
        "subjective_norm": 6,
        "intrinsic_motivation": 12,
        "motivational_competence": 4,
    }
    assert BACKEND_CONSTRUCT_RANGES == {
        "automaticity": (1, 7),
        "pa_specific_self_control": (1, 5),
        "action_planning": (1, 6),
        "intention": (1, 7),
        "perceived_behavioral_control": (1, 7),
        "attitude_toward_the_behavior": (1, 7),
        "subjective_norm": (1, 7),
        "intrinsic_motivation": (0, 4),
        "motivational_competence": (1, 5),
    }
    assert PSYCHOLOGICAL_CONSTRUCT_UPDATE_ALPHA == 0.20
    assert PSYCHOLOGICAL_CONSTRUCT_UPDATE_MAX_DAILY_CHANGE == 0.10


def test_empirical_persona_construct_mapping_remains_unchanged() -> None:
    from empirical_personas import PSYCHOLOGICAL_COLUMN_MAP

    assert PSYCHOLOGICAL_COLUMN_MAP == {
        "automaticity": "automaticity",
        "pa_specific_self_control": "pa_specific_self_control",
        "action_planning": "action_planning",
        "intention": "intention",
        "perceived_behavioral_control": "perceived_behavioral_control",
        "attitude": "attitude_toward_the_behavior",
        "subjective_norm": "subjective_norm",
        "intrinsic_motivation": "intrinsic_motivation",
        "motivational_competence": "motivational_competence",
    }


def _agent_context() -> dict:
    return {
        "persona_id": "ScenarioPersona_01_favourable_pa_context",
        "seed": 123,
        "day_index": 21,
        "phase": "holiday",
        "weekday": 2,
        "scenario": "favourable_pa_context",
        "task_description": "Use compact context.",
        "input_parameters": {
            "fitness_hours_week": 4.0,
            "values_normalized": {"must": "be removed"},
        },
        "selected_schedule_parameters": {
            "sport_frequency": 0.3,
            "raw_scale_means": {"must": "be removed"},
        },
        "psychological_state": {
            "values_normalized": {"automaticity": 0.5},
            "raw_scale_means": {"automaticity": 4.0},
        },
        "hourly_context_24h": _hourly_context(),
    }


def _valid_decision() -> dict:
    return {
        "persona_id": "ScenarioPersona_01_favourable_pa_context",
        "day_index": 21,
        "decision_code": 1,
        "decision_label": "do_planned_activity",
        "rationale_short": "Behavior policy and daily context support doing the activity.",
        "diary_entry": "Ich hatte heute genug Luft und habe mich wie geplant bewegt.",
    }




def _validated_decision(decision: dict | None = None) -> dict:
    from run_llm_pa_decision import validate_pa_decision_output

    payload = dict(decision or _valid_decision())
    return validate_pa_decision_output(payload, payload["persona_id"], payload["day_index"])


def _decision_with_label(decision_code: int, decision_label: str) -> dict:
    payload = _valid_decision()
    payload["decision_code"] = decision_code
    payload["decision_label"] = decision_label
    return payload


def test_run_llm_pa_decision_importable_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("UNI_LLM_API_KEY", raising=False)
    module = importlib.import_module("run_llm_pa_decision")
    importlib.reload(module)

    assert module.PA_DECISION_CODEBOOK[0] == "skip_activity"


def test_decision_codebook_contains_exact_codes() -> None:
    from run_llm_pa_decision import PA_DECISION_CODEBOOK

    assert PA_DECISION_CODEBOOK == {
        0: "skip_activity",
        1: "do_planned_activity",
        2: "adapt_activity",
        3: "extra_activity",
    }


@pytest.mark.parametrize("decision_code,decision_label", [(0, "skip_activity"), (1, "do_planned_activity"), (2, "adapt_activity"), (3, "extra_activity")])
def test_valid_decisions_do_not_include_app_specific_metadata(decision_code: int, decision_label: str) -> None:
    validated = _validated_decision(_decision_with_label(decision_code, decision_label))
    assert "app_interaction_status" not in validated
    assert validated["diary_entry_generated_for_simulation"] is True


def test_app_ignored_decision_is_rejected() -> None:
    with pytest.raises(ValueError, match="decision_code"):
        _validated_decision(_decision_with_label(4, "app_ignored"))


@pytest.mark.parametrize(
    ("decision_code", "decision_label", "expected_activity_performed"),
    [
        (0, "skip_activity", False),
        (1, "do_planned_activity", True),
        (2, "adapt_activity", True),
        (3, "extra_activity", True),
    ],
)
def test_valid_decisions_include_activity_performed_metadata(
    decision_code: int, decision_label: str, expected_activity_performed: bool
) -> None:
    validated = _validated_decision(_decision_with_label(decision_code, decision_label))

    assert validated["activity_performed"] is expected_activity_performed


def test_load_pa_decision_prompt_concatenates_prompt_and_fewshot_in_order(tmp_path: Path) -> None:
    from run_llm_pa_decision import load_pa_decision_prompt

    prompt_path = tmp_path / "PADecision_Prompt.md"
    fewshot_path = tmp_path / "PADecision_FewShot.md"
    prompt_path.write_text("BASE PROMPT", encoding="utf-8")
    fewshot_path.write_text("FEW SHOT", encoding="utf-8")

    combined = load_pa_decision_prompt(prompt_path, fewshot_path)

    assert "===== PA DECISION BASE PROMPT =====" in combined
    assert "===== PA DECISION FEW-SHOT EXAMPLES =====" in combined
    assert combined.index("BASE PROMPT") < combined.index("FEW SHOT")


@pytest.mark.parametrize("empty_file", ["prompt", "fewshot"])
def test_load_pa_decision_prompt_rejects_empty_files(tmp_path: Path, empty_file: str) -> None:
    from run_llm_pa_decision import load_pa_decision_prompt

    prompt_path = tmp_path / "PADecision_Prompt.md"
    fewshot_path = tmp_path / "PADecision_FewShot.md"
    prompt_path.write_text("BASE PROMPT", encoding="utf-8")
    fewshot_path.write_text("FEW SHOT", encoding="utf-8")
    if empty_file == "prompt":
        prompt_path.write_text("", encoding="utf-8")
    else:
        fewshot_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="empty"):
        load_pa_decision_prompt(prompt_path, fewshot_path)


def test_build_pa_decision_input_has_expected_structure_and_planned_activity() -> None:
    from run_llm_pa_decision import build_pa_decision_input

    planned_activity = {"label": "provided activity", "duration_min": 20}
    result = build_pa_decision_input(_agent_context(), BEHAVIOR_POLICY, planned_activity)

    assert set(result) == {
        "persona_id",
        "day_index",
        "behavior_policy",
        "behavior_policy_raw",
        "decision_context_has_planned_pa",
        "valid_decision_categories",
        "decision_source",
        "planned_physical_activity",
        "was_physical_activity_planned_today",
        "daily_context",
    }
    assert result["persona_id"] == "ScenarioPersona_01_favourable_pa_context"
    assert result["day_index"] == 21
    assert result["behavior_policy"] == BEHAVIOR_POLICY
    assert result["behavior_policy_raw"] == BEHAVIOR_POLICY
    assert result["decision_context_has_planned_pa"] is True
    assert result["valid_decision_categories"] == [
        "do_planned_activity",
        "adapt_activity",
        "skip_activity",
        "extra_activity",
    ]
    assert result["decision_source"] == "llm2_contextual_decision"
    assert result["planned_physical_activity"] == planned_activity
    assert result["was_physical_activity_planned_today"] is True
    assert "psychological_construct_values" not in result
    assert result["daily_context"]["persona_id"] == "ScenarioPersona_01_favourable_pa_context"
    assert result["daily_context"]["seed"] == 123
    assert result["daily_context"]["day_index"] == 21
    assert result["daily_context"]["phase"] == "holiday"
    assert result["daily_context"]["weekday"] == 2
    assert "task_description" not in result["daily_context"]
    assert "input_parameters" not in result["daily_context"]
    assert "selected_schedule_parameters" not in result["daily_context"]


def test_build_pa_decision_input_excludes_raw_psychological_state() -> None:
    from run_llm_pa_decision import build_pa_decision_input

    result = build_pa_decision_input(_agent_context(), BEHAVIOR_POLICY)
    serialized = json.dumps(result)

    assert "psychological_state" not in serialized
    assert "values_normalized" not in serialized
    assert "raw_scale_means" not in serialized


def test_unplanned_day_limits_valid_categories_without_sampling() -> None:
    from run_llm_pa_decision import build_pa_decision_input

    result = build_pa_decision_input(_agent_context(), BEHAVIOR_POLICY)

    assert result["decision_context_has_planned_pa"] is False
    assert result["valid_decision_categories"] == ["skip_activity", "extra_activity"]
    assert "sampled_decision_label" not in result
    assert "decision_sampling_seed" not in result


def test_valid_decision_categories_follow_planned_pa_availability() -> None:
    from run_llm_pa_decision import derive_valid_decision_categories

    assert derive_valid_decision_categories(has_planned_pa=True) == [
        "do_planned_activity",
        "adapt_activity",
        "skip_activity",
        "extra_activity",
    ]
    assert derive_valid_decision_categories(has_planned_pa=False) == [
        "skip_activity",
        "extra_activity",
    ]


def test_llm2_output_must_belong_to_valid_categories() -> None:
    from run_llm_pa_decision import validate_pa_decision_output

    with pytest.raises(ValueError, match="not valid for this day"):
        validate_pa_decision_output(
            _valid_decision(),
            _valid_decision()["persona_id"],
            _valid_decision()["day_index"],
            valid_decision_categories=["skip_activity", "extra_activity"],
            has_planned_pa=False,
        )


def test_prompt_distinguishes_unplanned_no_activity_from_skipping_plan() -> None:
    prompt = (ROOT_DIR / "PADecision_Prompt.md").read_text(encoding="utf-8")

    assert "keine spontane oder zusätzliche PA" in prompt
    assert "niemals als Überspringen" in prompt
    assert "sowohl an Tagen mit geplanter PA als auch an Tagen ohne geplante PA" in prompt
    assert "finale Entscheidung selbst treffen" in prompt


def test_build_pa_decision_input_keeps_complete_24h_hourly_context() -> None:
    from run_llm_pa_decision import build_pa_decision_input

    result = build_pa_decision_input(_agent_context(), BEHAVIOR_POLICY)

    assert len(result["daily_context"]["hourly_context_24h"]) == 24
    assert [entry["hour"] for entry in result["daily_context"]["hourly_context_24h"]] == list(range(24))


def test_build_pa_decision_input_rejects_incomplete_hourly_context() -> None:
    from run_llm_pa_decision import build_pa_decision_input

    context = _agent_context()
    context["hourly_context_24h"] = context["hourly_context_24h"][:23]

    with pytest.raises(ValueError, match="exactly 24"):
        build_pa_decision_input(context, BEHAVIOR_POLICY)


def test_valid_pa_decision_output_is_accepted() -> None:
    from run_llm_pa_decision import validate_pa_decision_output

    payload = _valid_decision()

    validated = validate_pa_decision_output(payload, payload["persona_id"], payload["day_index"])

    assert validated == {
        **payload,
        "activity_performed": True,
        "diary_entry_generated_for_simulation": True,
    }


def test_app_interaction_status_extra_is_rejected() -> None:
    from run_llm_pa_decision import validate_pa_decision_output
    payload = _valid_decision()
    payload["app_interaction_status"] = "engaged"
    with pytest.raises(ValueError, match="app_interaction_status"):
        validate_pa_decision_output(payload, payload["persona_id"], payload["day_index"])


def test_only_deterministic_pa_decision_metadata_extras_are_tolerated() -> None:
    from run_llm_pa_decision import validate_pa_decision_output

    payload = _valid_decision()
    payload.update(
        {
            "activity_performed": False,
            "diary_entry_generated_for_simulation": False,
            "unexpected_debug_field": "must still fail",
        }
    )

    with pytest.raises(ValueError, match="unexpected_debug_field"):
        validate_pa_decision_output(payload, payload["persona_id"], payload["day_index"])


def test_pa_decision_prompt_and_fewshot_do_not_output_metadata_fields() -> None:
    prompt_text = (ROOT_DIR / "PADecision_Prompt.md").read_text(encoding="utf-8")
    fewshot_text = (ROOT_DIR / "PADecision_FewShot.md").read_text(encoding="utf-8")

    metadata_fields = {
        "activity_performed",
        "diary_entry_generated_for_simulation",
    }

    for field_name in metadata_fields:
        assert field_name not in prompt_text
        assert field_name not in fewshot_text


@pytest.mark.parametrize("bad_code", [-1, 5, "1", True])
def test_invalid_decision_code_is_rejected(bad_code) -> None:
    from run_llm_pa_decision import validate_pa_decision_output

    payload = _valid_decision()
    payload["decision_code"] = bad_code

    with pytest.raises(ValueError):
        validate_pa_decision_output(payload, payload["persona_id"], payload["day_index"])


@pytest.mark.parametrize(
    "bad_label",
    ["not_done", "done_as_planned", "postponed", "adapted", "extra_movement", "not_completed"],
)
def test_wrong_or_old_decision_label_for_code_is_rejected(bad_label: str) -> None:
    from run_llm_pa_decision import validate_pa_decision_output

    payload = _valid_decision()
    payload["decision_label"] = bad_label

    with pytest.raises(ValueError, match="decision_label"):
        validate_pa_decision_output(payload, payload["persona_id"], payload["day_index"])


def test_mismatching_persona_id_is_rejected() -> None:
    from run_llm_pa_decision import validate_pa_decision_output

    payload = _valid_decision()

    with pytest.raises(ValueError, match="persona_id"):
        validate_pa_decision_output(payload, "other_persona", payload["day_index"])


def test_mismatching_day_index_is_rejected() -> None:
    from run_llm_pa_decision import validate_pa_decision_output

    payload = _valid_decision()

    with pytest.raises(ValueError, match="day_index"):
        validate_pa_decision_output(payload, payload["persona_id"], 22)


def test_missing_fields_are_rejected() -> None:
    from run_llm_pa_decision import validate_pa_decision_output

    payload = _valid_decision()
    payload.pop("diary_entry")

    with pytest.raises(ValueError, match="Missing"):
        validate_pa_decision_output(payload, payload["persona_id"], payload["day_index"])


def test_extra_fields_are_rejected() -> None:
    from run_llm_pa_decision import validate_pa_decision_output

    payload = _valid_decision()
    payload["main_context_factors"] = ["not required anymore"]

    with pytest.raises(ValueError, match="extra"):
        validate_pa_decision_output(payload, payload["persona_id"], payload["day_index"])


def test_invalid_json_is_rejected() -> None:
    from run_llm_pa_decision import parse_pa_decision_json

    with pytest.raises(ValueError, match="not valid JSON"):
        parse_pa_decision_json("not json")


def test_run_pipeline_for_context_with_fake_llms_writes_intermediate_and_final_outputs(tmp_path: Path) -> None:
    from run_llm_pa_decision import run_pipeline_for_context

    captured_pa_inputs: list[dict] = []

    def fake_behavior_runner(agent_context, **kwargs):
        assert kwargs["system_prompt"] == "behavior prompt"
        assert agent_context["psychological_state"]["values_normalized"] == {"automaticity": 0.5}
        return {"probabilities": dict(BEHAVIOR_POLICY)}

    def fake_pa_decision_runner(pa_decision_input, **kwargs):
        assert kwargs["system_prompt"] == "pa prompt"
        captured_pa_inputs.append(dict(pa_decision_input))
        serialized = json.dumps(pa_decision_input)
        assert "psychological_state" not in serialized
        assert "values_normalized" not in serialized
        assert "raw_scale_means" not in serialized
        assert pa_decision_input["valid_decision_categories"] == ["skip_activity", "extra_activity"]
        return _decision_with_label(0, "skip_activity")

    record = run_pipeline_for_context(
        _agent_context(),
        behavior_system_prompt="behavior prompt",
        pa_decision_system_prompt="pa prompt",
        output_dir=tmp_path,
        behavior_runner=fake_behavior_runner,
        pa_decision_runner=fake_pa_decision_runner,
    )

    behavior_path = tmp_path / "llm_behavior_probability_ScenarioPersona_01_favourable_pa_context.json"
    decision_path = tmp_path / "llm_pa_decision_ScenarioPersona_01_favourable_pa_context.json"
    assert behavior_path.exists()
    assert decision_path.exists()
    assert json.loads(behavior_path.read_text(encoding="utf-8"))["behavior_policy"] == BEHAVIOR_POLICY
    saved_decision = json.loads(decision_path.read_text(encoding="utf-8"))
    assert saved_decision["decision_label"] == "skip_activity"
    assert saved_decision["activity_performed"] is False
    daily_log_path = tmp_path / "llm_pa_decision_daily_log.csv"
    assert daily_log_path.exists()
    assert record["output_files"] == {
        "behavior_policy": str(behavior_path),
        "pa_decision": str(decision_path),
        "daily_decision_log": str(daily_log_path),
    }
    assert record["behavior_policy"] == BEHAVIOR_POLICY
    assert record["pa_decision"] == saved_decision
    assert record["decision_source"] == "llm2_contextual_decision"
    assert record["valid_decision_categories"] == ["skip_activity", "extra_activity"]
    assert len(captured_pa_inputs) == 1
    assert captured_pa_inputs[0]["planned_physical_activity"] is None
    assert captured_pa_inputs[0]["was_physical_activity_planned_today"] is False


def test_main_writes_combined_pipeline_output_with_metadata(tmp_path: Path, monkeypatch) -> None:
    import run_llm_pa_decision as module

    context_path = tmp_path / "contexts.json"
    behavior_prompt_path = tmp_path / "BehaviorProbability_Prompt.md"
    pa_prompt_path = tmp_path / "PADecision_Prompt.md"
    fewshot_path = tmp_path / "PADecision_FewShot.md"
    output_dir = tmp_path / "outputs"
    combined_path = tmp_path / "llm_pa_decision_pipeline_all_agents.json"

    context_path.write_text(
        json.dumps({"llm_contexts": [_agent_context()]}),
        encoding="utf-8",
    )
    behavior_prompt_path.write_text("behavior prompt", encoding="utf-8")
    pa_prompt_path.write_text("pa prompt", encoding="utf-8")
    fewshot_path.write_text("fewshot prompt", encoding="utf-8")

    def fake_run_pipeline_for_context(agent_context, **kwargs):
        assert kwargs["behavior_system_prompt"] == "behavior prompt"
        assert "pa prompt" in kwargs["pa_decision_system_prompt"]
        assert "fewshot prompt" in kwargs["pa_decision_system_prompt"]
        return {
            "persona_id": agent_context["persona_id"],
            "day_index": agent_context["day_index"],
            "behavior_policy": dict(BEHAVIOR_POLICY),
            "pa_decision": _validated_decision(),
            "output_files": {
                "behavior_policy": str(output_dir / "llm_behavior_probability_fake.json"),
                "pa_decision": str(output_dir / "llm_pa_decision_fake.json"),
            },
        }

    monkeypatch.setattr(module, "run_pipeline_for_context", fake_run_pipeline_for_context)

    module.main(
        [
            "--context-path",
            str(context_path),
            "--behavior-prompt-path",
            str(behavior_prompt_path),
            "--pa-decision-prompt-path",
            str(pa_prompt_path),
            "--pa-decision-fewshot-path",
            str(fewshot_path),
            "--output-dir",
            str(output_dir),
            "--combined-output-path",
            str(combined_path),
        ]
    )

    payload = json.loads(combined_path.read_text(encoding="utf-8"))
    assert payload["metadata"]["source_context_file"] == str(context_path)
    assert payload["metadata"]["behavior_probability_prompt_file"] == str(behavior_prompt_path)
    assert payload["metadata"]["pa_decision_prompt_file"] == str(pa_prompt_path)
    assert payload["metadata"]["pa_decision_fewshot_file"] == str(fewshot_path)
    assert payload["metadata"]["n_contexts"] == 1
    assert payload["records"][0]["behavior_policy"] == BEHAVIOR_POLICY
    assert payload["records"][0]["pa_decision"] == _validated_decision()


@pytest.mark.parametrize("decision_label", ["do_planned_activity", "skip_activity"])
def test_planned_activity_next_day_legacy_helper_is_deprecated(decision_label: str) -> None:
    from run_llm_pa_decision import generate_planned_activity_next_day

    with pytest.deprecated_call():
        planned_activity = generate_planned_activity_next_day(decision_label)

    assert set(planned_activity) == {
        "activity_type",
        "duration_min",
        "intensity",
        "preferred_time_window",
        "description",
    }
    assert isinstance(planned_activity["activity_type"], str)
    assert isinstance(planned_activity["duration_min"], int)
    assert isinstance(planned_activity["intensity"], str)
    assert isinstance(planned_activity["preferred_time_window"], list)
    assert len(planned_activity["preferred_time_window"]) == 2
    assert isinstance(planned_activity["description"], str)


def test_daily_decision_csv_log_rows_include_required_columns(tmp_path: Path) -> None:
    import csv
    from run_llm_pa_decision import (
        DAILY_DECISION_LOG_COLUMNS,
        build_pa_decision_input,
        write_daily_decision_log_row,
    )

    log_path = tmp_path / "llm_pa_decision_daily_log.csv"
    write_daily_decision_log_row(
        log_path=log_path,
        persona_id="ScenarioPersona_01_favourable_pa_context",
        day_index=21,
        pa_decision=_valid_decision(),
        activity_done=True,
        planned_physical_activity={"activity_type": "physical_activity"},
        was_physical_activity_planned_today=True,
        behavior_policy=BEHAVIOR_POLICY,
        decision_metadata=build_pa_decision_input(
            _agent_context(),
            BEHAVIOR_POLICY,
            {"activity_type": "physical_activity"},
        ),
        previous_psychological_constructs={"automaticity": 0.5},
        updated_psychological_constructs={"automaticity": 0.52},
    )

    with log_path.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 1
    assert tuple(rows[0].keys()) == DAILY_DECISION_LOG_COLUMNS
    assert rows[0]["persona_id"] == "ScenarioPersona_01_favourable_pa_context"
    assert rows[0]["day_index"] == "21"
    assert rows[0]["decision_label"] == "do_planned_activity"
    assert rows[0]["activity_done"] == "True"
    assert rows[0]["activity_performed"] == "True"
    assert "app_interaction_status" not in rows[0]
    assert rows[0]["diary_entry_generated_for_simulation"] == "True"
    assert json.loads(rows[0]["planned_physical_activity"]) == {
        "activity_type": "physical_activity"
    }
    assert rows[0]["was_physical_activity_planned_today"] == "True"
    assert json.loads(rows[0]["behavior_policy"]) == BEHAVIOR_POLICY
    assert json.loads(rows[0]["valid_decision_categories"]) == [
        "do_planned_activity",
        "adapt_activity",
        "skip_activity",
        "extra_activity",
    ]
    assert rows[0]["decision_source"] == "llm2_contextual_decision"
    assert json.loads(rows[0]["previous_psychological_constructs"]) == {"automaticity": 0.5}
    assert json.loads(rows[0]["updated_psychological_constructs"]) == {"automaticity": 0.52}


def test_run_pipeline_for_context_record_contains_closed_loop_update(tmp_path: Path) -> None:
    from run_llm_pa_decision import run_pipeline_for_context

    def fake_behavior_runner(agent_context, **kwargs):
        return {"probabilities": dict(BEHAVIOR_POLICY)}

    def fake_pa_decision_runner(pa_decision_input, **kwargs):
        assert "sampled_decision_label" not in pa_decision_input
        return _decision_with_label(0, "skip_activity")

    record = run_pipeline_for_context(
        _agent_context(),
        behavior_system_prompt="behavior prompt",
        pa_decision_system_prompt="pa prompt",
        output_dir=tmp_path,
        behavior_runner=fake_behavior_runner,
        pa_decision_runner=fake_pa_decision_runner,
    )

    assert "closed_loop_update" in record
    assert record["closed_loop_update"]["activity_done"] is False
    assert record["closed_loop_update"]["activity_performed"] is False
    assert "app_interaction_status" not in record["closed_loop_update"]
    assert record["closed_loop_update"]["diary_entry_generated_for_simulation"] is True
    assert record["closed_loop_update"]["previous_psychological_constructs"] == {
        "automaticity": 0.5
    }
    assert record["closed_loop_update"]["updated_psychological_constructs"] == {
        "automaticity": pytest.approx(0.5)
    }
    assert "planned_activity_next_day" not in record["closed_loop_update"]
    assert (tmp_path / "llm_pa_decision_daily_log.csv").exists()


def test_llm2_can_choose_different_decisions_for_same_probabilities_different_contexts(tmp_path: Path) -> None:
    from run_llm_pa_decision import build_pa_decision_input

    planned_activity = {"activity_type": "physical_activity", "duration_min": 60}
    favourable = build_pa_decision_input(_agent_context(), BEHAVIOR_POLICY, planned_activity)
    hindered_context = _agent_context()
    hindered_hours = []
    for entry in hindered_context["hourly_context_24h"]:
        updated = dict(entry)
        updated["is_wet"] = True
        updated["precipitation_mm"] = 4.0
        updated["energy_level"] = 0.2
        updated["energy_category"] = "low"
        hindered_hours.append(updated)
    hindered_context["hourly_context_24h"] = hindered_hours
    hindered = build_pa_decision_input(hindered_context, BEHAVIOR_POLICY, planned_activity)

    def contextual_mock(pa_decision_input: dict) -> dict:
        low_hours = sum(
            1
            for entry in pa_decision_input["daily_context"]["hourly_context_24h"]
            if entry["energy_category"] == "low"
        )
        if low_hours >= 8:
            return _decision_with_label(2, "adapt_activity")
        return _decision_with_label(1, "do_planned_activity")

    favourable_decision = contextual_mock(favourable)
    hindered_decision = contextual_mock(hindered)

    assert favourable["behavior_policy"] == hindered["behavior_policy"]
    assert favourable_decision["decision_label"] == "do_planned_activity"
    assert hindered_decision["decision_label"] == "adapt_activity"

def test_run_pa_decision_llm_request_uses_deterministic_defaults(monkeypatch, tmp_path: Path) -> None:
    import run_llm_pa_decision as module

    calls: list[dict] = []

    class _FakeMessage:
        content = json.dumps(_decision_with_label(0, "skip_activity"))

    class _FakeChoice:
        message = _FakeMessage()
        finish_reason = "stop"

    class _FakeResponse:
        choices = [_FakeChoice()]
        usage = {"completion_tokens": 1, "prompt_tokens": 1, "total_tokens": 2}

    class _FakeCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            return _FakeResponse()

    class _FakeClient:
        chat = type("Chat", (), {"completions": _FakeCompletions()})()

    monkeypatch.setattr(module, "get_client", lambda: _FakeClient())
    module.run_pa_decision_llm(
        module.build_pa_decision_input(_agent_context(), BEHAVIOR_POLICY),
        system_prompt="system",
        output_dir=tmp_path,
    )

    assert calls[0]["temperature"] == 0
    assert calls[0]["top_p"] == 1
    assert "seed" not in calls[0]


def test_run_pipeline_for_context_passes_generation_settings_to_both_llms(tmp_path: Path) -> None:
    from run_llm_pa_decision import run_pipeline_for_context

    behavior_kwargs: dict = {}
    pa_kwargs: dict = {}

    def behavior_runner(agent_context, **kwargs):
        del agent_context
        behavior_kwargs.update(kwargs)
        return {"probabilities": dict(BEHAVIOR_POLICY)}

    def pa_runner(pa_decision_input, **kwargs):
        pa_kwargs.update(kwargs)
        assert "sampled_decision_label" not in pa_decision_input
        return _decision_with_label(0, "skip_activity")

    run_pipeline_for_context(
        _agent_context(),
        behavior_system_prompt="behavior",
        pa_decision_system_prompt="pa",
        model="model",
        temperature=0.3,
        top_p=0.7,
        llm_seed=42,
        output_dir=tmp_path,
        behavior_runner=behavior_runner,
        pa_decision_runner=pa_runner,
    )

    assert behavior_kwargs["temperature"] == 0.3
    assert behavior_kwargs["top_p"] == 0.7
    assert behavior_kwargs["llm_seed"] == 42
    assert pa_kwargs["temperature"] == 0.3
    assert pa_kwargs["top_p"] == 0.7
    assert pa_kwargs["llm_seed"] == 42


def test_llm_pa_decision_cli_generation_defaults_and_overrides() -> None:
    from run_llm_pa_decision import parse_args

    defaults = parse_args([])
    custom = parse_args(["--temperature", "0.2", "--top-p", "0.8", "--llm-seed", "123"])

    assert defaults.temperature == 0
    assert defaults.top_p == 1
    assert defaults.llm_seed is None
    assert custom.temperature == 0.2
    assert custom.top_p == 0.8
    assert custom.llm_seed == 123


def test_pre_decision_context_keeps_planned_pa_but_not_realized_location() -> None:
    from run_llm_pa_decision import build_pa_decision_input

    context = _agent_context()
    context["hourly_context_24h"] = [
        {"hour": h, "activity_type": "downtime", "subtype": None, "current_location": "home",
         "poi_accessibility": {"indoor_activity": {"distance_km": 4.0, "travel_times_min": {"walk": 50}}}}
        for h in range(24)
    ]
    context["hourly_context_24h"][10].update({
        "activity_type": "physical_activity", "current_location": "indoor_activity",
        "poi_accessibility": {"indoor_activity": {"distance_km": 0.0, "travel_times_min": {"walk": 0}}},
    })
    planned = {"activity_type": "physical_activity", "scheduled_hours": [10], "start_hour": 10}

    result = build_pa_decision_input(context, BEHAVIOR_POLICY, planned)
    hour10 = result["daily_context"]["hourly_context_24h"][10]

    assert result["planned_physical_activity"] == planned
    assert hour10["activity_type"] == "planned_physical_activity"
    assert hour10["current_location"] == "home"
    assert hour10["planned_destination"] == "indoor_activity"
    assert hour10["poi_accessibility"]["indoor_activity"]["distance_km"] == 4.0
    assert set(result["valid_decision_categories"]) == {"do_planned_activity", "adapt_activity", "skip_activity", "extra_activity"}


def test_llm2_receives_behavior_policy_but_not_raw_constructs() -> None:
    from run_llm_pa_decision import build_pa_decision_input
    result = build_pa_decision_input(_agent_context(), BEHAVIOR_POLICY)
    assert result["behavior_policy"] == BEHAVIOR_POLICY
    assert set(result["behavior_policy"]) == {"do_planned_activity", "adapt_activity", "skip_activity", "extra_activity"}
    assert "psychological_construct_values" not in result


def _predecision_context_for_hour(entries: list[dict], planned: dict, hour: int) -> dict:
    from run_llm_pa_decision import build_pre_decision_hourly_context

    return build_pre_decision_hourly_context(entries, planned)[hour]


def _base_origin_edge_entries() -> list[dict]:
    entries = _hourly_context()
    for entry in entries:
        entry["poi_accessibility"] = {
            "indoor_activity": {"distance_km": 3.0, "travel_times_min": {"walk": 37.5}},
            "outdoor_activity": {"distance_km": 5.0, "travel_times_min": {"walk": 62.5}},
        }
    return entries


def test_pre_decision_origin_fallback_hour_zero_does_not_use_pa_target() -> None:
    entries = _base_origin_edge_entries()
    entries[0].update({
        "activity_type": "physical_activity",
        "subtype": "gym",
        "current_location": "indoor_activity",
        "poi_accessibility": {"indoor_activity": {"distance_km": 0.0, "travel_times_min": {"walk": 0.0}}},
    })
    planned = {"activity_type": "physical_activity", "scheduled_hours": [0], "start_hour": 0}

    hour0 = _predecision_context_for_hour(entries, planned, 0)

    assert hour0["current_location"] != "indoor_activity"
    assert hour0["current_location"] == "home"
    assert hour0["decision_status"] == "not_yet_realized"


def test_pre_decision_origin_fallback_all_preceding_entries_pa() -> None:
    entries = _base_origin_edge_entries()
    for hour in (0, 1, 2):
        entries[hour].update({
            "activity_type": "physical_activity",
            "subtype": "gym",
            "current_location": "indoor_activity",
            "poi_accessibility": {"indoor_activity": {"distance_km": 0.0, "travel_times_min": {"walk": 0.0}}},
        })
    planned = {"activity_type": "physical_activity", "scheduled_hours": [2], "start_hour": 2}

    hour2 = _predecision_context_for_hour(entries, planned, 2)

    assert hour2["current_location"] == "home"
    assert hour2["planned_destination"] == "indoor_activity"


def test_pre_decision_origin_skips_unknown_preceding_location_when_stable_exists() -> None:
    entries = _base_origin_edge_entries()
    entries[8]["current_location"] = "home"
    entries[9]["current_location"] = "unknown"
    entries[10].update({"activity_type": "physical_activity", "current_location": "indoor_activity"})
    planned = {"activity_type": "physical_activity", "scheduled_hours": [10], "start_hour": 10}

    hour10 = _predecision_context_for_hour(entries, planned, 10)

    assert hour10["current_location"] == "home"


def test_pre_decision_origin_skips_travel_transition_preceding_entry() -> None:
    entries = _base_origin_edge_entries()
    entries[8]["current_location"] = "workplace"
    entries[9].update({"activity_type": "travel", "subtype": "commute", "current_location": "unknown"})
    entries[10].update({"activity_type": "physical_activity", "current_location": "outdoor_activity"})
    planned = {"activity_type": "physical_activity", "scheduled_hours": [10], "start_hour": 10}

    hour10 = _predecision_context_for_hour(entries, planned, 10)

    assert hour10["current_location"] == "workplace"
    assert hour10["planned_destination"] == "outdoor_activity"


def test_pre_decision_origin_missing_accessibility_is_explicitly_unavailable() -> None:
    entries = _base_origin_edge_entries()
    entries[9].pop("poi_accessibility")
    entries[10].update({
        "activity_type": "physical_activity",
        "current_location": "indoor_activity",
        "poi_accessibility": {"indoor_activity": {"distance_km": 0.0, "travel_times_min": {"walk": 0.0}}},
    })
    planned = {"activity_type": "physical_activity", "scheduled_hours": [10], "start_hour": 10}

    hour10 = _predecision_context_for_hour(entries, planned, 10)

    assert hour10["poi_accessibility"]["_accessibility_unavailable"] is True
    assert hour10["poi_accessibility_validation_issue"] == "missing_origin_poi_accessibility"


def test_pre_decision_accessibility_invalidates_zero_distance_to_distinct_target() -> None:
    entries = _base_origin_edge_entries()
    entries[9]["poi_accessibility"] = {
        "indoor_activity": {"distance_km": 0.0, "travel_times_min": {"walk": 0.0}, "source": "bad_fixture"},
    }
    entries[10].update({"activity_type": "physical_activity", "current_location": "indoor_activity"})
    planned = {"activity_type": "physical_activity", "scheduled_hours": [10], "start_hour": 10}

    hour10 = _predecision_context_for_hour(entries, planned, 10)

    assert hour10["current_location"] == "home"
    assert hour10["poi_accessibility"]["indoor_activity"]["distance_km"] is None
    assert hour10["poi_accessibility_validation_issue"] == "zero_distance_to_distinct_planned_target"


def test_pre_decision_accessibility_missing_planned_target_key_is_unavailable() -> None:
    entries = _base_origin_edge_entries()
    entries[9]["poi_accessibility"] = {
        "outdoor_activity": {"distance_km": 2.0, "travel_times_min": {"walk": 25.0}},
    }
    entries[10].update({"activity_type": "physical_activity", "current_location": "indoor_activity"})
    planned = {"activity_type": "physical_activity", "scheduled_hours": [10], "start_hour": 10}

    hour10 = _predecision_context_for_hour(entries, planned, 10)

    assert hour10["poi_accessibility"]["_accessibility_unavailable"] is True
    assert hour10["poi_accessibility_validation_issue"] == "planned_target_missing_from_origin_accessibility"
    assert "indoor_activity" in hour10["poi_accessibility"]


def test_planned_pa_block_from_home_to_indoor_activity_uses_home_accessibility() -> None:
    from run_llm_pa_decision import build_pre_decision_hourly_context

    entries = _base_origin_edge_entries()
    entries[9]["current_location"] = "home"
    entries[9]["poi_accessibility"]["indoor_activity"]["distance_km"] = 3.7
    entries[10].update({"activity_type": "physical_activity", "current_location": "indoor_activity"})

    result = build_pre_decision_hourly_context(entries, {"scheduled_hours": [10]})

    assert result[10]["activity_type"] == "planned_physical_activity"
    assert result[10]["current_location"] == "home"
    assert result[10]["planned_destination"] == "indoor_activity"
    assert result[10]["decision_status"] == "not_yet_realized"
    assert result[10]["poi_accessibility"]["indoor_activity"]["distance_km"] == 3.7


def test_planned_pa_block_from_workplace_to_indoor_activity_uses_workplace_accessibility() -> None:
    from run_llm_pa_decision import build_pre_decision_hourly_context

    entries = _base_origin_edge_entries()
    entries[16]["current_location"] = "workplace"
    entries[16]["poi_accessibility"]["indoor_activity"]["distance_km"] = 8.4
    entries[17].update({"activity_type": "physical_activity", "current_location": "indoor_activity"})

    result = build_pre_decision_hourly_context(entries, {"scheduled_hours": [17]})

    assert result[17]["current_location"] == "workplace"
    assert result[17]["planned_destination"] == "indoor_activity"
    assert result[17]["poi_accessibility"]["indoor_activity"]["distance_km"] == 8.4


def test_multi_hour_planned_pa_block_uses_same_origin_for_all_hours() -> None:
    from run_llm_pa_decision import build_pre_decision_hourly_context

    entries = _base_origin_edge_entries()
    entries[18]["current_location"] = "home"
    entries[18]["poi_accessibility"]["indoor_activity"]["distance_km"] = 2.2
    for hour in (19, 20):
        entries[hour].update({"activity_type": "physical_activity", "current_location": "indoor_activity"})
        entries[hour]["poi_accessibility"] = {"indoor_activity": {"distance_km": 0.0, "travel_times_min": {"walk": 0.0}}}

    result = build_pre_decision_hourly_context(entries, {"scheduled_hours": [19, 20]})

    for hour in (19, 20):
        assert result[hour]["current_location"] == "home"
        assert result[hour]["planned_destination"] == "indoor_activity"
        assert result[hour]["poi_accessibility"]["indoor_activity"]["distance_km"] == 2.2


def test_day_without_planned_pa_is_unchanged() -> None:
    from run_llm_pa_decision import build_pre_decision_hourly_context

    entries = _base_origin_edge_entries()
    result = build_pre_decision_hourly_context(entries, None)

    assert result == entries


def test_pre_decision_context_does_not_mutate_original_hourly_context() -> None:
    from run_llm_pa_decision import build_pre_decision_hourly_context

    entries = _base_origin_edge_entries()
    original = json.loads(json.dumps(entries))
    entries[10].update({"activity_type": "physical_activity", "current_location": "indoor_activity"})
    original = json.loads(json.dumps(entries))

    result = build_pre_decision_hourly_context(entries, {"scheduled_hours": [10]})

    assert entries == original
    assert result is not entries
    assert result[10] is not entries[10]


def test_empirical_v1_2_input_forbids_schedule_pa_and_exposes_no_raw_constructs() -> None:
    from run_llm_pa_decision import build_pa_decision_input

    context = _agent_context()
    context["psychological_state"]["values_normalized"]["action_planning"] = 0.65
    result = build_pa_decision_input(
        context,
        BEHAVIOR_POLICY,
        empirical_pa_v1_2_metadata={
            "mode": "empirical_pa_v1_2",
            "action_planning_empirical_weight_applied": True,
        },
    )

    assert result["valid_decision_categories"] == ["skip_activity", "extra_activity"]
    assert result["planned_physical_activity"] is None
    assert result["was_physical_activity_planned_today"] is False
    assert result["empirical_pa_v1_2"]["enabled"] is True
    serialized = json.dumps(result)
    assert "psychological_state" not in serialized
    assert "values_normalized" not in serialized

    with pytest.raises(ValueError, match="must not receive schedule-derived"):
        build_pa_decision_input(
            context,
            BEHAVIOR_POLICY,
            planned_activity={"duration_min": 60},
            empirical_pa_v1_2_metadata={"mode": "empirical_pa_v1_2"},
        )


def test_empirical_v1_2_decision_requires_time_allocation() -> None:
    from run_llm_pa_decision import validate_pa_decision_output

    payload = {
        "persona_id": "p1",
        "day_index": 3,
        "decision_code": 3,
        "decision_label": "extra_activity",
        "start_hour": 17,
        "duration_min": 50,
        "rationale_short": "There is enough free time and energy for activity.",
        "diary_entry": "I trained moderately for about 50 minutes.",
    }
    validated = validate_pa_decision_output(
        payload,
        "p1",
        3,
        valid_decision_categories=["skip_activity", "extra_activity"],
        has_planned_pa=False,
        empirical_pa_v1_2=True,
    )

    assert validated["start_hour"] == 17
    assert validated["duration_min"] == 50
    assert validated["activity_performed"] is True


@pytest.mark.parametrize(
    ("decision_code", "decision_label", "duration_min"),
    [
        (0, "skip_activity", 20),
        (3, "extra_activity", 0),
    ],
)
def test_empirical_v1_2_rejects_inconsistent_activity_duration(
    decision_code: int,
    decision_label: str,
    duration_min: int,
) -> None:
    from run_llm_pa_decision import validate_pa_decision_output

    payload = {
        "persona_id": "p1",
        "day_index": 3,
        "decision_code": decision_code,
        "decision_label": decision_label,
        "start_hour": None if decision_label == "skip_activity" else 17,
        "duration_min": duration_min,
        "rationale_short": "context",
        "diary_entry": "entry",
    }
    with pytest.raises(ValueError):
        validate_pa_decision_output(
            payload,
            "p1",
            3,
            valid_decision_categories=["skip_activity", "extra_activity"],
            has_planned_pa=False,
            empirical_pa_v1_2=True,
        )


def test_empirical_v1_2_pipeline_neutralizes_ap_then_applies_empirical_weight(
    tmp_path: Path,
) -> None:
    from empirical_pa_v1_2 import ACTION_PLANNING_MEAN
    from run_llm_pa_decision import run_pipeline_for_context

    context = _agent_context()
    context["psychological_state"]["values_normalized"]["action_planning"] = 0.65
    seen: dict[str, object] = {}

    def fake_behavior_runner(agent_context, **kwargs):
        seen["llm1_action_planning"] = agent_context["psychological_state"][
            "values_normalized"
        ]["action_planning"]
        return {"probabilities": dict(BEHAVIOR_POLICY)}

    def fake_pa_runner(pa_decision_input, **kwargs):
        seen["pa_input"] = dict(pa_decision_input)
        return {
            "persona_id": pa_decision_input["persona_id"],
            "day_index": pa_decision_input["day_index"],
            "decision_code": 3,
            "decision_label": "extra_activity",
            "start_hour": 0,
            "duration_min": 45,
            "rationale_short": "Context supports activity.",
            "diary_entry": "I was active for about 45 minutes.",
        }

    record = run_pipeline_for_context(
        context,
        behavior_system_prompt="behavior prompt",
        pa_decision_system_prompt="pa prompt",
        behavior_runner=fake_behavior_runner,
        pa_decision_runner=fake_pa_runner,
        output_dir=tmp_path,
        empirical_pa_v1_2=True,
    )

    assert seen["llm1_action_planning"] == pytest.approx(ACTION_PLANNING_MEAN)
    pa_input = seen["pa_input"]
    assert isinstance(pa_input, dict)
    assert pa_input["valid_decision_categories"] == ["skip_activity", "extra_activity"]
    assert pa_input["behavior_policy"]["do_planned_activity"] == 0.0
    assert pa_input["behavior_policy"]["adapt_activity"] == 0.0
    assert "action_planning_value" not in json.dumps(pa_input)
    assert record["empirical_pa_v1_2"]["action_planning_value"] == pytest.approx(0.65)
    assert record["pa_decision"]["start_hour"] == 0
    assert record["pa_decision"]["duration_min"] == 45


def _empirical_context_with_activity_types(activity_types: list[str]) -> dict:
    context = _agent_context()
    context["seed"] = 11
    context["day_index"] = 2
    context["hourly_context_24h"] = [
        {**entry, "activity_type": activity_type, "hour": hour}
        for hour, (entry, activity_type) in enumerate(
            zip(_hourly_context(), activity_types, strict=True)
        )
    ]
    return context


def _empirical_pa_input(activity_types: list[str]) -> dict:
    from run_llm_pa_decision import build_pa_decision_input

    return build_pa_decision_input(
        _empirical_context_with_activity_types(activity_types),
        {
            "do_planned_activity": 0.0,
            "adapt_activity": 0.0,
            "skip_activity": 0.0,
            "extra_activity": 1.0,
        },
        empirical_pa_v1_2_metadata={"mode": "empirical_pa_v1_2"},
    )


def _assessment(
    *,
    start_hour: int | None,
    duration_min: int | None,
    probability: float = 1.0,
) -> dict:
    return {
        "persona_id": "ScenarioPersona_01_favourable_pa_context",
        "day_index": 2,
        "contextual_pa_probability": probability,
        "activity_if_performed": (
            None
            if start_hour is None or duration_min is None
            else {
                "start_hour": start_hour,
                "duration_min": duration_min,
                "activity_option": None,
                "rationale_short": "Synthetic feasible activity branch.",
                "diary_entry": "Synthetic activity diary.",
            }
        ),
        "no_activity_if_skipped": {
            "rationale_short": "Synthetic skipped branch.",
            "diary_entry": "Synthetic skipped diary.",
        },
    }


def _sample_empirical(activity_types: list[str], assessment: dict) -> dict:
    from empirical_pa_v1_2_stochastic import sample_final_decision

    return sample_final_decision(
        assessment,
        pa_decision_input=_empirical_pa_input(activity_types),
    )


def test_empirical_v1_2_no_downtime_forces_skip_even_with_high_prior() -> None:
    result = _sample_empirical(["work"] * 24, _assessment(start_hour=None, duration_min=None))

    assert result["decision_label"] == "skip_activity"
    assert result["start_hour"] is None
    assert result["duration_min"] == 0
    assert result["contextual_pa_probability"] == 1.0
    assert result["effective_pa_probability"] == 0.0
    assert result["sampled_decision_probability"] == 1.0
    assert result["pa_time_allocation"]["infeasibility_reason"] == "no_downtime_block_available"
    assert "kein freies Zeitfenster" in result["diary_entry"]


def test_empirical_v1_2_single_60_minute_block_allows_45_minutes() -> None:
    activity_types = ["work"] * 24
    activity_types[10] = "downtime"

    result = _sample_empirical(activity_types, _assessment(start_hour=10, duration_min=45))

    assert result["decision_label"] == "extra_activity"
    assert result["start_hour"] == 10
    assert result["duration_min"] == 45
    assert result["effective_pa_probability"] == 1.0


def test_empirical_v1_2_single_60_minute_block_rejects_90_minutes() -> None:
    activity_types = ["work"] * 24
    activity_types[10] = "downtime"

    with pytest.raises(ValueError, match="does not fit an available downtime block"):
        _sample_empirical(activity_types, _assessment(start_hour=10, duration_min=90))


def test_empirical_v1_2_separate_60_minute_blocks_do_not_allow_90_minutes() -> None:
    activity_types = ["work"] * 24
    activity_types[10] = "downtime"
    activity_types[12] = "downtime"

    with pytest.raises(ValueError, match="does not fit an available downtime block"):
        _sample_empirical(activity_types, _assessment(start_hour=10, duration_min=90))


def test_empirical_v1_2_two_hour_block_allows_pa_inside_block() -> None:
    activity_types = ["work"] * 24
    activity_types[16] = "downtime"
    activity_types[17] = "downtime"

    result = _sample_empirical(activity_types, _assessment(start_hour=16, duration_min=90))

    assert result["decision_label"] == "extra_activity"
    assert result["start_hour"] == 16
    assert result["duration_min"] == 90


def test_empirical_v1_2_exact_duration_fits_downtime_block() -> None:
    activity_types = ["work"] * 24
    activity_types[8] = "downtime"

    result = _sample_empirical(activity_types, _assessment(start_hour=8, duration_min=60))

    assert result["decision_label"] == "extra_activity"
    assert result["start_hour"] == 8
    assert result["duration_min"] == 60
    assert result["pa_time_allocation"]["time_allocation_feasible"] is True


def test_empirical_v1_2_multiple_suitable_windows_accepts_selected_block() -> None:
    activity_types = ["work"] * 24
    for hour in (8, 9, 18, 19):
        activity_types[hour] = "downtime"

    result = _sample_empirical(activity_types, _assessment(start_hour=18, duration_min=90))

    assert result["decision_label"] == "extra_activity"
    assert result["start_hour"] == 18
    assert result["pa_time_allocation"]["available_downtime_blocks"] == [
        {"start_hour": 8, "end_hour": 10, "duration_min": 120},
        {"start_hour": 18, "end_hour": 20, "duration_min": 120},
    ]


def test_empirical_v1_2_last_hour_of_day_accepts_60_minutes() -> None:
    activity_types = ["work"] * 24
    activity_types[23] = "downtime"

    result = _sample_empirical(activity_types, _assessment(start_hour=23, duration_min=60))

    assert result["decision_label"] == "extra_activity"
    assert result["start_hour"] == 23
    assert result["duration_min"] == 60


def test_empirical_v1_2_downtime_blocks_at_day_edges_are_detected() -> None:
    from empirical_pa_v1_2_stochastic import downtime_blocks

    hourly_context = [
        {"hour": hour, "activity_type": "downtime" if hour in {0, 1, 22, 23} else "work"}
        for hour in range(24)
    ]

    assert downtime_blocks(hourly_context) == [
        {"start_hour": 0, "end_hour": 2, "duration_min": 120},
        {"start_hour": 22, "end_hour": 24, "duration_min": 120},
    ]


def test_empirical_v1_2_rejects_incomplete_hourly_context_for_time_blocks() -> None:
    from empirical_pa_v1_2_stochastic import downtime_blocks

    with pytest.raises(ValueError, match="exactly 24"):
        downtime_blocks([{"hour": hour, "activity_type": "downtime"} for hour in range(23)])


def test_empirical_v1_2_rejects_nonchronological_hour_values() -> None:
    from empirical_pa_v1_2_stochastic import downtime_blocks

    hourly_context = [{"hour": hour, "activity_type": "downtime"} for hour in range(24)]
    hourly_context[10]["hour"] = 11
    hourly_context[11]["hour"] = 10

    with pytest.raises(ValueError, match="chronological"):
        downtime_blocks(hourly_context)


def test_empirical_v1_2_rejects_duplicate_hour_values() -> None:
    from empirical_pa_v1_2_stochastic import downtime_blocks

    hourly_context = [{"hour": hour, "activity_type": "downtime"} for hour in range(24)]
    hourly_context[12]["hour"] = 11

    with pytest.raises(ValueError, match="duplicate"):
        downtime_blocks(hourly_context)


def test_empirical_v1_2_rejects_missing_hour_values() -> None:
    from empirical_pa_v1_2_stochastic import downtime_blocks

    hourly_context = [{"hour": hour, "activity_type": "work"} for hour in range(24)]
    hourly_context[23]["hour"] = 24

    with pytest.raises(ValueError, match="exactly 0..23"):
        downtime_blocks(hourly_context)


@pytest.mark.parametrize("invalid_hour", [True, "10", None, 10.0])
def test_empirical_v1_2_rejects_invalid_hour_value_types(invalid_hour: object) -> None:
    from empirical_pa_v1_2_stochastic import downtime_blocks

    hourly_context = [{"hour": hour, "activity_type": "work"} for hour in range(24)]
    hourly_context[10]["hour"] = invalid_hour

    with pytest.raises(ValueError, match="integer hour"):
        downtime_blocks(hourly_context)


def test_empirical_v1_2_rejects_non_mapping_hourly_entries() -> None:
    from empirical_pa_v1_2_stochastic import downtime_blocks

    hourly_context: list[object] = [
        {"hour": hour, "activity_type": "work"} for hour in range(24)
    ]
    hourly_context[10] = ["not", "an", "object"]

    with pytest.raises(ValueError, match="entries must be objects"):
        downtime_blocks(hourly_context)


def test_empirical_v1_2_invalid_start_hour_is_rejected_before_sampling() -> None:
    assessment = _assessment(start_hour=24, duration_min=30)

    with pytest.raises(ValueError, match="start_hour"):
        _sample_empirical(["downtime"] * 24, assessment)


def test_empirical_v1_2_overlap_with_non_downtime_is_prevented() -> None:
    activity_types = ["sleep"] * 8 + ["work"] * 8 + ["social_time"] * 8
    activity_types[17] = "downtime"

    with pytest.raises(ValueError, match="does not fit an available downtime block"):
        _sample_empirical(activity_types, _assessment(start_hour=17, duration_min=90))


def test_empirical_v1_2_sampling_is_reproducible_for_identical_seed_and_llm_output() -> None:
    activity_types = ["work"] * 24
    activity_types[10] = "downtime"
    assessment = _assessment(start_hour=10, duration_min=45, probability=0.5)

    first = _sample_empirical(activity_types, assessment)
    second = _sample_empirical(activity_types, assessment)

    assert first == second


def test_empirical_v1_2_valid_time_window_keeps_seeded_sampling_probability() -> None:
    from empirical_pa_v1_2_stochastic import sampling_seed
    import random

    activity_types = ["work"] * 24
    activity_types[10] = "downtime"
    pa_input = _empirical_pa_input(activity_types)
    assessment = _assessment(start_hour=10, duration_min=45, probability=0.5)

    result = _sample_empirical(activity_types, assessment)
    expected_random_value = random.Random(sampling_seed(pa_input)).random()

    assert result["effective_pa_probability"] == result["contextual_pa_probability"] == 0.5
    assert result["decision_sampling_random_value"] == expected_random_value
    assert result["decision_label"] == (
        "extra_activity" if expected_random_value < 0.5 else "skip_activity"
    )
    assert result["sampled_decision_probability"] == 0.5


def test_empirical_v1_2_trace_stores_time_allocation_and_probabilities() -> None:
    activity_types = ["work"] * 24
    activity_types[10] = "downtime"

    result = _sample_empirical(activity_types, _assessment(start_hour=10, duration_min=45))

    assert result["contextual_pa_probability"] == 1.0
    assert result["effective_pa_probability"] == 1.0
    assert result["sampled_decision_label"] == result["decision_label"]
    assert result["pa_time_allocation"] == {
        "available_downtime_blocks": [{"start_hour": 10, "end_hour": 11, "duration_min": 60}],
        "requested_start_hour": 10,
        "requested_duration_min": 45,
        "time_allocation_feasible": True,
        "infeasibility_reason": None,
    }


def _flexibility_case(*, wet: bool = False, indoor: dict | None = None, outdoor: dict | None = None,
                      downtime_hour: int | None = 17, selected_option: str | None = None,
                      downtime_hours: tuple[int, ...] | None = None,
                      activity_start_hour: int | None = None,
                      probability: float = 1.0) -> dict:
    from empirical_pa_v1_2_stochastic import sample_final_decision

    active_hours = set(downtime_hours if downtime_hours is not None else (
        (downtime_hour,) if downtime_hour is not None else ()
    ))
    hourly = []
    for hour in range(24):
        entry = {"hour": hour, "activity_type": "downtime" if hour in active_hours else "work"}
        if hour in active_hours:
            entry.update({
                "is_wet": wet,
                "precipitation_mm": 2.0 if wet else 0.0,
                "current_location": "home",
                "energy_category": "medium",
                "poi_accessibility": {
                    key: value for key, value in (("indoor_activity", indoor), ("outdoor_activity", outdoor))
                    if value is not None
                },
            })
        hourly.append(entry)
    start_hour = activity_start_hour if activity_start_hour is not None else downtime_hour
    assessment = _assessment(start_hour=start_hour, duration_min=30, probability=probability)
    if assessment["activity_if_performed"] is not None:
        inferred_option = "indoor_activity" if indoor is not None else "outdoor_activity" if outdoor is not None else None
        assessment["activity_if_performed"]["activity_option"] = selected_option or inferred_option
    return sample_final_decision(assessment, pa_decision_input={
        "persona_id": assessment["persona_id"],
        "day_index": assessment["day_index"],
        "behavior_policy": {"extra_activity": 1.0},
        "daily_context": {"seed": 11, "hourly_context_24h": hourly},
    })


def _synthetic_poi(distance: float, walk_min: float) -> dict:
    return {"distance_km": distance, "travel_times_min": {"walk": walk_min}}


def test_empirical_v1_2_rain_with_evidenced_indoor_option() -> None:
    result = _flexibility_case(
        wet=True, indoor=_synthetic_poi(1.0, 10.0), outdoor=_synthetic_poi(2.0, 20.0),
        downtime_hours=(16, 17, 18),
    )
    trace = result["llm2_contextual_assessment"]["contextual_flexibility"]
    assert {barrier["category"] for barrier in trace["contextual_barriers"]} >= {"weather"}
    assert trace["available_pa_options"]["indoor_activity"]["status"] == "supported"
    assert trace["available_pa_options"]["outdoor_activity"]["status"] == "limited"
    assert result["contextual_response"]["used_option"] == "indoor_activity"
    assert result["contextual_response"]["potentially_mitigated_barriers"] == ["weather"]
    assert "barriers_navigated" not in result["contextual_response"]
    assert trace["adaptation_reference"] == "none_no_preplanned_pa"
    assert result["decision_label"] == "extra_activity"


def test_empirical_v1_2_rain_without_evidenced_indoor_alternative() -> None:
    result = _flexibility_case(
        wet=True, outdoor=_synthetic_poi(0.5, 5.0), downtime_hours=(16, 17, 18),
    )
    options = result["llm2_contextual_assessment"]["contextual_flexibility"]["available_pa_options"]
    assert options["indoor_activity"]["status"] == "unknown"
    assert options["indoor_activity"]["evidence"]["distance_km"] is None
    assert result["contextual_response"]["used_option"] == "outdoor_activity"


def test_empirical_v1_2_short_window_does_not_fit_long_activity() -> None:
    result = _flexibility_case(indoor=_synthetic_poi(0.0, 0.0))
    assert result["duration_min"] == 30
    assert result["pa_time_allocation"]["time_allocation_feasible"] is True
    assert "time" in result["contextual_response"]["barriers_present"]
    assert result["contextual_response"]["potentially_mitigated_barriers"] == []
    activity_types = ["work"] * 24
    activity_types[17] = "downtime"
    with pytest.raises(ValueError, match="does not fit an available downtime block"):
        _sample_empirical(activity_types, _assessment(start_hour=17, duration_min=90))


def test_empirical_v1_2_distance_evidence_distinguishes_options() -> None:
    result = _flexibility_case(
        indoor=_synthetic_poi(7.0, 70.0), outdoor=_synthetic_poi(0.5, 5.0),
        selected_option="outdoor_activity", downtime_hours=(16, 17, 18),
    )
    options = result["llm2_contextual_assessment"]["contextual_flexibility"]["available_pa_options"]
    assert options["indoor_activity"]["status"] == "limited"
    assert options["indoor_activity"]["evidence"]["round_trip_walk_min"] == 140.0
    assert options["outdoor_activity"]["status"] == "supported"
    barriers = result["llm2_contextual_assessment"]["contextual_flexibility"]["contextual_barriers"]
    assert any(item["category"] == "distance" and item["evidence"]["option"] == "indoor_activity" for item in barriers)
    assert result["contextual_response"]["used_option"] == "outdoor_activity"
    assert result["contextual_response"]["potentially_mitigated_barriers"] == []


def test_empirical_v1_2_late_pa_start_does_not_reuse_earlier_downtime_for_return_trip() -> None:
    late = _flexibility_case(
        indoor=_synthetic_poi(3.0, 40.0), downtime_hours=(17, 18, 19),
        activity_start_hour=19,
    )
    early = _flexibility_case(
        indoor=_synthetic_poi(3.0, 40.0), downtime_hours=(17, 18, 19),
        activity_start_hour=18,
    )
    late_option = late["llm2_contextual_assessment"]["contextual_flexibility"]["available_pa_options"]["indoor_activity"]
    early_option = early["llm2_contextual_assessment"]["contextual_flexibility"]["available_pa_options"]["indoor_activity"]
    assert late["pa_time_allocation"]["time_allocation_feasible"] is True
    assert late_option["evidence"]["block_duration_min"] == 180
    assert late_option["evidence"]["remaining_from_reference_min"] == 60
    assert late_option["evidence"]["minutes_before_start"] == 120
    assert late_option["evidence"]["minutes_after_activity"] == 30
    assert late_option["evidence"]["travel_fits_around_activity"] is False
    assert late_option["status"] == "limited"
    assert late["contextual_response"]["used_option"] is None
    assert early_option["evidence"]["travel_fits_around_activity"] is True
    assert early_option["status"] == "supported"
    assert late["effective_pa_probability"] == early["effective_pa_probability"] == 1.0


def test_empirical_v1_2_skip_still_records_weather_and_distance_barriers() -> None:
    rainy = _flexibility_case(
        wet=True, indoor=_synthetic_poi(1.0, 10.0),
        downtime_hours=(16, 17, 18), probability=0.0,
    )
    distant = _flexibility_case(
        indoor=_synthetic_poi(7.0, 70.0), outdoor=_synthetic_poi(0.5, 5.0),
        selected_option="outdoor_activity", downtime_hours=(16, 17, 18), probability=0.0,
    )
    for result, barrier in ((rainy, "weather"), (distant, "distance")):
        response = result["contextual_response"]
        assert result["decision_label"] == "skip_activity"
        assert response["activity_performed"] is False
        assert barrier in response["barriers_present"]
        assert response["used_option"] is None
        assert response["potentially_mitigated_barriers"] == []


def test_empirical_v1_2_near_option_does_not_imply_prior_distance_barrier() -> None:
    result = _flexibility_case(
        outdoor=_synthetic_poi(0.5, 5.0), downtime_hours=(16, 17, 18),
    )
    response = result["contextual_response"]
    assert response["used_option"] == "outdoor_activity"
    assert "distance" not in response["barriers_present"]
    assert response["potentially_mitigated_barriers"] == []
    assert response["adaptation_reference"] == "none_no_preplanned_pa"


def test_empirical_v1_2_context_trace_does_not_change_seeded_bernoulli_result() -> None:
    dry = _flexibility_case(
        indoor=_synthetic_poi(1.0, 10.0), downtime_hours=(16, 17, 18),
        probability=0.5,
    )
    wet = _flexibility_case(
        wet=True, indoor=_synthetic_poi(1.0, 10.0), downtime_hours=(16, 17, 18),
        probability=0.5,
    )
    for field in (
        "behavior_policy_pa_prior", "contextual_pa_probability",
        "effective_pa_probability", "decision_sampling_seed",
        "decision_sampling_random_value", "decision_label", "sampled_decision_probability",
    ):
        assert dry[field] == wet[field]


def test_empirical_v1_2_missing_travel_time_remains_unknown() -> None:
    result = _flexibility_case(
        indoor={"distance_km": 1.0, "travel_times_min": {}},
        downtime_hours=(16, 17, 18),
    )
    option = result["llm2_contextual_assessment"]["contextual_flexibility"]["available_pa_options"]["indoor_activity"]
    assert option["status"] == "unknown"
    assert option["evidence"]["walk_travel_time_min"] is None
    assert result["contextual_response"]["used_option"] is None


def test_empirical_v1_2_no_downtime_has_no_realized_option() -> None:
    result = _flexibility_case(downtime_hour=None)
    assert result["llm2_contextual_assessment"]["activity_if_performed"] is None
    assert result["effective_pa_probability"] == 0.0
    assert result["decision_label"] == "skip_activity"
    assert result["contextual_response"]["activity_performed"] is False
    assert result["contextual_response"]["used_option"] is None
    assert result["contextual_response"]["barriers_present"] == ["no_downtime"]
    assert result["contextual_response"]["potentially_mitigated_barriers"] == []
    assert result["contextual_response"]["adaptation_reference"] == "none_no_preplanned_pa"


def test_empirical_v1_2_rejects_fictive_option_without_downtime() -> None:
    from empirical_pa_v1_2_stochastic import sample_final_decision

    pa_input = _empirical_pa_input(["work"] * 24)
    with pytest.raises(ValueError, match="must be null when no downtime"):
        sample_final_decision(
            _assessment(start_hour=17, duration_min=30), pa_decision_input=pa_input,
        )


def test_empirical_v1_2_spontaneous_pa_stays_binary_without_plan() -> None:
    result = _flexibility_case(indoor=_synthetic_poi(0.0, 0.0))
    assert result["decision_label"] == "extra_activity"
    assert result["contextual_response"]["activity_performed"] is True
    assert result["contextual_response"]["adaptation_reference"] == "none_no_preplanned_pa"
    assert "adapt_activity" not in json.dumps(result)


def test_empirical_v1_2_proposed_option_is_not_realized_after_skip() -> None:
    from empirical_pa_v1_2_stochastic import sample_final_decision

    pa_input = _empirical_pa_input(["downtime"] * 24)
    assessment = _assessment(start_hour=10, duration_min=30, probability=0.0)
    assessment["activity_if_performed"]["activity_option"] = "indoor_activity"
    result = sample_final_decision(assessment, pa_decision_input=pa_input)
    assert result["decision_label"] == "skip_activity"
    assert result["llm2_contextual_assessment"]["activity_if_performed"]["activity_option"] == "indoor_activity"
    assert result["contextual_response"]["activity_performed"] is False
    assert result["contextual_response"]["used_option"] is None


def test_empirical_v1_2_only_explicit_illness_counts_as_physical_constraint() -> None:
    from empirical_pa_v1_2_stochastic import contextual_flexibility_trace

    pa_input = _empirical_pa_input(["downtime"] * 24)
    pa_input["daily_context"]["hourly_context_24h"][10]["active_constraints"] = [
        {"type": "WorkPressure", "name": "deadline"},
        {"type": "AcuteIllnessConstraint", "name": "illness_0001", "intensity": "low"},
    ]
    trace = contextual_flexibility_trace(
        pa_decision_input=pa_input, activity={"start_hour": 10, "duration_min": 30},
    )
    physical = next(item for item in trace["contextual_barriers"] if item["category"] == "physical_constraint")
    assert physical["evidence"]["active_constraints"] == [
        {"type": "AcuteIllnessConstraint", "name": "illness_0001", "intensity": "low"},
    ]


def test_empirical_v1_2_unknown_location_does_not_certify_option() -> None:
    from empirical_pa_v1_2_stochastic import contextual_flexibility_trace

    pa_input = _empirical_pa_input(["downtime"] * 24)
    pa_input["daily_context"]["hourly_context_24h"][10].update({
        "current_location": "unknown",
        "poi_accessibility": {"indoor_activity": _synthetic_poi(1.0, 10.0)},
    })
    trace = contextual_flexibility_trace(
        pa_decision_input=pa_input, activity={"start_hour": 10, "duration_min": 30},
    )
    assert trace["available_pa_options"]["indoor_activity"]["status"] == "unknown"


def _empirical_v1_2_fewshot_path() -> Path:
    return ROOT_DIR / "PADecision_EmpiricalV1_2_FewShot.md"


def _empirical_v1_2_fewshot_payloads() -> list[dict]:
    text = _empirical_v1_2_fewshot_path().read_text(encoding="utf-8")
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    return [json.loads(block) for block in blocks]


def _pa_input_for_fewshot_payload(
    payload: dict,
    activity_types: list[str],
    *,
    prior: float,
) -> dict:
    return {
        "persona_id": payload["persona_id"],
        "day_index": payload["day_index"],
        "behavior_policy": {
            "do_planned_activity": 0.0,
            "adapt_activity": 0.0,
            "skip_activity": 1.0 - prior,
            "extra_activity": prior,
        },
        "daily_context": {
            "seed": 100,
            "hourly_context_24h": [
                {"hour": hour, "activity_type": activity_type}
                for hour, activity_type in enumerate(activity_types)
            ],
        },
        "empirical_pa_v1_2": {"enabled": True},
    }


def test_empirical_v1_2_full_simulation_uses_dedicated_fewshot_file() -> None:
    from run_full_pa_simulation import EMPIRICAL_V1_2_PA_DECISION_FEWSHOT_PATH
    from run_llm_pa_decision import (
        EMPIRICAL_V1_2_PA_DECISION_PROMPT_PATH,
        load_pa_decision_prompt,
    )

    assert EMPIRICAL_V1_2_PA_DECISION_FEWSHOT_PATH == _empirical_v1_2_fewshot_path()
    combined = load_pa_decision_prompt(
        EMPIRICAL_V1_2_PA_DECISION_PROMPT_PATH,
        EMPIRICAL_V1_2_PA_DECISION_FEWSHOT_PATH,
    )

    assert "Keine verfügbare Freizeit" in combined
    assert "PA DECISION FEW-SHOT EXAMPLES" in combined


def test_empirical_v1_2_fewshot_examples_validate_against_contextual_schema() -> None:
    from empirical_pa_v1_2_stochastic import validate_contextual_assessment

    payloads = _empirical_v1_2_fewshot_payloads()

    assert len(payloads) == 3
    for payload in payloads:
        assert "decision_label" not in payload
        assert "decision_code" not in payload
        validated = validate_contextual_assessment(
            payload,
            expected_persona_id=payload["persona_id"],
            expected_day_index=payload["day_index"],
        )
        assert 0.0 <= validated["contextual_pa_probability"] <= 1.0


def test_empirical_v1_2_fewshot_no_downtime_example_is_present_and_forces_skip() -> None:
    from empirical_pa_v1_2_stochastic import sample_final_decision

    no_downtime = _empirical_v1_2_fewshot_payloads()[0]
    assert no_downtime["activity_if_performed"] is None

    result = sample_final_decision(
        no_downtime,
        pa_decision_input=_pa_input_for_fewshot_payload(
            no_downtime,
            ["work"] * 24,
            prior=0.68,
        ),
    )

    assert result["decision_label"] == "skip_activity"
    assert result["effective_pa_probability"] == 0.0
    assert result["pa_time_allocation"]["infeasibility_reason"] == "no_downtime_block_available"


def test_empirical_v1_2_fewshot_activity_examples_fit_declared_downtime_blocks() -> None:
    from empirical_pa_v1_2_stochastic import availability_trace, validate_contextual_assessment

    supportive, barrier = _empirical_v1_2_fewshot_payloads()[1:]

    supportive_hours = ["work"] * 24
    for hour in (17, 18):
        supportive_hours[hour] = "downtime"
    supportive_validated = validate_contextual_assessment(
        supportive,
        expected_persona_id=supportive["persona_id"],
        expected_day_index=supportive["day_index"],
    )
    assert availability_trace(
        supportive_validated,
        pa_decision_input=_pa_input_for_fewshot_payload(
            supportive,
            supportive_hours,
            prior=0.45,
        ),
    )["time_allocation_feasible"] is True

    barrier_hours = ["work"] * 24
    barrier_hours[20] = "downtime"
    barrier_validated = validate_contextual_assessment(
        barrier,
        expected_persona_id=barrier["persona_id"],
        expected_day_index=barrier["day_index"],
    )
    assert availability_trace(
        barrier_validated,
        pa_decision_input=_pa_input_for_fewshot_payload(
            barrier,
            barrier_hours,
            prior=0.74,
        ),
    )["time_allocation_feasible"] is True


def test_empirical_v1_2_no_downtime_work_does_not_imply_low_priority() -> None:
    from empirical_pa_v1_2_stochastic import sample_final_decision

    payload = _empirical_v1_2_fewshot_payloads()[0]
    activity_types = ["sleep"] * 24
    activity_types[7] = "commute"
    activity_types[8:19] = ["work"] * 11
    activity_types[19] = "commute"
    activity_types[20:22] = ["household"] * 2
    result = sample_final_decision(
        payload,
        pa_decision_input=_pa_input_for_fewshot_payload(
            payload, activity_types, prior=0.68,
        ),
    )

    assert result["decision_label"] == "skip_activity"
    assert result["effective_pa_probability"] == 0.0
    assert "kein freies Zeitfenster" in payload["no_activity_if_skipped"]["diary_entry"]
    assert "kein freies Zeitfenster" in result["diary_entry"]
    assert "motiviert" not in payload["no_activity_if_skipped"]["diary_entry"]
    assert "Priorität" not in payload["no_activity_if_skipped"]["diary_entry"]


def test_empirical_v1_2_downtime_skip_leaves_unreported_motive_open() -> None:
    from empirical_pa_v1_2_stochastic import sample_final_decision

    payload = dict(_empirical_v1_2_fewshot_payloads()[1])
    payload["contextual_pa_probability"] = 0.0
    activity_types = ["sleep"] * 24
    activity_types[8:17] = ["work"] * 9
    activity_types[17:19] = ["downtime", "downtime"]
    activity_types[19:21] = ["household"] * 2
    result = sample_final_decision(
        payload,
        pa_decision_input=_pa_input_for_fewshot_payload(
            payload, activity_types, prior=0.45,
        ),
    )

    assert result["decision_label"] == "skip_activity"
    assert result["pa_time_allocation"]["time_allocation_feasible"] is True
    assert result["diary_entry"] == payload["no_activity_if_skipped"]["diary_entry"]
    assert "Abend war frei" in result["diary_entry"]
    assert "warum sie heute ausbleibt" in result["rationale_short"]
    assert all(
        phrase not in result["diary_entry"]
        for phrase in ("ausgeruht", "wichtiger", "keine Motivation", "keine Selbstkontrolle")
    )


def test_empirical_v1_2_pa_after_obligations_does_not_imply_high_priority() -> None:
    from empirical_pa_v1_2_stochastic import sample_final_decision

    payload = dict(_empirical_v1_2_fewshot_payloads()[2])
    payload["contextual_pa_probability"] = 1.0
    activity_types = ["sleep"] * 24
    activity_types[8:19] = ["work"] * 11
    activity_types[19] = "social_time"
    activity_types[20] = "downtime"
    result = sample_final_decision(
        payload,
        pa_decision_input=_pa_input_for_fewshot_payload(
            payload, activity_types, prior=0.74,
        ),
    )

    assert result["decision_label"] == "extra_activity"
    assert result["duration_min"] == 30
    assert result["diary_entry"] == payload["activity_if_performed"]["diary_entry"]
    assert "langen Tag" in result["diary_entry"]
    assert all(
        phrase not in result["diary_entry"]
        for phrase in ("wichtiger", "Priorität", "Verpflichtungen zurückgestellt", "geschafft")
    )


def test_empirical_v1_2_priority_evidence_rules_and_fewshot_diaries() -> None:
    prompt = (ROOT_DIR / "PADecision_EmpiricalV1_2_Prompt.md").read_text(encoding="utf-8")
    assert "Keine PA wegen Zeitmangel bedeutet nicht geringe PA-Priorität" in prompt
    assert "Keine PA trotz `downtime` bedeutet nicht automatisch" in prompt
    assert "PA-Durchführung beweist umgekehrt keine generell hohe Priorität" in prompt
    assert "konkurrierende Aktivität **und deren Vorrang** ausdrücklich belegen" in prompt

    for payload in _empirical_v1_2_fewshot_payloads():
        branches = [payload["no_activity_if_skipped"]]
        if payload["activity_if_performed"] is not None:
            branches.append(payload["activity_if_performed"])
        for branch in branches:
            diary = branch["diary_entry"]
            assert diary.strip()
            assert all(
                phrase not in diary
                for phrase in ("eigentlich motiviert", "wollte mich eigentlich", "ausgeruht", "wichtiger", "Priorität")
            )


def test_empirical_v1_2_fewshots_do_not_change_stochastic_sampling_constants() -> None:
    from empirical_pa_v1_2_stochastic import DECISION_SAMPLING_SEED_OFFSET
    from run_llm_pa_decision import DECISION_SOURCE_EMPIRICAL_V1_2_STOCHASTIC

    assert DECISION_SAMPLING_SEED_OFFSET == 20_000_033
    assert (
        DECISION_SOURCE_EMPIRICAL_V1_2_STOCHASTIC
        == "llm2_contextual_probability_seeded_sampling"
    )


def test_empirical_v1_2_impossible_duration_with_available_downtime_triggers_retry(
    monkeypatch,
    tmp_path: Path,
) -> None:
    import run_llm_pa_decision as module

    activity_types = ["work"] * 24
    activity_types[10] = "downtime"
    pa_input = _empirical_pa_input(activity_types)
    responses = [
        _assessment(start_hour=10, duration_min=90),
        _assessment(start_hour=10, duration_min=45),
    ]
    calls: list[dict] = []

    class _FakeMessage:
        def __init__(self, content: str) -> None:
            self.content = content

    class _FakeChoice:
        finish_reason = "stop"

        def __init__(self, content: str) -> None:
            self.message = _FakeMessage(content)

    class _FakeResponse:
        usage = {"completion_tokens": 1, "prompt_tokens": 1, "total_tokens": 2}

        def __init__(self, content: str) -> None:
            self.choices = [_FakeChoice(content)]

    class _FakeCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            return _FakeResponse(json.dumps(responses[len(calls) - 1]))

    class _FakeClient:
        chat = type("Chat", (), {"completions": _FakeCompletions()})()

    monkeypatch.setattr(module, "get_client", lambda: _FakeClient())

    result = module.run_pa_decision_llm(
        pa_input,
        system_prompt="system",
        output_dir=tmp_path,
    )

    assert len(calls) == 2
    assert result["decision_label"] == "extra_activity"
    assert result["start_hour"] == 10
    assert result["duration_min"] == 45


def test_empirical_v1_2_forced_inactivity_diary_is_used_for_pipeline_record(
    monkeypatch,
    tmp_path: Path,
) -> None:
    import run_llm_pa_decision as module

    context = _empirical_context_with_activity_types(["work"] * 24)
    context["psychological_state"]["values_normalized"]["action_planning"] = 0.65

    def fake_behavior_runner(agent_context, **kwargs):
        del agent_context, kwargs
        return {
            "probabilities": {
                "do_planned_activity": 0.0,
                "adapt_activity": 0.0,
                "skip_activity": 0.0,
                "extra_activity": 1.0,
            }
        }

    class _FakeMessage:
        content = json.dumps(_assessment(start_hour=None, duration_min=None))

    class _FakeChoice:
        message = _FakeMessage()
        finish_reason = "stop"

    class _FakeResponse:
        choices = [_FakeChoice()]
        usage = {"completion_tokens": 1, "prompt_tokens": 1, "total_tokens": 2}

    class _FakeCompletions:
        def create(self, **kwargs):
            return _FakeResponse()

    class _FakeClient:
        chat = type("Chat", (), {"completions": _FakeCompletions()})()

    monkeypatch.setattr(module, "get_client", lambda: _FakeClient())

    record = module.run_pipeline_for_context(
        context,
        behavior_system_prompt="behavior",
        pa_decision_system_prompt="pa",
        behavior_runner=fake_behavior_runner,
        output_dir=tmp_path,
        empirical_pa_v1_2=True,
    )

    assert record["pa_decision"]["decision_label"] == "skip_activity"
    assert "kein freies Zeitfenster" in record["pa_decision"]["diary_entry"]
    assert "fehlende Motivation" not in record["pa_decision"]["diary_entry"]


def test_empirical_v1_2_forced_inactivity_flows_to_llm3_dry_run_prompt(
    monkeypatch,
    tmp_path: Path,
) -> None:
    import run_llm_pa_decision as module
    from state_assessment import ACTIVE_CONSTRUCTS, run_state_assessment

    context = _empirical_context_with_activity_types(["work"] * 24)
    context["psychological_state"]["values_normalized"] = {
        construct: 0.5 for construct in ACTIVE_CONSTRUCTS
    }
    context["psychological_state"]["values_normalized"]["action_planning"] = 0.65

    def fake_behavior_runner(agent_context, **kwargs):
        del agent_context, kwargs
        return {
            "probabilities": {
                "do_planned_activity": 0.0,
                "adapt_activity": 0.0,
                "skip_activity": 0.0,
                "extra_activity": 1.0,
            }
        }

    class _FakeMessage:
        content = json.dumps(_assessment(start_hour=None, duration_min=None))

    class _FakeChoice:
        message = _FakeMessage()
        finish_reason = "stop"

    class _FakeResponse:
        choices = [_FakeChoice()]
        usage = {"completion_tokens": 1, "prompt_tokens": 1, "total_tokens": 2}

    class _FakeCompletions:
        def create(self, **kwargs):
            return _FakeResponse()

    class _FakeClient:
        chat = type("Chat", (), {"completions": _FakeCompletions()})()

    monkeypatch.setattr(module, "get_client", lambda: _FakeClient())

    record = module.run_pipeline_for_context(
        context,
        behavior_system_prompt="behavior",
        pa_decision_system_prompt="pa",
        behavior_runner=fake_behavior_runner,
        output_dir=tmp_path,
        empirical_pa_v1_2=True,
    )
    decision = record["pa_decision"]

    prompt_template = "\n".join(
        [
            "{persona_id}",
            "{day_index}",
            "{previous_psychological_construct_values}",
            "{current_decision_label}",
            "{was_physical_activity_planned_today}",
            "{planned_physical_activity_summary}",
            "{current_simulated_diary_entry}",
            "{previous_diary_entries}",
            "{previous_diary_entries_summary}",
        ]
    )
    assessment = run_state_assessment(
        persona_id=record["persona_id"],
        day_index=record["day_index"],
        previous_normalized_values={
            construct: 0.5 for construct in ACTIVE_CONSTRUCTS
        },
        current_simulated_diary_entry=decision["diary_entry"],
        previous_diary_entries=[],
        current_decision_label=decision["decision_label"],
        was_physical_activity_planned_today=False,
        planned_physical_activity_summary=None,
        prompt_template=prompt_template,
        dry_run=True,
        output_dir=tmp_path,
    )

    assert assessment["state_assessment_mode"] == "dry_run_mock"
    assert "skip_activity" in assessment["rendered_prompt"]
    assert "kein freies Zeitfenster" in assessment["rendered_prompt"]
    assert "fehlende Motivation" not in assessment["rendered_prompt"]


def _state_values(value: float = 0.5) -> dict[str, float]:
    from state_assessment import ACTIVE_CONSTRUCTS

    return {construct: value for construct in ACTIVE_CONSTRUCTS}


def _raw_state_assessment_payload(
    *,
    persona_id: str,
    day_index: int,
    scores_by_construct: dict[str, object],
) -> dict:
    from psychological_state import BACKEND_CONSTRUCT_RANGES
    from state_assessment import ACTIVE_CONSTRUCTS, CONSTRUCT_ITEM_COUNTS

    item_scores = {}
    for construct in ACTIVE_CONSTRUCTS:
        low, high = BACKEND_CONSTRUCT_RANGES[construct]
        score = scores_by_construct.get(construct)
        item_scores[construct] = {
            "items": [
                {
                    "question_id": f"{construct}_q{index}",
                    "score": score,
                    "range": f"{low:g}-{high:g}",
                    "evidence_spans": [] if score is None else ["synthetic diary evidence"],
                    "reasoning_short": "" if score is None else "synthetic fixed score",
                }
                for index in range(1, CONSTRUCT_ITEM_COUNTS[construct] + 1)
            ],
            "mean_score": score,
        }
    return {
        "persona_id": persona_id,
        "day_index": day_index,
        "item_scores": item_scores,
        "metadata": {"mode": "synthetic_test_payload"},
    }


def _scores_with_only(construct: str, score: float | None) -> dict[str, float | None]:
    from state_assessment import ACTIVE_CONSTRUCTS

    return {
        active_construct: (score if active_construct == construct else None)
        for active_construct in ACTIVE_CONSTRUCTS
    }


def _run_mocked_state_assessment(
    *,
    monkeypatch,
    tmp_path: Path,
    previous_values: dict[str, float],
    scores_by_construct: dict[str, object],
    persona_id: str,
    day_index: int,
    diary_entry: str,
    current_decision_label: str,
    was_planned: bool,
    planned_summary: dict | None,
) -> tuple[dict, list[str]]:
    import state_assessment as module

    captured_prompts: list[str] = []

    def fake_call_state_assessment_llm(rendered_prompt: str, **kwargs):
        del kwargs
        captured_prompts.append(rendered_prompt)
        payload = _raw_state_assessment_payload(
            persona_id=persona_id,
            day_index=day_index,
            scores_by_construct=scores_by_construct,
        )
        return {
            "raw_response": json.dumps(payload),
            "finish_reason": "stop",
            "resource_usage": {
                "prompt_tokens": 1,
                "response_tokens": 1,
                "tokens_total": 2,
                "token_source": "synthetic_test",
                "paper_seconds": 0.0,
            },
        }

    monkeypatch.setattr(module, "call_state_assessment_llm", fake_call_state_assessment_llm)
    assessment = module.run_state_assessment(
        persona_id=persona_id,
        day_index=day_index,
        previous_normalized_values=previous_values,
        current_simulated_diary_entry=diary_entry,
        previous_diary_entries=[],
        current_decision_label=current_decision_label,
        was_physical_activity_planned_today=was_planned,
        planned_physical_activity_summary=planned_summary,
        dry_run=False,
        output_dir=tmp_path,
    )
    return assessment, captured_prompts


def test_llm3_dynamics_seven_days_forced_inactivity_keeps_null_constructs_unchanged(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from state_assessment import ACTIVE_CONSTRUCTS

    values = _state_values()
    scores = {construct: None for construct in ACTIVE_CONSTRUCTS}

    for day_index in range(7):
        decision = _sample_empirical(
            ["work"] * 24,
            _assessment(start_hour=None, duration_min=None, probability=1.0),
        )

        assert decision["decision_label"] == "skip_activity"
        assert decision["start_hour"] is None
        assert decision["duration_min"] == 0
        assert decision["effective_pa_probability"] == 0.0
        assert decision["sampled_decision_probability"] == 1.0
        assert decision["pa_time_allocation"]["infeasibility_reason"] == (
            "no_downtime_block_available"
        )

        assessment, prompts = _run_mocked_state_assessment(
            monkeypatch=monkeypatch,
            tmp_path=tmp_path,
            previous_values=values,
            scores_by_construct=scores,
            persona_id="SyntheticPersona_NoFreeTime",
            day_index=day_index,
            diary_entry=decision["diary_entry"],
            current_decision_label=decision["decision_label"],
            was_planned=False,
            planned_summary=None,
        )

        assert len(prompts) == 1
        assert "skip_activity" in prompts[0]
        assert "kein freies Zeitfenster" in prompts[0]
        assert "fehlende Motivation" not in prompts[0]

        updated = assessment["psychological_construct_values_after_state_assessment"]
        for construct in ("intention", "pa_specific_self_control", "intrinsic_motivation"):
            assert updated[construct] == pytest.approx(values[construct])
        assert updated == pytest.approx(values)
        values = updated


def test_llm3_dynamics_seven_days_regular_pa_updates_only_mocked_construct(
    monkeypatch,
    tmp_path: Path,
) -> None:
    values = _state_values()
    activity_types = ["work"] * 24
    activity_types[18] = "downtime"

    for day_index in range(7):
        before = dict(values)
        decision = _sample_empirical(
            activity_types,
            _assessment(start_hour=18, duration_min=45, probability=1.0),
        )

        assert decision["decision_label"] == "extra_activity"
        assert decision["start_hour"] == 18
        assert decision["duration_min"] == 45
        assert decision["pa_time_allocation"]["time_allocation_feasible"] is True

        assessment, prompts = _run_mocked_state_assessment(
            monkeypatch=monkeypatch,
            tmp_path=tmp_path,
            previous_values=values,
            scores_by_construct=_scores_with_only("action_planning", 6.0),
            persona_id="SyntheticPersona_RegularPA",
            day_index=day_index,
            diary_entry=decision["diary_entry"],
            current_decision_label=decision["decision_label"],
            was_planned=False,
            planned_summary=None,
        )

        assert len(prompts) == 1
        assert "extra_activity" in prompts[0]
        assert "Was PA planned today: false" in prompts[0]
        assert "Planned PA summary: null" in prompts[0]
        updated = assessment["psychological_construct_values_after_state_assessment"]
        assert updated["action_planning"] > before["action_planning"]
        assert updated["action_planning"] - before["action_planning"] <= 0.1000000001
        for construct, value in updated.items():
            assert 0.0 <= value <= 1.0
            if construct != "action_planning":
                assert value == pytest.approx(before[construct])
        values = updated


def test_llm3_dynamics_same_pa_path_keeps_structured_inputs_except_diary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    previous = _state_values()
    observed_diary = "Ich war heute von 18 Uhr bis 18:45 Uhr körperlich aktiv."
    interpretive_diary = (
        "Ich war heute von 18 Uhr bis 18:45 Uhr körperlich aktiv und fühlte mich "
        "dabei sehr entschlossen."
    )

    observed, observed_prompts = _run_mocked_state_assessment(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        previous_values=previous,
        scores_by_construct=_scores_with_only("action_planning", 6.0),
        persona_id="SyntheticPersona_SamePAPath",
        day_index=3,
        diary_entry=observed_diary,
        current_decision_label="extra_activity",
        was_planned=False,
        planned_summary=None,
    )
    interpretive, interpretive_prompts = _run_mocked_state_assessment(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        previous_values=previous,
        scores_by_construct=_scores_with_only("action_planning", 6.0),
        persona_id="SyntheticPersona_SamePAPath",
        day_index=3,
        diary_entry=interpretive_diary,
        current_decision_label="extra_activity",
        was_planned=False,
        planned_summary=None,
    )

    assert observed_diary in observed_prompts[0]
    assert interpretive_diary in interpretive_prompts[0]
    assert "Was PA planned today: false" in observed_prompts[0]
    assert "Was PA planned today: false" in interpretive_prompts[0]
    assert "Planned PA summary: null" in observed_prompts[0]
    assert "Planned PA summary: null" in interpretive_prompts[0]
    assert observed_prompts[0] != interpretive_prompts[0]
    assert observed_prompts[0].replace(observed_diary, "<DIARY>") == (
        interpretive_prompts[0].replace(interpretive_diary, "<DIARY>")
    )
    assert observed["state_assessment_mean_scores_raw"] == (
        interpretive["state_assessment_mean_scores_raw"]
    )
    assert observed["psychological_construct_values_after_state_assessment"] == (
        interpretive["psychological_construct_values_after_state_assessment"]
    )


def _simulate_normalized_state_path(
    *,
    start_value: float,
    target_value: float | None,
    days: int,
) -> list[dict[str, float]]:
    from state_assessment import ACTIVE_CONSTRUCTS, apply_smoothed_bounded_construct_update

    values = {construct: start_value for construct in ACTIVE_CONSTRUCTS}
    target_values = {construct: target_value for construct in ACTIVE_CONSTRUCTS}
    raw_targets = {construct: target_value for construct in ACTIVE_CONSTRUCTS}
    path = []
    for _ in range(days):
        update = apply_smoothed_bounded_construct_update(
            values,
            target_values,
            raw_targets,
        )
        values = update["updated_values"]
        path.append(dict(values))
    return path


def test_llm3_dynamics_math_extremes_are_deterministic_bounded_and_null_safe() -> None:
    from state_assessment import ACTIVE_CONSTRUCTS

    high_30_first = _simulate_normalized_state_path(
        start_value=0.5,
        target_value=1.0,
        days=30,
    )
    high_30_second = _simulate_normalized_state_path(
        start_value=0.5,
        target_value=1.0,
        days=30,
    )
    low_90 = _simulate_normalized_state_path(start_value=0.5, target_value=0.0, days=90)
    null_90 = _simulate_normalized_state_path(start_value=0.5, target_value=None, days=90)
    from_zero = _simulate_normalized_state_path(start_value=0.0, target_value=1.0, days=7)
    from_one = _simulate_normalized_state_path(start_value=1.0, target_value=0.0, days=7)

    assert high_30_first == high_30_second
    for path in (high_30_first, low_90, null_90, from_zero, from_one):
        previous = None
        for values in path:
            assert set(values) == set(ACTIVE_CONSTRUCTS)
            for value in values.values():
                assert 0.0 <= value <= 1.0
            if previous is not None:
                for construct in ACTIVE_CONSTRUCTS:
                    assert abs(values[construct] - previous[construct]) <= 0.1000000001
            previous = values

    assert all(value == pytest.approx(0.5) for day in null_90 for value in day.values())
    assert all(value == pytest.approx(0.1) for value in from_zero[0].values())
    assert all(value == pytest.approx(0.9) for value in from_one[0].values())
    assert all(high_30_first[6][construct] < high_30_first[29][construct] for construct in ACTIVE_CONSTRUCTS)
    assert all(low_90[6][construct] > low_90[29][construct] for construct in ACTIVE_CONSTRUCTS)


def test_llm3_dynamics_validation_caps_numeric_scores_and_rejects_nonnumeric_items() -> None:
    from state_assessment import validate_state_assessment_output

    capped_payload = _raw_state_assessment_payload(
        persona_id="SyntheticPersona_InvalidScores",
        day_index=0,
        scores_by_construct=_scores_with_only("automaticity", 99.0),
    )
    capped = validate_state_assessment_output(
        capped_payload,
        expected_persona_id="SyntheticPersona_InvalidScores",
        expected_day_index=0,
    )

    assert capped["mean_scores_raw"]["automaticity"] == pytest.approx(7.0)

    invalid_payload = _raw_state_assessment_payload(
        persona_id="SyntheticPersona_InvalidScores",
        day_index=0,
        scores_by_construct=_scores_with_only("automaticity", 4.0),
    )
    invalid_payload["item_scores"]["automaticity"]["items"][0]["score"] = "not numeric"

    with pytest.raises(ValueError, match="numeric or null"):
        validate_state_assessment_output(
            invalid_payload,
            expected_persona_id="SyntheticPersona_InvalidScores",
            expected_day_index=0,
        )
