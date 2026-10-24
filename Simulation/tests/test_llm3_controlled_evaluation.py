from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_controlled_evaluation_builds_synthetic_scenarios_without_planned_pa() -> None:
    from llm3_controlled_evaluation import build_synthetic_cases

    cases = build_synthetic_cases()
    scenario_keys = {(case.scenario_id, case.variant_id) for case in cases}

    assert scenario_keys == {
        ("A_time_shortage", "main"),
        ("B_regular_pa", "main"),
        ("C_habit_instigation", "main"),
        ("D_diary_feedback", "neutral"),
        ("D_diary_feedback", "interpretive"),
        ("E_selective_evidence", "main"),
    }
    assert len(cases) == 42
    assert all(case.was_physical_activity_planned_today is False for case in cases)
    assert all(case.planned_physical_activity_summary is None for case in cases)
    assert all(case.persona_id.startswith("SyntheticLLM3_") for case in cases)

    time_shortage = [case for case in cases if case.scenario_id == "A_time_shortage"]
    assert all(case.current_decision_label == "skip_activity" for case in time_shortage)
    assert all(case.pa_decision["start_hour"] is None for case in time_shortage)
    assert all(case.pa_decision["duration_min"] == 0 for case in time_shortage)

    regular = [case for case in cases if case.scenario_id == "B_regular_pa"]
    habit = [case for case in cases if case.scenario_id == "C_habit_instigation"]
    assert {case.persona_id for case in regular + habit} == {
        "SyntheticLLM3_regular_pa_habit_comparison"
    }
    assert [case.pa_decision for case in regular] == [case.pa_decision for case in habit]
    assert any("automatic" in case.current_simulated_diary_entry for case in habit)
    assert all("automatic" not in case.current_simulated_diary_entry for case in regular)

    diary_feedback = [case for case in cases if case.scenario_id == "D_diary_feedback"]
    assert {case.persona_id for case in diary_feedback} == {
        "SyntheticLLM3_diary_feedback_comparison"
    }


def test_controlled_evaluation_loads_default_synthetic_scenarios() -> None:
    from llm3_controlled_evaluation import build_synthetic_cases, load_synthetic_cases

    assert load_synthetic_cases() == build_synthetic_cases()


def test_controlled_evaluation_diary_feedback_differs_only_in_diary_text_on_day_zero() -> None:
    from dataclasses import asdict

    from llm3_controlled_evaluation import build_synthetic_cases

    cases = build_synthetic_cases()
    neutral = next(
        case
        for case in cases
        if case.scenario_id == "D_diary_feedback"
        and case.variant_id == "neutral"
        and case.day_index == 0
    )
    interpretive = next(
        case
        for case in cases
        if case.scenario_id == "D_diary_feedback"
        and case.variant_id == "interpretive"
        and case.day_index == 0
    )

    neutral_dict = asdict(neutral)
    interpretive_dict = asdict(interpretive)
    for field in (
        "case_id",
        "variant_id",
        "scenario_label",
        "manipulation",
        "current_simulated_diary_entry",
    ):
        neutral_dict.pop(field)
        interpretive_dict.pop(field)

    assert neutral_dict == interpretive_dict
    assert neutral.current_simulated_diary_entry != interpretive.current_simulated_diary_entry


def test_controlled_evaluation_day_zero_prompts_differ_only_by_manipulated_diary() -> None:
    from llm3_controlled_evaluation import build_synthetic_cases, render_case_prompt

    cases = build_synthetic_cases()

    def case_for(scenario_id: str, variant_id: str):
        return next(
            case
            for case in cases
            if case.scenario_id == scenario_id
            and case.variant_id == variant_id
            and case.day_index == 0
        )

    comparison_pairs = [
        (case_for("B_regular_pa", "main"), case_for("C_habit_instigation", "main")),
        (
            case_for("D_diary_feedback", "neutral"),
            case_for("D_diary_feedback", "interpretive"),
        ),
    ]
    for first, second in comparison_pairs:
        assert first.persona_id == second.persona_id
        assert first.previous_normalized_values == second.previous_normalized_values
        assert first.previous_diary_entries == second.previous_diary_entries == []
        assert first.pa_decision == second.pa_decision
        first_prompt = render_case_prompt(first)
        second_prompt = render_case_prompt(second)

        assert first.current_simulated_diary_entry in first_prompt
        assert second.current_simulated_diary_entry in second_prompt
        assert first_prompt != second_prompt
        assert first_prompt.replace(first.current_simulated_diary_entry, "<DIARY>") == (
            second_prompt.replace(second.current_simulated_diary_entry, "<DIARY>")
        )


