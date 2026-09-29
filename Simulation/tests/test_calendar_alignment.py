from __future__ import annotations

from datetime import date
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))


def _config(tmp_path: Path, *, start_date: date, n_days: int):
    from run_full_pa_simulation import FullSimulationConfig

    return FullSimulationConfig(
        n_personas=1,
        n_days=n_days,
        start_date=start_date,
        base_seed=137,
        output_dir=tmp_path,
        model="gpt-oss-120b",
        temperature=0,
        llm1_max_tokens=2000,
        llm2_max_tokens=1200,
        dry_run=True,
        include_full_hourly_context=True,
    )


def test_july_9_2026_maps_to_thursday_and_internal_week_27() -> None:
    from run_full_pa_simulation import calendar_schedule_coordinates

    assert date(2026, 7, 9).isocalendar().week == 28
    assert calendar_schedule_coordinates(date(2026, 7, 9)) == (27, 3)


def test_sunday_to_monday_uses_next_iso_week() -> None:
    from run_full_pa_simulation import calendar_schedule_coordinates

    assert calendar_schedule_coordinates(date(2026, 7, 12)) == (27, 6)
    assert calendar_schedule_coordinates(date(2026, 7, 13)) == (28, 0)


def test_iso_week_53_folds_into_last_year_structure_week() -> None:
    from run_full_pa_simulation import calendar_schedule_coordinates

    assert date(2026, 12, 31).isocalendar().week == 53
    assert calendar_schedule_coordinates(date(2026, 12, 31)) == (51, 3)


def test_environment_switches_from_july_to_august(tmp_path: Path) -> None:
    from run_full_pa_simulation import build_global_environment_by_date

    environment = build_global_environment_by_date(
        _config(tmp_path, start_date=date(2026, 7, 31), n_days=2)
    )
    assert {hour["month"] for hour in environment["2026-07-31"]} == {7}
    assert {hour["month"] for hour in environment["2026-08-01"]} == {8}


def test_multiday_trace_aligns_date_weekday_week_and_phase(tmp_path: Path) -> None:
    from run_full_pa_simulation import run_full_simulation

    trace = run_full_simulation(
        _config(tmp_path, start_date=date(2026, 7, 9), n_days=5)
    )
    records = trace["records"]
    assert [(row["calendar_date"], row["weekday"], row["week_index"]) for row in records] == [
        ("2026-07-09", 3, 27),
        ("2026-07-10", 4, 27),
        ("2026-07-11", 5, 27),
        ("2026-07-12", 6, 27),
        ("2026-07-13", 0, 28),
    ]
    states = __import__("run_full_pa_simulation")._build_persona_states(
        _config(tmp_path / "states", start_date=date(2026, 7, 9), n_days=5)
    )
    expected_phases = [
        states[0].runner.year_structure.weeks[row["week_index"]].phase
        for row in records
    ]
    assert [row["phase"] for row in records] == expected_phases
