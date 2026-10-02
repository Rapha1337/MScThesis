from __future__ import annotations

import copy
import math
from typing import Any, Mapping

EMPIRICAL_PA_V1_2_MODE = "empirical_pa_v1_2"

# Held-out T1 calibration: simple OLS MVPA ~ action planning after excluding the
# four medoid personas (7067, 8361, 8237, 8303). Action planning is normalized
# to [0, 1]. The standardized beta is used only as a small directional weight;
# it is not interpreted as a probability or as a causal effect.
ACTION_PLANNING_BETA = 0.10728499572967862
ACTION_PLANNING_MEAN = 0.3898648648648649
ACTION_PLANNING_SD = 0.2737966534941716
ACTION_PLANNING_UNSTANDARDIZED_B = 1.9774300552445538
ACTION_PLANNING_INTERCEPT = 2.27298841765128
ACTION_PLANNING_P_VALUE = 0.19433507322993454
ACTION_PLANNING_R2 = 0.011510070308717202
ACTION_PLANNING_CALIBRATION_N = 148
ACTION_PLANNING_CALIBRATION_DESCRIPTION = (
    "Held-out T1 OLS calibration excluding the four simulated medoid personas: "
    "MVPA_hours_week ~ action_planning_normalized. Standardized beta is used as "
    "a small relative weighting coefficient only."
)


def action_planning_modifier(action_planning: float) -> float:
    """Return the standardized empirical action-planning modifier.

    The returned value is beta * z(action planning). It is a relative model
    weight, not an absolute probability change.
    """
    value = float(action_planning)
    if not math.isfinite(value):
        raise ValueError("action_planning must be finite.")
    if ACTION_PLANNING_SD <= 0:
        raise ValueError("ACTION_PLANNING_SD must be positive.")
    return ACTION_PLANNING_BETA * (
        (value - ACTION_PLANNING_MEAN) / ACTION_PLANNING_SD
    )


def extract_action_planning(agent_context: Mapping[str, Any]) -> float:
    psychological_state = agent_context.get("psychological_state")
    if not isinstance(psychological_state, Mapping):
        raise ValueError("agent context must contain psychological_state as an object.")
    values = psychological_state.get("values_normalized")
    if not isinstance(values, Mapping):
        raise ValueError(
            "psychological_state must contain values_normalized as an object."
        )
    raw = values.get("action_planning")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError("action_planning must be numeric in values_normalized.")
    value = float(raw)
    if not 0.0 <= value <= 1.0:
        raise ValueError("action_planning must be normalized to [0, 1].")
    return value


def neutralize_action_planning_for_llm1(
    agent_context: Mapping[str, Any],
) -> dict[str, Any]:
    """Copy a context and replace AP with the held-out T1 mean for LLM1.

    This prevents the individual action-planning value from being counted twice:
    once by the qualitative LLM1 policy matrix and again by the empirical
    calibration below. The original context is never mutated.
    """
    output = copy.deepcopy(dict(agent_context))
    psychological_state = output.get("psychological_state")
    if not isinstance(psychological_state, dict):
        raise ValueError("agent context must contain psychological_state as an object.")
    values = psychological_state.get("values_normalized")
    if not isinstance(values, dict):
        raise ValueError(
            "psychological_state must contain values_normalized as an object."
        )
    values["action_planning"] = ACTION_PLANNING_MEAN
    return output


def calibrate_unplanned_behavior_policy(
    behavior_policy: Mapping[str, float],
    *,
    action_planning: float,
) -> tuple[dict[str, float], dict[str, float | int | str]]:
    """Calibrate the no-plan skip/extra tendency with the held-out T1 beta.

    Empirical v1.2 has no schedule-derived PA blocks, so only the no-plan
    categories are behaviorally available. LLM1 first estimates psychological
    tendencies with action planning neutralized to the sample mean. The actual
    action-planning value then applies a small exponential tilt to the
    extra-activity odds using beta*z(AP). This preserves a modest empirical
    directional effect without treating beta as a percentage-point probability.

    Planned-activity categories are set to zero because they are impossible in
    this mode. The remaining skip/extra probabilities are renormalized.
    """
    modifier = action_planning_modifier(action_planning)
    skip = float(behavior_policy.get("skip_activity", 0.0))
    extra = float(behavior_policy.get("extra_activity", 0.0))
    if not math.isfinite(skip) or not math.isfinite(extra) or skip < 0.0 or extra < 0.0:
        raise ValueError("behavior_policy skip/extra values must be finite and non-negative.")

    weighted_extra = extra * math.exp(modifier)
    total = skip + weighted_extra
    if total <= 0.0:
        skip_probability = 0.5
        extra_probability = 0.5
    else:
        skip_probability = skip / total
        extra_probability = weighted_extra / total

    calibrated = {
        "do_planned_activity": 0.0,
        "adapt_activity": 0.0,
        "skip_activity": skip_probability,
        "extra_activity": extra_probability,
    }
    metadata: dict[str, float | int | str] = {
        "mode": EMPIRICAL_PA_V1_2_MODE,
        "action_planning_value": float(action_planning),
        "action_planning_population_mean": ACTION_PLANNING_MEAN,
        "action_planning_population_sd": ACTION_PLANNING_SD,
        "standardized_beta": ACTION_PLANNING_BETA,
        "modifier_beta_times_z": modifier,
        "calibration_n": ACTION_PLANNING_CALIBRATION_N,
        "calibration_p_value": ACTION_PLANNING_P_VALUE,
        "calibration_r2": ACTION_PLANNING_R2,
        "interpretation": (
            "Small relative tilt of unplanned PA propensity; beta is not treated "
            "as an absolute probability or causal effect."
        ),
    }
    return calibrated, metadata
