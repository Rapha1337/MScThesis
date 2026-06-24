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
    EVIDENCE_TARGET_OFFSETS,
    build_dry_run_state_assessment,
    evidence_to_deterministic_construct_update,
    load_state_assessment_prompt,
    render_state_assessment_prompt,
    run_state_assessment,
    validate_state_assessment_output,
)


def _previous_values() -> dict[str, float]:
    return {construct: 0.5 for construct in ACTIVE_CONSTRUCTS}


def _none_payload(diary: str = "current") -> dict:
    return build_dry_run_state_assessment(
        persona_id="Persona_01", day_index=2, previous_normalized_values=_previous_values()
    )


def _present(construct: str, span: str, direction: str = "positive", strength: str = "moderate") -> dict:
    payload = _none_payload(span)
    payload["construct_evidence"][construct] = {
        "evidence_present": True,
        "direction": direction,
        "strength": strength,
        "evidence_span": span,
        "reasoning_short": f"direct {construct} evidence",
    }
    return payload


def test_prompt_loads_evidence_schema_and_context_only_inputs() -> None:
    prompt = load_state_assessment_prompt()
    assert "construct_evidence" in prompt
    assert "Never output questionnaire item scores" in prompt
    assert "Feeling energetic is not automatically PBC" in prompt
    rendered = render_state_assessment_prompt(
        prompt,
        persona_id="Persona_01",
        day_index=2,
        previous_psychological_construct_values=_previous_values(),
        current_simulated_diary_entry="I felt energetic today.",
        previous_diary_entries=[{"day_index": 0, "diary_entry": "Earlier entry"}],
        previous_diary_entries_summary=None,
        current_decision_label="extra_activity",
        was_physical_activity_planned_today=False,
        planned_physical_activity_summary=None,
    )
    assert "I felt energetic today." in rendered
    assert "Earlier entry" in rendered
    assert all("{" + key + "}" not in rendered for key in state_assessment.REQUIRED_PROMPT_PLACEHOLDERS)


@pytest.mark.parametrize(
    "diary",
    [
        "I completed the planned workout.",
        "The rain and cold made going outside unattractive.",
        "I felt energetic today.",
    ],
)
def test_absent_evidence_keeps_all_constructs_unchanged(diary: str) -> None:
    validated = validate_state_assessment_output(
        _none_payload(diary),
        expected_persona_id="Persona_01",
        expected_day_index=2,
        current_simulated_diary_entry=diary,
    )
    update = evidence_to_deterministic_construct_update(_previous_values(), validated["accepted_evidence"])
    assert all(not ev["evidence_present"] for ev in validated["accepted_evidence"].values())
    assert update["updated_values"] == pytest.approx(_previous_values())
    assert all(target is None for target in update["targets_normalized"].values())


@pytest.mark.parametrize(
    "construct,diary",
    [
        ("intention", "I decided in the morning that I would exercise after work."),
        ("action_planning", "I packed my training clothes in the morning and planned to go to the gym at 18:00 after work."),
        ("intrinsic_motivation", "I genuinely enjoyed the workout and had fun during the session."),
        ("pa_specific_self_control", "I wanted to stay on the sofa, but I resisted the temptation to skip and went to training."),
        ("perceived_behavioral_control", "Despite the busy day, I felt capable of completing the session and believed it was under my control."),
        ("attitude_toward_the_behavior", "I considered the exercise beneficial and worthwhile."),
        ("subjective_norm", "My training partner encouraged me and expected me to attend."),
        ("motivational_competence", "I knew how to motivate myself and was able to get started effectively."),
    ],
)
def test_explicit_construct_evidence_updates_only_that_construct(construct: str, diary: str) -> None:
    validated = validate_state_assessment_output(
        _present(construct, diary),
        expected_persona_id="Persona_01",
        expected_day_index=2,
        current_simulated_diary_entry=diary,
    )
    update = evidence_to_deterministic_construct_update(_previous_values(), validated["accepted_evidence"])
    for name in ACTIVE_CONSTRUCTS:
        if name == construct:
            assert validated["accepted_evidence"][name]["evidence_present"] is True
            assert update["updated_values"][name] == pytest.approx(0.53)
        else:
            assert update["updated_values"][name] == pytest.approx(0.5)


