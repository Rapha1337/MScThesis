from __future__ import annotations

from itertools import combinations
from statistics import mean, pstdev
from typing import Any


def week_to_7x24_activity_grid(week_structure: Any) -> list[list[str]]:
    """Normalize supported weekly structures to a Monday-Sunday 7x24 activity grid."""
    if isinstance(week_structure, list) and len(week_structure) == 7 and all(isinstance(day, list) and len(day) == 24 for day in week_structure):
        return [[str(slot) for slot in day] for day in week_structure]

    if isinstance(week_structure, dict) and set(week_structure.keys()) >= set(range(7)):
        grid: list[list[str]] = []
        for weekday in range(7):
            slots = ["unknown"] * 24
            for ep in week_structure[weekday]:
                hour = int(getattr(ep, "hour", ep.get("hour")))
                activity = getattr(ep, "activity_type", ep.get("activity_type"))
                activity_value = getattr(activity, "value", activity)
                slots[hour] = str(activity_value)
            grid.append(slots)
        return grid

    raise ValueError("Unsupported week structure format for 7x24 normalization")


def compare_week_structures(week_a: Any, week_b: Any) -> dict[str, float | int]:
    grid_a = week_to_7x24_activity_grid(week_a)
    grid_b = week_to_7x24_activity_grid(week_b)
    total_slots = 7 * 24
    matching_slots = sum(1 for d in range(7) for h in range(24) if grid_a[d][h] == grid_b[d][h])
    similarity = matching_slots / total_slots
    variance = 1.0 - similarity
    return {
        "matching_slots": matching_slots,
        "total_slots": total_slots,
        "similarity": similarity,
        "variance": variance,
        "similarity_percent": similarity * 100.0,
        "variance_percent": variance * 100.0,
    }


def summarize_pairwise_week_variance(weeks: list[Any]) -> dict[str, float | int]:
    pair_results = [compare_week_structures(a, b) for a, b in combinations(weeks, 2)]
    similarities = [x["similarity_percent"] for x in pair_results] if pair_results else [100.0]
    variances = [x["variance_percent"] for x in pair_results] if pair_results else [0.0]
    return {
        "n_weeks": len(weeks),
        "n_pairwise_comparisons": len(pair_results),
        "mean_similarity_percent": mean(similarities),
        "mean_variance_percent": mean(variances),
        "min_similarity_percent": min(similarities),
        "max_similarity_percent": max(similarities),
        "std_similarity_percent": pstdev(similarities) if len(similarities) > 1 else 0.0,
        "std_variance_percent": pstdev(variances) if len(variances) > 1 else 0.0,
    }
