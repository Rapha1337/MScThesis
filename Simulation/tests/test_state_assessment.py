from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

SIMULATION_DIR = Path(__file__).resolve().parents[1]
if str(SIMULATION_DIR) not in sys.path:
    sys.path.append(str(SIMULATION_DIR))

import state_assessment
from psychological_state import BACKEND_CONSTRUCT_RANGES
from state_assessment import (
    ACTIVE_CONSTRUCTS,
    apply_smoothed_bounded_construct_update,
    CONSTRUCT_ITEM_COUNTS,
    build_dry_run_state_assessment,
    load_state_assessment_prompt,
    normalize_mean_scores,
    render_state_assessment_prompt,
    run_state_assessment,
    validate_state_assessment_output,
)


def _previous_values() -> dict[str, float]:
    return {construct: 0.5 for construct in ACTIVE_CONSTRUCTS}


def _valid_payload() -> dict:
    return build_dry_run_state_assessment(
        persona_id="Persona_01",
        day_index=2,
        previous_normalized_values=_previous_values(),
    )


def test_prompt_loads_and_contains_only_allowed_assessment_context() -> None:
    prompt = load_state_assessment_prompt()
    assert "Leere `items`-Arrays" in prompt
    assert "keine gültige finale Ausgabe" in prompt
    assert "Python `json.loads`" in prompt
    assert "nachgestellten Kommas" in prompt
    assert "doppelten Anführungszeichen" in prompt
    assert "maximal 8 Wörter" in prompt
    rendered = render_state_assessment_prompt(
        prompt,
        persona_id="Persona_01",
        day_index=2,
        previous_psychological_construct_values=_previous_values(),
        current_simulated_diary_entry="I went for a short walk.",
        previous_diary_entries=[{"day_index": 0, "diary_entry": "Earlier entry"}],
        previous_diary_entries_summary=None,
    )
    assert "{recommendation_data}" not in prompt
    assert "{recommendation_data}" not in rendered
    assert "Earlier entry" in rendered
    assert "I went for a short walk." in rendered
    assert all("{" + key + "}" not in rendered for key in (
        "persona_id",
        "day_index",
        "previous_psychological_construct_values",
        "current_simulated_diary_entry",
        "previous_diary_entries",
        "previous_diary_entries_summary",
    ))
    assert state_assessment.REQUIRED_PROMPT_PLACEHOLDERS == (
        "persona_id",
        "day_index",
        "previous_psychological_construct_values",
        "current_simulated_diary_entry",
        "previous_diary_entries",
        "previous_diary_entries_summary",
    )
    for forbidden_placeholder in (
        "{current_day_context}",
        "{planned_physical_activity}",
        "{physical_activity_decision}",
        "{decision_rationale}",
    ):
        assert forbidden_placeholder not in prompt


def test_rendered_prompt_excludes_decision_context_and_sampling_metadata() -> None:
    prompt = load_state_assessment_prompt()
    rendered = render_state_assessment_prompt(
        prompt,
        persona_id="Persona_01",
        day_index=2,
        previous_psychological_construct_values=_previous_values(),
        current_simulated_diary_entry="Today I rested.",
        previous_diary_entries=[],
        previous_diary_entries_summary=None,
    )
    forbidden_values = (
        "behavior_policy",
        "active_decision_probabilities",
        "sampled_decision_label",
        "sampled_decision_probability",
        "decision rationale",
        "planned physical activity",
        "current day context",
    )
    assert all(value not in rendered.lower() for value in forbidden_values)


def test_prompt_requires_direct_evidence_and_does_not_minimize_no_pa_days() -> None:
    prompt = load_state_assessment_prompt()
    assert "Keine PA heute ≠ niedrige Intention" in prompt
    assert "Ein Tag ohne PA ist für sich allein kein Beleg für niedrige Werte" in prompt
    assert "direkte, konstruktspezifische Tagebuchevidenz erforderlich" in prompt


def test_validation_accepts_exactly_nine_constructs_and_recomputes_means() -> None:
    payload = _valid_payload()
    payload["item_scores"]["automaticity"]["mean_score"] = 7
    payload["item_scores"]["automaticity"]["items"][0]["score"] = 1
    payload["item_scores"]["automaticity"]["items"][1]["score"] = 3
    payload["item_scores"]["automaticity"]["items"][2]["score"] = None
    payload["item_scores"]["automaticity"]["items"][3]["score"] = 5

    validated = validate_state_assessment_output(
        payload,
        expected_persona_id="Persona_01",
        expected_day_index=2,
    )

    assert set(validated["item_scores"]) == set(ACTIVE_CONSTRUCTS)
    assert validated["mean_scores_raw"]["automaticity"] == pytest.approx(3)


