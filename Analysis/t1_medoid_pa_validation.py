"""Reproducible, descriptive PA validation for the four empirical T1 medoids.

One production 90-day trajectory is generated per persona and the 7-, 30-, and
90-day results are nested prefixes.  Seed selection is deliberately based only
on YearStructure context; it never executes or examines a PA decision.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[1]
SIMULATION = ROOT / "Simulation"
for path in (ROOT, SIMULATION):
    if str(path) not in sys.path:
        sys.path.append(str(path))

from empirical_personas import load_empirical_personas  # noqa: E402
from run_full_pa_simulation import (  # noqa: E402
    LLM1_MAX_TOKENS,
    LLM2_MAX_TOKENS,
    MODEL_NAME,
    STATE_ASSESSMENT_MAX_TOKENS,
    TEMPERATURE,
    TOP_P,
    FullSimulationConfig,
    run_full_simulation,
)
from year_structure import (  # noqa: E402
    YearStructureGenerator,
    calendar_date_to_schedule_coordinates,
)

START_DATE = date(2026, 7, 9)
HORIZONS = (7, 30, 90)
N_PERSONAS = 4
DEFAULT_PERSONA_FILE = ROOT / "Analysis/results_t1_persona_clustering/11_primary_medoid_personas.csv"
DEFAULT_OUTPUT_DIR = ROOT / "Analysis/results_t1_medoid_pa_validation"
DECISIONS = ("do_planned_activity", "adapt_activity", "skip_activity", "extra_activity")
SELECTION_CRITERION = (
    "representative modal phase on all seven dates and no acute schedule-altering events"
)


def derive_persona_seeds(base_seed: int, n_personas: int = N_PERSONAS) -> list[int]:
    """Mirror production's ordered ``random.Random(base_seed).randint`` derivation."""
    rng = random.Random(int(base_seed))
    return [rng.randint(0, 2**31 - 1) for _ in range(n_personas)]


def phase_counts_and_representative_phase(profile: Any) -> tuple[dict[str, int], str]:
    """Derive a medoid's modal annual phase from its empirical week counts."""
    counts = {
        "normal": int(profile.normal_weeks),
        "high_stress": int(profile.stress_weeks),
        "holiday": int(profile.holiday_weeks),
    }
    maximum = max(counts.values())
    modes = [phase for phase, count in counts.items() if count == maximum]
    if len(modes) != 1:
        raise ValueError(
            f"Representative phase is ambiguous for {profile.persona_id}: {counts}."
        )
    return counts, modes[0]


def inspect_event_free_seed(
    base_seed: int,
    persona_file: str | Path = DEFAULT_PERSONA_FILE,
) -> dict[str, Any]:
    """Inspect representative phase and events in the initial validation window."""
    profiles = load_empirical_personas(persona_file)
    if len(profiles) != N_PERSONAS:
        raise ValueError(f"Expected exactly four medoid personas; found {len(profiles)}.")
    seeds = derive_persona_seeds(base_seed, len(profiles))
    persona_results: list[dict[str, Any]] = []
    valid = True
    for profile, persona_seed in zip(profiles, seeds, strict=True):
        phase_counts, representative_phase = phase_counts_and_representative_phase(profile)
        wrapper = profile.to_wrapper()
        structure = YearStructureGenerator(wrapper.year_structure_config()).generate_year(
            persona_id=profile.persona_id,
            persona_seed=persona_seed,
            parameters=wrapper,
        )
        days: list[dict[str, Any]] = []
        for offset in range(7):
            calendar_day = START_DATE + timedelta(days=offset)
            week_index, weekday = calendar_date_to_schedule_coordinates(calendar_day)
            week = structure.weeks[week_index]
            absolute_day = week_index * 7 + weekday
            active_events = [
                event for event in structure.events
                if event.start_week * 7 + event.start_day <= absolute_day
                < event.start_week * 7 + event.start_day + event.duration_days
            ]
            event_types = [event.event_type for event in active_events]
            day_valid = week.phase == representative_phase and not active_events
            valid = valid and day_valid
            days.append({
                "calendar_date": calendar_day.isoformat(),
                "week_index": week_index,
                "weekday": weekday,
                "phase": week.phase,
                "fixed_block_tag": week.fixed_block_tag,
                "active_event_ids": [event.event_id for event in active_events],
                "active_event_types": event_types,
                "illness_active": "illness" in event_types,
                "public_holiday_active": "public_holiday" in event_types,
                "valid": day_valid,
            })
        persona_results.append({
            "persona_id": profile.persona_id,
            "cluster": profile.cluster,
            "participant_id": profile.participant_id,
            "persona_seed": persona_seed,
            "phase_counts": phase_counts,
            "representative_phase": representative_phase,
            "phase_sequence": [day["phase"] for day in days],
            "days": days,
        })
    return {
        "selected_base_seed": int(base_seed),
        "derived_persona_seeds": seeds,
        "start_date": START_DATE.isoformat(),
        "validation_window_days": 7,
        "valid": valid,
        "selection_criterion": SELECTION_CRITERION,
        "representative_phase_used_for_selection": True,
        "event_free_used_for_selection": True,
        "pa_outcomes_used_for_selection": False,
        "correlations_used_for_selection": False,
        "personas": persona_results,
    }


