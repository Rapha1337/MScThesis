### Beispiel 1: Förderliche Behavior Policy und günstiger Tageskontext

Input:

```json
{
  "persona_id": "ExamplePersona_01",
  "day_index": 1,
  "behavior_policy": {
    "do_planned_activity": 0.56,
    "adapt_activity": 0.24,
    "postpone_activity": 0.06,
    "skip_activity": 0.04,
    "extra_activity": 0.08,
    "app_ignored": 0.02
  },
  "planned_activity": {
    "activity_type": "indoor_activity",
    "duration_min": 30,
    "intensity": "moderate",
    "preferred_time_window": [
      18,
      21
    ]
  },
  "daily_context": {
    "seed": 393430179,
    "phase": "holiday",
    "weekday": 0,
    "task_description": "Use the compact 24-hour schedule, energy, quantitative weather, daylight, constraints, location, and POI-accessibility context to reason about this persona's day.",
    "input_parameters": {
      "fitness_hours_week": 6.0,
      "social_hours_week": 8.0,
      "work_hours_week": 5.0,
      "carework_hours_week": 7.0,
      "workplace_distance_km": 3.0,
      "indoor_activity_distance_km": 1.2,
      "outdoor_activity_distance_km": 0.6,
      "day_index": 1
    },
    "selected_schedule_parameters": {
      "name": "ExamplePersona_01",
      "schedule_rigidity": 0.632913952800257,
      "phase_variability": 0.52,
      "university_load": 0.6236915869451473,
      "employment_load": 0.29045642804675137,
      "study_intensity": 0.6079748598758692,
      "sport_frequency": 0.5980611308232949,
      "sport_fixedness": 0.5276284825850128,
      "evening_flexibility": 0.6184465652824861,
      "day_fragmentation": 0.41198814060498207,
      "random_event_rate": 0.18,
      "commute_load": 0.2,
      "location_switch_frequency": 0.22,
      "weekend_structure": 0.34,
      "weekend_social_intensity": 0.6626283886892752,
      "social_hours_week": 8.0,
      "carework_hours_week": 7.0
    },
    "hourly_context_24h": [
      {
        "hour": 0,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.558,
        "energy_category": "medium",
        "temperature_c": -2.106,
        "feels_like_c": -5.692,
        "humidity_pct": 86.115,
        "wind_m_s": 2.661,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
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
        "energy_level": 0.54,
        "energy_category": "medium",
        "temperature_c": -1.001,
        "feels_like_c": -1.001,
        "humidity_pct": 89.663,
        "wind_m_s": 0.317,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
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
        "energy_level": 0.574,
        "energy_category": "medium",
        "temperature_c": -2.256,
        "feels_like_c": -2.256,
        "humidity_pct": 89.941,
        "wind_m_s": 1.332,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
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
        "energy_level": 0.482,
        "energy_category": "medium",
        "temperature_c": -3.067,
        "feels_like_c": -5.016,
        "humidity_pct": 97.57,
        "wind_m_s": 1.37,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
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
        "energy_level": 0.551,
        "energy_category": "medium",
        "temperature_c": -3.229,
        "feels_like_c": -5.889,
        "humidity_pct": 94.34,
        "wind_m_s": 1.775,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
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
        "energy_level": 0.564,
        "energy_category": "medium",
        "temperature_c": -4.701,
        "feels_like_c": -4.701,
        "humidity_pct": 90.677,
        "wind_m_s": 0.233,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
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
        "energy_level": 0.577,
        "energy_category": "medium",
        "temperature_c": -2.789,
        "feels_like_c": -5.739,
        "humidity_pct": 97.157,
        "wind_m_s": 2.025,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 7,
        "activity_type": "wake_up",
        "subtype": "morning_wake_up",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.597,
        "energy_category": "medium",
        "temperature_c": -2.739,
        "feels_like_c": -6.946,
        "humidity_pct": 91.745,
        "wind_m_s": 3.164,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
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
        "energy_level": 0.577,
        "energy_category": "medium",
        "temperature_c": -1.173,
        "feels_like_c": -3.41,
        "humidity_pct": 81.542,
        "wind_m_s": 1.703,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.064,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 9,
        "activity_type": "downtime",
        "subtype": "between_blocks",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.746,
        "energy_category": "high",
        "temperature_c": -0.386,
        "feels_like_c": -3.888,
        "humidity_pct": 83.941,
        "wind_m_s": 2.917,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.361,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 10,
        "activity_type": "downtime",
        "subtype": "between_blocks",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.753,
        "energy_category": "high",
        "temperature_c": -0.352,
        "feels_like_c": -0.352,
        "humidity_pct": 85.43,
        "wind_m_s": 1.13,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.473,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 11,
        "activity_type": "downtime",
        "subtype": "between_blocks",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.729,
        "energy_category": "high",
        "temperature_c": 1.386,
        "feels_like_c": -1.195,
        "humidity_pct": 81.033,
        "wind_m_s": 2.317,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.625,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
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
        "energy_level": 0.602,
        "energy_category": "medium",
        "temperature_c": 2.625,
        "feels_like_c": -0.202,
        "humidity_pct": 82.147,
        "wind_m_s": 2.824,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.656,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 13,
        "activity_type": "work",
        "subtype": "paid_work",
        "current_location": "workplace",
        "active_constraints": [],
        "energy_level": 0.589,
        "energy_category": "medium",
        "temperature_c": 3.325,
        "feels_like_c": 3.325,
        "humidity_pct": 69.064,
        "wind_m_s": 1.253,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.726,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.1,
            "travel_times_min": {
              "walk": 26.25,
              "bike": 8.4,
              "car": 4.2
            }
          },
          "outdoor_activity": {
            "distance_km": 1.8,
            "travel_times_min": {
              "walk": 22.5,
              "bike": 7.2,
              "car": 3.6
            }
          }
        }
      },
      {
        "hour": 14,
        "activity_type": "work",
        "subtype": "paid_work",
        "current_location": "workplace",
        "active_constraints": [],
        "energy_level": 0.585,
        "energy_category": "medium",
        "temperature_c": 1.806,
        "feels_like_c": 0.521,
        "humidity_pct": 71.554,
        "wind_m_s": 1.361,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.484,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.1,
            "travel_times_min": {
              "walk": 26.25,
              "bike": 8.4,
              "car": 4.2
            }
          },
          "outdoor_activity": {
            "distance_km": 1.8,
            "travel_times_min": {
              "walk": 22.5,
              "bike": 7.2,
              "car": 3.6
            }
          }
        }
      },
      {
        "hour": 15,
        "activity_type": "work",
        "subtype": "paid_work",
        "current_location": "workplace",
        "active_constraints": [],
        "energy_level": 0.629,
        "energy_category": "medium",
        "temperature_c": 2.979,
        "feels_like_c": 2.979,
        "humidity_pct": 73.407,
        "wind_m_s": 0.493,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.332,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.1,
            "travel_times_min": {
              "walk": 26.25,
              "bike": 8.4,
              "car": 4.2
            }
          },
          "outdoor_activity": {
            "distance_km": 1.8,
            "travel_times_min": {
              "walk": 22.5,
              "bike": 7.2,
              "car": 3.6
            }
          }
        }
      },
      {
        "hour": 16,
        "activity_type": "work",
        "subtype": "paid_work",
        "current_location": "workplace",
        "active_constraints": [],
        "energy_level": 0.733,
        "energy_category": "high",
        "temperature_c": 2.587,
        "feels_like_c": 0.519,
        "humidity_pct": 85.021,
        "wind_m_s": 2.034,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.123,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.1,
            "travel_times_min": {
              "walk": 26.25,
              "bike": 8.4,
              "car": 4.2
            }
          },
          "outdoor_activity": {
            "distance_km": 1.8,
            "travel_times_min": {
              "walk": 22.5,
              "bike": 7.2,
              "car": 3.6
            }
          }
        }
      },
      {
        "hour": 17,
        "activity_type": "work",
        "subtype": "paid_work",
        "current_location": "workplace",
        "active_constraints": [],
        "energy_level": 0.693,
        "energy_category": "high",
        "temperature_c": 3.337,
        "feels_like_c": 0.474,
        "humidity_pct": 71.624,
        "wind_m_s": 3.043,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.1,
            "travel_times_min": {
              "walk": 26.25,
              "bike": 8.4,
              "car": 4.2
            }
          },
          "outdoor_activity": {
            "distance_km": 1.8,
            "travel_times_min": {
              "walk": 22.5,
              "bike": 7.2,
              "car": 3.6
            }
          }
        }
      },
      {
        "hour": 18,
        "activity_type": "eat",
        "subtype": "dinner",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.707,
        "energy_category": "high",
        "temperature_c": 2.826,
        "feels_like_c": -0.51,
        "humidity_pct": 70.516,
        "wind_m_s": 3.543,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 19,
        "activity_type": "downtime",
        "subtype": "open_time",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.641,
        "energy_category": "medium",
        "temperature_c": 2.431,
        "feels_like_c": 2.431,
        "humidity_pct": 81.436,
        "wind_m_s": 1.222,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 20,
        "activity_type": "downtime",
        "subtype": "evening_wind_down",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.691,
        "energy_category": "high",
        "temperature_c": 1.026,
        "feels_like_c": -1.73,
        "humidity_pct": 76.162,
        "wind_m_s": 2.423,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 21,
        "activity_type": "downtime",
        "subtype": "evening_wind_down",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.58,
        "energy_category": "medium",
        "temperature_c": 1.365,
        "feels_like_c": -1.318,
        "humidity_pct": 93.924,
        "wind_m_s": 2.413,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 22,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.522,
        "energy_category": "medium",
        "temperature_c": 0.584,
        "feels_like_c": 0.584,
        "humidity_pct": 91.408,
        "wind_m_s": 0.887,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
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
        "energy_level": 0.526,
        "energy_category": "medium",
        "temperature_c": 1.1,
        "feels_like_c": -1.681,
        "humidity_pct": 95.898,
        "wind_m_s": 2.462,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
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
  "decision_label": "done_as_planned",
  "rationale_short": "Die Behavior Policy spricht überwiegend für die geplante Aktivität und der Tageskontext bietet am Abend ein realistisches Zeitfenster mit ausreichender Energie und guter Erreichbarkeit.",
  "diary_entry": "Am Abend hatte ich endlich etwas Zeit für mich und habe mich daran erinnert, dass ich heute noch körperlich aktiv sein wollte. Ich war nicht völlig voller Energie, aber es war machbar und danach war ich zufrieden, dass ich es gemacht habe."
}
```

