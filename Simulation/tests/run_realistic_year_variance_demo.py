from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from week_variance import (
    run_between_agent_realistic_year_variance,
    run_between_seed_year_variance,
)


def main() -> None:
    n_agents = 30
    base_seed = 123

    realistic_summary = run_between_agent_realistic_year_variance(
        n_agents=n_agents,
        base_seed=base_seed,
        n_weeks=52,
    )
    baseline_summary = run_between_seed_year_variance(
        n_personas=n_agents,
        base_seed=base_seed,
        phase="normal",
        week_indices=list(range(1, 53)),
    )

    print("REALISTIC YEAR VARIANCE DEMO")
    print("============================")
    print(f"n_agents: {n_agents}")
    print(f"example_phase_counts: {realistic_summary['example_phase_counts']}")
    print(f"example_block_counts: {realistic_summary['example_block_counts']}")
    print(f"example_public_holiday_count: {realistic_summary['example_public_holiday_count']}")
    print(f"example_illness_event_count: {realistic_summary['example_illness_event_count']}")
    print("\nbetween-agent realistic year variance:")
    print(f"  similarity_percent_mean: {realistic_summary['mean_similarity_percent']:.2f}")
    print(f"  variance_percent_mean:   {realistic_summary['mean_variance_percent']:.2f}")
    print("\nold baseline (single-phase normal) year variance:")
    print(f"  similarity_percent_mean: {baseline_summary['mean_similarity_percent']:.2f}")
    print(f"  variance_percent_mean:   {baseline_summary['mean_variance_percent']:.2f}")


if __name__ == "__main__":
    main()
