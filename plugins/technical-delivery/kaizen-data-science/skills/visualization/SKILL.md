---
name: visualization
description: Create code-generated visualizations — histograms, box/violin plots, scatter plots, correlation heatmaps, count/bar charts, time-series lines, missingness charts, and model diagnostics (ROC/PR curves, confusion matrix, residuals, feature-importance bars, forecast plots) — using matplotlib and seaborn. Use this skill when a chart would genuinely aid understanding, especially during exploratory data analysis, and whenever the user asks to plot, chart, graph, visualize, or "show me" data. These are real plots produced by running plotting code, never AI-generated images. Be intentional and choose the charts that fit the variables and the question rather than producing every possible plot.
---

# Visualization

Produce real, code-generated charts to support analysis — built by running matplotlib/seaborn, never image generation. Helpers live in `scripts/visualize.py`; seaborn is installed on demand and the library falls back to matplotlib if it can't be installed.

## Core principles

- **Code, not image generation.** Every chart is produced by executing plotting code on the actual data. Never fabricate or "describe" a chart you didn't render.
- **Intentional and selective.** Choose the few charts that genuinely illuminate the data or answer the question — driven by variable types and intent (see `references/chart-selection.md`). Do **not** generate every possible plot; a wall of charts is noise. A good EDA pass is usually a handful of well-chosen visuals, each with a one-line takeaway.
- **Proactive but restrained.** When a visual would make a finding clearer than text — a skewed distribution, a relationship, a class imbalance, a trend, a model's performance — offer/produce it without being asked, especially during EDA. But if text already answers the question cleanly, don't force a chart.
- **Honest reading.** A chart shows association, not cause. Describe what it shows plainly; don't over-read patterns, and note skew/outliers/small-n where they affect interpretation.

## How to use

- Call the relevant function in `scripts/visualize.py` (e.g. `histogram`, `boxplot`, `scatter`, `correlation_heatmap`, `countplot`, `line_plot`, `missingness_bar`, `roc_curve_plot`, `confusion_matrix_plot`, `importance_bar`, `forecast_plot`). Each returns a matplotlib `Figure` and, if given `save_path`, writes a PNG.
- **Live session:** pass `save_path` to produce a PNG and present it to the user.
- **Inside an exported notebook:** ensure `%matplotlib inline` is set (the export setup cell does this) and call the function with a **trailing semicolon** (e.g. `viz.histogram(df, "fare");`) so the figure renders once inline; this is the path the `project-export` skill uses (the helper is bundled there as `src/visualization/visualize.py`).
- Always pair a chart with a brief written takeaway — the chart supports the narrative, it doesn't replace it.

## Chart selection (summary)

See `references/chart-selection.md` for the full guide. Quick map: one numeric → histogram/box; numeric by category → box/violin; two numeric → scatter (+ correlation heatmap across many); one categorical → count/bar; over time → line (with rolling mean); missing data → missingness bar; classifier quality → ROC/PR + confusion matrix; regression fit → residual plot; drivers → importance bar; forecast → forecast plot with intervals.

## Scope

Static, code-generated statistical graphics for EDA, relationships, time series, and model diagnostics. Interactive dashboards and bespoke infographics are out of scope. Choose charts intentionally and never imply a chart was produced unless the plotting code actually ran.
