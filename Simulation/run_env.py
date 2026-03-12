"""Kleines Demo-Skript, das die Wetterumgebung ausführt und die Zeitreihen plottet."""

from env_time_weather import TimeWeatherEnv
import matplotlib.pyplot as plt
import numpy as np
import random


# 1) Environment erstellen
env = TimeWeatherEnv(month=1, sample_rate_hours=1, horizon_hours=24 * 365)

# 2) Neue Episode starten
obs, info = env.reset()

# 3) Container für Plotdaten
hours = []
temps = []
precips = []
wet_flags = []
months = []

terminated = False
while not terminated:
    # Observation-Layout:
    # [hour_of_day, month_norm, temperature_C, precip_mm, wet_flag]
    hour, month_norm, temp, precip, wet = obs

    hours.append(len(hours))
    temps.append(temp)
    precips.append(precip)
    wet_flags.append(wet)
    months.append(info["month"])

    obs, reward, terminated, truncated, info = env.step(action=0)


# 4) In Arrays umwandeln
hours = np.array(hours)
temp_series = np.array(temps)
precips = np.array(precips)
wet_flags = np.array(wet_flags)
months = np.array(months)

# Ganze Tage sicherstellen
n_days = len(temp_series) // 24
temp_series_day = temp_series[: n_days * 24].reshape(n_days, 24)
precips_day = precips[: n_days * 24].reshape(n_days, 24)

# 5) Kennzahlen berechnen und ausgeben
daily_max = temp_series_day.max(axis=1)
daily_min = temp_series_day.min(axis=1)

heat_days = np.sum(daily_max >= 30.0)
summer_days = np.sum(daily_max >= 25.0)
frost_days = np.sum(daily_min < 0.0)
ice_days = np.sum(daily_max < 0.0)

mean_temp = temp_series.mean()
mean_precip_hour = precips.mean()
wet_hour_share = wet_flags.mean()
annual_precip = precips.sum()

print("=== Kennzahlen der Simulation ===")
print(f"Hitzetage (Tmax >= 30Grad): {heat_days}")
print(f"Sommertage (Tmax >= 25Grad): {summer_days}")
print(f"Frosttage (Tmin < 0Grad): {frost_days}")
print(f"Eistage (Tmax < 0GRad): {ice_days}")
print(f"Mittlere Temperatur ueber das Jahr: {mean_temp:.2f} Grad")
print(f"Jahresniederschlag: {annual_precip:.1f} mm")
print(f"Mittlerer Niederschlag pro Stunde: {mean_precip_hour:.3f} mm/h")
print(f"Anteil nasser Stunden: {wet_hour_share:.3f}")


# Plots erstellen
# Plot 1: Jahresverlauf von Temperatur und Niederschlag

# Tageswerte berechnen
daily_mean = temp_series_day.mean(axis=1)
daily_min = temp_series_day.min(axis=1)
daily_max = temp_series_day.max(axis=1)
daily_precip = precips_day.sum(axis=1)

days = np.arange(1, n_days + 1)

# Jahreszeitenpositionen (bei 30 Tage/Monat)
season_positions = [
    0,
    60,
    150,
    240,
    330
]

season_labels = ["Winter", "Frühling", "Sommer", "Herbst", "Winter"]

fig, ax1 = plt.subplots(figsize=(14, 5))

# Temperaturband (Min-Max)
ax1.fill_between(days, daily_min, daily_max, color="tab:red", alpha=0.2)

# Mitteltemperatur
ax1.plot(days, daily_mean, color="tab:red", linewidth=2)

ax1.set_ylabel("Temperatur (°C)", color="tab:red")
ax1.tick_params(axis="y", labelcolor="tab:red")
ax1.set_xlabel("Jahreszeit")

ax1.set_xticks(season_positions)
ax1.set_xticklabels(season_labels)

# Niederschlag
ax2 = ax1.twinx()
ax2.bar(days, daily_precip, color="tab:blue", alpha=0.35, width=1.0)
ax2.set_ylabel("Niederschlag (mm/Tag)", color="tab:blue")
ax2.tick_params(axis="y", labelcolor="tab:blue")

plt.title("Simuliertes Wetterjahr (Temperatur und Niederschlag)")
plt.tight_layout()
plt.show()

# Plot 2: Monat mit Tagesverlauf von Temperatur und Niederschlag

month_names = {
    1: "Januar", 2: "Februar", 3: "März", 4: "April",
    5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
    9: "September", 10: "Oktober", 11: "November", 12: "Dezember"
}

month = 10
month_mask = months == month

month_temps = temp_series[month_mask]
month_precips = precips[month_mask]

# Ganze Tage im Monat
n_days_month = len(month_temps) // 24
month_temps_day = month_temps[:n_days_month * 24].reshape(n_days_month, 24)
month_precips_day = month_precips[:n_days_month * 24].reshape(n_days_month, 24)

daily_mean_month = month_temps_day.mean(axis=1)
daily_min_month = month_temps_day.min(axis=1)
daily_max_month = month_temps_day.max(axis=1)
daily_precip_month = month_precips_day.sum(axis=1)

days = np.arange(1, n_days_month + 1)

fig, ax1 = plt.subplots(figsize=(14, 5))

# Temperaturbereich als Band
ax1.fill_between(days, daily_min_month, daily_max_month, color="tab:red", alpha=0.2)
ax1.plot(days, daily_mean_month, color="tab:red", linewidth=2)

ax1.set_ylabel("Temperatur (°C)", color="tab:red")
ax1.tick_params(axis="y", labelcolor="tab:red")
ax1.set_xlabel("Tag im Monat")
ax1.set_xlim(1, n_days_month)

ax2 = ax1.twinx()
ax2.bar(days, daily_precip_month, color="tab:blue", alpha=0.3, width=0.8)
ax2.set_ylabel("Niederschlag (mm/Tag)", color="tab:blue")
ax2.tick_params(axis="y", labelcolor="tab:blue")

plt.title(f"Wetter-Simulation im Monat: {month_names[month]}")
plt.tight_layout()
plt.show()

# Plot 3: Zufälliger Tag mit Tagesverlauf von Temperatur und Niederschlag

month_indices = np.where(month_mask)[0]

n_days_month = len(month_indices) // 24
random_day = random.randint(0, n_days_month - 1)

start = random_day * 24
end = start + 24

day_indices = month_indices[start:end]

day_temps = temp_series[day_indices]
day_precips = precips[day_indices]

day_hours = np.arange(24)

fig, ax1 = plt.subplots(figsize=(10, 5))

ax1.plot(day_hours, day_temps, color="tab:red", linewidth=2)
ax1.set_ylabel("Temperatur (°C)", color="tab:red")
ax1.tick_params(axis="y", labelcolor="tab:red")

ax1.set_xticks(np.arange(0, 24, 2))
ax1.set_xlabel("Uhrzeit")

ax2 = ax1.twinx()
ax2.bar(day_hours, day_precips, color="tab:blue", alpha=0.35)
ax2.set_ylabel("Niederschlag (mm/h)", color="tab:blue")
ax2.tick_params(axis="y", labelcolor="tab:blue")

plt.title(f"Wetter an einem zufälligen Tag im {month_names[month]}")
plt.tight_layout()
plt.show()