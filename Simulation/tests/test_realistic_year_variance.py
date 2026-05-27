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
