from __future__ import annotations

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from bern_map import BernMap
from MobilityModel import MobilityModel


class TimeWeatherEnv(gym.Env):
    """
    Wetter- und Zeit-Environment für stündliche Simulationen über mehrere Monate/Jahre.
    GPS und Mobilitätsmodell zusätzlich eingebaut.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        month: int = 1,
        sample_rate_hours: int = 1,
        horizon_hours: int = 24 * 365,
        bern_map: BernMap | None = None,
    ):
        """
        Initialisiert das Environment und alle Modellparameter.

        Args:
            month: Startmonat der Simulation (1..12).
            sample_rate_hours: Wie viele Stunden ein `step()` weiterspringt.
            horizon_hours: Episodenlänge in Stunden.
            bern_map: Optional bereits initialisierte BernMap.
        """
        super().__init__()

        assert 1 <= month <= 12
        assert sample_rate_hours >= 1
        assert horizon_hours >= 24

        self.month = month
        self.sample_rate_hours = sample_rate_hours
        self.horizon_hours = horizon_hours

        # Dummy-Actionspace:
        # aktuell noch ohne Einfluss auf Mobilität
        self.action_space = spaces.Discrete(2)

        # Observation-Space:
        # 10 Wetter/Zeit-Features + 7 Mobility-Features
        self.observation_space = spaces.Box(
            low=np.array([
                0.0,    # hour_of_day
                0.0,    # month_norm
                -40.0,  # temperature_C
                0.0,    # precip_mm
                0.0,    # wet_flag
                0.0,    # sun_frac
                0.0,    # humidity_rel
                0.0,    # wind_ms
                0.0,    # snow_cover_flag
                -50.0,  # feels_like_C
                0.0,    # is_at_home
                0.0,    # minutes_to_nearest_gym_walk
                0.0,    # minutes_to_nearest_gym_bike
                0.0,    # minutes_to_nearest_pool_walk
                0.0,    # minutes_to_nearest_pool_bike
                0.0,    # minutes_to_nearest_park_walk
                0.0,    # minutes_to_nearest_park_bike
            ], dtype=np.float32),
            high=np.array([
                23.0,   # hour_of_day
                1.0,    # month_norm
                50.0,   # temperature_C
                120.0,  # precip_mm
                1.0,    # wet_flag
                1.0,    # sun_frac
                100.0,  # humidity_rel
                12.0,   # wind_ms
                1.0,    # snow_cover_flag
                50.0,   # feels_like_C
                1.0,    # is_at_home
                300.0,  # minutes_to_nearest_gym_walk
                120.0,  # minutes_to_nearest_gym_bike
                300.0,  # minutes_to_nearest_pool_walk
                120.0,  # minutes_to_nearest_pool_bike
                300.0,  # minutes_to_nearest_park_walk
                120.0,  # minutes_to_nearest_park_bike
            ], dtype=np.float32),
            dtype=np.float32,
        )

        # Monatliche Mittelwerte für die Temperatur (°C)
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
            12: 0.9,
        }

        # Monatsspezifische Tagesamplituden der Temperatur (°C)
        self._month_temp_amp = {
            1: 2.5,
            2: 3.0,
            3: 4.5,
            4: 5.5,
            5: 5.5,
            6: 5.6,
            7: 5.8,
            8: 5.6,
            9: 5.1,
            10: 4.2,
            11: 3.3,
            12: 2.5,
        }

        # Markov-OCCURRENCE-Parameter für Niederschlag
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

        # Gamma-Parameter für Niederschlagsmenge
        self._gamma_shape = {m: 1.3 for m in range(1, 13)}
        self._gamma_scale = {
            1: 1.0,
            2: 1.0,
            3: 1.1,
            4: 1.3,
            5: 1.4,
            6: 1.7,
            7: 1.9,
            8: 1.8,
            9: 1.5,
            10: 1.3,
            11: 1.1,
            12: 1.0,
        }

        # Temperaturmodell-Parameter
        self._beta_wet = {m: -0.8 for m in range(1, 13)}
        self._phi = {m: 0.78 for m in range(1, 13)}
        self._sigma = {
            1: 0.9,
            2: 0.9,
            3: 0.9,
            4: 1.0,
            5: 1.1,
            6: 1.5,
            7: 2.0,
            8: 1.8,
            9: 1.1,
            10: 1.0,
            11: 0.9,
            12: 0.9,
        }

        # Monatliche mittlere Sonnenaufgangszeiten
        self._month_sunrise_hour = {
            1: 8.15,
            2: 7.53,
            3: 6.68,
            4: 6.67,
            5: 5.88,
            6: 5.53,
            7: 5.80,
            8: 6.43,
            9: 7.10,
            10: 7.77,
            11: 7.52,
            12: 8.12,
        }

        # Monatliche mittlere Sonnenuntergangszeiten
        self._month_sunset_hour = {
            1: 17.15,
            2: 17.92,
            3: 18.60,
            4: 20.32,
            5: 21.00,
            6: 21.47,
            7: 21.38,
            8: 20.72,
            9: 19.73,
            10: 18.75,
            11: 16.95,
            12: 16.72,
        }

        # Monatsparameter für Sonnenschein
        self._month_sun_pct = {
            1: 26, 2: 35, 3: 44, 4: 47, 5: 45, 6: 50,
            7: 55, 8: 56, 9: 50, 10: 38, 11: 26, 12: 22,
        }

        # Monatsparameter für relative Luftfeuchtigkeit
        self._month_rel_humidity = {
            1: 84, 2: 79, 3: 73, 4: 70, 5: 72, 6: 72,
            7: 71, 8: 73, 9: 79, 10: 84, 11: 86, 12: 86,
        }

        # Monatsparameter für Windgeschwindigkeit
        self._month_wind_ms = {
            1: 1.8, 2: 2.0, 3: 2.2, 4: 2.1, 5: 2.0, 6: 2.0,
            7: 1.9, 8: 1.7, 9: 1.7, 10: 1.6, 11: 1.6, 12: 1.8,
        }

        # Monatsparameter für Schneedecke > 1 cm
        self._month_snowcover_days_gt1 = {
            1: 9.7, 2: 8.1, 3: 2.3, 4: 0.3, 5: 0.0, 6: 0.0,
            7: 0.0, 8: 0.0, 9: 0.0, 10: 0.1, 11: 1.6, 12: 6.4,
        }

        # Interner Zustand Wetter/Zeit
        self._rng: np.random.Generator | None = None
        self._t = 0
        self._eps_prev = 0.0
        self._wet_prev = 0
        self._temp = 0.0
        self._precip = 0.0
        self._sun_frac = 0.0
        self._humidity = 0.0
        self._wind = 0.0
        self._snow_cover_flag = 0
        self._feels_like = 0.0
        self._sun_day_factor = 1.0

        # Interner Zustand räumliche Umgebung
        self.map = bern_map if bern_map is not None else BernMap(dist_km=8.0)
        self.mobility = MobilityModel(self.map)

    def reset(self, seed: int | None = None, options: dict | None = None):
        """
        Setzt die Episode zurück und initialisiert den internen Wetterzustand.
        """
        del options

        super().reset(seed=seed)
        self._rng = np.random.default_rng(seed)
        self._t = 0

        # Mobility neu initialisieren
        home_node, _, _ = self.map.sample_random_node()
        self.mobility.set_home(home_node)
        self.mobility.reset_to_home()
        self.mobility.clear_pois()

        # Zufällige POIs auf zufälligen OSM-Nodes
        gym_1, _, _ = self.map.sample_random_node()
        gym_2, _, _ = self.map.sample_random_node()
        pool_1, _, _ = self.map.sample_random_node()
        park_1, _, _ = self.map.sample_random_node()

        self.mobility.add_poi("gym", gym_1, name="Gym 1")
        self.mobility.add_poi("gym", gym_2, name="Gym 2")
        self.mobility.add_poi("pool", pool_1, name="Pool 1")
        self.mobility.add_poi("park", park_1, name="Park 1")

        start_month = self.month

        self._sun_frac = 0.0
        self._humidity = self._month_rel_humidity[start_month]
        self._wind = self._month_wind_ms[start_month]

        p_snow_start = self._month_snowcover_days_gt1[start_month] / 30.0
        self._snow_cover_flag = int(self._rng.random() < p_snow_start)

        self._feels_like = self._month_mean_temp[start_month]
        self._sun_day_factor = float(np.clip(self._rng.normal(1.0, 0.35), 0.2, 1.6))

        p_wet = self._p01[start_month] / (
            self._p01[start_month] + 1.0 - self._p11[start_month]
        )
        self._wet_prev = int(self._rng.random() < p_wet)

        self._eps_prev = float(self._rng.normal(0.0, self._sigma[start_month]))

        (
            self._temp,
            self._precip,
            self._wet_prev,
            self._eps_prev,
            self._sun_frac,
            self._wind,
            self._humidity,
            self._snow_cover_flag,
            self._feels_like,
        ) = self._simulate_hour(
            month=start_month,
            hour=0,
            wet_prev=self._wet_prev,
            eps_prev=self._eps_prev,
            snow_prev=self._snow_cover_flag,
        )

        current_lat, current_lon = self.mobility.get_current_position()

        return self._get_obs(), {
            "month": start_month,
            "home_node": self.mobility.home_node,
            "current_node": self.mobility.current_node,
            "lat": current_lat,
            "lon": current_lon,
        }

    def step(self, action: int):
        """
        Führt einen Simulationsschritt aus.

        Aktionen:
            0 = stay
            1 = mache eine zufällige Aktivität mit zufälligem Modus

        Logik:
        - Bei action == 1 wählt das Environment zufällig eine Aktivitätskategorie
        und einen Modus (walk oder bike).
        - Die Reisezeit zur Aktivität wird in echte Simulationszeit übersetzt.
        - Wetter/Zeit werden auf den neuen Zeitpunkt aktualisiert.
        """
        assert action in [0, 1]
        assert self._rng is not None

        mobility_info = {
            "target_category": None,
            "target_name": None,
            "target_node": None,
            "mode": None,
            "distance_m": 0.0,
            "travel_time_min": 0.0,
        }

        # Standard: ein normaler Zeitschritt
        delta_hours = self.sample_rate_hours

        # --------------------------------------------------------
        # Action 1 = zufällige Aktivität mit zufälligem Modus
        # --------------------------------------------------------
        if action == 1:
            categories = self.mobility.get_categories()

            if len(categories) > 0:
                category = str(self._rng.choice(categories))
                mode = str(self._rng.choice(["walk", "bike", "drive"]))
                mobility_info = self.mobility.go_to_nearest(category, mode=mode)

                travel_time_min = float(mobility_info["travel_time_min"])

                # Reisezeit in Stunden übersetzen:
                # mindestens 1 Stunde, wenn eine Aktivität ausgeführt wird
                delta_hours = max(
                    self.sample_rate_hours,
                    int(np.ceil(travel_time_min / 60.0)),
                )

        # --------------------------------------------------------
        # Zeit fortschreiten lassen
        # --------------------------------------------------------
        self._t += delta_hours

        terminated = self._t >= self.horizon_hours
        truncated = False

        if not terminated:
            month, hour = self._month_hour(self._t)

            if hour == 0:
                self._sun_day_factor = float(
                    np.clip(self._rng.normal(1.0, 0.35), 0.2, 1.6)
                )

            (
                self._temp,
                self._precip,
                self._wet_prev,
                self._eps_prev,
                self._sun_frac,
                self._wind,
                self._humidity,
                self._snow_cover_flag,
                self._feels_like,
            ) = self._simulate_hour(
                month=month,
                hour=hour,
                wet_prev=self._wet_prev,
                eps_prev=self._eps_prev,
                snow_prev=self._snow_cover_flag,
            )

        reward = 0.0

        month, hour = self._month_hour(min(self._t, self.horizon_hours - 1))
        current_lat, current_lon = self.mobility.get_current_position()

        info = {
            "action": int(action),
            "action_name": "stay" if action == 0 else "random_activity",
            "delta_hours": int(delta_hours),
            "month": month,
            "hour": hour,
            "sun_frac": self._sun_frac,
            "humidity": self._humidity,
            "wind": self._wind,
            "snow_cover_flag": self._snow_cover_flag,
            "feels_like": self._feels_like,
            "home_node": self.mobility.home_node,
            "current_node": self.mobility.current_node,
            "lat": current_lat,
            "lon": current_lon,
            "mobility": mobility_info,
        }

        return self._get_obs(), reward, terminated, truncated, info

    def _simulate_hour(
        self,
        month: int,
        hour: int,
        wet_prev: int,
        eps_prev: float,
        snow_prev: int,
    ):
        """
        Simuliert genau eine Stunde Wetter.
        """
        assert self._rng is not None

        wet_prob = self._p11[month] if wet_prev else self._p01[month]
        wet = int(self._rng.random() < wet_prob)

        precip = 0.0
        if wet:
            precip = float(
                self._rng.gamma(
                    shape=self._gamma_shape[month],
                    scale=self._gamma_scale[month],
                )
            )

        eps = self._phi[month] * eps_prev + self._sigma[month] * float(self._rng.normal())
        temp = self._compute_temp(month, hour) + self._beta_wet[month] * wet + eps

        sun_frac = self._compute_sun_frac(month, hour, wet)
        wind = self._compute_wind(month, wet)
        humidity = self._compute_humidity(month, hour, temp, wet)
        snow_cover_flag = self._update_snow_cover(temp, wet, snow_prev)
        feels_like = self._compute_feels_like(temp, wind, humidity)

        return (
            float(temp),
            float(precip),
            int(wet),
            float(eps),
            float(sun_frac),
            float(wind),
            float(humidity),
            int(snow_cover_flag),
            float(feels_like),
        )

    def _compute_temp(self, month: int, hour: int) -> float:
        """
        Deterministische Temperatur-Basis mu(month, hour).
        """
        month_mean = self._month_mean_temp[month]
        amplitude = self._month_temp_amp[month]
        phase = (hour - 15) / 24.0 * 2.0 * np.pi
        return float(month_mean + amplitude * np.cos(phase))

    def _compute_sun_frac(self, month: int, hour: int, wet: int) -> float:
        """
        Simuliert den stündlichen Sonnenanteil sun_frac in [0, 1].
        """
        assert self._rng is not None

        sunrise = self._month_sunrise_hour[month]
        sunset = self._month_sunset_hour[month]
        hour_center = hour + 0.5

        if hour_center < sunrise or hour_center > sunset:
            return 0.0

        base_clear = self._month_sun_pct[month] / 100.0
        day_progress = (hour_center - sunrise) / (sunset - sunrise)

        daylight_profile = np.sin(np.pi * day_progress)
        daylight_profile = max(0.0, daylight_profile)
        daylight_profile *= (np.pi / 2.0)

        sun_frac = base_clear * daylight_profile * self._sun_day_factor

        if wet:
            sun_frac *= 0.35

        sun_frac += 0.04 * self._rng.normal()

        return float(np.clip(sun_frac, 0.0, 1.0))

    def _compute_wind(self, month: int, wet: int) -> float:
        """
        Simuliert Windgeschwindigkeit in m/s.
        """
        assert self._rng is not None

        base_wind = self._month_wind_ms[month]
        wind = base_wind + 0.8 * self._rng.normal() + (0.4 if wet else 0.0)

        if self._rng.random() < 0.01:
            wind += self._rng.uniform(2.0, 5.0)

        return float(np.clip(wind, 0.0, 12.0))

    def _compute_humidity(self, month: int, hour: int, temp: float, wet: int) -> float:
        """
        Simuliert relative Feuchte in %.
        """
        assert self._rng is not None

        base_hum = self._month_rel_humidity[month]
        diurnal_hum = -8.0 * np.cos((hour - 15) / 24.0 * 2.0 * np.pi)
        temp_effect = -0.6 * (temp - self._month_mean_temp[month])
        wet_bonus = 10.0 if wet else 0.0
        noise = 4.0 * self._rng.normal()

        humidity = base_hum + diurnal_hum + temp_effect + wet_bonus + noise
        return float(np.clip(humidity, 30.0, 100.0))

    def _update_snow_cover(self, temp: float, wet: int, snow_prev: int) -> int:
        """
        Aktualisiert den Flag für Schneedecke > 1 cm.
        """
        assert self._rng is not None

        snow_cover_flag = snow_prev

        if wet and temp <= 0.5:
            p_add = 0.10 + 0.10 * max(0.0, 0.5 - temp)
            if self._rng.random() < min(p_add, 0.9):
                snow_cover_flag = 1

        elif snow_prev == 1 and temp > 1.5:
            p_melt = min(0.02 + 0.03 * (temp - 1.5), 0.5)
            if self._rng.random() < p_melt:
                snow_cover_flag = 0

        return int(snow_cover_flag)

    def _compute_feels_like(self, temp: float, wind: float, humidity: float) -> float:
        """
        Berechnet die gefühlte Temperatur (feels like) in °C.
        """
        rh = float(np.clip(humidity, 0.0, 100.0))

        temp_f = temp * 9.0 / 5.0 + 32.0
        wind_mph = wind * 2.23694

        if temp_f <= 50.0 and wind_mph > 3.0:
            wc_f = (
                35.74
                + 0.6215 * temp_f
                - 35.75 * (wind_mph ** 0.16)
                + 0.4275 * temp_f * (wind_mph ** 0.16)
            )
            return float((wc_f - 32.0) * 5.0 / 9.0)

        if temp_f >= 80.0:
            hi_f = (
                -42.379
                + 2.04901523 * temp_f
                + 10.14333127 * rh
                - 0.22475541 * temp_f * rh
                - 6.83783e-3 * (temp_f ** 2)
                - 5.481717e-2 * (rh ** 2)
                + 1.22874e-3 * (temp_f ** 2) * rh
                + 8.5282e-4 * temp_f * (rh ** 2)
                - 1.99e-6 * (temp_f ** 2) * (rh ** 2)
            )

            if 80.0 <= temp_f <= 112.0 and rh < 13.0:
                adjustment = ((13.0 - rh) / 4.0) * np.sqrt((17.0 - abs(temp_f - 95.0)) / 17.0)
                hi_f -= adjustment
            elif 80.0 <= temp_f <= 87.0 and rh > 85.0:
                adjustment = ((rh - 85.0) / 10.0) * ((87.0 - temp_f) / 5.0)
                hi_f += adjustment

            return float((hi_f - 32.0) * 5.0 / 9.0)

        return float(temp)

    def _month_hour(self, t: int) -> tuple[int, int]:
        """
        Wandelt absolute Stunden seit Episodenstart in (Monat, Stunde) um.
        """
        day_idx, hour = divmod(t, 24)
        month_shift = (day_idx // 30) % 12
        month = ((self.month - 1 + month_shift) % 12) + 1
        return month, hour

    def _get_obs(self) -> np.ndarray:
        """
        Baut den aktuellen Beobachtungsvektor für den Agenten.
        """
        month, hour = self._month_hour(min(self._t, self.horizon_hours - 1))
        month_norm = (month - 1) / 11.0
        wet_flag = float(self._wet_prev)
        snow_flag = float(self._snow_cover_flag)

        mobility_features = self.mobility.get_state_features(
            include_walk=True,
            include_bike=True,
            include_drive=False,
        )

        return np.array(
            [
                hour,
                month_norm,
                self._temp,
                self._precip,
                wet_flag,
                self._sun_frac,
                self._humidity,
                self._wind,
                snow_flag,
                self._feels_like,
                mobility_features["is_at_home"],
                mobility_features["minutes_to_nearest_gym_walk"],
                mobility_features["minutes_to_nearest_gym_bike"],
                mobility_features["minutes_to_nearest_pool_walk"],
                mobility_features["minutes_to_nearest_pool_bike"],
                mobility_features["minutes_to_nearest_park_walk"],
                mobility_features["minutes_to_nearest_park_bike"],
            ],
            dtype=np.float32,
        )
