from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
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


def _constraint_summary(constraints: list[dict[str, object]] | None) -> str:
    if not constraints:
        return "-"
    return ",".join(
        f"{constraint.get('name', constraint.get('type', 'constraint'))}:{constraint.get('intensity', '-')}"
        for constraint in constraints
    )


def _poi_summary(entry: dict[str, object], target: str) -> str:
    poi = entry.get("poi_accessibility", {})
    if not isinstance(poi, dict) or target not in poi:
        return "-"
    target_payload = poi[target]
    if not isinstance(target_payload, dict):
        return "-"
    travel_times = target_payload.get("travel_times_min", {})
    if not isinstance(travel_times, dict):
        travel_times = {}
    distance = target_payload.get("distance_km")
    walk = travel_times.get("walk")
    bike = travel_times.get("bike")
    car = travel_times.get("car")
    return f"{distance}km w/b/c={walk}/{bike}/{car}m"


def _parse_args() -> object:
    parser = ArgumentParser(description="Print a full-day compact hourly LLM-context demo.")
    parser.add_argument("--day-index", type=int, default=0, help="Absolute simulated day index from year start.")
    parser.add_argument("--seed", type=int, default=37, help="Seed for persona/year/weather simulation.")
    parser.add_argument(
        "--persona-index",
        type=int,
        default=0,
        help="Optional index suffix for the demo persona name; useful when comparing deterministic variants.",
    )
    return parser.parse_args()


def run_demo(day_index: int = 0, seed: int = 37, persona_index: int = 0) -> None:
    if day_index < 0:
        raise ValueError("day_index must be >= 0")

    persona = StudentHoursWrapper.from_zve_student_generic(
        name=f"hourly_environment_demo_student_{persona_index}"
    )
    env = TimeWeatherEnv(month=1, sample_rate_hours=1, horizon_hours=24 * 365, bern_map=DemoBernMap())
    accessibility_model = build_accessibility_model(
        workplace_distance_km=3.0,
        indoor_activity_distance_km=1.2,
        outdoor_activity_distance_km=0.6,
    )
    runner = SimulationRunner(
        persona=persona,
        phase=YearPhase.SEMESTER,
        env=env,
        seed=seed,
        use_year_structure=True,
        accessibility_model=accessibility_model,
    )
    runner.reset_world()
    runner._sim_hour = day_index * 24

    context = runner.get_day_context()
    hourly_context = context["hourly_context_24h"]
    week_index = (day_index // 7) % runner.n_weeks
    weekday = day_index % 7
    phase = context["phase"]
    month = hourly_context[0]["month"]
    active_constraints = context.get("active_constraints", [])
    active_events = []
    if runner.year_structure is not None:
        active_events = [
            getattr(event, "event_id", str(event))
            for event in runner._get_active_events_for_day(week_index, weekday)
        ]

    print("Hourly environment/context demo")
    print(
        "Header: "
        f"day_index={day_index}, week_index={week_index}, weekday={weekday}, "
        f"phase={phase}, month={month}, "
        f"active_events={active_events or '-'}, "
        f"active_constraints={_constraint_summary(active_constraints)}"
    )
    print(
        "| hour | activity/subtype | location | energy | constraints | temp | feels | "
        "humidity | wind | precip/wet | sun/daylight | indoor POI | outdoor POI |"
    )
    print(
        "|---:|---|---|---:|---|---:|---:|---:|---:|---|---|---|---|"
    )
    for entry in hourly_context:
        precip_wet = f"{entry['precipitation_mm']}mm/{entry['is_wet']}"
        sun_daylight = f"{entry['sun_frac']}/{entry['is_daylight']}"
        print(
            "| "
            f"{entry['hour']} | "
            f"{entry['activity_type']}/{entry['subtype']} | "
            f"{entry['current_location']} | "
            f"{entry['energy_level']} | "
            f"{_constraint_summary(entry.get('active_constraints'))} | "
            f"{entry['temperature_c']} | "
            f"{entry['feels_like_c']} | "
            f"{entry['humidity_pct']} | "
            f"{entry['wind_m_s']} | "
            f"{precip_wet} | "
            f"{sun_daylight} | "
            f"{_poi_summary(entry, 'indoor_activity')} | "
            f"{_poi_summary(entry, 'outdoor_activity')} |"
        )


if __name__ == "__main__":
    args = _parse_args()
    run_demo(day_index=args.day_index, seed=args.seed, persona_index=args.persona_index)
