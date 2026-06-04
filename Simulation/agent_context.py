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
    accessibility_model=None,
    accessibility_profile=None,
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

    if accessibility_model is not None and accessibility_profile is not None:
        raise ValueError("Pass either accessibility_model or accessibility_profile, not both.")

    # Legacy alias: keep accepting energy_state as an input name for older callers,
    # but expose only the canonical energy_level / energy_category keys in context.
    energy_context = energy_level_result if energy_level_result is not None else energy_state
    if energy_context is not None:
        context["agent_state"] = {"energy": energy_context.to_dict()}

    accessibility_context = accessibility_model if accessibility_model is not None else accessibility_profile
    if accessibility_context is not None:
        if hasattr(accessibility_context, "to_dict"):
            accessibility_payload = accessibility_context.to_dict()
        else:
            accessibility_payload = dict(accessibility_context)
        context["accessibility_model"] = accessibility_payload

    return context
