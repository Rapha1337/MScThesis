from __future__ import annotations

import random
from typing import Any


# Backend-compatible initial psychological state model from T1 student profiles
# of the simulated AIcoPA dataset. This module intentionally does not implement
# current-state dynamics, update functions, app-feedback logic, or multi-day
# adaptation. The Excel source data is not required at runtime; the reference
# parameters below are embedded directly for deterministic seed-based sampling.
BACKEND_CONSTRUCT_RANGES: dict[str, tuple[float, float]] = {
    "automaticity": (1, 7),
    "pa_specific_self_control": (1, 5),
    "action_planning": (1, 6),
    "intention": (1, 7),
    "perceived_behavioral_control": (1, 7),
    "attitude_toward_the_behavior": (1, 7),
    "subjective_norm": (1, 7),
    "interest_enjoyment": (0, 4),
    "perceived_competence": (0, 4),
    "perceived_choice": (0, 4),
    "pressure_tension": (0, 4),
    "motivational_competence": (1, 5),
}

PSYCHOLOGICAL_STATE_REFERENCE: dict[str, Any] = {
    "source": "T1_students_from_simulated_AIcoPA_dataset",
    "reference_group": "T1_Studierend",
    "n": 64,
    "constructs": {
        "automaticity": {
            "backend_range": (1, 7),
            "norm_mean": 0.337,
            "norm_sd": 0.287,
            "norm_var": 0.082,
            "backend_raw_mean": 3.02,
            "backend_raw_sd": 1.72,
            "backend_raw_var": 2.967,
        },
        "pa_specific_self_control": {
            "backend_range": (1, 5),
            "norm_mean": 0.568,
            "norm_sd": 0.200,
            "norm_var": 0.040,
            "backend_raw_mean": 3.27,
            "backend_raw_sd": 0.80,
            "backend_raw_var": 0.639,
        },
        "action_planning": {
            "backend_range": (1, 6),
            "norm_mean": 0.399,
            "norm_sd": 0.269,
            "norm_var": 0.072,
            "backend_raw_mean": 2.99,
            "backend_raw_sd": 1.34,
            "backend_raw_var": 1.806,
        },
        "intention": {
            "backend_range": (1, 7),
            "norm_mean": 0.645,
            "norm_sd": 0.188,
            "norm_var": 0.035,
            "backend_raw_mean": 4.87,
            "backend_raw_sd": 1.13,
            "backend_raw_var": 1.273,
        },
        "perceived_behavioral_control": {
            "backend_range": (1, 7),
            "norm_mean": 0.661,
            "norm_sd": 0.181,
            "norm_var": 0.033,
            "backend_raw_mean": 4.97,
            "backend_raw_sd": 1.09,
            "backend_raw_var": 1.184,
        },
        "attitude_toward_the_behavior": {
            "backend_range": (1, 7),
            "norm_mean": 0.707,
            "norm_sd": 0.195,
            "norm_var": 0.038,
            "backend_raw_mean": 5.24,
            "backend_raw_sd": 1.17,
            "backend_raw_var": 1.367,
        },
        "subjective_norm": {
            "backend_range": (1, 7),
            "norm_mean": 0.513,
            "norm_sd": 0.156,
            "norm_var": 0.024,
            "backend_raw_mean": 4.08,
            "backend_raw_sd": 0.94,
            "backend_raw_var": 0.877,
        },
        "interest_enjoyment": {
            "backend_range": (0, 4),
            "norm_mean": 0.803,
            "norm_sd": 0.164,
            "norm_var": 0.027,
            "backend_raw_mean": 3.21,
            "backend_raw_sd": 0.65,
            "backend_raw_var": 0.428,
        },
        "perceived_competence": {
            "backend_range": (0, 4),
            "norm_mean": 0.738,
            "norm_sd": 0.151,
            "norm_var": 0.023,
            "backend_raw_mean": 2.95,
            "backend_raw_sd": 0.60,
            "backend_raw_var": 0.363,
        },
        "perceived_choice": {
            "backend_range": (0, 4),
            "norm_mean": 0.744,
            "norm_sd": 0.139,
            "norm_var": 0.019,
            "backend_raw_mean": 2.98,
            "backend_raw_sd": 0.56,
            "backend_raw_var": 0.310,
        },
        "pressure_tension": {
            "backend_range": (0, 4),
            "norm_mean": 0.398,
            "norm_sd": 0.146,
            "norm_var": 0.021,
            "backend_raw_mean": 1.59,
            "backend_raw_sd": 0.58,
            "backend_raw_var": 0.341,
        },
        "motivational_competence": {
            "backend_range": (1, 5),
            "norm_mean": 0.826,
            "norm_sd": 0.145,
            "norm_var": 0.021,
            "backend_raw_mean": 4.30,
            "backend_raw_sd": 0.58,
            "backend_raw_var": 0.335,
        },
    },
}

