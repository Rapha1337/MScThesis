from __future__ import annotations

import argparse, json, math, sys, types
from pathlib import Path
from typing import Iterable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "Simulation"
if str(SIM) not in sys.path:
    sys.path.insert(0, str(SIM))
if "osmnx" not in sys.modules:
    sys.modules["osmnx"] = types.ModuleType("osmnx")
from env_time_weather import TimeWeatherEnv

MONTH_LABELS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
REFERENCE_DAYS = dict(zip(range(1,13), [31,28.2666667,31,30,31,30,31,31,30,31,30,31]))
QUANTILES = [0.0, .2, .4, .6, .8, 1.0]

class WeatherOnlyBernMap:
    """Minimal local BernMap stub matching TimeWeatherEnv mobility calls without OSM/network access."""
    def __init__(self) -> None: self._next_node = 1
    def sample_random_node(self):
        n = self._next_node; self._next_node += 1; return n, 46.0 + n*.001, 7.0 + n*.001
    def get_node_position(self, node_id: int, mode: str = "walk"):
        del mode; return 46.0 + int(node_id)*.001, 7.0 + int(node_id)*.001
    def shortest_path_length_m(self, source_node: int, target_node: int, mode: str = "walk") -> float:
        del mode; return abs(int(target_node)-int(source_node))*100.0
    def travel_time_minutes(self, source_node: int, target_node: int, speed_kmh: float, mode: str = "walk") -> float:
        del mode; return self.shortest_path_length_m(source_node, target_node)/1000.0/speed_kmh*60.0
    def nearest_node(self, lat: float, lon: float, mode: str = "walk"):
        del lat, lon, mode; return 1, 46.001, 7.001
    def travel_time_minutes_from_positions(self, source_lat: float, source_lon: float, target_lat: float, target_lon: float, speed_kmh: float, mode: str = "drive") -> float:
        del mode; return (abs(target_lat-source_lat)+abs(target_lon-source_lon))/speed_kmh*60.0

def load_reference(path: Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or ROOT/"Analysis/data/zollikofen_climate_normals_1991_2020.csv", comment="#")
    expected = {"month","month_number","reference_month_days","temperature_mean_c","precipitation_total_mm"}
    missing = expected - set(df.columns)
    if missing: raise ValueError(f"Reference data missing columns: {sorted(missing)}")
    return df.sort_values("month_number").reset_index(drop=True)

def seeds(n_years: int, base_seed: int) -> list[int]:
    if n_years < 1: raise ValueError("--n-years must be at least 1")
    return list(range(base_seed, base_seed+n_years))

def possible_daylight_hours(env: TimeWeatherEnv, month: int, days: float = 30.0) -> float:
    return max(0.0, float(env._month_sunset_hour[month] - env._month_sunrise_hour[month])) * days

def standardize_extensive(native_value: float, month: int) -> float:
    return float(native_value) / 30.0 * REFERENCE_DAYS[int(month)]

def simulate_one_year(seed: int, model_year_index: int = 0) -> pd.DataFrame:
    env = TimeWeatherEnv(month=1, sample_rate_hours=1, horizon_hours=24*360, bern_map=WeatherOnlyBernMap())
    env.reset(seed=seed)
    rows = []
    for absolute_hour in range(24*360):
        st = env.get_environment_state()
        month = int(st["month"]); hour = int(st["hour"]); model_day = absolute_hour//24 + 1
        rows.append({"seed": seed, "model_year_index": model_year_index, "absolute_hour": absolute_hour,
            "model_day": model_day, "month": month, "day_in_month": ((model_day-1)%30)+1, "hour": hour,
            "temperature_c": st["temperature_c"], "feels_like_c": st["feels_like_c"], "precipitation_mm": st["precipitation_mm"],
            "is_wet": bool(st["is_wet"]), "sun_frac": st["sun_frac"], "humidity_pct": st["humidity_pct"],
            "wind_m_s": st["wind_m_s"], "snow_cover": bool(st["snow_cover"])})
        if absolute_hour < 24*360-1: env.step(0)
    df = pd.DataFrame(rows)
    validate_hourly_year(df)
    return df

