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
    build_dry_run_state_assessment,
    evidence_to_deterministic_construct_update,
    load_state_assessment_prompt,
    render_state_assessment_prompt,
    run_state_assessment,
    validate_state_assessment_output,
)


def _previous_values(value: float = 0.5) -> dict[str, float]:
    return {construct: value for construct in ACTIVE_CONSTRUCTS}


def _none_payload() -> dict:
    return build_dry_run_state_assessment(persona_id="Persona_01", day_index=2, previous_normalized_values=_previous_values())


def _present(construct: str, span: str, target: float = 0.65, reasoning: str | None = None) -> dict:
    payload = _none_payload()
    payload["construct_evidence"][construct] = {
        "evidence_present": True,
        "target_value_normalized": target,
        "evidence_span": span,
        "reasoning_short": reasoning or f"direct {construct} evidence",
    }
    return payload


def test_prompt_loads_continuous_target_schema_and_context_only_inputs() -> None:
    prompt = load_state_assessment_prompt()
    assert "target_value_normalized" in prompt
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


@pytest.mark.parametrize("diary", ["I completed the planned workout.", "I felt energetic and the gym was nearby, so I trained."])
def test_behavior_energy_and_accessibility_have_no_evidence(diary: str) -> None:
    validated = validate_state_assessment_output(_none_payload(), expected_persona_id="Persona_01", expected_day_index=2, current_simulated_diary_entry=diary)
    update = evidence_to_deterministic_construct_update(_previous_values(), validated["accepted_evidence"])
    assert all(not ev["evidence_present"] for ev in validated["accepted_evidence"].values())
    assert all(target is None for target in update["targets_normalized"].values())
    assert update["updated_values"] == pytest.approx(_previous_values())


@pytest.mark.parametrize(
    "construct,diary,target,compare",
    [
        ("intention", "I was determined to train after work and had decided in the morning that I would go.", 0.70, "above"),
        ("perceived_behavioral_control", "I did not feel capable of completing the workout and felt that it was beyond my control today.", 0.30, "below"),
        ("pa_specific_self_control", "I wanted to stay on the sofa, but I resisted the temptation to skip and went to training.", 0.72, "above"),
        ("intrinsic_motivation", "I genuinely enjoyed the session and had fun while exercising.", 0.75, "above"),
        ("attitude_toward_the_behavior", "I considered the exercise worthwhile and beneficial.", 0.76, "above"),
        ("subjective_norm", "My training partner encouraged me and expected me to attend.", 0.68, "above"),
        ("motivational_competence", "I knew how to motivate myself and managed to get started effectively.", 0.71, "above"),
    ],
)
def test_explicit_construct_evidence_updates_only_that_construct(construct: str, diary: str, target: float, compare: str) -> None:
    validated = validate_state_assessment_output(_present(construct, diary, target), expected_persona_id="Persona_01", expected_day_index=2, current_simulated_diary_entry=diary)
    update = evidence_to_deterministic_construct_update(_previous_values(), validated["accepted_evidence"])
    for name in ACTIVE_CONSTRUCTS:
        if name == construct:
            assert validated["accepted_evidence"][name]["evidence_present"] is True
            assert 0 <= validated["accepted_evidence"][name]["target_value_normalized"] <= 1
            if compare == "above":
                assert update["updated_values"][name] > 0.5
            else:
                assert update["updated_values"][name] < 0.5
        else:
            assert update["updated_values"][name] == pytest.approx(0.5)


def test_multiple_valid_clauses_can_share_span_without_duplicate_rejection() -> None:
    diary = "I was determined to go, and I genuinely enjoyed the workout once I started."
    payload = _none_payload()
    payload["construct_evidence"]["intention"] = {"evidence_present": True, "target_value_normalized": 0.7, "evidence_span": diary, "reasoning_short": "determination clause supports intention"}
    payload["construct_evidence"]["intrinsic_motivation"] = {"evidence_present": True, "target_value_normalized": 0.72, "evidence_span": diary, "reasoning_short": "enjoyment clause supports intrinsic motivation"}
    validated = validate_state_assessment_output(payload, expected_persona_id="Persona_01", expected_day_index=2, current_simulated_diary_entry=diary)
    assert not validated["duplicate_span_conflicts"]
    assert validated["accepted_evidence"]["intention"]["evidence_present"]
    assert validated["accepted_evidence"]["intrinsic_motivation"]["evidence_present"]


def test_duplicate_span_conflict_rejects_ambiguous_assignments() -> None:
    diary = "I felt good and completed the workout."
    payload = _none_payload()
    for construct in ["perceived_behavioral_control", "intrinsic_motivation", "attitude_toward_the_behavior"]:
        payload["construct_evidence"][construct] = {"evidence_present": True, "target_value_normalized": 0.7, "evidence_span": diary, "reasoning_short": "generic positive phrase"}
    validated = validate_state_assessment_output(payload, expected_persona_id="Persona_01", expected_day_index=2, current_simulated_diary_entry=diary)
    assert all(not validated["accepted_evidence"][c]["evidence_present"] for c in ["perceived_behavioral_control", "intrinsic_motivation", "attitude_toward_the_behavior"])