PSYCHOLOGICAL_STATE_CORRELATION_MATRIX: dict[str, dict[str, float]] = {
    "automaticity": {
        "automaticity": 1.000,
        "pa_specific_self_control": 0.251,
        "action_planning": 0.209,
        "intention": 0.119,
        "perceived_behavioral_control": 0.238,
        "attitude_toward_the_behavior": 0.062,
        "subjective_norm": 0.081,
        "interest_enjoyment": 0.129,
        "perceived_competence": 0.186,
        "perceived_choice": 0.081,
        "pressure_tension": 0.022,
        "motivational_competence": 0.199,
    },
    "pa_specific_self_control": {
        "automaticity": 0.251,
        "pa_specific_self_control": 1.000,
        "action_planning": 0.163,
        "intention": 0.325,
        "perceived_behavioral_control": 0.152,
        "attitude_toward_the_behavior": 0.134,
        "subjective_norm": 0.186,
        "interest_enjoyment": 0.249,
        "perceived_competence": 0.012,
        "perceived_choice": 0.095,
        "pressure_tension": -0.072,
        "motivational_competence": -0.039,
    },
    "action_planning": {
        "automaticity": 0.209,
        "pa_specific_self_control": 0.163,
        "action_planning": 1.000,
        "intention": 0.432,
        "perceived_behavioral_control": 0.172,
        "attitude_toward_the_behavior": 0.027,
        "subjective_norm": 0.104,
        "interest_enjoyment": 0.224,
        "perceived_competence": 0.224,
        "perceived_choice": 0.112,
        "pressure_tension": -0.020,
        "motivational_competence": 0.127,
    },
    "intention": {
        "automaticity": 0.119,
        "pa_specific_self_control": 0.325,
        "action_planning": 0.432,
        "intention": 1.000,
        "perceived_behavioral_control": 0.178,
        "attitude_toward_the_behavior": 0.429,
        "subjective_norm": 0.135,
        "interest_enjoyment": 0.111,
        "perceived_competence": 0.231,
        "perceived_choice": 0.149,
        "pressure_tension": -0.040,
        "motivational_competence": 0.187,
    },
    "perceived_behavioral_control": {
        "automaticity": 0.238,
        "pa_specific_self_control": 0.152,
        "action_planning": 0.172,
        "intention": 0.178,
        "perceived_behavioral_control": 1.000,
        "attitude_toward_the_behavior": 0.179,
        "subjective_norm": 0.206,
        "interest_enjoyment": 0.024,
        "perceived_competence": 0.067,
        "perceived_choice": 0.033,
        "pressure_tension": 0.061,
        "motivational_competence": 0.080,
    },
    "attitude_toward_the_behavior": {
        "automaticity": 0.062,
        "pa_specific_self_control": 0.134,
        "action_planning": 0.027,
        "intention": 0.429,
        "perceived_behavioral_control": 0.179,
        "attitude_toward_the_behavior": 1.000,
        "subjective_norm": 0.288,
        "interest_enjoyment": -0.076,
        "perceived_competence": 0.035,
        "perceived_choice": -0.048,
        "pressure_tension": -0.193,
        "motivational_competence": -0.058,
    },
    "subjective_norm": {
        "automaticity": 0.081,
        "pa_specific_self_control": 0.186,
        "action_planning": 0.104,
        "intention": 0.135,
        "perceived_behavioral_control": 0.206,
        "attitude_toward_the_behavior": 0.288,
        "subjective_norm": 1.000,
        "interest_enjoyment": 0.105,
        "perceived_competence": -0.016,
        "perceived_choice": -0.057,
        "pressure_tension": 0.067,
        "motivational_competence": -0.004,
    },
    "interest_enjoyment": {
        "automaticity": 0.129,
        "pa_specific_self_control": 0.249,
        "action_planning": 0.224,
        "intention": 0.111,
        "perceived_behavioral_control": 0.024,
        "attitude_toward_the_behavior": -0.076,
        "subjective_norm": 0.105,
        "interest_enjoyment": 1.000,
        "perceived_competence": 0.452,
        "perceived_choice": 0.321,
        "pressure_tension": 0.214,
        "motivational_competence": 0.478,
    },
    "perceived_competence": {
        "automaticity": 0.186,
        "pa_specific_self_control": 0.012,
        "action_planning": 0.224,
        "intention": 0.231,
        "perceived_behavioral_control": 0.067,
        "attitude_toward_the_behavior": 0.035,
        "subjective_norm": -0.016,
        "interest_enjoyment": 0.452,
        "perceived_competence": 1.000,
        "perceived_choice": 0.333,
        "pressure_tension": 0.133,
        "motivational_competence": 0.592,
    },
    "perceived_choice": {
        "automaticity": 0.081,
        "pa_specific_self_control": 0.095,
        "action_planning": 0.112,
        "intention": 0.149,
        "perceived_behavioral_control": 0.033,
        "attitude_toward_the_behavior": -0.048,
        "subjective_norm": -0.057,
        "interest_enjoyment": 0.321,
        "perceived_competence": 0.333,
        "perceived_choice": 1.000,
        "pressure_tension": 0.069,
        "motivational_competence": 0.279,
    },
    "pressure_tension": {
        "automaticity": 0.022,
        "pa_specific_self_control": -0.072,
        "action_planning": -0.020,
        "intention": -0.040,
        "perceived_behavioral_control": 0.061,
        "attitude_toward_the_behavior": -0.193,
        "subjective_norm": 0.067,
        "interest_enjoyment": 0.214,
        "perceived_competence": 0.133,
        "perceived_choice": 0.069,
        "pressure_tension": 1.000,
        "motivational_competence": 0.222,
    },
    "motivational_competence": {
        "automaticity": 0.199,
        "pa_specific_self_control": -0.039,
        "action_planning": 0.127,
        "intention": 0.187,
        "perceived_behavioral_control": 0.080,
        "attitude_toward_the_behavior": -0.058,
        "subjective_norm": -0.004,
        "interest_enjoyment": 0.478,
        "perceived_competence": 0.592,
        "perceived_choice": 0.279,
        "pressure_tension": 0.222,
        "motivational_competence": 1.000,
    },
}

