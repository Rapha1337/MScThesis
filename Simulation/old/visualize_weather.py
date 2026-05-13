from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

"""Kleines Demo-Skript, das die Wetterumgebung ausführt und Zeitreihen plottet."""

import random

import matplotlib

# ============================================================
# EINSTELLUNGEN
# ============================================================
PLOT_MODE = "save"   # "show" oder "save"
SAVE_DIR = Path("plots")
SEED = random.randint(0, 999999)

if PLOT_MODE == "show":
    matplotlib.use("QtAgg")
elif PLOT_MODE == "save":
    matplotlib.use("Agg")
else:
    raise ValueError("PLOT_MODE muss 'show' oder 'save' sein.")

import matplotlib.pyplot as plt
import numpy as np

from env_time_weather import TimeWeatherEnv


# ============================================================
# HILFSFUNKTIONEN
# ============================================================
def finalize_plot(filename: str | None = None) -> None:
    """Zeigt oder speichert den aktuellen Plot, je nach PLOT_MODE."""
    if PLOT_MODE == "show":
        plt.show()
        plt.close()
    else:
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        if filename is None:
            raise ValueError("Im save-Modus muss ein Dateiname angegeben werden.")
        plt.savefig(SAVE_DIR / filename, dpi=200)
        plt.close()


def set_season_axis(ax) -> None:
    """Setzt Jahreszeiten-Beschriftung für Jahresplots."""
    season_positions = [1, 61, 151, 241, 331]
    season_labels = ["Winter", "Frühling", "Sommer", "Herbst", "Winter"]
    ax.set_xlabel("Jahreszeit")
    ax.set_xticks(season_positions)
    ax.set_xticklabels(season_labels)


# ============================================================
# 1) ENVIRONMENT ERSTELLEN
# ============================================================
env = TimeWeatherEnv(month=1, sample_rate_hours=1, horizon_hours=24 * 365)

# ============================================================
# 2) EPISODE STARTEN
# ============================================================
obs, info = env.reset(seed=SEED)

print("Spawn:")
print(" node_id:", info["node_id"])
print(" lat:", info["lat"])
print(" lon:", info["lon"])

# ============================================================
# 3) DATEN SAMMELN
# ============================================================
temps = []
precips = []
wet_flags = []
months = []
sun_fracs = []
humidities = []
winds = []
snow_flags = []
feels_like_vals = []
x_positions = []
y_positions = []

terminated = False
while not terminated:
    # Observation-Layout:
    # [hour_of_day, month_norm, temperature_C, precip_mm, wet_flag,
    #  sun_frac, humidity_rel, wind_ms, snow_cover_flag, feels_like_C, x_norm, y_norm]
    (
        hour,
        month_norm,
        temp,
        precip,
        wet,
        sun_frac,
        humidity,
        wind,
        snow_flag,
        feels_like,
        x_norm,
        y_norm,
    ) = obs

    temps.append(temp)
    precips.append(precip)
    wet_flags.append(wet)
    months.append(info["month"])
    sun_fracs.append(sun_frac)
    humidities.append(humidity)
    winds.append(wind)
    snow_flags.append(snow_flag)
    feels_like_vals.append(feels_like)
    x_positions.append(x_norm)
    y_positions.append(y_norm)

    action = random.choice([0, 1])
    obs, reward, terminated, truncated, info = env.step(action=action)

# ============================================================
# 4) IN ARRAYS UMWANDELN
# ============================================================
temp_series = np.array(temps)
precips = np.array(precips)
wet_flags = np.array(wet_flags)
months = np.array(months)
sun_fracs = np.array(sun_fracs)
humidities = np.array(humidities)
winds = np.array(winds)
snow_flags = np.array(snow_flags)
feels_like_vals = np.array(feels_like_vals)

# Ganze Tage sicherstellen
n_days = len(temp_series) // 24
temp_series_day = temp_series[: n_days * 24].reshape(n_days, 24)
precips_day = precips[: n_days * 24].reshape(n_days, 24)
sun_day = sun_fracs[: n_days * 24].reshape(n_days, 24)
humidity_day = humidities[: n_days * 24].reshape(n_days, 24)
wind_day = winds[: n_days * 24].reshape(n_days, 24)
snow_day = snow_flags[: n_days * 24].reshape(n_days, 24)
feels_like_day = feels_like_vals[: n_days * 24].reshape(n_days, 24)

# Neu: Sonnenstunden aus stündlichem Sonnenanteil
sun_hours_day = sun_day.sum(axis=1)

# ============================================================
# 5) KENNZAHLEN
# ============================================================
daily_max = temp_series_day.max(axis=1)
daily_min = temp_series_day.min(axis=1)

