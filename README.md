# A Theory-Informed Agent-Based Model of Context-Dependent Physical Activity Decisions

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21341956.svg)](https://doi.org/10.5281/zenodo.21341956)

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

The model is intended as a proof of concept. Version 1.1 can initialize representative personas from observed AIcoPA T1 profiles. This empirical parameterization does not constitute external validation and the model does not predict the behavior of real individuals.

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
│   ├── GUI_pa_simulation.py
│   └── run_full_pa_simulation.py
├── CITATION.cff                 Software citation metadata
├── LICENSE                      GNU General Public License v3.0
├── requirements.txt             Python dependencies
└── README.md
```

Generated simulation and analysis outputs are not version-controlled.

## Software Requirements

The project was developed and analyzed using Python 3.11.

Install the required Python packages from the repository root:

```powershell
python -m pip install -r requirements.txt
```

A valid API key for the OpenAI-compatible language model endpoint used by the University of Bern is required for full simulations involving the large-language-model-supported components.

The key must be provided through the following environment variable:

```text
UNI_LLM_API_KEY
```

API keys and other credentials must not be committed to the repository.

## Running the Simulation

### Recommended: Graphical User Interface

The simulation can be configured and started through the graphical user interface without manually entering the simulation parameters as terminal arguments.

From the repository root, start the GUI with:

```powershell
python Simulation/GUI_pa_simulation.py
```

The GUI provides fields for the number of personas, number of days, start date, seeds, model parameters, weekly activity inputs, distances, output location, dry-run mode, and resource tracking. It validates the entered values and starts the full simulation using the selected configuration.

### Alternative: Command-Line Interface

For scripted or reproducible runs, the full simulation can also be started directly from the terminal:

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

### Empirical T1 Medoid Personas (Version 1.1)

The primary T1 clustering analysis writes one observed PAM medoid per cluster to:

```text
Analysis/results_t1_persona_clustering/11_primary_medoid_personas.csv
```

Run the four empirical profiles with:

```powershell
python Simulation/run_full_pa_simulation.py `
  --n-personas 4 `
  --n-days 365 `
  --start-date 2026-01-01 `
  --base-seed 137 `
  --persona-input-file Analysis/results_t1_persona_clustering/11_primary_medoid_personas.csv `
  --output-dir Simulation/output/t1_medoids_v1_1
```

The empirical path uses each medoid's observed combination of:

- normalized psychological construct values;
- occupational status and weekly workload;
- MVPA, social, and care-work hours;
- normal, high-stress, and holiday weeks; and
- distances to workplace/study, indoor activity, and outdoor activity.

The reported daily routine variables are retained in persona metadata for traceability but are not currently used to place schedule blocks. Some medoid rows contain daily time reports that are not arithmetically compatible with the reported weekly workload. Primary obligations are therefore distributed from the weekly workload and occupation type. The legacy synthetic student initialization remains the default when `--persona-input-file` is omitted.

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

Version 1.0.0 is archived on Zenodo:

**Reinalter R. A Theory-Informed Agent-Based Model of Context-Dependent Physical Activity Decisions. Version 1.0.0. Zenodo. 2026. doi:10.5281/zenodo.21341956**

https://doi.org/10.5281/zenodo.21341956

Machine-readable citation metadata are provided in `CITATION.cff`.

## License

This project is licensed under the GNU General Public License v3.0. See the `LICENSE` file for details.

## Author

Raphael Reinalter  
Institute of Sport Science  
University of Bern, Switzerland
