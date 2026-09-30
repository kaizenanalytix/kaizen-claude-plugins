---
name: modeling
description: Build and evaluate predictive and prescriptive models — regression and classification (scikit-learn, XGBoost, LightGBM, statsmodels), forecasting (ARIMA/SARIMAX, Holt-Winters, Prophet), Bayesian inference (conjugate/analytic and PyMC), and optimization (linear, mixed-integer, and non-linear programs). Use this skill when the user wants to predict an outcome from features, forecast a series into the future, quantify uncertainty as probabilities/credible intervals, or find an optimal decision under constraints. Leakage-safe, baseline-first, and holdout-validated; it advises and lets the user choose, and never reads causation off a model fit.
---

# Modeling

Predictive and prescriptive modeling on a dataset that has already been explored and quality-checked. Covers a shared modeling foundation plus four families: predictive modeling, forecasting, Bayesian modeling, and optimization. The skill **advises and lets the data scientist choose** rather than auto-running everything.

## Core principles (apply throughout)

- **Evidence over inference, and compute — don't guess.** Every metric, coefficient, interval, forecast, posterior, or optimum you report must come from code you actually execute this session — never estimated or recalled. If you didn't compute it, run it or omit it.
- **Leakage-safe and honest evaluation.** Check for target leakage; establish a **baseline** first; split before touching the data; fit all preprocessing **inside** the training fold; tune on cross-validation and report the **untouched holdout** as the final number — never an in-sample score.
- **Association, not causation.** Feature importances and coefficients are associative. A model fit never licenses a causal claim.
- **Transform only with consent, on a copy**; confirm judgment calls **before** producing results. See `references/data-transformation-policy.md`.
- **Verification before completion is mandatory** — see `modules/verification-before-completion.md`.

## Routing

- Start with `modules/modeling-foundation.md` — the shared rulebook for target/metric selection, leakage checks, splits, baselines, and the leakage-safe preprocessor (`scripts/modeling_foundation.py`, which also provides `ensure_optional` to install heavy libraries on demand when warranted). See `references/model-catalog.md` for the annotated menu of model families.
- Use `modules/predictive-modeling.md` to **predict an outcome from features** — regression/classification, multi-model and cross-validated comparison, hyperparameter tuning, importance, and statsmodels inference (`scripts/predictive_modeling.py`).
- Use `modules/forecasting.md` to **predict future values of a time series** — baselines, ARIMA/SARIMAX, Holt-Winters, Prophet, time-based backtest, and forecasts with intervals (`scripts/forecasting.py`). Confirm the series is actually forecastable; refuse on a snapshot.
- Use `modules/bayesian-modeling.md` to **quantify uncertainty as probabilities** — conjugate/analytic posteriors and optional PyMC (`scripts/bayesian_modeling.py`). Credible interval ≠ confidence interval.
- Use `modules/optimization.md` to **find the best decision under constraints** — LP/MILP (global) and non-linear (local) via scipy (`scripts/optimization.py`). Confirm the formulation first; always report solver status.
- Run `modules/verification-before-completion.md` before finalizing.

Worked runs in `examples/`.

## Visualization

When a chart aids interpretation of a model, **invoke the `visualization` skill** for the right diagnostic — ROC and PR curves and a confusion matrix for classifiers (lead with PR + confusion under class imbalance), residuals-vs-predicted for regression, a feature-importance bar for drivers (associative), or a forecast-with-intervals plot. Proactive but selective: show the diagnostics that inform the decision, not every possible plot.

## Scope

The modeling foundation plus predictive, forecasting, Bayesian, and optimization families. For exploration/quality use the **data-exploration** skill; for descriptive statistics/tests/segmentation/time-series description use the **statistical-analysis** skill. Out-of-scope advanced variants must not be implied to exist, and no result may be reported unless its helper was actually run.
