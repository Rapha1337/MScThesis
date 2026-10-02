# Empirical T1 medoid PA correspondence analysis v1.2

## Design

One continuous 90-day simulation starts 2026-07-09. The 7-, 30-, and 90-day analyses are nested prefixes.

Base seed 14 was selected without examining any PA outcome or correlation. The first seven dates must remain in each persona's modal annual phase and contain no acute schedule-altering event.

Observed medoid T1 MVPA and total PA are validation-only in v1.2. They are retained for the final comparison but are not passed into schedule generation, LLM1, or LLM2. Therefore there is no input-informed scheduler PA baseline.

## Action-planning calibration

Held-out T1 OLS calibration excluding the four simulated medoid personas: MVPA_hours_week ~ action_planning_normalized. Standardized beta is used as a small relative weighting coefficient only.

Held-out calibration: n=148, standardized beta=0.107, B=1.977 h/week per 0-1 AP unit, p=0.194, R2=0.012. Action-planning mean=0.390, SD=0.274.

The standardized beta is used only as a small monotonic weighting of unplanned PA propensity. It is not interpreted as a probability, a percentage-point effect, or a causal coefficient. Individual action planning is neutralized before LLM1 and reintroduced once through this calibration to avoid double counting.

## Primary outcome

LLM2 reports only duration for each performed activity. The simulation does not introduce an additional light/moderate/vigorous classification. All actually performed PA minutes are normalized to hours/week and compared descriptively with the T1 MVPA and total-PA reference values.

| horizon | Spearman T1 MVPA vs simulated PA duration | Pearson T1 MVPA vs simulated PA duration |
|---:|---:|---:|
| 7 | 0.800 | 0.843 |
| 30 | 0.400 | 0.732 |
| 90 | 1.000 | 0.951 |

All correlations are descriptive/exploratory with n=4 and should not be treated as inferential validation evidence.

## Persona-level correspondence

| horizon_days | cluster | participant_id | empirical_mvpa_hours_week | empirical_total_pa_hours_week | simulated_pa_hours_week | error_vs_empirical_mvpa_hours_week | active_days_per_week | mean_duration_min_active_day | normal_days | high_stress_days | holiday_days |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 7.000 | 1.000 | 7067 | 2.000 | 4.667 | 3.333 | 1.333 | 5.000 | 40.000 | 7.000 | 0.000 | 0.000 |
| 7.000 | 2.000 | 8361 | 1.333 | 3.667 | 3.750 | 2.417 | 5.000 | 45.000 | 7.000 | 0.000 | 0.000 |
| 7.000 | 3.000 | 8237 | 2.250 | 8.250 | 4.083 | 1.833 | 7.000 | 35.000 | 7.000 | 0.000 | 0.000 |
| 7.000 | 4.000 | 8303 | 0.333 | 1.000 | 2.450 | 2.117 | 4.000 | 36.750 | 0.000 | 7.000 | 0.000 |
| 30.000 | 1.000 | 7067 | 2.000 | 4.667 | 3.481 | 1.481 | 5.133 | 40.682 | 25.000 | 0.000 | 5.000 |
| 30.000 | 2.000 | 8361 | 1.333 | 3.667 | 4.511 | 3.178 | 6.300 | 42.963 | 25.000 | 0.000 | 5.000 |
| 30.000 | 3.000 | 8237 | 2.250 | 8.250 | 4.064 | 1.814 | 6.067 | 40.192 | 23.000 | 0.000 | 7.000 |
| 30.000 | 4.000 | 8303 | 0.333 | 1.000 | 1.777 | 1.444 | 3.267 | 32.643 | 0.000 | 30.000 | 0.000 |
| 90.000 | 1.000 | 7067 | 2.000 | 4.667 | 3.416 | 1.416 | 5.211 | 39.328 | 76.000 | 0.000 | 14.000 |
| 90.000 | 2.000 | 8361 | 1.333 | 3.667 | 3.338 | 2.005 | 5.133 | 39.015 | 39.000 | 44.000 | 7.000 |
| 90.000 | 3.000 | 8237 | 2.250 | 8.250 | 3.893 | 1.643 | 5.756 | 40.581 | 76.000 | 0.000 | 14.000 |
| 90.000 | 4.000 | 8303 | 0.333 | 1.000 | 1.467 | 1.134 | 2.722 | 32.343 | 0.000 | 90.000 | 0.000 |

## Limitations

The four medoids are a deliberately small descriptive sample. T1 MVPA is self-reported baseline behavior, whereas the simulation evolves over time. LLM-generated duration is a structured simulation output, not an objective activity measurement. No additional intensity classification is imposed. The action-planning calibration is a model mapping choice informed by the T1 association rather than a directly estimated daily transition probability. The cross-sectional T1 coefficient is applied to evolving simulated action-planning states, which is an explicit longitudinal model assumption.
