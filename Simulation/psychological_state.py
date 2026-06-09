from __future__ import annotations

from copy import deepcopy
from typing import Any


# Static initial psychological state from T1 student means of the simulated
# AIcoPA dataset. This module intentionally does not implement current-state
# dynamics, update functions, app-feedback logic, or multi-day adaptation.
DEFAULT_PSYCHOLOGICAL_STATE: dict[str, Any] = {
    "source": "T1_students_mean_from_simulated_AIcoPA_dataset",
    "n": 64,
    "values_normalized": {
        "habit": 0.34,
        "intention": 0.64,
        "attitude": 0.71,
        "injunctive_norm": 0.52,
        "descriptive_norm": 0.50,
        "perceived_behavioral_control": 0.66,
        "intrinsic_motivation": 0.80,
        "perceived_competence": 0.74,
        "perceived_choice": 0.74,
        "extrinsic_motivation": 0.40,
        "motivational_competence": 0.83,
        "volitional_self_control": 0.57,
        "action_planning": 0.40,
    },
    "raw_scale_means": {
        "habit": 2.35,
        "intention": 4.87,
        "attitude": 5.24,
        "injunctive_norm": 4.13,
        "descriptive_norm": 4.03,
        "perceived_behavioral_control": 4.97,
        "intrinsic_motivation": 3.21,
        "perceived_competence": 2.95,
        "perceived_choice": 2.98,
        "extrinsic_motivation": 1.59,
        "motivational_competence": 4.30,
        "volitional_self_control": 3.27,
        "action_planning": 2.20,
    },
}


def build_default_psychological_state() -> dict[str, Any]:
    """Return a fresh copy of the static initial T1 student mean state."""
    return deepcopy(DEFAULT_PSYCHOLOGICAL_STATE)
