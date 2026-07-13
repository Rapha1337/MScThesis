# A Theory-Informed Agent-Based Model of Context-Dependent Physical Activity Decisions

This repository contains the agent-based simulation framework developed as part of a master's thesis at the Institute of Sport Science, University of Bern.

The model provides a modular virtual environment for representing heterogeneous synthetic agents, daily contextual conditions, and context-dependent physical activity decisions. It was developed as a methodological foundation for the future virtual pretesting of mobile health interventions.

## Project Overview

The model combines:

- heterogeneous synthetic agents
- annual and weekly activity schedules
- hourly environmental conditions
- spatial accessibility
- energy levels
- psychological constructs
- large-language-model-supported physical activity decisions
- longitudinal psychological state updates

The model is intended as a proof of concept. It does not predict the behavior of real individuals and has not yet been empirically calibrated or externally validated.

## Simulation Architecture

The daily physical activity decision pipeline consists of three consecutive stages:

1. **Behavior probability estimation**  
   The first large-language-model-supported component estimates behavioral tendency probabilities from the agent's current psychological state.

2. **Context-dependent physical activity decision**  
   The second component combines the behavioral tendencies with the generated daily context and planned physical activity. It produces one final daily decision, a short rationale, and a diary entry.

3. **Psychological state assessment**  
   The third component assesses evidence contained in the diary entry and updates the agent's psychological constructs within a closed feedback loop.

The possible daily decision categories are:

- `do_planned_activity`
- `adapt_activity`
- `skip_activity`
- `extra_activity`

## Research Questions

The accompanying thesis examined whether the model could:

1. represent relevant environmental conditions;
2. generate heterogeneous agents despite identical high-level persona inputs;
3. produce decisions consistent with supportive contextual conditions; and
4. produce decisions consistent with hindering contextual conditions.

## Repository Structure

```text
MScThesis/
├── Analysis/                    Final analysis and validation scripts
├── Simulation/                  Agent-based simulation framework
│   ├── constraints/             Contextual constraint components
│   ├── tests/                   Simulation tests
│   ├── BehaviorProbability_Prompt.md
│   ├── PADecision_Prompt.md
│   ├── AssessmentModel_Prompt.md
│   └── run_full_pa_simulation.py
├── CITATION.cff                 Software citation metadata
├── LICENSE                      GNU General Public License v3.0
└── README.md
```

Generated simulation and analysis outputs are not version-controlled.

## Software Requirements

The project was developed and analyzed using Python 3.11.

A valid API key for the OpenAI-compatible language model endpoint used by the University of Bern is required for full simulations involving the large-language-model-supported components.

The key must be provided through the following environment variable:

```text
UNI_LLM_API_KEY
```

API keys and other credentials must not be committed to the repository.

## Running the Full Simulation

From the repository root:

```powershell
python Simulation/run_full_pa_simulation.py `
  --n-personas 1 `
  --n-days 365 `
  --start-date 2026-01-01 `
  --base-seed 137 `
  --output-dir Simulation/output/example_run
```

The main configurable parameters include:

- number of personas
- number of simulated days
- start date
- base seed
- weekly physical activity hours
- weekly work, social, and care-work hours
- distances to relevant points of interest
- language model and generation parameters
- output directory
- checkpoint and resume behavior

A simulation can be resumed from an existing checkpoint by adding:

```powershell
--resume
```

A dry run without external language-model calls can be performed using:

```powershell
--dry-run
```

## Running the Analyses

### Environmental Validation

```powershell
python Analysis/h1_weather_validation.py
```

### Agent Heterogeneity

```powershell
python Analysis/h2_agent_heterogeneity.py
```

### Final H1-H4 Analysis

```powershell
python Analysis/final_h1_h4_analysis.py `
  --h1-dir Analysis/outputs/h1_weather_final `
  --h2-dir Analysis/outputs/h2_agent_heterogeneity_final `
  --supportive Simulation/output/365x1_SupportiveScenario `
  --hindering Simulation/output/365x1_HinderingScenario `
  --output-dir Analysis/outputs/final_h1_h4 `
  --overwrite
```

The final analysis script calculates the descriptive and inferential results reported in the thesis.

## Testing

Run the test suite from the repository root:

```powershell
python -m pytest
```

## Reproducibility

Random seeds are used for the generation of agents, schedules, environmental conditions, and initial psychological states. Reusing the same configuration and seeds reproduces the deterministic simulation components.

Outputs involving a large language model may additionally depend on the model endpoint, model version, and inference implementation available at the time of execution.

## Citation

A permanent Zenodo DOI will be added following publication of version 1.0.0.

Citation metadata are provided in `CITATION.cff`.

## License

This project is licensed under the GNU General Public License v3.0. See the `LICENSE` file for details.

## Author

Raphael Reinalter  
Institute of Sport Science  
University of Bern, Switzerland
