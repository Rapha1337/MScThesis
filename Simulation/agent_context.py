from __future__ import annotations


def build_agent_context(
    persona_name,
    phase,
    weekday,
    world_info,
    active_constraints,
    normal_schedule,
    constrained_schedule,
) -> dict:
    return {
        "persona_name": str(persona_name),
        "phase": getattr(phase, "value", str(phase)),
        "weekday": int(weekday),
        "world_info": dict(world_info or {}),
        "active_constraints": list(active_constraints or []),
        "normal_schedule": list(normal_schedule or []),
        "constrained_schedule": list(constrained_schedule or []),
    }
