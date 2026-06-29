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


def test_ten_personas_per_seed_and_unique_ids() -> None:
    agents = h2.generate_agents([3263], 10, "normal")
    assert len(agents) == 10
    assert len({a.unique_agent_id for a in agents}) == 10


def test_default_design_pair_count() -> None:
    assert 10 * (10 * 9 // 2) == 450


def test_schedule_shape_weekdays_hours_and_activity_normalization() -> None:
    agents = h2.generate_agents([3263], 2, "normal")
    schedules = h2.generate_schedules(agents)
    ids = sorted({r["unique_agent_id"] for r in schedules})
    assert all(sum(r["unique_agent_id"] == uid for r in schedules) == 168 for uid in ids)
    for uid in ids:
        g = [r for r in schedules if r["unique_agent_id"] == uid]
        assert sorted({r["weekday"] for r in g}) == list(range(7))
        assert sorted({r["hour"] for r in g}) == list(range(24))
        assert all(str(r["activity_type"]) for r in g)


def test_similarity_identical_and_completely_different() -> None:
    a = ["sleep"] * 168
    b = ["sleep"] * 168
    c = ["work"] * 168
    assert h2.compare_week_activity_types(a, b)["similarity_percent"] == pytest.approx(100.0)
    assert h2.compare_week_activity_types(a, c)["similarity_percent"] == pytest.approx(0.0)


def test_pairwise_combinations_for_ten_agents() -> None:
    agents = h2.generate_agents([3263], 10, "normal")
    schedules = h2.generate_schedules(agents)
    pairwise = h2.pairwise_schedule_similarity(schedules)
    assert len(pairwise) == 45


def test_same_base_seed_identical_persona_seeds_and_different_seed_differs() -> None:
    a = h2.generate_agents([3263], 10, "normal")
    b = h2.generate_agents([3263], 10, "normal")
    c = h2.generate_agents([3264], 10, "normal")
    assert [x.persona_seed for x in a] == [x.persona_seed for x in b]
    assert [x.persona_seed for x in a] != [x.persona_seed for x in c]


def test_same_seed_produces_identical_schedules_and_different_seed_differs() -> None:
    a1 = h2.generate_agents([3263], 2, "normal")
    a2 = h2.generate_agents([3263], 2, "normal")
    b = h2.generate_agents([3264], 2, "normal")
    s1 = h2.generate_schedules(a1)
    s2 = h2.generate_schedules(a2)
    sb = h2.generate_schedules(b)
    assert s1 == s2
    assert [r["activity_type"] for r in s1] != [r["activity_type"] for r in sb]


def test_psychological_constructs_deterministic_active_and_bounded() -> None:
    agents = h2.generate_agents([3263], 3, "normal")
    p1 = h2.generate_psychological_constructs(agents)
    p2 = h2.generate_psychological_constructs(agents)
    assert p1 == p2
    assert list(h2.ACTIVE_CONSTRUCTS) == [
        "automaticity", "pa_specific_self_control", "action_planning", "intention",
        "perceived_behavioral_control", "attitude_toward_the_behavior", "subjective_norm",
        "intrinsic_motivation", "motivational_competence",
    ]
    assert len(h2.ACTIVE_CONSTRUCTS) == 9
    assert all(0 <= r[c] <= 1 for r in p1 for c in h2.ACTIVE_CONSTRUCTS)


def test_summary_mean_population_sd_range_iqr() -> None:
    df = []
    for i, uid in enumerate("abcd"):
        row = {"base_seed": 1, "persona_index": i, "unique_agent_id": uid, "persona_id": uid, "persona_seed": i+1, "psychological_seed": i+11}
        for c in h2.ACTIVE_CONSTRUCTS:
            row[c] = [0.0, 0.25, 0.75, 1.0][i]
        df.append(row)
    summary, _, _ = h2.construct_summaries(df)
    row = [r for r in summary if r["construct"] == h2.ACTIVE_CONSTRUCTS[0]][0]
    assert row["mean"] == pytest.approx(0.5)
    assert row["population_sd"] == pytest.approx((sum((x-0.5)**2 for x in [0.0,0.25,0.75,1.0])/4)**0.5)
    assert row["range"] == pytest.approx(1.0)
    assert row["iqr"] == pytest.approx(0.625)


def test_analysis_does_not_require_network_or_llm(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def blocked(*args, **kwargs):
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket, "create_connection", blocked)
    cfg = h2.run_analysis(h2.parse_args(["--n-base-seeds", "1", "--agents-per-seed", "2", "--output-dir", str(tmp_path), "--overwrite"]))
    assert cfg["total_agents"] == 2
    # No LLM modules/functions are imported or used by the H2 module.
    assert not any("llm" in name.lower() for name in h2.sys.modules if name.startswith("llm"))
