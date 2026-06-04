from __future__ import annotations

import json
from pathlib import Path
import sys
import types

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))


def _install_optional_dependency_stubs() -> None:

    if "numpy" not in sys.modules:
        import math
        import random as py_random

        numpy = types.ModuleType("numpy")
        numpy.pi = math.pi
        numpy.float32 = float
        numpy.array = lambda values, dtype=None: list(values)
        numpy.clip = lambda value, low, high: max(low, min(high, value))
        numpy.cos = math.cos
        numpy.sin = math.sin
        numpy.sqrt = math.sqrt
        numpy.isscalar = lambda value: isinstance(value, (int, float, bool, str, bytes))
        numpy.ndarray = list
        numpy.bool_ = bool

        class _FakeBitGenerator:
            def __init__(self, rng):
                self._rng = rng

            @property
            def state(self):
                return self._rng.getstate()

            @state.setter
            def state(self, value):
                self._rng.setstate(value)

        class _FakeGenerator:
            def __init__(self, seed=None):
                self._rng = py_random.Random(seed)
                self.bit_generator = _FakeBitGenerator(self._rng)

            def random(self):
                return self._rng.random()

            def normal(self, loc=0.0, scale=1.0):
                return self._rng.gauss(loc, scale)

            def gamma(self, shape, scale):
                return self._rng.gammavariate(shape, scale)

            def choice(self, values):
                values = list(values)
                return values[self._rng.randrange(len(values))]

            def uniform(self, low=0.0, high=1.0):
                return self._rng.uniform(low, high)

        numpy.random = types.SimpleNamespace(default_rng=lambda seed=None: _FakeGenerator(seed))
        sys.modules["numpy"] = numpy

    if "gymnasium" not in sys.modules:
        gymnasium = types.ModuleType("gymnasium")

        class Env:
            def reset(self, seed=None):
                del seed
                return None

        gymnasium.Env = Env
        sys.modules["gymnasium"] = gymnasium

    if "gymnasium.spaces" not in sys.modules:
        spaces = types.ModuleType("gymnasium.spaces")

        class Discrete:
            def __init__(self, n):
                self.n = n

        class Box:
            def __init__(self, low, high, dtype=None):
                self.low = low
                self.high = high
                self.dtype = dtype

        spaces.Discrete = Discrete
        spaces.Box = Box
        sys.modules["gymnasium.spaces"] = spaces
        sys.modules["gymnasium"].spaces = spaces

    if "osmnx" not in sys.modules:
        sys.modules["osmnx"] = types.ModuleType("osmnx")


_install_optional_dependency_stubs()

from env_time_weather import TimeWeatherEnv
from persona_wrappers import StudentHoursWrapper
from schedule_model_student import YearPhase
from simulation_runner import SimulationRunner


class FakeBernMap:
    def __init__(self) -> None:
        self._next_node = 1

    def sample_random_node(self):
        node = self._next_node
        self._next_node += 1
        return node, 46.0 + node * 0.001, 7.0 + node * 0.001

    def get_node_position(self, node_id: int, mode: str = "walk"):
        del mode
        return 46.0 + int(node_id) * 0.001, 7.0 + int(node_id) * 0.001

    def shortest_path_length_m(self, source_node: int, target_node: int, mode: str = "walk") -> float:
        del mode
        return abs(int(target_node) - int(source_node)) * 100.0

    def travel_time_minutes(self, source_node: int, target_node: int, speed_kmh: float, mode: str = "walk") -> float:
        del mode
        distance_km = self.shortest_path_length_m(source_node, target_node) / 1000.0
        return distance_km / speed_kmh * 60.0

    def nearest_node(self, lat: float, lon: float, mode: str = "walk"):
        del lat, lon, mode
        return 1, 46.001, 7.001

    def travel_time_minutes_from_positions(
        self,
        source_lat: float,
        source_lon: float,
        target_lat: float,
        target_lon: float,
        speed_kmh: float,
        mode: str = "drive",
    ) -> float:
        del mode
        distance_km = abs(target_lat - source_lat) + abs(target_lon - source_lon)
        return distance_km / speed_kmh * 60.0


