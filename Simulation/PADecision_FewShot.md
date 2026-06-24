### Beispiel 1: Klar positive psychologische Tendenzen und unterstützender Kontext

Geplante PA ist vorhanden; die psychologischen Tendenzen und der simulierte Tageskontext sprechen gemeinsam für die unveränderte Durchführung.

Input:

```json
{
  "persona_id": "ExamplePersona_01",
  "day_index": 1,
  "behavior_policy": {
    "do_planned_activity": 0.78,
    "adapt_activity": 0.12,
    "skip_activity": 0.06,
    "extra_activity": 0.04
  },
  "behavior_policy_raw": {
    "do_planned_activity": 0.78,
    "adapt_activity": 0.12,
    "skip_activity": 0.06,
    "extra_activity": 0.04
  },
  "decision_context_has_planned_pa": true,
  "valid_decision_categories": [
    "do_planned_activity",
    "adapt_activity",
    "skip_activity",
    "extra_activity"
  ],
  "decision_source": "llm2_contextual_decision",
  "planned_physical_activity": {
    "source": "current_day_schedule",
    "activity_type": "physical_activity",
    "scheduled_hours": [
      17,
      18
    ],
    "start_hour": 17,
    "end_hour": 19,
    "duration_min": 120,
    "schedule_entries": [
      {
        "hour": 17,
        "activity_type": "physical_activity",
        "subtype": "sport_anchor",
        "current_location": "indoor_activity",
        "active_constraints": []
      },
      {
        "hour": 18,
        "activity_type": "physical_activity",
        "subtype": "sport_anchor",
        "current_location": "indoor_activity",
        "active_constraints": []
      }
    ]
  },
  "was_physical_activity_planned_today": true,
  "daily_context": {
    "persona_id": "ExamplePersona_01",
    "seed": 101,
    "day_index": 1,
    "calendar_date": "2026-04-06",
    "phase": "normal",
    "weekday": 0,
    "weekday_name": "Monday",
    "hourly_context_24h": [
      {
        "hour": 0,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 1,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 2,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 3,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 4,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 5,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 6,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 7,
        "activity_type": "wake_up",
        "subtype": "morning_routine",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.72,
        "energy_category": "high",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.55,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 8,
        "activity_type": "eat",
        "subtype": "breakfast",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.72,
        "energy_category": "high",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.55,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 9,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.66,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.4,
        "humidity_pct": 55.0,
        "wind_m_s": 1.5,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.55,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 10,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.66,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.4,
        "humidity_pct": 55.0,
        "wind_m_s": 1.5,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.55,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 11,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.66,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.4,
        "humidity_pct": 55.0,
        "wind_m_s": 1.5,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.55,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 12,
        "activity_type": "eat",
        "subtype": "lunch",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.72,
        "energy_category": "high",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.55,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 13,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.66,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.4,
        "humidity_pct": 55.0,
        "wind_m_s": 1.5,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.55,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 14,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.66,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.4,
        "humidity_pct": 55.0,
        "wind_m_s": 1.5,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.55,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 15,
        "activity_type": "downtime",
        "subtype": "open_time",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.72,
        "energy_category": "high",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.4,
        "humidity_pct": 55.0,
        "wind_m_s": 1.5,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.55,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 16,
        "activity_type": "downtime",
        "subtype": "open_time",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.72,
        "energy_category": "high",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.4,
        "humidity_pct": 55.0,
        "wind_m_s": 1.5,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.55,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 17,
        "activity_type": "physical_activity",
        "subtype": "sport_anchor",
        "current_location": "indoor_activity",
        "active_constraints": [],
        "energy_level": 0.78,
        "energy_category": "high",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.4,
        "humidity_pct": 55.0,
        "wind_m_s": 1.5,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.55,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 18,
        "activity_type": "physical_activity",
        "subtype": "sport_anchor",
        "current_location": "indoor_activity",
        "active_constraints": [],
        "energy_level": 0.78,
        "energy_category": "high",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.4,
        "humidity_pct": 55.0,
        "wind_m_s": 1.5,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.55,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 19,
        "activity_type": "eat",
        "subtype": "dinner",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.72,
        "energy_category": "high",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.55,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 20,
        "activity_type": "downtime",
        "subtype": "open_time",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.72,
        "energy_category": "high",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.4,
        "humidity_pct": 55.0,
        "wind_m_s": 1.5,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 21,
        "activity_type": "downtime",
        "subtype": "open_time",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.72,
        "energy_category": "high",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.4,
        "humidity_pct": 55.0,
        "wind_m_s": 1.5,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 22,
        "activity_type": "downtime",
        "subtype": "open_time",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.72,
        "energy_category": "high",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.4,
        "humidity_pct": 55.0,
        "wind_m_s": 1.5,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      },
      {
        "hour": 23,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 0.8,
            "travel_times_min": {
              "walk": 10.0,
              "bike": 3.2,
              "car": 1.6
            }
          },
          "outdoor_activity": {
            "distance_km": 0.5,
            "travel_times_min": {
              "walk": 6.3,
              "bike": 2.0,
              "car": 1.0
            }
          }
        }
      }
    ]
  }
}
```

