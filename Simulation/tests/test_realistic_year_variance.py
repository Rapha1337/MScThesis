from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from week_variance import generate_realistic_student_year


def test_realistic_year_has_52_weeks_default() -> None:
    out = generate_realistic_student_year(persona_seed=123)
    assert len(out["year_structure"].weeks) == 52


def test_realistic_year_grid_shape() -> None:
    out = generate_realistic_student_year(persona_seed=123)
    grids = out["year_grids"]
    assert len(grids) == 52
    assert all(len(week) == 7 for week in grids)
    assert all(len(day) == 24 for week in grids for day in week)


def test_realistic_year_supports_holiday_tags_and_public_holidays() -> None:
    out = generate_realistic_student_year(persona_seed=123)
    year = out["year_structure"]
    tags = {w.fixed_block_tag for w in year.weeks if w.fixed_block_tag is not None}
    assert "winter_holiday" in tags
    assert "summer_holiday" in tags

    public_events = [e for e in year.events if e.event_type == "public_holiday"]
    assert 9 <= len(public_events) <= 13
    assert out["public_holiday_count"] == len(public_events)


def test_same_seed_identical_realistic_year_input() -> None:
    a = generate_realistic_student_year(persona_seed=555, year_seed=999)
    b = generate_realistic_student_year(persona_seed=555, year_seed=999)
    assert [w.phase for w in a["year_structure"].weeks] == [w.phase for w in b["year_structure"].weeks]
    assert [w.fixed_block_tag for w in a["year_structure"].weeks] == [w.fixed_block_tag for w in b["year_structure"].weeks]
    assert [(e.event_type, e.start_week, e.start_day, e.duration_days, e.intensity) for e in a["year_structure"].events] == [
        (e.event_type, e.start_week, e.start_day, e.duration_days, e.intensity) for e in b["year_structure"].events
    ]
    assert a["year_grids"] == b["year_grids"]


def test_different_seed_usually_changes_realistic_year_structure() -> None:
    a = generate_realistic_student_year(persona_seed=555, year_seed=999)
    b = generate_realistic_student_year(persona_seed=555, year_seed=1000)
    phases_a = [w.phase for w in a["year_structure"].weeks]
    phases_b = [w.phase for w in b["year_structure"].weeks]
    tags_a = [w.fixed_block_tag for w in a["year_structure"].weeks]
    tags_b = [w.fixed_block_tag for w in b["year_structure"].weeks]
    events_a = [(e.event_type, e.start_week, e.start_day, e.duration_days, e.intensity) for e in a["year_structure"].events]
    events_b = [(e.event_type, e.start_week, e.start_day, e.duration_days, e.intensity) for e in b["year_structure"].events]
    assert phases_a != phases_b or tags_a != tags_b or events_a != events_b


def test_public_holiday_only_changes_target_day() -> None:
    out = generate_realistic_student_year(persona_seed=222, year_seed=333, n_weeks=52)
    year = out["year_structure"]
    events = [e for e in year.events if e.event_type == "public_holiday" and e.start_week < 4]
    assert events
    target = events[0]
    grid = out["year_grids"][target.start_week]
    day = grid[target.start_day]
    assert "public_holiday" not in day  # grid stores activity types only
    work_hours_target = sum(1 for slot in day if slot == "work")

    other_day_idx = (target.start_day + 1) % 7
    other_day = grid[other_day_idx]
    work_hours_other = sum(1 for slot in other_day if slot == "work")
    assert work_hours_target <= work_hours_other


def test_illness_multiday_and_intensity_effect() -> None:
    out = None
    illness = None
    for seed in range(900, 960):
        candidate = generate_realistic_student_year(persona_seed=555, year_seed=seed, n_weeks=52)
        year = candidate["year_structure"]
        illness = next((e for e in year.events if e.event_type == "illness" and e.duration_days >= 2), None)
        if illness is not None:
            out = candidate
            break
    assert out is not None
    assert illness is not None

    week = illness.start_week
    day0 = illness.start_day
    grid0 = out["year_grids"][week][day0]
    next_abs = week * 7 + day0 + 1
    week1, day1 = divmod(next_abs, 7)
    grid1 = out["year_grids"][week1][day1]

    assert sum(1 for x in grid0 if x == "physical_activity") <= 1
    assert sum(1 for x in grid1 if x == "physical_activity") <= 1

    if illness.intensity in {"medium", "high"}:
        assert sum(1 for x in grid0 if x == "work") <= 6


def test_without_events_baseline_unchanged_shape() -> None:
    out = generate_realistic_student_year(persona_seed=888, year_seed=888, n_weeks=52)
    grids = out["year_grids"]
    assert len(grids) == 52
    assert all(len(w) == 7 and all(len(d) == 24 for d in w) for w in grids)


def test_realistic_year_variance_still_runs() -> None:
    out = generate_realistic_student_year(persona_seed=321, year_seed=654, n_weeks=52)
    assert "year_grids" in out and "year_structure" in out