heat_days = np.sum(daily_max >= 30.0)
summer_days = np.sum(daily_max >= 25.0)
frost_days = np.sum(daily_min < 0.0)
ice_days = np.sum(daily_max < 0.0)
snow_days = np.sum(snow_day.max(axis=1) == 1)

mean_temp = temp_series.mean()
mean_precip_hour = precips.mean()
wet_hour_share = wet_flags.mean()
annual_precip = precips.sum()

mean_sun_frac = sun_fracs.mean()
annual_sun_hours = sun_hours_day.sum()

mean_humidity = humidities.mean()
mean_wind = winds.mean()
mean_feels_like = feels_like_vals.mean()

print("=== Kennzahlen der Simulation ===")
print(f"Hitzetage (Tmax >= 30 Grad): {heat_days}")
print(f"Sommertage (Tmax >= 25 Grad): {summer_days}")
print(f"Frosttage (Tmin < 0 Grad): {frost_days}")
print(f"Eistage (Tmax < 0 Grad): {ice_days}")
print(f"Mittlere Temperatur über das Jahr: {mean_temp:.2f} Grad")
print(f"Mittlere gefühlte Temperatur über das Jahr: {mean_feels_like:.2f} Grad")
print(f"Jahresniederschlag: {annual_precip:.1f} mm")
print(f"Mittlerer Niederschlag pro Stunde: {mean_precip_hour:.3f} mm/h")
print(f"Anteil nasser Stunden: {wet_hour_share:.3f}")
print(f"Mittlerer Sonnenanteil sun_frac: {mean_sun_frac:.3f}")
print(f"Jährliche Sonnenstunden: {annual_sun_hours:.1f} h")
print(f"Mittlere relative Feuchte: {mean_humidity:.1f} %")
print(f"Mittlere Windgeschwindigkeit: {mean_wind:.2f} m/s")
print(f"Tage mit Schneedecke-Flag: {snow_days}")

# ============================================================
# 6) TAGESWERTE FÜR JAHRESPLOTS
# ============================================================
daily_mean_temp = temp_series_day.mean(axis=1)
daily_min_temp = temp_series_day.min(axis=1)
daily_max_temp = temp_series_day.max(axis=1)
daily_precip = precips_day.sum(axis=1)

# Statt Tagesmittel von sun_frac jetzt Sonnenstunden pro Tag
daily_sun_hours = sun_day.sum(axis=1)

daily_humidity = humidity_day.mean(axis=1)
daily_wind = wind_day.mean(axis=1)
daily_snow = snow_day.mean(axis=1)
daily_feels_like = feels_like_day.mean(axis=1)

days = np.arange(1, n_days + 1)

# ============================================================
# 7) JAHRESPLOTS
# ============================================================

# Plot 1: Temperatur + Niederschlag
fig, ax1 = plt.subplots(figsize=(14, 5))
ax1.fill_between(days, daily_min_temp, daily_max_temp, color="tab:red", alpha=0.2)
ax1.plot(days, daily_mean_temp, color="tab:red", linewidth=2)
ax1.set_ylabel("Temperatur (°C)", color="tab:red")
ax1.tick_params(axis="y", labelcolor="tab:red")
set_season_axis(ax1)

ax2 = ax1.twinx()
ax2.bar(days, daily_precip, color="tab:blue", alpha=0.35, width=1.0)
ax2.set_ylabel("Niederschlag (mm/Tag)", color="tab:blue")
ax2.tick_params(axis="y", labelcolor="tab:blue")

plt.title("Simuliertes Wetterjahr: Temperatur und Niederschlag")
plt.tight_layout()
finalize_plot("plot_01_temp_precip_year.png")

# Plot 2: Sonnenstunden
fig, ax1 = plt.subplots(figsize=(14, 5))
ax1.plot(days, daily_sun_hours, linewidth=2)
ax1.set_ylabel("Sonnenstunden pro Tag")
ax1.set_ylim(0, max(16, daily_sun_hours.max() + 0.5))
set_season_axis(ax1)

plt.title("Simulierte Sonnenstunden über das Jahr")
plt.tight_layout()
finalize_plot("plot_02_sun_year.png")

# Plot 3: Relative Feuchte
fig, ax1 = plt.subplots(figsize=(14, 5))
ax1.plot(days, daily_humidity, linewidth=2)
ax1.set_ylabel("Relative Feuchte (%)")
ax1.set_ylim(30, 100)
set_season_axis(ax1)

plt.title("Simulierte relative Feuchte über das Jahr")
plt.tight_layout()
finalize_plot("plot_03_humidity_year.png")

