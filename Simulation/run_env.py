from env_time_weather import TimeWeatherEnv
import matplotlib.pyplot as plt

# Environment erstellen
env = TimeWeatherEnv(sample_rate_hours=1)

# Neue Episode starten (simulierter Tag)
obs, info = env.reset(seed=42)

# Listen zum Speichern der simulierten Daten
hours, temps = [], []

terminated = False
while not terminated:

    # Observation besteht aus [hour, temperature]
    hour, temp = obs

    # Stunde speichern
    hours.append(hour)

    # Temperatur speichern
    temps.append(temp)

    # Dummy-Action (wird aktuell nicht verwendet)
    action = 0

    # Environment einen Schritt weiter simulieren
    obs, reward, terminated, truncated, info = env.step(action)

# Plot Temperaturverlauf über den Tag
plt.figure()
plt.plot(hours, temps)
plt.xlabel("Stunde")
plt.ylabel("Temperatur (°C)")
plt.title("Temperaturverlauf über einen Tag")
plt.xticks(range(0, 24))
plt.grid(True)
plt.show()

# Ausgabe welcher Monat simuliert wurde
print(f"Simulierter Tag aus Monat: {env.month}")