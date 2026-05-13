from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import random

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from env_time_weather import TimeWeatherEnv
from bern_map import BernMap


# ============================================================
# HELPERS
# ============================================================

def make_env(
    month: int,
    horizon_hours: int,
    bern_map: BernMap,
    seed: int = 42,
) -> TimeWeatherEnv:
    """
    Creates the real environment using an already initialized BernMap.
    """
    env = TimeWeatherEnv(
        month=month,
        sample_rate_hours=1,
        horizon_hours=horizon_hours,
        bern_map=bern_map,
    )
    env.reset(seed=seed)
    return env


def run_random_policy(
    env: TimeWeatherEnv,
    max_steps: int | None = None,
    move_prob: float = 0.6,
) -> pd.DataFrame:
    """
    Runs the environment with a random stay/move policy.
    action 0 = stay
    action 1 = random activity
    """
    history: list[dict] = []
    step_idx = 0

    while True:
        if max_steps is not None and step_idx >= max_steps:
            break

        action = 1 if random.random() < move_prob else 0
        obs, reward, terminated, truncated, info = env.step(action)

        month, hour = env._month_hour(min(env._t, env.horizon_hours - 1))
        mobility = info["mobility"]

        history.append({
            "step": step_idx,
            "t": env._t,
            "month": month,
            "hour": hour,
            "action": action,
            "action_name": info["action_name"],
            "delta_hours": info["delta_hours"],
            "temp": env._temp,
            "precip_mm": env._precip,
            "wet": env._wet_prev,
            "sun_frac": env._sun_frac,
            "humidity": env._humidity,
            "wind": env._wind,
            "snow_cover_flag": env._snow_cover_flag,
            "feels_like": env._feels_like,
            "lat": info["lat"],
            "lon": info["lon"],
            "current_node": info["current_node"],
            "poi_category": mobility["target_category"],
            "poi_name": mobility["target_name"],
            "target_node": mobility["target_node"],
            "mode": mobility["mode"],
            "distance_m": mobility["distance_m"],
            "travel_time_min": mobility["travel_time_min"],
        })

        step_idx += 1

        if terminated or truncated:
            break

    return pd.DataFrame(history)


def save_console_summary(df: pd.DataFrame, title: str, out_txt: Path) -> None:
    """
    Saves a short console-style summary for Miro / presentation.
    Works robustly even if some columns are missing.
    """
    lines = [f"=== {title} ===", f"rows: {len(df)}", ""]

    if len(df) == 0:
        lines.append("DataFrame is empty.")
        out_txt.write_text("\n".join(lines), encoding="utf-8")
        return

    lines.append(f"columns: {list(df.columns)}")
    lines.append("")

    if "action" in df.columns:
        n_moves = int((df["action"] == 1).sum())
        n_stays = int((df["action"] == 0).sum())
        lines.append(f"moves: {n_moves}")
        lines.append(f"stays: {n_stays}")

    if "temp" in df.columns:
        lines.append(f"mean temperature: {df['temp'].mean():.2f} C")

    if "sun_frac" in df.columns:
        lines.append(f"mean sun fraction: {df['sun_frac'].mean():.2f}")

    if "wet" in df.columns:
        wet_hours = int((df["wet"] == 1).sum())
        lines.append(f"wet hours: {wet_hours}")

    if "delta_hours" in df.columns:
        lines.append(f"mean delta hours: {df['delta_hours'].mean():.2f}")
        lines.append(f"max delta hours: {df['delta_hours'].max():.2f}")

    if "travel_time_min" in df.columns:
        lines.append(f"mean travel time: {df['travel_time_min'].mean():.2f} min")

    if "distance_m" in df.columns:
        lines.append(f"mean distance: {df['distance_m'].mean():.2f} m")

    if "mode" in df.columns:
        lines.append(f"mode counts: {df['mode'].value_counts(dropna=False).to_dict()}")

    if "poi_category" in df.columns:
        lines.append(
            f"poi counts: {df['poi_category'].fillna('stay').value_counts().to_dict()}"
        )

    lines.append("")
    lines.append("First 10 rows:")
    lines.append(df.head(10).to_string(index=False))

    out_txt.write_text("\n".join(lines), encoding="utf-8")


