from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from psychological_state import BACKEND_CONSTRUCT_RANGES
from state_assessment import (
    ACTIVE_CONSTRUCTS,
    CONSTRUCT_ITEM_COUNTS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL_NAME,
    DEFAULT_PROMPT_PATH,
    PSYCHOLOGICAL_CONSTRUCT_UPDATE_ALPHA,
    PSYCHOLOGICAL_CONSTRUCT_UPDATE_MAX_DAILY_CHANGE,
    load_state_assessment_prompt,
    normalize_mean_scores,
    parse_state_assessment_json,
    render_state_assessment_prompt,
    validate_state_assessment_output,
    apply_smoothed_bounded_construct_update,
)

SIMULATION_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SIMULATION_DIR / "output" / "llm3_controlled_evaluation"
DEFAULT_TEMPERATURE = 0.0
DEFAULT_TOP_P = 1.0

IMPLEMENTED_DRY_RUN_METRICS: tuple[str, ...] = (
    "null_fraction_per_construct",
    "raw_mean_score_per_construct",
    "target_normalized_value_per_construct",
    "smoothed_normalized_value_change",
    "absolute_daily_change",
    "scenario_variant_cumulative_delta",
    "scenario_variant_max_abs_daily_delta",
)

PLANNED_LIVE_EVALUATION_METRICS: tuple[str, ...] = (
    "between_scenario_differences",
    "neutral_vs_interpretive_diary_differences",
    "regular_pa_vs_habit_evidence_automaticity_difference",
    "repeat_run_consistency",
)

INTERPRETATION_NOTES: tuple[str, ...] = (
    "Day 0 supports controlled single-day comparisons because psychological "
    "starting values and diary history are identical within comparison pairs.",
    "From day 1 onward, psychological states and diary histories may diverge as "
    "a consequence of the condition-specific feedback path.",
    "Seven-day differences are total effects of the simulated feedback path, not "
    "isolated effects of the current-day diary text.",
    "Mock dry-run results are technical checks and must not be interpreted as "
    "empirical LLM3 behavior.",
)

PROMPT_HISTORY_SUMMARY_NOTE = (
    "previous_diary_entries are passed verbatim; no synthetic summary is generated. "
    "This matches the production path when previous_diary_entries_summary is omitted."
)


@dataclass(frozen=True)
class SyntheticLLM3Case:
    case_id: str
    scenario_id: str
    variant_id: str
    scenario_label: str
    manipulation: str
    persona_id: str
    day_index: int
    previous_normalized_values: dict[str, float]
    current_decision_label: str
    current_simulated_diary_entry: str
    previous_diary_entries: list[dict[str, Any]]
    was_physical_activity_planned_today: bool
    planned_physical_activity_summary: dict[str, Any] | None
    pa_decision: dict[str, Any]
    daily_context: dict[str, Any] | None = None


def synthetic_initial_values() -> dict[str, float]:
    values = {construct: 0.50 for construct in ACTIVE_CONSTRUCTS}
    values.update(
        {
            "intention": 0.85,
            "intrinsic_motivation": 0.85,
            "attitude_toward_the_behavior": 0.75,
            "perceived_behavioral_control": 0.70,
            "action_planning": 0.60,
        }
    )
    return values


def _pa_decision(day_index: int, *, performed: bool) -> dict[str, Any]:
    if performed:
        return {
            "day_index": day_index,
            "decision_label": "extra_activity",
            "start_hour": 18,
            "duration_min": 45,
            "activity_performed": True,
        }
    return {
        "day_index": day_index,
        "decision_label": "skip_activity",
        "start_hour": None,
        "duration_min": 0,
        "activity_performed": False,
        "infeasibility_reason": "no_downtime_block_available",
    }


