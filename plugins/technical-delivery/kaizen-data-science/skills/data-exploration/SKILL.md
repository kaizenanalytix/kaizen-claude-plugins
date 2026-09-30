---
name: data-exploration
description: Explore, understand, and quality-check a dataset and report findings. Use this skill whenever the user shares or references a dataset, dataframe, CSV/Excel/parquet file, or table and wants it inspected, profiled, summarized, assessed for quality, cleaned-assessed, or written up — including casual phrasing like "what's in this data", "take a look at this file", "is this data any good", or "what should I do with this". Start here for any new dataset before deeper statistical analysis or modeling.
---

# Data Exploration & Quality

The entry point for working with a new dataset: plan the approach, understand the data, assess its quality, and report findings clearly. For deeper work, hand off to the statistical-analysis or modeling skills.

## Core principles (apply throughout)

- **Evidence over inference, and compute — don't guess.** Every quantitative value you report (counts, percentages, summary statistics) must come from code you actually execute this session, never from estimation or recollection. If you didn't compute it, don't state it.
- **Transform only with consent, always on a copy, never mutating the source.** Inspection and measurement are always allowed. Cleaning, conversion, dedup, normalization, imputation, and feature engineering happen only when the user asks or confirms — on a derived copy written to a *new* file, logged, never overwriting the input. Judgment-based or lossy steps (which labels are synonyms, which rows to drop, which imputation) must be confirmed **before** producing any result that uses them. See `references/data-transformation-policy.md`.
- **Association, not causation.** Descriptive analysis describes; it does not establish cause.
- **Verification before completion is mandatory** — see `modules/verification-before-completion.md` and run it before returning any analysis.

## Routing

1. Always begin with `modules/analysis-planning.md` to choose the smallest sufficient path.
2. Use `modules/data-understanding.md` to profile structure, types, and distributions (`scripts/profile_dataframe.py`).
3. Use `modules/data-quality.md` to assess missingness, duplicates, outliers, and consistency (`scripts/quality_checks.py`). Resolve or caveat quality issues before any downstream statistics or modeling.
4. Use `modules/reporting.md` to summarize findings for the intended audience.
5. Run `modules/verification-before-completion.md` before finalizing.

See `references/data-analysis-standards.md` for conventions and `examples/basic-eda-example.md` for a worked run.

## Visualization

Charts are often the fastest way to convey an EDA finding. When a visual would make something clearer than text — a skewed distribution, an outlier-heavy variable, a class imbalance, or the shape of missingness — **invoke the `visualization` skill** to produce the appropriate chart (e.g. histogram, box plot, count plot, missingness bar). Be proactive but selective: a handful of well-chosen charts, each with a one-line takeaway, not one per column. If text already answers the question, don't force a chart.

## Scope

Exploration, data quality, and reporting. For distributions/relationships/tests/segments/time-series use the **statistical-analysis** skill; for prediction/forecasting/Bayesian/optimization use the **modeling** skill. Never imply an analysis was performed unless its helper was actually run.
