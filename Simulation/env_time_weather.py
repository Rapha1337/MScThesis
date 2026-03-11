from __future__ import annotations

import gymnasium as gym
import numpy as np
from gymnasium import spaces


class TimeWeatherEnv(gym.Env):
    """
    Wetter- und Zeit-Environment für stündliche Simulationen über mehrere Monate/Jahre.

    1) Niederschlags-Auftreten über 2-Zustands-Markov-Kette nach Gabriell und Neummann (1962).
    2) Niederschlags-Menge in nassen Stunden über Gamma-Verteilung nach Wilks (1999).
    3) Temperatur über deterministische Monats-/Tageskomponente + AR(1)-Residuum nach Wilks (1999).
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
            horizon_hours: Episodenlänge in Stunden
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

        # Dummy-Actionspace (hat keinen Einfluss auf die Simulation)
        self.action_space = spaces.Discrete(2)

        # Observation-Space::
        # hour_of_day: 0..23
        # month_norm: 0..1 (normalisierte Monatszahl)
        # temperature_C: -40..50 (realistische Temperaturskala)
        # precip_mm: 0..120 (realistische Niederschlagsskala pro Stunde)
        # wet_flag: 0 oder 1 (trocken oder nass)
        # [hour_of_day, month_norm, temperature_C, precip_mm, wet_flag]
        self.observation_space = spaces.Box(
            low=np.array([0.0, 0.0, -40.0, 0.0, 0.0], dtype=np.float32),
            high=np.array([23.0, 1.0, 50.0, 120.0, 1.0], dtype=np.float32),
            dtype=np.float32,
        )

        # Monatliche Mittelwerte für die Temperatur (in °C) Quelle: Klimanormwerte Bern/Zollkikofen 1991-2920.
        self._month_mean_temp = {
                1: 0.2,   
                2: 1.1,   
                3: 5.2,   
                4: 9.0,   
                5: 13.2,  
                6: 16.8,  
                7: 18.8,  
                8: 18.4,  
                9: 14.1,  
                10: 9.5,  
                11: 4.2,  
                12: 0.9   
            }

        # Markov-OCCURRENCE-Parameter für Niederschlag pro Monat. Schätzung aus Klimanormwerte Bern/Zollkikofen 1991-2920.
        # p01: P(nass | vorher trocken) --> Regen beginnt
        # p11: P(nass | vorher nass) --> Regen bleibt
        self._p01 = {
            1: 0.013,
            2: 0.012,
            3: 0.015,
            4: 0.018,
            5: 0.020,
            6: 0.019,
            7: 0.017,
            8: 0.017,
            9: 0.016,
            10: 0.015,
            11: 0.014,
            12: 0.014,
        }
        self._p11 = {
            1: 0.85,
            2: 0.84,
            3: 0.82,
            4: 0.80,
            5: 0.78,
            6: 0.76,
            7: 0.75,
            8: 0.76,
            9: 0.79,
            10: 0.82,
            11: 0.84,
            12: 0.85,
        }

        # AMOUNT-Parameter für Anzahl nasse Stunden (Gamma-Verteilung). Schätzung aus Klimanormwerte Bern/Zollkikofen 1991-2920.
        # Niederschlagsmenge ~ Gamma(shape, scale)
        self._gamma_shape = {m: 1.3 for m in range(1, 13)}
        self._gamma_scale = {
            1: 1.1,
            2: 1.1,
            3: 1.2,
            4: 1.4,
            5: 1.6,
            6: 1.9,
            7: 2.1,
            8: 2.0,
            9: 1.7,
            10: 1.4,
            11: 1.2,
            12: 1.1,
        }

        # Temperaturmodell-Parameter nach Wilks (1999):
        # temp = mu(month,hour) + beta_wet * wet + eps_t
        # eps_t = phi * eps_(t-1) + sigma * N(0,1)
        self._beta_wet = {m: -0.8 for m in range(1, 13)} # Niederschlag kühlt die Temperatur um ca. 0.8°C ab (durchschnittlicher Effekt über alle Monate).
        self._phi = {m: 0.78 for m in range(1, 13)} # Autokorrelationsparameter des Temperaturrauschens. Wert von 0.78 führt zu langsamen veränderungen in der Temperatur.
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
        Führt einen Simulationsschritt aus.

        Da das Wetter exogen ist, hat die Aktion aktuell keinen Einfluss
        auf die Wetterentwicklung. Das Environment simuliert einfach die
        nächste Stunde und gibt die neue Observation zurück.
        """
        del action  # Aktion wird derzeit nicht verwendet

        # Zeit fortschreiten lassen
        self._t += self.sample_rate_hours

        # Prüfen, ob Episode beendet ist
        terminated = self._t >= self.horizon_hours
        truncated = False

        # Falls die Episode noch läuft: nächste Stunde simulieren
        if not terminated:
            month, hour = self._month_hour(self._t)
            self._temp, self._precip, self._wet_prev, self._eps_prev = self._simulate_hour(
                month=month,
                hour=hour,
                wet_prev=self._wet_prev,
                eps_prev=self._eps_prev,
            )

        # Dummy-Reward, da Wetter nicht agentengesteuert ist
        reward = 0.0

        # Zusätzliche Infos
        month, hour = self._month_hour(min(self._t, self.horizon_hours - 1))
        info = {
            "month": month,
            "hour": hour,
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
