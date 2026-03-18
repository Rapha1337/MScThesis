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
            ], dtype=np.float32),
            dtype=np.float32,
        )

        # Monatliche Mittelwerte für die Temperatur (in °C) Quelle: Klimanormwerte Bern/Zollikofen 1991-2020.
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
        
        # Monatsspezifische Tagesamplituden der Temperatur (in °C), abgeleitet aus den Klimanormwerten Bern/Zollikofen 1991–2020.
        # Diese Werte bestimmen, wie stark die Temperatur im Tagesverlauf schwankt.
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

        # Markov-OCCURRENCE-Parameter für Niederschlag pro Monat. Schätzung aus Klimanormwerte Bern/Zollikofen 1991-2020.
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

        # AMOUNT-Parameter für Anzahl nasse Stunden (Gamma-Verteilung). Schätzung aus Klimanormwerte Bern/Zollikofen 1991-2020.
        # Niederschlagsmenge ~ Gamma(shape, scale)
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

        # Temperaturmodell-Parameter nach Wilks (1999):
        # temp = mu(month,hour) + beta_wet * wet + eps_t
        # eps_t = phi * eps_(t-1) + sigma * N(0,1)
        self._beta_wet = {m: -0.8 for m in range(1, 13)} # Niederschlag kühlt die Temperatur um ca. 0.8°C ab (durchschnittlicher Effekt über alle Monate).
        self._phi = {m: 0.78 for m in range(1, 13)} # Autokorrelationsparameter des Temperaturrauschens. Wert von 0.78 führt zu langsamen veränderungen in der Temperatur.
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

        # Monatliche mittlere Sonnenaufgangs- und Sonnenuntergangszeiten für Bern. Quelle: https://www.laenderdaten.info/
        # Werte in Dezimalstunden (z. B. 08:09 -> 8.15).
        self._month_sunrise_hour = {
            1: 8.15,   # 08:09
            2: 7.53,   # 07:32
            3: 6.68,   # 06:41
            4: 6.67,   # 06:40
            5: 5.88,   # 05:53
            6: 5.53,   # 05:32
            7: 5.80,   # 05:48
            8: 6.43,   # 06:26
            9: 7.10,   # 07:06
            10: 7.77,  # 07:46
            11: 7.52,  # 07:31
            12: 8.12,  # 08:07
        }

        self._month_sunset_hour = {
            1: 17.15,   # 17:09
            2: 17.92,   # 17:55
            3: 18.60,   # 18:36
            4: 20.32,   # 20:19
            5: 21.00,   # 21:00
            6: 21.47,   # 21:28
            7: 21.38,   # 21:23
            8: 20.72,   # 20:43
            9: 19.73,   # 19:44
            10: 18.75,  # 18:45
            11: 16.95,  # 16:57
            12: 16.72,  # 16:43
        }

        # Monatsparameter für monatliche Sonnenstunden. Quelle: Klimanormwerte Bern/Zollikofen 1991-2020.
        self._month_sun_pct = {
            1: 26, 2: 35, 3: 44, 4: 47, 5: 45, 6: 50,
            7: 55, 8: 56, 9: 50, 10: 38, 11: 26, 12: 22,
        }

        # Monatsparameter für monatliche relative Luftfeuchtigkeit (in %). Quelle: Klimanormwerte Bern/Zollikofen 1991-2020.
        self._month_rel_humidity = {
            1: 84, 2: 79, 3: 73, 4: 70, 5: 72, 6: 72,
            7: 71, 8: 73, 9: 79, 10: 84, 11: 86, 12: 86,
        }

        # Monatsparameter für monatliche Windgeschwindigkeit (in m/s). Quelle: Klimanormwerte Bern/Zollikofen 1991-2020.
        self._month_wind_ms = {
            1: 1.8, 2: 2.0, 3: 2.2, 4: 2.1, 5: 2.0, 6: 2.0,
            7: 1.9, 8: 1.7, 9: 1.7, 10: 1.6, 11: 1.6, 12: 1.8,
        }

        # Monatsparameter für durchschnittliche Anzahl Tage mit Schneedecke > 1cm. Quelle: Klimanormwerte Bern/Zollikofen 1991-2020.
        self._month_snowcover_days_gt1 = {
            1: 9.7, 2: 8.1, 3: 2.3, 4: 0.3, 5: 0.0, 6: 0.0,
            7: 0.0, 8: 0.0, 9: 0.0, 10: 0.1, 11: 1.6, 12: 6.4,
        }

        # Interner Zustand der Simulation.
        self._rng: np.random.Generator | None = None
        self._t = 0  # absolute Zeitschrittzahl seit Episode-Start in Stunden
        self._eps_prev = 0.0  # vorheriges AR(1)-Residuum
        self._wet_prev = 0  # vorheriger Wet/Dry-Zustand (0 trocken, 1 nass)
        self._temp = 0.0  # zuletzt simulierte Temperatur
        self._precip = 0.0  # zuletzt simulierte Niederschlagsmenge
        self._sun_frac = 0.0 # # zuletzt simulierter stündlicher Sonnenanteil (0..1)
        self._humidity = 0.0 # zuletzt simulierte relative Luftfeuchtigkeit (in %)
        self._wind = 0.0 # zuletzt simulierte Windgeschwindigkeit (in m/s)
        self._snow_cover_flag = 0 # zuletzt simulierte Schneedecke > 1cm (0 oder 1)
        self._feels_like = 0.0 # zuletzt simulierte gefühlte Temperatur (in °C)
        self._sun_day_factor = 1.0  # tagesweiser Wolken-/Klarheitsfaktor

    def reset(self, seed: int | None = None, options: dict | None = None):
        """
        Setzt die Episode zurück und initialisiert den internen Wetterzustand.
        """
        del options

        super().reset(seed=seed)
        self._rng = np.random.default_rng(seed)
        self._t = 0

        start_month = self.month

        self._sun_frac = 0.0
        self._humidity = self._month_rel_humidity[start_month]
        self._wind = self._month_wind_ms[start_month]

        p_snow_start = self._month_snowcover_days_gt1[start_month] / 30.0
        self._snow_cover_flag = int(self._rng.random() < p_snow_start)

        self._feels_like = self._month_mean_temp[start_month]

        self._sun_day_factor = float(np.clip(self._rng.normal(1.0, 0.35), 0.2, 1.6))

        # Stationäre Wahrscheinlichkeit für den Zustand "nass"
        p_wet = self._p01[start_month] / (
            self._p01[start_month] + 1.0 - self._p11[start_month]
        )
        self._wet_prev = int(self._rng.random() < p_wet)

        # Startwert für AR(1)-Residuum
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
            if hour == 0:
                # neuer Tag -> neuer Tagesfaktor
                self._sun_day_factor = float(np.clip(self._rng.normal(1.0, 0.35), 0.2, 1.6))
            self._temp, self._precip, self._wet_prev, self._eps_prev, self._sun_frac, self._wind, \
            self._humidity, self._snow_cover_flag, self._feels_like = self._simulate_hour(
                month=month, hour=hour, wet_prev=self._wet_prev, eps_prev=self._eps_prev, 
                snow_prev=self._snow_cover_flag)

        # Dummy-Reward, da Wetter nicht agentengesteuert ist
        reward = 0.0

        # Zusätzliche Infos
        month, hour = self._month_hour(min(self._t, self.horizon_hours - 1))
        info = {
            "month": month,
            "hour": hour,
            "sun_frac": self._sun_frac,
            "humidity": self._humidity,
            "wind": self._wind,
            "snow_cover_flag": self._snow_cover_flag,
            "feels_like": self._feels_like,
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

        # 1) Wet/Dry
        wet_prob = self._p11[month] if wet_prev else self._p01[month]
        wet = int(self._rng.random() < wet_prob)

        # 2) Niederschlag
        precip = 0.0
        if wet:
            precip = float(
                self._rng.gamma(
                    shape=self._gamma_shape[month],
                    scale=self._gamma_scale[month],
                )
            )

        # 3) Temperatur
        eps = self._phi[month] * eps_prev + self._sigma[month] * float(self._rng.normal())
        temp = self._compute_temp(month, hour) + self._beta_wet[month] * wet + eps

        # 4) Sonne
        sun_frac = self._compute_sun_frac(month, hour, wet)

        # 5) Wind
        wind = self._compute_wind(month, wet)

        # 6) Feuchte
        humidity = self._compute_humidity(month, hour, temp, wet)

        # 7) Schneedecke
        snow_cover_flag = self._update_snow_cover(temp, wet, snow_prev)

        # 8) Gefühlte Temperatur
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

            - Monatlicher Mittelwert bildet den Jahresgang.
            - Monatsspezifische Amplitude bildet den mittleren Tagesgang ab.
            - Kosinusfunktion mit Maximum am Nachmittag (~15 Uhr).
            """
            month_mean = self._month_mean_temp[month]
            amplitude = self._month_temp_amp[month]
            phase = (hour - 15) / 24.0 * 2.0 * np.pi
            return float(month_mean + amplitude * np.cos(phase))
        
    def _compute_sun_frac(self, month: int, hour: int, wet: int) -> float:
        """
        Simuliert den stündlichen Sonnenanteil sun_frac in [0, 1].

        Idee:
        - monatsspezifische Sonnenaufgangs- und Sonnenuntergangszeiten für Bern
        - nachts immer 0
        - tagsüber sinusförmiges Profil mit Maximum zur Tagesmitte
        - Monatswert Sonne[%] aus dem Klimareport wirkt als saisonaler Klarheitsfaktor
        - tagesweiser Wolkenfaktor erzeugt realistische Tag-zu-Tag-Variation
        - bei Niederschlag zusätzliche Reduktion
        """
        assert self._rng is not None

        sunrise = self._month_sunrise_hour[month]
        sunset = self._month_sunset_hour[month]
        hour_center = hour + 0.5

        # Nacht
        if hour_center < sunrise or hour_center > sunset:
            return 0.0

        # Monatlicher Klarheitsfaktor aus Klimanormwerten
        base_clear = self._month_sun_pct[month] / 100.0

        # Position innerhalb der Tageslichtphase
        day_progress = (hour_center - sunrise) / (sunset - sunrise)

        # Glockenförmiger Tagesgang, Maximum um Mittag
        daylight_profile = np.sin(np.pi * day_progress)
        daylight_profile = max(0.0, daylight_profile)

        # Normierung, damit Tagesmittel des Profils ungefähr 1 ergibt
        daylight_profile *= (np.pi / 2.0)

        # Tagesweiser Faktor: wolkiger vs. klarer Tag
        # Etwas breiter wählen, damit mehr Tag-zu-Tag-Variation entsteht
        sun_frac = base_clear * daylight_profile * self._sun_day_factor

        # Niederschlag reduziert Sonnenschein deutlich
        if wet:
            sun_frac *= 0.35

        # Kleine stündliche Restvariation
        sun_frac += 0.04 * self._rng.normal()

        return float(np.clip(sun_frac, 0.0, 1.0))
    
    def _compute_wind(self, month: int, wet: int) -> float:
        """
        Simuliert Windgeschwindigkeit in m/s.

        Basis ist das monatliche Mittel aus dem Klimareport.
        Nasse Stunden sind leicht windiger, dazu kommen kleine Zufallsschwankungen
        und seltene stärkere Böen.
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

        Basis ist das monatliche Mittel aus dem Klimareport.
        Bei Regen steigt die Feuchte, tagsüber ist sie leicht tiefer,
        nachts leicht höher.
        """
        assert self._rng is not None

        base_hum = self._month_rel_humidity[month]

        # Nachmittags etwas tiefer, nachts etwas höher
        diurnal_hum = -8.0 * np.cos((hour - 15) / 24.0 * 2.0 * np.pi)

        # Wärmere Luft -> im Modell tendenziell geringere relative Feuchte
        temp_effect = -0.6 * (temp - self._month_mean_temp[month])

        wet_bonus = 10.0 if wet else 0.0
        noise = 4.0 * self._rng.normal()

        humidity = base_hum + diurnal_hum + temp_effect + wet_bonus + noise
        return float(np.clip(humidity, 30.0, 100.0))
    
    def _update_snow_cover(self, temp: float, wet: int, snow_prev: int) -> int:
        """
        Aktualisiert den Flag für Schneedecke > 1 cm.

        Einfache Logik:
        - bei kaltem Niederschlag kann sich eine Schneedecke bilden
        - bei wärmeren Bedingungen kann sie wieder verschwinden
        - der Zustand ist persistent
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

        Logik:
        - Bei kalten Bedingungen: Windchill
        - Bei warm/heissen Bedingungen: Heat Index
        - Sonst: Lufttemperatur

        Eingaben:
            temp: Lufttemperatur in °C
            wind: Windgeschwindigkeit in m/s
            humidity: relative Luftfeuchte in %
        """
        # Sicherheit: Feuchte physikalisch begrenzen
        rh = float(np.clip(humidity, 0.0, 100.0))

        # Umrechnungen für die offiziellen NWS-Formeln
        temp_f = temp * 9.0 / 5.0 + 32.0
        wind_mph = wind * 2.23694

        # 1) Windchill:
        # Gültig für T <= 50°F und Wind > 3 mph
        if temp_f <= 50.0 and wind_mph > 3.0:
            wc_f = (
                35.74
                + 0.6215 * temp_f
                - 35.75 * (wind_mph ** 0.16)
                + 0.4275 * temp_f * (wind_mph ** 0.16)
            )
            return float((wc_f - 32.0) * 5.0 / 9.0)

        # 2) Heat Index:
        # Sinnvoll nur bei warmen/heissen Bedingungen
        # Praktisch oft ab ca. 80°F (~26.7°C)
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

            # Adjustments für bestimmte Feuchtebereiche
            if 80.0 <= temp_f <= 112.0 and rh < 13.0:
                adjustment = ((13.0 - rh) / 4.0) * np.sqrt((17.0 - abs(temp_f - 95.0)) / 17.0)
                hi_f -= adjustment
            elif 80.0 <= temp_f <= 87.0 and rh > 85.0:
                adjustment = ((rh - 85.0) / 10.0) * ((87.0 - temp_f) / 5.0)
                hi_f += adjustment

            return float((hi_f - 32.0) * 5.0 / 9.0)

        # 3) Übergangsbereich: feels like = Lufttemperatur
        return float(temp)
        
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
            [hour_of_day, month_norm, temp_C, precip_mm, wet_flag,
            sun_frac, humidity_rel, wind_ms, snow_cover_flag, feels_like_C]

        month_norm ist auf [0, 1] skaliert, damit Features in ähnlichen
        Größenordnungen liegen.
        """
        month, hour = self._month_hour(min(self._t, self.horizon_hours - 1))
        month_norm = (month - 1) / 11.0
        wet_flag = float(self._wet_prev)
        snow_flag = float(self._snow_cover_flag)

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
            ],
            dtype=np.float32,
        )