def _diary_text(scenario_id: str, variant_id: str, day_index: int) -> str:
    day = day_index + 1
    if scenario_id == "A_time_shortage":
        return (
            f"Day {day}: I wanted to be physically active and still felt motivated, "
            "but the day contained no open time block for PA."
        )
    if scenario_id == "B_regular_pa":
        return (
            f"Day {day}: I used the open 18:00 slot for 45 minutes of physical "
            "activity. The entry only records that the activity happened."
        )
    if scenario_id == "C_habit_instigation":
        return (
            f"Day {day}: When the open 18:00 slot arrived, I started the 45-minute "
            "activity with little deliberation and noticed the initiation felt more "
            "automatic than before."
        )
    if scenario_id == "D_diary_feedback" and variant_id == "neutral":
        return (
            f"Day {day}: I completed 45 minutes of physical activity at 18:00. "
            "This is a neutral observation of the behaviour."
        )
    if scenario_id == "D_diary_feedback" and variant_id == "interpretive":
        return (
            f"Day {day}: I completed 45 minutes of physical activity at 18:00 and "
            "felt motivated, enjoyed it, and started almost automatically."
        )
    if scenario_id == "E_selective_evidence":
        return (
            f"Day {day}: I made a clearer plan for what activity to do, where to "
            "do it, which day to use, and how long it should last. The entry gives "
            "no new information about other people or automatic initiation."
        )
    raise ValueError(f"Unknown synthetic scenario/variant: {scenario_id}/{variant_id}.")


def _history_entry(case: SyntheticLLM3Case) -> dict[str, Any]:
    return {
        "day_index": case.day_index,
        "diary_entry": case.current_simulated_diary_entry,
        "physical_activity_decision": case.current_decision_label,
        "planned_physical_activity": case.planned_physical_activity_summary,
    }


def _persona_id_for_scenario(scenario_id: str, variant_id: str) -> str:
    del variant_id
    if scenario_id in {"B_regular_pa", "C_habit_instigation"}:
        return "SyntheticLLM3_regular_pa_habit_comparison"
    if scenario_id == "D_diary_feedback":
        return "SyntheticLLM3_diary_feedback_comparison"
    return f"SyntheticLLM3_{scenario_id}"


def build_synthetic_cases(days: int = 7) -> list[SyntheticLLM3Case]:
    if days < 1:
        raise ValueError("days must be at least 1.")
    scenarios = [
        (
            "A_time_shortage",
            "main",
            "Scenario A: time shortage",
            "No downtime despite high intention and motivation.",
            False,
        ),
        (
            "B_regular_pa",
            "main",
            "Scenario B: regular PA",
            "Regular PA without diary claims about habit formation.",
            True,
        ),
        (
            "C_habit_instigation",
            "main",
            "Scenario C: habit instigation",
            "Same PA path as B with concrete automatic-initiation evidence.",
            True,
        ),
        (
            "D_diary_feedback",
            "neutral",
            "Scenario D: neutral diary",
            "Same PA path and structured context; neutral diary wording.",
            True,
        ),
        (
            "D_diary_feedback",
            "interpretive",
            "Scenario D: interpretive diary",
            "Same PA path and structured context; interpretive diary wording.",
            True,
        ),
        (
            "E_selective_evidence",
            "main",
            "Scenario E: selective evidence",
            "Diary evidence targets action planning only.",
            True,
        ),
    ]
    cases: list[SyntheticLLM3Case] = []
    for scenario_id, variant_id, label, manipulation, performed in scenarios:
        persona_id = _persona_id_for_scenario(scenario_id, variant_id)
        history: list[dict[str, Any]] = []
        for day_index in range(days):
            decision = _pa_decision(day_index, performed=performed)
            case = SyntheticLLM3Case(
                case_id=f"{scenario_id}__{variant_id}__day_{day_index:02d}",
                scenario_id=scenario_id,
                variant_id=variant_id,
                scenario_label=label,
                manipulation=manipulation,
                persona_id=persona_id,
                day_index=day_index,
                previous_normalized_values=synthetic_initial_values(),
                current_decision_label=str(decision["decision_label"]),
                current_simulated_diary_entry=_diary_text(
                    scenario_id,
                    variant_id,
                    day_index,
                ),
                previous_diary_entries=deepcopy(history),
                was_physical_activity_planned_today=False,
                planned_physical_activity_summary=None,
                pa_decision=decision,
            )
            cases.append(case)
            history.append(_history_entry(case))
    return cases


