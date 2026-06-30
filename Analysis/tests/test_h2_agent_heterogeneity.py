from __future__ import annotations

from pathlib import Path
import socket
import sys

import pytest

ANALYSIS_DIR = Path(__file__).resolve().parents[1]
ROOT = ANALYSIS_DIR.parent

for path in (ROOT, ANALYSIS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import h2_agent_heterogeneity as h2


def test_base_seed_sequence() -> None:
    assert h2.base_seed_sequence(3263, 10) == list(range(3263, 3273))


def test_ten_personas_per_seed_and_unique_ids_without_fixed_phase() -> None:
    agents = h2.generate_agents([3263], 10)
    assert len(agents) == 10
    assert len({agent.unique_agent_id for agent in agents}) == 10
    assert not hasattr(agents[0], "phase")


def test_default_design_pair_count() -> None:
    assert 10 * (10 * 9 // 2) == 450


def test_complete_agent_year_shape_and_generated_phase_coverage() -> None:
    agents = h2.generate_agents([3263], 1)
    schedules = h2.generate_schedules(agents)

    assert len(schedules) == h2.TOTAL_YEAR_SLOTS
    assert sorted({row["week_index"] for row in schedules}) == list(range(52))
    assert sorted({row["weekday"] for row in schedules}) == list(range(7))
    assert sorted({row["hour"] for row in schedules}) == list(range(24))
    assert set(row["phase"] for row in schedules) == set(h2.PHASES)
    assert all(str(row["activity_type"]) for row in schedules)


def test_similarity_identical_and_completely_different() -> None:
    a = ["sleep"] * h2.TOTAL_YEAR_SLOTS
    b = ["sleep"] * h2.TOTAL_YEAR_SLOTS
    c = ["work"] * h2.TOTAL_YEAR_SLOTS
    assert h2.compare_year_activity_types(a, b)[
        "similarity_percent"
    ] == pytest.approx(100.0)
    assert h2.compare_year_activity_types(a, c)[
        "similarity_percent"
    ] == pytest.approx(0.0)


def test_pairwise_combinations_for_three_agents() -> None:
    agents = h2.generate_agents([3263], 3)
    schedules = h2.generate_schedules(agents)
    pairwise = h2.pairwise_schedule_similarity(schedules)
    assert len(pairwise) == 3
    assert all(row["total_slots"] == h2.TOTAL_YEAR_SLOTS for row in pairwise)


def test_same_base_seed_identical_persona_seeds_and_different_seed_differs() -> None:
    first = h2.generate_agents([3263], 10)
    repeated = h2.generate_agents([3263], 10)
    different = h2.generate_agents([3264], 10)

    assert [agent.persona_seed for agent in first] == [
        agent.persona_seed for agent in repeated
    ]
    assert [agent.persona_seed for agent in first] != [
        agent.persona_seed for agent in different
    ]


def test_same_seed_produces_identical_annual_schedule_and_phase_sequence() -> None:
    first = h2.generate_agents([3263], 1)
    repeated = h2.generate_agents([3263], 1)
    different = h2.generate_agents([3264], 1)

    first_schedule = h2.generate_schedules(first)
    repeated_schedule = h2.generate_schedules(repeated)
    different_schedule = h2.generate_schedules(different)

    assert first_schedule == repeated_schedule
    assert [
        (row["week_index"], row["phase"])
        for row in h2.phase_sequence_rows(first_schedule)
    ] == [
        (row["week_index"], row["phase"])
        for row in h2.phase_sequence_rows(repeated_schedule)
    ]
    assert [row["activity_type"] for row in first_schedule] != [
        row["activity_type"] for row in different_schedule
    ]


def test_phase_counts_sum_to_52_for_each_agent() -> None:
    agents = h2.generate_agents([3263], 2)
    schedules = h2.generate_schedules(agents)
    counts = h2.phase_week_counts(h2.phase_sequence_rows(schedules))

    for agent in agents:
        agent_counts = [
            row for row in counts
            if row["unique_agent_id"] == agent.unique_agent_id
        ]
        assert sum(int(row["n_weeks"]) for row in agent_counts) == 52
        assert {row["phase"] for row in agent_counts} == set(h2.PHASES)


def test_psychological_constructs_deterministic_active_and_bounded() -> None:
    agents = h2.generate_agents([3263], 3)
    first = h2.generate_psychological_constructs(agents)
    repeated = h2.generate_psychological_constructs(agents)

    assert first == repeated
    assert list(h2.ACTIVE_CONSTRUCTS) == [
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
    assert len(h2.ACTIVE_CONSTRUCTS) == 9
    assert all(
        0 <= row[construct] <= 1
        for row in first
        for construct in h2.ACTIVE_CONSTRUCTS
    )


def test_summary_mean_population_sd_range_iqr() -> None:
    rows = []
    for index, unique_agent_id in enumerate("abcd"):
        row = {
            "base_seed": 1,
            "persona_index": index,
            "unique_agent_id": unique_agent_id,
            "persona_id": unique_agent_id,
            "persona_seed": index + 1,
            "psychological_seed": index + 11,
        }
        for construct in h2.ACTIVE_CONSTRUCTS:
            row[construct] = [0.0, 0.25, 0.75, 1.0][index]
        rows.append(row)

    summary, _, _ = h2.construct_summaries(rows)
    result = [
        row
        for row in summary
        if row["construct"] == h2.ACTIVE_CONSTRUCTS[0]
    ][0]

    assert result["mean"] == pytest.approx(0.5)
    assert result["population_sd"] == pytest.approx(
        (
            sum(
                (value - 0.5) ** 2
                for value in [0.0, 0.25, 0.75, 1.0]
            )
            / 4
        )
        ** 0.5
    )
    assert result["range"] == pytest.approx(1.0)
    assert result["iqr"] == pytest.approx(0.625)


def test_cli_has_no_externally_fixed_phase_argument() -> None:
    args = h2.parse_args([])
    assert not hasattr(args, "phase")


def test_analysis_does_not_require_network_or_llm(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def blocked(*args, **kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "create_connection", blocked)
    config = h2.run_analysis(
        h2.parse_args(
            [
                "--n-base-seeds",
                "1",
                "--agents-per-seed",
                "2",
                "--output-dir",
                str(tmp_path),
                "--overwrite",
            ]
        )
    )

    assert config["total_agents"] == 2
    assert config["n_weeks_per_agent"] == 52
    assert config["slots_per_agent_year"] == h2.TOTAL_YEAR_SLOTS
    assert config["phase_source"].startswith("YearStructureGenerator")
    assert not any(
        "llm" in name.lower()
        for name in h2.sys.modules
        if name.startswith("llm")
    )
    assert (tmp_path / "tables" / "phase_activity_summary.csv").exists()
    assert (tmp_path / "figures" / "phase_sequence_heatmap.png").exists()
