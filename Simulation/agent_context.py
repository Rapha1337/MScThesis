from __future__ import annotations


def _as_hourly_list(name: str, entries) -> list[dict[str, object]]:
    hourly = [dict(entry) for entry in list(entries or [])]
    if len(hourly) != 24:
        raise ValueError(f"{name} must contain exactly 24 entries.")
    return hourly


def build_hourly_context_24h(
    constrained_schedule,
    hourly_accessibility_24h,
    hourly_energy_24h,
    hourly_environment_24h,
) -> list[dict[str, object]]:
    """Merge schedule, accessibility, energy, and environment into aligned hourly context."""
    schedule = _as_hourly_list("constrained_schedule", constrained_schedule)
    accessibility = _as_hourly_list("hourly_accessibility_24h", hourly_accessibility_24h)
    energy = _as_hourly_list("hourly_energy_24h", hourly_energy_24h)
    environment = _as_hourly_list("hourly_environment_24h", hourly_environment_24h)

    hourly_context: list[dict[str, object]] = []

    for index, (schedule_entry, accessibility_entry, energy_entry, environment_entry) in enumerate(
        zip(schedule, accessibility, energy, environment, strict=True)
    ):
        schedule_hour = schedule_entry.get("hour")
        accessibility_hour = accessibility_entry.get("hour")
        energy_hour = energy_entry.get("hour")
        environment_hour = environment_entry.get("hour")

        if not (
            schedule_hour == accessibility_hour
            and schedule_hour == energy_hour
            and schedule_hour == environment_hour
        ):
            raise ValueError(
                "Hourly context hour alignment failed at "
                f"index={index}: schedule_hour={schedule_hour}, "
                f"accessibility_hour={accessibility_hour}, "
                f"energy_hour={energy_hour}, environment_hour={environment_hour}"
            )

        energy_effects = energy_entry.get("energy_effects", energy_entry.get("energy_factors"))
        energy_drivers = energy_entry.get("drivers", energy_effects)

        hourly_context.append(
            {
                "hour": schedule_hour,
                "activity_type": schedule_entry.get("activity_type"),
                "subtype": schedule_entry.get("subtype"),
                "flexibility": schedule_entry.get("flexibility"),
                "current_location": accessibility_entry.get("current_location"),
                "previous_location": accessibility_entry.get("previous_location"),
                "location_changed_from_previous_hour": accessibility_entry.get(
                    "location_changed_from_previous_hour"
                ),
                "travel_from_previous_location": accessibility_entry.get("travel_from_previous_location"),
                "accessibility_from_current_location": accessibility_entry.get("accessibility"),
                "energy_level": energy_entry.get("energy_level"),
                "energy_score": energy_entry.get("energy_score", energy_entry.get("energy_level")),
                "energy_category": energy_entry.get("energy_category", energy_entry.get("category")),
                "energy_effects": energy_effects,
                "energy_drivers": energy_drivers,
                "active_constraints": energy_entry.get("active_constraints"),
                "month": environment_entry.get("month"),
                "season": environment_entry.get("season"),
                "temperature_c": environment_entry.get("temperature_c"),
                "feels_like_c": environment_entry.get("feels_like_c"),
                "precipitation_mm": environment_entry.get("precipitation_mm"),
                "is_wet": environment_entry.get("is_wet"),
                "weather_condition": environment_entry.get("weather_condition"),
                "sun_frac": environment_entry.get("sun_frac"),
                "is_daylight": environment_entry.get("is_daylight"),
                "humidity_pct": environment_entry.get("humidity_pct"),
                "wind_m_s": environment_entry.get("wind_m_s"),
                "snow_cover": environment_entry.get("snow_cover"),
            }
        )

    return hourly_context


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
    hourly_energy_24h=None,
    hourly_environment_24h=None,
) -> dict:
    context = {
        "persona_name": str(persona_name),
        "persona_profile": {
            "source": "pending_cluster_analysis",
            "data": None,
        },
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

    # Legacy alias: keep accepting energy_state as an input name for older callers
    # and preserve a top-level energy_state payload for existing consumers.
    energy_context = energy_level_result if energy_level_result is not None else energy_state
    if energy_context is not None:
        energy_payload = energy_context.to_dict()
        context["agent_state"] = {"energy": energy_payload}
        context["energy_state"] = dict(energy_payload)

    if hourly_energy_24h is not None:
        hourly_energy = list(hourly_energy_24h)
        if len(hourly_energy) != 24:
            raise ValueError("hourly_energy_24h must contain exactly 24 entries.")
        context["hourly_energy_24h"] = hourly_energy

    if hourly_environment_24h is not None:
        hourly_environment = list(hourly_environment_24h)
        if len(hourly_environment) != 24:
            raise ValueError("hourly_environment_24h must contain exactly 24 entries.")
        if any("hour" not in entry for entry in hourly_environment):
            raise ValueError("Each hourly_environment_24h entry must contain an hour field.")
        context["hourly_environment_24h"] = hourly_environment

    accessibility_context = accessibility_model if accessibility_model is not None else accessibility_profile
    if accessibility_context is not None:
        if hasattr(accessibility_context, "to_dict"):
            accessibility_payload = accessibility_context.to_dict()
        else:
            accessibility_payload = dict(accessibility_context)
        context["accessibility_model"] = accessibility_payload

        if hasattr(accessibility_context, "build_hourly_accessibility"):
            context["hourly_accessibility_24h"] = accessibility_context.build_hourly_accessibility(
                context["constrained_schedule"],
            )

    if all(
        key in context
        for key in (
            "constrained_schedule",
            "hourly_accessibility_24h",
            "hourly_energy_24h",
            "hourly_environment_24h",
        )
    ):
        context["hourly_context_24h"] = build_hourly_context_24h(
            context["constrained_schedule"],
            context["hourly_accessibility_24h"],
            context["hourly_energy_24h"],
            context["hourly_environment_24h"],
        )

    return context
