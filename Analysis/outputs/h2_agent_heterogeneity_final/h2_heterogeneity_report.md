# H2 Agent Heterogeneity Report



> H2: The proposed agent-based simulation model can represent heterogeneous agents who differ in their individual characteristics, daily and weekly routines, and levels of psychological constructs.



This analysis evaluates H2 descriptively; no inferential tests, p-values, or pass/fail thresholds are used.

Base seeds: [3263, 3264, 3265, 3266, 3267, 3268, 3269, 3270, 3271, 3272]; agents per seed: 10; total agent realizations: 100; phase: normal; common high-level inputs: `{'fitness_hours_week': 5.5, 'social_hours_week': 10.0, 'work_hours_week': 4.5, 'carework_hours_week': None, 'workplace_distance_km': 3.0, 'indoor_activity_distance_km': 1.2, 'outdoor_activity_distance_km': 0.6}`.

Persona seeds come from `StudentWrapper.create_personas`; psychological seeds use `persona_seed + 10_000_019`; schedules use generated weekly structures and `generate_full_day_schedule` with `persona_seed + weekday` daily RNGs.

Schedules are 168 hourly top-level activity-type labels. Similarity is matching slots / 168 and difference is 1 - similarity. Population SD is reported.

Total within-run pairwise comparisons: 450

## Main schedule heterogeneity table

|scope|n_pairs|mean_similarity_percent|sd_similarity_percent|min_similarity_percent|max_similarity_percent|mean_difference_percent|sd_difference_percent|min_difference_percent|max_difference_percent|sd_type|
|---|---|---|---|---|---|---|---|---|---|---|
|all_within_run_pairs|450|86.79232804232804|3.2584348511572716|79.16666666666666|94.64285714285714|13.207671957671957|3.258434851157271|5.35714285714286|20.833333333333336|population|

## Main construct heterogeneity table

|construct|n|mean|population_sd|minimum|percentile_25|median|percentile_75|maximum|range|iqr|n_exactly_0|percent_exactly_0|n_exactly_1|percent_exactly_1|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|automaticity|100|0.37386|0.22827663130509002|0.0|0.19275|0.379|0.512|1.0|1.0|0.31925000000000003|5|5.0|1|1.0|
|pa_specific_self_control|100|0.52914|0.1967063303506016|0.183|0.37275|0.512|0.638|1.0|0.817|0.26525|0|0.0|1|1.0|
|action_planning|100|0.36808|0.28020851807181024|0.0|0.14225|0.29|0.553|1.0|1.0|0.41075000000000006|9|9.0|2|2.0|
|intention|100|0.62042|0.19635285483027742|0.021|0.5105|0.635|0.748|1.0|0.979|0.23750000000000004|0|0.0|2|2.0|
|perceived_behavioral_control|100|0.64478|0.17624974212747094|0.081|0.52675|0.6435|0.773|1.0|0.919|0.24624999999999997|0|0.0|1|1.0|
|attitude_toward_the_behavior|100|0.69687|0.19491278331602574|0.206|0.5732499999999999|0.719|0.8402499999999999|1.0|0.794|0.267|0|0.0|7|7.0|
|subjective_norm|100|0.50722|0.18249452484937734|0.0|0.394|0.505|0.6355|0.932|0.932|0.24149999999999994|1|1.0|0|0.0|
|intrinsic_motivation|100|0.71321|0.08270275630231437|0.492|0.667|0.719|0.76875|0.86|0.368|0.10175000000000001|0|0.0|0|0.0|
|motivational_competence|100|0.8248|0.11767276660298252|0.474|0.7475|0.8274999999999999|0.91725|1.0|0.526|0.16974999999999996|0|0.0|10|10.0|

## Figures

- [Schedule heatmap](figures/schedule_heatmap.png)

- [Schedule similarity distribution](figures/schedule_similarity_distribution.png)

- [Schedule run means](figures/schedule_run_means.png)

- [Construct heatmap](figures/construct_heatmap.png)

- [Construct boxplots](figures/construct_boxplots.png)

## Reproducibility results

|check|result|
|---|---|
|same_seed_persona_seeds_identical|True|
|same_seed_schedules_identical|True|
|same_seed_psychological_seeds_identical|True|
|same_seed_psychological_values_identical|True|
|different_base_seed_persona_seeds_differ|True|
|different_base_seed_schedules_differ|True|
|different_base_seed_psychological_values_differ|True|

Only nine active constructs are analysed: automaticity, pa_specific_self_control, action_planning, intention, perceived_behavioral_control, attitude_toward_the_behavior, subjective_norm, intrinsic_motivation, motivational_competence. The legacy intrinsic-motivation subscales (`interest_enjoyment`, `perceived_competence`, `perceived_choice`, `pressure_tension`) are not separate model outputs.

## Limitations

- simulated rather than empirical agents;

- common high-level input parameters;

- one controlled normal-phase week per agent;

- descriptive evidence does not establish real-world population validity;

- schedule similarity is based on top-level activity type and not subtype;

- psychological values are sampled from embedded reference parameters.

## Neutral conclusion

The descriptive outputs do not automatically accept or reject H2.