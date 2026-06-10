from __future__ import annotations

import copy
import importlib
import json
from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from psychological_state import DEFAULT_PSYCHOLOGICAL_STATE


def test_run_llm_pa_decision_importable_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("UNI_LLM_API_KEY", raising=False)
    module = importlib.import_module("run_llm_pa_decision")
    importlib.reload(module)

    assert module.DECISION_CODEBOOK[0] == "not_completed"


def test_decision_codebook_contains_exact_codes() -> None:
    from run_llm_pa_decision import DECISION_CODEBOOK

    assert DECISION_CODEBOOK == {
        0: "not_completed",
        1: "completed_as_planned",
        2: "postponed",
        3: "adapted_completed",
        4: "extra_movement",
        5: "app_ignored",
    }


def _valid_decision() -> dict:
    return {
        "decision_code": 1,
        "decision_label": "completed_as_planned",
        "diary_entry": "Ich habe mich heute wie geplant etwas bewegt.",
        "rationale_short": "Es gab passende freie Zeit und keine starken Barrieren.",
        "main_context_factors": ["freie Zeit", "mittlere Energie"],
    }


def test_valid_decision_json_is_accepted() -> None:
    from run_llm_pa_decision import parse_and_validate_llm_decision

    payload = _valid_decision()

    assert parse_and_validate_llm_decision(json.dumps(payload)) == payload


@pytest.mark.parametrize("bad_code", [-1, 6, "1", True])
def test_invalid_decision_code_is_rejected(bad_code) -> None:
    from run_llm_pa_decision import validate_llm_decision_payload

    payload = _valid_decision()
    payload["decision_code"] = bad_code

    with pytest.raises(ValueError):
        validate_llm_decision_payload(payload)


def test_wrong_decision_label_for_code_is_rejected() -> None:
    from run_llm_pa_decision import validate_llm_decision_payload

    payload = _valid_decision()
    payload["decision_label"] = "not_completed"

    with pytest.raises(ValueError):
        validate_llm_decision_payload(payload)


def test_missing_fields_are_rejected() -> None:
    from run_llm_pa_decision import validate_llm_decision_payload

    payload = _valid_decision()
    payload.pop("diary_entry")

    with pytest.raises(ValueError):
        validate_llm_decision_payload(payload)


def test_extra_fields_are_rejected() -> None:
    from run_llm_pa_decision import validate_llm_decision_payload

    payload = _valid_decision()
    payload["action_plan"] = "not allowed"

    with pytest.raises(ValueError):
        validate_llm_decision_payload(payload)


def test_invalid_json_is_rejected() -> None:
    from run_llm_pa_decision import parse_llm_decision_json

    with pytest.raises(ValueError):
        parse_llm_decision_json("not json")


@pytest.mark.parametrize("bad_factors", ["free time", ["free time", 1], ["free time", None]])
def test_main_context_factors_must_be_list_of_strings(bad_factors) -> None:
    from run_llm_pa_decision import validate_llm_decision_payload

    payload = _valid_decision()
    payload["main_context_factors"] = bad_factors

    with pytest.raises(ValueError):
        validate_llm_decision_payload(payload)


def test_prepare_agent_context_for_llm_removes_legacy_fields_and_adds_psychological_state() -> None:
    from run_llm_pa_decision import prepare_agent_context_for_llm

    source = {
        "persona_id": "legacy_agent",
        "input_parameters": {"fitness_hours_week": 4},
        "selected_schedule_parameters": {"sport_frequency": 0.3},
        "action_plan": {"legacy": True},
        "hourly_context_24h": [],
    }
    original = copy.deepcopy(source)

    prepared = prepare_agent_context_for_llm(source)

    assert source == original
    assert "input_parameters" not in prepared
    assert "selected_schedule_parameters" not in prepared
    assert "action_plan" not in prepared
    assert prepared["psychological_state"] == DEFAULT_PSYCHOLOGICAL_STATE


def test_prepare_agent_context_for_llm_preserves_existing_psychological_state() -> None:
    from run_llm_pa_decision import prepare_agent_context_for_llm

    custom_state = {
        "source": "custom",
        "n": 1,
        "values_normalized": {"automaticity": 0.1},
        "raw_scale_means": {"automaticity": 1.6},
    }
    source = {
        "persona_id": "current_agent",
        "psychological_state": custom_state,
        "input_parameters": {"fitness_hours_week": 4},
    }

    prepared = prepare_agent_context_for_llm(source)

    assert prepared["psychological_state"] == custom_state
    assert prepared["psychological_state"] is not custom_state
    assert source["psychological_state"] == custom_state