class FakeRunnerEnv:
    def __init__(self) -> None:
        self.requested_start_t = None

    def reset(self, seed=None, options=None):
        del options
        return None, {"seed": seed, "hour": 9, "state": "reset"}

    def step(self, action: int = 0):
        return None, 0.0, False, False, {"action": action, "hour": 10, "state": "stepped"}

    def build_hourly_environment_24h(self, start_t: int | None = None):
        self.requested_start_t = start_t
        return [
            {
                "hour": hour,
                "month": 1,
                "season": "winter",
                "temperature_c": 1.0,
                "feels_like_c": 0.0,
                "precipitation_mm": 0.0,
                "is_wet": False,
                "weather_condition": "clear_night" if hour < 7 else "overcast",
                "sun_frac": 0.0,
                "is_daylight": False,
                "humidity_pct": 80.0,
                "wind_m_s": 2.0,
                "snow_cover": False,
            }
            for hour in range(24)
        ]


def _env() -> TimeWeatherEnv:
    env = TimeWeatherEnv(month=1, sample_rate_hours=1, horizon_hours=24 * 60, bern_map=FakeBernMap())
    env.reset(seed=123)
    return env


def _weather_state(env: TimeWeatherEnv) -> dict[str, object]:
    return {
        "_t": env._t,
        "_eps_prev": env._eps_prev,
        "_wet_prev": env._wet_prev,
        "_temp": env._temp,
        "_precip": env._precip,
        "_sun_frac": env._sun_frac,
        "_humidity": env._humidity,
        "_wind": env._wind,
        "_snow_cover_flag": env._snow_cover_flag,
        "_feels_like": env._feels_like,
        "_sun_day_factor": env._sun_day_factor,
        "rng_state": repr(env._rng.bit_generator.state),
    }


def test_time_weather_env_builds_hourly_environment_shape_fields_and_json() -> None:
    env = _env()

    hourly = env.build_hourly_environment_24h(start_t=0)

    required = {
        "hour",
        "month",
        "season",
        "temperature_c",
        "feels_like_c",
        "precipitation_mm",
        "is_wet",
        "weather_condition",
        "sun_frac",
        "is_daylight",
        "humidity_pct",
        "wind_m_s",
        "snow_cover",
    }
    assert len(hourly) == 24
    assert [entry["hour"] for entry in hourly] == list(range(24))
    assert all(required.issubset(entry) for entry in hourly)
    json.dumps(hourly)


def test_hourly_environment_does_not_include_legacy_mobility_fields() -> None:
    env = _env()

    hourly = env.build_hourly_environment_24h(start_t=0)

    legacy_mobility_fields = {
        "home_node",
        "current_node",
        "lat",
        "lon",
        "mobility",
        "is_at_home",
        "minutes_to_nearest_gym_walk",
        "minutes_to_nearest_gym_bike",
        "minutes_to_nearest_pool_walk",
        "minutes_to_nearest_pool_bike",
        "minutes_to_nearest_park_walk",
        "minutes_to_nearest_park_bike",
    }
    assert all(legacy_mobility_fields.isdisjoint(entry) for entry in hourly)


def test_build_hourly_environment_does_not_mutate_live_weather_state() -> None:
    env = _env()
    env.step(0)
    before = _weather_state(env)

    env.build_hourly_environment_24h(start_t=24)

    after = _weather_state(env)
    assert after == before


def test_simulation_runner_context_includes_hourly_environment_when_supported() -> None:
    persona = StudentHoursWrapper.from_zve_student_generic(name="environment_context_student")
    env = FakeRunnerEnv()
    runner = SimulationRunner(
        persona=persona,
        phase=YearPhase.SEMESTER,
        env=env,
        seed=37,
        use_year_structure=False,
    )

    context = runner.get_day_context(weekday=2)

    assert "hourly_environment_24h" in context
    assert len(context["hourly_environment_24h"]) == 24
    assert [entry["hour"] for entry in context["hourly_environment_24h"]] == list(range(24))
    assert env.requested_start_t == 2 * 24
