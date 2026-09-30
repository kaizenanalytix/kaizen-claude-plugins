---
name: statistical-analysis
description: Analyze distributions and relationships, run hypothesis tests, segment or cluster data, and analyze time series. Use this skill when the user wants to examine how a variable is distributed, whether variables relate or correlate, test a hypothesis or compare groups, divide data into segments/clusters and profile them, or understand behaviour over time (trend, seasonality, stationarity, gaps). Run data exploration and quality checks first, since statistics on unclean data mislead.
---

# Statistical Analysis

Descriptive and inferential statistics on a dataset that has already been explored and quality-checked: distributions, relationships, hypothesis tests, segmentation, and time-series description.

## Core principles (apply throughout)

- **Evidence over inference, and compute — don't guess.** Every statistic, test statistic, p-value, effect size, or correlation you report must come from code you actually execute this session — never estimated or recalled. If you didn't compute it, don't state it.
- **Transform only with consent, on a copy, never mutating the source**; confirm judgment calls **before** producing any result that depends on them. See `references/data-transformation-policy.md`.
- **Association, not causation.** Correlations, group differences, and clusters are descriptive; they do not establish cause.
- **Verification before completion is mandatory** — see `modules/verification-before-completion.md`.

## Routing

- Use `modules/statistical-analysis.md` for variable **distributions** and **relationships/correlations** (`scripts/statistical_analysis.py`).
- Use `modules/hypothesis-testing.md` to **test a hypothesis or compare groups** — state H0/H1/α up front, pick the right test, report effect sizes and confidence intervals, and correct for multiple comparisons (`scripts/hypothesis_testing.py`).
- Use `modules/segmentation-analysis.md` to **divide data into groups and profile them** — rule-based, quantile/binning, or k-means clustering (`scripts/segmentation.py`). Unsupervised/descriptive only.
- Use `modules/time-series-analysis.md` to understand behaviour **over time** — trend, seasonality, stationarity, gaps (`scripts/time_series.py`). Descriptive only; for predicting future values, use the **modeling** skill's forecasting capability. First confirm the data has a real time dimension, not just a snapshot.
- Run `modules/verification-before-completion.md` before finalizing.

See `references/data-analysis-standards.md` and the worked runs in `examples/`.

## Visualization

When a chart clarifies a statistical finding, **invoke the `visualization` skill** to render it — distributions (histogram/box), group comparisons (box/violin by group), relationships (scatter, correlation heatmap), or behaviour over time (line plot with a rolling mean). Proactive but selective: visualize the headline result (e.g. a key correlation, a group difference, the trend), not every variable. Pair each chart with its takeaway.

## Scope

Distribution, relationship discovery, hypothesis testing, segmentation, and time-series **description**. For prediction/forecasting/Bayesian/optimization use the **modeling** skill. Never imply an analysis was performed unless its helper was actually run.