EXPERIENCE_DIARIES: dict[str, str] = {
    "positive": (
        "Ich war heute 30 Minuten joggen. Die Bewegung hat mir Freude gemacht "
        "und ich fühlte mich danach wohl."
    ),
    "neutral": "Ich war heute 30 Minuten joggen.",
    "negative": (
        "Ich war heute 30 Minuten joggen. Die Bewegung war unangenehm "
        "und ich fühlte mich danach unwohl."
    ),
}

EXPERIENCE_INTERPRETATION_NOTES: tuple[str, ...] = (
    "The three single-day conditions share persona, baseline, history, decision, "
    "and synthetic day context; only diary experience wording differs.",
    "Diary emotions are experimentally specified synthetic statements, not "
    "independently measured experiences.",
    "Mock responses check data flow and arithmetic, not semantic LLM3 behavior.",
)

EXPERIENCE_LIVE_METRICS: tuple[str, ...] = (
    "item_scores_and_nulls_by_condition",
    "evidence_spans_by_condition",
    "positive_neutral_negative_raw_and_normalized_differences",
    "positive_neutral_negative_bounded_update_differences",
)


def build_experience_cases() -> list[SyntheticLLM3Case]:
    """Single-day synthetic comparison; only the diary experience wording varies."""
    baseline = {construct: 0.50 for construct in ACTIVE_CONSTRUCTS}
    decision = {
        "day_index": 0,
        "decision_label": "extra_activity",
        "start_hour": 18,
        "duration_min": 30,
        "activity_form": "jogging",
        "activity_performed": True,
    }
    context = {"available_time_window": {"start_hour": 18, "end_hour": 19}}
    return [
        SyntheticLLM3Case(
            case_id=f"F_pa_experience__{variant_id}__day_00",
            scenario_id="F_pa_experience",
            variant_id=variant_id,
            scenario_label=f"PA experience: {variant_id}",
            manipulation="Only the synthetic subjective-experience statement varies.",
            persona_id="SyntheticLLM3_pa_experience_comparison",
            day_index=0,
            previous_normalized_values=deepcopy(baseline),
            current_decision_label="extra_activity",
            current_simulated_diary_entry=diary,
            previous_diary_entries=[],
            was_physical_activity_planned_today=False,
            planned_physical_activity_summary=None,
            pa_decision=deepcopy(decision),
            daily_context=deepcopy(context),
        )
        for variant_id, diary in EXPERIENCE_DIARIES.items()
    ]


def load_synthetic_cases(path: Path | None = None) -> list[SyntheticLLM3Case]:
    if path is None:
        return build_synthetic_cases()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Synthetic scenario file must contain a JSON list.")
    return [SyntheticLLM3Case(**item) for item in payload]


def prompt_sha256(prompt_template: str) -> str:
    return hashlib.sha256(prompt_template.encode("utf-8")).hexdigest()


def render_case_prompt(
    case: SyntheticLLM3Case,
    *,
    prompt_template: str | None = None,
    previous_values: Mapping[str, float] | None = None,
) -> str:
    template = prompt_template if prompt_template is not None else load_state_assessment_prompt()
    return render_state_assessment_prompt(
        template,
        persona_id=case.persona_id,
        day_index=case.day_index,
        previous_psychological_construct_values=(
            previous_values if previous_values is not None else case.previous_normalized_values
        ),
        current_simulated_diary_entry=case.current_simulated_diary_entry,
        previous_diary_entries=case.previous_diary_entries,
        current_decision_label=case.current_decision_label,
        was_physical_activity_planned_today=case.was_physical_activity_planned_today,
        planned_physical_activity_summary=case.planned_physical_activity_summary,
        previous_diary_entries_summary=None,
    )