CONSTRUCT_NAMES: tuple[str, ...] = tuple(BACKEND_CONSTRUCT_RANGES)


def _clip_normalized(value: float) -> float:
    return min(1.0, max(0.0, value))


def _denormalize(normalized_value: float, construct_name: str) -> float:
    min_value, max_value = BACKEND_CONSTRUCT_RANGES[construct_name]
    return min_value + normalized_value * (max_value - min_value)


def _covariance_matrix() -> list[list[float]]:
    covariance: list[list[float]] = []
    constructs = PSYCHOLOGICAL_STATE_REFERENCE["constructs"]
    for row_name in CONSTRUCT_NAMES:
        row_sd = float(constructs[row_name]["norm_sd"])
        covariance_row: list[float] = []
        for column_name in CONSTRUCT_NAMES:
            column_sd = float(constructs[column_name]["norm_sd"])
            correlation = PSYCHOLOGICAL_STATE_CORRELATION_MATRIX[row_name][column_name]
            covariance_row.append(row_sd * column_sd * correlation)
        covariance.append(covariance_row)
    return covariance


def _cholesky_decomposition(matrix: list[list[float]]) -> list[list[float]]:
    """Return a lower-triangular Cholesky factor for a positive-semidefinite matrix."""
    size = len(matrix)
    jitter = 0.0
    for _ in range(8):
        lower = [[0.0 for _ in range(size)] for _ in range(size)]
        try:
            for row in range(size):
                for column in range(row + 1):
                    diagonal_jitter = jitter if row == column else 0.0
                    value = matrix[row][column] + diagonal_jitter
                    value -= sum(lower[row][k] * lower[column][k] for k in range(column))
                    if row == column:
                        if value <= 0.0:
                            if value > -1e-12:
                                value = 0.0
                            else:
                                raise ValueError("Covariance matrix is not positive semidefinite.")
                        lower[row][column] = value**0.5
                    elif lower[column][column] == 0.0:
                        lower[row][column] = 0.0
                    else:
                        lower[row][column] = value / lower[column][column]
            return lower
        except ValueError:
            jitter = 1e-9 if jitter == 0.0 else jitter * 10.0

    raise ValueError("Covariance matrix could not be stabilized for sampling.")