def test_validator_rejects_forbidden_scoring_keys_and_non_substring_spans() -> None:
    payload = _present("intention", "not in diary")
    validated = validate_state_assessment_output(
        payload,
        expected_persona_id="Persona_01",
        expected_day_index=2,
        current_simulated_diary_entry="I decided to exercise.",
    )
    assert not validated["accepted_evidence"]["intention"]["evidence_present"]
    assert validated["rejected_evidence"]["intention"]

    payload["item_scores"] = {}
    with pytest.raises(ValueError, match="forbidden scoring/target keys"):
        validate_state_assessment_output(
            payload,
            expected_persona_id="Persona_01",
            expected_day_index=2,
            current_simulated_diary_entry="I decided to exercise.",
        )


def test_duplicate_span_conflict_rejects_ambiguous_assignments() -> None:
    diary = "I felt good after going outside."
    payload = _none_payload(diary)
    for construct in ["intention", "intrinsic_motivation", "attitude_toward_the_behavior"]:
        payload["construct_evidence"][construct] = {
            "evidence_present": True,
            "direction": "positive",
            "strength": "moderate",
            "evidence_span": diary,
            "reasoning_short": "generic positive phrase",
        }
    validated = validate_state_assessment_output(
        payload,
        expected_persona_id="Persona_01",
        expected_day_index=2,
        current_simulated_diary_entry=diary,
    )
    assert validated["duplicate_span_conflicts"]
    assert all(not validated["accepted_evidence"][c]["evidence_present"] for c in ["intention", "intrinsic_motivation", "attitude_toward_the_behavior"])


def test_deterministic_update_calculation_strength_direction_clamping_and_bounds() -> None:
    evidence = {construct: {"evidence_present": False, "direction": None, "strength": None, "evidence_span": None, "reasoning_short": ""} for construct in ACTIVE_CONSTRUCTS}
    evidence["intention"] = {"evidence_present": True, "direction": "positive", "strength": "weak"}
    evidence["attitude_toward_the_behavior"] = {"evidence_present": True, "direction": "negative", "strength": "moderate"}
    evidence["intrinsic_motivation"] = {"evidence_present": True, "direction": "positive", "strength": "strong"}
    previous = _previous_values(); previous["intrinsic_motivation"] = 0.95
    update = evidence_to_deterministic_construct_update(previous, evidence)
    assert EVIDENCE_TARGET_OFFSETS == {"weak": 0.05, "moderate": 0.15, "strong": 0.25}
    assert update["targets_normalized"]["intention"] == pytest.approx(0.55)
    assert update["updated_values"]["intention"] == pytest.approx(0.51)
    assert update["targets_normalized"]["attitude_toward_the_behavior"] == pytest.approx(0.35)
    assert update["updated_values"]["attitude_toward_the_behavior"] == pytest.approx(0.47)
    assert update["targets_normalized"]["intrinsic_motivation"] == pytest.approx(1.0)
    assert update["updated_values"]["intrinsic_motivation"] == pytest.approx(0.96)
    assert update["targets_normalized"]["automaticity"] is None
    assert max(abs(delta) for delta in update["delta_applied"].values()) <= 0.10