Output:

```json
{
  "persona_id": "ExamplePersona_01",
  "day_index": 1,
  "decision_code": 1,
  "decision_label": "do_planned_activity",
  "rationale_short": "Die psychologischen Tendenzen sprechen klar für die geplante PA, und der Tageskontext bietet hohe Energie, Tageslicht, trockene Bedingungen, freie Zeit und gut erreichbare Aktivitätsorte.",
  "diary_entry": "Ich hatte nach den Tagesaufgaben noch genug Energie und die Bedingungen passten gut. Deshalb habe ich die geplante Bewegung wie vorgesehen gemacht."
}
```

### Beispiel 2: Klar negative psychologische Tendenzen und hinderlicher Kontext

Geplante PA ist vorhanden; die psychologischen Tendenzen sprechen deutlich gegen PA und der simulierte Kontext enthält mehrere hinderliche Bedingungen.

Input:

```json
{
  "persona_id": "ExamplePersona_02",
  "day_index": 2,
  "behavior_policy": {
    "do_planned_activity": 0.07,
    "adapt_activity": 0.12,
    "skip_activity": 0.76,
    "extra_activity": 0.05
  },
  "behavior_policy_raw": {
    "do_planned_activity": 0.07,
    "adapt_activity": 0.12,
    "skip_activity": 0.76,
    "extra_activity": 0.05
  },
  "decision_context_has_planned_pa": true,
  "valid_decision_categories": [
    "do_planned_activity",
    "adapt_activity",
    "skip_activity",
    "extra_activity"
  ],
  "decision_source": "llm2_contextual_decision",
  "planned_physical_activity": {
    "source": "current_day_schedule",
    "activity_type": "physical_activity",
    "scheduled_hours": [
      18
    ],
    "start_hour": 18,
    "end_hour": 19,
    "duration_min": 60,
    "schedule_entries": [
      {
        "hour": 18,
        "activity_type": "physical_activity",
        "subtype": "sport_anchor",
        "current_location": "indoor_activity",
        "active_constraints": []
      }
    ]
  },
  "was_physical_activity_planned_today": true,
  "daily_context": {
    "persona_id": "ExamplePersona_02",
    "seed": 102,
    "day_index": 2,
    "calendar_date": "2026-04-07",
    "phase": "high_stress",
    "weekday": 1,
    "weekday_name": "Tuesday",
    "hourly_context_24h": [
      {
        "hour": 0,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 1,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 2,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 3,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 4,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 5,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 6,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 7,
        "activity_type": "wake_up",
        "subtype": "morning_routine",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.28,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 70.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 6.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 8,
        "activity_type": "eat",
        "subtype": "breakfast",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.28,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 70.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 6.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 9,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.22,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 9.6,
        "humidity_pct": 70.0,
        "wind_m_s": 6.0,
        "precipitation_mm": 6.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 10,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.22,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 9.6,
        "humidity_pct": 70.0,
        "wind_m_s": 6.0,
        "precipitation_mm": 6.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 11,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.22,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 9.6,
        "humidity_pct": 70.0,
        "wind_m_s": 6.0,
        "precipitation_mm": 6.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 12,
        "activity_type": "eat",
        "subtype": "lunch",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.28,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 70.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 6.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 13,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.22,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 9.6,
        "humidity_pct": 70.0,
        "wind_m_s": 6.0,
        "precipitation_mm": 6.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 14,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.22,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 9.6,
        "humidity_pct": 70.0,
        "wind_m_s": 6.0,
        "precipitation_mm": 6.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 15,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.22,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 9.6,
        "humidity_pct": 70.0,
        "wind_m_s": 6.0,
        "precipitation_mm": 6.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 16,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.22,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 9.6,
        "humidity_pct": 70.0,
        "wind_m_s": 6.0,
        "precipitation_mm": 6.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 17,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.22,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 9.6,
        "humidity_pct": 70.0,
        "wind_m_s": 6.0,
        "precipitation_mm": 6.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 18,
        "activity_type": "physical_activity",
        "subtype": "sport_anchor",
        "current_location": "indoor_activity",
        "active_constraints": [],
        "energy_level": 0.18,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 9.6,
        "humidity_pct": 70.0,
        "wind_m_s": 6.0,
        "precipitation_mm": 6.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 19,
        "activity_type": "eat",
        "subtype": "dinner",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.28,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 70.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 6.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 20,
        "activity_type": "downtime",
        "subtype": "open_time",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.28,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 9.6,
        "humidity_pct": 70.0,
        "wind_m_s": 6.0,
        "precipitation_mm": 6.2,
        "is_wet": true,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 21,
        "activity_type": "downtime",
        "subtype": "open_time",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.28,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 9.6,
        "humidity_pct": 70.0,
        "wind_m_s": 6.0,
        "precipitation_mm": 6.2,
        "is_wet": true,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 22,
        "activity_type": "downtime",
        "subtype": "open_time",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.28,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 9.6,
        "humidity_pct": 70.0,
        "wind_m_s": 6.0,
        "precipitation_mm": 6.2,
        "is_wet": true,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      },
      {
        "hour": 23,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 6.0,
            "travel_times_min": {
              "walk": 75.0,
              "bike": 24.0,
              "car": 12.0
            }
          },
          "outdoor_activity": {
            "distance_km": 5.0,
            "travel_times_min": {
              "walk": 62.5,
              "bike": 20.0,
              "car": 10.0
            }
          }
        }
      }
    ]
  }
}
```

