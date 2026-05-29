from __future__ import annotations

CANONICAL_INTENSITIES = {"low", "medium", "high"}
LEGACY_INTENSITY_ALIASES = {"mid": "medium"}


def normalize_intensity(
    intensity: object,
    *,
    default: str | None = None,
    allow_none: bool = False,
) -> str | None:
    """Return the canonical intensity label low/medium/high.

    The legacy label ``mid`` is accepted only as an alias for ``medium``.
    """
    if intensity is None:
        if allow_none:
            return None
        if default is not None:
            return default
        raise ValueError("intensity must be one of: low, medium, high")

    value = str(intensity).lower()
    value = LEGACY_INTENSITY_ALIASES.get(value, value)

    if value in CANONICAL_INTENSITIES:
        return value
    if default is not None:
        return default
    raise ValueError("intensity must be one of: low, medium, high")
