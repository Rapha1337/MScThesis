from __future__ import annotations

import importlib
import json
import math
from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))


def test_run_behavior_probability_estimation_importable_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("UNI_LLM_API_KEY", raising=False)
    module = importlib.import_module("run_behavior_probability_estimation")
    importlib.reload(module)

    assert module.BEHAVIOR_PROBABILITY_KEYS == (
        "do_planned_activity",
        "adapt_activity",
        "skip_activity",
        "extra_activity",
        "app_ignored",
    )


def _valid_payload() -> dict:
    return {
        "probabilities": {
            "do_planned_activity": 0.25,
            "adapt_activity": 0.30,
            "skip_activity": 0.20,
            "extra_activity": 0.10,
            "app_ignored": 0.15,
        }
    }


def _extract_prompt_input_json(prompt: str) -> dict:
    input_marker = "INPUT:\n"
    important_marker = "\n\nIMPORTANT:"
    assert input_marker in prompt
    assert important_marker in prompt
    input_json = prompt.split(input_marker, 1)[1].split(important_marker, 1)[0]
    return json.loads(input_json)


def test_behavior_probability_user_prompt_only_sends_psychological_construct_values() -> None:
    from psychological_state import DEFAULT_PSYCHOLOGICAL_STATE
    from run_behavior_probability_estimation import build_behavior_probability_user_prompt

    agent_context = {
        "persona_id": "persona_should_not_be_sent",
        "scenario": "favourable_pa_context",
        "seed": 12345,
        "daily_context": {"label": "negative_pa_context"},
        "hourly_context_24h": [{"label": "busy_day_context"}],
        "accessibility": "high",
        "weather": "sunny",
        "schedule": {"busy": False},
        "activity_suggestion": "walk",
        "psychological_state": DEFAULT_PSYCHOLOGICAL_STATE,
    }

    prompt = build_behavior_probability_user_prompt(agent_context)
    prompt_payload = _extract_prompt_input_json(prompt)
    expected_constructs = set(DEFAULT_PSYCHOLOGICAL_STATE["values_normalized"])

    assert prompt_payload == {
        "psychological_construct_values_normalized": DEFAULT_PSYCHOLOGICAL_STATE[
            "values_normalized"
        ]
    }
    assert set(prompt_payload["psychological_construct_values_normalized"]) == expected_constructs
    assert "psychological_construct_values_normalized" in prompt
    assert "Base the probability estimate only on psychological_construct_values_normalized" in prompt
    assert "persona_id" not in prompt
    assert "persona_should_not_be_sent" not in prompt
    assert '"scenario"' not in prompt
    assert "seed" not in prompt
    assert "favourable_pa_context" not in prompt
    assert "negative_pa_context" not in prompt
    assert "busy_day_context" not in prompt
    assert "daily_context" not in prompt
    assert "hourly_context_24h" not in prompt
    assert "accessibility" not in prompt
    assert "weather" not in prompt
    assert "schedule" not in prompt
    assert "activity_suggestion" not in prompt


def test_exact_sum_one_payload_accepted_unchanged() -> None:
    from run_behavior_probability_estimation import validate_behavior_probability_payload

    payload = _valid_payload()

    assert validate_behavior_probability_payload(payload) == payload


def test_missing_top_level_key_rejected() -> None:
    from run_behavior_probability_estimation import validate_behavior_probability_payload

    with pytest.raises(ValueError, match="Missing"):
        validate_behavior_probability_payload({})


def test_extra_top_level_key_rejected() -> None:
    from run_behavior_probability_estimation import validate_behavior_probability_payload

    payload = _valid_payload()
    payload["rationale"] = "not allowed"

    with pytest.raises(ValueError, match="extra"):
        validate_behavior_probability_payload(payload)