def _save_single_plot(fig, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


# ============================================================
# CASE 1
# ============================================================

def case_1_short_term_behavior(
    out_dir: Path,
    bern_map: BernMap,
    start_month: int = 3,
    n_months: int = 2,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Start in March, simulate 2 months, random movement between POIs.
    """
    horizon_hours = 24 * 30 * n_months
    env = make_env(
        month=start_month,
        horizon_hours=horizon_hours,
        bern_map=bern_map,
        seed=seed,
    )
    df = run_random_policy(env, move_prob=0.7)

    out_csv = out_dir / "case_1_short_term_behavior.csv"
    out_txt = out_dir / "case_1_short_term_behavior_summary.txt"
    df.to_csv(out_csv, index=False)
    save_console_summary(df, "CASE 1: SHORT-TERM BEHAVIOR", out_txt)

    fig = plt.figure(figsize=(12, 5))
    plt.plot(df["t"], df["temp"], label="Temperature (C)")
    plt.plot(df["t"], df["sun_frac"], label="Sun fraction")
    plt.xlabel("Simulation time (hours)")
    plt.ylabel("Value")
    plt.title("Case 1 - Temperature and Sun Over Time")
    plt.legend()
    _save_single_plot(fig, out_dir / "case_1_temp_sun.png")

    fig = plt.figure(figsize=(12, 4))
    cat_map = {"gym": 1, "pool": 2, "park": 3, None: 0}
    y = df["poi_category"].map(cat_map).fillna(0)
    plt.plot(df["t"], y, marker="o", linestyle="-")
    plt.yticks([0, 1, 2, 3], ["stay", "gym", "pool", "park"])
    plt.xlabel("Simulation time (hours)")
    plt.ylabel("Visited category")
    plt.title("Case 1 - POI Category Timeline")
    _save_single_plot(fig, out_dir / "case_1_poi_timeline.png")

    fig = plt.figure(figsize=(8, 4))
    plt.hist(df["delta_hours"], bins=range(1, int(df["delta_hours"].max()) + 3), edgecolor="black")
    plt.xlabel("Delta hours per step")
    plt.ylabel("Frequency")
    plt.title("Case 1 - Distribution of Time Jumps")
    _save_single_plot(fig, out_dir / "case_1_delta_hist.png")

    return df


# ============================================================
# CASE 2
# ============================================================

def case_2_daily_cycle_validation(
    out_dir: Path,
    bern_map: BernMap,
    start_month: int = 3,
    days: int = 5,
    seed: int = 43,
) -> pd.DataFrame:
    """
    Focus on hourly weather cycle over a few days.
    """
    env = make_env(
        month=start_month,
        horizon_hours=24 * days,
        bern_map=bern_map,
        seed=seed,
    )
    df = run_random_policy(env, move_prob=0.0)

    out_csv = out_dir / "case_2_daily_cycle.csv"
    out_txt = out_dir / "case_2_daily_cycle_summary.txt"
    df.to_csv(out_csv, index=False)
    save_console_summary(df, "CASE 2: DAILY CYCLE VALIDATION", out_txt)

    fig = plt.figure(figsize=(10, 4))
    plt.plot(df["hour"], df["sun_frac"], marker="o", linestyle="None")
    plt.xlabel("Hour of day")
    plt.ylabel("Sun fraction")
    plt.title("Case 2 - Hour vs Sun Fraction")
    _save_single_plot(fig, out_dir / "case_2_hour_vs_sun.png")

    fig = plt.figure(figsize=(10, 4))
    plt.plot(df["hour"], df["temp"], marker="o", linestyle="None")
    plt.xlabel("Hour of day")
    plt.ylabel("Temperature (C)")
    plt.title("Case 2 - Hour vs Temperature")
    _save_single_plot(fig, out_dir / "case_2_hour_vs_temp.png")

    return df


# ============================================================
# CASE 3
# ============================================================

def case_3_mobility_impact_on_time(
    out_dir: Path,
    bern_map: BernMap,
    start_month: int = 3,
    seed: int = 44,
) -> pd.DataFrame:
    """
    Show that transport mode / travel time influence time progression.
    """
    env = make_env(
        month=start_month,
        horizon_hours=24 * 14,
        bern_map=bern_map,
        seed=seed,
    )
    env.reset(seed=seed)

    category = env.mobility.get_categories()[0]
    records = []

    for mode in ["walk", "bike", "drive"] * 5:
        env.mobility.reset_to_home()
        info = env.mobility.go_to_nearest(category, mode=mode)
        travel_time_min = float(info["travel_time_min"])
        delta_hours = max(env.sample_rate_hours, int(np.ceil(travel_time_min / 60.0)))

        records.append({
            "trial": len(records),
            "mode": mode,
            "travel_time_min": travel_time_min,
            "delta_hours": delta_hours,
            "distance_m": float(info["distance_m"]),
            "target_category": info["target_category"],
            "target_name": info["target_name"],
        })

    df = pd.DataFrame(records)

    out_csv = out_dir / "case_3_mobility_impact.csv"
    out_txt = out_dir / "case_3_mobility_impact_summary.txt"
    df.to_csv(out_csv, index=False)
    save_console_summary(df, "CASE 3: MOBILITY IMPACT ON TIME", out_txt)

    fig = plt.figure(figsize=(8, 4))
    plt.scatter(df["travel_time_min"], df["delta_hours"])
    plt.xlabel("Travel time (min)")
    plt.ylabel("Delta hours")
    plt.title("Case 3 - Travel Time vs Time Jump")
    _save_single_plot(fig, out_dir / "case_3_travel_vs_delta.png")

    fig = plt.figure(figsize=(8, 4))
    grouped = df.groupby("mode")["travel_time_min"].mean()
    plt.bar(grouped.index, grouped.values)
    plt.xlabel("Mode")
    plt.ylabel("Mean travel time (min)")
    plt.title("Case 3 - Mean Travel Time by Transport Mode")
    _save_single_plot(fig, out_dir / "case_3_mode_bar.png")

    return df


# ============================================================
# CASE 4
# ============================================================

def case_4_weather_behavior_interaction(
    out_dir: Path,
    bern_map: BernMap,
    start_month: int = 10,
    n_months: int = 2,
    seed: int = 45,
) -> pd.DataFrame:
    """
    Longer run to capture wet periods and lower sun during precipitation.
    Autumn start helps show weather variation.
    """
    env = make_env(
        month=start_month,
        horizon_hours=24 * 30 * n_months,
        bern_map=bern_map,
        seed=seed,
    )
    df = run_random_policy(env, move_prob=0.7)

    out_csv = out_dir / "case_4_weather_behavior.csv"
    out_txt = out_dir / "case_4_weather_behavior_summary.txt"
    df.to_csv(out_csv, index=False)
    save_console_summary(df, "CASE 4: WEATHER x BEHAVIOR INTERACTION", out_txt)

    fig = plt.figure(figsize=(12, 4))
    plt.plot(df["t"], df["precip_mm"], label="Precipitation (mm)")
    plt.plot(df["t"], df["sun_frac"], label="Sun fraction")
    plt.xlabel("Simulation time (hours)")
    plt.ylabel("Value")
    plt.title("Case 4 - Precipitation and Sun Over Time")
    plt.legend()
    _save_single_plot(fig, out_dir / "case_4_precip_sun.png")

    fig = plt.figure(figsize=(8, 4))
    wet_counts = df["wet"].value_counts().sort_index()
    plt.bar([str(x) for x in wet_counts.index], wet_counts.values)
    plt.xlabel("Wet flag")
    plt.ylabel("Count")
    plt.title("Case 4 - Frequency of Dry vs Wet Hours")
    _save_single_plot(fig, out_dir / "case_4_wet_counts.png")

    return df


# ============================================================
# CASE 5
# ============================================================

def case_5_system_stability(
    out_dir: Path,
    bern_map: BernMap,
    start_month: int = 1,
    n_months: int = 1,
    seed: int = 46,
) -> pd.DataFrame:
    """
    Stress test over a moderate horizon with frequent movement.
    Reduced version to keep runtime manageable on the real OSM graph.
    """
    env = make_env(
        month=start_month,
        horizon_hours=24 * 30 * n_months,
        bern_map=bern_map,
        seed=seed,
    )
    df = run_random_policy(env, max_steps=400, move_prob=0.7)

    finite_cols = ["temp", "precip_mm", "sun_frac", "humidity", "wind", "feels_like", "delta_hours"]
    finite_ok = np.isfinite(df[finite_cols].to_numpy()).all()

    out_csv = out_dir / "case_5_system_stability.csv"
    out_txt = out_dir / "case_5_system_stability_summary.txt"
    df.to_csv(out_csv, index=False)
    save_console_summary(df, "CASE 5: SYSTEM STABILITY", out_txt)

    extra = [
        "",
        f"finite values check: {finite_ok}",
        f"max delta_hours: {df['delta_hours'].max()}",
    ]
    out_txt.write_text(out_txt.read_text(encoding="utf-8") + "\n" + "\n".join(extra), encoding="utf-8")

    fig = plt.figure(figsize=(12, 4))
    plt.plot(df["t"], df["temp"], label="Temperature")
    plt.plot(df["t"], df["delta_hours"], label="Delta hours")
    plt.xlabel("Simulation time (hours)")
    plt.ylabel("Value")
    plt.title("Case 5 - Long Run Stability")
    plt.legend()
    _save_single_plot(fig, out_dir / "case_5_long_run.png")

    fig = plt.figure(figsize=(8, 4))
    plt.hist(df["travel_time_min"].fillna(0), bins=20, edgecolor="black")
    plt.xlabel("Travel time (min)")
    plt.ylabel("Frequency")
    plt.title("Case 5 - Travel Time Distribution")
    _save_single_plot(fig, out_dir / "case_5_travel_hist.png")

    return df


# ============================================================
# RUN ALL
# ============================================================

def run_all_cases(output_dir: str = "scenario_outputs") -> dict[str, pd.DataFrame]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # BernMap nur EINMAL laden
    bern_map = BernMap(dist_km=8.0)

    results: dict[str, pd.DataFrame] = {}
    results["case_1"] = case_1_short_term_behavior(out_dir, bern_map=bern_map)
    results["case_2"] = case_2_daily_cycle_validation(out_dir, bern_map=bern_map)
    results["case_3"] = case_3_mobility_impact_on_time(out_dir, bern_map=bern_map)
    results["case_4"] = case_4_weather_behavior_interaction(out_dir, bern_map=bern_map)
    results["case_5"] = case_5_system_stability(out_dir, bern_map=bern_map)

    overview = []
    for case_name, df in results.items():
        overview.append({
            "case": case_name,
            "rows": len(df),
            "n_columns": len(df.columns),
        })

    pd.DataFrame(overview).to_csv(out_dir / "overview.csv", index=False)
    print(f"All cases finished. Outputs saved to: {out_dir.resolve()}")
    return results


if __name__ == "__main__":
    run_all_cases()