def test_controlled_evaluation_renders_production_prompt_and_writes_dry_run_outputs(
    tmp_path: Path,
) -> None:
    from llm3_controlled_evaluation import (
        prompt_sha256,
        run_controlled_evaluation,
    )
    from state_assessment import load_state_assessment_prompt

    result = run_controlled_evaluation(output_dir=tmp_path)

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    results = _read_jsonl(tmp_path / "results.jsonl")
    prompts = _read_jsonl(tmp_path / "prompts.jsonl")

    expected_prompt_hash = prompt_sha256(load_state_assessment_prompt())
    assert result["manifest"] == manifest
    assert manifest["mode"] == "dry_run_synthetic_mock"
    assert manifest["api_calls_performed"] == 0
    assert manifest["synthetic_only"] is True
    assert manifest["prompt_sha256"] == expected_prompt_hash
    assert manifest["active_constructs"] == [
        "automaticity",
        "pa_specific_self_control",
        "action_planning",
        "intention",
        "perceived_behavioral_control",
        "attitude_toward_the_behavior",
        "subjective_norm",
        "intrinsic_motivation",
        "motivational_competence",
    ]
    assert manifest["alpha"] == 0.20
    assert manifest["max_daily_change"] == 0.10
    assert len(results) == manifest["case_count"] == 42
    assert len(prompts) == 42
    assert "scenario_summaries" in summary
    assert "implemented_dry_run_metrics" in summary
    assert "planned_live_evaluation_metrics" in summary
    assert "evaluation_criteria" not in summary
    assert "repeat_run_consistency" in summary["planned_live_evaluation_metrics"]
    assert "repeat_run_consistency" not in summary["implemented_dry_run_metrics"]
    assert manifest["state_isolation_key"] == "scenario_id__variant_id"
    assert "Day 0 supports controlled single-day comparisons" in (
        " ".join(manifest["interpretation_notes"])
    )
    assert "no synthetic summary is generated" in manifest["prompt_history_summary_note"]
    assert all(prompt["prompt_sha256"] == expected_prompt_hash for prompt in prompts)
    assert all("Was PA planned today: false" in prompt["rendered_prompt"] for prompt in prompts)
    assert all("Planned PA summary: null" in prompt["rendered_prompt"] for prompt in prompts)


def test_controlled_evaluation_mock_updates_separate_raw_targets_from_smoothed_updates(
    tmp_path: Path,
) -> None:
    from llm3_controlled_evaluation import run_controlled_evaluation

    result = run_controlled_evaluation(output_dir=tmp_path)
    results = result["results"]

    selective_day0 = next(
        row
        for row in results
        if row["case"]["scenario_id"] == "E_selective_evidence"
        and row["case"]["day_index"] == 0
    )
    metrics = selective_day0["construct_metrics"]

    assert selective_day0["state_assessment_mean_scores_raw"]["action_planning"] == 6.0
    assert selective_day0["state_assessment_target_values_normalized"]["action_planning"] == 1.0
    assert metrics["action_planning"]["delta"] > 0
    for construct, construct_metrics in metrics.items():
        if construct == "action_planning":
            continue
        assert construct_metrics["raw_mean_score"] is None
        assert construct_metrics["target_normalized_value"] is None
        assert construct_metrics["delta"] == pytest.approx(0.0)

    habit_day0 = next(
        row
        for row in results
        if row["case"]["scenario_id"] == "C_habit_instigation"
        and row["case"]["day_index"] == 0
    )
    regular_day0 = next(
        row
        for row in results
        if row["case"]["scenario_id"] == "B_regular_pa"
        and row["case"]["day_index"] == 0
    )
    assert habit_day0["construct_metrics"]["automaticity"]["delta"] > 0
    assert regular_day0["construct_metrics"]["automaticity"]["delta"] == pytest.approx(0.0)


