from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from accessibility_model import build_accessibility_model
from constraints.illness import AcuteIllnessConstraint
from constraints.manager import ConstraintManager
from persona_wrappers import StudentHoursWrapper
from schedule_model_student import YearPhase
from simulation_runner import SimulationRunner


class DemoEnv:
    def reset(self, seed=None, options=None):
        del options
        return None, {"seed": seed, "hour": 10, "state": "reset"}

    def step(self, action: int = 0):
        return None, 0.0, False, False, {"action": action, "hour": 10, "state": "stepped"}


def _build_accessibility_model():
    return build_accessibility_model(
        workplace_distance_km=3.0,
        indoor_activity_distance_km=1.2,
        outdoor_activity_distance_km=0.6,
    )


def run_demo() -> None:
    persona = StudentHoursWrapper.from_zve_student_generic(name="hourly_energy_demo_student")
    illness = AcuteIllnessConstraint(name="demo_flu", intensity="medium", start_weekday=1, duration_days=1)
    runner = SimulationRunner(
        persona=persona,
        phase=YearPhase.SEMESTER,
        env=DemoEnv(),
        constraint_manager=ConstraintManager([illness]),
        seed=37,
        use_year_structure=False,
        accessibility_model=_build_accessibility_model(),
    )

    context = runner.get_day_context(weekday=1)
    hourly_energy = context["hourly_energy_24h"]
    hourly_accessibility = {
        entry["hour"]: entry
        for entry in context.get("hourly_accessibility_24h", [])
    }

    selected_hours = [7, 10, 14, 18, 22]
    selected = []
    for entry in hourly_energy:
        if entry["hour"] not in selected_hours:
            continue
        accessibility_entry = hourly_accessibility.get(entry["hour"], {})
        selected.append(
            {
                "hour": entry["hour"],
                "activity_type": entry["activity_type"],
                "energy_level": entry["energy_level"],
                "energy_score": entry["energy_score"],
                "energy_category": entry["energy_category"],
                "drivers": entry["drivers"],
                "active_constraints": entry["active_constraints"],
                "current_location": accessibility_entry.get("current_location"),
            }
        )

    print("Selected hourly energy context from SimulationRunner:")
    print(json.dumps(selected, indent=2, sort_keys=True))


if __name__ == "__main__":
    run_demo()
