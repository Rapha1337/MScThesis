from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

SIMULATION_DIR = Path(__file__).resolve().parents[1]
if str(SIMULATION_DIR) not in sys.path:
    sys.path.append(str(SIMULATION_DIR))

from psychological_state import BACKEND_CONSTRUCT_RANGES
from state_assessment import (
    ACTIVE_CONSTRUCTS,
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


def test_prompt_loads_and_contains_all_required_context() -> None:
    prompt = load_state_assessment_prompt()
    assert "Leere `items`-Arrays" in prompt
    assert "keine gültige finale Ausgabe" in prompt
    rendered = render_state_assessment_prompt(
        prompt,
        persona_id="Persona_01",
        day_index=2,
        previous_psychological_construct_values=_previous_values(),
        current_day_context={"weekday": 2},
        planned_physical_activity=None,
        physical_activity_decision="extra_activity",
        decision_rationale="Spontaneous movement was plausible.",
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
        "current_day_context",
        "planned_physical_activity",
        "physical_activity_decision",
        "decision_rationale",
        "current_simulated_diary_entry",
        "previous_diary_entries",
        "previous_diary_entries_summary",
    ))


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


def test_validation_rejects_out_of_range_and_accepts_intrinsic_zero() -> None:
    payload = _valid_payload()
    for item in payload["item_scores"]["intrinsic_motivation"]["items"]:
        item["score"] = 0
    validated = validate_state_assessment_output(
        payload,
        expected_persona_id="Persona_01",
        expected_day_index=2,
    )
    assert validated["mean_scores_raw"]["intrinsic_motivation"] == 0

    invalid = _valid_payload()
    invalid["item_scores"]["automaticity"]["items"][0]["score"] = 0
    with pytest.raises(ValueError, match="outside expected range"):
        validate_state_assessment_output(
            invalid,
            expected_persona_id="Persona_01",
            expected_day_index=2,
        )


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
        current_day_context={"weekday": 2},
        planned_physical_activity=None,
        pa_decision={
            "decision_label": "extra_activity",
            "rationale_short": "rationale",
            "diary_entry": "current",
        },
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
