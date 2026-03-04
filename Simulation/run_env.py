from env_time_weather import TimeWeatherEnv
import matplotlib.pyplot as plt

env = TimeWeatherEnv(month=6, sample_rate_hours=1)

obs, info = env.reset(seed=42)

hours, temps, steps = [], [], []

terminated = False
while not terminated:
    hour, temp = obs
    hours.append(hour)
    temps.append(temp)

    # Test-Policy: tagsüber aktiv, nachts inaktiv
    action = 1 if 7 <= hour <= 21 else 0

    obs, reward, terminated, truncated, info = env.step(action)
    steps.append(info["steps"])

# Plot Temperatur
plt.figure()
plt.plot(hours, temps)
plt.xlabel("Stunde")
plt.ylabel("Temperatur (°C)")
plt.title("Temperaturverlauf über einen Tag")
plt.xticks(range(0,23))
plt.grid(True)
plt.show()

# Plot Schritte
plt.figure()
plt.plot(hours, steps)
plt.xlabel("Stunde des Tages")
plt.ylabel("Schritte pro Stunde")
plt.title("Simulierte Aktivität")
plt.xticks(range(0,23))
plt.grid(True)
plt.show()
