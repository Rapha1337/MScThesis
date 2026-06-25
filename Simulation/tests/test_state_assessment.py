from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

SIMULATION_DIR = Path(__file__).resolve().parents[1]
if str(SIMULATION_DIR) not in sys.path:
    sys.path.append(str(SIMULATION_DIR))

import state_assessment
from state_assessment import (
    ACTIVE_CONSTRUCTS,
    BACKEND_CONSTRUCT_RANGES,
    CONSTRUCT_ITEM_COUNTS,
    build_dry_run_state_assessment,
    item_assessment_to_smoothed_construct_update,
    load_state_assessment_prompt,
    normalize_construct_scale_score,
    render_state_assessment_prompt,
    run_state_assessment,
    validate_state_assessment_output,
)


def _previous_values(value: float = 0.5) -> dict[str, float]:
    return {construct: value for construct in ACTIVE_CONSTRUCTS}


def _items(construct: str, score: float | None, span: str = "explicit diary evidence") -> list[dict]:
    low, high = BACKEND_CONSTRUCT_RANGES[construct]
    return [
        {
            "question_id": f"{construct}_q{i + 1}",
            "score": score,
            "range": f"{low}-{high}",
            "evidence_spans": [] if score is None else [span],
            "reasoning_short": "" if score is None else "diary explicitly supports this item",
        }
        for i in range(CONSTRUCT_ITEM_COUNTS[construct])
    ]


def _payload(construct: str | None = None, score: float | None = None, span: str = "explicit diary evidence") -> dict:
    payload = build_dry_run_state_assessment(
        persona_id="Persona_01", day_index=2, previous_normalized_values=_previous_values()
    )
    for name in ACTIVE_CONSTRUCTS:
        payload["item_scores"][name] = {"items": _items(name, None, span), "mean_score": None}
    if construct is not None:
        payload["item_scores"][construct] = {
            "items": _items(construct, score, span),
            "mean_score": score,
        }
    return payload


def test_prompt_loads_questionnaire_schema_and_diary_only_policy() -> None:
    prompt = load_state_assessment_prompt()
    assert "item_scores" in prompt
    assert "Use the original response scale for every item" in prompt
    assert "not evidence" in prompt
    rendered = render_state_assessment_prompt(
        prompt,
        persona_id="Persona_01",
        day_index=2,
        previous_psychological_construct_values=_previous_values(),
        current_simulated_diary_entry="I was determined to exercise.",
        previous_diary_entries=[{"day_index": 0, "diary_entry": "Earlier entry"}],
        previous_diary_entries_summary=None,
        current_decision_label="extra_activity",
        was_physical_activity_planned_today=False,
        planned_physical_activity_summary={"activity": "run"},
    )
    assert "I was determined to exercise." in rendered
    assert "Earlier entry" in rendered
    assert all("{" + key + "}" not in rendered for key in state_assessment.REQUIRED_PROMPT_PLACEHOLDERS)


@pytest.mark.parametrize(
    "construct,low,high",
    [(name, *BACKEND_CONSTRUCT_RANGES[name]) for name in ACTIVE_CONSTRUCTS],
)
def test_scale_normalization_uses_original_ranges(construct: str, low: float, high: float) -> None:
    assert normalize_construct_scale_score(construct, low) == pytest.approx(0.0)
    assert normalize_construct_scale_score(construct, high) == pytest.approx(1.0)
    assert normalize_construct_scale_score(construct, (low + high) / 2) == pytest.approx(0.5)
    assert normalize_construct_scale_score(construct, low - 0.01) is None
    assert normalize_construct_scale_score(construct, high + 0.01) is None
    assert normalize_construct_scale_score(construct, None) is None


def test_questionnaire_assessment_is_normalized_then_smoothed() -> None:
    diary = "I was determined to exercise."
    payload = _payload("intention", 5.8, diary)  # [1,7] -> .8
    validated = validate_state_assessment_output(
        payload, expected_persona_id="Persona_01", expected_day_index=2, current_simulated_diary_entry=diary
    )
    update = item_assessment_to_smoothed_construct_update(
        {**_previous_values(), "intention": 0.50}, validated["accepted_item_scores"]
    )
    assert update["scale_means"]["intention"] == pytest.approx(5.8)
    assert update["targets_normalized"]["intention"] == pytest.approx(0.8)
    assert update["delta_proposed"]["intention"] == pytest.approx(0.03)
    assert update["delta_applied"]["intention"] == pytest.approx(0.03)
    assert update["updated_values"]["intention"] == pytest.approx(0.53)
    assert update["details"]["intention"]["raw_llm3_item_or_scale_assessment"]["mean_score"] == pytest.approx(5.8)