def select_event_free_seed(
    persona_file: str | Path = DEFAULT_PERSONA_FILE,
    *,
    first_seed: int = 1,
    max_seed: int = 100_000,
) -> dict[str, Any]:
    """Return the lowest representative-phase, event-free base seed."""
    if first_seed < 1 or max_seed < first_seed:
        raise ValueError("Seed search requires 1 <= first_seed <= max_seed.")
    # Fail fast on the first invalid persona/day.  The full, auditable detail is
    # then generated once for the selected seed.  This makes a 100k upper bound
    # practical without changing a single production random draw.
    profiles = load_empirical_personas(persona_file)
    if len(profiles) != N_PERSONAS:
        raise ValueError(f"Expected exactly four medoid personas; found {len(profiles)}.")
    for base_seed in range(first_seed, max_seed + 1):
        candidate_valid = True
        for profile, persona_seed in zip(
            profiles, derive_persona_seeds(base_seed, len(profiles)), strict=True
        ):
            _, representative_phase = phase_counts_and_representative_phase(profile)
            wrapper = profile.to_wrapper()
            structure = YearStructureGenerator(wrapper.year_structure_config()).generate_year(
                persona_id=profile.persona_id, persona_seed=persona_seed, parameters=wrapper
            )
            for offset in range(7):
                week_index, weekday = calendar_date_to_schedule_coordinates(
                    START_DATE + timedelta(days=offset)
                )
                week = structure.weeks[week_index]
                absolute_day = week_index * 7 + weekday
                if week.phase != representative_phase or any(
                        event.start_week * 7 + event.start_day <= absolute_day
                        < event.start_week * 7 + event.start_day + event.duration_days
                        for event in structure.events
                    ):
                    candidate_valid = False
                    break
            if not candidate_valid:
                break
        if candidate_valid:
            result = inspect_event_free_seed(base_seed, persona_file)
            result.update({"search_first_seed": first_seed, "search_max_seed": max_seed})
            return result
    raise RuntimeError(
        f"No base seed satisfying the representative event-free initial-window criterion found in "
        f"{first_seed}..{max_seed}."
    )


def load_empirical_pa(persona_file: str | Path = DEFAULT_PERSONA_FILE) -> pd.DataFrame:
    """Read individual (not cluster-mean) observed PA values from the medoid CSV."""
    rows = []
    with Path(persona_file).open(encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle):
            cluster = int(raw["cluster"])
            participant = str(raw["participant_id"])
            rows.append({
                "cluster": cluster,
                "participant_id": participant,
                "persona_id": f"T1_Medoid_C{cluster}_{participant}",
                "occupation": raw["occupational_status"],
                "empirical_mvpa_hours_week": float(raw["pa_mvpa_hours_per_week"]),
                "empirical_total_pa_hours_week": float(raw["pa_total_hours_per_week"]),
            })
    if len(rows) != N_PERSONAS:
        raise ValueError(f"Expected exactly four medoid rows; found {len(rows)}.")
    return pd.DataFrame(rows)


def _planned_duration(value: Any) -> float:
    if not isinstance(value, Mapping):
        return 0.0
    duration = value.get("duration_min")
    return float(duration) if duration is not None else 0.0