Output:

```json
{
  "persona_id": "ExamplePersona_02",
  "day_index": 2,
  "decision_code": 0,
  "decision_label": "skip_activity",
  "rationale_short": "Die psychologischen Tendenzen sprechen deutlich gegen die geplante PA, und niedrige Energie, hoher Arbeitsanteil, Nässe, Niederschlag, Wind und schlechte Erreichbarkeit verstärken diese Richtung.",
  "diary_entry": "Ich habe die geplante Bewegung heute nicht gemacht. Nach dem langen Arbeitstag war meine Energie niedrig, und das nasse Wetter sowie der weite Weg machten es zusätzlich unattraktiv."
}
```

### Beispiel 3: Durchschnittlicher gemischter Fall mit angepasster PA

Geplante PA ist vorhanden; moderate gemischte Tendenzen treffen auf einen Kontext mit nutzbarem Zeitfenster, aber leichteren Barrieren.

Input:

```json
{
  "persona_id": "ExamplePersona_03",
  "day_index": 3,
  "behavior_policy": {
    "do_planned_activity": 0.34,
    "adapt_activity": 0.32,
    "skip_activity": 0.24,
    "extra_activity": 0.1
  },
  "behavior_policy_raw": {
    "do_planned_activity": 0.34,
    "adapt_activity": 0.32,
    "skip_activity": 0.24,
    "extra_activity": 0.1
  },
  "decision_context_has_planned_pa": true,
  "valid_decision_categories": [
    "do_planned_activity",
    "adapt_activity",
    "skip_activity",
    "extra_activity"
  ],
  "decision_source": "llm2_contextual_decision",
  "planned_physical_activity": {
    "source": "current_day_schedule",
    "activity_type": "physical_activity",
    "scheduled_hours": [
      18
    ],
    "start_hour": 18,
    "end_hour": 19,
    "duration_min": 60,
    "schedule_entries": [
      {
        "hour": 18,
        "activity_type": "physical_activity",
        "subtype": "sport_anchor",
        "current_location": "indoor_activity",
        "active_constraints": []
      }
    ]
  },
  "was_physical_activity_planned_today": true,
  "daily_context": {
    "persona_id": "ExamplePersona_03",
    "seed": 103,
    "day_index": 3,
    "calendar_date": "2026-04-08",
    "phase": "normal",
    "weekday": 2,
    "weekday_name": "Wednesday",
    "hourly_context_24h": [
      {
        "hour": 0,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 1,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 2,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 3,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 4,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 5,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 6,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 7,
        "activity_type": "wake_up",
        "subtype": "morning_routine",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.55,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 70.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.8,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 8,
        "activity_type": "eat",
        "subtype": "breakfast",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.55,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 70.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.8,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 9,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.5,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.8,
        "humidity_pct": 70.0,
        "wind_m_s": 3.0,
        "precipitation_mm": 0.8,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 10,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.5,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.8,
        "humidity_pct": 70.0,
        "wind_m_s": 3.0,
        "precipitation_mm": 0.8,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 11,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.5,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.8,
        "humidity_pct": 70.0,
        "wind_m_s": 3.0,
        "precipitation_mm": 0.8,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 12,
        "activity_type": "eat",
        "subtype": "lunch",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.55,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 70.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.8,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 13,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.5,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.8,
        "humidity_pct": 70.0,
        "wind_m_s": 3.0,
        "precipitation_mm": 0.8,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 14,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.5,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.8,
        "humidity_pct": 70.0,
        "wind_m_s": 3.0,
        "precipitation_mm": 0.8,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 15,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.5,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.8,
        "humidity_pct": 70.0,
        "wind_m_s": 3.0,
        "precipitation_mm": 0.8,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 16,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.5,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.8,
        "humidity_pct": 70.0,
        "wind_m_s": 3.0,
        "precipitation_mm": 0.8,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 17,
        "activity_type": "downtime",
        "subtype": "open_time",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.55,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.8,
        "humidity_pct": 70.0,
        "wind_m_s": 3.0,
        "precipitation_mm": 0.8,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 18,
        "activity_type": "physical_activity",
        "subtype": "sport_anchor",
        "current_location": "indoor_activity",
        "active_constraints": [],
        "energy_level": 0.54,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.8,
        "humidity_pct": 70.0,
        "wind_m_s": 3.0,
        "precipitation_mm": 0.8,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 19,
        "activity_type": "eat",
        "subtype": "dinner",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.55,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 70.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.8,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 20,
        "activity_type": "downtime",
        "subtype": "open_time",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.55,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.8,
        "humidity_pct": 70.0,
        "wind_m_s": 3.0,
        "precipitation_mm": 0.8,
        "is_wet": true,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 21,
        "activity_type": "downtime",
        "subtype": "open_time",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.55,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.8,
        "humidity_pct": 70.0,
        "wind_m_s": 3.0,
        "precipitation_mm": 0.8,
        "is_wet": true,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 22,
        "activity_type": "downtime",
        "subtype": "open_time",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.55,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.8,
        "humidity_pct": 70.0,
        "wind_m_s": 3.0,
        "precipitation_mm": 0.8,
        "is_wet": true,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 23,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      }
    ]
  }
}
```