def test_null_and_malformed_construct_assessments_keep_previous_value_exactly() -> None:
    diary = "I was determined to exercise."
    payload = _payload("intention", None, diary)
    payload["item_scores"]["action_planning"] = {"items": "bad", "mean_score": 3}
    payload["item_scores"]["subjective_norm"] = {"items": _items("subjective_norm", 9, diary), "mean_score": 9}
    validated = validate_state_assessment_output(
        payload, expected_persona_id="Persona_01", expected_day_index=2, current_simulated_diary_entry=diary
    )
    update = item_assessment_to_smoothed_construct_update(_previous_values(0.63), validated["accepted_item_scores"])
    assert update["updated_values"]["intention"] == pytest.approx(0.63)
    assert update["updated_values"]["action_planning"] == pytest.approx(0.63)
    assert update["updated_values"]["subjective_norm"] == pytest.approx(0.63)
    assert update["targets_normalized"]["action_planning"] is None
    assert validated["rejected_item_scores"]["action_planning"]


def test_maximum_daily_bounds_are_applied_after_proposed_delta() -> None:
    assessment = {construct: {"items": [], "mean_score": None} for construct in ACTIVE_CONSTRUCTS}
    assessment["intention"] = {"items": _items("intention", 7.0, "x"), "mean_score": 7.0}
    update = item_assessment_to_smoothed_construct_update({**_previous_values(), "intention": 0.0}, assessment)
    assert update["targets_normalized"]["intention"] == pytest.approx(1.0)
    assert update["delta_proposed"]["intention"] == pytest.approx(0.10)
    assert update["delta_applied"]["intention"] == pytest.approx(0.05)
    assert update["updated_values"]["intention"] == pytest.approx(0.05)


def test_next_day_state_propagation_uses_updated_values() -> None:
    day0 = {**_previous_values(), "intention": 0.50}
    assessment = {construct: {"items": [], "mean_score": None} for construct in ACTIVE_CONSTRUCTS}
    assessment["intention"] = {"items": _items("intention", 5.8, "x"), "mean_score": 5.8}
    day1 = item_assessment_to_smoothed_construct_update(day0, assessment)["updated_values"]
    day2 = item_assessment_to_smoothed_construct_update(day1, assessment)["updated_values"]
    assert day1["intention"] == pytest.approx(0.53)
    assert day2["intention"] == pytest.approx(0.557)


def test_dry_run_assessment_keeps_state_and_records_schema() -> None:
    result = run_state_assessment(
        persona_id="Persona_01",
        day_index=2,
        previous_normalized_values=_previous_values(),
        current_simulated_diary_entry="current",
        previous_diary_entries=[],
        dry_run=True,
    )
    assert result["state_assessment_mode"] == "dry_run_mock"
    assert result["psychological_construct_values_after_state_assessment"] == pytest.approx(_previous_values())
    assert "state_assessment_raw_item_or_scale_assessment" in result
    assert "state_assessment_construct_scale_means" in result


@pytest.mark.parametrize("json_mode", [False, True])
def test_state_assessment_response_format_is_explicitly_opt_in(monkeypatch: pytest.MonkeyPatch, json_mode: bool) -> None:
    captured: dict = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            choice = type("Choice", (), {"message": type("Message", (), {"content": json.dumps(_payload())})(), "finish_reason": "stop"})()
            return type("Response", (), {"choices": [choice], "usage": None})()

    fake_client = type("Client", (), {"chat": type("Chat", (), {"completions": FakeCompletions()})()})()
    monkeypatch.setattr(state_assessment, "_get_client", lambda: fake_client)
    state_assessment.call_state_assessment_llm("prompt", json_mode=json_mode)
    assert (captured.get("response_format") == {"type": "json_object"}) is json_mode


