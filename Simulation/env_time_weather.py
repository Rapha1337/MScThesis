from __future__ import annotations

import numpy as np
import gymnasium as gym
from gymnasium import spaces


class TimeWeatherEnv(gym.Env):
    """
    Environment: 1 Episode = 1 Tag
    Observation: [hour, temperature]
    Action: 0 = inaktiv, 1 = aktiv
    Reward: simulierte Schritte pro Stunde (abhängig von Aktion, Uhrzeit, Temperatur).
    """

    metadata = {"render_modes": []}

    # Setup: Zufälliger Monat (1-12) und stündliche sample_rate
    def __init__(self, month: int = np.random.randint(1, 13), sample_rate_hours: int = 1):
        super().__init__()
        assert 1 <= month <= 12
        assert sample_rate_hours >= 1

        self.month = month
        self.sample_rate_hours = sample_rate_hours
        self.hours_per_day = 24

        # Action Space: 0 = inaktiv, 1 = aktiv
        self.action_space = spaces.Discrete(2)

        # Observation Space: [hour (0-23), temperature (-10 bis 45 °C)]
        self.observation_space = spaces.Box(
            low=np.array([0.0, -10.0], dtype=np.float32),
            high=np.array([23.0, 45.0], dtype=np.float32),
            dtype=np.float32
        )

        # Mittelewerte der Monatsmitteltemperaturen 2025 (Schweiz, Deutschland, Österreich)
        self._month_mean_temp = {
            1: 0.3, 2: 0.5, 3: 4.6, 4: 8.7, 5: 10.7, 6: 17.7, 
            7: 16.4, 8: 16.9, 9: 13.1, 10: 7.9, 11: 3.1, 12: 1.5
        }

        # Interner Zustand des Environments
        self._rng = None
        self._hour = 0
        self._base_temp = 0.0
        self._temp = 0.0

    # Reset: Startet eine neue Episode (neuer Tag) mit zufälliger Basistemperatur für den Monat
    def reset(self, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        self._rng = np.random.default_rng(seed)

        self._hour = 0

        # Basistemperatur für den Tag aus Monatsmittel + Noise
        month_mean = self._month_mean_temp[self.month]
        self._base_temp = float(self._rng.normal(loc=month_mean, scale=3.0))

        self._temp = self._compute_temp(self._hour)

        obs = np.array([self._hour, self._temp], dtype=np.float32)
        info = {"month": self.month, "base_temp": self._base_temp}
        return obs, info

    def step(self, action: int):
        # 1) Reward berechnen (Schritte pro Zeitschritt)
        steps = self._simulate_steps(action=action, hour=self._hour, temp=self._temp)
        reward = float(steps)

        # 2) Zeit fortschreiben
        self._hour += self.sample_rate_hours

        # 3) Termination
        terminated = self._hour >= self.hours_per_day
        truncated = False

        # 4) Nächster State
        if not terminated:
            self._temp = self._compute_temp(self._hour)
            obs = np.array([self._hour, self._temp], dtype=np.float32)
        else:
            # bei Episode-Ende: letzte gültige Observation zurückgeben
            obs = np.array([23.0, self._temp], dtype=np.float32)

        info = {"steps": steps}
        return obs, reward, terminated, truncated, info

    def _compute_temp(self, hour: int) -> float:
        """
        Sehr einfache Tageskurve:
        - Peak am Nachmittag (~15 Uhr)
        - plus stündliches Noise
        """
        phase = (hour - 15) / 24.0 * 2 * np.pi
        diurnal = 3.0 * np.cos(phase)  # Amplitude 3°C
        noise = float(self._rng.normal(0.0, 1.5))
        return float(self._base_temp + diurnal + noise)

    def _simulate_steps(self, action: int, hour: int, temp: float) -> int:
        """
        Super einfache Schritte-Logik (nur für den Start!):
        - action=0: wenige Schritte
        - action=1: mehr Schritte
        - nachts (0-6 Uhr): weniger Schritte unabhängig von action
        - sehr extremes Wetter (temp < 0 oder > 30): etwas weniger Schritte
        """
        if action not in (0, 1):
            raise ValueError("Action must be 0 or 1.")

        # Basis-Schritte abhängig von Aktion
        if action == 0:
            base = self._rng.normal(80, 30)     # inaktiv
        else:
            base = self._rng.normal(600, 150)   # aktiv

        # Nacht-Dämpfung
        if 0 <= hour <= 6:
            base *= 0.2

        # Wetter-Dämpfung
        if temp < 0 or temp > 30:
            base *= 0.7

        return int(max(0, base))
    