### Beispiel 2: Niedrige Behavior Policy und ungünstiger Tageskontext

Input:

```json
{
  "persona_id": "ExamplePersona_02",
  "day_index": 2,
  "behavior_policy": {
    "do_planned_activity": 0.18,
    "adapt_activity": 0.17,
    "postpone_activity": 0.2,
    "skip_activity": 0.3,
    "extra_activity": 0.05,
    "app_ignored": 0.1
  },
  "planned_activity": {
    "activity_type": "indoor_activity",
    "duration_min": 30,
    "intensity": "moderate",
    "preferred_time_window": [
      18,
      21
    ]
  },
  "daily_context": {
    "seed": 152221923,
    "day_index": 2,
    "phase": "high_stress",
    "weekday": 1,
    "task_description": "Use the compact 24-hour schedule, energy, quantitative weather, daylight, constraints, location, and POI-accessibility context to reason about this persona's day.",
    "input_parameters": {
      "fitness_hours_week": 6.0,
      "social_hours_week": 8.0,
      "work_hours_week": 5.0,
      "carework_hours_week": 7.0,
      "workplace_distance_km": 3.0,
      "indoor_activity_distance_km": 1.2,
      "outdoor_activity_distance_km": 0.6,
      "day_index": 2
    },
    "selected_schedule_parameters": {
      "name": "ExamplePersona_02",
      "schedule_rigidity": 0.78,
      "phase_variability": 0.52,
      "university_load": 0.74,
      "employment_load": 0.2540321715948124,
      "study_intensity": 0.81,
      "sport_frequency": 0.24,
      "sport_fixedness": 0.31,
      "evening_flexibility": 0.22,
      "day_fragmentation": 0.72,
      "random_event_rate": 0.18,
      "commute_load": 0.2,
      "location_switch_frequency": 0.22,
      "weekend_structure": 0.34,
      "weekend_social_intensity": 0.45,
      "social_hours_week": 8.0,
      "carework_hours_week": 7.0
    },
    "hourly_context_24h": [
      {
        "hour": 0,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.505,
        "energy_category": "medium",
        "temperature_c": 0.256,
        "feels_like_c": -2.547,
        "humidity_pct": 96.99,
        "wind_m_s": 2.336,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 1,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.447,
        "energy_category": "low",
        "temperature_c": -0.963,
        "feels_like_c": -2.658,
        "humidity_pct": 91.269,
        "wind_m_s": 1.385,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 2,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.492,
        "energy_category": "medium",
        "temperature_c": -2.301,
        "feels_like_c": -2.301,
        "humidity_pct": 87.186,
        "wind_m_s": 0.67,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 3,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.468,
        "energy_category": "medium",
        "temperature_c": -2.5,
        "feels_like_c": -2.5,
        "humidity_pct": 96.076,
        "wind_m_s": 0.771,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 4,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.493,
        "energy_category": "medium",
        "temperature_c": -2.197,
        "feels_like_c": -2.197,
        "humidity_pct": 96.764,
        "wind_m_s": 0.98,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 5,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.528,
        "energy_category": "medium",
        "temperature_c": -3.075,
        "feels_like_c": -3.075,
        "humidity_pct": 88.306,
        "wind_m_s": 0.827,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 6,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.476,
        "energy_category": "medium",
        "temperature_c": -2.64,
        "feels_like_c": -6.496,
        "humidity_pct": 90.866,
        "wind_m_s": 2.823,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 7,
        "activity_type": "wake_up",
        "subtype": "morning_wake_up",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.445,
        "energy_category": "low",
        "temperature_c": -2.097,
        "feels_like_c": -5.871,
        "humidity_pct": 87.349,
        "wind_m_s": 2.848,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 8,
        "activity_type": "eat",
        "subtype": "breakfast",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.433,
        "energy_category": "low",
        "temperature_c": -2.01,
        "feels_like_c": -2.01,
        "humidity_pct": 82.666,
        "wind_m_s": 1.127,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.048,
        "is_daylight": true,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 9,
        "activity_type": "work",
        "subtype": "university",
        "current_location": "workplace",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.591,
        "energy_category": "medium",
        "temperature_c": -0.575,
        "feels_like_c": -4.064,
        "humidity_pct": 81.716,
        "wind_m_s": 2.863,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.217,
        "is_daylight": true,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.1,
            "travel_times_min": {
              "walk": 26.25,
              "bike": 8.4,
              "car": 4.2
            }
          },
          "outdoor_activity": {
            "distance_km": 1.8,
            "travel_times_min": {
              "walk": 22.5,
              "bike": 7.2,
              "car": 3.6
            }
          }
        }
      },
      {
        "hour": 10,
        "activity_type": "work",
        "subtype": "university",
        "current_location": "workplace",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.62,
        "energy_category": "medium",
        "temperature_c": 0.227,
        "feels_like_c": -2.177,
        "humidity_pct": 78.687,
        "wind_m_s": 1.988,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.453,
        "is_daylight": true,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.1,
            "travel_times_min": {
              "walk": 26.25,
              "bike": 8.4,
              "car": 4.2
            }
          },
          "outdoor_activity": {
            "distance_km": 1.8,
            "travel_times_min": {
              "walk": 22.5,
              "bike": 7.2,
              "car": 3.6
            }
          }
        }
      },
      {
        "hour": 11,
        "activity_type": "work",
        "subtype": "university",
        "current_location": "workplace",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.596,
        "energy_category": "medium",
        "temperature_c": 2.025,
        "feels_like_c": 0.699,
        "humidity_pct": 74.033,
        "wind_m_s": 1.404,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.501,
        "is_daylight": true,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.1,
            "travel_times_min": {
              "walk": 26.25,
              "bike": 8.4,
              "car": 4.2
            }
          },
          "outdoor_activity": {
            "distance_km": 1.8,
            "travel_times_min": {
              "walk": 22.5,
              "bike": 7.2,
              "car": 3.6
            }
          }
        }
      },
      {
        "hour": 12,
        "activity_type": "eat",
        "subtype": "lunch",
        "current_location": "workplace",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.554,
        "energy_category": "medium",
        "temperature_c": 2.236,
        "feels_like_c": -1.063,
        "humidity_pct": 79.851,
        "wind_m_s": 3.318,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.517,
        "is_daylight": true,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.1,
            "travel_times_min": {
              "walk": 26.25,
              "bike": 8.4,
              "car": 4.2
            }
          },
          "outdoor_activity": {
            "distance_km": 1.8,
            "travel_times_min": {
              "walk": 22.5,
              "bike": 7.2,
              "car": 3.6
            }
          }
        }
      },
      {
        "hour": 13,
        "activity_type": "work",
        "subtype": "university",
        "current_location": "workplace",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.353,
        "energy_category": "low",
        "temperature_c": 2.735,
        "feels_like_c": 0.413,
        "humidity_pct": 68.192,
        "wind_m_s": 2.298,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.527,
        "is_daylight": true,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.1,
            "travel_times_min": {
              "walk": 26.25,
              "bike": 8.4,
              "car": 4.2
            }
          },
          "outdoor_activity": {
            "distance_km": 1.8,
            "travel_times_min": {
              "walk": 22.5,
              "bike": 7.2,
              "car": 3.6
            }
          }
        }
      },
      {
        "hour": 14,
        "activity_type": "work",
        "subtype": "university",
        "current_location": "workplace",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.346,
        "energy_category": "low",
        "temperature_c": 3.035,
        "feels_like_c": 1.277,
        "humidity_pct": 71.167,
        "wind_m_s": 1.829,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.465,
        "is_daylight": true,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.1,
            "travel_times_min": {
              "walk": 26.25,
              "bike": 8.4,
              "car": 4.2
            }
          },
          "outdoor_activity": {
            "distance_km": 1.8,
            "travel_times_min": {
              "walk": 22.5,
              "bike": 7.2,
              "car": 3.6
            }
          }
        }
      },
      {
        "hour": 15,
        "activity_type": "work",
        "subtype": "self_study",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.392,
        "energy_category": "low",
        "temperature_c": 3.657,
        "feels_like_c": 2.525,
        "humidity_pct": 73.616,
        "wind_m_s": 1.423,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.343,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 16,
        "activity_type": "work",
        "subtype": "self_study",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.48,
        "energy_category": "medium",
        "temperature_c": 2.048,
        "feels_like_c": -0.952,
        "humidity_pct": 88.0,
        "wind_m_s": 1.645,
        "precipitation_mm": 2.409,
        "is_wet": true,
        "sun_frac": 0.06,
        "is_daylight": true,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 17,
        "activity_type": "work",
        "subtype": "self_study",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.431,
        "energy_category": "low",
        "temperature_c": 1.134,
        "feels_like_c": -1.866,
        "humidity_pct": 88.0,
        "wind_m_s": 2.037,
        "precipitation_mm": 1.405,
        "is_wet": true,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 18,
        "activity_type": "eat",
        "subtype": "dinner",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.407,
        "energy_category": "low",
        "temperature_c": 0.175,
        "feels_like_c": -2.825,
        "humidity_pct": 87.283,
        "wind_m_s": 2.768,
        "precipitation_mm": 0.593,
        "is_wet": true,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 19,
        "activity_type": "carework",
        "subtype": "carework",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.35,
        "energy_category": "low",
        "temperature_c": -0.668,
        "feels_like_c": -3.668,
        "humidity_pct": 90.105,
        "wind_m_s": 2.278,
        "precipitation_mm": 0.29,
        "is_wet": true,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 20,
        "activity_type": "carework",
        "subtype": "carework",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.301,
        "energy_category": "low",
        "temperature_c": -0.966,
        "feels_like_c": -3.966,
        "humidity_pct": 88.513,
        "wind_m_s": 1.61,
        "precipitation_mm": 0.324,
        "is_wet": true,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 21,
        "activity_type": "downtime",
        "subtype": "evening_wind_down",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.277,
        "energy_category": "low",
        "temperature_c": -2.021,
        "feels_like_c": -5.021,
        "humidity_pct": 88.881,
        "wind_m_s": 2.573,
        "precipitation_mm": 0.24,
        "is_wet": true,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 22,
        "activity_type": "downtime",
        "subtype": "evening_wind_down",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.25,
        "energy_category": "low",
        "temperature_c": -1.383,
        "feels_like_c": -4.383,
        "humidity_pct": 94.812,
        "wind_m_s": 1.262,
        "precipitation_mm": 0.55,
        "is_wet": true,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 23,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.434,
        "energy_category": "low",
        "temperature_c": -1.668,
        "feels_like_c": -4.668,
        "humidity_pct": 99.229,
        "wind_m_s": 1.57,
        "precipitation_mm": 0.24,
        "is_wet": true,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": true,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
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
  "decision_label": "not_done",
  "rationale_short": "Die Behavior Policy spricht nur schwach für körperliche Aktivität und der Tageskontext erschwert die Umsetzung durch niedrige Energie, hohe Belastung und fehlende passende Zeitfenster.",
  "diary_entry": "Ich habe heute zwar kurz daran gedacht, mich noch zu bewegen, aber es fühlte sich einfach nach zu viel an. Der Tag war voll, mein Kopf war müde und ich hatte weder Energie noch Lust, mich noch aufzuraffen."
}
```