def daily_rows_from_trace(trace: Mapping[str, Any], empirical: pd.DataFrame) -> pd.DataFrame:
    """Flatten production trace records without imputing unobserved duration."""
    lookup = empirical.set_index("persona_id").to_dict("index")
    rows: list[dict[str, Any]] = []
    for record in trace.get("records", []):
        persona_id = str(record["persona_id"])
        decision = str(record["pa_decision"]["decision_label"])
        planned = record.get("planned_physical_activity")
        duration = _planned_duration(planned)
        performed = bool(record["closed_loop_update"]["activity_done"])
        # This proxy credits the scheduled duration for successful planned PA.
        # In particular, extra activity is always zero because its duration is unknown.
        proxy = duration if decision in {"do_planned_activity", "adapt_activity"} else 0.0
        metadata = lookup[persona_id]
        rows.append({
            "persona_id": persona_id,
            "cluster": metadata["cluster"],
            "participant_id": metadata["participant_id"],
            "calendar_date": record["calendar_date"],
            "day_index": int(record["day_index"]),
            "week_index": int(record["week_index"]),
            "phase": record["phase"],
            "weekday": int(record["weekday"]),
            "was_physical_activity_planned_today": bool(record["was_physical_activity_planned_today"]),
            "planned_duration_min": duration,
            "decision_label": decision,
            "activity_performed": performed,
            "active_day": performed,
            "proxy_realized_planned_minutes": proxy,
            "psychological_constructs_before": json.dumps(record.get("psychological_constructs_before_update", {}), sort_keys=True),
            "psychological_constructs_after": json.dumps(record.get("psychological_constructs_after_update", {}), sort_keys=True),
        })
    return pd.DataFrame(rows)


def summarize_horizons(daily: pd.DataFrame, empirical: pd.DataFrame) -> pd.DataFrame:
    """Calculate nested-prefix primary and secondary outcomes."""
    output: list[dict[str, Any]] = []
    expected_personas = set(empirical["persona_id"])
    for horizon in HORIZONS:
        window = daily[daily["day_index"] < horizon]
        if set(window["persona_id"]) != expected_personas:
            raise ValueError(f"Horizon {horizon} does not contain every empirical persona.")
        for persona_id, group in window.groupby("persona_id", sort=False):
            if len(group) != horizon or group["day_index"].nunique() != horizon:
                raise ValueError(f"{persona_id} must have exactly {horizon} unique days in horizon {horizon}.")
            meta = empirical.loc[empirical["persona_id"] == persona_id].iloc[0]
            active_days = int(group["activity_performed"].astype(bool).sum())
            planned_mask = group["was_physical_activity_planned_today"].astype(bool)
            successful_mask = planned_mask & group["decision_label"].isin(
                ["do_planned_activity", "adapt_activity"]
            )
            skipped_mask = planned_mask & group["decision_label"].eq("skip_activity")
            planned_days = int(planned_mask.sum())
            scheduled_minutes = float(group.loc[planned_mask, "planned_duration_min"].sum())
            realized_minutes = float(group["proxy_realized_planned_minutes"].sum())
            scheduled_hours_week = scheduled_minutes / 60 / horizon * 7
            realized_hours_week = realized_minutes / 60 / horizon * 7
            row = {
                "horizon_days": horizon,
                "cluster": int(meta["cluster"]),
                "participant_id": str(meta["participant_id"]),
                "persona_id": persona_id,
                "occupation": meta["occupation"],
                "empirical_mvpa_hours_week": float(meta["empirical_mvpa_hours_week"]),
                "n_days": horizon,
                "active_days": active_days,
                "inactive_days": horizon - active_days,
                "active_day_proportion": active_days / horizon,
                "active_days_per_week": active_days / horizon * 7,
                "planned_pa_days": planned_days,
                "successful_planned_pa_days": int(successful_mask.sum()),
                "skipped_planned_pa_days": int(skipped_mask.sum()),
                "planned_pa_adherence_rate": (int(successful_mask.sum()) / planned_days if planned_days else math.nan),
                "extra_activity_days": int(group["decision_label"].eq("extra_activity").sum()),
                "extra_activity_days_per_week": int(group["decision_label"].eq("extra_activity").sum()) / horizon * 7,
                "normal_days": int(group["phase"].eq("normal").sum()),
                "high_stress_days": int(group["phase"].eq("high_stress").sum()),
                "holiday_days": int(group["phase"].eq("holiday").sum()),
                # Pre-decision, input-informed scheduler baseline.
                "scheduled_planned_pa_days": planned_days,
                "scheduled_planned_pa_days_per_week": planned_days / horizon * 7,
                "scheduled_planned_pa_minutes": scheduled_minutes,
                "scheduled_planned_pa_hours_per_week": scheduled_hours_week,
                # Retain the original name alongside the explicit scheduler name.
                "planned_pa_minutes": scheduled_minutes,
                "realized_planned_pa_minutes_proxy": realized_minutes,
                "realized_planned_pa_hours_per_week_proxy": realized_hours_week,
                "planned_pa_realization_ratio": (realized_minutes / scheduled_minutes if scheduled_minutes else math.nan),
                "planned_pa_realization_delta_hours_per_week": realized_hours_week - scheduled_hours_week,
            }
            for decision in DECISIONS:
                row[f"decision_count_{decision}"] = int(group["decision_label"].eq(decision).sum())
            output.append(row)
    summary = pd.DataFrame(output)
    summary["empirical_rank"] = summary.groupby("horizon_days")["empirical_mvpa_hours_week"].rank(method="average", ascending=False)
    summary["simulated_rank"] = summary.groupby("horizon_days")["active_days_per_week"].rank(method="average", ascending=False)
    return summary


