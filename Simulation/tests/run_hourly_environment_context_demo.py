from __future__ import annotations

from pathlib import Path
import json
import sys
import types

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))


def _install_lightweight_optional_dependency_stubs() -> None:
    """Keep the demo runnable in minimal environments without GIS/Gym deps."""
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


_install_lightweight_optional_dependency_stubs()

from accessibility_model import build_accessibility_model
from env_time_weather import TimeWeatherEnv
from persona_wrappers import StudentHoursWrapper
from schedule_model_student import YearPhase
from simulation_runner import SimulationRunner


class DemoBernMap:
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


def run_demo() -> None:
    persona = StudentHoursWrapper.from_zve_student_generic(name="hourly_environment_demo_student")
    env = TimeWeatherEnv(month=1, sample_rate_hours=1, horizon_hours=24 * 60, bern_map=DemoBernMap())
    accessibility_model = build_accessibility_model(
        workplace_distance_km=3.0,
        indoor_activity_distance_km=1.2,
        outdoor_activity_distance_km=0.6,
    )
    runner = SimulationRunner(
        persona=persona,
        phase=YearPhase.SEMESTER,
        env=env,
        seed=37,
        use_year_structure=False,
        accessibility_model=accessibility_model,
    )

    context = runner.get_day_context()
    hourly_context = context["hourly_context_24h"]
    transition_hour = next(
        (
            entry["hour"]
            for entry in hourly_context
            if entry["location_changed_from_previous_hour"]
        ),
        10,
    )
    selected_hours = {
        max(0, transition_hour - 1),
        transition_hour,
        min(23, transition_hour + 1),
    }

    selected = [
        {
            "hour": entry["hour"],
            "activity_type": entry["activity_type"],
            "subtype": entry["subtype"],
            "current_location": entry["current_location"],
            "travel_from_previous_location": entry["travel_from_previous_location"],
            "energy_score": entry["energy_score"],
            "energy_level": entry["energy_level"],
            "weather_condition": entry["weather_condition"],
            "temperature_c": entry["temperature_c"],
        }
        for entry in hourly_context
        if entry["hour"] in selected_hours
    ]

    print("Selected merged hourly_context_24h entries around a location transition:")
    print(json.dumps(selected, indent=2, sort_keys=True))


if __name__ == "__main__":
    run_demo()