### Beispiel 3: Durchschnittliche Behavior Policy und durchschnittlicher Tageskontext mit angepasster Umsetzung

Input:

```json
{
  "persona_id": "ExamplePersona_03",
  "day_index": 3,
  "behavior_policy": {
    "do_planned_activity": 0.36,
    "adapt_activity": 0.26,
    "postpone_activity": 0.16,
    "skip_activity": 0.1,
    "extra_activity": 0.08,
    "app_ignored": 0.04
  },
  "planned_activity": {
    "activity_type": "indoor_activity",
    "duration_min": 30,
    "intensity": "moderate",
    "preferred_time_window": [
      8,
      11
    ]
  },
  "daily_context": {
    "seed": 320303103,
    "day_index": 3,
    "phase": "normal",
    "weekday": 2,
    "task_description": "Use the compact 24-hour schedule, energy, quantitative weather, daylight, constraints, location, and POI-accessibility context to reason about this persona's day.",
    "input_parameters": {
      "fitness_hours_week": 3.0,
      "social_hours_week": 7.0,
      "work_hours_week": 6.0,
      "carework_hours_week": 3.0,
      "workplace_distance_km": 3.0,
      "indoor_activity_distance_km": 1.2,
      "outdoor_activity_distance_km": 0.6,
      "day_index": 3
    },
    "selected_schedule_parameters": {
      "name": "ExamplePersona_03",
      "schedule_rigidity": 0.52,
      "phase_variability": 0.48,
      "university_load": 0.55,
      "employment_load": 0.25,
      "study_intensity": 0.56,
      "sport_frequency": 0.45,
      "sport_fixedness": 0.42,
      "evening_flexibility": 0.5,
      "day_fragmentation": 0.48,
      "random_event_rate": 0.1,
      "commute_load": 0.25,
      "location_switch_frequency": 0.42,
      "weekend_structure": 0.5,
      "weekend_social_intensity": 0.5,
      "social_hours_week": 7.0,
      "carework_hours_week": 3.0
    },
    "hourly_context_24h": [
      {
        "hour": 0,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.5,
        "energy_category": "medium",
        "temperature_c": 4,
        "feels_like_c": 3.4,
        "humidity_pct": 64.0,
        "wind_m_s": 1.2,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 1,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.515,
        "energy_category": "medium",
        "temperature_c": 3.6,
        "feels_like_c": 2.4,
        "humidity_pct": 66.071,
        "wind_m_s": 1.76,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 2,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.53,
        "energy_category": "medium",
        "temperature_c": 3.2,
        "feels_like_c": 2.6,
        "humidity_pct": 68.0,
        "wind_m_s": 1.44,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 3,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.5,
        "energy_category": "medium",
        "temperature_c": 3,
        "feels_like_c": 1.8,
        "humidity_pct": 69.657,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 4,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.515,
        "energy_category": "medium",
        "temperature_c": 2.8,
        "feels_like_c": 1.6,
        "humidity_pct": 70.928,
        "wind_m_s": 1.68,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 5,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.53,
        "energy_category": "medium",
        "temperature_c": 3.1,
        "feels_like_c": 2.5,
        "humidity_pct": 71.727,
        "wind_m_s": 1.36,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 6,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.5,
        "energy_category": "medium",
        "temperature_c": 4,
        "feels_like_c": 2.8,
        "humidity_pct": 72.0,
        "wind_m_s": 1.92,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 7,
        "activity_type": "wake_up",
        "subtype": "morning_wake_up",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.55,
        "energy_category": "medium",
        "temperature_c": 5.5,
        "feels_like_c": 4.3,
        "humidity_pct": 71.727,
        "wind_m_s": 1.6,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.259,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 8,
        "activity_type": "eat",
        "subtype": "breakfast",
        "current_location": "home",
        "active_constraints": [
          "meal"
        ],
        "energy_level": 0.56,
        "energy_category": "medium",
        "temperature_c": 7,
        "feels_like_c": 6.4,
        "humidity_pct": 70.928,
        "wind_m_s": 1.28,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.5,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 9,
        "activity_type": "work",
        "subtype": "university",
        "current_location": "workplace",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.6,
        "energy_category": "medium",
        "temperature_c": 8.8,
        "feels_like_c": 7.6,
        "humidity_pct": 69.657,
        "wind_m_s": 1.84,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.707,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.0,
            "travel_times_min": {
              "walk": 25.0,
              "bike": 8.0,
              "car": 4.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.75,
              "bike": 6.0,
              "car": 3.0
            }
          }
        }
      },
      {
        "hour": 10,
        "activity_type": "work",
        "subtype": "university",
        "current_location": "workplace",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.6,
        "energy_category": "medium",
        "temperature_c": 10,
        "feels_like_c": 8.0,
        "humidity_pct": 86.0,
        "wind_m_s": 1.52,
        "precipitation_mm": 0.2,
        "is_wet": true,
        "sun_frac": 0.866,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.0,
            "travel_times_min": {
              "walk": 25.0,
              "bike": 8.0,
              "car": 4.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.75,
              "bike": 6.0,
              "car": 3.0
            }
          }
        }
      },
      {
        "hour": 11,
        "activity_type": "work",
        "subtype": "university",
        "current_location": "workplace",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.6,
        "energy_category": "medium",
        "temperature_c": 11.2,
        "feels_like_c": 9.8,
        "humidity_pct": 84.071,
        "wind_m_s": 1.2,
        "precipitation_mm": 0.2,
        "is_wet": true,
        "sun_frac": 0.966,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.0,
            "travel_times_min": {
              "walk": 25.0,
              "bike": 8.0,
              "car": 4.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.75,
              "bike": 6.0,
              "car": 3.0
            }
          }
        }
      },
      {
        "hour": 12,
        "activity_type": "eat",
        "subtype": "lunch",
        "current_location": "workplace",
        "active_constraints": [
          "meal"
        ],
        "energy_level": 0.58,
        "energy_category": "medium",
        "temperature_c": 12,
        "feels_like_c": 10.8,
        "humidity_pct": 64.0,
        "wind_m_s": 1.76,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 1.0,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.0,
            "travel_times_min": {
              "walk": 25.0,
              "bike": 8.0,
              "car": 4.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.75,
              "bike": 6.0,
              "car": 3.0
            }
          }
        }
      },
      {
        "hour": 13,
        "activity_type": "work",
        "subtype": "self_study",
        "current_location": "workplace",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.55,
        "energy_category": "medium",
        "temperature_c": 12.5,
        "feels_like_c": 11.9,
        "humidity_pct": 61.929,
        "wind_m_s": 1.44,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.966,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.0,
            "travel_times_min": {
              "walk": 25.0,
              "bike": 8.0,
              "car": 4.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.75,
              "bike": 6.0,
              "car": 3.0
            }
          }
        }
      },
      {
        "hour": 14,
        "activity_type": "work",
        "subtype": "self_study",
        "current_location": "workplace",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.55,
        "energy_category": "medium",
        "temperature_c": 12.8,
        "feels_like_c": 11.6,
        "humidity_pct": 60.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.866,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.0,
            "travel_times_min": {
              "walk": 25.0,
              "bike": 8.0,
              "car": 4.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.75,
              "bike": 6.0,
              "car": 3.0
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
        "energy_level": 0.62,
        "energy_category": "medium",
        "temperature_c": 12.3,
        "feels_like_c": 11.1,
        "humidity_pct": 58.343,
        "wind_m_s": 1.68,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.707,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
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
        "energy_level": 0.64,
        "energy_category": "medium",
        "temperature_c": 11.5,
        "feels_like_c": 10.9,
        "humidity_pct": 57.072,
        "wind_m_s": 1.36,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.5,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
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
        "energy_level": 0.6,
        "energy_category": "medium",
        "temperature_c": 10.4,
        "feels_like_c": 9.2,
        "humidity_pct": 56.273,
        "wind_m_s": 1.92,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.259,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 18,
        "activity_type": "eat",
        "subtype": "dinner",
        "current_location": "home",
        "active_constraints": [
          "meal"
        ],
        "energy_level": 0.56,
        "energy_category": "medium",
        "temperature_c": 9.2,
        "feels_like_c": 8.0,
        "humidity_pct": 56.0,
        "wind_m_s": 1.6,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 19,
        "activity_type": "downtime",
        "subtype": "open_time",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.54,
        "energy_category": "medium",
        "temperature_c": 8.1,
        "feels_like_c": 7.5,
        "humidity_pct": 56.273,
        "wind_m_s": 1.28,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
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
        "energy_level": 0.5,
        "energy_category": "medium",
        "temperature_c": 7.4,
        "feels_like_c": 6.2,
        "humidity_pct": 57.072,
        "wind_m_s": 1.84,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 21,
        "activity_type": "downtime",
        "subtype": "evening_wind_down",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.46,
        "energy_category": "medium",
        "temperature_c": 6.7,
        "feels_like_c": 5.5,
        "humidity_pct": 58.343,
        "wind_m_s": 1.52,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 22,
        "activity_type": "downtime",
        "subtype": "evening_wind_down",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.44,
        "energy_category": "low",
        "temperature_c": 6,
        "feels_like_c": 5.4,
        "humidity_pct": 60.0,
        "wind_m_s": 1.2,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 23,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.53,
        "energy_category": "medium",
        "temperature_c": 5.2,
        "feels_like_c": 4.0,
        "humidity_pct": 61.929,
        "wind_m_s": 1.76,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
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
  "decision_code": 3,
  "decision_label": "adapted",
  "rationale_short": "Die Behavior Policy zeigt eine durchschnittliche, aber ausreichende Tendenz zur Aktivität, und der Tageskontext erlaubt eine angepasste Umsetzung zu einem späteren Zeitpunkt am Tag.",
  "diary_entry": "Ich war heute nicht besonders motiviert und hatte morgens keine Zeit, die Aktivität wie geplant zu machen. Am Nachmittag hatte ich dann doch ein freies Zeitfenster und wollte sie diesmal nicht ganz ausfallen lassen. Als ich einmal angefangen hatte, war es weniger mühsam als gedacht, und am Ende war ich froh, es gemacht zu haben."
}
```

