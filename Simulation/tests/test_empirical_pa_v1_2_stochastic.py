from __future__ import annotations

from pathlib import Path
import sys

import pytest

SIMULATION_DIR = Path(__file__).resolve().parents[1]
if str(SIMULATION_DIR) not in sys.path:
    sys.path.append(str(SIMULATION_DIR))

from empirical_pa_v1_2_stochastic import (
    sample_final_decision,
    sampling_seed,
    validate_contextual_assessment,
)
from run_llm_pa_decision import (
    DECISION_SOURCE_EMPIRICAL_V1_2_STOCHASTIC,
    build_pa_decision_input,
)


def _pa_input(*, extra_probability: float = 0.35, day_index: int = 2) -> dict:
    context = {
        "persona_id": "T1_Medoid_C4_8303",
        "seed": 1098547461,
        "day_index": day_index,
        "calendar_date": "2026-07-11",
        "phase": "high_stress",
        "phase_llm": "high_stress",
        "weekday": 5,
        "weekday_name": "Saturday",
        "weekday_convention": "0=Monday",
        "psychological_state": {
            "values_normalized": {
                "automaticity": 0.125,
                "action_planning": 0.0,
            }
        },
        "hourly_context_24h": [
            {
                "hour": hour,
                "activity_type": "downtime",
                "subtype": "downtime",
                "current_location": "home",
                "energy_level": 0.5,
                "energy_category": "medium",
                "is_daylight": 8 <= hour <= 20,
                "is_wet": False,
                "active_constraints": [],
                "poi_accessibility": {},
            }
            for hour in range(24)
        ],
    }
    behavior_policy = {
        "do_planned_activity": 0.0,
        "adapt_activity": 0.0,
        "skip_activity": 1.0 - extra_probability,
        "extra_activity": extra_probability,
    }
    return build_pa_decision_input(
        context,
        behavior_policy,
        empirical_pa_v1_2_metadata={"mode": "empirical_pa_v1_2"},
    )


def _assessment(probability: float) -> dict:
    return {
        "persona_id": "T1_Medoid_C4_8303",
        "day_index": 2,
        "contextual_pa_probability": probability,
        "activity_if_performed": {
            "duration_min": 35,
            "intensity": "light",
            "rationale_short": "Free time makes a short light activity plausible.",
            "diary_entry": "I went for a relaxed 35-minute walk.",
        },
        "no_activity_if_skipped": {
            "rationale_short": "The sampled outcome was no activity.",
            "diary_entry": "I did not do any additional physical activity today.",
        },
    }


def test_contextual_assessment_validates_probability_and_conditional_branches() -> None:
    validated = validate_contextual_assessment(
        _assessment(0.42),
        expected_persona_id="T1_Medoid_C4_8303",
        expected_day_index=2,
    )
    assert validated["contextual_pa_probability"] == pytest.approx(0.42)
    assert validated["activity_if_performed"]["duration_min"] == 35
    assert validated["activity_if_performed"]["intensity"] == "light"


@pytest.mark.parametrize("bad_probability", [-0.01, 1.01])
def test_contextual_assessment_rejects_probability_outside_unit_interval(
    bad_probability: float,
) -> None:
    with pytest.raises(ValueError, match=r"within \[0, 1\]"):
        validate_contextual_assessment(
            _assessment(bad_probability),
            expected_persona_id="T1_Medoid_C4_8303",
            expected_day_index=2,
        )


def test_seeded_sampling_is_reproducible_and_uses_persona_day_seed() -> None:
    pa_input = _pa_input(extra_probability=0.35)
    first = sample_final_decision(_assessment(0.42), pa_decision_input=pa_input)
    second = sample_final_decision(_assessment(0.42), pa_decision_input=pa_input)

    assert first == second
    assert first["decision_sampling_seed"] == sampling_seed(pa_input)
    assert first["behavior_policy_pa_prior"] == pytest.approx(0.35)
    assert first["contextual_pa_probability"] == pytest.approx(0.42)
    assert 0.0 <= first["decision_sampling_random_value"] < 1.0
    assert first["sampled_decision_label"] == first["decision_label"]


