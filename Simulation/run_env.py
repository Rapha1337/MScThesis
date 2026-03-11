"""Kleines Demo-Skript, das die Wetterumgebung ausführt und die Zeitreihen plottet."""

from env_time_weather import TimeWeatherEnv
import matplotlib.pyplot as plt


# 1) Environment erstellen
# month=1      -> Start im Januar
# sample_rate=1 -> stündlicher Schritt
# horizon=72    -> 3 Tage simulieren
env = TimeWeatherEnv(month=1, sample_rate_hours=1, horizon_hours=24 * 3)

# 2) Neue Episode starten (mit Seed für reproduzierbare Werte)
obs, info = env.reset(seed=42)

# 3) Container für Plotdaten
hours = []
temps = []
precips = []
wet_flags = []

terminated = False
while not terminated:
    # Observation-Layout:
    # [hour_of_day, month_norm, temperature_C, precip_mm, wet_flag]
    hour, month_norm, temp, precip, wet = obs

    # Für den Plot verwenden wir einen fortlaufenden Zeitindex (0..N-1 Stunden).
    hours.append(len(hours))
    temps.append(temp)
    precips.append(precip)
    wet_flags.append(wet)

    # Aktion ist Dummy (hat keinen Einfluss auf das Wettermodell).
    obs, reward, terminated, truncated, info = env.step(action=0)


# 4) Visualisierung: Temperatur-Linie + Niederschlags-Balken
fig, ax1 = plt.subplots()
ax1.plot(hours, temps, label="Temperatur", color="tab:red")
ax1.set_xlabel("Zeitschritt (h)")
ax1.set_ylabel("Temperatur (°C)", color="tab:red")
ax1.tick_params(axis="y", labelcolor="tab:red")

ax2 = ax1.twinx()
ax2.bar(hours, precips, label="Niederschlag", color="tab:blue", alpha=0.35)
ax2.set_ylabel("Niederschlag (mm/h)", color="tab:blue")
ax2.tick_params(axis="y", labelcolor="tab:blue")

plt.title("Stündliche Wetter-Simulation (Temperatur + Niederschlag)")
plt.tight_layout()
plt.show()

# 5) Kurzinfo in die Konsole
print(f"Simulierter Monat am Episodenende: {info['month']}")
print(f"Anteil nasser Stunden: {sum(wet_flags) / len(wet_flags):.2f}")