### Beispiel 4: Durchschnittliche Behavior Policy und durchschnittlicher Tageskontext ohne Umsetzung

Input:

```json
{
  "persona_id": "ExamplePersona_04",
  "day_index": 4,
  "behavior_policy": {
    "do_planned_activity": 0.32,
    "adapt_activity": 0.24,
    "postpone_activity": 0.18,
    "skip_activity": 0.15,
    "extra_activity": 0.07,
    "app_ignored": 0.04
  },
  "planned_activity": {
    "activity_type": "indoor_activity",
    "duration_min": 30,
    "intensity": "moderate",
    "preferred_time_window": [
      15,
      20
    ]
  },
  "daily_context": {
    "seed": 410404104,
    "day_index": 4,
    "phase": "normal",
    "weekday": 3,
    "task_description": "Use the compact 24-hour schedule, energy, quantitative weather, daylight, constraints, location, and POI-accessibility context to reason about this persona's day.",
    "input_parameters": {
      "fitness_hours_week": 3.0,
      "social_hours_week": 7.0,
      "work_hours_week": 6.0,
      "carework_hours_week": 3.0,
      "workplace_distance_km": 3.0,
      "indoor_activity_distance_km": 1.2,
      "outdoor_activity_distance_km": 0.6,
      "day_index": 4
    },
    "selected_schedule_parameters": {
      "name": "ExamplePersona_04",
      "schedule_rigidity": 0.5,
      "phase_variability": 0.5,
      "university_load": 0.55,
      "employment_load": 0.25,
      "study_intensity": 0.55,
      "sport_frequency": 0.42,
      "sport_fixedness": 0.38,
      "evening_flexibility": 0.48,
      "day_fragmentation": 0.5,
      "random_event_rate": 0.1,
      "commute_load": 0.25,
      "location_switch_frequency": 0.4,
      "weekend_structure": 0.5,
      "weekend_social_intensity": 0.5,
      "social_hours_week": 7.0,
      "carework_hours_week": 3.0
    },
    "hourly_context_24h": [
      {
        "hour": 0,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.5,
        "energy_category": "medium",
        "temperature_c": 5,
        "feels_like_c": 4.4,
        "humidity_pct": 64.0,
        "wind_m_s": 1.2,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 1,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.5,
        "energy_category": "medium",
        "temperature_c": 4.7,
        "feels_like_c": 3.5,
        "humidity_pct": 66.071,
        "wind_m_s": 1.76,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 2,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.5,
        "energy_category": "medium",
        "temperature_c": 4.5,
        "feels_like_c": 3.9,
        "humidity_pct": 68.0,
        "wind_m_s": 1.44,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 3,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.5,
        "energy_category": "medium",
        "temperature_c": 4.2,
        "feels_like_c": 3.0,
        "humidity_pct": 69.657,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 4,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.5,
        "energy_category": "medium",
        "temperature_c": 4,
        "feels_like_c": 2.8,
        "humidity_pct": 70.928,
        "wind_m_s": 1.68,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 5,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.5,
        "energy_category": "medium",
        "temperature_c": 4.3,
        "feels_like_c": 3.7,
        "humidity_pct": 71.727,
        "wind_m_s": 1.36,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 6,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.5,
        "energy_category": "medium",
        "temperature_c": 5,
        "feels_like_c": 3.8,
        "humidity_pct": 72.0,
        "wind_m_s": 1.92,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 7,
        "activity_type": "wake_up",
        "subtype": "morning_wake_up",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.54,
        "energy_category": "medium",
        "temperature_c": 6.1,
        "feels_like_c": 4.9,
        "humidity_pct": 71.727,
        "wind_m_s": 1.6,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.259,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 8,
        "activity_type": "eat",
        "subtype": "breakfast",
        "current_location": "home",
        "active_constraints": [
          "meal"
        ],
        "energy_level": 0.55,
        "energy_category": "medium",
        "temperature_c": 7.5,
        "feels_like_c": 6.9,
        "humidity_pct": 70.928,
        "wind_m_s": 1.28,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.5,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 9,
        "activity_type": "work",
        "subtype": "university",
        "current_location": "workplace",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.59,
        "energy_category": "medium",
        "temperature_c": 8.8,
        "feels_like_c": 7.6,
        "humidity_pct": 69.657,
        "wind_m_s": 1.84,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.707,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.0,
            "travel_times_min": {
              "walk": 25.0,
              "bike": 8.0,
              "car": 4.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.75,
              "bike": 6.0,
              "car": 3.0
            }
          }
        }
      },
      {
        "hour": 10,
        "activity_type": "work",
        "subtype": "university",
        "current_location": "workplace",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.59,
        "energy_category": "medium",
        "temperature_c": 10.1,
        "feels_like_c": 8.9,
        "humidity_pct": 68.0,
        "wind_m_s": 1.52,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.866,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.0,
            "travel_times_min": {
              "walk": 25.0,
              "bike": 8.0,
              "car": 4.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.75,
              "bike": 6.0,
              "car": 3.0
            }
          }
        }
      },
      {
        "hour": 11,
        "activity_type": "work",
        "subtype": "university",
        "current_location": "workplace",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.59,
        "energy_category": "medium",
        "temperature_c": 11,
        "feels_like_c": 10.4,
        "humidity_pct": 66.071,
        "wind_m_s": 1.2,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.966,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.0,
            "travel_times_min": {
              "walk": 25.0,
              "bike": 8.0,
              "car": 4.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.75,
              "bike": 6.0,
              "car": 3.0
            }
          }
        }
      },
      {
        "hour": 12,
        "activity_type": "eat",
        "subtype": "lunch",
        "current_location": "workplace",
        "active_constraints": [
          "meal"
        ],
        "energy_level": 0.57,
        "energy_category": "medium",
        "temperature_c": 11.7,
        "feels_like_c": 10.5,
        "humidity_pct": 64.0,
        "wind_m_s": 1.76,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 1.0,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.0,
            "travel_times_min": {
              "walk": 25.0,
              "bike": 8.0,
              "car": 4.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.75,
              "bike": 6.0,
              "car": 3.0
            }
          }
        }
      },
      {
        "hour": 13,
        "activity_type": "work",
        "subtype": "self_study",
        "current_location": "workplace",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.55,
        "energy_category": "medium",
        "temperature_c": 12.1,
        "feels_like_c": 11.5,
        "humidity_pct": 61.929,
        "wind_m_s": 1.44,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.966,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.0,
            "travel_times_min": {
              "walk": 25.0,
              "bike": 8.0,
              "car": 4.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.75,
              "bike": 6.0,
              "car": 3.0
            }
          }
        }
      },
      {
        "hour": 14,
        "activity_type": "work",
        "subtype": "self_study",
        "current_location": "workplace",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.55,
        "energy_category": "medium",
        "temperature_c": 12,
        "feels_like_c": 10.8,
        "humidity_pct": 60.0,
        "wind_m_s": 2.0,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.866,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 2.0,
            "travel_times_min": {
              "walk": 25.0,
              "bike": 8.0,
              "car": 4.0
            }
          },
          "outdoor_activity": {
            "distance_km": 1.5,
            "travel_times_min": {
              "walk": 18.75,
              "bike": 6.0,
              "car": 3.0
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
        "energy_level": 0.58,
        "energy_category": "medium",
        "temperature_c": 11.7,
        "feels_like_c": 10.5,
        "humidity_pct": 58.343,
        "wind_m_s": 1.68,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.707,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
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
        "energy_level": 0.57,
        "energy_category": "medium",
        "temperature_c": 11.2,
        "feels_like_c": 10.6,
        "humidity_pct": 57.072,
        "wind_m_s": 1.36,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.5,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
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
        "energy_level": 0.54,
        "energy_category": "medium",
        "temperature_c": 10.3,
        "feels_like_c": 9.1,
        "humidity_pct": 56.273,
        "wind_m_s": 1.92,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.259,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 18,
        "activity_type": "eat",
        "subtype": "dinner",
        "current_location": "home",
        "active_constraints": [
          "meal"
        ],
        "energy_level": 0.51,
        "energy_category": "medium",
        "temperature_c": 9.1,
        "feels_like_c": 7.9,
        "humidity_pct": 56.0,
        "wind_m_s": 1.6,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": true,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 19,
        "activity_type": "downtime",
        "subtype": "open_time",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.49,
        "energy_category": "medium",
        "temperature_c": 8.2,
        "feels_like_c": 7.6,
        "humidity_pct": 56.273,
        "wind_m_s": 1.28,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
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
        "energy_level": 0.46,
        "energy_category": "medium",
        "temperature_c": 7.5,
        "feels_like_c": 6.3,
        "humidity_pct": 57.072,
        "wind_m_s": 1.84,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 21,
        "activity_type": "downtime",
        "subtype": "evening_wind_down",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.43,
        "energy_category": "low",
        "temperature_c": 6.8,
        "feels_like_c": 5.6,
        "humidity_pct": 58.343,
        "wind_m_s": 1.52,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 22,
        "activity_type": "downtime",
        "subtype": "evening_wind_down",
        "current_location": "home",
        "active_constraints": [],
        "energy_level": 0.4,
        "energy_category": "low",
        "temperature_c": 6.2,
        "feels_like_c": 5.6,
        "humidity_pct": 60.0,
        "wind_m_s": 1.2,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
            }
          }
        }
      },
      {
        "hour": 23,
        "activity_type": "sleep",
        "subtype": "night_sleep",
        "current_location": "home",
        "active_constraints": [
          "fixed_block"
        ],
        "energy_level": 0.5,
        "energy_category": "medium",
        "temperature_c": 5.6,
        "feels_like_c": 4.4,
        "humidity_pct": 61.929,
        "wind_m_s": 1.76,
        "precipitation_mm": 0.0,
        "is_wet": false,
        "sun_frac": 0.0,
        "is_daylight": false,
        "snow_cover": false,
        "poi_accessibility": {
          "indoor_activity": {
            "distance_km": 1.2,
            "travel_times_min": {
              "walk": 15.0,
              "bike": 4.8,
              "car": 2.4
            }
          },
          "outdoor_activity": {
            "distance_km": 0.6,
            "travel_times_min": {
              "walk": 7.5,
              "bike": 2.4,
              "car": 1.2
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
  "decision_label": "not_done",
  "rationale_short": "Die Behavior Policy zeigt eine durchschnittliche, aber nicht starke Tendenz zur Aktivität, und der Tageskontext bietet zwar keine klaren Barrieren, aber auch keinen besonders unterstützenden Anlass zur Umsetzung.",
  "diary_entry": "Ich habe kurz überlegt, ob ich mich noch bewegen soll, aber irgendwie hat der letzte Anstoss gefehlt. Es war kein besonders schlechter Tag, aber mir war es wohl einfach nicht wichtig genug. Ich habe die Aktivität immer weiter vor mir hergeschoben, und am Ende war es zu spät und ich hatte keine Lust und Energie mehr."
}
```