@pytest.mark.parametrize("mutation", ["missing", "extra"])
def test_validation_rejects_construct_key_mismatches(mutation: str) -> None:
    payload = _valid_payload()
    if mutation == "missing":
        del payload["item_scores"]["automaticity"]
    else:
        payload["item_scores"]["unexpected_construct"] = {"items": [], "mean_score": None}
    with pytest.raises(ValueError, match="construct keys mismatch"):
        validate_state_assessment_output(
            payload,
            expected_persona_id="Persona_01",
            expected_day_index=2,
        )


@pytest.mark.parametrize(
    "removed_key",
    ["interest_enjoyment", "perceived_competence", "perceived_choice", "pressure_tension"],
)
def test_validation_rejects_removed_constructs(removed_key: str) -> None:
    payload = _valid_payload()
    payload["item_scores"][removed_key] = {"items": [], "mean_score": None}
    with pytest.raises(ValueError, match="removed construct"):
        validate_state_assessment_output(
            payload,
            expected_persona_id="Persona_01",
            expected_day_index=2,
        )


def test_validation_allows_null_items_and_null_mean_keeps_previous_value() -> None:
    payload = _valid_payload()
    for item in payload["item_scores"]["automaticity"]["items"]:
        item["score"] = None
    validated = validate_state_assessment_output(
        payload,
        expected_persona_id="Persona_01",
        expected_day_index=2,
    )
    normalized = normalize_mean_scores(validated["mean_scores_raw"], _previous_values())
    assert validated["mean_scores_raw"]["automaticity"] is None
    assert normalized["automaticity"] == 0.5


def test_validation_caps_out_of_range_scores_and_accepts_intrinsic_zero() -> None:
    payload = _valid_payload()
    for item in payload["item_scores"]["intrinsic_motivation"]["items"]:
        item["score"] = 0
    validated = validate_state_assessment_output(
        payload,
        expected_persona_id="Persona_01",
        expected_day_index=2,
    )
    assert validated["mean_scores_raw"]["intrinsic_motivation"] == 0

    payload = _valid_payload()
    payload["item_scores"]["automaticity"]["items"][0]["score"] = 8.0
    payload["item_scores"]["automaticity"]["items"][1]["score"] = 0.0
    payload["item_scores"]["intrinsic_motivation"]["items"][0]["score"] = -1.0
    payload["item_scores"]["pa_specific_self_control"]["items"][0]["score"] = 6.0
    validated = validate_state_assessment_output(
        payload,
        expected_persona_id="Persona_01",
        expected_day_index=2,
    )
    assert validated["item_scores"]["automaticity"]["items"][0]["score"] == 7.0
    assert validated["item_scores"]["automaticity"]["items"][1]["score"] == 1.0
    assert validated["item_scores"]["intrinsic_motivation"]["items"][0]["score"] == 0.0
    assert (
        validated["item_scores"]["pa_specific_self_control"]["items"][0]["score"] == 5.0
    )


def test_validation_keeps_null_scores_and_rejects_non_numeric_scores() -> None:
    payload = _valid_payload()
    payload["item_scores"]["automaticity"]["items"][0]["score"] = None
    validated = validate_state_assessment_output(
        payload,
        expected_persona_id="Persona_01",
        expected_day_index=2,
    )
    assert validated["item_scores"]["automaticity"]["items"][0]["score"] is None

    payload = _valid_payload()
    payload["item_scores"]["automaticity"]["items"][0]["score"] = "6"
    with pytest.raises(ValueError, match="must be numeric or null"):
        validate_state_assessment_output(
            payload,
            expected_persona_id="Persona_01",
            expected_day_index=2,
        )


def test_capped_scores_are_used_for_recomputed_means_and_normalization() -> None:
    payload = _valid_payload()
    self_control = payload["item_scores"]["pa_specific_self_control"]
    self_control["mean_score"] = 99
    for item, score in zip(self_control["items"], [6.0, 0.0, 3.0]):
        item["score"] = score

    validated = validate_state_assessment_output(
        payload,
        expected_persona_id="Persona_01",
        expected_day_index=2,
    )
    normalized = normalize_mean_scores(validated["mean_scores_raw"], _previous_values())

    assert validated["mean_scores_raw"]["pa_specific_self_control"] == pytest.approx(3.0)
    assert validated["item_scores"]["pa_specific_self_control"]["mean_score"] == pytest.approx(
        3.0
    )
    assert normalized["pa_specific_self_control"] == pytest.approx(0.5)


