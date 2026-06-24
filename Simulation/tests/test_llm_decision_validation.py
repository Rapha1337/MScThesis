from __future__ import annotations

import importlib
import json
from pathlib import Path
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
    assert hour10["activity_type"] == "pre_decision_context"
    assert hour10["current_location"] == "home"
    assert hour10["planned_pa_target_location"] == "indoor_activity"
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
    assert hour0["pre_decision_origin_location"] == "home"
    assert hour0["poi_accessibility_origin_location"] == "home"
    assert hour0["planned_activity_not_yet_realized"] is True


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
    assert hour2["pre_decision_origin_location"] == "home"
    assert hour2["planned_pa_target_location"] == "indoor_activity"


def test_pre_decision_origin_skips_unknown_preceding_location_when_stable_exists() -> None:
    entries = _base_origin_edge_entries()
    entries[8]["current_location"] = "home"
    entries[9]["current_location"] = "unknown"
    entries[10].update({"activity_type": "physical_activity", "current_location": "indoor_activity"})
    planned = {"activity_type": "physical_activity", "scheduled_hours": [10], "start_hour": 10}

    hour10 = _predecision_context_for_hour(entries, planned, 10)

    assert hour10["pre_decision_origin_location"] == "home"


def test_pre_decision_origin_skips_travel_transition_preceding_entry() -> None:
    entries = _base_origin_edge_entries()
    entries[8]["current_location"] = "workplace"
    entries[9].update({"activity_type": "travel", "subtype": "commute", "current_location": "unknown"})
    entries[10].update({"activity_type": "physical_activity", "current_location": "outdoor_activity"})
    planned = {"activity_type": "physical_activity", "scheduled_hours": [10], "start_hour": 10}

    hour10 = _predecision_context_for_hour(entries, planned, 10)

    assert hour10["pre_decision_origin_location"] == "workplace"
    assert hour10["planned_pa_target_location"] == "outdoor_activity"


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

    assert hour10["pre_decision_origin_location"] == "home"
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
