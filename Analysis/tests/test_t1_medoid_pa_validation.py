from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Analysis"))

import t1_medoid_pa_validation as validation


def _empirical() -> pd.DataFrame:
    return pd.DataFrame([
        {"cluster": i, "participant_id": str(7000 + i), "persona_id": f"p{i}",
         "occupation": "test", "empirical_mvpa_hours_week": mvpa,
         "empirical_total_pa_hours_week": mvpa + 1}
        for i, mvpa in enumerate([4.0, 3.0, 2.0, 1.0], 1)
    ])


def _trace() -> dict:
    records = []
    decisions = ["do_planned_activity", "adapt_activity", "skip_activity", "extra_activity"]
    for persona in range(1, 5):
        for day in range(90):
            decision = decisions[day % 4]
            planned = decision != "extra_activity"
            performed = decision != "skip_activity"
            records.append({
                "persona_id": f"p{persona}", "calendar_date": f"2026-07-{(day % 28) + 1:02d}",
                "day_index": day, "week_index": day // 7, "phase": "normal", "weekday": day % 7,
                "was_physical_activity_planned_today": planned,
                "planned_physical_activity": {"duration_min": 60} if planned else None,
                "pa_decision": {"decision_label": decision},
                "closed_loop_update": {"activity_done": performed},
                "psychological_constructs_before_update": {}, "psychological_constructs_after_update": {},
            })
    return {"records": records}


def test_calendar_alignment_precondition():
    assert validation.calendar_date_to_schedule_coordinates(validation.START_DATE) == (27, 3)


def test_production_seed_derivation_is_deterministic():
    assert validation.derive_persona_seeds(42) == validation.derive_persona_seeds(42)
    assert len(set(validation.derive_persona_seeds(42))) == 4


def test_seed_search_is_deterministic_and_selected_seed_is_event_free():
    first = validation.select_event_free_seed(max_seed=100)
    second = validation.select_event_free_seed(max_seed=100)
    assert first["selected_base_seed"] == second["selected_base_seed"] == 14
    assert first["derived_persona_seeds"] == second["derived_persona_seeds"]
    assert all(not day["active_event_types"] for persona in first["personas"] for day in persona["days"])


def test_seed_inspection_uses_only_preregistered_context_not_outcomes(monkeypatch):
    # The seed path has no trace/decision/correlation argument or call; make any
    # accidental outcome analysis fail loudly.
    monkeypatch.setattr(validation, "calculate_correlations", lambda *_: pytest.fail("PA inspected"))
    monkeypatch.setattr(validation, "daily_rows_from_trace", lambda *_: pytest.fail("PA inspected"))
    result = validation.inspect_event_free_seed(14)
    assert result["representative_phase_used_for_selection"] is True
    assert result["event_free_used_for_selection"] is True
    assert result["pa_outcomes_used_for_selection"] is False
    assert result["correlations_used_for_selection"] is False
    assert len(result["personas"]) == 4
    for persona in result["personas"]:
        assert len(persona["days"]) == 7
        for day in persona["days"]:
            assert {"phase", "illness_active", "public_holiday_active", "active_event_types"} <= day.keys()
            assert not day["active_event_types"]


def test_selected_seed_matches_every_representative_phase():
    selected = validation.select_event_free_seed(max_seed=100)
    for persona in selected["personas"]:
        assert persona["phase_sequence"] == [persona["representative_phase"]] * 7
    assert selected["valid"] is True


def test_modal_phases_are_derived_from_empirical_counts():
    profiles = validation.load_empirical_personas(validation.DEFAULT_PERSONA_FILE)
    expected = {"7067": "normal", "8153": "normal", "8237": "normal", "8303": "high_stress"}
    for profile in profiles:
        counts, phase = validation.phase_counts_and_representative_phase(profile)
        assert phase == expected[profile.participant_id]
        assert sum(counts.values()) == 52
    c4 = next(profile for profile in profiles if profile.participant_id == "8303")
    assert validation.phase_counts_and_representative_phase(c4)[0] == {
        "normal": 9, "high_stress": 37, "holiday": 6
    }


def test_nested_windows_primary_counts_and_normalization():
    empirical = _empirical()
    daily = validation.daily_rows_from_trace(_trace(), empirical)
    summary = validation.summarize_horizons(daily, empirical)
    assert summary.groupby("horizon_days")["n_days"].unique().map(list).to_dict() == {
        7: [7], 30: [30], 90: [90]
    }
    seven = summary[summary.horizon_days == 7].iloc[0]
    assert seven.active_days == 5
    assert seven.inactive_days == 2
    assert seven.active_days_per_week == 5
    assert seven.normal_days == 7
    assert seven.high_stress_days == 0
    assert seven.holiday_days == 0


def test_decisions_adherence_and_explicit_duration_proxy():
    empirical = _empirical()
    daily = validation.daily_rows_from_trace(_trace(), empirical)
    first_four = daily[(daily.persona_id == "p1") & (daily.day_index < 4)]
    assert first_four.set_index("decision_label")["proxy_realized_planned_minutes"].to_dict() == {
        "do_planned_activity": 60, "adapt_activity": 60, "skip_activity": 0, "extra_activity": 0,
    }
    # In particular, an active extra day never receives invented minutes.
    extra = daily[daily.decision_label == "extra_activity"]
    assert extra.activity_performed.all()
    assert (extra.proxy_realized_planned_minutes == 0).all()
    summary = validation.summarize_horizons(daily, empirical)
    seven = summary[summary.horizon_days == 7].iloc[0]
    assert seven.decision_count_do_planned_activity == 2
    assert seven.decision_count_adapt_activity == 2
    assert seven.decision_count_skip_activity == 2
    assert seven.decision_count_extra_activity == 1
    assert seven.planned_pa_days == 6
    assert seven.successful_planned_pa_days == 4
    assert seven.skipped_planned_pa_days == 2
    assert seven.planned_pa_adherence_rate == pytest.approx(4 / 6)
    assert seven.planned_pa_minutes == 360
    assert seven.scheduled_planned_pa_days == 6
    assert seven.scheduled_planned_pa_days_per_week == 6
    assert seven.scheduled_planned_pa_minutes == 360
    assert seven.scheduled_planned_pa_hours_per_week == 6
    assert seven.realized_planned_pa_minutes_proxy == 240
    assert seven.realized_planned_pa_hours_per_week_proxy == 4
    assert seven.planned_pa_realization_ratio == pytest.approx(2 / 3)
    assert seven.planned_pa_realization_delta_hours_per_week == -2
    assert seven.extra_activity_days_per_week == 1


