# Project

# Consensus and Dissension on the Power of Monetary Policy

## Project Overview

This repository contains the code, data, and manuscript for the paper *"Consensus and Dissension on the Power of Monetary Policy: What 75 Macroeconomic Models Have to Say"* by William B. English (Yale University), Robert J. Tetlow (Federal Reserve Board), and Connor M. Brennan (University of Chicago).

## Purpose

The project investigates a fundamental question for central banks: how large are the effects of monetary policy on output and inflation, and how quickly do they materialize? Despite decades of research, substantial uncertainty remains about these magnitudes and lags — uncertainty that directly affects how aggressively policymakers should adjust interest rates in response to economic conditions.

Rather than building a single model, the paper takes a meta-analytic approach: it simulates monetary policy shocks across 75 mostly New Keynesian DSGE models of the U.S. economy (drawn from the Macroeconomic Model Data Base curated by Volker Wieland and colleagues at Goethe University Frankfurt), then analyzes what model-level and non-model-level attributes explain the wide variation in results.

### What the Code Does

The pipeline performs the following:

1. **Model simulation.** For each of 75 macroeconomic models, run two classes of monetary policy experiments under three standardized policy rules (Taylor rule, inertial Taylor rule, growth rule):
   - One-time orthogonalized shocks to the policy rule (used to construct impulse response functions).
   - Permanent reductions in the inflation target (used to compute sacrifice ratios).

2. **Outcome variable construction.** From the resulting IRFs, compute five summary measures:
   - *y-slope*: cumulative output response normalized by cumulative real interest rate response.
   - *π-slope*: same, for inflation.
   - *sacratio*: sacrifice ratio from the disinflation experiment.
   - *y-timing* and *π-timing*: quarter at which the output / inflation IRF peaks.

3. **Attribute coding.** Hand-code each model on dimensions including nominal rigidities (sticky wages, price/wage indexation), real rigidities and transmission channels (wealth, bank credit, net worth, open economy), and non-model attributes (estimated vs. calibrated, number of equations, publication vintage, central bank authorship, estimation sample period).

4. **Regression analysis.** Relate the outcome variables to the attributes using:
   - Robust least squares (M-regression with bisquare objective, Huber scaling) for the elasticity outcomes, since the data contain large asymmetric outliers.
   - Negative binomial QML regressions (corrected for overdispersion) for the integer-valued timing variables.

5. **Tables and figures.** Generate the IRF "cloud" plots, descriptive statistics tables, and regression tables that appear in the manuscript, plus the estimated-models-only counterparts in Appendix B.

### Key Findings (Context for the AI)

- The range of estimated monetary policy effects across models is very wide, with peak output effects ranging from near zero to over 2 percent and peak timing from immediate to many quarters out.
- Most of the persistence in IRFs comes from inertia in the policy rule itself, not from propagation in the rest of the model.
- Estimated models exhibit more gradual responses than calibrated models.
- Models with central bank co-authors tend to produce longer lags, though this effect has waned in more recent vintages.
- Even after controlling for all coded attributes, R² values remain below 50% — a large share of cross-model variation remains unexplained.

### Tech Stack

The simulations rely on the MMB (Macroeconomic Model Data Base) framework, which uses Dynare/MATLAB. Downstream data manipulation, regressions, and figure generation are typically done in [fill in: Stata / R / Python / MATLAB, depending on what you're using].

### Disclaimer

The views expressed are those of the authors and do not reflect the views of the Board of Governors of the Federal Reserve System, the Federal Open Market Committee, or members of their staffs.


## Core principles

- Keep exploration in `scratch/`
- Promote stable, reusable work into `tasks/`
- Each production task has:
  - `input/`
  - `code/`
  - `output/`
  - `README.md`
  - `Makefile`
- Use relative paths only
- Keep code simple and inspectable
- Use Make for stable production dependencies
- Keep a running log in `notes/logbook.md`

## Structure

- `config/` — reusable parameters
- `notes/` — logbook, ideas, derivations
- `scratch/` — exploratory notebooks and one-offs
- `tasks/` — production workflow
- `paper/` — manuscript files
- `scripts/` — helper scripts

## Workflow

1. Explore in `scratch/`
2. Promote stable work into `tasks/`
3. Write the task `README.md` first
4. Then the task `Makefile`
5. Then the task script(s)
6. Record important results or decisions in `notes/logbook.md`

## Create a new task

```bash
bash scripts/new_task.sh measurement construct_novelty_index
```

## Create a new workstream

```bash
bash scripts/new_workstream.sh evidence
```