def test_controlled_evaluation_carries_state_forward_without_variant_mixing(
    tmp_path: Path,
) -> None:
    from llm3_controlled_evaluation import run_controlled_evaluation

    result = run_controlled_evaluation(output_dir=tmp_path)
    results = result["results"]

    def row_for(scenario_id: str, variant_id: str, day_index: int):
        return next(
            row
            for row in results
            if row["case"]["scenario_id"] == scenario_id
            and row["case"]["variant_id"] == variant_id
            and row["case"]["day_index"] == day_index
        )

    regular_day0 = row_for("B_regular_pa", "main", 0)
    regular_day1 = row_for("B_regular_pa", "main", 1)
    habit_day0 = row_for("C_habit_instigation", "main", 0)
    habit_day1 = row_for("C_habit_instigation", "main", 1)
    neutral_day0 = row_for("D_diary_feedback", "neutral", 0)
    neutral_day1 = row_for("D_diary_feedback", "neutral", 1)
    interpretive_day0 = row_for("D_diary_feedback", "interpretive", 0)
    interpretive_day1 = row_for("D_diary_feedback", "interpretive", 1)

    assert regular_day0["case"]["persona_id"] == habit_day0["case"]["persona_id"]
    assert neutral_day0["case"]["persona_id"] == interpretive_day0["case"]["persona_id"]

    assert regular_day1["psychological_construct_values_before_state_assessment"] == (
        regular_day0["psychological_construct_values_after_state_assessment"]
    )
    assert habit_day1["psychological_construct_values_before_state_assessment"] == (
        habit_day0["psychological_construct_values_after_state_assessment"]
    )
    assert neutral_day1["psychological_construct_values_before_state_assessment"] == (
        neutral_day0["psychological_construct_values_after_state_assessment"]
    )
    assert interpretive_day1["psychological_construct_values_before_state_assessment"] == (
        interpretive_day0["psychological_construct_values_after_state_assessment"]
    )

    assert habit_day1["psychological_construct_values_before_state_assessment"] != (
        regular_day1["psychological_construct_values_before_state_assessment"]
    )
    assert interpretive_day1["psychological_construct_values_before_state_assessment"] != (
        neutral_day1["psychological_construct_values_before_state_assessment"]
    )


def test_controlled_evaluation_live_mode_is_explicitly_blocked(tmp_path: Path) -> None:
    from llm3_controlled_evaluation import run_controlled_evaluation

    with pytest.raises(RuntimeError, match="Live LLM3 calls are intentionally disabled"):
        run_controlled_evaluation(output_dir=tmp_path, dry_run=False)


def test_experience_cases_control_every_input_except_diary() -> None:
    from dataclasses import asdict

    from llm3_controlled_evaluation import (
        EXPERIENCE_DIARIES,
        build_experience_cases,
        render_case_prompt,
    )

    cases = build_experience_cases()
    assert [case.variant_id for case in cases] == ["positive", "neutral", "negative"]
    assert [case.current_simulated_diary_entry for case in cases] == list(
        EXPERIENCE_DIARIES.values()
    )
    assert len({case.persona_id for case in cases}) == 1
    assert all(case.previous_diary_entries == [] for case in cases)
    assert all(case.previous_normalized_values == cases[0].previous_normalized_values for case in cases)
    assert all(case.daily_context == cases[0].daily_context for case in cases)
    assert all(case.pa_decision == cases[0].pa_decision for case in cases)
    assert cases[0].pa_decision["duration_min"] == 30
    assert cases[0].pa_decision["activity_form"] == "jogging"
    assert cases[0].current_decision_label == "extra_activity"

    baseline = asdict(cases[0])
    for case in cases[1:]:
        compared = asdict(case)
        for field in (
            "case_id", "variant_id", "scenario_label", "current_simulated_diary_entry"
        ):
            baseline.pop(field, None)
            compared.pop(field)
        assert compared == baseline

    prompts = [render_case_prompt(case) for case in cases]
    for case, prompt in zip(cases, prompts, strict=True):
        assert case.current_simulated_diary_entry in prompt
        assert "Was PA planned today: false" in prompt
        assert "Planned PA summary: null" in prompt
    normalized = [
        prompt.replace(case.current_simulated_diary_entry, "<DIARY>")
        for case, prompt in zip(cases, prompts, strict=True)
    ]
    assert normalized[0] == normalized[1] == normalized[2]


