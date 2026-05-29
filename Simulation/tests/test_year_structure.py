from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from year_structure import ALLOWED_PHASES, YearStructureConfig, YearStructureGenerator


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
        assert event.intensity is None
        assert event.source == "calendar"
    assert all(event.intensity != "low" for event in public_events)


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


def test_fixed_holiday_blocks_stay_inside_configured_windows_and_are_contiguous() -> None:
    config = YearStructureConfig(
        holiday_block_placement_windows={
            "winter_holiday": [(0, 7), (47, 51)],
            "summer_holiday": [(23, 36)],
        }
    )
    generator = YearStructureGenerator(config=config)
    year = generator.generate_year(persona_id="p4", persona_seed=2026, parameters=_DummyParams())

    summer_weeks = [w.week_index for w in year.weeks if w.fixed_block_tag == "summer_holiday"]
    winter_weeks = [w.week_index for w in year.weeks if w.fixed_block_tag == "winter_holiday"]
    assert summer_weeks
    assert winter_weeks

    summer_windows = config.holiday_block_placement_windows["summer_holiday"]
    winter_windows = config.holiday_block_placement_windows["winter_holiday"]

    assert all(any(start <= idx <= end for start, end in summer_windows) for idx in summer_weeks)
    assert all(any(start <= idx <= end for start, end in winter_windows) for idx in winter_weeks)

    assert summer_weeks == list(range(min(summer_weeks), max(summer_weeks) + 1))
    assert winter_weeks == list(range(min(winter_weeks), max(winter_weeks) + 1))


def test_no_summer_holiday_at_week_zero_if_not_in_summer_window() -> None:
    config = YearStructureConfig(
        holiday_block_placement_windows={
            "winter_holiday": [(0, 7), (47, 51)],
            "summer_holiday": [(23, 36)],
        }
    )
    generator = YearStructureGenerator(config=config)
    year = generator.generate_year(persona_id="p5", persona_seed=4040, parameters=_DummyParams())
    assert all(not (w.week_index == 0 and w.fixed_block_tag == "summer_holiday") for w in year.weeks)


def test_year_structure_normalizes_legacy_mid_config_to_medium() -> None:
    config = YearStructureConfig(
        illness_duration_days_probs={1: 1.0},
        illness_intensity_probs={"mid": 1.0},
    )
    config.illness_occurrence_prob = 1.0
    config.illness_episode_count_probs = {1: 1.0}
    generator = YearStructureGenerator(config=config)
    year = generator.generate_year(persona_id="p5", persona_seed=2027, parameters=_DummyParams())

    illness_events = [event for event in year.events if event.event_type == "illness"]
    assert illness_events
    assert all(event.intensity == "medium" for event in illness_events)
    assert generator.config.illness_intensity_probs == {"medium": 1.0}


def _phase_indices(year, phase: str) -> list[int]:
    return [week.week_index for week in year.weeks if week.phase == phase]


def _contiguous_blocks(indices: list[int]) -> list[list[int]]:
    if not indices:
        return []
    blocks: list[list[int]] = [[indices[0]]]
    for idx in indices[1:]:
        if idx == blocks[-1][-1] + 1:
            blocks[-1].append(idx)
        else:
            blocks.append([idx])
    return blocks


def _exam_friendly_config() -> YearStructureConfig:
    return YearStructureConfig(
        phase_target_ranges={
            "normal": (34, 34),
            "high_stress": (6, 6),
            "holiday": (12, 12),
        },
        holiday_block_ranges={"winter_holiday": (4, 4), "summer_holiday": (8, 8)},
        holiday_block_placement_windows={
            "winter_holiday": [(48, 51)],
            "summer_holiday": [(30, 37)],
        },
    )


def test_high_stress_count_stays_in_configured_range() -> None:
    config = YearStructureConfig(
        phase_target_ranges={"normal": (30, 34), "high_stress": (6, 10), "holiday": (12, 16)}
    )
    generator = YearStructureGenerator(config=config)
    year = generator.generate_year(persona_id="p6", persona_seed=111, parameters=_DummyParams())

    low, high = config.phase_target_ranges["high_stress"]
    assert low <= year.phase_counts["high_stress"] <= high


def test_high_stress_does_not_overwrite_fixed_holiday_blocks() -> None:
    generator = YearStructureGenerator(config=_exam_friendly_config())
    year = generator.generate_year(persona_id="p7", persona_seed=222, parameters=_DummyParams())

    for week in year.weeks:
        if week.fixed_block_tag in {"winter_holiday", "summer_holiday"}:
            assert week.phase == "holiday"


def test_high_stress_has_multi_week_block_when_count_allows() -> None:
    generator = YearStructureGenerator(config=_exam_friendly_config())
    year = generator.generate_year(persona_id="p8", persona_seed=333, parameters=_DummyParams())

    high_stress_blocks = _contiguous_blocks(_phase_indices(year, "high_stress"))
    assert year.phase_counts["high_stress"] >= 2
    assert any(len(block) >= 2 for block in high_stress_blocks)


def test_high_stress_prefers_weeks_directly_before_summer_holiday_when_available() -> None:
    generator = YearStructureGenerator(config=_exam_friendly_config())
    year = generator.generate_year(persona_id="p9", persona_seed=444, parameters=_DummyParams())

    summer_weeks = [week.week_index for week in year.weeks if week.fixed_block_tag == "summer_holiday"]
    summer_start = min(summer_weeks)

    assert [year.weeks[idx].phase for idx in range(summer_start - 2, summer_start)] == [
        "high_stress",
        "high_stress",
    ]


def test_high_stress_prefers_weeks_directly_before_or_near_winter_holiday_when_available() -> None:
    generator = YearStructureGenerator(config=_exam_friendly_config())
    year = generator.generate_year(persona_id="p10", persona_seed=555, parameters=_DummyParams())

    winter_weeks = [week.week_index for week in year.weeks if week.fixed_block_tag == "winter_holiday"]
    winter_start = min(winter_weeks)
    nearby_before_winter = range(max(0, winter_start - 3), winter_start)

    assert any(year.weeks[idx].phase == "high_stress" for idx in nearby_before_winter)


def test_year_structure_deterministic_with_grouped_high_stress_blocks() -> None:
    generator = YearStructureGenerator(config=_exam_friendly_config())
    a = generator.generate_year(persona_id="p11", persona_seed=666, parameters=_DummyParams())
    b = generator.generate_year(persona_id="p11", persona_seed=666, parameters=_DummyParams())

    assert asdict(a) == asdict(b)