def test_normalization_uses_each_construct_range() -> None:
    raw_midpoints = {
        construct: (low + high) / 2
        for construct, (low, high) in BACKEND_CONSTRUCT_RANGES.items()
    }
    normalized = normalize_mean_scores(raw_midpoints, _previous_values())
    assert normalized == pytest.approx({construct: 0.5 for construct in ACTIVE_CONSTRUCTS})


def test_dry_run_assessment_keeps_state_and_records_previous_context() -> None:
    previous_entries = [
        {"day_index": 0, "diary_entry": "first"},
        {"day_index": 1, "diary_entry": "second"},
    ]
    result = run_state_assessment(
        persona_id="Persona_01",
        day_index=2,
        previous_normalized_values=_previous_values(),
        current_simulated_diary_entry="current",
        previous_diary_entries=previous_entries,
        dry_run=True,
    )
    assert result["state_assessment_mode"] == "dry_run_mock"
    assert result["psychological_construct_values_after_state_assessment"] == pytest.approx(
        _previous_values()
    )
    assert result["previous_diary_entries_count"] == 2
    assert [entry["day_index"] for entry in result["previous_diary_entries_context_used"]] == [0, 1]
    assert "current" not in json.dumps(result["previous_diary_entries_context_used"])


def test_item_counts_match_required_schema() -> None:
    payload = _valid_payload()
    for construct, expected_count in CONSTRUCT_ITEM_COUNTS.items():
        assert len(payload["item_scores"][construct]["items"]) == expected_count


def test_smoothed_bounded_update_handles_null_zero_direction_bounds_and_clipping() -> None:
    previous = _previous_values()
    targets = dict(previous)
    raw_targets: dict[str, float | None] = {key: 4.0 for key in ACTIVE_CONSTRUCTS}
    targets.update(
        {
            "automaticity": 0.0,
            "pa_specific_self_control": 1.0,
            "action_planning": 0.0,
            "intention": 1.0,
        }
    )
    raw_targets["automaticity"] = 1.0
    raw_targets["pa_specific_self_control"] = 7.0
    raw_targets["action_planning"] = None
    previous["intention"] = 0.99

    result = apply_smoothed_bounded_construct_update(previous, targets, raw_targets)

    assert result["updated_values"]["automaticity"] == pytest.approx(0.4)
    assert result["updated_values"]["pa_specific_self_control"] == pytest.approx(0.6)
    assert result["updated_values"]["action_planning"] == pytest.approx(0.5)
    assert result["updated_values"]["intention"] == pytest.approx(0.992)
    assert max(abs(delta) for delta in result["delta_applied"].values()) <= 0.10
    assert all(0.0 <= value <= 1.0 for value in result["updated_values"].values())


def test_state_assessment_logs_direct_targets_and_smoothed_values() -> None:
    result = run_state_assessment(
        persona_id="Persona_01",
        day_index=0,
        previous_normalized_values=_previous_values(),
        current_simulated_diary_entry="No activity today.",
        previous_diary_entries=[],
        dry_run=True,
    )
    assert result["psychological_construct_update_strategy"] == "smoothed_bounded"
    assert result["psychological_construct_update_alpha"] == pytest.approx(0.20)
    assert result["psychological_construct_update_max_daily_change"] == pytest.approx(0.10)
    assert result["state_assessment_target_values_normalized"] == pytest.approx(
        _previous_values()
    )
    assert result["psychological_construct_values_after_smoothed_update"] == pytest.approx(
        _previous_values()
    )


def _run_real_assessment(tmp_path: Path) -> dict:
    return run_state_assessment(
        persona_id="Persona_01",
        day_index=2,
        previous_normalized_values=_previous_values(),
        current_simulated_diary_entry="current",
        previous_diary_entries=[],
        output_dir=tmp_path,
        max_tokens=10000,
    )


