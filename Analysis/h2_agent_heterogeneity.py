from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
import sys
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any, Iterable

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import BoundaryNorm
    from matplotlib.patches import Patch
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "H2 figure generation requires numpy and matplotlib. "
        "Install them before running Analysis/h2_agent_heterogeneity.py."
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "Simulation"
if str(SIM) not in sys.path:
    sys.path.insert(0, str(SIM))

from agent_context_export import PSYCHOLOGICAL_SEED_OFFSET
from persona_wrappers import StudentHoursWrapper, StudentWrapper
from psychological_state import BACKEND_CONSTRUCT_RANGES, build_psychological_state
from schedule_model_student import (
    YearPhase,
    distribute_weekly_budgets_to_days,
    generate_full_day_schedule,
)


ACTIVE_CONSTRUCTS = tuple(BACKEND_CONSTRUCT_RANGES.keys())
WEEKDAY_LABELS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
TOTAL_WEEK_SLOTS = 168
DEFAULT_OUTPUT_DIR = ROOT / "Analysis" / "outputs" / "h2_agent_heterogeneity"

CONSTRUCT_DISPLAY_LABELS = {
    "automaticity": "Automaticity",
    "pa_specific_self_control": "PA-specific\nself-control",
    "action_planning": "Action\nplanning",
    "intention": "Intention",
    "perceived_behavioral_control": "Perceived\nbehavioral control",
    "attitude_toward_the_behavior": "Attitude",
    "subjective_norm": "Subjective\nnorm",
    "intrinsic_motivation": "Intrinsic\nmotivation",
    "motivational_competence": "Motivational\ncompetence",
}


@dataclass(frozen=True)
class AgentRecord:
    unique_agent_id: str
    base_seed: int
    persona_index: int
    persona_id: str
    persona_seed: int
    psychological_seed: int
    phase: str
    wrapper: StudentHoursWrapper
    weekly_structure: Any


def base_seed_sequence(base_seed: int, n_base_seeds: int) -> list[int]:
    if n_base_seeds < 1:
        raise ValueError("n_base_seeds must be at least 1")
    return list(range(base_seed, base_seed + n_base_seeds))


def psychological_seed_from_persona_seed(persona_seed: int) -> int:
    return int(persona_seed) + int(PSYCHOLOGICAL_SEED_OFFSET)


def generic_student_inputs() -> dict[str, float | None]:
    return StudentHoursWrapper.from_zve_student_generic().input_parameters()


def generate_agents(
    base_seeds: Iterable[int],
    agents_per_seed: int,
    phase: str,
) -> list[AgentRecord]:
    phase_value = YearPhase.coerce(phase)
    parameters = StudentHoursWrapper.from_zve_student_generic()
    agents: list[AgentRecord] = []

    for base_seed in base_seeds:
        personas = StudentWrapper(
            parameters,
            int(base_seed),
        ).create_personas(agents_per_seed, phase_value)

        if len(personas) != agents_per_seed:
            raise ValueError("persona count mismatch")

        for persona in personas:
            persona_index = int(persona["persona_index"])
            persona_id = str(persona["persona_name"])
            persona_seed = int(persona["persona_seed"])

            agents.append(
                AgentRecord(
                    unique_agent_id=f"base{base_seed}_{persona_id}",
                    base_seed=int(base_seed),
                    persona_index=persona_index,
                    persona_id=persona_id,
                    persona_seed=persona_seed,
                    psychological_seed=psychological_seed_from_persona_seed(
                        persona_seed
                    ),
                    phase=phase_value.value,
                    wrapper=persona["wrapper"],
                    weekly_structure=persona["weekly_structure"],
                )
            )

    if len({agent.unique_agent_id for agent in agents}) != len(agents):
        raise ValueError("Generated agent IDs are not globally unique")

    return sorted(agents, key=lambda agent: (agent.base_seed, agent.persona_index))


