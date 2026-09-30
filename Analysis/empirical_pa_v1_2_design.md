# Empirical PA model v1.2

## Motivation

The first empirical-medoid run showed that observed T1 MVPA was being mapped
directly to weekly physical-activity blocks in the schedule. This produced a
strong pre-decision correspondence between observed MVPA and scheduled PA and
made planned activity very easy for LLM2 to confirm. The resulting comparison
was therefore input-informed rather than an independent behavioral
correspondence check.

Version 1.2 removes that pathway.

## Data separation

For the four medoid personas, observed T1 MVPA is retained only as a validation
target. It is stored in profile metadata but is set to zero for schedule
generation. The ordinary schedule contains work/study, social time, care work,
downtime, sleep, weather, energy, location, accessibility, and other contextual
constraints, but no pre-generated physical-activity block.

The runtime contains an assertion that fails if a PA block appears in an
empirical-v1.2 schedule.

## Action planning calibration

Kai suggested empirically weighting the effect of action planning using the T1
survey. A simple linear regression of T1 MVPA hours/week on normalized action
planning was calculated.

Full T1 sample:

- n = 147
- standardized beta = 0.1648
- B = 2.6449 h/week per 0-1 action-planning unit
- p = 0.0461
- R2 = 0.0272

To avoid using the four validation medoids' own MVPA values when calibrating
their simulation, the final v1.2 coefficient is estimated after excluding
participants 7067, 8153, 8237, and 8303:

- n = 143
- standardized beta = 0.1616428
- B = 2.6175879 h/week per 0-1 action-planning unit
- intercept = 1.8487240 h/week
- action-planning mean = 0.3919580
- action-planning SD = 0.2751856
- p = 0.0537675
- R2 = 0.0261284

The held-out coefficient is almost unchanged from the full-sample estimate, but
the conventional p value moves just above .05. This is reported transparently.

The standardized beta is not interpreted as a probability, percentage-point
effect, or causal effect. In v1.2 it is used as a small monotonic calibration of
the PA/no-PA propensity:

modifier = beta * z(action planning)

The extra-activity odds from the no-plan LLM1 policy are multiplied by
exp(modifier) and then renormalized against the no-activity tendency. This
mapping preserves the direction and small magnitude of the empirical
association while keeping probabilities in [0, 1]. The exponential odds mapping
is a simulation design choice rather than a transformation directly estimated
by the linear regression.

## Avoiding double counting

Individual action planning is not allowed to affect behavior twice.

Before LLM1, the person's action-planning value is replaced by the held-out T1
mean. The v1.2 LLM1 prompt also explicitly treats action planning as neutral.
The person's actual current action-planning value is then reintroduced once,
after LLM1, through the empirical calibration above.

All other psychological constructs continue to inform the psychological
PA/no-PA propensity.

The calibration is applied to the **current simulated** action-planning value on
each day, because psychological constructs can evolve during the longitudinal
simulation. The regression itself is cross-sectional T1 evidence, so carrying
that coefficient forward to evolving within-person states is an explicit model
assumption rather than a longitudinally estimated effect.

## LLM2 decision

In v1.2 there is no pre-existing sport appointment to follow. LLM2 receives the
calibrated psychological tendency plus the actual day context and chooses
between:

- skip_activity: no PA today
- extra_activity: PA occurs today

The historical extra_activity label is retained for code compatibility; in v1.2
it simply means that PA is performed today.

When PA occurs, LLM2 must additionally report:

- duration_min
- intensity: light, moderate, or vigorous

When no PA occurs, duration is 0 and intensity is none.

## Validation outcome

The primary simulated outcome is now directly comparable with T1 MVPA:

simulated MVPA h/week =
sum(moderate minutes + vigorous minutes) / 60 / simulated days * 7

Light activity is retained as simulated total PA but does not count as MVPA.

The 7-, 30-, and 90-day outcomes remain nested prefixes of one continuous
90-day trajectory. Correlations across the four medoids are descriptive only.

## Seed

The original seed-selection criterion is retained: all four personas must begin
with seven days in their modal annual phase and without acute schedule-altering
events. Seed 14 remains valid. Selection does not inspect PA outcomes or
correlations.

## Run command

From the repository root:

    python Analysis/t1_medoid_pa_validation_v1_2.py \
      --base-seed 14 \
      --persona-input-file Analysis/results_t1_persona_clustering/11_primary_medoid_personas.csv \
      --output-dir Analysis/results_t1_medoid_pa_validation_v1_2

For a no-LLM wiring test, add --dry-run.