def test_zero_scheduled_pa_returns_nan_realization_ratio():
    trace = _trace()
    for record in trace["records"]:
        record["was_physical_activity_planned_today"] = False
        record["planned_physical_activity"] = None
        record["pa_decision"]["decision_label"] = "extra_activity"
        record["closed_loop_update"]["activity_done"] = True
    summary = validation.summarize_horizons(
        validation.daily_rows_from_trace(trace, _empirical()), _empirical()
    )
    assert (summary["scheduled_planned_pa_minutes"] == 0).all()
    assert summary["planned_pa_realization_ratio"].isna().all()
    assert (summary["planned_pa_realization_delta_hours_per_week"] == 0).all()


def test_known_four_observation_correlations():
    summary = validation.summarize_horizons(
        validation.daily_rows_from_trace(_trace(), _empirical()), _empirical()
    )
    # Supply a strict matching ordering to exercise the n=4 implementation.
    mask = summary.horizon_days == 7
    summary.loc[mask, "active_days_per_week"] = [4, 3, 2, 1]
    correlations = validation.calculate_correlations(summary[mask])
    primary = correlations[(correlations.role == "primary")].iloc[0]
    assert primary.n_personas == 4
    assert primary.coefficient == pytest.approx(1.0)


def test_correlation_schema_separates_baseline_and_post_decision():
    summary = validation.summarize_horizons(
        validation.daily_rows_from_trace(_trace(), _empirical()), _empirical()
    )
    correlations = validation.calculate_correlations(summary)
    baseline = correlations[correlations.analysis_stage == "pre_decision_input_informed_baseline"]
    post = correlations[correlations.analysis_stage == "post_decision"]
    assert set(baseline.simulated_variable) == {
        "scheduled_planned_pa_hours_per_week", "scheduled_planned_pa_days_per_week"
    }
    assert {"active_days_per_week", "realized_planned_pa_hours_per_week_proxy"} <= set(
        post.simulated_variable
    )


def test_empirical_values_are_read_from_medoid_csv():
    frame = validation.load_empirical_pa()
    assert frame.set_index("participant_id")["empirical_mvpa_hours_week"].to_dict() == {
        "7067": pytest.approx(2.0), "8153": pytest.approx(1.66666666666667),
        "8237": pytest.approx(2.25), "8303": pytest.approx(0.333333333333333),
    }


def test_output_and_report_schemas_are_stable(tmp_path):
    seed = {"selected_base_seed": 1, "derived_persona_seeds": [1, 2, 3, 4], "valid": True}
    persona_file = tmp_path / "personas.csv"
    pd.DataFrame([
        {"cluster": i, "participant_id": str(7000 + i), "occupational_status": "test",
         "pa_mvpa_hours_per_week": mvpa, "pa_total_hours_per_week": mvpa + 1}
        for i, mvpa in enumerate([4.0, 3.0, 2.0, 1.0], 1)
    ]).to_csv(persona_file, index=False)
    trace = _trace()
    for record in trace["records"]:
        number = int(record["persona_id"][1:])
        record["persona_id"] = f"T1_Medoid_C{number}_{7000 + number}"
    validation.write_analysis_outputs(tmp_path, seed, trace, persona_file)
    expected = {
        "01_seed_selection.json", "02_persona_empirical_pa.csv", "03_daily_simulated_pa.csv",
        "04_horizon_persona_summary.csv", "05_horizon_correlations.csv", "06_validation_report.md",
    }
    assert expected <= {path.name for path in tmp_path.iterdir()}
    daily_columns = set(pd.read_csv(tmp_path / "03_daily_simulated_pa.csv").columns)
    assert {
        "persona_id", "cluster", "participant_id", "calendar_date", "day_index", "week_index",
        "phase", "weekday", "was_physical_activity_planned_today", "planned_duration_min",
        "decision_label", "activity_performed", "active_day", "proxy_realized_planned_minutes",
    } <= daily_columns
    summary_columns = set(pd.read_csv(tmp_path / "04_horizon_persona_summary.csv").columns)
    assert {
        "scheduled_planned_pa_days", "scheduled_planned_pa_days_per_week",
        "scheduled_planned_pa_minutes", "scheduled_planned_pa_hours_per_week",
        "planned_pa_realization_ratio", "planned_pa_realization_delta_hours_per_week",
        "extra_activity_days_per_week",
    } <= summary_columns
    report = (tmp_path / "06_validation_report.md").read_text()
    assert "n=4" in report and "PROXY" in report
    assert "internal behavioral reproduction analysis" in report
    assert "cannot be interpreted as independent out-of-sample validation" in report
    metadata = json.loads((tmp_path / "01_seed_selection.json").read_text())
    assert metadata["selected_base_seed"] == 1
