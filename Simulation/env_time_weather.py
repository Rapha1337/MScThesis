from __future__ import annotations

import gymnasium as gym
import numpy as np
from gymnasium import spaces


class TimeWeatherEnv(gym.Env):
    """
    Stündliche Wetterumgebung (Temperatur + Niederschlag) für RL-Experimente.

    Modellidee (einfach, aber nachvollziehbar):
    1) Niederschlags-Auftreten über 2-Zustands-Markov-Kette (trocken/nass).
    2) Niederschlags-Menge in nassen Stunden über Gamma-Verteilung.
    3) Temperatur über deterministische Monats-/Tageskomponente + AR(1)-Residuum.

    Die Aktion ist aktuell exogen (hat keinen Einfluss auf das Wetter), damit das
    Environment als Wetter-"Hintergrundprozess" in Agenten-Simulationen genutzt werden kann.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        month: int = 1,
        sample_rate_hours: int = 1,
        horizon_hours: int = 24 * 365,
    ):
        """
        Initialisiert das Environment und alle Modellparameter.

        Args:
            month: Startmonat der Simulation (1..12).
            sample_rate_hours: Wie viele Stunden ein `step()` weiterspringt.
            horizon_hours: Episodenlänge in Stunden (z. B. 8760 für ~1 Jahr).
        """
        super().__init__()

        # Eingabevalidierung, damit später keine stillen Fehler entstehen.
        assert 1 <= month <= 12
        assert sample_rate_hours >= 1
        assert horizon_hours >= 24

        # Konfiguration, die von außen gesetzt wird.
        self.month = month
        self.sample_rate_hours = sample_rate_hours
        self.horizon_hours = horizon_hours

        # Dummy-Actions (Wetter ist exogen und nicht vom Agent steuerbar).
        self.action_space = spaces.Discrete(2)

        # Observation-Format:
        # [hour_of_day, month_norm, temperature_C, precip_mm, wet_flag]
        self.observation_space = spaces.Box(
            low=np.array([0.0, 0.0, -40.0, 0.0, 0.0], dtype=np.float32),
            high=np.array([23.0, 1.0, 50.0, 120.0, 1.0], dtype=np.float32),
            dtype=np.float32,
        )

        # Monats-Mitteltemperaturen (hier fixe, beispielhafte Werte).
        # Diese bilden den "langsamen" Jahresgang ab.
        self._month_mean_temp = {
            1: 0.3,
            2: 0.5,
            3: 4.6,
            4: 8.7,
            5: 10.7,
            6: 17.7,
            7: 16.4,
            8: 16.9,
            9: 13.1,
            10: 7.9,
            11: 3.1,
            12: 1.5,
        }

        # Markov-OCCURRENCE-Parameter für Niederschlag pro Monat:
        # p01: P(nass | vorher trocken)
        # p11: P(nass | vorher nass)
        self._p01 = {
            1: 0.08,
            2: 0.08,
            3: 0.10,
            4: 0.11,
            5: 0.12,
            6: 0.11,
            7: 0.10,
            8: 0.10,
            9: 0.09,
            10: 0.10,
            11: 0.10,
            12: 0.09,
        }
        self._p11 = {
            1: 0.60,
            2: 0.58,
            3: 0.56,
            4: 0.55,
            5: 0.54,
            6: 0.53,
            7: 0.52,
            8: 0.54,
            9: 0.56,
            10: 0.58,
            11: 0.60,
            12: 0.61,
        }

        # AMOUNT-Parameter für nasse Stunden:
        # Niederschlagsmenge ~ Gamma(shape, scale)
        self._gamma_shape = {m: 1.3 for m in range(1, 13)}
        self._gamma_scale = {
            1: 1.2,
            2: 1.2,
            3: 1.3,
            4: 1.4,
            5: 1.6,
            6: 1.8,
            7: 1.8,
            8: 1.7,
            9: 1.5,
            10: 1.4,
            11: 1.3,
            12: 1.2,
        }

        # Temperaturmodell-Parameter:
        # temp = mu(month,hour) + beta_wet * wet + eps_t
        # eps_t = phi * eps_(t-1) + sigma * N(0,1)
        self._beta_wet = {m: -0.8 for m in range(1, 13)}
        self._phi = {m: 0.78 for m in range(1, 13)}
        self._sigma = {
            1: 1.1,
            2: 1.1,
            3: 1.0,
            4: 0.9,
            5: 0.9,
            6: 0.8,
            7: 0.8,
            8: 0.8,
            9: 0.9,
            10: 1.0,
            11: 1.0,
            12: 1.1,
        }

        # Interner Zustand der Simulation.
        self._rng: np.random.Generator | None = None
        self._t = 0  # absolute Zeitschrittzahl seit Episode-Start in Stunden
        self._eps_prev = 0.0  # vorheriges AR(1)-Residuum
        self._wet_prev = 0  # vorheriger Wet/Dry-Zustand (0 trocken, 1 nass)
        self._temp = 0.0  # zuletzt simulierte Temperatur
        self._precip = 0.0  # zuletzt simulierte Niederschlagsmenge

    def reset(self, seed: int | None = None, options: dict | None = None):
        """
        Setzt die Episode zurück und initialisiert den internen Wetterzustand.

        Ablauf:
        1) RNG mit Seed initialisieren (Reproduzierbarkeit).
        2) Anfangs-Wet-Zustand aus stationärer Nass-Wahrscheinlichkeit ziehen.
        3) Anfangs-Residuum für AR(1) ziehen.
        4) Stunde 0 simulieren und erste Observation zurückgeben.
        """
        del options  # derzeit ungenutzt, aber im Gym-API-Signature enthalten

        super().reset(seed=seed)
        self._rng = np.random.default_rng(seed)
        self._t = 0

        start_month = self.month

        # Stationäre Wahrscheinlichkeit für den Zustand "nass" der 2-Zustands-Markov-Kette.
        # pi_wet = p01 / (p01 + (1 - p11))
        p_wet = self._p01[start_month] / (
            self._p01[start_month] + 1.0 - self._p11[start_month]
        )
        self._wet_prev = int(self._rng.random() < p_wet)

        # Startwert für AR(1)-Residuum (Normalverteilung mit monatsabhängiger Skala).
        self._eps_prev = float(self._rng.normal(0.0, self._sigma[start_month]))

        # Explizit erste Stunde generieren, damit Beobachtung echte Wetterwerte enthält.
        self._temp, self._precip, self._wet_prev, self._eps_prev = self._simulate_hour(
            month=start_month,
            hour=0,
            wet_prev=self._wet_prev,
            eps_prev=self._eps_prev,
        )

        return self._get_obs(), {"month": start_month}

    def step(self, action: int):
        """
        Führt einen Zeitschritt aus.

        Die Aktion wird aktuell ignoriert (Wetterprozess ist exogen).
        Bei Bedarf kann hier später z. B. ein energie-/verhaltensbasiertes Reward-Modell
        angebunden werden, das das Wetter als Input nutzt.
        """
        del action

        # Zeit fortschreiben.
        self._t += self.sample_rate_hours

        # Episode endet, sobald die gewünschte Gesamtlänge erreicht ist.
        terminated = self._t >= self.horizon_hours
        truncated = False

        # Solange die Episode läuft, wird das Wetter für den neuen Zeitschritt simuliert.
        if not terminated:
            month, hour = self._month_hour(self._t)
            self._temp, self._precip, self._wet_prev, self._eps_prev = self._simulate_hour(
                month=month,
                hour=hour,
                wet_prev=self._wet_prev,
                eps_prev=self._eps_prev,
            )

        # Reward ist noch neutral (0.0), da dieses Environment nur Wetter liefert.
        reward = 0.0

        # Zusatzinfos für Debugging/Logging.
        info = {
            "t": self._t,
            "wet": int(self._wet_prev),
            "month": self._month_hour(min(self._t, self.horizon_hours - 1))[0],
        }
        return self._get_obs(), reward, terminated, truncated, info

    def _simulate_hour(self, month: int, hour: int, wet_prev: int, eps_prev: float):
        """
        Simuliert genau *eine* Stunde Wetter.

        Reihenfolge:
        1) Wet/Dry-Zustand über Markov-Übergang simulieren.
        2) Bei Wet=1 Niederschlagsmenge aus Gamma-Verteilung ziehen.
        3) AR(1)-Residuum für Temperatur aktualisieren.
        4) Temperatur aus Basiswert + Wet-Effekt + Residuum berechnen.

        Returns:
            (temp, precip, wet, eps)
        """
        assert self._rng is not None

        # Markov-Schritt für Auftreten von Niederschlag.
        wet_prob = self._p11[month] if wet_prev else self._p01[month]
        wet = int(self._rng.random() < wet_prob)

        # Niederschlagsmenge nur in nassen Stunden > 0, sonst 0.
        precip = 0.0
        if wet:
            precip = float(
                self._rng.gamma(
                    shape=self._gamma_shape[month],
                    scale=self._gamma_scale[month],
                )
            )

        # AR(1)-Update für den Temperaturrest.
        eps = self._phi[month] * eps_prev + self._sigma[month] * float(self._rng.normal())

        # Gesamttemperatur aus deterministischer Komponente + Wet-Effekt + stochastischer Rest.
        temp = self._mu(month, hour) + self._beta_wet[month] * wet + eps

        return float(temp), float(precip), wet, float(eps)

    def _mu(self, month: int, hour: int) -> float:
        """
        Deterministische Temperatur-Basis mu(month, hour).

        - Monatlicher Mittelwert bildet den Jahresgang.
        - Kosinusfunktion bildet den Tagesgang (Peak am Nachmittag) ab.
        - Amplitude variiert über das Jahr (Sommer stärkerer Tagesgang als Winter).
        """
        month_mean = self._month_mean_temp[month]
        amplitude = 2.5 + 1.5 * np.sin((month - 1) / 12.0 * 2.0 * np.pi)
        phase = (hour - 15) / 24.0 * 2.0 * np.pi
        return float(month_mean + amplitude * np.cos(phase))

    def _month_hour(self, t: int) -> tuple[int, int]:
        """
        Wandelt absolute Stunden seit Episodenstart in (Monat, Stunde) um.

        Vereinfachung für ein leichtes Simulationsmodell:
        - 30 Tage pro Monat
        - 12 Monate zyklisch

        Diese Kalenderversion ist absichtlich einfach und schnell.
        """
        day_idx, hour = divmod(t, 24)
        month_shift = (day_idx // 30) % 12
        month = ((self.month - 1 + month_shift) % 12) + 1
        return month, hour

    def _get_obs(self) -> np.ndarray:
        """
        Baut den aktuellen Beobachtungsvektor für den Agenten.

        Rückgabeformat:
            [hour_of_day, month_norm, temp_C, precip_mm, wet_flag]

        month_norm ist auf [0, 1] skaliert, damit Features in ähnlichen Größenordnungen liegen.
        """
        month, hour = self._month_hour(min(self._t, self.horizon_hours - 1))
        month_norm = (month - 1) / 11.0
        wet_flag = float(self._wet_prev)
        return np.array([hour, month_norm, self._temp, self._precip, wet_flag], dtype=np.float32)