def test_experience_dry_run_writes_three_prompts_and_readable_mock_results(
    tmp_path: Path,
) -> None:
    from llm3_controlled_evaluation import run_controlled_evaluation
    from state_assessment import ACTIVE_CONSTRUCTS

    run_controlled_evaluation(output_dir=tmp_path, case_set="experience")
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    prompts = _read_jsonl(tmp_path / "prompts.jsonl")
    results = _read_jsonl(tmp_path / "results.jsonl")

    assert manifest["case_set"] == "experience"
    assert manifest["case_count"] == len(prompts) == len(results) == 3
    assert manifest["api_calls_performed"] == 0
    assert manifest["model"] == "gpt-oss-120b"
    assert manifest["temperature"] == 0
    assert manifest["top_p"] == 1
    assert manifest["alpha"] == 0.20
    assert manifest["max_daily_change"] == 0.10
    assert manifest["experience_evidence_status"].startswith("experimentally_specified")
    assert "experience_comparison" in summary
    assert all(row["prompt_sha256"] == manifest["prompt_sha256"] for row in prompts)
    assert all(row["llm_response_mode"] == "synthetic_mock_or_recorded_payload" for row in results)
    for result in results:
        assert result["case"]["current_simulated_diary_entry"] in result["rendered_prompt"]
        assert set(result["state_assessment_item_scores"]) == set(ACTIVE_CONSTRUCTS)
        for construct in ACTIVE_CONSTRUCTS:
            items = result["state_assessment_item_scores"][construct]["items"]
            assert all(item["score"] is None for item in items)
            assert all(item["evidence_spans"] == [] for item in items)
            assert result["state_assessment_target_values_normalized"][construct] is None
            assert result["psychological_construct_update_delta_applied"][construct] == 0
            assert (
                result["psychological_construct_values_after_state_assessment"][construct]
                == result["psychological_construct_values_before_state_assessment"][construct]
            )
    assert (
        summary["experience_comparison"]["comparisons"]["positive_vs_neutral"]
        ["intrinsic_motivation"]["raw_mean_difference"] is None
    )


def test_experience_recorded_payload_uses_existing_validation_and_bounded_update() -> None:
    from llm3_controlled_evaluation import (
        build_experience_cases,
        build_llm3_payload_from_construct_scores,
        evaluate_case_raw_response,
        prompt_sha256,
        render_case_prompt,
        summarize_experience_comparison,
    )
    from state_assessment import ACTIVE_CONSTRUCTS, load_state_assessment_prompt

    cases = build_experience_cases()
    prompt_hash = prompt_sha256(load_state_assessment_prompt())
    results = []
    for case in cases:
        previous = dict(case.previous_normalized_values)
        previous["attitude_toward_the_behavior"] = 0.0
        evidence_span = case.current_simulated_diary_entry.split(". ", 1)[-1].rstrip(".")
        assert evidence_span in case.current_simulated_diary_entry
        payload = build_llm3_payload_from_construct_scores(
            persona_id=case.persona_id,
            day_index=case.day_index,
            scores_by_construct={"attitude_toward_the_behavior": 7.0},
        )
        payload["item_scores"]["attitude_toward_the_behavior"]["items"][0][
            "evidence_spans"
        ] = [evidence_span]
        result = evaluate_case_raw_response(
            case,
            previous_values=previous,
            raw_response=json.dumps(payload),
            rendered_prompt=render_case_prompt(case),
            prompt_hash=prompt_hash,
        )
        results.append(result)
        assert result["state_assessment_item_scores"]["attitude_toward_the_behavior"][
            "items"
        ][0]["evidence_spans"] == [evidence_span]
        assert result["psychological_construct_update_delta_proposed"][
            "attitude_toward_the_behavior"
        ] == pytest.approx(0.20)
        assert result["psychological_construct_update_delta_applied"][
            "attitude_toward_the_behavior"
        ] == pytest.approx(0.10)
        assert result["psychological_construct_values_after_state_assessment"][
            "attitude_toward_the_behavior"
        ] == pytest.approx(0.10)
        for construct in set(ACTIVE_CONSTRUCTS) - {"attitude_toward_the_behavior"}:
            assert result["state_assessment_mean_scores_raw"][construct] is None
            assert result["psychological_construct_update_delta_applied"][construct] == 0
            assert result["psychological_construct_values_after_state_assessment"][
                construct
            ] == previous[construct]

    comparison = summarize_experience_comparison(results)["comparisons"]
    assert comparison["positive_vs_neutral"]["attitude_toward_the_behavior"][
        "applied_update_difference"
    ] == 0
    assert comparison["negative_vs_neutral"]["intention"]["raw_mean_difference"] is None