def generate_agent_schedule(agent: AgentRecord) -> list[dict[str, Any]]:
    distribute_weekly_budgets_to_days(
        agent.weekly_structure,
        rng=random.Random(agent.persona_seed),
    )

    rows: list[dict[str, Any]] = []
    for weekday in range(7):
        day = generate_full_day_schedule(
            agent.weekly_structure,
            weekday,
            rng=random.Random(agent.persona_seed + weekday),
        )

        if len(day) != 24:
            raise ValueError("day must have 24 slots")

        for episode in sorted(day, key=lambda item: int(item.hour)):
            rows.append(
                {
                    "unique_agent_id": agent.unique_agent_id,
                    "base_seed": agent.base_seed,
                    "persona_index": agent.persona_index,
                    "persona_id": agent.persona_id,
                    "persona_seed": agent.persona_seed,
                    "psychological_seed": agent.psychological_seed,
                    "phase": agent.phase,
                    "weekday": weekday,
                    "weekday_label": WEEKDAY_LABELS[weekday],
                    "hour": int(episode.hour),
                    "week_hour": weekday * 24 + int(episode.hour),
                    "activity_type": str(
                        getattr(episode.activity_type, "value", episode.activity_type)
                    ),
                    "subtype": episode.subtype or "",
                }
            )

    return rows


def generate_schedules(agents: list[AgentRecord]) -> list[dict[str, Any]]:
    rows = [
        row
        for agent in agents
        for row in generate_agent_schedule(agent)
    ]
    validate_schedules(rows, len(agents))
    return sorted(
        rows,
        key=lambda row: (
            row["base_seed"],
            row["persona_index"],
            row["weekday"],
            row["hour"],
        ),
    )


def validate_schedules(
    rows: list[dict[str, Any]],
    expected_agents: int,
) -> None:
    agent_ids = sorted({row["unique_agent_id"] for row in rows})
    if len(agent_ids) != expected_agents:
        raise ValueError("agent count mismatch")

    for agent_id in agent_ids:
        agent_rows = [
            row for row in rows if row["unique_agent_id"] == agent_id
        ]
        unique_slots = {
            (row["weekday"], row["hour"]) for row in agent_rows
        }

        if len(agent_rows) != TOTAL_WEEK_SLOTS or len(unique_slots) != TOTAL_WEEK_SLOTS:
            raise ValueError(
                "Each agent must have 168 unique weekday-hour rows"
            )
        if sorted({row["weekday"] for row in agent_rows}) != list(range(7)):
            raise ValueError("bad weekday coverage")
        if sorted({row["hour"] for row in agent_rows}) != list(range(24)):
            raise ValueError("bad hour coverage")
        if any(not str(row["activity_type"]) for row in agent_rows):
            raise ValueError("empty activity_type")


def week_grid(
    rows: list[dict[str, Any]],
    agent_id: str,
) -> list[str]:
    agent_rows = [
        row for row in rows if row["unique_agent_id"] == agent_id
    ]
    return [
        row["activity_type"]
        for row in sorted(
            agent_rows,
            key=lambda item: (item["weekday"], item["hour"]),
        )
    ]


def compare_week_activity_types(
    week_a: list[str],
    week_b: list[str],
) -> dict[str, float | int]:
    if len(week_a) != TOTAL_WEEK_SLOTS or len(week_b) != TOTAL_WEEK_SLOTS:
        raise ValueError("Weekly schedules must contain 168 activity labels")

    matching_slots = sum(
        activity_a == activity_b
        for activity_a, activity_b in zip(week_a, week_b)
    )
    similarity = matching_slots / TOTAL_WEEK_SLOTS

    return {
        "matching_slots": matching_slots,
        "differing_slots": TOTAL_WEEK_SLOTS - matching_slots,
        "total_slots": TOTAL_WEEK_SLOTS,
        "similarity": similarity,
        "similarity_percent": similarity * 100,
        "difference": 1 - similarity,
        "difference_percent": (1 - similarity) * 100,
    }


