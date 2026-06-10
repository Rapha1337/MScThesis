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
        "postpone_activity",
        "skip_activity",
        "extra_activity",
        "app_ignored",
    )


def _valid_payload() -> dict:
    return {
        "probabilities": {
            "do_planned_activity": 0.25,
            "adapt_activity": 0.20,
            "postpone_activity": 0.15,
            "skip_activity": 0.15,
            "extra_activity": 0.10,
            "app_ignored": 0.15,
        }
    }


def test_valid_payload_accepted() -> None:
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


def test_extra_probability_key_rejected() -> None:
    from run_behavior_probability_estimation import validate_behavior_probability_payload

    payload = _valid_payload()
    payload["probabilities"]["not_a_probability"] = 0.0

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


def test_probability_sum_not_equal_to_one_rejected() -> None:
    from run_behavior_probability_estimation import validate_behavior_probability_payload

    payload = _valid_payload()
    payload["probabilities"]["do_planned_activity"] = 0.24

    with pytest.raises(ValueError, match="sum to 1.0"):
        validate_behavior_probability_payload(payload)


def test_json_parse_error_rejected() -> None:
    from run_behavior_probability_estimation import parse_behavior_probability_json

    with pytest.raises(ValueError, match="not valid JSON"):
        parse_behavior_probability_json("not json")


def test_parse_and_validate_behavior_probabilities_accepts_valid_json() -> None:
    from run_behavior_probability_estimation import parse_and_validate_behavior_probabilities

    payload = _valid_payload()

    assert parse_and_validate_behavior_probabilities(json.dumps(payload)) == payload