# Plot 4: Wind
fig, ax1 = plt.subplots(figsize=(14, 5))
ax1.plot(days, daily_wind, linewidth=2)
ax1.set_ylabel("Wind (m/s)")
ax1.set_ylim(0, max(6, daily_wind.max() + 0.5))
set_season_axis(ax1)

plt.title("Simulierte Windgeschwindigkeit über das Jahr")
plt.tight_layout()
finalize_plot("plot_04_wind_year.png")

# Plot 5: Schneedecke
fig, ax1 = plt.subplots(figsize=(14, 5))
ax1.step(days, daily_snow, where="mid")
ax1.set_ylabel("Anteil Stunden mit Schneedecke")
ax1.set_ylim(-0.05, 1.05)
set_season_axis(ax1)

plt.title("Simulierter Schneedecken-Flag über das Jahr")
plt.tight_layout()
finalize_plot("plot_05_snowflag_year.png")

# Plot 6: Temperatur vs. gefühlte Temperatur
fig, ax1 = plt.subplots(figsize=(14, 5))
ax1.plot(days, daily_mean_temp, label="Temperatur", linewidth=2)
ax1.plot(days, daily_feels_like, label="Gefühlte Temperatur", linewidth=2)
ax1.set_ylabel("°C")
set_season_axis(ax1)
ax1.legend()

plt.title("Temperatur vs. gefühlte Temperatur")
plt.tight_layout()
finalize_plot("plot_06_temp_vs_feelslike_year.png")

# ============================================================
# 8) MONATSPLOTS
# ============================================================
month_names = {
    1: "Januar", 2: "Februar", 3: "März", 4: "April",
    5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
    9: "September", 10: "Oktober", 11: "November", 12: "Dezember",
}

month = 10  # z.B. random.randint(1, 12)
month_mask = months == month

month_temps = temp_series[month_mask]
month_precips = precips[month_mask]
month_sun = sun_fracs[month_mask]
month_humidity = humidities[month_mask]
month_wind = winds[month_mask]
month_snow = snow_flags[month_mask]
month_feels_like = feels_like_vals[month_mask]

n_days_month = len(month_temps) // 24

month_temps_day = month_temps[: n_days_month * 24].reshape(n_days_month, 24)
month_precips_day = month_precips[: n_days_month * 24].reshape(n_days_month, 24)
month_sun_day = month_sun[: n_days_month * 24].reshape(n_days_month, 24)
month_humidity_day = month_humidity[: n_days_month * 24].reshape(n_days_month, 24)
month_wind_day = month_wind[: n_days_month * 24].reshape(n_days_month, 24)
month_snow_day = month_snow[: n_days_month * 24].reshape(n_days_month, 24)
month_feels_like_day = month_feels_like[: n_days_month * 24].reshape(n_days_month, 24)

daily_mean_month = month_temps_day.mean(axis=1)
daily_min_month = month_temps_day.min(axis=1)
daily_max_month = month_temps_day.max(axis=1)
daily_precip_month = month_precips_day.sum(axis=1)

# Statt Tagesmittel von sun_frac jetzt Sonnenstunden pro Tag
daily_sun_hours_month = month_sun_day.sum(axis=1)

daily_humidity_month = month_humidity_day.mean(axis=1)
daily_wind_month = month_wind_day.mean(axis=1)
daily_snow_month = month_snow_day.mean(axis=1)
daily_feels_like_month = month_feels_like_day.mean(axis=1)

days_month = np.arange(1, n_days_month + 1)

# Plot 7: Temperatur + Niederschlag im Monat
fig, ax1 = plt.subplots(figsize=(14, 5))
ax1.fill_between(days_month, daily_min_month, daily_max_month, color="tab:red", alpha=0.2)
ax1.plot(days_month, daily_mean_month, color="tab:red", linewidth=2)
ax1.set_ylabel("Temperatur (°C)", color="tab:red")
ax1.tick_params(axis="y", labelcolor="tab:red")
ax1.set_xlabel("Tag im Monat")
ax1.set_xlim(1, n_days_month)

ax2 = ax1.twinx()
ax2.bar(days_month, daily_precip_month, color="tab:blue", alpha=0.3, width=0.8)
ax2.set_ylabel("Niederschlag (mm/Tag)", color="tab:blue")
ax2.tick_params(axis="y", labelcolor="tab:blue")

plt.title(f"Wetter-Simulation im Monat: {month_names[month]}")
plt.tight_layout()
finalize_plot("plot_07_temp_precip_month.png")

# Plot 8: Sonnenstunden im Monat
fig, ax1 = plt.subplots(figsize=(14, 4))
ax1.plot(days_month, daily_sun_hours_month, linewidth=2)
ax1.set_ylim(0, max(16, daily_sun_hours_month.max() + 0.5))
ax1.set_xlabel("Tag im Monat")
ax1.set_ylabel("Sonnenstunden pro Tag")
plt.title(f"Sonnenstunden im {month_names[month]}")
plt.tight_layout()
finalize_plot("plot_08_sun_month.png")