def mock_llm3_payload_for_case(case: SyntheticLLM3Case) -> dict[str, Any]:
    scores: dict[str, float | None] = {construct: None for construct in ACTIVE_CONSTRUCTS}
    if case.scenario_id == "C_habit_instigation":
        scores["automaticity"] = 6.0
    elif case.scenario_id == "D_diary_feedback" and case.variant_id == "interpretive":
        scores["automaticity"] = 6.0
        scores["intrinsic_motivation"] = 3.5
    elif case.scenario_id == "E_selective_evidence":
        scores["action_planning"] = 6.0
    return build_llm3_payload_from_construct_scores(
        persona_id=case.persona_id,
        day_index=case.day_index,
        scores_by_construct=scores,
    )


def build_llm3_payload_from_construct_scores(
    *,
    persona_id: str,
    day_index: int,
    scores_by_construct: Mapping[str, float | None],
) -> dict[str, Any]:
    item_scores: dict[str, Any] = {}
    for construct in ACTIVE_CONSTRUCTS:
        low, high = BACKEND_CONSTRUCT_RANGES[construct]
        score = scores_by_construct.get(construct)
        item_scores[construct] = {
            "items": [
                {
                    "question_id": f"{construct}_q{index}",
                    "score": score,
                    "range": f"{low:g}-{high:g}",
                    "evidence_spans": [] if score is None else ["synthetic evidence"],
                    "reasoning_short": "" if score is None else "synthetic mock response",
                }
                for index in range(1, CONSTRUCT_ITEM_COUNTS[construct] + 1)
            ],
            "mean_score": score,
        }
    return {
        "persona_id": persona_id,
        "day_index": day_index,
        "item_scores": item_scores,
        "metadata": {"source": "synthetic_mock"},
    }


def evaluate_case_payload(
    case: SyntheticLLM3Case,
    *,
    previous_values: Mapping[str, float],
    payload: Mapping[str, Any],
    rendered_prompt: str,
    prompt_hash: str,
) -> dict[str, Any]:
    validated = validate_state_assessment_output(
        payload,
        expected_persona_id=case.persona_id,
        expected_day_index=case.day_index,
    )
    target_normalized = normalize_mean_scores(
        validated["mean_scores_raw"],
        previous_values,
    )
    visible_targets = {
        construct: (
            None
            if validated["mean_scores_raw"][construct] is None
            else target_normalized[construct]
        )
        for construct in ACTIVE_CONSTRUCTS
    }
    update = apply_smoothed_bounded_construct_update(
        previous_values,
        visible_targets,
        validated["mean_scores_raw"],
    )
    return {
        "case": asdict(case),
        "prompt_sha256": prompt_hash,
        "rendered_prompt": rendered_prompt,
        "llm_response_mode": "synthetic_mock_or_recorded_payload",
        "state_assessment_item_scores": validated["item_scores"],
        "state_assessment_mean_scores_raw": validated["mean_scores_raw"],
        "state_assessment_mean_scores_normalized": target_normalized,
        "state_assessment_target_values_normalized": visible_targets,
        "psychological_construct_values_before_state_assessment": dict(previous_values),
        "psychological_construct_update_delta_proposed": update["delta_proposed"],
        "psychological_construct_update_delta_applied": update["delta_applied"],
        "psychological_construct_values_after_state_assessment": update["updated_values"],
        "construct_metrics": construct_metrics(
            validated["item_scores"],
            validated["mean_scores_raw"],
            visible_targets,
            previous_values,
            update["updated_values"],
        ),
    }


def evaluate_case_raw_response(
    case: SyntheticLLM3Case,
    *,
    previous_values: Mapping[str, float],
    raw_response: str,
    rendered_prompt: str,
    prompt_hash: str,
) -> dict[str, Any]:
    payload = parse_state_assessment_json(raw_response)
    return evaluate_case_payload(
        case,
        previous_values=previous_values,
        payload=payload,
        rendered_prompt=rendered_prompt,
        prompt_hash=prompt_hash,
    )