def test_malformed_json_is_saved_with_metadata_and_retried_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = iter([
        {"raw_response": '{"persona_id": "Persona_01", bad: true}', "finish_reason": "stop", "resource_usage": {}},
        {"raw_response": json.dumps(_payload()), "finish_reason": "stop", "resource_usage": {}},
    ])
    calls: list[dict] = []

    def fake_call(*args, **kwargs):
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(state_assessment, "call_state_assessment_llm", fake_call)
    result = run_state_assessment(
        persona_id="Persona_01",
        day_index=2,
        previous_normalized_values=_previous_values(),
        current_simulated_diary_entry="current",
        previous_diary_entries=[],
        output_dir=tmp_path,
        max_tokens=10000,
    )
    assert result["state_assessment_mode"] == "llm"
    assert len(calls) == 2
    assert calls[1]["repair_instruction"] == state_assessment.JSON_REPAIR_INSTRUCTION
    assert (tmp_path / "state_assessment_Persona_01_raw_invalid.txt").exists()


def _mixed_items(construct: str, scores: list[float | None], span: str = "explicit diary evidence") -> list[dict]:
    low, high = BACKEND_CONSTRUCT_RANGES[construct]
    return [
        {
            "question_id": f"{construct}_q{i + 1}",
            "score": score,
            "range": f"{low:g}-{high:g}",
            "evidence_spans": [] if score is None else [span],
            "reasoning_short": "" if score is None else "diary explicitly supports this item",
        }
        for i, score in enumerate(scores)
    ]


def test_all_null_construct_is_accepted_and_keeps_previous_value() -> None:
    diary = "No psychological questionnaire evidence today."
    payload = _payload()
    payload["item_scores"]["intention"] = {"items": _mixed_items("intention", [None, None, None], diary), "mean_score": None}
    validated = validate_state_assessment_output(payload, expected_persona_id="Persona_01", expected_day_index=2, current_simulated_diary_entry=diary)
    assert not validated["rejected_item_scores"]["intention"]
    assert validated["accepted_item_scores"]["intention"]["mean_score"] is None
    update = item_assessment_to_smoothed_construct_update({**_previous_values(), "intention": 0.63}, validated["accepted_item_scores"])
    assert update["targets_normalized"]["intention"] is None
    assert update["delta_applied"]["intention"] == pytest.approx(0.0)
    assert update["updated_values"]["intention"] == pytest.approx(0.63)


def test_mixed_numeric_and_null_items_recalculate_mean_from_numeric_scores_only() -> None:
    diary = "I strongly intend to exercise and I also plan to be active."
    payload = _payload()
    payload["item_scores"]["intention"] = {"items": _mixed_items("intention", [5, None, 3], diary), "mean_score": 4.0}
    validated = validate_state_assessment_output(payload, expected_persona_id="Persona_01", expected_day_index=2, current_simulated_diary_entry=diary)
    assert validated["accepted_item_scores"]["intention"]["mean_score"] == pytest.approx(4.0)
    assert not validated["rejected_item_scores"]["intention"]


def test_incorrect_llm_mean_is_logged_not_authoritative() -> None:
    diary = "I strongly intend to exercise and I also plan to be active."
    payload = _payload()
    payload["item_scores"]["intention"] = {"items": _mixed_items("intention", [5, None, 3], diary), "mean_score": 2.6667}
    validated = validate_state_assessment_output(payload, expected_persona_id="Persona_01", expected_day_index=2, current_simulated_diary_entry=diary)
    accepted = validated["accepted_item_scores"]["intention"]
    assert accepted["mean_score"] == pytest.approx(4.0)
    assert accepted["validation_diagnostics"]["mean_score_discrepancy"]["raw_llm_mean_score"] == pytest.approx(2.6667)
    update = item_assessment_to_smoothed_construct_update({**_previous_values(), "intention": 0.5}, validated["accepted_item_scores"])
    assert update["targets_normalized"]["intention"] == pytest.approx(0.5)
    assert update["updated_values"]["intention"] == pytest.approx(0.5)


def test_null_item_with_evidence_is_rejected_as_malformed() -> None:
    diary = "some text"
    payload = _payload()
    items = _mixed_items("intention", [None, None, None], diary)
    items[0]["evidence_spans"] = ["some text"]
    payload["item_scores"]["intention"] = {"items": items, "mean_score": None}
    validated = validate_state_assessment_output(payload, expected_persona_id="Persona_01", expected_day_index=2, current_simulated_diary_entry=diary)
    assert validated["rejected_item_scores"]["intention"]
    assert validated["accepted_item_scores"]["intention"]["mean_score"] is None