def test_experience_comparison_matches_item_ids_and_rejects_invalid_ids(
    tmp_path: Path,
) -> None:
    from copy import deepcopy

    from llm3_controlled_evaluation import (
        run_controlled_evaluation,
        summarize_experience_comparison,
    )

    results = run_controlled_evaluation(
        output_dir=tmp_path, case_set="experience"
    )["results"]
    construct = "attitude_toward_the_behavior"
    positive_items = results[0]["state_assessment_item_scores"][construct]["items"]
    neutral_items = results[1]["state_assessment_item_scores"][construct]["items"]
    positive_items[0]["score"], positive_items[1]["score"] = 4.0, 3.0
    neutral_items[0]["score"], neutral_items[1]["score"] = 1.0, 2.0
    neutral_items.reverse()

    differences = summarize_experience_comparison(results)["comparisons"][
        "positive_vs_neutral"
    ][construct]["item_score_differences"]
    assert differences[f"{construct}_q1"] == pytest.approx(3.0)
    assert differences[f"{construct}_q2"] == pytest.approx(1.0)

    for corruption, error in (
        (None, "Missing question_id"),
        ("other_q1", "Item IDs mismatch"),
        (f"{construct}_q2", "Duplicate question_id"),
    ):
        invalid = deepcopy(results)
        item = invalid[0]["state_assessment_item_scores"][construct]["items"][0]
        if corruption is None:
            item.pop("question_id")
        else:
            item["question_id"] = corruption
        with pytest.raises(ValueError, match=error):
            summarize_experience_comparison(invalid)


def _eight_day_context(scenario: str, day_index: int) -> dict:
    from constraints.illness import AcuteIllnessConstraint
    from schedule_model_student import ActivityType, BlockFlexibility, DayEpisode

    activity_types = (
        [ActivityType.SLEEP] * 8
        + [ActivityType.WORK] * 10
        + [ActivityType.DOWNTIME] * 2
        + [ActivityType.SOCIAL_TIME] * 2
        + [ActivityType.SLEEP] * 2
    )
    stressed = scenario == "work_stress" and 2 <= day_index <= 4
    if stressed:
        for hour in range(18, 22 if day_index < 4 else 21):
            activity_types[hour] = ActivityType.WORK
        if day_index == 4:
            activity_types[21] = ActivityType.DOWNTIME

    illness = AcuteIllnessConstraint(duration_days=3, start_weekday=2, intensity="low")
    episodes = [
        DayEpisode(
            hour,
            activity_type,
            BlockFlexibility.FIXED,
            "paid_work" if activity_type == ActivityType.WORK else None,
        )
        for hour, activity_type in enumerate(activity_types)
    ]
    ill = scenario == "illness" and 2 <= day_index <= 4
    if ill:
        assert illness.is_active_on_weekday(day_index)
        episodes = illness.apply(episodes, day_index)

    return {
        "seed": 11,
        "hourly_context_24h": [
            {
                "hour": episode.hour,
                "activity_type": episode.activity_type.value,
                "subtype": episode.subtype,
                "energy_category": "low" if ill else "medium",
                "active_constraints": (
                    [{"type": "AcuteIllnessConstraint", "name": illness.name, "intensity": illness.intensity}]
                    if ill else []
                ),
            }
            for episode in episodes
        ],
    }