# Plot 9: Feuchte im Monat
fig, ax1 = plt.subplots(figsize=(14, 4))
ax1.plot(days_month, daily_humidity_month, linewidth=2)
ax1.set_ylim(30, 100)
ax1.set_xlabel("Tag im Monat")
ax1.set_ylabel("Relative Feuchte (%)")
plt.title(f"Relative Feuchte im {month_names[month]}")
plt.tight_layout()
finalize_plot("plot_09_humidity_month.png")

# Plot 10: Wind im Monat
fig, ax1 = plt.subplots(figsize=(14, 4))
ax1.plot(days_month, daily_wind_month, linewidth=2)
ax1.set_ylim(0, max(6, daily_wind_month.max() + 0.5))
ax1.set_xlabel("Tag im Monat")
ax1.set_ylabel("Wind (m/s)")
plt.title(f"Windgeschwindigkeit im {month_names[month]}")
plt.tight_layout()
finalize_plot("plot_10_wind_month.png")

# Plot 11: Schnee im Monat
fig, ax1 = plt.subplots(figsize=(14, 4))
ax1.step(days_month, daily_snow_month, where="mid")
ax1.set_ylim(-0.05, 1.05)
ax1.set_xlabel("Tag im Monat")
ax1.set_ylabel("Anteil Stunden mit Schneedecke")
plt.title(f"Schneedecke-Flag im {month_names[month]}")
plt.tight_layout()
finalize_plot("plot_11_snow_month.png")

# Plot 12: Temperatur vs gefühlte Temperatur im Monat
fig, ax1 = plt.subplots(figsize=(14, 4))
ax1.plot(days_month, daily_mean_month, label="Temperatur", linewidth=2)
ax1.plot(days_month, daily_feels_like_month, label="Gefühlte Temperatur", linewidth=2)
ax1.set_xlabel("Tag im Monat")
ax1.set_ylabel("°C")
ax1.legend()
plt.title(f"Temperatur vs. gefühlte Temperatur im {month_names[month]}")
plt.tight_layout()
finalize_plot("plot_12_temp_vs_feelslike_month.png")

# ============================================================
# 9) ZUFÄLLIGER TAG IM GEWÄHLTEN MONAT
# ============================================================
month_indices = np.where(month_mask)[0]
n_days_month = len(month_indices) // 24
random_day = random.randint(0, n_days_month - 1)

start = random_day * 24
end = start + 24
day_indices = month_indices[start:end]

day_temps = temp_series[day_indices]
day_precips = precips[day_indices]
day_sun = sun_fracs[day_indices]
day_humidity = humidities[day_indices]
day_wind = winds[day_indices]
day_snow = snow_flags[day_indices]
day_feels_like = feels_like_vals[day_indices]

day_hours = np.arange(24)

# Plot 13: Zufälliger Tag Temperatur + Niederschlag
fig, ax1 = plt.subplots(figsize=(10, 5))
ax1.plot(day_hours, day_temps, color="tab:red", linewidth=2, label="Temperatur")
ax1.plot(
    day_hours,
    day_feels_like,
    color="tab:orange",
    linewidth=2,
    linestyle="--",
    label="Gefühlte Temperatur",
)
ax1.set_ylabel("Temperatur (°C)")
ax1.set_xticks(np.arange(0, 24, 2))
ax1.set_xlabel("Uhrzeit")
ax1.legend(loc="upper left")

ax2 = ax1.twinx()
ax2.bar(day_hours, day_precips, color="tab:blue", alpha=0.35)
ax2.set_ylabel("Niederschlag (mm/h)")

plt.title(f"Wetter an einem zufälligen Tag im {month_names[month]}")
plt.tight_layout()
finalize_plot("plot_13_random_day_temp_precip.png")

# Plot 14: NPC Route im x/y-Norm-Koordinatensystem
fig, ax = plt.subplots(figsize=(6, 6))
ax.plot(x_positions, y_positions, linewidth=1.5)
ax.scatter(x_positions[0], y_positions[0], label="Start")
ax.scatter(x_positions[-1], y_positions[-1], label="Ende")
ax.set_xlabel("x_norm")
ax.set_ylabel("y_norm")
ax.set_title("Normierte NPC-Trajektorie")
ax.legend()
plt.tight_layout()
finalize_plot("plot_14_npc_trajectory.png")

if PLOT_MODE == "save":
    print(f"Plots wurden als PNG-Dateien in '{SAVE_DIR}' gespeichert.")