def validate_hourly_year(df: pd.DataFrame) -> None:
    if len(df) != 8640: raise ValueError(f"Expected 8,640 hours, got {len(df)}")
    if df.model_day.nunique() != 360: raise ValueError("Expected 360 model days")
    if sorted(df.month.unique()) != list(range(1,13)): raise ValueError("Expected 12 months")
    counts = df.groupby("month").size()
    if not (counts == 720).all(): raise ValueError("Expected 720 hours per model month")
    days = df.groupby("month").day_in_month.nunique()
    if not (days == 30).all(): raise ValueError("Expected 30 days per model month")

def simulate_years(seed_list: Iterable[int]) -> pd.DataFrame:
    return pd.concat([simulate_one_year(s, i) for i, s in enumerate(seed_list)], ignore_index=True)

def aggregate_daily(hourly: pd.DataFrame) -> pd.DataFrame:
    """Aggregate hourly weather to 360-day model days; precipitation thresholds use daily sums."""
    required = {"seed","model_year_index","model_day","month","day_in_month","temperature_c","precipitation_mm","sun_frac","humidity_pct","wind_m_s","snow_cover"}
    missing = required - set(hourly.columns)
    if missing: raise ValueError(f"Hourly data missing columns: {sorted(missing)}")
    g = hourly.groupby(["seed","model_year_index","model_day","month","day_in_month"], sort=True)
    d = g.agg(temperature_mean_c=("temperature_c","mean"), temperature_max_c=("temperature_c","max"), temperature_min_c=("temperature_c","min"),
              precipitation_total_mm=("precipitation_mm","sum"), sunshine_equivalent_hours=("sun_frac","sum"), humidity_pct=("humidity_pct","mean"),
              wind_m_s=("wind_m_s","mean"), snow_cover_day=("snow_cover","max")).reset_index()
    d["ice_day"] = d.temperature_max_c < 0; d["frost_day"] = d.temperature_min_c < 0
    d["summer_day"] = d.temperature_max_c >= 25; d["heat_day"] = d.temperature_max_c >= 30
    for th in [1,5,10,50]: d[f"precip_day_ge_{th}mm"] = d.precipitation_total_mm >= th
    return d.sort_values(["seed","model_day"]).reset_index(drop=True)