@pytest.mark.parametrize("json_mode", [False, True])
def test_state_assessment_response_format_is_explicitly_opt_in(
    monkeypatch: pytest.MonkeyPatch, json_mode: bool
) -> None:
    captured: dict = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            choice = type(
                "Choice",
                (),
                {
                    "message": type("Message", (), {"content": json.dumps(_valid_payload())})(),
                    "finish_reason": "stop",
                },
            )()
            return type("Response", (), {"choices": [choice], "usage": None})()

    fake_client = type(
        "Client",
        (),
        {"chat": type("Chat", (), {"completions": FakeCompletions()})()},
    )()
    monkeypatch.setattr(state_assessment, "_get_client", lambda: fake_client)

    state_assessment.call_state_assessment_llm("prompt", json_mode=json_mode)

    if json_mode:
        assert captured["response_format"] == {"type": "json_object"}
    else:
        assert "response_format" not in captured


def test_malformed_json_is_saved_with_metadata_and_retried_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    valid_raw = json.dumps(_valid_payload())
    responses = iter(
        [
            {
                "raw_response": '{"persona_id": "Persona_01", bad: true}',
                "finish_reason": "stop",
                "resource_usage": {},
            },
            {
                "raw_response": valid_raw,
                "finish_reason": "stop",
                "resource_usage": {},
            },
        ]
    )
    calls: list[dict] = []

    def fake_call(*args, **kwargs):
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(state_assessment, "call_state_assessment_llm", fake_call)
    result = _run_real_assessment(tmp_path)

    assert result["state_assessment_mode"] == "llm"
    assert len(calls) == 2
    assert calls[0]["max_tokens"] == 10000
    assert calls[0]["repair_instruction"] is None
    assert calls[0]["json_mode"] is False
    assert calls[1]["max_tokens"] == 12000
    assert calls[1]["repair_instruction"] == state_assessment.JSON_REPAIR_INSTRUCTION
    assert calls[1]["json_mode"] is False
    raw_path = tmp_path / "state_assessment_Persona_01_raw_invalid.txt"
    metadata_path = tmp_path / "state_assessment_Persona_01_parse_error.json"
    assert raw_path.read_text(encoding="utf-8").endswith("bad: true}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["persona_id"] == "Persona_01"
    assert metadata["day_index"] == 2
    assert metadata["line_number"] == 1
    assert metadata["column_number"] > 0
    assert metadata["character_position"] > 0
    assert metadata["finish_reason"] == "stop"
    assert metadata["response_length"] == len(raw_path.read_text(encoding="utf-8"))
    assert metadata["state_assessment_max_tokens"] == 10000
    assert metadata["model_name"] == "gpt-oss-120b"
    assert metadata["raw_invalid_output_path"] == str(raw_path)


def test_second_malformed_json_is_saved_and_raised_without_third_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    def fake_call(*args, **kwargs):
        nonlocal calls
        calls += 1
        return {
            "raw_response": "{invalid,}",
            "finish_reason": "length",
            "resource_usage": {},
        }

    monkeypatch.setattr(state_assessment, "call_state_assessment_llm", fake_call)
    with pytest.raises(ValueError, match="not valid JSON"):
        _run_real_assessment(tmp_path)

    assert calls == 2
    assert (tmp_path / "state_assessment_Persona_01_raw_invalid.txt").exists()
    assert (tmp_path / "state_assessment_Persona_01_parse_error.json").exists()
    assert (tmp_path / "state_assessment_Persona_01_retry_raw_invalid.txt").exists()
    retry_metadata = json.loads(
        (tmp_path / "state_assessment_Persona_01_retry_parse_error.json").read_text(
            encoding="utf-8"
        )
    )
    assert retry_metadata["state_assessment_max_tokens"] == 12000


def test_retry_uses_configured_json_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    responses = iter(
        [
            {"raw_response": "{invalid}", "finish_reason": "stop", "resource_usage": {}},
            {
                "raw_response": json.dumps(_valid_payload()),
                "finish_reason": "stop",
                "resource_usage": {},
            },
        ]
    )
    calls: list[dict] = []

    def fake_call(*args, **kwargs):
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(state_assessment, "call_state_assessment_llm", fake_call)
    _run_real_assessment_with_json_mode(tmp_path)

    assert [call["json_mode"] for call in calls] == [True, True]


def _run_real_assessment_with_json_mode(tmp_path: Path) -> dict:
    return run_state_assessment(
        persona_id="Persona_01",
        day_index=2,
        previous_normalized_values=_previous_values(),
        current_simulated_diary_entry="current",
        previous_diary_entries=[],
        output_dir=tmp_path,
        max_tokens=10000,
        json_mode=True,
    )
