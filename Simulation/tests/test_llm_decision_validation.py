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
    "adapt_activity": 0.20,
    "postpone_activity": 0.15,
    "skip_activity": 0.15,
    "extra_activity": 0.10,
    "app_ignored": 0.15,
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
        "decision_label": "done_as_planned",
        "rationale_short": "Behavior policy and daily context support doing the activity.",
        "diary_entry": "Ich hatte heute genug Luft und habe mich wie geplant bewegt.",
    }


def test_run_llm_pa_decision_importable_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("UNI_LLM_API_KEY", raising=False)
    module = importlib.import_module("run_llm_pa_decision")
    importlib.reload(module)

    assert module.PA_DECISION_CODEBOOK[0] == "not_done"


def test_decision_codebook_contains_exact_codes() -> None:
    from run_llm_pa_decision import PA_DECISION_CODEBOOK

    assert PA_DECISION_CODEBOOK == {
        0: "not_done",
        1: "done_as_planned",
        2: "postponed",
        3: "adapted",
        4: "extra_movement",
        5: "app_ignored",
    }


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
        "planned_activity",
        "daily_context",
    }
    assert result["persona_id"] == "ScenarioPersona_01_favourable_pa_context"
    assert result["day_index"] == 21
    assert result["behavior_policy"] == BEHAVIOR_POLICY
    assert result["planned_activity"] == planned_activity
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

    assert validate_pa_decision_output(payload, payload["persona_id"], payload["day_index"]) == payload


@pytest.mark.parametrize("bad_code", [-1, 6, "1", True])
def test_invalid_decision_code_is_rejected(bad_code) -> None:
    from run_llm_pa_decision import validate_pa_decision_output

    payload = _valid_decision()
    payload["decision_code"] = bad_code

    with pytest.raises(ValueError):
        validate_pa_decision_output(payload, payload["persona_id"], payload["day_index"])


