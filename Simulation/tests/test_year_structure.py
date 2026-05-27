from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from year_structure import ALLOWED_PHASES, YearStructureGenerator


class _DummyParams:
    pass


def test_generate_year_default_has_52_weeks() -> None:
    generator = YearStructureGenerator()
    year = generator.generate_year(persona_id="p1", persona_seed=123, parameters=_DummyParams())
    assert year.n_weeks == 52
    assert len(year.weeks) == 52


def test_phase_counts_sum_to_n_weeks() -> None:
    generator = YearStructureGenerator()
    year = generator.generate_year(persona_id="p1", persona_seed=123, parameters=_DummyParams())
    assert sum(year.phase_counts.values()) == year.n_weeks


def test_phases_remain_only_normal_high_stress_holiday() -> None:
    generator = YearStructureGenerator()
    year = generator.generate_year(persona_id="p1", persona_seed=123, parameters=_DummyParams())
    assert all(week.phase in ALLOWED_PHASES for week in year.weeks)


def test_holiday_range_and_block_tags_present() -> None:
    generator = YearStructureGenerator()
    year = generator.generate_year(persona_id="p1", persona_seed=321, parameters=_DummyParams())
    holiday_count = sum(1 for week in year.weeks if week.phase == "holiday")
    assert 12 <= holiday_count <= 18

    winter_count = sum(1 for week in year.weeks if week.fixed_block_tag == "winter_holiday")
    summer_count = sum(1 for week in year.weeks if week.fixed_block_tag == "summer_holiday")
    assert 4 <= winter_count <= 6
    assert 8 <= summer_count <= 12


def test_same_seed_same_output() -> None:
    generator = YearStructureGenerator()
    a = generator.generate_year(persona_id="p1", persona_seed=777, parameters=_DummyParams())
    b = generator.generate_year(persona_id="p1", persona_seed=777, parameters=_DummyParams())
    assert asdict(a) == asdict(b)


def test_different_seed_different_output() -> None:
    generator = YearStructureGenerator()
    a = generator.generate_year(persona_id="p1", persona_seed=777, parameters=_DummyParams())
    b = generator.generate_year(persona_id="p1", persona_seed=778, parameters=_DummyParams())

    a_phases = [w.phase for w in a.weeks]
    b_phases = [w.phase for w in b.weeks]
    a_events = [(e.event_type, e.start_week, e.start_day, e.duration_days, e.intensity) for e in a.events]
    b_events = [(e.event_type, e.start_week, e.start_day, e.duration_days, e.intensity) for e in b.events]

    assert a_phases != b_phases or a_events != b_events or a.metadata != b.metadata


def test_illness_events_valid_and_canonical_intensity() -> None:
    generator = YearStructureGenerator()
    year = generator.generate_year(persona_id="p1", persona_seed=12345, parameters=_DummyParams())
    illness_events = [event for event in year.events if event.event_type == "illness"]
    for event in illness_events:
        assert 0 <= event.start_week < year.n_weeks
        assert 0 <= event.start_day <= 6
        assert event.duration_days >= 1
        assert event.intensity in {"low", "medium", "high"}
        assert event.intensity != "mid"


def test_public_holidays_are_events_not_phases() -> None:
    generator = YearStructureGenerator()
    year = generator.generate_year(persona_id="p3", persona_seed=941, parameters=_DummyParams())
    public_events = [event for event in year.events if event.event_type == "public_holiday"]
    assert 9 <= len(public_events) <= 13
    for event in public_events:
        assert event.duration_days == 1
        assert event.intensity == "low"
        assert event.source == "calendar"


def test_active_event_ids_attached_to_all_affected_weeks() -> None:
    generator = YearStructureGenerator()
    year = generator.generate_year(persona_id="p2", persona_seed=31415, parameters=_DummyParams())

    week_by_id = {w.week_index: w for w in year.weeks}
    for event in year.events:
        start_abs_day = event.start_week * 7 + event.start_day
        end_abs_day = start_abs_day + event.duration_days - 1
        expected_start_week = start_abs_day // 7
        expected_end_week = min(year.n_weeks - 1, end_abs_day // 7)

        for week_idx in range(expected_start_week, expected_end_week + 1):
            week = week_by_id[week_idx]
            assert event.event_id in week.active_event_ids
            assert any(entry.get("event_id") == event.event_id for entry in week.constraints_week_view)
