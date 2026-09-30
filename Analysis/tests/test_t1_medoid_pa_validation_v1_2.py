from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "Analysis"
SIMULATION = ROOT / "Simulation"
for path in (ROOT, ANALYSIS, SIMULATION):
    if str(path) not in sys.path:
        sys.path.append(str(path))

from t1_medoid_pa_validation import inspect_event_free_seed
from t1_medoid_pa_validation_v1_2 import (
    START_DATE,
    build_report,
    calculate_correlations,
    daily_rows_from_trace,
    summarize_horizons,
)


MEDOID_FILE = (
    ANALYSIS
    / "results_t1_persona_clustering"
    / "11_primary_medoid_personas.csv"
)


def _empirical() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "cluster": 1,
                "participant_id": "7067",
                "persona_id": "T1_Medoid_C1_7067",
                "occupation": "Studium",
                "empirical_mvpa_hours_week": 2.0,
                "empirical_total_pa_hours_week": 4.6666666667,
            },
            {
                "cluster": 2,
                "participant_id": "8153",
                "persona_id": "T1_Medoid_C2_8153",
                "occupation": "Sonstiges",
                "empirical_mvpa_hours_week": 1.6666666667,
                "empirical_total_pa_hours_week": 8.6666666667,
            },
            {
                "cluster": 3,
                "participant_id": "8237",
                "persona_id": "T1_Medoid_C3_8237",
                "occupation": "Angestellt",
                "empirical_mvpa_hours_week": 2.25,
                "empirical_total_pa_hours_week": 8.25,
            },
            {
                "cluster": 4,
                "participant_id": "8303",
                "persona_id": "T1_Medoid_C4_8303",
                "occupation": "Arbeitslos",
                "empirical_mvpa_hours_week": 0.3333333333,
                "empirical_total_pa_hours_week": 1.0,
            },
        ]
    )


def _trace() -> dict:
    records = []
    personas = [
        ("T1_Medoid_C1_7067", 30, "moderate", 0.30),
        ("T1_Medoid_C2_8153", 20, "moderate", 0.40),
        ("T1_Medoid_C3_8237", 40, "vigorous", 0.65),
        ("T1_Medoid_C4_8303", 15, "light", 0.00),
    ]
    for persona_id, duration, intensity, action_planning in personas:
        for day_index in range(90):
            active = day_index % 3 == 0
            decision = {
                "decision_label": "extra_activity" if active else "skip_activity",
                "duration_min": duration if active else 0,
                "intensity": intensity if active else "none",
            }
            records.append(
                {
                    "persona_id": persona_id,
                    "calendar_date": (START_DATE + timedelta(days=day_index)).isoformat(),
                    "day_index": day_index,
                    "week_index": day_index // 7,
                    "phase": "normal",
                    "weekday": day_index % 7,
                    "planned_physical_activity": None,
                    "was_physical_activity_planned_today": False,
                    "pa_decision": decision,
                    "closed_loop_update": {"activity_done": active},
                    "empirical_pa_v1_2": {
                        "action_planning_value": action_planning,
                        "modifier_beta_times_z": 0.0,
                    },
                    "psychological_constructs_before_update": {},
                    "psychological_constructs_after_update": {},
                }
            )
    return {"records": records}


def test_seed_14_remains_valid_when_pa_schedule_is_disabled() -> None:
    result = inspect_event_free_seed(
        14,
        MEDOID_FILE,
        include_pa_schedule=False,
    )

    assert result["valid"] is True
    assert result["derived_persona_seeds"] == [
        458825077,
        1060578839,
        1164431025,
        1098547461,
    ]


def test_v1_2_daily_rows_use_only_moderate_and_vigorous_minutes_as_mvpa() -> None:
    daily = daily_rows_from_trace(_trace(), _empirical())

    c1 = daily[daily["persona_id"].eq("T1_Medoid_C1_7067")]
    c4 = daily[daily["persona_id"].eq("T1_Medoid_C4_8303")]

    assert c1.loc[c1["activity_performed"], "mvpa_minutes"].eq(30).all()
    assert c4.loc[c4["activity_performed"], "mvpa_minutes"].eq(0).all()
    assert c4.loc[c4["activity_performed"], "light_pa_minutes"].eq(15).all()


def test_v1_2_summary_produces_direct_mvpa_hours_per_week() -> None:
    empirical = _empirical()
    daily = daily_rows_from_trace(_trace(), empirical)
    summary = summarize_horizons(daily, empirical)

    c1_90 = summary[
        summary["persona_id"].eq("T1_Medoid_C1_7067")
        & summary["horizon_days"].eq(90)
    ].iloc[0]
    c4_90 = summary[
        summary["persona_id"].eq("T1_Medoid_C4_8303")
        & summary["horizon_days"].eq(90)
    ].iloc[0]

    expected_c1 = (30 * 30) / 60 / 90 * 7
    assert c1_90["simulated_mvpa_hours_week"] == pytest.approx(expected_c1)
    assert c4_90["simulated_mvpa_hours_week"] == 0.0


def test_v1_2_correlations_and_report_label_analysis_as_descriptive() -> None:
    empirical = _empirical()
    daily = daily_rows_from_trace(_trace(), empirical)
    summary = summarize_horizons(daily, empirical)
    correlations = calculate_correlations(summary)
    seed = {
        "selected_base_seed": 14,
        "derived_persona_seeds": [1, 2, 3, 4],
    }
    report = build_report(seed, summary, correlations)

    assert set(correlations["horizon_days"]) == {7, 30, 90}
    assert "validation-only" in report
    assert "descriptive/exploratory with n=4" in report
    assert "no input-informed scheduler PA baseline" in report


def test_v1_2_daily_rows_reject_planned_pa_leakage() -> None:
    trace = _trace()
    trace["records"][0]["was_physical_activity_planned_today"] = True

    with pytest.raises(ValueError, match="planned PA"):
        daily_rows_from_trace(trace, _empirical())