def _correlation(x: pd.Series, y: pd.Series, method: str) -> tuple[float, float]:
    if x.nunique(dropna=True) < 2 or y.nunique(dropna=True) < 2:
        return math.nan, math.nan
    result = spearmanr(x, y) if method == "spearman" else pearsonr(x, y)
    return float(result.statistic), float(result.pvalue)


def calculate_correlations(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    metrics = (
        ("scheduled_planned_pa_hours_per_week", "spearman", False, "pre_decision_input_informed_baseline"),
        ("scheduled_planned_pa_days_per_week", "spearman", False, "pre_decision_input_informed_baseline"),
        ("active_days_per_week", "spearman", True, "post_decision"),
        ("active_days_per_week", "pearson", False, "post_decision"),
        ("planned_pa_adherence_rate", "spearman", False, "behavioral_transformation"),
        ("realized_planned_pa_hours_per_week_proxy", "spearman", False, "post_decision"),
    )
    for horizon, group in summary.groupby("horizon_days", sort=True):
        for metric, method, primary, analysis_stage in metrics:
            complete = group[["empirical_mvpa_hours_week", metric]].dropna()
            coefficient, pvalue = _correlation(complete.iloc[:, 0], complete.iloc[:, 1], method)
            rows.append({
                "horizon_days": int(horizon), "n_personas": len(complete),
                "empirical_variable": "empirical_mvpa_hours_week",
                "simulated_variable": metric, "method": method,
                "analysis_stage": analysis_stage,
                "role": "primary" if primary else "secondary_descriptive",
                "coefficient": coefficient, "exploratory_p_value": pvalue,
            })
    return pd.DataFrame(rows)


def _format_coefficient(value: float) -> str:
    return "NA" if pd.isna(value) else f"{value:.3f}"


def _dataframe_markdown(frame: pd.DataFrame) -> str:
    """Render a small table without pandas' optional ``tabulate`` dependency."""
    columns = list(frame.columns)
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for values in frame.itertuples(index=False, name=None):
        cells = []
        for value in values:
            cells.append(f"{value:.3f}" if isinstance(value, float) else str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def build_report(seed: Mapping[str, Any], summary: pd.DataFrame, correlations: pd.DataFrame) -> str:
    primary = correlations[(correlations["role"] == "primary")]
    coefficients = list(primary.sort_values("horizon_days")["coefficient"])
    finite = [value for value in coefficients if not pd.isna(value)]
    if len(finite) < 2:
        trend = "not assessable because one or more coefficients are undefined"
    elif finite[-1] > finite[0] + 0.05:
        trend = "increases"
    elif finite[-1] < finite[0] - 0.05:
        trend = "decreases"
    else:
        trend = "stays similar"
    lines = [
        "# Empirical T1 medoid physical-activity correspondence analysis", "",
        "## Design and seed selection", "",
        f"Base seed **{seed['selected_base_seed']}** was the first ascending seed satisfying: {SELECTION_CRITERION}. ",
        "The first seven dates form a representative event-free initial validation window. Each persona must remain in its modal annual phase, derived from that medoid's empirical normal/high-stress/holiday week counts, and have no acute stochastic schedule-altering event. Exact calendar placement is synthetic because T1 does not identify the phase on 2026-07-09; using the modal phase provides a representative realization without forcing every persona into the same context. Thus C1/C2/C3 begin in normal phase, while C4 begins in high-stress because 37 of its 52 reported weeks are high-stress. Selection makes no LLM calls and examines no PA outcome or correlation. Actual phase remains available daily and is summarized for every persona and horizon.", "",
        "A single continuous 90-day simulation begins 2026-07-09. The 7-, 30-, and 90-day estimates are nested prefixes of that trajectory, rather than independent simulations.", "",
        "## Measures", "",
        "The empirical comparator is each observed medoid person's `pa_mvpa_hours_per_week`, not a cluster mean. Empirical T1 MVPA is also used to parameterize planned PA opportunities. Therefore correspondence between T1 MVPA and simulated realized PA is partly input-informed and cannot be interpreted as independent out-of-sample validation or prediction accuracy.", "",
        "This internal behavioral reproduction analysis evaluates: (1) how the scheduler translates empirical PA into planned opportunities; (2) how LLM2 and context transform those opportunities into realized behavior; (3) whether between-person ordering is retained, amplified, or attenuated; and (4) how correspondence changes across 7, 30, and 90 days as psychological states evolve.", "",
        "The primary post-decision simulated measure is active days per week, where a day is active exactly when `activity_performed == true`. It is a behavioral consistency check of relative correspondence, not absolute agreement in hours.", "",
        "Planned-duration results are explicitly **PROXY** measures. `do_planned_activity` and `adapt_activity` receive scheduled duration; `skip_activity` receives zero. No duration is invented for `extra_activity`. Actual adapted and extra-activity duration is unavailable.", "",
        "## Pre-decision, input-informed scheduler baseline", "",
        "These correlations quantify correspondence already present because empirical MVPA was supplied to the scheduler. They are not model validation.", "",
        "| horizon | scheduled hours/week Spearman | scheduled days/week Spearman |", "|---:|---:|---:|",
    ]
    for horizon in HORIZONS:
        subset = correlations[correlations.horizon_days == horizon]
        hours = subset[(subset.simulated_variable == "scheduled_planned_pa_hours_per_week") & (subset.method == "spearman")].iloc[0].coefficient
        days = subset[(subset.simulated_variable == "scheduled_planned_pa_days_per_week") & (subset.method == "spearman")].iloc[0].coefficient
        lines.append(f"| {horizon} | {_format_coefficient(hours)} | {_format_coefficient(days)} |")
    lines += ["", "## Post-decision empirical correspondence", "",
              "Post-decision correlations remain partly input-informed and are not independent prediction accuracy.", "",
              "| horizon | active days/week Spearman | active days/week Pearson | realized planned hours/week PROXY Spearman |", "|---:|---:|---:|---:|"]
    for horizon in HORIZONS:
        subset = correlations[correlations.horizon_days == horizon]
        active = subset[subset.simulated_variable == "active_days_per_week"]
        realized = subset[(subset.simulated_variable == "realized_planned_pa_hours_per_week_proxy") & (subset.method == "spearman")].iloc[0].coefficient
        spear = active[active.method == "spearman"].iloc[0].coefficient
        pear = active[active.method == "pearson"].iloc[0].coefficient
        lines.append(f"| {horizon} | {_format_coefficient(spear)} | {_format_coefficient(pear)} | {_format_coefficient(realized)} |")
    lines += ["", f"From 7 to 90 days, primary correspondence **{trend}** (0.05 is used only as a descriptive similarity tolerance). Interpret direction, magnitude, ordering, and horizon-to-horizon change; no decline is assumed in advance.", "",
              "All correlations and p-values are descriptive/exploratory with **n=4** and are not meaningful inferential evidence. Ties can materially affect rank correlation. Psychological constructs evolve during the trajectory, so later correspondence may increase, decrease, or remain similar.", "", "## Persona ordering", ""]
    display = summary[["horizon_days", "cluster", "participant_id", "empirical_mvpa_hours_week", "empirical_rank", "active_days", "active_days_per_week", "simulated_rank", "normal_days", "high_stress_days", "holiday_days"]]
    lines.append(_dataframe_markdown(display))
    lines += ["", "## Behavioral transformation", ""]
    transformation = summary[["horizon_days", "cluster", "participant_id", "scheduled_planned_pa_days_per_week", "scheduled_planned_pa_hours_per_week", "planned_pa_adherence_rate", "planned_pa_realization_ratio", "planned_pa_realization_delta_hours_per_week", "extra_activity_days_per_week"]]
    lines.append(_dataframe_markdown(transformation))
    lines += ["", "## Limitations", "", "This is an internal, descriptive comparison of four selected medoid people, not external validation or evidence of predictive accuracy. Active days do not measure duration or intensity. The planned-duration proxy cannot recover actual adapted or extra-activity duration, and T1 is a baseline snapshot compared with an evolving simulation.", ""]
    return "\n".join(lines)


def write_analysis_outputs(output_dir: Path, seed: Mapping[str, Any], trace: Mapping[str, Any], persona_file: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    empirical = load_empirical_pa(persona_file)
    daily = daily_rows_from_trace(trace, empirical)
    summary = summarize_horizons(daily, empirical)
    correlations = calculate_correlations(summary)
    (output_dir / "01_seed_selection.json").write_text(json.dumps(seed, indent=2), encoding="utf-8")
    empirical.to_csv(output_dir / "02_persona_empirical_pa.csv", index=False)
    daily.to_csv(output_dir / "03_daily_simulated_pa.csv", index=False)
    summary.to_csv(output_dir / "04_horizon_persona_summary.csv", index=False)
    correlations.to_csv(output_dir / "05_horizon_correlations.csv", index=False)
    (output_dir / "06_validation_report.md").write_text(build_report(seed, summary, correlations), encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--persona-input-file", type=Path, default=DEFAULT_PERSONA_FILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--base-seed", type=int, help="Override automatic lowest-valid seed selection.")
    parser.add_argument("--skip-event-free-check", action="store_true", help="Allow an explicitly overridden seed that fails the representative-phase or event-free initial-window check.")
    parser.add_argument("--max-seed", type=int, default=100_000)
    parser.add_argument("--seed-only", action="store_true", help="Find/verify and record the seed without running the simulation.")
    parser.add_argument("--analyze-only", action="store_true", help="Analyze an existing simulation/full_simulation_trace.json.")
    parser.add_argument("--dry-run", action="store_true", help="Use the production no-LLM mock pipeline.")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--disable-resource-tracking", action="store_true")
    parser.add_argument("--disable-codecarbon", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    seed = (inspect_event_free_seed(args.base_seed, args.persona_input_file)
            if args.base_seed is not None else
            select_event_free_seed(args.persona_input_file, max_seed=args.max_seed))
    seed["selection_mode"] = "explicit_override" if args.base_seed is not None else "lowest_valid_ascending_search"
    if not seed["valid"] and not (args.base_seed is not None and args.skip_event_free_check):
        raise ValueError("The requested base seed does not provide a representative event-free initial validation window. Use --skip-event-free-check only for an intentional exception.")
    (args.output_dir / "01_seed_selection.json").write_text(json.dumps(seed, indent=2), encoding="utf-8")
    if args.seed_only:
        print(json.dumps(seed, indent=2))
        return
    simulation_dir = args.output_dir / "simulation"
    trace_path = simulation_dir / "full_simulation_trace.json"
    if args.analyze_only:
        if not trace_path.is_file():
            raise FileNotFoundError(f"Existing production trace not found: {trace_path}")
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
    else:
        config = FullSimulationConfig(
            n_personas=N_PERSONAS, n_days=90, start_date=START_DATE,
            base_seed=int(seed["selected_base_seed"]), output_dir=simulation_dir,
            model=args.model, temperature=TEMPERATURE, top_p=TOP_P,
            llm_seed=None, llm1_max_tokens=LLM1_MAX_TOKENS,
            llm2_max_tokens=LLM2_MAX_TOKENS,
            state_assessment_max_tokens=STATE_ASSESSMENT_MAX_TOKENS,
            state_assessment_json_mode=False, dry_run=args.dry_run,
            include_full_hourly_context=False, enable_resource_tracking=not args.disable_resource_tracking,
            enable_codecarbon=not args.disable_codecarbon, resume=args.resume,
            persona_input_file=args.persona_input_file,
        )
        trace = run_full_simulation(config)
    write_analysis_outputs(args.output_dir, seed, trace, args.persona_input_file)
    run_config = {
        "study": "T1 empirical medoid PA validation", "start_date": START_DATE.isoformat(),
        "n_days": 90, "nested_horizons_days": list(HORIZONS), "n_personas": N_PERSONAS,
        "base_seed": seed["selected_base_seed"], "persona_seeds": seed["derived_persona_seeds"],
        "persona_input_file": str(args.persona_input_file), "simulation_output_dir": str(simulation_dir),
        "dry_run": args.dry_run, "resume": args.resume,
        "primary_empirical_metric": "pa_mvpa_hours_per_week",
        "primary_simulated_metric": "active_days_per_week",
    }
    (args.output_dir / "run_config.json").write_text(json.dumps(run_config, indent=2), encoding="utf-8")
    print(json.dumps(run_config, indent=2))


if __name__ == "__main__":
    main()
