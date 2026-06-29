from __future__ import annotations

from pathlib import Path
import socket
import sys

import pandas as pd
import pytest

ANALYSIS_DIR = Path(__file__).resolve().parents[1]
ROOT = ANALYSIS_DIR.parent

for path in (ROOT, ANALYSIS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import h1_weather_validation as h1


def tiny_hourly(seed: int = 1) -> pd.DataFrame:
    rows=[]
    for day,temp_pair,precip in [(1,(1,3),0.5),(2,(-2,-1),6.0),(3,(24,31),12.0),(4,(10,12),51.0)]:
        for hour in range(24):
            temp=temp_pair[0] if hour < 12 else temp_pair[1]
            rows.append({"seed":seed,"model_year_index":0,"absolute_hour":(day-1)*24+hour,"model_day":day,"month":1,"day_in_month":day,"hour":hour,"temperature_c":temp,"feels_like_c":temp,"precipitation_mm":precip/24,"is_wet":precip>0,"sun_frac":0.5,"humidity_pct":80,"wind_m_s":2,"snow_cover":hour==0 and day==2})
    return pd.DataFrame(rows)


def test_one_simulated_year_calendar_shape() -> None:
    df = h1.simulate_one_year(3263)
    assert len(df) == 8640
    assert df.model_day.nunique() == 360
    assert sorted(df.month.unique()) == list(range(1, 13))
    assert (df.groupby("month").day_in_month.nunique() == 30).all()
    assert (df.groupby("month").size() == 720).all()


def test_same_seed_identical_and_different_seed_differs() -> None:
    a = h1.simulate_one_year(100).head(200)
    b = h1.simulate_one_year(100).head(200)
    c = h1.simulate_one_year(101).head(200)
    pd.testing.assert_frame_equal(a, b)
    assert not a[["temperature_c", "precipitation_mm", "sun_frac"]].equals(c[["temperature_c", "precipitation_mm", "sun_frac"]])


def test_daily_temperature_precipitation_and_event_definitions() -> None:
    d = h1.aggregate_daily(tiny_hourly())
    assert d.loc[d.model_day == 1, "temperature_max_c"].iloc[0] == 3
    assert d.loc[d.model_day == 1, "temperature_min_c"].iloc[0] == 1
    assert not d.loc[d.model_day == 1, "precip_day_ge_1mm"].iloc[0]
    assert d.loc[d.model_day == 2, "precip_day_ge_5mm"].iloc[0]
    assert d.loc[d.model_day == 3, "precip_day_ge_10mm"].iloc[0]
    assert d.loc[d.model_day == 4, "precip_day_ge_50mm"].iloc[0]
    assert d.loc[d.model_day == 2, "ice_day"].iloc[0]
    assert d.loc[d.model_day == 2, "frost_day"].iloc[0]
    assert d.loc[d.model_day == 3, "summer_day"].iloc[0]
    assert d.loc[d.model_day == 3, "heat_day"].iloc[0]


def test_extensive_standardization() -> None:
    assert h1.standardize_extensive(30, 1) == pytest.approx(31)
    assert h1.standardize_extensive(30, 2) == pytest.approx(28.2666667)
    assert h1.standardize_extensive(30, 4) == pytest.approx(30)


def test_relative_sunshine_uses_astronomical_daylight_hours() -> None:
    env = h1.TimeWeatherEnv(month=1, sample_rate_hours=1, horizon_hours=24*360, bern_map=h1.WeatherOnlyBernMap())
    possible = h1.possible_daylight_hours(env, 1, 30)
    expected = (env._month_sunset_hour[1] - env._month_sunrise_hour[1]) * 30
    assert possible == pytest.approx(expected)
    daily = h1.aggregate_daily(tiny_hourly())
    monthly = h1.aggregate_monthly(daily)
    assert monthly.loc[0, "sunshine_pct"] == pytest.approx(100 * monthly.loc[0, "sunshine_native_30d_hours"] / expected)


def test_monthly_precipitation_quantiles_across_years() -> None:
    monthly = pd.DataFrame({"month":[1,1,1],"precipitation_total_mm":[10.0,20.0,30.0]})
    ref = h1.load_reference()
    out = h1.precip_quantile_comparison(monthly, ref)
    jan = out[out.month == 1]
    assert jan.loc[jan["quantile"] == 0, "simulated_mm"].iloc[0] == pytest.approx(10)
    assert jan.loc[jan["quantile"] == 100, "simulated_mm"].iloc[0] == pytest.approx(30)
    assert jan.loc[jan["quantile"] == 40, "simulated_mm"].iloc[0] == pytest.approx(18)


def test_script_does_not_require_network_access(monkeypatch, tmp_path: Path) -> None:
    def fail_network(*args, **kwargs):
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket, "create_connection", fail_network)
    h1.run(n_years=1, base_seed=400, output_dir=tmp_path / "h1", overwrite=True)
    assert (tmp_path / "h1" / "run_config.json").exists()
    assert not (tmp_path / "h1" / "data" / "simulated_hourly_weather.csv.gz").exists()
