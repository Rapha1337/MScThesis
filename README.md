# MSc Thesis: Synthetic Agent Simulation for mHealth Intervention Research

This repository contains the code for a **virtual simulation environment used to generate synthetic behavioral data** in the context of a mobile health (mHealth) intervention study.

The project is part of a **Master’s thesis at the University of Bern** and aims to investigate whether **synthetic datasets generated through agent-based simulations can be used to approximate intervention outcomes in behavioral science research**.

The simulation framework models **virtual participants (agents)** derived from real pre-test data and simulates their behavior across multiple time points.

---

## Project Idea

The overarching study collects **real pre-test data** from participants of the AIcoPA project: [AIcoPA on OSF](https://osf.io/w45tn/overview).

Instead of waiting for the full longitudinal dataset (post-test and follow-up), this project generates **synthetic behavioral trajectories** based on these initial data.

The workflow is:

1. Identify participant **clusters** using pre-test data.
2. Derive **personas** (user archetypes) from these clusters.
3. Create **synthetic agents** representing these personas.
4. Simulate how these agents respond to environmental conditions and potentially an intervention.
5. Generate **synthetic longitudinal datasets**.

These synthetic datasets represent **simulated responses of participants over time** (e.g., post-test and follow-up).

If the real data become available later, they can be used to **validate or falsify the simulated results**.

---

## Project Phases

### Phase 1 — Cluster Analysis and Persona Creation

Pre-test data collected in the overarching study include:

- amount physical activity
- different psychosocial constructs
- questionnaire data based on sport and health psychology theories

Using these variables, a **cluster analysis** is performed to identify groups of participants with similar characteristics.

From these clusters, **personas (archetypical user profiles)** are derived.

Example persona attributes:

- age
- baseline activity level
- motivational profile
- psychosocial constructs

These personas serve as the **basis for synthetic agents**.

### Phase 2 — Virtual Simulation Environment

A **simulation environment** is created where synthetic agents interact with environmental conditions.

The environment is implemented in **Python using the Gymnasium framework**.

#### Environment Components

**Global Environment Parameters**

These parameters affect all agents.

Examples:

- time of day
- weather
- seasonal conditions

**Agent Parameters**

Each agent represents a persona and has individual attributes.

Examples:

- age
- activity level
- behavioral tendencies
- psychosocial profile

Agents respond to these parameters and generate **individual behavioral trajectories**.

### Phase 3 — Simulation of App Intervention

In an extended phase, agents may interact with the **logic of the mobile health application**.

Possible simulated features:

- activity suggestions
- diary entries
- psychological assessments
- activity tracking

This phase allows simulation of how **different user types interact with the intervention** and how outcomes may differ.

---

## Research Goal

The thesis investigates whether synthetic data generation using agent-based simulations can support behavioral science research.

**Key questions include:**

- Can personas derived from real pre-test data produce realistic simulated behavior?

- Can synthetic trajectories approximate real intervention outcomes?

- Can synthetic datasets support early hypothesis testing?

---

## Technology Stack

**Languages**

- **Python** — main simulation environment
- **R** — potential use for cluster analysis

**Libraries / Frameworks**

- **Gymnasium** — simulation environment
- **NumPy / Pandas** — data processing
- **Scikit-learn or R packages** — cluster analysis (to be determined)

---

## Status

This repository currently focuses on the simulation code.
In the future, it may also include additional code related to the full MSc thesis workflow, such as clustering, preprocessing, analysis, and validation.

---

## Author

Raphael Reinalter  
MSc Thesis Project  
Institute of Sport Science  
University of Bern, Switzerland

---

## Current PA Decision Pipeline Note

The current full PA simulation workflow (`Simulation/run_full_pa_simulation.py`) uses a two-stage LLM decision pipeline:

1. LLM1 receives only the current normalized psychological constructs and returns psychological tendency probabilities for `do_planned_activity`, `adapt_activity`, `skip_activity`, and `extra_activity`.
2. The simulation constrains only which decision labels are valid based on whether the generated day contains planned PA.
3. LLM2 receives the generated daily context, planned PA summary, LLM1 tendency probabilities, and valid decision categories, then makes the final context-sensitive PA decision.

The active workflow no longer performs seeded categorical PA-decision sampling before LLM2. Seeded sampling helpers in the code are retained only as deprecated legacy compatibility helpers.