def _eight_day_results(scenario: str) -> list[dict]:
    from empirical_pa_v1_2_stochastic import sample_final_decision
    from llm3_controlled_evaluation import (
        SyntheticLLM3Case,
        build_llm3_payload_from_construct_scores,
        evaluate_case_payload,
        prompt_sha256,
        render_case_prompt,
        synthetic_initial_values,
    )
    from state_assessment import ACTIVE_CONSTRUCTS, load_state_assessment_prompt

    persona_id = "Synthetic_Kai6_Comparison"
    policy = {
        "do_planned_activity": 0.0,
        "adapt_activity": 0.0,
        "skip_activity": 0.1,
        "extra_activity": 0.9,
    }
    previous_values = synthetic_initial_values()
    history: list[dict] = []
    template = load_state_assessment_prompt()
    prompt_hash = prompt_sha256(template)
    rows = []
    for day_index in range(8):
        context = _eight_day_context(scenario, day_index)
        hourly = context["hourly_context_24h"]
        has_downtime = any(hour["activity_type"] == "downtime" for hour in hourly)
        stressed = scenario == "work_stress" and 2 <= day_index <= 4
        ill = scenario == "illness" and 2 <= day_index <= 4
        probability = 0.6 if stressed else 0.4 if ill else 0.9
        start_hour = 21 if stressed and day_index == 4 else 18
        assessment = {
            "persona_id": persona_id,
            "day_index": day_index,
            "contextual_pa_probability": probability,
            "activity_if_performed": (
                {
                    "start_hour": start_hour,
                    "duration_min": 45,
                    "activity_option": None,
                    "rationale_short": "Synthetische Aktivitätsoption im freien Zeitfenster.",
                    "diary_entry": "Nach dem Tagesprogramm war ich 45 Minuten spazieren.",
                }
                if has_downtime else None
            ),
            "no_activity_if_skipped": {
                "rationale_short": "Heute fand keine zusätzliche PA statt; ein Grund ist nicht belegt.",
                "diary_entry": "Heute fand keine zusätzliche körperliche Aktivität statt.",
            },
        }
        pa_input = {
            "persona_id": persona_id,
            "day_index": day_index,
            "behavior_policy": policy,
            "daily_context": context,
        }
        sampled = sample_final_decision(assessment, pa_decision_input=pa_input)
        assert sampled == sample_final_decision(assessment, pa_decision_input=pa_input)

        intervention = scenario == "interrupted" and 2 <= day_index <= 4
        selected = (
            {
                "decision_label": "skip_activity",
                "start_hour": None,
                "duration_min": 0,
                "diary_entry": assessment["no_activity_if_skipped"]["diary_entry"],
            }
            if intervention else sampled
        )
        outcome_source = (
            "controlled_synthetic_intervention" if intervention else "bernoulli_sampling"
        )
        case = SyntheticLLM3Case(
            case_id=f"Kai6__{scenario}__day_{day_index:02d}",
            scenario_id=f"Kai6_{scenario}",
            variant_id="main",
            scenario_label=scenario,
            manipulation=outcome_source,
            persona_id=persona_id,
            day_index=day_index,
            previous_normalized_values=dict(previous_values),
            current_decision_label=selected["decision_label"],
            current_simulated_diary_entry=selected["diary_entry"],
            previous_diary_entries=history[-7:].copy(),
            was_physical_activity_planned_today=False,
            planned_physical_activity_summary=None,
            pa_decision=dict(selected),
            daily_context=context,
        )
        prompt = render_case_prompt(
            case, prompt_template=template, previous_values=previous_values,
        )
        payload = build_llm3_payload_from_construct_scores(
            persona_id=persona_id,
            day_index=day_index,
            scores_by_construct={construct: None for construct in ACTIVE_CONSTRUCTS},
        )
        evaluation = evaluate_case_payload(
            case,
            previous_values=previous_values,
            payload=payload,
            rendered_prompt=prompt,
            prompt_hash=prompt_hash,
        )
        rows.append({
            "context": context,
            "assessment": assessment,
            "sampled": sampled,
            "selected": selected,
            "outcome_source": outcome_source,
            "evaluation": evaluation,
        })
        previous_values = evaluation["psychological_construct_values_after_state_assessment"]
        history.append({
            "day_index": day_index,
            "diary_entry": selected["diary_entry"],
            "physical_activity_decision": selected["decision_label"],
            "planned_physical_activity": None,
        })
    return rows