def test_numerical_score_without_current_diary_evidence_is_rejected() -> None:
    diary = "current diary has no matching phrase"
    payload = _payload()
    items = _mixed_items("intention", [5, None, 3], "previous-only phrase")
    items[0]["evidence_spans"] = []
    payload["item_scores"]["intention"] = {"items": items, "mean_score": 4.0}
    validated = validate_state_assessment_output(payload, expected_persona_id="Persona_01", expected_day_index=2, current_simulated_diary_entry=diary)
    assert validated["rejected_item_scores"]["intention"]


def test_evidence_from_previous_diary_only_is_rejected() -> None:
    diary = "current diary has no matching phrase"
    payload = _payload()
    payload["item_scores"]["intention"] = {"items": _mixed_items("intention", [5, None, 3], "previous-only phrase"), "mean_score": 4.0}
    validated = validate_state_assessment_output(payload, expected_persona_id="Persona_01", expected_day_index=2, current_simulated_diary_entry=diary)
    assert validated["rejected_item_scores"]["intention"]


def test_intrinsic_motivation_has_exactly_three_expected_items() -> None:
    diary = "The activity was fun and interesting today."
    payload = _payload()
    payload["item_scores"]["intrinsic_motivation"] = {"items": _mixed_items("intrinsic_motivation", [4, None, 2], diary), "mean_score": 3.0}
    validated = validate_state_assessment_output(payload, expected_persona_id="Persona_01", expected_day_index=2, current_simulated_diary_entry=diary)
    assert CONSTRUCT_ITEM_COUNTS["intrinsic_motivation"] == 3
    assert [item["question_id"] for item in validated["accepted_item_scores"]["intrinsic_motivation"]["items"]] == [
        "intrinsic_motivation_q1", "intrinsic_motivation_q2", "intrinsic_motivation_q3"
    ]
    twelve_items = _mixed_items("intrinsic_motivation", [4, None, 2] + [1] * 9, diary)
    payload["item_scores"]["intrinsic_motivation"] = {"items": twelve_items, "mean_score": 1.7}
    rejected = validate_state_assessment_output(payload, expected_persona_id="Persona_01", expected_day_index=2, current_simulated_diary_entry=diary)
    assert rejected["rejected_item_scores"]["intrinsic_motivation"]


def test_partial_intrinsic_motivation_normalizes_recalculated_mean() -> None:
    diary = "The activity was fun and interesting today."
    payload = _payload()
    payload["item_scores"]["intrinsic_motivation"] = {"items": _mixed_items("intrinsic_motivation", [4, None, 2], diary), "mean_score": 3.0}
    validated = validate_state_assessment_output(payload, expected_persona_id="Persona_01", expected_day_index=2, current_simulated_diary_entry=diary)
    update = item_assessment_to_smoothed_construct_update({**_previous_values(), "intrinsic_motivation": 0.5}, validated["accepted_item_scores"])
    assert update["scale_means"]["intrinsic_motivation"] == pytest.approx(3.0)
    assert update["targets_normalized"]["intrinsic_motivation"] == pytest.approx(0.75)


def test_malformed_construct_does_not_invalidate_valid_construct() -> None:
    diary = "I strongly intend to exercise and I also plan to be active."
    payload = _payload()
    payload["item_scores"]["intention"] = {"items": _mixed_items("intention", [5, None, 3], diary), "mean_score": 4.0}
    bad = _mixed_items("action_planning", [6, None, 4, None], diary)
    bad[0]["question_id"] = "action_planning_q9"
    payload["item_scores"]["action_planning"] = {"items": bad, "mean_score": 5.0}
    validated = validate_state_assessment_output(payload, expected_persona_id="Persona_01", expected_day_index=2, current_simulated_diary_entry=diary)
    update = item_assessment_to_smoothed_construct_update({**_previous_values(), "intention": 0.0, "action_planning": 0.5}, validated["accepted_item_scores"])
    assert update["updated_values"]["action_planning"] == pytest.approx(0.5)
    assert update["updated_values"]["intention"] > 0.0


def test_prompt_regression_for_partial_null_item_schema() -> None:
    prompt = load_state_assessment_prompt()
    assert "Absence of information is not evidence of a low construct value" in prompt
    assert "Items with `score = null` must be excluded completely from the calculation" in prompt
    assert "Every `evidence_span` must be an exact substring of the current simulated diary entry" in prompt
    for construct, count in CONSTRUCT_ITEM_COUNTS.items():
        assert construct in prompt
        for i in range(1, count + 1):
            assert f"`{construct}_q{i}`" in prompt or f'"question_id": "{construct}_q{i}"' in prompt
    assert "intrinsic_motivation_q4" not in prompt
