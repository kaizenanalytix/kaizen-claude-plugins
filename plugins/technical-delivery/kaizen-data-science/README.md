# Kaizen Data Science

**Version 2.9.4** · Kaizen Analytix LLC

A modular set of data-analysis skills that trigger on demand. Hand Claude a dataset and ask a
question; the right skill engages for the task, and the work can be packaged at the end as a
reproducible Jupyter notebook in the mandatory Kaizen data-science project structure.

## Skills

| Skill | What it does |
|---|---|
| `data-exploration` | Profiles and quality-checks a dataset and reports findings. **Start here** for any new dataset. |
| `statistical-analysis` | Distributions and relationships, hypothesis tests, segmentation/clustering, time-series behaviour (trend, seasonality, stationarity). |
| `modeling` | Regression and classification, forecasting, Bayesian inference and optimization. Leakage-safe, baseline-first, holdout-validated. |
| `visualization` | Real, code-generated charts with matplotlib/seaborn, including EDA plots and model diagnostics. |
| `project-export` | Packages the analysis into one notebook that re-runs from the raw data, with the plugin's helper scripts placed in `src/`. |

## Typical flow

`data-exploration` → `statistical-analysis` and/or `modeling` (with `visualization` throughout)
→ `project-export`

## Requirements

Python 3 with `pandas`, `numpy`, `scipy`, `scikit-learn`, `statsmodels` and `matplotlib`.

Optional, used when a task calls for them: `seaborn`, `xgboost`, `lightgbm`, `pymc`, `arviz`,
`prophet`, and the Jupyter notebook tooling (`nbformat`, `nbclient`) for `project-export`.

> **Heads-up: on-demand installs.** When an optional library is missing, some scripts install it
> automatically with `pip install <package> --break-system-packages` into the Python the session
> is using. This is fine in the claude.ai / Cowork sandbox. On your own machine, run Claude Code
> from a virtual environment (or pre-install the packages above) if you don't want your system
> Python changed. If an install fails, the modeling skill falls back to a scikit-learn equivalent
> and says so.
