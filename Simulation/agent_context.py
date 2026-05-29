from __future__ import annotations


def build_agent_context(
    persona_name,
    phase,
    weekday,
    world_info,
    active_constraints,
    normal_schedule,
    constrained_schedule,
    energy_level_result=None,
    *,
    energy_state=None,
) -> dict:
    context = {
        "persona_name": str(persona_name),
        "phase": getattr(phase, "value", str(phase)),
        "weekday": int(weekday),
        "world_info": dict(world_info or {}),
        "active_constraints": list(active_constraints or []),
        "normal_schedule": list(normal_schedule or []),
        "constrained_schedule": list(constrained_schedule or []),
    }

    if energy_level_result is not None and energy_state is not None:
        raise ValueError("Pass either energy_level_result or legacy energy_state, not both.")

    # Legacy alias: keep accepting energy_state as an input name for older callers,
    # but expose only the canonical energy_level / energy_category keys in context.
    energy_context = energy_level_result if energy_level_result is not None else energy_state
    if energy_context is not None:
        context["agent_state"] = {"energy": energy_context.to_dict()}

    return context