def test_missing_probability_key_rejected() -> None:
    from run_behavior_probability_estimation import validate_behavior_probability_payload

    payload = _valid_payload()
    payload["probabilities"].pop("app_ignored")

    with pytest.raises(ValueError, match="Missing"):
        validate_behavior_probability_payload(payload)


@pytest.mark.parametrize("extra_key", ["not_a_probability", "postpone_activity"])
def test_extra_probability_key_rejected(extra_key: str) -> None:
    from run_behavior_probability_estimation import validate_behavior_probability_payload

    payload = _valid_payload()
    payload["probabilities"][extra_key] = 0.0

    with pytest.raises(ValueError, match="extra"):
        validate_behavior_probability_payload(payload)


@pytest.mark.parametrize("bad_value", ["0.1", None, [0.1], {"value": 0.1}])
def test_non_numeric_probability_rejected(bad_value) -> None:
    from run_behavior_probability_estimation import validate_behavior_probability_payload

    payload = _valid_payload()
    payload["probabilities"]["do_planned_activity"] = bad_value

    with pytest.raises(ValueError, match="numeric"):
        validate_behavior_probability_payload(payload)


def test_boolean_probability_rejected() -> None:
    from run_behavior_probability_estimation import validate_behavior_probability_payload

    payload = _valid_payload()
    payload["probabilities"]["do_planned_activity"] = True

    with pytest.raises(ValueError, match="numeric"):
        validate_behavior_probability_payload(payload)


@pytest.mark.parametrize("bad_value", [-0.01, 1.01])
def test_out_of_range_probability_rejected(bad_value: float) -> None:
    from run_behavior_probability_estimation import validate_behavior_probability_payload

    payload = _valid_payload()
    payload["probabilities"]["do_planned_activity"] = bad_value

    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        validate_behavior_probability_payload(payload)


@pytest.mark.parametrize("bad_value", [math.inf, -math.inf, math.nan])
def test_non_finite_probability_rejected(bad_value: float) -> None:
    from run_behavior_probability_estimation import validate_behavior_probability_payload

    payload = _valid_payload()
    payload["probabilities"]["do_planned_activity"] = bad_value

    with pytest.raises(ValueError, match="finite"):
        validate_behavior_probability_payload(payload)


@pytest.mark.parametrize("target_sum", [0.98, 1.02])
def test_near_valid_probability_sum_accepted_and_normalized(target_sum: float) -> None:
    from run_behavior_probability_estimation import (
        BEHAVIOR_PROBABILITY_KEYS,
        validate_behavior_probability_payload,
    )

    payload = _valid_payload()
    scale_factor = target_sum / sum(payload["probabilities"].values())
    payload["probabilities"] = {
        key: value * scale_factor for key, value in payload["probabilities"].items()
    }

    validated = validate_behavior_probability_payload(payload)

    assert sum(validated["probabilities"].values()) == pytest.approx(1.0)
    for key in BEHAVIOR_PROBABILITY_KEYS:
        assert validated["probabilities"][key] == pytest.approx(
            payload["probabilities"][key] / target_sum
        )


@pytest.mark.parametrize("target_sum", [0.50, 1.50])
def test_probability_sum_outside_normalization_range_rejected(target_sum: float) -> None:
    from run_behavior_probability_estimation import validate_behavior_probability_payload

    payload = _valid_payload()
    scale_factor = target_sum / sum(payload["probabilities"].values())
    payload["probabilities"] = {
        key: value * scale_factor for key, value in payload["probabilities"].items()
    }

    with pytest.raises(ValueError, match="normalization range"):
        validate_behavior_probability_payload(payload)


def test_json_parse_error_rejected() -> None:
    from run_behavior_probability_estimation import parse_behavior_probability_json

    with pytest.raises(ValueError, match="not valid JSON"):
        parse_behavior_probability_json("not json")


def test_parse_and_validate_behavior_probabilities_accepts_valid_json() -> None:
    from run_behavior_probability_estimation import parse_and_validate_behavior_probabilities

    payload = _valid_payload()

    assert parse_and_validate_behavior_probabilities(json.dumps(payload)) == payload


