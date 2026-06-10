from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any, Mapping

from accessibility_model import build_accessibility_model
from persona_wrappers import StudentHoursWrapper, StudentWrapper
from psychological_state import build_psychological_state
from schedule_model_student import YearPhase
from simulation_runner import SimulationRunner


def _install_lightweight_optional_dependency_stubs() -> None:
    """Allow TimeWeatherEnv construction in minimal test/demo environments."""
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


class _LightweightBernMap:
    """Minimal BernMap-compatible object for context export without OSM access."""

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


REQUIRED_INPUT_PARAMETER_NAMES: tuple[str, ...] = (
    "day_index",
    "fitness_hours_week",
    "social_hours_week",
    "work_hours_week",
    "carework_hours_week",
    "workplace_distance_km",
    "indoor_activity_distance_km",
    "outdoor_activity_distance_km",
)

SCHEDULE_PARAMETER_NAMES: tuple[str, ...] = (
    "fitness_hours_week",
    "social_hours_week",
    "work_hours_week",
    "carework_hours_week",
)

ACCESSIBILITY_PARAMETER_NAMES: tuple[str, ...] = (
    "workplace_distance_km",
    "indoor_activity_distance_km",
    "outdoor_activity_distance_km",
)

PSYCHOLOGICAL_SEED_OFFSET = 10_000_019


def _psychological_seed_from_persona_seed(persona_seed: int) -> int:
    """Derive a stable seed namespace for psychological start-state sampling."""
    return int(persona_seed) + PSYCHOLOGICAL_SEED_OFFSET


DEFAULT_INPUT_PARAMETERS: dict[str, float | int] = {
    "day_index": 0,
    "fitness_hours_week": 5.5,
    "social_hours_week": 10.0,
    "work_hours_week": 4.5,
    "carework_hours_week": 0.0,
    "workplace_distance_km": 3.0,
    "indoor_activity_distance_km": 1.2,
    "outdoor_activity_distance_km": 0.6,
}


def _normalize_input_parameters(input_parameters: Mapping[str, Any] | None) -> dict[str, object]:
    """Return a compact JSON-serializable simulation input parameter dict."""
    normalized = dict(DEFAULT_INPUT_PARAMETERS)
    if input_parameters:
        for key in REQUIRED_INPUT_PARAMETER_NAMES:
            if key in input_parameters:
                normalized[key] = input_parameters[key]

    normalized["day_index"] = int(normalized["day_index"])
    for key in SCHEDULE_PARAMETER_NAMES + ACCESSIBILITY_PARAMETER_NAMES:
        normalized[key] = float(normalized[key])

    return normalized


def _student_parameters_from_inputs(persona_id: str, input_parameters: Mapping[str, Any]) -> StudentHoursWrapper:
    return StudentHoursWrapper(
        name=persona_id,
        fitness_hours_week=float(input_parameters["fitness_hours_week"]),
        social_hours_week=float(input_parameters["social_hours_week"]),
        work_hours_week=float(input_parameters["work_hours_week"]),
        carework_hours_week=float(input_parameters["carework_hours_week"]),
        workplace_distance_km=float(input_parameters["workplace_distance_km"]),
        indoor_activity_distance_km=float(input_parameters["indoor_activity_distance_km"]),
        outdoor_activity_distance_km=float(input_parameters["outdoor_activity_distance_km"]),
    )


def _build_accessibility_model_from_parameters(accessibility_parameters: Mapping[str, Any]):
    return build_accessibility_model(
        workplace_distance_km=float(accessibility_parameters["workplace_distance_km"]),
        indoor_activity_distance_km=float(accessibility_parameters["indoor_activity_distance_km"]),
        outdoor_activity_distance_km=float(accessibility_parameters["outdoor_activity_distance_km"]),
    )


def _build_accessibility_parameters(persona_parameters: StudentHoursWrapper) -> dict[str, object]:
    accessibility_inputs = persona_parameters.accessibility_input_parameters()
    model = _build_accessibility_model_from_parameters(accessibility_inputs)
    return {
        **accessibility_inputs,
        "accessibility_model": model.to_dict(),
    }


def _json_ready(value: Any) -> Any:
    """Recursively coerce common scalar/container values to JSON-native objects."""
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if hasattr(value, "item") and callable(value.item):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    if hasattr(value, "value"):
        return _json_ready(value.value)
    return value


