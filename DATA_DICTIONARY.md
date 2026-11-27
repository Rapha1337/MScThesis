# Data dictionary

The repository does not contain T1 microdata, empirical medoid profiles, H3 traces, classified H3 days, medoid-by-run records or pooled H3 run records. Synthetic data are not actual participants.

| Path | Row unit and variables | Origin and disclosure limitations |
|---|---|---|
| `data/h1/simulated_daily_weather.csv` | Seed ? model day: model calendar and simulated weather | 30 generated 360-day years; no person records. |
| `data/h1/simulated_monthly_weather.csv` | Seed ? model month, weather aggregates | Derived from generated daily data. |
| `data/h1/h1_annual_summary.csv` | Seed ? model year | Derived from generated weather. |
| `data/h2/run_config.json` | H2 settings, generic persona settings, seeds, nine means and sample SDs | Nine aggregate T1 marginals, N=144; no person-level records. Aggregate precision and cross-release inference remain a privacy consideration. |
| `data/h2/data/initial_psychological_constructs.csv` | Generated agent ID, seed and nine sampled constructs | Synthetic draws with T1 aggregate marginals, assumed correlations and bounded values; not participant profiles. |
| `data/h2/data/agent_year_schedules_long.csv.gz` | Synthetic agent ? model hour, activity, phase and generated event indicators | 200 synthetic years ? 8,736 hours; lossless compression. |
| `data/h2/data/agent_phase_sequence.csv`, `agent_phase_week_counts.csv` | Synthetic agent ? week or phase | Derived from generated schedule. |
| `data/h2/data/pairwise_annual_schedule_similarity.csv` | Synthetic agent pair within one base seed | 1,900 generated schedule comparisons. |
| `data/h2/tables/` and `data/h2/figure_5*` | Synthetic H2 summary tables, bootstrap intervals and figure | Hierarchical bootstrap resamples 10 seeds and then 20 agents/seed, 5,000 draws, fixed random seed; population SD (ddof=0). |
| `Simulation/empirical_pa_v1_2.py` | Aggregate held-out regression calibration, N=148 | Model coefficients, not individual profiles. Existing public version uses exact precision; further linkage assessment may be required. |

H3 category label `hindering` in the later exploratory analysis denotes the frozen classifier's entire `non_supportive` category, including neutral context. Controlled inputs required for H3 regeneration and independent validation are not released. No claim of formal anonymity follows solely from aggregation or simulation.