def test_automaticity_gate_requires_third_similar_occurrence() -> None:
    evidence = {construct: {"evidence_present": False, "direction": None, "strength": None, "evidence_span": None, "reasoning_short": ""} for construct in ACTIVE_CONSTRUCTS}
    evidence["automaticity"] = {"evidence_present": True, "direction": "positive", "strength": "moderate", "evidence_span": "automatically", "reasoning_short": "explicit automatic action"}
    kwargs = dict(current_decision_label="do_planned_activity", was_physical_activity_planned_today=True, planned_physical_activity_summary={"location": "gym", "time_of_day": "evening"})
    first = evidence_to_deterministic_construct_update(_previous_values(), evidence, previous_diary_entries=[], **kwargs)
    sig = first["automaticity_repetition_gate"]["current_context_signature"]
    one_prior = [{"state_assessment_automaticity_context_signature": sig}]
    two_prior = [{"state_assessment_automaticity_context_signature": sig}, {"state_assessment_automaticity_context_signature": sig}]
    second = evidence_to_deterministic_construct_update(_previous_values(), evidence, previous_diary_entries=one_prior, **kwargs)
    third = evidence_to_deterministic_construct_update(_previous_values(), evidence, previous_diary_entries=two_prior, **kwargs)
    dissimilar = evidence_to_deterministic_construct_update(_previous_values(), evidence, previous_diary_entries=[{"state_assessment_automaticity_context_signature": {"planned_vs_extra": "extra"}} for _ in range(2)], **kwargs)
    assert first["updated_values"]["automaticity"] == pytest.approx(0.5)
    assert second["updated_values"]["automaticity"] == pytest.approx(0.5)
    assert third["updated_values"]["automaticity"] == pytest.approx(0.53)
    assert dissimilar["updated_values"]["automaticity"] == pytest.approx(0.5)


def test_dry_run_assessment_keeps_state_and_records_previous_context() -> None:
    previous_entries = [{"day_index": 0, "diary_entry": "first"}, {"day_index": 1, "diary_entry": "second"}]
    result = run_state_assessment(
        persona_id="Persona_01", day_index=2, previous_normalized_values=_previous_values(),
        current_simulated_diary_entry="current", previous_diary_entries=previous_entries, dry_run=True,
    )
    assert result["state_assessment_mode"] == "dry_run_mock"
    assert result["psychological_construct_values_after_state_assessment"] == pytest.approx(_previous_values())
    assert result["state_assessment_construct_evidence"]
    assert result["state_assessment_validation"]["accepted_evidence"]
    assert result["previous_diary_entries_count"] == 2


@pytest.mark.parametrize("json_mode", [False, True])
def test_state_assessment_response_format_is_explicitly_opt_in(monkeypatch: pytest.MonkeyPatch, json_mode: bool) -> None:
    captured: dict = {}
    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            choice = type("Choice", (), {"message": type("Message", (), {"content": json.dumps(_none_payload())})(), "finish_reason": "stop"})()
            return type("Response", (), {"choices": [choice], "usage": None})()
    fake_client = type("Client", (), {"chat": type("Chat", (), {"completions": FakeCompletions()})()})()
    monkeypatch.setattr(state_assessment, "_get_client", lambda: fake_client)
    state_assessment.call_state_assessment_llm("prompt", json_mode=json_mode)
    assert (captured.get("response_format") == {"type": "json_object"}) is json_mode


def test_malformed_json_is_saved_with_metadata_and_retried_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = iter([
        {"raw_response": '{"persona_id": "Persona_01", bad: true}', "finish_reason": "stop", "resource_usage": {}},
        {"raw_response": json.dumps(_none_payload()), "finish_reason": "stop", "resource_usage": {}},
    ])
    calls: list[dict] = []
    def fake_call(*args, **kwargs):
        calls.append(kwargs); return next(responses)
    monkeypatch.setattr(state_assessment, "call_state_assessment_llm", fake_call)
    result = run_state_assessment(persona_id="Persona_01", day_index=2, previous_normalized_values=_previous_values(), current_simulated_diary_entry="current", previous_diary_entries=[], output_dir=tmp_path, max_tokens=10000)
    assert result["state_assessment_mode"] == "llm"
    assert len(calls) == 2
    assert calls[1]["repair_instruction"] == state_assessment.JSON_REPAIR_INSTRUCTION
    assert (tmp_path / "state_assessment_Persona_01_raw_invalid.txt").exists()
    assert (tmp_path / "state_assessment_Persona_01_parse_error.json").exists()