def pairwise_schedule_similarity(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for base_seed in sorted({row["base_seed"] for row in rows}):
        run_rows = [row for row in rows if row["base_seed"] == base_seed]
        agent_ids = [
            unique_agent_id
            for _, unique_agent_id in sorted(
                {
                    (row["persona_index"], row["unique_agent_id"])
                    for row in run_rows
                }
            )
        ]
        grids = {
            agent_id: week_grid(run_rows, agent_id)
            for agent_id in agent_ids
        }

        for agent_a, agent_b in combinations(agent_ids, 2):
            results.append(
                {
                    "base_seed": base_seed,
                    "agent_a_id": agent_a,
                    "agent_b_id": agent_b,
                    **compare_week_activity_types(
                        grids[agent_a],
                        grids[agent_b],
                    ),
                }
            )

    return results


def summarize_schedule_similarity(
    pairs: list[dict[str, Any]],
    agents_per_seed: int,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    run_summary: list[dict[str, Any]] = []

    for base_seed in sorted({pair["base_seed"] for pair in pairs}):
        run_pairs = [
            pair for pair in pairs if pair["base_seed"] == base_seed
        ]
        similarities = [
            float(pair["similarity_percent"]) for pair in run_pairs
        ]
        differences = [
            float(pair["difference_percent"]) for pair in run_pairs
        ]

        run_summary.append(
            {
                "base_seed": base_seed,
                "n_agents": agents_per_seed,
                "n_pairs": len(run_pairs),
                "mean_similarity_percent": mean(similarities),
                "sd_similarity_percent": (
                    pstdev(similarities) if len(similarities) > 1 else 0
                ),
                "min_similarity_percent": min(similarities),
                "max_similarity_percent": max(similarities),
                "mean_difference_percent": mean(differences),
                "sd_difference_percent": (
                    pstdev(differences) if len(differences) > 1 else 0
                ),
                "min_difference_percent": min(differences),
                "max_difference_percent": max(differences),
            }
        )

    similarities = [
        float(pair["similarity_percent"]) for pair in pairs
    ] or [100.0]
    differences = [
        float(pair["difference_percent"]) for pair in pairs
    ] or [0.0]

    overall_summary = [
        {
            "scope": "all_within_run_pairs",
            "n_pairs": len(pairs),
            "mean_similarity_percent": mean(similarities),
            "sd_similarity_percent": (
                pstdev(similarities) if len(similarities) > 1 else 0
            ),
            "min_similarity_percent": min(similarities),
            "max_similarity_percent": max(similarities),
            "mean_difference_percent": mean(differences),
            "sd_difference_percent": (
                pstdev(differences) if len(differences) > 1 else 0
            ),
            "min_difference_percent": min(differences),
            "max_difference_percent": max(differences),
            "sd_type": "population",
        }
    ]

    run_means = [
        float(row["mean_similarity_percent"]) for row in run_summary
    ] or [100.0]
    across_run_summary = [
        {
            "scope": "run_level_means",
            "n_runs": len(run_summary),
            "mean_of_run_mean_similarity_percent": mean(run_means),
            "sd_of_run_mean_similarity_percent": (
                pstdev(run_means) if len(run_means) > 1 else 0
            ),
            "min_run_mean_similarity_percent": min(run_means),
            "max_run_mean_similarity_percent": max(run_means),
            "sd_type": "population",
        }
    ]

    return overall_summary, run_summary, across_run_summary


def activity_hours(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    def count(keys: list[str]) -> list[dict[str, Any]]:
        counts: dict[tuple[Any, ...], int] = {}
        for row in rows:
            key = tuple(row[column] for column in keys)
            counts[key] = counts.get(key, 0) + 1

        output: list[dict[str, Any]] = []
        for key, hours in sorted(counts.items()):
            result = {
                **dict(zip(keys, key)),
                "hours": hours,
            }
            if "weekday" in keys:
                result["day_type"] = (
                    "weekday"
                    if int(result["weekday"]) < 5
                    else "weekend"
                )
            output.append(result)
        return output

    weekly = count(
        [
            "unique_agent_id",
            "base_seed",
            "persona_index",
            "activity_type",
        ]
    )
    daily = count(
        [
            "unique_agent_id",
            "base_seed",
            "persona_index",
            "weekday",
            "weekday_label",
            "activity_type",
        ]
    )
    return weekly, daily


def generate_psychological_constructs(
    agents: list[AgentRecord],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for agent in agents:
        state = build_psychological_state(
            agent.psychological_seed,
            method="multivariate_normal",
        )
        values = state["values_normalized"]

        if tuple(values.keys()) != ACTIVE_CONSTRUCTS:
            raise ValueError("Expected exactly nine active constructs")
        if any(not 0 <= float(value) <= 1 for value in values.values()):
            raise ValueError("values out of range")

        rows.append(
            {
                "unique_agent_id": agent.unique_agent_id,
                "base_seed": agent.base_seed,
                "persona_index": agent.persona_index,
                "persona_id": agent.persona_id,
                "persona_seed": agent.persona_seed,
                "psychological_seed": agent.psychological_seed,
                **values,
            }
        )

    return rows


def quantile(values: list[float], probability: float) -> float:
    sorted_values = sorted(values)
    position = (len(sorted_values) - 1) * probability
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    return sorted_values[lower_index] + (
        sorted_values[upper_index] - sorted_values[lower_index]
    ) * (position - lower_index)


def construct_summaries(
    psychological_rows: list[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    summary: list[dict[str, Any]] = []
    run_summary: list[dict[str, Any]] = []

    for construct in ACTIVE_CONSTRUCTS:
        values = [
            float(row[construct]) for row in psychological_rows
        ]
        q1 = quantile(values, 0.25)
        med = quantile(values, 0.5)
        q3 = quantile(values, 0.75)

        summary.append(
            {
                "construct": construct,
                "n": len(values),
                "mean": mean(values),
                "population_sd": (
                    pstdev(values) if len(values) > 1 else 0
                ),
                "minimum": min(values),
                "percentile_25": q1,
                "median": med,
                "percentile_75": q3,
                "maximum": max(values),
                "range": max(values) - min(values),
                "iqr": q3 - q1,
                "n_exactly_0": sum(value == 0 for value in values),
                "percent_exactly_0": (
                    100 * sum(value == 0 for value in values) / len(values)
                ),
                "n_exactly_1": sum(value == 1 for value in values),
                "percent_exactly_1": (
                    100 * sum(value == 1 for value in values) / len(values)
                ),
            }
        )

        for base_seed in sorted(
            {row["base_seed"] for row in psychological_rows}
        ):
            run_values = [
                float(row[construct])
                for row in psychological_rows
                if row["base_seed"] == base_seed
            ]
            run_summary.append(
                {
                    "base_seed": base_seed,
                    "construct": construct,
                    "n_agents": len(run_values),
                    "mean": mean(run_values),
                    "population_sd": (
                        pstdev(run_values) if len(run_values) > 1 else 0
                    ),
                    "minimum": min(run_values),
                    "maximum": max(run_values),
                }
            )

    correlations: list[dict[str, Any]] = []
    for construct_a in ACTIVE_CONSTRUCTS:
        row: dict[str, Any] = {"construct": construct_a}
        values_a = [
            float(item[construct_a]) for item in psychological_rows
        ]

        for construct_b in ACTIVE_CONSTRUCTS:
            values_b = [
                float(item[construct_b]) for item in psychological_rows
            ]
            mean_a = mean(values_a)
            mean_b = mean(values_b)
            denominator_a = sum(
                (value - mean_a) ** 2 for value in values_a
            ) ** 0.5
            denominator_b = sum(
                (value - mean_b) ** 2 for value in values_b
            ) ** 0.5

            if denominator_a and denominator_b:
                correlation = sum(
                    (value_a - mean_a) * (value_b - mean_b)
                    for value_a, value_b in zip(values_a, values_b)
                ) / (denominator_a * denominator_b)
            else:
                correlation = 0

            row[construct_b] = correlation

        correlations.append(row)

    return summary, run_summary, correlations


def reproducibility_summary(
    base_seed: int,
    agents_per_seed: int,
    phase: str,
) -> list[dict[str, Any]]:
    first = generate_agents([base_seed], agents_per_seed, phase)
    repeated = generate_agents([base_seed], agents_per_seed, phase)
    different = generate_agents([base_seed + 1], agents_per_seed, phase)

    first_schedules = generate_schedules(first)
    repeated_schedules = generate_schedules(repeated)
    different_schedules = generate_schedules(different)

    first_psychology = generate_psychological_constructs(first)
    repeated_psychology = generate_psychological_constructs(repeated)
    different_psychology = generate_psychological_constructs(different)

    return [
        {
            "check": "same_seed_persona_seeds_identical",
            "result": (
                [agent.persona_seed for agent in first]
                == [agent.persona_seed for agent in repeated]
            ),
        },
        {
            "check": "same_seed_schedules_identical",
            "result": (
                [
                    (
                        row["weekday"],
                        row["hour"],
                        row["activity_type"],
                        row["subtype"],
                    )
                    for row in first_schedules
                ]
                == [
                    (
                        row["weekday"],
                        row["hour"],
                        row["activity_type"],
                        row["subtype"],
                    )
                    for row in repeated_schedules
                ]
            ),
        },
        {
            "check": "same_seed_psychological_seeds_identical",
            "result": (
                [
                    row["psychological_seed"]
                    for row in first_psychology
                ]
                == [
                    row["psychological_seed"]
                    for row in repeated_psychology
                ]
            ),
        },
        {
            "check": "same_seed_psychological_values_identical",
            "result": (
                [
                    [row[construct] for construct in ACTIVE_CONSTRUCTS]
                    for row in first_psychology
                ]
                == [
                    [row[construct] for construct in ACTIVE_CONSTRUCTS]
                    for row in repeated_psychology
                ]
            ),
        },
        {
            "check": "different_base_seed_persona_seeds_differ",
            "result": (
                [agent.persona_seed for agent in first]
                != [agent.persona_seed for agent in different]
            ),
        },
        {
            "check": "different_base_seed_schedules_differ",
            "result": (
                [
                    row["activity_type"] for row in first_schedules
                ]
                != [
                    row["activity_type"] for row in different_schedules
                ]
            ),
        },
        {
            "check": "different_base_seed_psychological_values_differ",
            "result": (
                [
                    [row[construct] for construct in ACTIVE_CONSTRUCTS]
                    for row in first_psychology
                ]
                != [
                    [row[construct] for construct in ACTIVE_CONSTRUCTS]
                    for row in different_psychology
                ]
            ),
        },
    ]


def write_csv(
    path: Path,
    rows: Iterable[dict[str, Any]],
) -> None:
    output_rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as file:
        if not output_rows:
            return
        writer = csv.DictWriter(
            file,
            fieldnames=list(output_rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(output_rows)


def activity_codebook(
    schedules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    activities = sorted(
        {str(row["activity_type"]) for row in schedules}
    )
    return [
        {
            "activity_type": activity,
            "activity_code": code,
        }
        for code, activity in enumerate(activities)
    ]


def _ordered_schedule_agent_ids(
    schedules: list[dict[str, Any]],
) -> list[str]:
    return [
        unique_agent_id
        for _, _, unique_agent_id in sorted(
            {
                (
                    int(row["base_seed"]),
                    int(row["persona_index"]),
                    str(row["unique_agent_id"]),
                )
                for row in schedules
            }
        )
    ]


def _ordered_psychological_rows(
    psychological_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return sorted(
        psychological_rows,
        key=lambda row: (
            int(row["base_seed"]),
            int(row["persona_index"]),
        ),
    )


def _sparse_tick_positions(
    n_rows: int,
    max_ticks: int = 20,
) -> list[int]:
    if n_rows <= max_ticks:
        return list(range(n_rows))
    step = max(1, int(np.ceil(n_rows / max_ticks)))
    positions = list(range(0, n_rows, step))
    if positions[-1] != n_rows - 1:
        positions.append(n_rows - 1)
    return positions


def _short_agent_label(agent_id: str) -> str:
    if "_StudentPersona_" in agent_id:
        base, persona = agent_id.split("_StudentPersona_", 1)
        return f"{base} / P{persona}"
    return agent_id


def _save_figure(
    fig: Any,
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_schedule_heatmap(
    schedules: list[dict[str, Any]],
    codebook: list[dict[str, Any]],
    path: Path,
) -> None:
    agent_ids = _ordered_schedule_agent_ids(schedules)
    activity_to_code = {
        str(row["activity_type"]): int(row["activity_code"])
        for row in codebook
    }

    matrix = np.asarray(
        [
            [
                activity_to_code[activity]
                for activity in week_grid(schedules, agent_id)
            ]
            for agent_id in agent_ids
        ],
        dtype=int,
    )

    n_activities = max(len(codebook), 1)
    cmap = plt.get_cmap("tab20", n_activities)
    norm = BoundaryNorm(
        np.arange(-0.5, n_activities + 0.5, 1),
        cmap.N,
    )

    figure_height = max(5.5, min(12, 3.5 + len(agent_ids) * 0.06))
    fig, ax = plt.subplots(figsize=(15, figure_height))
    ax.imshow(
        matrix,
        aspect="auto",
        interpolation="nearest",
        cmap=cmap,
        norm=norm,
    )

    for boundary in range(24, TOTAL_WEEK_SLOTS, 24):
        ax.axvline(boundary - 0.5, linewidth=0.8)

    ax.set_xticks([11.5 + 24 * index for index in range(7)])
    ax.set_xticklabels(WEEKDAY_LABELS)
    ax.set_xlabel("Day of week")
    ax.set_ylabel("Agent realization")
    ax.set_title("Generated weekly routines")

    y_positions = _sparse_tick_positions(len(agent_ids))
    ax.set_yticks(y_positions)
    ax.set_yticklabels(
        [_short_agent_label(agent_ids[index]) for index in y_positions],
        fontsize=7,
    )

    legend_handles = [
        Patch(
            facecolor=cmap(int(row["activity_code"])),
            label=str(row["activity_type"]).replace("_", " "),
        )
        for row in codebook
    ]
    ax.legend(
        handles=legend_handles,
        title="Activity type",
        loc="upper left",
        bbox_to_anchor=(1.01, 1),
        borderaxespad=0,
        fontsize=8,
    )

    _save_figure(fig, path)


def plot_schedule_similarity_distribution(
    pairs: list[dict[str, Any]],
    path: Path,
) -> None:
    similarities = np.asarray(
        [float(pair["similarity_percent"]) for pair in pairs],
        dtype=float,
    )
    if similarities.size == 0:
        raise ValueError(
            "At least one pairwise schedule comparison is required for plotting"
        )

    mean_value = float(np.mean(similarities))
    median_value = float(np.median(similarities))
    n_bins = min(25, max(6, int(np.sqrt(similarities.size)) + 1))

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.hist(similarities, bins=n_bins, edgecolor="black", linewidth=0.6)
    ax.axvline(
        mean_value,
        linestyle="-",
        linewidth=1.5,
        label=f"Mean = {mean_value:.1f}%",
    )
    ax.axvline(
        median_value,
        linestyle="--",
        linewidth=1.5,
        label=f"Median = {median_value:.1f}%",
    )
    ax.set_xlim(0, 100)
    ax.set_xlabel("Schedule similarity (%)")
    ax.set_ylabel("Number of agent pairs")
    ax.set_title(
        "Distribution of within-run schedule similarity "
        f"(n = {similarities.size})"
    )
    ax.legend()

    _save_figure(fig, path)


def plot_schedule_run_means(
    run_summary: list[dict[str, Any]],
    path: Path,
) -> None:
    if not run_summary:
        raise ValueError("Run-level schedule summary is empty")

    ordered = sorted(
        run_summary,
        key=lambda row: int(row["base_seed"]),
    )
    x_positions = np.arange(len(ordered))
    means = np.asarray(
        [float(row["mean_similarity_percent"]) for row in ordered],
        dtype=float,
    )
    standard_deviations = np.asarray(
        [float(row["sd_similarity_percent"]) for row in ordered],
        dtype=float,
    )

    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    ax.errorbar(
        x_positions,
        means,
        yerr=standard_deviations,
        fmt="o",
        capsize=4,
        linewidth=1,
        label="Mean ± within-run SD",
    )
    ax.set_xticks(x_positions)
    ax.set_xticklabels(
        [str(row["base_seed"]) for row in ordered],
        rotation=45 if len(ordered) > 6 else 0,
        ha="right" if len(ordered) > 6 else "center",
    )
    ax.set_ylim(0, 100)
    ax.set_xlabel("Base seed")
    ax.set_ylabel("Mean schedule similarity (%)")
    ax.set_title("Mean schedule similarity by base seed")
    ax.legend()

    _save_figure(fig, path)


def plot_construct_heatmap(
    psychological_rows: list[dict[str, Any]],
    path: Path,
) -> None:
    ordered = _ordered_psychological_rows(psychological_rows)
    matrix = np.asarray(
        [
            [float(row[construct]) for construct in ACTIVE_CONSTRUCTS]
            for row in ordered
        ],
        dtype=float,
    )

    figure_height = max(5.5, min(12, 3.5 + len(ordered) * 0.06))
    fig, ax = plt.subplots(figsize=(11.5, figure_height))
    image = ax.imshow(
        matrix,
        aspect="auto",
        interpolation="nearest",
        vmin=0,
        vmax=1,
        cmap="viridis",
    )

    ax.set_xticks(np.arange(len(ACTIVE_CONSTRUCTS)))
    ax.set_xticklabels(
        [
            CONSTRUCT_DISPLAY_LABELS.get(
                construct,
                construct.replace("_", " "),
            )
            for construct in ACTIVE_CONSTRUCTS
        ],
        rotation=35,
        ha="right",
    )
    ax.set_ylabel("Agent realization")
    ax.set_title("Initial psychological construct profiles")

    agent_ids = [
        str(row["unique_agent_id"]) for row in ordered
    ]
    y_positions = _sparse_tick_positions(len(agent_ids))
    ax.set_yticks(y_positions)
    ax.set_yticklabels(
        [_short_agent_label(agent_ids[index]) for index in y_positions],
        fontsize=7,
    )

    colorbar = fig.colorbar(image, ax=ax, pad=0.02)
    colorbar.set_label("Normalized construct value")

    _save_figure(fig, path)


def plot_construct_boxplots(
    psychological_rows: list[dict[str, Any]],
    path: Path,
) -> None:
    values = [
        [
            float(row[construct])
            for row in psychological_rows
        ]
        for construct in ACTIVE_CONSTRUCTS
    ]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.boxplot(
        values,
        labels=[
            CONSTRUCT_DISPLAY_LABELS.get(
                construct,
                construct.replace("_", " "),
            ).replace("\n", " ")
            for construct in ACTIVE_CONSTRUCTS
        ],
        showfliers=True,
    )
    ax.set_ylim(0, 1)
    ax.set_ylabel("Normalized construct value")
    ax.set_title("Distribution of initial psychological constructs")
    ax.tick_params(axis="x", labelrotation=35)
    for label in ax.get_xticklabels():
        label.set_ha("right")

    _save_figure(fig, path)


def make_dirs(
    output_dir: Path,
    overwrite: bool,
) -> tuple[Path, Path, Path]:
    if output_dir.exists() and overwrite:
        shutil.rmtree(output_dir)

    data_dir = output_dir / "data"
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"

    for directory in (data_dir, tables_dir, figures_dir):
        directory.mkdir(parents=True, exist_ok=True)

    return data_dir, tables_dir, figures_dir


def md_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""

    columns = list(rows[0].keys())
    lines = [
        "|" + "|".join(columns) + "|",
        "|" + "|".join(["---"] * len(columns)) + "|",
    ]
    lines.extend(
        "|"
        + "|".join(str(row.get(column, "")) for column in columns)
        + "|"
        for row in rows[:20]
    )
    return "\n".join(lines)


def run_analysis(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir)
    data_dir, tables_dir, figures_dir = make_dirs(
        output_dir,
        args.overwrite,
    )

    seeds = base_seed_sequence(
        args.base_seed,
        args.n_base_seeds,
    )
    agents = generate_agents(
        seeds,
        args.agents_per_seed,
        args.phase,
    )
    schedules = generate_schedules(agents)
    psychological_rows = generate_psychological_constructs(agents)
    pairs = pairwise_schedule_similarity(schedules)
    weekly_hours, daily_hours = activity_hours(schedules)

    (
        overall_schedule_summary,
        run_schedule_summary,
        across_run_schedule_summary,
    ) = summarize_schedule_similarity(
        pairs,
        args.agents_per_seed,
    )

    (
        construct_summary,
        construct_run_summary,
        construct_correlations,
    ) = construct_summaries(psychological_rows)

    reproducibility = reproducibility_summary(
        args.base_seed,
        args.agents_per_seed,
        args.phase,
    )

    expected_pairs = args.n_base_seeds * (
        args.agents_per_seed * (args.agents_per_seed - 1) // 2
    )
    if len(pairs) != expected_pairs:
        raise ValueError("pair count mismatch")

    data_outputs = {
        "agent_schedules_long.csv": schedules,
        "agent_weekly_activity_hours.csv": weekly_hours,
        "agent_daily_activity_hours.csv": daily_hours,
        "initial_psychological_constructs.csv": psychological_rows,
        "pairwise_schedule_similarity.csv": pairs,
    }
    for filename, rows in data_outputs.items():
        write_csv(data_dir / filename, rows)

    table_outputs = {
        "schedule_similarity_overall_summary.csv": overall_schedule_summary,
        "schedule_similarity_run_summary.csv": run_schedule_summary,
        "schedule_similarity_across_run_means.csv": (
            across_run_schedule_summary
        ),
        "construct_heterogeneity_summary.csv": construct_summary,
        "construct_run_summary.csv": construct_run_summary,
        "construct_correlation_matrix.csv": construct_correlations,
        "reproducibility_summary.csv": reproducibility,
    }
    for filename, rows in table_outputs.items():
        write_csv(tables_dir / filename, rows)

    codebook = activity_codebook(schedules)
    write_csv(tables_dir / "activity_codebook.csv", codebook)

    plot_schedule_heatmap(
        schedules,
        codebook,
        figures_dir / "schedule_heatmap.png",
    )
    plot_schedule_similarity_distribution(
        pairs,
        figures_dir / "schedule_similarity_distribution.png",
    )
    plot_schedule_run_means(
        run_schedule_summary,
        figures_dir / "schedule_run_means.png",
    )
    plot_construct_heatmap(
        psychological_rows,
        figures_dir / "construct_heatmap.png",
    )
    plot_construct_boxplots(
        psychological_rows,
        figures_dir / "construct_boxplots.png",
    )

    config = {
        "n_base_seeds": args.n_base_seeds,
        "agents_per_seed": args.agents_per_seed,
        "base_seed": args.base_seed,
        "base_seeds": seeds,
        "phase": YearPhase.coerce(args.phase).value,
        "total_agents": len(agents),
        "total_schedule_rows": len(schedules),
        "total_pairwise_comparisons": len(pairs),
        "psychological_seed_offset": PSYCHOLOGICAL_SEED_OFFSET,
        "input_parameters": generic_student_inputs(),
        "sd_type": "population",
        "active_constructs": list(ACTIVE_CONSTRUCTS),
    }
    (output_dir / "run_config.json").write_text(
        json.dumps(config, indent=2),
        encoding="utf-8",
    )

    report = [
        "# H2 Agent Heterogeneity Report",
        "",
        (
            "> H2: The proposed agent-based simulation model can represent "
            "heterogeneous agents who differ in their individual "
            "characteristics, daily and weekly routines, and levels of "
            "psychological constructs."
        ),
        "",
        (
            "This analysis evaluates H2 descriptively; no inferential tests, "
            "p-values, or pass/fail thresholds are used."
        ),
        (
            f"Base seeds: {seeds}; agents per seed: "
            f"{args.agents_per_seed}; total agent realizations: "
            f"{len(agents)}; phase: {config['phase']}; common high-level "
            f"inputs: `{config['input_parameters']}`."
        ),
        (
            "Persona seeds come from `StudentWrapper.create_personas`; "
            "psychological seeds use `persona_seed + 10_000_019`; schedules "
            "use generated weekly structures and "
            "`generate_full_day_schedule` with `persona_seed + weekday` "
            "daily RNGs."
        ),
        (
            "Schedules are 168 hourly top-level activity-type labels. "
            "Similarity is matching slots / 168 and difference is "
            "1 - similarity. Population SD is reported."
        ),
        f"Total within-run pairwise comparisons: {len(pairs)}",
        "## Main schedule heterogeneity table",
        md_table(overall_schedule_summary),
        "## Main construct heterogeneity table",
        md_table(construct_summary),
        "## Figures",
        "- [Schedule heatmap](figures/schedule_heatmap.png)",
        (
            "- [Schedule similarity distribution]"
            "(figures/schedule_similarity_distribution.png)"
        ),
        "- [Schedule run means](figures/schedule_run_means.png)",
        "- [Construct heatmap](figures/construct_heatmap.png)",
        "- [Construct boxplots](figures/construct_boxplots.png)",
        "## Reproducibility results",
        md_table(reproducibility),
        (
            "Only nine active constructs are analysed: "
            f"{', '.join(ACTIVE_CONSTRUCTS)}. The legacy "
            "intrinsic-motivation subscales (`interest_enjoyment`, "
            "`perceived_competence`, `perceived_choice`, "
            "`pressure_tension`) are not separate model outputs."
        ),
        "## Limitations",
        "- simulated rather than empirical agents;",
        "- common high-level input parameters;",
        "- one controlled normal-phase week per agent;",
        (
            "- descriptive evidence does not establish real-world "
            "population validity;"
        ),
        (
            "- schedule similarity is based on top-level activity type "
            "and not subtype;"
        ),
        (
            "- psychological values are sampled from embedded reference "
            "parameters."
        ),
        "## Neutral conclusion",
        (
            "The descriptive outputs do not automatically accept or "
            "reject H2."
        ),
    ]
    (output_dir / "h2_heterogeneity_report.md").write_text(
        "\n\n".join(report),
        encoding="utf-8",
    )

    return config


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--n-base-seeds",
        type=int,
        default=10,
    )
    parser.add_argument(
        "--agents-per-seed",
        type=int,
        default=10,
    )
    parser.add_argument(
        "--base-seed",
        type=int,
        default=3263,
    )
    parser.add_argument(
        "--phase",
        default="normal",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
) -> None:
    args = parse_args(argv)
    result = {
        "output_dir": str(Path(args.output_dir)),
        **run_analysis(args),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