def _sample_multivariate_normal(seed: int) -> dict[str, float]:
    rng = random.Random(seed)
    means = [
        float(PSYCHOLOGICAL_STATE_REFERENCE["constructs"][name]["norm_mean"])
        for name in CONSTRUCT_NAMES
    ]
    lower = _cholesky_decomposition(_covariance_matrix())
    standard_normals = [rng.gauss(0.0, 1.0) for _ in CONSTRUCT_NAMES]

    sampled_values: dict[str, float] = {}
    for row_index, construct_name in enumerate(CONSTRUCT_NAMES):
        correlated_offset = sum(
            lower[row_index][column] * standard_normals[column]
            for column in range(row_index + 1)
        )
        sampled_values[construct_name] = _clip_normalized(means[row_index] + correlated_offset)

    return sampled_values


def _mean_state_values() -> dict[str, float]:
    return {
        construct_name: float(PSYCHOLOGICAL_STATE_REFERENCE["constructs"][construct_name]["norm_mean"])
        for construct_name in CONSTRUCT_NAMES
    }


def _format_psychological_state(
    values_normalized: dict[str, float], seed: int, method: str
) -> dict[str, Any]:
    rounded_normalized = {
        construct_name: round(_clip_normalized(values_normalized[construct_name]), 3)
        for construct_name in CONSTRUCT_NAMES
    }
    raw_scale_means = {
        construct_name: round(_denormalize(rounded_normalized[construct_name], construct_name), 2)
        for construct_name in CONSTRUCT_NAMES
    }

    return {
        "source": PSYCHOLOGICAL_STATE_REFERENCE["source"],
        "reference_group": PSYCHOLOGICAL_STATE_REFERENCE["reference_group"],
        "n": PSYCHOLOGICAL_STATE_REFERENCE["n"],
        "sampling_method": method,
        "seed": int(seed),
        "values_normalized": rounded_normalized,
        "raw_scale_means": raw_scale_means,
    }


def build_psychological_state(seed: int, method: str = "multivariate_normal") -> dict[str, Any]:
    """Build a deterministic seed-based initial psychological state.

    Sampling happens on normalized 0-1 values. Raw scale means are always
    back-transformed from the rounded normalized values and backend ranges.
    """
    if method == "multivariate_normal":
        sampled_values = _sample_multivariate_normal(int(seed))
    elif method == "mean":
        sampled_values = _mean_state_values()
    else:
        raise ValueError(f"Unsupported psychological_state sampling method: {method!r}")

    return _format_psychological_state(sampled_values, seed=int(seed), method=method)


def build_default_psychological_state() -> dict[str, Any]:
    """Return a deterministic legacy fallback using the backend construct list."""
    return build_psychological_state(seed=0)


DEFAULT_PSYCHOLOGICAL_STATE: dict[str, Any] = build_default_psychological_state()