Output:

```json
{
  "persona_id": "ExamplePersona_03",
  "day_index": 3,
  "decision_code": 2,
  "decision_label": "adapt_activity",
  "rationale_short": "Die psychologischen Tendenzen sind gemischt, unterstützen aber weiterhin etwas PA; mittlere Energie, leichter Niederschlag und ein begrenztes Abendfenster sprechen eher für eine angepasste statt unveränderte Umsetzung.",
  "diary_entry": "Ich war nicht ganz frisch und draußen war es leicht nass, aber ein kurzes Zeitfenster war noch da. Deshalb habe ich die geplante Einheit kürzer und ruhiger gemacht."
}
```

### Beispiel 4: Durchschnittlicher gemischter Fall ohne PA

Geplante PA ist vorhanden; die psychologischen Tendenzen sind ähnlich moderat wie im dritten Beispiel, aber mehrere alltägliche Barrieren summieren sich.

Input:

```json
{
  "persona_id": "ExamplePersona_04",
  "day_index": 4,
  "behavior_policy": {
    "do_planned_activity": 0.31,
    "adapt_activity": 0.28,
    "skip_activity": 0.31,
    "extra_activity": 0.1
  },
  "behavior_policy_raw": {
    "do_planned_activity": 0.31,
    "adapt_activity": 0.28,
    "skip_activity": 0.31,
    "extra_activity": 0.1
  },
  "decision_context_has_planned_pa": true,
  "valid_decision_categories": [
    "do_planned_activity",
    "adapt_activity",
    "skip_activity",
    "extra_activity"
  ],
  "decision_source": "llm2_contextual_decision",
  "planned_physical_activity": {
    "source": "current_day_schedule",
    "activity_type": "physical_activity",
    "scheduled_hours": [
      18
    ],
    "start_hour": 18,
    "end_hour": 19,
    "duration_min": 60,
    "schedule_entries": [
      {
        "hour": 18,
        "activity_type": "physical_activity",
        "subtype": "sport_anchor",
        "current_location": "indoor_activity",
        "active_constraints": []
      }
    ]
  },
  "was_physical_activity_planned_today": true,
  "daily_context": {
    "persona_id": "ExamplePersona_04",
    "seed": 104,
    "day_index": 4,
    "calendar_date": "2026-04-09",
    "phase": "normal",
    "weekday": 3,
    "weekday_name": "Thursday",
    "hourly_context_24h": [
      {
        "hour": 0,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 1,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 2,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 3,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 4,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 5,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 6,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 7,
        "activity_type": "wake_up",
        "subtype": "morning_routine",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.4,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 70.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 1.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 8,
        "activity_type": "eat",
        "subtype": "breakfast",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.4,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 70.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 1.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 9,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.38,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.2,
        "humidity_pct": 70.0,
        "wind_m_s": 4.5,
        "precipitation_mm": 1.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 10,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.38,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.2,
        "humidity_pct": 70.0,
        "wind_m_s": 4.5,
        "precipitation_mm": 1.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 11,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.38,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.2,
        "humidity_pct": 70.0,
        "wind_m_s": 4.5,
        "precipitation_mm": 1.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 12,
        "activity_type": "eat",
        "subtype": "lunch",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.4,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 70.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 1.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 13,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.38,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.2,
        "humidity_pct": 70.0,
        "wind_m_s": 4.5,
        "precipitation_mm": 1.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 14,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.38,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.2,
        "humidity_pct": 70.0,
        "wind_m_s": 4.5,
        "precipitation_mm": 1.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 15,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.38,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.2,
        "humidity_pct": 70.0,
        "wind_m_s": 4.5,
        "precipitation_mm": 1.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 16,
        "activity_type": "work",
        "subtype": "studying",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.38,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.2,
        "humidity_pct": 70.0,
        "wind_m_s": 4.5,
        "precipitation_mm": 1.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 17,
        "activity_type": "carework",
        "subtype": "carework",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.4,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.2,
        "humidity_pct": 70.0,
        "wind_m_s": 4.5,
        "precipitation_mm": 1.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 18,
        "activity_type": "physical_activity",
        "subtype": "sport_anchor",
        "current_location": "indoor_activity",
        "active_constraints": [],
        "energy_level": 0.36,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.2,
        "humidity_pct": 70.0,
        "wind_m_s": 4.5,
        "precipitation_mm": 1.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 19,
        "activity_type": "eat",
        "subtype": "dinner",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.4,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 70.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 1.2,
        "is_wet": true,
        "sun_frac": 0.12,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 20,
        "activity_type": "social_time",
        "subtype": "evening_social",
        "current_location": "unknown",
        "active_constraints": [],
        "energy_level": 0.4,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.2,
        "humidity_pct": 70.0,
        "wind_m_s": 4.5,
        "precipitation_mm": 1.2,
        "is_wet": true,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 21,
        "activity_type": "downtime",
        "subtype": "open_time",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.4,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.2,
        "humidity_pct": 70.0,
        "wind_m_s": 4.5,
        "precipitation_mm": 1.2,
        "is_wet": true,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 22,
        "activity_type": "downtime",
        "subtype": "open_time",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.4,
        "energy_category": "medium",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 10.2,
        "humidity_pct": 70.0,
        "wind_m_s": 4.5,
        "precipitation_mm": 1.2,
        "is_wet": true,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      },
      {
        "hour": 23,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.45,
        "energy_category": "low",
        "month": 4,
        "season": "spring",
        "temperature_c": 12.0,
        "feels_like_c": 11.2,
        "humidity_pct": 55.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.8,
              "bike": 6.0,
              "car": 3.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          }
        }
      }
    ]
  }
}
```

Output:

```json
{
  "persona_id": "ExamplePersona_04",
  "day_index": 4,
  "decision_code": 0,
  "decision_label": "skip_activity",
  "rationale_short": "Die psychologischen Tendenzen sind moderat und gemischt; zusammen mit niedrigerer Energie, engem Abendverlauf, Carework, Nässe und Wind reichen die alltäglichen Barrieren heute gegen PA.",
  "diary_entry": "Ich habe kurz überlegt, die Bewegung noch einzubauen, aber nach Arbeit und Carework war der Abend eng. Mit der niedrigen Energie und dem nassen Wetter habe ich die geplante PA heute ausgelassen."
}
```