def aggregate_monthly(daily: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily data to native 30-day months and standardized Gregorian-comparable values."""
    g = daily.groupby(["seed","model_year_index","month"], sort=True)
    m = g.agg(temperature_mean_c=("temperature_mean_c","mean"), temperature_daily_max_mean_c=("temperature_max_c","mean"), temperature_daily_min_mean_c=("temperature_min_c","mean"),
              precipitation_native_30d_mm=("precipitation_total_mm","sum"), sunshine_native_30d_hours=("sunshine_equivalent_hours","sum"),
              humidity_pct=("humidity_pct","mean"), wind_m_s=("wind_m_s","mean"), ice_days_native_30d=("ice_day","sum"), frost_days_native_30d=("frost_day","sum"),
              summer_days_native_30d=("summer_day","sum"), heat_days_native_30d=("heat_day","sum"), snow_cover_days_native_30d=("snow_cover_day","sum"),
              precip_days_ge_1mm_native_30d=("precip_day_ge_1mm","sum"), precip_days_ge_5mm_native_30d=("precip_day_ge_5mm","sum"),
              precip_days_ge_10mm_native_30d=("precip_day_ge_10mm","sum"), precip_days_ge_50mm_native_30d=("precip_day_ge_50mm","sum")).reset_index()
    env = TimeWeatherEnv(month=1, sample_rate_hours=1, horizon_hours=24*360, bern_map=WeatherOnlyBernMap())
    for col in ["precipitation","sunshine","ice_days","frost_days","summer_days","heat_days","snow_cover_days","precip_days_ge_1mm","precip_days_ge_5mm","precip_days_ge_10mm","precip_days_ge_50mm"]:
        native = "precipitation_native_30d_mm" if col=="precipitation" else "sunshine_native_30d_hours" if col=="sunshine" else f"{col}_native_30d"
        out = "precipitation_total_mm" if col=="precipitation" else "sunshine_hours" if col=="sunshine" else col
        m[out] = [standardize_extensive(v, mo) for v, mo in zip(m[native], m.month)]
    m["sunshine_pct"] = [100.0*s/possible_daylight_hours(env, int(mo), 30.0) for s, mo in zip(m.sunshine_native_30d_hours, m.month)]
    m["month_label"] = m.month.map(dict(zip(range(1,13), MONTH_LABELS)))
    return m.sort_values(["seed","month"]).reset_index(drop=True)

def monthly_comparison(monthly: pd.DataFrame, reference: pd.DataFrame) -> pd.DataFrame:
    mapping = {"temperature_mean_c":"temperature_mean_c","temperature_daily_max_mean_c":"temperature_daily_max_mean_c","temperature_daily_min_mean_c":"temperature_daily_min_mean_c","ice_days":"ice_days","frost_days":"frost_days","summer_days":"summer_days","heat_days":"heat_days","sunshine_hours":"sunshine_hours","sunshine_pct":"sunshine_pct","precipitation_total_mm":"precipitation_total_mm","precip_days_ge_1mm":"precip_days_ge_1mm","precip_days_ge_5mm":"precip_days_ge_5mm","precip_days_ge_10mm":"precip_days_ge_10mm","precip_days_ge_50mm":"precip_days_ge_50mm","snow_cover_days":"snow_cover_days","humidity_pct":"humidity_pct","wind_m_s":"wind_m_s"}
    rows=[]
    for var, refcol in mapping.items():
        for mo in range(1,13):
            vals = monthly.loc[monthly.month==mo, var].astype(float)
            ref = float(reference.loc[reference.month_number==mo, refcol].iloc[0])
            rows.append({"variable":var,"month":mo,"month_label":MONTH_LABELS[mo-1],"reference_value":ref,"simulated_mean":vals.mean(),"simulated_sd":vals.std(ddof=1),"simulated_p025":vals.quantile(.025),"simulated_p975":vals.quantile(.975),"absolute_difference":abs(vals.mean()-ref),"reference_inside_95_interval": bool(vals.quantile(.025) <= ref <= vals.quantile(.975))})
    return pd.DataFrame(rows)

def summary_metrics(comp: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for var, sub in comp.groupby("variable", sort=True):
        x=sub.reference_value.to_numpy(float); y=sub.simulated_mean.to_numpy(float)
        corr = float(np.corrcoef(x,y)[0,1]) if np.std(x)>0 and np.std(y)>0 else math.nan
        diff=y-x; rows.append({"variable":var,"pearson_r":corr,"mae":float(np.mean(np.abs(diff))),"rmse":float(np.sqrt(np.mean(diff**2))),"mean_bias_sim_minus_ref":float(np.mean(diff))})
    return pd.DataFrame(rows)

def precip_quantile_comparison(
    monthly: pd.DataFrame,
    reference: pd.DataFrame,
) -> pd.DataFrame:
    """Compare simulated and reference precipitation quantiles by available month."""
    rows = []

    available_months = sorted(monthly["month"].dropna().astype(int).unique())

    for month in available_months:
        values = (
            monthly.loc[
                monthly["month"] == month,
                "precipitation_total_mm",
            ]
            .dropna()
            .to_numpy(dtype=float)
        )

        if values.size == 0:
            continue

        reference_row = reference.loc[reference["month_number"] == month]
        if reference_row.empty:
            raise ValueError(
                f"No reference precipitation quantiles found for month {month}."
            )

        for quantile in QUANTILES:
            quantile_percent = int(quantile * 100)
            reference_value = float(
                reference_row[f"precip_q{quantile_percent}_mm"].iloc[0]
            )
            simulated_value = float(np.quantile(values, quantile))

            rows.append(
                {
                    "month": month,
                    "month_label": MONTH_LABELS[month - 1],
                    "quantile": quantile_percent,
                    "reference_mm": reference_value,
                    "simulated_mm": simulated_value,
                    "difference_mm": simulated_value - reference_value,
                    "absolute_difference_mm": abs(
                        simulated_value - reference_value
                    ),
                }
            )

    return pd.DataFrame(rows)

def annual_summary(monthly: pd.DataFrame) -> pd.DataFrame:
    return monthly.groupby(["seed","model_year_index"], sort=True).agg(annual_precipitation_mm=("precipitation_total_mm","sum"), annual_sunshine_hours=("sunshine_hours","sum"), annual_temperature_mean_c=("temperature_mean_c","mean"), annual_snow_cover_days=("snow_cover_days","sum")).reset_index()

def plot_band(ax, comp, variable, title, ylabel):
    s=comp[comp.variable==variable].sort_values("month"); x=np.arange(12)
    ax.fill_between(x, s.simulated_p025.astype(float).to_numpy(), s.simulated_p975.astype(float).to_numpy(), alpha=.2, label="95% simulation interval")
    ax.plot(x, s.reference_value, marker="o", label="Reference")
    ax.plot(x, s.simulated_mean, marker="s", label="Simulated mean")
    ax.set_title(title); ax.set_ylabel(ylabel); ax.set_xticks(x, MONTH_LABELS); ax.grid(True, alpha=.3)

def make_figures(comp: pd.DataFrame, pq: pd.DataFrame, fig_dir: Path) -> None:
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig, axs = plt.subplots(3,1,figsize=(9,10), sharex=True); 
    for ax,var,title in zip(axs,["temperature_mean_c","temperature_daily_max_mean_c","temperature_daily_min_mean_c"],["Monthly mean temperature","Mean daily maximum temperature","Mean daily minimum temperature"]): plot_band(ax, comp, var, title, "°C")
    axs[0].legend(); fig.tight_layout(); fig.savefig(fig_dir/"temperature_monthly_comparison.png", dpi=200); plt.close(fig)
    fig, axs = plt.subplots(2,2,figsize=(11,7), sharex=True); 
    for ax,var in zip(axs.ravel(),["frost_days","ice_days","summer_days","heat_days"]): plot_band(ax, comp, var, var.replace("_"," ").title(), "standardized days")
    axs.ravel()[0].legend(); fig.tight_layout(); fig.savefig(fig_dir/"temperature_event_days.png", dpi=200); plt.close(fig)
    fig, ax=plt.subplots(figsize=(9,5)); plot_band(ax, comp, "precipitation_total_mm", "Monthly precipitation total", "mm"); ax.legend(); fig.tight_layout(); fig.savefig(fig_dir/"precipitation_monthly_comparison.png", dpi=200); plt.close(fig)
    fig, ax=plt.subplots(figsize=(10,6));
    for q, sub in pq.groupby("quantile"): ax.plot(sub.month_label, sub.simulated_mm, marker="s", label=f"Sim q{q}"); ax.plot(sub.month_label, sub.reference_mm, linestyle="--", alpha=.7, label=f"Ref q{q}")
    ax.set_ylabel("mm"); ax.set_title("Monthly precipitation quantiles"); ax.grid(True, alpha=.3); ax.legend(ncol=3, fontsize=8); fig.tight_layout(); fig.savefig(fig_dir/"precipitation_quantiles.png", dpi=200); plt.close(fig)
    fig, axs=plt.subplots(2,2,figsize=(11,7), sharex=True)
    for ax,var,y in zip(axs.ravel(),["sunshine_pct","humidity_pct","wind_m_s","snow_cover_days"],["%","%","m/s","standardized days"]): plot_band(ax, comp, var, var.replace("_"," ").title(), y)
    axs.ravel()[0].legend(); fig.tight_layout(); fig.savefig(fig_dir/"other_weather_variables.png", dpi=200); plt.close(fig)

def write_report(out: Path, cfg: dict, metrics: pd.DataFrame, coverage: pd.DataFrame, pq: pd.DataFrame) -> None:
    lines=["# H1 Weather Internal Consistency and Plausibility Assessment", "", "## Purpose", "This analysis provides an internal consistency and plausibility assessment against the climate normals used for model parameterization for H1, using weather as the empirically assessable everyday contextual condition.", "", "It is not an independent external validation.", "", "## Source and reference period", "MeteoSwiss climate normals for Bern/Zollikofen, 553 m above sea level, 46.99 N, 7.46 E, Central Plateau, reference period 1991–2020; climsheet 2.2.0, status 2024.", "", "## Simulation design", f"Number of simulated 360-day model years: {cfg['n_years']}", f"Seed range/list: {cfg['seeds'][0]}–{cfg['seeds'][-1]}; complete list recorded in `run_config.json`.", "", "The native weather model calendar contains 12 months, 30 days per month, 360 days per simulated model year, and 8,640 hourly observations per simulated model year.", "", "For extensive variables and event-day counts, native 30-day monthly values are preserved and standardized as native / 30 × average Gregorian month length for 1991–2020. The reference period contains eight leap years.", "", "The simulated snow-cover variable is a binary hourly indicator; a simulated snow-cover day is operationalized as at least one hour with `snow_cover=True`.", "", "## Summary metrics", metrics.to_string(index=False), "", "Undefined Pearson correlations are reported as NaN when either the reference or simulated monthly series has zero variance.", "", "## 95% interval coverage", coverage.to_string(index=False), "", "## Precipitation quantile comparison", pq.to_string(index=False), "", "## Figures", "- [Temperature monthly comparison](figures/temperature_monthly_comparison.png)", "- [Temperature event days](figures/temperature_event_days.png)", "- [Precipitation monthly comparison](figures/precipitation_monthly_comparison.png)", "- [Precipitation quantiles](figures/precipitation_quantiles.png)", "- [Other weather variables](figures/other_weather_variables.png)", "", "## Limitations", "- Reference data were used for parameterization.", "- Simulated years contain 360 days.", "- Only climate normals, not independent hourly observations, are used.", "- Agreement demonstrates implementation consistency, not predictive validity.", "", "## Neutral conclusion", "The outputs provide descriptive evidence about implementation consistency and plausibility. They do not automatically support or reject H1."]
    (out/"h1_validation_report.md").write_text("\n".join(lines), encoding="utf-8")

def run(n_years:int, base_seed:int, output_dir:Path, save_hourly:bool=False, overwrite:bool=False) -> None:
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite: raise FileExistsError(f"{output_dir} exists and is not empty; use --overwrite")
    data_dir=output_dir/"data"; table_dir=output_dir/"tables"; fig_dir=output_dir/"figures"
    for p in [data_dir, table_dir, fig_dir]: p.mkdir(parents=True, exist_ok=True)
    seed_list=seeds(n_years, base_seed); ref=load_reference(); hourly=simulate_years(seed_list); daily=aggregate_daily(hourly); monthly=aggregate_monthly(daily)
    comp=monthly_comparison(monthly, ref); metrics=summary_metrics(comp); pq=precip_quantile_comparison(monthly, ref)
    coverage=comp.groupby("variable", sort=True).agg(months_inside_95_interval=("reference_inside_95_interval","sum"), n_months=("month","count")).reset_index(); coverage["coverage_fraction"]=coverage.months_inside_95_interval/coverage.n_months
    daily.to_csv(data_dir/"simulated_daily_weather.csv", index=False); monthly.to_csv(data_dir/"simulated_monthly_weather.csv", index=False); comp.to_csv(data_dir/"monthly_climate_comparison.csv", index=False); pq.to_csv(data_dir/"precipitation_quantile_comparison.csv", index=False)
    if save_hourly: hourly.to_csv(data_dir/"simulated_hourly_weather.csv.gz", index=False, compression="gzip")
    metrics.to_csv(table_dir/"h1_summary_metrics.csv", index=False); coverage.to_csv(table_dir/"h1_interval_coverage.csv", index=False); annual_summary(monthly).to_csv(table_dir/"h1_annual_summary.csv", index=False)
    make_figures(comp, pq, fig_dir)
    cfg={"analysis":"H1 weather internal consistency and plausibility assessment against the climate normals used for model parameterization","n_years":n_years,"base_seed":base_seed,"seeds":seed_list,"calendar":"12 30-day months; 360-day model years; 8640 hourly observations per simulated model year","save_hourly":save_hourly}
    (output_dir/"run_config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    write_report(output_dir, cfg, metrics, coverage, pq)

def parse_args() -> argparse.Namespace:
    p=argparse.ArgumentParser(description="H1 weather internal consistency and plausibility assessment")
    p.add_argument("--n-years", type=int, default=50); p.add_argument("--base-seed", type=int, default=3263); p.add_argument("--output-dir", type=Path, default=Path("Analysis/outputs/h1_weather")); p.add_argument("--save-hourly", action="store_true"); p.add_argument("--overwrite", action="store_true")
    return p.parse_args()

if __name__ == "__main__":
    a=parse_args(); run(a.n_years, a.base_seed, a.output_dir, a.save_hourly, a.overwrite)