def test_validator_rejects_forbidden_fields_bad_targets_and_non_substring_spans() -> None:
    diary = "I decided to exercise."
    for bad in [
        {"evidence_present": True, "target_value_normalized": 1.2, "evidence_span": diary, "reasoning_short": "bad high"},
        {"evidence_present": True, "target_value_normalized": "high", "evidence_span": diary, "reasoning_short": "bad type"},
        {"evidence_present": True, "target_value_normalized": 0.7, "evidence_span": "not in diary", "reasoning_short": "bad span"},
        {"evidence_present": True, "target_value_normalized": 0.7, "evidence_span": diary, "reasoning_short": "bad", "direction": "positive"},
    ]:
        payload = _none_payload(); payload["construct_evidence"]["intention"] = bad
        validated = validate_state_assessment_output(payload, expected_persona_id="Persona_01", expected_day_index=2, current_simulated_diary_entry=diary)
        assert not validated["accepted_evidence"]["intention"]["evidence_present"]


def test_continuous_update_calculation_clamping_null_and_boundaries() -> None:
    evidence = {construct: {"evidence_present": False, "target_value_normalized": None, "evidence_span": None, "reasoning_short": ""} for construct in ACTIVE_CONSTRUCTS}
    evidence["intention"] = {"evidence_present": True, "target_value_normalized": 0.72, "evidence_span": "determined", "reasoning_short": "explicit intention"}
    update = evidence_to_deterministic_construct_update({**_previous_values(), "intention": 0.60}, evidence)
    assert update["delta_proposed"]["intention"] == pytest.approx(0.024)
    assert update["updated_values"]["intention"] == pytest.approx(0.624)
    evidence["intention"]["target_value_normalized"] = 0.1
    assert evidence_to_deterministic_construct_update({**_previous_values(), "intention": 0.6}, evidence)["updated_values"]["intention"] == pytest.approx(0.5)
    evidence["intention"]["target_value_normalized"] = None
    assert evidence_to_deterministic_construct_update({**_previous_values(), "intention": 0.6}, evidence)["updated_values"]["intention"] == pytest.approx(0.6)
    evidence["intention"]["target_value_normalized"] = 1.0
    assert evidence_to_deterministic_construct_update({**_previous_values(), "intention": 0.0}, evidence)["updated_values"]["intention"] == pytest.approx(0.1)
    evidence["intention"]["target_value_normalized"] = 0.0
    assert evidence_to_deterministic_construct_update({**_previous_values(), "intention": 1.0}, evidence)["updated_values"]["intention"] == pytest.approx(0.9)
    evidence["intention"]["target_value_normalized"] = "bad"
    assert evidence_to_deterministic_construct_update({**_previous_values(), "intention": 0.6}, evidence)["updated_values"]["intention"] == pytest.approx(0.6)


def test_automaticity_diary_only_gate_requires_third_qualifying_occurrence() -> None:
    evidence = {construct: {"evidence_present": False, "target_value_normalized": None, "evidence_span": None, "reasoning_short": ""} for construct in ACTIVE_CONSTRUCTS}
    evidence["automaticity"] = {"evidence_present": True, "target_value_normalized": 0.7, "evidence_span": "as part of my routine", "reasoning_short": "explicit routine wording"}
    first = evidence_to_deterministic_construct_update(_previous_values(), evidence, previous_diary_entries=[])
    second = evidence_to_deterministic_construct_update(_previous_values(), evidence, previous_diary_entries=[{"diary_entry": "I trained as part of my routine."}])
    third = evidence_to_deterministic_construct_update(_previous_values(), evidence, previous_diary_entries=[{"diary_entry": "I trained as part of my routine."}, {"diary_entry": "I went automatically."}])
    repeated_schedule = evidence_to_deterministic_construct_update(_previous_values(), evidence, previous_diary_entries=[{"diary_entry": "I completed the workout.", "time_of_day": "evening"} for _ in range(3)])
    no_current = evidence.copy(); no_current["automaticity"] = {"evidence_present": False, "target_value_normalized": None, "evidence_span": None, "reasoning_short": ""}
    assert first["updated_values"]["automaticity"] == pytest.approx(0.5)
    assert second["updated_values"]["automaticity"] == pytest.approx(0.5)
    assert third["updated_values"]["automaticity"] > 0.5
    assert repeated_schedule["updated_values"]["automaticity"] == pytest.approx(0.5)
    assert evidence_to_deterministic_construct_update(_previous_values(), no_current, previous_diary_entries=[{"decision_category": "do_planned_activity"} for _ in range(3)])["updated_values"]["automaticity"] == pytest.approx(0.5)


def test_dry_run_assessment_keeps_state_and_records_previous_context() -> None:
    previous_entries = [{"day_index": 0, "diary_entry": "first"}, {"day_index": 1, "diary_entry": "second"}]
    result = run_state_assessment(persona_id="Persona_01", day_index=2, previous_normalized_values=_previous_values(), current_simulated_diary_entry="current", previous_diary_entries=previous_entries, dry_run=True)
    assert result["state_assessment_mode"] == "dry_run_mock"
    assert result["psychological_construct_values_after_state_assessment"] == pytest.approx(_previous_values())
    assert "state_assessment_target_values_normalized" in result
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
