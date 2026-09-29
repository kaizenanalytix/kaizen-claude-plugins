# Modeling Foundation

The shared entry point and rulebook for the modeling families (forecasting, predictive modeling, Bayesian modeling, optimization). Use this **before and alongside** any specific model family. Its job is to help the data scientist **choose** the right approach and run it soundly — not to pick or train a model for them silently.

Helpers live in `scripts/modeling_foundation.py` (`check_target_leakage`, `make_split`, `regression_metrics`, `classification_metrics`, `baseline`, `build_preprocessor`). All are read-only and require scikit-learn (degrading to a note if absent).

## When to engage (and when not to)

- Modeling is **opt-in and post-EDA.** Do not jump to a model by default; reach here only when the user actually wants to predict, forecast, optimize, or quantify uncertainty, and after data understanding and quality are in hand.
- If the question can be answered descriptively (a correlation, a group comparison, a trend), say so and don't escalate to modeling.
- A model is a **bigger commitment** than EDA: it has a target, a metric, and assumptions the user should agree to. Confirm those before producing headline results (see "Judgment calls" below).

## Advise, then let the data scientist choose

Lay out the **relevant** options for the use case with their trade-offs, and let the DS pick — don't assert one model as "the answer." Map the question to candidate families:

- Predict a **number** → regression (Predictive Modeling): linear/regularized → tree ensembles (XGBoost/LightGBM) for accuracy, linear/`statsmodels` for interpretability.
- Predict a **category / probability** → classification (Predictive Modeling).
- Predict a **future value of a series** → Forecasting (ARIMA/Prophet) — needs a real time dimension.
- Need **uncertainty / small data / priors** → Bayesian Modeling (PyMC).
- Choose the **best decision under constraints** → Optimization.

State which families are implemented vs planned; never imply a planned family ran. (Predictive Modeling is the first family being built out; the others follow.)

For the **full annotated menu of models per family** — when to use each, strengths/weaknesses, assumptions, key hyperparameters, and what's runnable — see `references/model-catalog.md`. Use it to lay out the relevant options and their trade-offs so the data scientist can choose; start simple and benchmark against a baseline.

## The workflow every family inherits

1. **Define the target and the success metric up front** — what is predicted, and what "good" means (and why that metric).
2. **Frame baselines first** — the naive baseline to beat (`baseline`: mean for regression, most-frequent class for classification). A model that can't beat it isn't worth shipping.
3. **Split correctly before looking at the data again** (`make_split`):
   - random / **stratified** (classification, to preserve class balance),
   - **grouped** when rows cluster (e.g., multiple rows per customer) so no group spans train and test,
   - **time-aware** for anything temporal — earliest rows train, latest test, **never shuffle the future into the past**.
   - Keep the test set untouched until the very end; tune on validation/CV, not on test.
4. **Preprocess leakage-safely** (`build_preprocessor`): fit imputation/scaling/encoding **on train only**, inside a pipeline. This is the core leakage defense and a direct extension of the transformation policy (all transforms on copies, learned from train).
5. **Train candidate models, evaluate on the holdout** with task-appropriate metrics.
6. **Report honestly** — performance, uncertainty, and limits.

## Leakage — check before trusting any model

Leakage produces "great" models that fail in reality. Guard against:

- **Target leakage** — a feature that encodes the outcome (run `check_target_leakage`; recall the Titanic `alive` ≡ `survived` case). Exclude such features, don't use them.
- **Temporal leakage** — using future information to predict the past (avoid via time-aware splits).
- **Preprocessing leakage** — fitting scalers/imputers/encoders on the full dataset before splitting (avoid via the train-only pipeline).
- **Group leakage** — the same entity in train and test (avoid via grouped splits).

## Metrics by task

- **Regression**: MAE, RMSE, R² (`regression_metrics`). Report error in the target's units, not just R².
- **Classification**: accuracy *plus* precision/recall/F1 and ROC-AUC; with class imbalance, accuracy alone misleads — always state the base rate (`classification_metrics`).
- **Forecasting**: error on a time holdout (MAE/RMSE/MAPE), not in-sample fit.
- **Probabilistic**: calibration and interval coverage, not just point error.

## Judgment calls to confirm before headline results

Target definition, feature set, split strategy, evaluation metric, class-imbalance handling, and "which model wins" are judgment calls. Surface them and confirm before presenting a model result as the answer — consistent with `references/data-transformation-policy.md`. Show the *impact* of an option to help the DS decide; withhold the headline until they choose.

## Honest reporting (hard rules)

- A predictive model shows **association and pattern, not causation** — never say a feature "causes" the target from a fit.
- Report test-set performance with its **uncertainty** and the **baseline** for context; a number without a baseline is not a finding.
- Be explicit about **generalization limits** and distribution shift — performance holds only for data like the training data.
- **Only claim a model was validated if a held-out test (or proper CV) was actually used.** Never imply tuning/validation that didn't happen, and never report in-sample scores as if they were out-of-sample.