def build_agent_contexts(
    n_personas: int,
    base_seed: int,
    input_parameters: dict,
) -> list[dict]:
    """Build deterministic persona-level simulation contexts for JSON export.

    The returned payloads make wiring explicit: schedule-hour inputs are mapped
    through StudentHoursWrapper, while POI-distance inputs are mapped through the
    AccessibilityModel used by SimulationRunner day-context generation.
    """
    if n_personas < 1:
        raise ValueError("n_personas must be >= 1")

    normalized_inputs = _normalize_input_parameters(input_parameters)
    template_parameters = _student_parameters_from_inputs("student_template", normalized_inputs)
    wrapper = StudentWrapper(parameters=template_parameters, base_seed=int(base_seed))
    generated_personas = wrapper.create_personas(n_personas=n_personas, phase=YearPhase.NORMAL)

    agent_contexts: list[dict] = []
    for generated in generated_personas:
        persona_id = str(generated["persona_name"])
        seed = int(generated["persona_seed"])
        persona_parameters = _student_parameters_from_inputs(persona_id, normalized_inputs)
        schedule_parameters = persona_parameters.to_structure_parameters(seed=seed)

        wired_parameters = {
            "fitness_hours_week": "Mapped by StudentHoursWrapper to sport_frequency/sport_fixedness and the physical_activity weekly budget.",
            "social_hours_week": "Mapped by StudentHoursWrapper to evening/weekend social intensity and the social_time weekly budget.",
            "work_hours_week": "Mapped by StudentHoursWrapper to employment_load and the paid_work weekly budget.",
            "carework_hours_week": "Passed through StudentHoursWrapper to StudentStructureParameters.carework_hours_week and the carework weekly budget when > 0.",
            "workplace_distance_km": "Passed to build_accessibility_model and exposed in hourly poi_accessibility for the workplace target.",
            "indoor_activity_distance_km": "Passed to build_accessibility_model and exposed in hourly poi_accessibility for the indoor_activity target.",
            "outdoor_activity_distance_km": "Passed to build_accessibility_model and exposed in hourly poi_accessibility for the outdoor_activity target.",
        }

        unsupported_or_partially_wired_parameters: dict[str, str] = {}

        agent_contexts.append(
            _json_ready(
                {
                    "persona_id": persona_id,
                    "seed": seed,
                    "psychological_state": build_psychological_state(
                        seed=_psychological_seed_from_persona_seed(seed)
                    ),
                    "input_parameters": {
                        **persona_parameters.input_parameters(),
                        "day_index": normalized_inputs["day_index"],
                    },
                    "generated_persona_summary": persona_parameters.summary(seed=seed),
                    "accessibility_parameters": _build_accessibility_parameters(persona_parameters),
                    "schedule_parameters": {
                        "name": schedule_parameters.name,
                        "schedule_rigidity": schedule_parameters.schedule_rigidity,
                        "phase_variability": schedule_parameters.phase_variability,
                        "university_load": schedule_parameters.university_load,
                        "employment_load": schedule_parameters.employment_load,
                        "study_intensity": schedule_parameters.study_intensity,
                        "sport_frequency": schedule_parameters.sport_frequency,
                        "sport_fixedness": schedule_parameters.sport_fixedness,
                        "evening_flexibility": schedule_parameters.evening_flexibility,
                        "day_fragmentation": schedule_parameters.day_fragmentation,
                        "random_event_rate": schedule_parameters.random_event_rate,
                        "commute_load": schedule_parameters.commute_load,
                        "location_switch_frequency": schedule_parameters.location_switch_frequency,
                        "weekend_structure": schedule_parameters.weekend_structure,
                        "weekend_social_intensity": schedule_parameters.weekend_social_intensity,
                        "social_hours_week": schedule_parameters.social_hours_week,
                        "carework_hours_week": schedule_parameters.carework_hours_week,
                    },
                    "wired_parameters": wired_parameters,
                    "unsupported_or_partially_wired_parameters": unsupported_or_partially_wired_parameters,
                }
            )
        )

    return agent_contexts


def build_runner_from_agent_context(agent_context: dict) -> SimulationRunner:
    """Build and reset a SimulationRunner for one exported agent context."""
    input_parameters = _normalize_input_parameters(agent_context.get("input_parameters", {}))
    seed = int(agent_context["seed"])
    persona_id = str(agent_context["persona_id"])
    persona = _student_parameters_from_inputs(persona_id, input_parameters)
    accessibility_parameters = dict(
        agent_context.get("accessibility_parameters")
        or persona.accessibility_input_parameters()
    )
    _install_lightweight_optional_dependency_stubs()
    from env_time_weather import TimeWeatherEnv

    env = TimeWeatherEnv(month=1, sample_rate_hours=1, horizon_hours=24 * 365, bern_map=_LightweightBernMap())
    accessibility_model = _build_accessibility_model_from_parameters(accessibility_parameters)
    runner = SimulationRunner(
        persona=persona,
        phase=YearPhase.NORMAL,
        env=env,
        seed=seed,
        use_year_structure=True,
        accessibility_model=accessibility_model,
    )
    runner.reset_world()
    return runner


def generate_day_contexts_for_personas(
    n_personas: int,
    base_seed: int,
    day_index: int,
    input_parameters: dict,
) -> dict:
    """Generate one selected 24h day context for each deterministic persona."""
    merged_inputs = dict(input_parameters or {})
    merged_inputs["day_index"] = int(day_index)
    agent_contexts = build_agent_contexts(
        n_personas=n_personas,
        base_seed=base_seed,
        input_parameters=merged_inputs,
    )

    personas: list[dict[str, object]] = []
    for agent_context in agent_contexts:
        runner = build_runner_from_agent_context(agent_context)
        runner._sim_hour = int(day_index) * 24
        day_context = runner.get_day_context()
        personas.append(
            {
                "persona_id": agent_context["persona_id"],
                "seed": agent_context["seed"],
                "input_parameters": agent_context["input_parameters"],
                "agent_context": agent_context,
                "day_context": day_context,
            }
        )

    payload = {
        "simulation_metadata": {
            "base_seed": int(base_seed),
            "day_index": int(day_index),
            "n_personas": int(n_personas),
        },
        "personas": personas,
    }
    payload = _json_ready(payload)
    json.dumps(payload)
    return payload


def export_day_contexts_to_json(payload: dict, output_path: str | Path) -> Path:
    """Write day-context payload as UTF-8, indented JSON after serialization validation."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable_payload = _json_ready(payload)
    encoded = json.dumps(serializable_payload, ensure_ascii=False, indent=2)
    path.write_text(encoded + "\n", encoding="utf-8")
    json.loads(path.read_text(encoding="utf-8"))
    return path
