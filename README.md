# Theory-informed physical activity simulation ? v1.2.0

This repository contains the final simulation source, prompts, synthetic regression tests and the locally reviewable H1 and H2 analysis data for a master's thesis. The agent-based model combines schedules, weather, accessibility, psychological state and a three-stage LLM decision/update process. The empirical PA v1.2 pathway uses held-out aggregate calibration; model decisions and nonrandomized simulated context associations should not be interpreted as causal effects. The nine H2 T1 marginals are aggregate statistics; the generator's correlation structure is an assumption, not an empirical T1 correlation matrix.

## Layout

- `Simulation/`: simulator, actual prompts and synthetic tests.
- `Analysis/`: weather, H2 and H3 analysis code; `Analysis/h3_plan/` contains the original fixed analysis and validator.
- `data/h1/`: 30 simulated weather years and aggregate tables.
- `data/h2/`: synthetic H2 input records, hourly schedules, summaries and Figure 5.
- `reproducibility/`: offline checks and the restricted-data analysis script.
- `docs/H3_METHODS.md`: estimability, exploratory analyses, interpretation and disclosure limitations.
- `DATA_DICTIONARY.md`: data provenance and definitions.

## Installation

Python 3.11. Create a virtual environment and install `requirements.txt` for the simulator and tests. These broad dependencies are not a lock file. For the offline reproduction checks, `requirements-reproduce.txt` records the tested analysis versions:

```powershell
python -m venv .venv-repro
.venv-repro/Scripts/python -m pip install -r requirements-reproduce.txt
.venv-repro/Scripts/python reproducibility/verify_h1_simulated.py --repo . --output ../h1-reproduced
.venv-repro/Scripts/python reproducibility/reproduce_h2.py --repo . --output ../h2-reproduced
```

Each output directory must be new. These checks use stored generated results and do not generate agents, simulate, or make LLM calls. H1 checks 30 ? 360 generated weather days and their monthly and annual aggregation. H2 reconstructs all 1,900 within-seed comparisons from losslessly compressed schedules, checks phase counts and psychometric summaries, and reproduces Figure 5 with 5,000 seed-then-agent bootstrap replicates and the fixed bootstrap seed. PNG image pixels match the saved figure; image metadata can differ.

## Running the model

`python Simulation/run_full_pa_simulation.py --help` shows all arguments without making a model call. A live run requires authorization, an LLM endpoint and key configured in the local environment, and an independently authorized complete persona input file. For illustration only, substitute your own approved input and output paths:

```powershell
python Simulation/run_full_pa_simulation.py --n-personas 4 --n-days 90 --start-date 2027-01-01 --base-seed 654346558 --model gpt-oss-120b --temperature 0 --empirical-pa-v1-2 --persona-input-file <AUTHORIZED_PRIVATE_CSV> --output-dir <NEW_PRIVATE_OUTPUT_DIRECTORY>
```

The command may invoke a paid LLM service. The empirical input is not distributed. Do not commit person-level input or resulting traces. The H2 generator also accepts an explicit aggregate parameter file; running it is not required to reproduce the saved statistics.

## Limits of reproduction

H1 final comparisons against historical MeteoSwiss reference data cannot be recalculated without a separately authorized reference extract; rights and provenance of all its columns have not been established. H2 is reproducible from the included synthetic records and aggregate parameters without T1 access or an LLM. H3 code and analysis methods are provided, but the day-level, medoid-level and pooled H3 outputs are omitted due to outstanding disclosure risk; neither original H3 validation nor the final H3 statistics and figures can be fully recomputed using only this tree. An authorized researcher may use `reproducibility/reproduce_restricted.py --repo . --data-dir <AUTHORIZED_DATA_DIRECTORY> --output <NEW_OUTPUT_DIRECTORY>` with separately controlled data. The script must not be used to publish those inputs. See `docs/H3_METHODS.md`.

The code is distributed under the unchanged GPL-3.0 license. The previous release DOI is 10.5281/zenodo.21341956; no v1.2.0 DOI has been assigned. Any MeteoSwiss open-data reuse requires verifying the exact product, version and applicable [terms](https://opendatadocs.meteoswiss.ch/general/terms-of-use).