@pytest.mark.parametrize("scenario", ["stable", "work_stress", "illness", "interrupted"])
def test_kai6_eight_day_synthetic_interruption_and_feedback(scenario: str) -> None:
    from empirical_pa_v1_2_stochastic import activity_fits_downtime_block
    from llm3_controlled_evaluation import synthetic_initial_values
    from state_assessment import ACTIVE_CONSTRUCTS

    rows = _eight_day_results(scenario)
    assert len(rows) == 8
    assert rows[0]["evaluation"]["psychological_construct_values_before_state_assessment"] == (
        synthetic_initial_values()
    )
    for day_index, row in enumerate(rows):
        sampled = row["sampled"]
        selected = row["selected"]
        result = row["evaluation"]
        case = result["case"]
        blocks = sampled["pa_time_allocation"]["available_downtime_blocks"]
        assert sampled["behavior_policy_pa_prior"] == pytest.approx(0.9)
        assert sampled["contextual_pa_probability"] == row["assessment"]["contextual_pa_probability"]
        assert sampled["decision_sampling_seed"] == rows[0]["sampled"]["decision_sampling_seed"] + day_index
        assert sampled["decision_label"] == (
            "extra_activity" if sampled["decision_sampling_random_value"] < sampled["effective_pa_probability"]
            else "skip_activity"
        )
        assert sampled["effective_pa_probability"] == (
            sampled["contextual_pa_probability"] if blocks else 0.0
        )
        assert sampled["pa_time_allocation"]["time_allocation_feasible"] == bool(blocks)
        if sampled["decision_label"] == "extra_activity":
            assert activity_fits_downtime_block(
                start_hour=sampled["start_hour"],
                duration_min=sampled["duration_min"],
                available_blocks=blocks,
            )
        assert case["current_simulated_diary_entry"] == selected["diary_entry"]
        assert case["current_decision_label"] == selected["decision_label"]
        assert case["manipulation"] == row["outcome_source"]
        assert case["pa_decision"] == selected
        assert selected["diary_entry"] in result["rendered_prompt"]
        assert case["previous_diary_entries"] == [
            {
                "day_index": earlier,
                "diary_entry": rows[earlier]["selected"]["diary_entry"],
                "physical_activity_decision": rows[earlier]["selected"]["decision_label"],
                "planned_physical_activity": None,
            }
            for earlier in range(max(0, day_index - 7), day_index)
        ]
        assert case["was_physical_activity_planned_today"] is False
        assert case["planned_physical_activity_summary"] is None
        for construct in ACTIVE_CONSTRUCTS:
            items = result["state_assessment_item_scores"][construct]["items"]
            assert all(item["score"] is None and item["evidence_spans"] == [] for item in items)
            assert result["state_assessment_target_values_normalized"][construct] is None
            assert result["psychological_construct_update_delta_applied"][construct] == 0.0
        assert result["psychological_construct_values_after_state_assessment"] == (
            result["psychological_construct_values_before_state_assessment"]
        )
        if day_index:
            assert result["psychological_construct_values_before_state_assessment"] == (
                rows[day_index - 1]["evaluation"]["psychological_construct_values_after_state_assessment"]
            )
        if row["outcome_source"] == "bernoulli_sampling":
            assert selected is sampled
        else:
            assert row["outcome_source"] == "controlled_synthetic_intervention"

    assert all(row["selected"]["decision_label"] == "extra_activity" for row in rows[:2])
    assert all(row["selected"]["decision_label"] == "extra_activity" for row in rows[5:])
    if scenario == "stable":
        assert all(row["selected"]["decision_label"] == "extra_activity" for row in rows)
    elif scenario == "work_stress":
        for row in rows[2:4]:
            assert sum(hour["activity_type"] == "work" for hour in row["context"]["hourly_context_24h"]) == 14
            assert row["sampled"]["effective_pa_probability"] == 0.0
            assert row["selected"]["decision_label"] == "skip_activity"
            assert row["sampled"]["pa_time_allocation"]["infeasibility_reason"] == "no_downtime_block_available"
        assert len(rows[4]["sampled"]["pa_time_allocation"]["available_downtime_blocks"]) == 1
        assert rows[4]["sampled"]["pa_time_allocation"]["available_downtime_blocks"][0]["duration_min"] == 60
        assert sum(hour["activity_type"] == "work" for hour in rows[4]["context"]["hourly_context_24h"]) == 13
        assert rows[4]["sampled"]["effective_pa_probability"] == pytest.approx(0.6)
        assert rows[5]["sampled"]["effective_pa_probability"] == pytest.approx(0.9)
    elif scenario == "illness":
        for row in rows[2:5]:
            reference = row["context"]["hourly_context_24h"][18]
            assert reference["energy_category"] == "low"
            assert reference["active_constraints"][0]["type"] == "AcuteIllnessConstraint"
            assert row["sampled"]["effective_pa_probability"] == pytest.approx(0.4)
            assert "physical_constraint" in row["sampled"]["contextual_response"]["barriers_present"]
            assert row["context"]["hourly_context_24h"][21]["activity_type"] == "downtime"
        assert rows[3]["selected"]["decision_label"] == "extra_activity"
        assert rows[5]["context"]["hourly_context_24h"][18]["active_constraints"] == []
        assert rows[5]["context"]["hourly_context_24h"][21]["activity_type"] == "social_time"
    else:
        for row in rows[2:5]:
            assert row["sampled"]["decision_label"] == "extra_activity"
            assert row["selected"]["decision_label"] == "skip_activity"
            assert row["outcome_source"] == "controlled_synthetic_intervention"
            assert row["sampled"]["effective_pa_probability"] == pytest.approx(0.9)
        assert all(row["outcome_source"] == "bernoulli_sampling" for row in rows[:2] + rows[5:])