def construct_metrics(
    item_scores: Mapping[str, Any],
    raw_means: Mapping[str, float | None],
    target_values: Mapping[str, float | None],
    before_values: Mapping[str, float],
    after_values: Mapping[str, float],
) -> dict[str, dict[str, float | None]]:
    metrics: dict[str, dict[str, float | None]] = {}
    for construct in ACTIVE_CONSTRUCTS:
        items = item_scores[construct]["items"]
        null_count = sum(1 for item in items if item["score"] is None)
        item_count = len(items)
        before = float(before_values[construct])
        after = float(after_values[construct])
        delta = after - before
        metrics[construct] = {
            "item_count": float(item_count),
            "null_item_count": float(null_count),
            "null_fraction": null_count / item_count,
            "raw_mean_score": raw_means[construct],
            "target_normalized_value": target_values[construct],
            "value_before": before,
            "value_after": after,
            "delta": delta,
            "abs_delta": abs(delta),
        }
    return metrics


def summarize_results(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    scenario_summaries: dict[str, Any] = {}
    for result in results:
        case = result["case"]
        key = f"{case['scenario_id']}__{case['variant_id']}"
        summary = scenario_summaries.setdefault(
            key,
            {
                "scenario_id": case["scenario_id"],
                "variant_id": case["variant_id"],
                "days": 0,
                "constructs": {
                    construct: {
                        "mean_null_fraction": 0.0,
                        "cumulative_delta": 0.0,
                        "max_abs_daily_delta": 0.0,
                    }
                    for construct in ACTIVE_CONSTRUCTS
                },
            },
        )
        summary["days"] += 1
        for construct, metrics in result["construct_metrics"].items():
            construct_summary = summary["constructs"][construct]
            construct_summary["mean_null_fraction"] += float(metrics["null_fraction"])
            construct_summary["cumulative_delta"] += float(metrics["delta"])
            construct_summary["max_abs_daily_delta"] = max(
                construct_summary["max_abs_daily_delta"],
                float(metrics["abs_delta"]),
            )
    for summary in scenario_summaries.values():
        days = max(int(summary["days"]), 1)
        for construct_summary in summary["constructs"].values():
            construct_summary["mean_null_fraction"] /= days
    return {
        "implemented_dry_run_metrics": list(IMPLEMENTED_DRY_RUN_METRICS),
        "planned_live_evaluation_metrics": list(PLANNED_LIVE_EVALUATION_METRICS),
        "interpretation_notes": list(INTERPRETATION_NOTES),
        "prompt_history_summary_note": PROMPT_HISTORY_SUMMARY_NOTE,
        "scenario_summaries": scenario_summaries,
        "notes": [
            "Raw LLM3 estimates and smoothed state updates are stored separately.",
            "No thresholds for psychologically correct changes are defined here.",
            "Mock dry-run summaries do not contain observed LLM3 effects.",
        ],
    }


def summarize_experience_comparison(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_variant = {result["case"]["variant_id"]: result for result in results}
    if set(by_variant) != set(EXPERIENCE_DIARIES) or len(results) != 3:
        raise ValueError("Experience comparison requires exactly three distinct conditions.")

    def difference(first: float | None, second: float | None) -> float | None:
        return None if first is None or second is None else first - second

    def items_by_question_id(
        items: Sequence[Mapping[str, Any]], construct: str
    ) -> dict[str, Mapping[str, Any]]:
        expected_ids = {
            f"{construct}_q{index}"
            for index in range(1, CONSTRUCT_ITEM_COUNTS[construct] + 1)
        }
        by_id: dict[str, Mapping[str, Any]] = {}
        for item in items:
            question_id = item.get("question_id")
            if not isinstance(question_id, str) or not question_id:
                raise ValueError(f"Missing question_id in {construct} comparison.")
            if question_id in by_id:
                raise ValueError(f"Duplicate question_id {question_id!r} in {construct} comparison.")
            by_id[question_id] = item
        if set(by_id) != expected_ids:
            raise ValueError(
                f"Item IDs mismatch in {construct} comparison: "
                f"missing={sorted(expected_ids - set(by_id))}, "
                f"unexpected={sorted(set(by_id) - expected_ids)}."
            )
        return by_id

    comparisons: dict[str, Any] = {}
    for first_id, second_id in (
        ("positive", "neutral"),
        ("negative", "neutral"),
        ("positive", "negative"),
    ):
        first, second = by_variant[first_id], by_variant[second_id]
        constructs: dict[str, Any] = {}
        for construct in ACTIVE_CONSTRUCTS:
            first_items = items_by_question_id(
                first["state_assessment_item_scores"][construct]["items"], construct
            )
            second_items = items_by_question_id(
                second["state_assessment_item_scores"][construct]["items"], construct
            )
            constructs[construct] = {
                "item_score_differences": {
                    question_id: difference(item["score"], second_items[question_id]["score"])
                    for question_id, item in first_items.items()
                },
                "null_item_count_difference": (
                    first["construct_metrics"][construct]["null_item_count"]
                    - second["construct_metrics"][construct]["null_item_count"]
                ),
                "raw_mean_difference": difference(
                    first["state_assessment_mean_scores_raw"][construct],
                    second["state_assessment_mean_scores_raw"][construct],
                ),
                "normalized_target_difference": difference(
                    first["state_assessment_target_values_normalized"][construct],
                    second["state_assessment_target_values_normalized"][construct],
                ),
                "applied_update_difference": (
                    first["psychological_construct_update_delta_applied"][construct]
                    - second["psychological_construct_update_delta_applied"][construct]
                ),
            }
        comparisons[f"{first_id}_vs_{second_id}"] = constructs
    return {
        "interpretation": (
            "Differences describe supplied responses only; mock differences are not "
            "evidence of semantic LLM3 behavior."
        ),
        "comparisons": comparisons,
    }


def run_controlled_evaluation(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    dry_run: bool = True,
    model: str = DEFAULT_MODEL_NAME,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P,
    llm_seed: int | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    case_set: str = "existing",
    mock_payload_builder: Callable[[SyntheticLLM3Case], Mapping[str, Any]] = (
        mock_llm3_payload_for_case
    ),
) -> dict[str, Any]:
    if not dry_run:
        raise RuntimeError(
            "Live LLM3 calls are intentionally disabled in the controlled evaluation "
            "helper. Record explicit live responses separately and evaluate them with "
            "evaluate_case_raw_response()."
        )

    if case_set not in {"existing", "experience"}:
        raise ValueError("case_set must be 'existing' or 'experience'.")

    prompt_template = load_state_assessment_prompt()
    prompt_hash = prompt_sha256(prompt_template)
    output_dir.mkdir(parents=True, exist_ok=True)

    cases = build_experience_cases() if case_set == "experience" else load_synthetic_cases()
    previous_values_by_variant: dict[str, dict[str, float]] = {}
    results: list[dict[str, Any]] = []
    for case in cases:
        variant_key = f"{case.scenario_id}__{case.variant_id}"
        previous_values = previous_values_by_variant.setdefault(
            variant_key,
            dict(case.previous_normalized_values),
        )
        rendered_prompt = render_case_prompt(
            case,
            prompt_template=prompt_template,
            previous_values=previous_values,
        )
        payload = mock_payload_builder(case)
        result = evaluate_case_payload(
            case,
            previous_values=previous_values,
            payload=payload,
            rendered_prompt=rendered_prompt,
            prompt_hash=prompt_hash,
        )
        results.append(result)
        previous_values_by_variant[variant_key] = result[
            "psychological_construct_values_after_state_assessment"
        ]

    summary = summarize_results(results)
    if case_set == "experience":
        summary["interpretation_notes"] = list(EXPERIENCE_INTERPRETATION_NOTES)
        summary["planned_live_evaluation_metrics"] = list(EXPERIENCE_LIVE_METRICS)
        summary["experience_comparison"] = summarize_experience_comparison(results)
    comparison_persona_ids = (
        {
            f"F_pa_experience__{variant_id}": "SyntheticLLM3_pa_experience_comparison"
            for variant_id in EXPERIENCE_DIARIES
        }
        if case_set == "experience"
        else {
            "B_regular_pa__main": "SyntheticLLM3_regular_pa_habit_comparison",
            "C_habit_instigation__main": "SyntheticLLM3_regular_pa_habit_comparison",
            "D_diary_feedback__neutral": "SyntheticLLM3_diary_feedback_comparison",
            "D_diary_feedback__interpretive": "SyntheticLLM3_diary_feedback_comparison",
        }
    )
    manifest = {
        "mode": "dry_run_synthetic_mock",
        "api_calls_performed": 0,
        "model": model,
        "temperature": temperature,
        "top_p": top_p,
        "llm_seed": llm_seed,
        "max_tokens": max_tokens,
        "prompt_path": str(DEFAULT_PROMPT_PATH),
        "prompt_sha256": prompt_hash,
        "prompt_character_count": len(prompt_template),
        "active_constructs": list(ACTIVE_CONSTRUCTS),
        "alpha": PSYCHOLOGICAL_CONSTRUCT_UPDATE_ALPHA,
        "max_daily_change": PSYCHOLOGICAL_CONSTRUCT_UPDATE_MAX_DAILY_CHANGE,
        "case_count": len(cases),
        "case_set": case_set,
        "scenario_variant_count": len(previous_values_by_variant),
        "synthetic_only": True,
        "state_isolation_key": "scenario_id__variant_id",
        "comparison_persona_ids": comparison_persona_ids,
        "interpretation_notes": summary["interpretation_notes"],
        "prompt_history_summary_note": PROMPT_HISTORY_SUMMARY_NOTE,
        "implemented_dry_run_metrics": list(IMPLEMENTED_DRY_RUN_METRICS),
        "planned_live_evaluation_metrics": summary["planned_live_evaluation_metrics"],
    }
    if case_set == "experience":
        manifest["experience_evidence_status"] = (
            "experimentally_specified_synthetic_diary_not_independently_measured"
        )
        manifest["live_test_prerequisites"] = [
            "UNI_LLM_API_KEY access to University of Bern GPUStack",
            "authorization and clarified usage costs",
            "explicit approval to submit the three saved prompts",
        ]
    write_json(output_dir / "manifest.json", manifest)
    write_json(output_dir / "summary.json", summary)
    write_jsonl(output_dir / "results.jsonl", results)
    write_jsonl(
        output_dir / "prompts.jsonl",
        [
            {
                "case_id": result["case"]["case_id"],
                "scenario_id": result["case"]["scenario_id"],
                "variant_id": result["case"]["variant_id"],
                "prompt_sha256": result["prompt_sha256"],
                "rendered_prompt": result["rendered_prompt"],
            }
            for result in results
        ],
    )
    return {"manifest": manifest, "summary": summary, "results": results}


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a controlled synthetic dry-run evaluation for LLM3."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--case-set", choices=("existing", "experience"), default="existing")
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--top-p", type=float, default=DEFAULT_TOP_P)
    parser.add_argument("--llm-seed", type=int, default=None)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Reserved for explicit future live evaluations; currently rejected.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    run_controlled_evaluation(
        output_dir=args.output_dir,
        dry_run=not args.live,
        model=args.model,
        temperature=args.temperature,
        top_p=args.top_p,
        llm_seed=args.llm_seed,
        max_tokens=args.max_tokens,
        case_set=args.case_set,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