def test_probability_zero_always_skips_and_probability_one_always_performs() -> None:
    pa_input = _pa_input(extra_probability=0.35)

    skipped = sample_final_decision(_assessment(0.0), pa_decision_input=pa_input)
    performed = sample_final_decision(_assessment(1.0), pa_decision_input=pa_input)

    assert skipped["decision_label"] == "skip_activity"
    assert skipped["duration_min"] == 0
    assert skipped["intensity"] == "none"

    assert performed["decision_label"] == "extra_activity"
    assert performed["duration_min"] == 35
    assert performed["intensity"] == "light"


def test_empirical_v1_2_input_records_stochastic_decision_source() -> None:
    pa_input = _pa_input()
    assert pa_input["decision_source"] == DECISION_SOURCE_EMPIRICAL_V1_2_STOCHASTIC
    assert pa_input["valid_decision_categories"] == ["skip_activity", "extra_activity"]
    assert pa_input["planned_physical_activity"] is None


def test_v1_2_prompt_requires_probability_not_binary_choice_and_classifies_normal_walk_as_light() -> None:
    prompt = (SIMULATION_DIR / "PADecision_EmpiricalV1_2_Prompt.md").read_text(
        encoding="utf-8"
    )
    assert "entscheidest deshalb **nicht direkt**" in prompt
    assert "contextual_pa_probability" in prompt
    assert "reproduzierbar" in prompt
    assert "normales oder gemütliches Spazieren ist **light**" in prompt


def test_real_llm2_path_parses_contextual_probability_and_returns_sampled_decision(
    monkeypatch,
    tmp_path: Path,
) -> None:
    import json
    import run_llm_pa_decision as module

    assessment = _assessment(1.0)

    class _FakeMessage:
        content = json.dumps(assessment)

    class _FakeChoice:
        message = _FakeMessage()
        finish_reason = "stop"

    class _FakeResponse:
        choices = [_FakeChoice()]
        usage = {"completion_tokens": 1, "prompt_tokens": 1, "total_tokens": 2}

    class _FakeCompletions:
        def create(self, **kwargs):
            del kwargs
            return _FakeResponse()

    class _FakeClient:
        chat = type("Chat", (), {"completions": _FakeCompletions()})()

    monkeypatch.setattr(module, "get_client", lambda: _FakeClient())

    result = module.run_pa_decision_llm(
        _pa_input(extra_probability=0.35),
        system_prompt="system",
        output_dir=tmp_path,
    )

    assert result["decision_label"] == "extra_activity"
    assert result["duration_min"] == 35
    assert result["intensity"] == "light"
    assert result["contextual_pa_probability"] == pytest.approx(1.0)
    assert result["behavior_policy_pa_prior"] == pytest.approx(0.35)
    assert result["sampled_decision_label"] == "extra_activity"
    assert result["decision_sampling_seed"] == sampling_seed(_pa_input(extra_probability=0.35))
    assert result["llm2_contextual_assessment"]["contextual_pa_probability"] == pytest.approx(1.0)


def test_sampling_seed_is_runtime_only_and_not_exposed_to_llm2() -> None:
    import json
    from run_llm_pa_decision import build_pa_decision_user_prompt

    pa_input = _pa_input()
    assert pa_input["daily_context"]["seed"] == 1098547461

    prompt = build_pa_decision_user_prompt(pa_input)
    serialized_input = prompt.split("INPUT:\n", 1)[1].split("\n\nIMPORTANT:", 1)[0]
    prompt_payload = json.loads(serialized_input)

    assert "seed" not in prompt_payload["daily_context"]
    assert prompt_payload["behavior_policy"]["extra_activity"] == pytest.approx(0.35)