def test_kai6_bounded_update_parameters_remain_unchanged() -> None:
    from llm3_controlled_evaluation import synthetic_initial_values
    from state_assessment import (
        ACTIVE_CONSTRUCTS,
        PSYCHOLOGICAL_CONSTRUCT_UPDATE_ALPHA,
        PSYCHOLOGICAL_CONSTRUCT_UPDATE_MAX_DAILY_CHANGE,
        apply_smoothed_bounded_construct_update,
    )

    assert PSYCHOLOGICAL_CONSTRUCT_UPDATE_ALPHA == 0.20
    assert PSYCHOLOGICAL_CONSTRUCT_UPDATE_MAX_DAILY_CHANGE == 0.10
    before = synthetic_initial_values()
    before["action_planning"] = 0.0
    raw = {construct: None for construct in ACTIVE_CONSTRUCTS}
    targets = dict(raw)
    raw["action_planning"] = 7.0
    targets["action_planning"] = 1.0
    update = apply_smoothed_bounded_construct_update(before, targets, raw)
    assert update["delta_proposed"]["action_planning"] == pytest.approx(0.20)
    assert update["delta_applied"]["action_planning"] == pytest.approx(0.10)
    assert update["updated_values"]["action_planning"] == pytest.approx(0.10)
    assert all(update["updated_values"][construct] == before[construct] for construct in ACTIVE_CONSTRUCTS if construct != "action_planning")