@pytest.mark.parametrize(
    "bad_label",
    ["not_done", "not_completed", "completed_as_planned", "adapted_completed"],
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
        return _valid_decision()

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
    assert json.loads(decision_path.read_text(encoding="utf-8")) == _valid_decision()
    daily_log_path = tmp_path / "llm_pa_decision_daily_log.csv"
    assert daily_log_path.exists()
    assert record["output_files"] == {
        "behavior_policy": str(behavior_path),
        "pa_decision": str(decision_path),
        "daily_decision_log": str(daily_log_path),
    }
    assert record["behavior_policy"] == BEHAVIOR_POLICY
    assert record["pa_decision"] == _valid_decision()
    assert len(captured_pa_inputs) == 1
    assert captured_pa_inputs[0]["planned_activity"] is None


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
            "pa_decision": _valid_decision(),
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
    assert payload["records"][0]["pa_decision"] == _valid_decision()


@pytest.mark.parametrize("decision_label", ["done_as_planned", "adapted", "extra_movement"])
def test_simple_construct_update_increases_after_successful_pa(decision_label: str) -> None:
    from run_llm_pa_decision import update_psychological_constructs_simple

    updated = update_psychological_constructs_simple(
        {"automaticity": 0.50, "motivation": 0.20, "pressure_tension": 0.30}, decision_label
    )

    assert updated == {
        "automaticity": pytest.approx(0.52),
        "motivation": pytest.approx(0.22),
        "pressure_tension": pytest.approx(0.28),
    }


@pytest.mark.parametrize("decision_label", ["not_done", "postponed", "app_ignored"])
def test_simple_construct_update_decreases_after_unsuccessful_pa(decision_label: str) -> None:
    from run_llm_pa_decision import update_psychological_constructs_simple

    updated = update_psychological_constructs_simple(
        {"automaticity": 0.50, "motivation": 0.20, "pressure_tension": 0.30}, decision_label
    )

    assert updated == {
        "automaticity": pytest.approx(0.48),
        "motivation": pytest.approx(0.18),
        "pressure_tension": pytest.approx(0.32),
    }


def test_simple_construct_update_clamps_values_to_unit_interval() -> None:
    from run_llm_pa_decision import update_psychological_constructs_simple

    increased = update_psychological_constructs_simple(
        {"high": 0.99, "pressure_tension": 0.01}, "done_as_planned"
    )
    decreased = update_psychological_constructs_simple(
        {"low": 0.01, "pressure_tension": 0.99}, "not_done"
    )

    assert increased == {"high": 1.0, "pressure_tension": 0.0}
    assert decreased == {"low": 0.0, "pressure_tension": 1.0}


@pytest.mark.parametrize("decision_label", ["done_as_planned", "not_done"])
def test_planned_activity_next_day_has_required_fields(decision_label: str) -> None:
    from run_llm_pa_decision import generate_planned_activity_next_day

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
    from run_llm_pa_decision import DAILY_DECISION_LOG_COLUMNS, write_daily_decision_log_row

    log_path = tmp_path / "llm_pa_decision_daily_log.csv"
    planned_activity_next_day = {
        "activity_type": "indoor_activity",
        "duration_min": 20,
        "intensity": "moderate",
        "preferred_time_window": [17, 20],
        "description": "20 Minuten intensive Oberkörpereinheit im Gym",
    }

    write_daily_decision_log_row(
        log_path=log_path,
        persona_id="ScenarioPersona_01_favourable_pa_context",
        day_index=21,
        pa_decision=_valid_decision(),
        activity_done=True,
        planned_activity_for_day={"activity_type": "outdoor_activity"},
        planned_activity_next_day=planned_activity_next_day,
        behavior_policy=BEHAVIOR_POLICY,
        previous_psychological_constructs={"automaticity": 0.5},
        updated_psychological_constructs={"automaticity": 0.52},
    )

    with log_path.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 1
    assert tuple(rows[0].keys()) == DAILY_DECISION_LOG_COLUMNS
    assert rows[0]["persona_id"] == "ScenarioPersona_01_favourable_pa_context"
    assert rows[0]["day_index"] == "21"
    assert rows[0]["decision_label"] == "done_as_planned"
    assert rows[0]["activity_done"] == "True"
    assert json.loads(rows[0]["planned_activity_next_day"]) == planned_activity_next_day
    assert json.loads(rows[0]["behavior_policy"]) == BEHAVIOR_POLICY
    assert json.loads(rows[0]["previous_psychological_constructs"]) == {"automaticity": 0.5}
    assert json.loads(rows[0]["updated_psychological_constructs"]) == {"automaticity": 0.52}


def test_run_pipeline_for_context_record_contains_closed_loop_update(tmp_path: Path) -> None:
    from run_llm_pa_decision import run_pipeline_for_context

    def fake_behavior_runner(agent_context, **kwargs):
        return {"probabilities": dict(BEHAVIOR_POLICY)}

    def fake_pa_decision_runner(pa_decision_input, **kwargs):
        return _valid_decision()

    record = run_pipeline_for_context(
        _agent_context(),
        behavior_system_prompt="behavior prompt",
        pa_decision_system_prompt="pa prompt",
        output_dir=tmp_path,
        behavior_runner=fake_behavior_runner,
        pa_decision_runner=fake_pa_decision_runner,
    )

    assert "closed_loop_update" in record
    assert record["closed_loop_update"]["activity_done"] is True
    assert record["closed_loop_update"]["previous_psychological_constructs"] == {
        "automaticity": 0.5
    }
    assert record["closed_loop_update"]["updated_psychological_constructs"] == {
        "automaticity": pytest.approx(0.52)
    }
    assert set(record["closed_loop_update"]["planned_activity_next_day"]) == {
        "activity_type",
        "duration_min",
        "intensity",
        "preferred_time_window",
        "description",
    }
    assert (tmp_path / "llm_pa_decision_daily_log.csv").exists()