class _FakeMessage:
    def __init__(self, **fields):
        self._fields = fields
        for key, value in fields.items():
            setattr(self, key, value)

    def model_dump(self) -> dict:
        return dict(self._fields)


class _FakeChoice:
    def __init__(self, message: _FakeMessage, finish_reason: str = "stop"):
        self.message = message
        self.finish_reason = finish_reason

    def model_dump(self) -> dict:
        return {
            "finish_reason": self.finish_reason,
            "message": self.message.model_dump(),
        }


class _FakeResponse:
    usage = {"completion_tokens": 1, "prompt_tokens": 1, "total_tokens": 2}

    def __init__(self, message: _FakeMessage, finish_reason: str = "stop"):
        self.choices = [_FakeChoice(message, finish_reason=finish_reason)]

    def model_dump(self) -> dict:
        return {
            "choices": [choice.model_dump() for choice in self.choices],
            "usage": self.usage,
        }


def test_extract_llm_message_content_uses_normal_content(tmp_path) -> None:
    from run_behavior_probability_estimation import extract_llm_message_content

    payload = _valid_payload()
    response = _FakeResponse(_FakeMessage(content=json.dumps(payload)))

    extracted = extract_llm_message_content(response, persona_id="normal", output_dir=tmp_path)

    assert extracted == json.dumps(payload)
    assert not (tmp_path / "llm_behavior_probability_normal_empty_response_debug.json").exists()


def test_extract_llm_message_content_recovers_valid_parsed_schema(tmp_path) -> None:
    from run_behavior_probability_estimation import parse_and_validate_behavior_probabilities
    from run_behavior_probability_estimation import extract_llm_message_content

    response = _FakeResponse(_FakeMessage(content="", parsed=_valid_payload()))

    extracted = extract_llm_message_content(response, persona_id="parsed", output_dir=tmp_path)

    assert parse_and_validate_behavior_probabilities(extracted) == _valid_payload()
    assert (tmp_path / "llm_behavior_probability_parsed_empty_response_debug.json").exists()


def test_extract_llm_message_content_empty_raises_helpful_error_and_saves_debug(tmp_path) -> None:
    from run_behavior_probability_estimation import extract_llm_message_content

    response = _FakeResponse(_FakeMessage(content=None, refusal=None), finish_reason="stop")

    with pytest.raises(RuntimeError, match="finish_reason='stop'.*Debug response saved"):
        extract_llm_message_content(response, persona_id="empty/persona", output_dir=tmp_path)

    debug_path = tmp_path / "llm_behavior_probability_empty_persona_empty_response_debug.json"
    assert debug_path.exists()
    debug_payload = json.loads(debug_path.read_text(encoding="utf-8"))
    assert debug_payload["choices"][0]["finish_reason"] == "stop"
    assert debug_payload["choices"][0]["message"]["content"] is None


def test_extract_llm_message_content_length_finish_reason_suggests_max_tokens(tmp_path) -> None:
    from run_behavior_probability_estimation import extract_llm_message_content

    response = _FakeResponse(_FakeMessage(content=""), finish_reason="length")

    with pytest.raises(RuntimeError, match="Increase --max-tokens or shorten the prompt"):
        extract_llm_message_content(response, persona_id="too_long", output_dir=tmp_path)


def test_extract_llm_message_content_does_not_use_reasoning_as_output(tmp_path) -> None:
    from run_behavior_probability_estimation import extract_llm_message_content

    response = _FakeResponse(
        _FakeMessage(content="", reasoning_content=json.dumps(_valid_payload())),
        finish_reason="stop",
    )

    with pytest.raises(RuntimeError, match="keine sichtbare JSON-Antwort"):
        extract_llm_message_content(response, persona_id="reasoning", output_dir=tmp_path)
