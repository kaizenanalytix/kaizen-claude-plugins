# Predictive Modeling

Use this module when the user wants to **predict an outcome** — a number (regression) or a category/probability (classification) — from features. It builds directly on `modules/modeling-foundation.md`: read that first, because every rule there (splits, leakage prevention, baselines, metrics, honest reporting) applies here.

Covers scikit-learn (linear/regularized, tree ensembles, SVM, KNN), **XGBoost** and **LightGBM** (gradient boosting), and **statsmodels** for interpretable inference. Helpers live in `scripts/predictive_modeling.py` (`list_models`, `train_evaluate`, `compare_models`, `feature_importance`, `statsmodels_inference`). All run through the foundation's leakage-safe pipeline and held-out evaluation. scikit-learn is required; XGBoost/LightGBM/statsmodels are used only if installed and otherwise reported as unavailable.

## Predict vs. explain — pick the tool to the goal

- **Prediction / accuracy** → scikit-learn ensembles, XGBoost, LightGBM. The question is "how well can we predict," and the model can be a black box.
- **Explanation / inference** → linear/logistic models or `statsmodels` (`statsmodels_inference`), where you want interpretable coefficients with p-values and confidence intervals. The question is "which factors are associated, adjusted for the others."

These answer different questions. Don't hand someone a 200-tree forest when they wanted to understand drivers, and don't read causal stories off a black-box model.

## Advise and compare, don't anoint one model

Use `list_models` to show the available menu for the task (13 regression / 12 classification model families, plus XGBoost/LightGBM when installed), and `compare_models` (single split) or `cross_validate_models` (k-fold, more robust) to evaluate several candidates so the data scientist can choose with evidence. For each model's when/why/trade-offs, see `references/model-catalog.md`. Guidance:

- **Start simple.** A linear/logistic model plus the baseline first; reach for ensembles only if the simpler model and the data justify it.
- **When candidates are close, prefer the simpler/more interpretable one** — small holdout gaps are often noise, not a real winner.
- Surface the trade-offs (accuracy vs interpretability vs training cost), and let the DS pick rather than declaring a single "best."

## Workflow (inherited from the foundation)

1. Confirm the **target**, **task** (regression/classification), and **success metric** — and the judgment calls (feature set, split strategy, imbalance handling) before headline results.
2. **Check leakage** (`check_target_leakage` from the foundation) and exclude target-encoding features.
3. **Baseline** first.
4. **Split** appropriately (stratified for classification; time-aware/grouped when relevant) and keep the test set untouched.
5. **Train in a leakage-safe pipeline** (`train_evaluate` builds it for you — preprocessing fit on train only) and **evaluate on the holdout**.
6. **Tune on validation / cross-validation, never on the test set.** Use `cross_validate_models` to compare candidates by k-fold score, and `tune_model` to search hyperparameters by cross-validation — it returns the **best hyperparameters** plus an honest score on a held-out test set the search never saw. Report the final number once, on that untouched test set (the holdout score), not the CV score.

## Reading results honestly

- Always report scores **against the baseline** and in the target's units (regression) or with the **base rate** (classification, where accuracy alone misleads under imbalance — read precision/recall/F1/AUC).
- **Feature importance and coefficients are associative, not causal** (`feature_importance` says so). Correlated features split or trade credit, so importance rankings are not a causal ordering and can shift between model types.
- Class imbalance: state the positive-class rate; consider precision/recall trade-offs and resampling/class weights as options to confirm, not defaults.
- **Only call a model "validated" if a real held-out test (or proper CV) was used.** Never report in-sample fit as if it were out-of-sample, and never imply tuning that didn't happen.
- A predictive model describes patterns in data like the training data; flag generalization limits and distribution shift.

## Performance on large data

Training cost grows with rows × models × CV folds, and the tree ensembles dominate it. To keep runs fast (everything is CPU — there is no GPU path):

- **Parallelism is automatic.** Random forest, extra trees, KNN, and (when installed) XGBoost/LightGBM run multi-core (`n_jobs=-1`), and `cross_validate_models` runs its folds in parallel. No action needed.
- **`hist_gradient_boosting` is the fast large-data learner** — it now works through the leakage-safe pipeline (the sparse one-hot is densified for it automatically), so prefer it over `random_forest`/`gradient_boosting` on large row counts; it is typically much faster and competitive in accuracy.
- **On large data (roughly ≥ 50k rows), prefer a single-holdout comparison (`compare_models`) over k-fold (`cross_validate_models`)** — a single split is several times cheaper and the ranking is usually stable at that scale. Reserve k-fold CV for smaller data or a final check on the chosen model, and tune (`tune_model`) only the one model you've selected, not the whole menu.
- Be selective with the menu on big data: compare a few sensible candidates (e.g. logistic/linear baseline + `hist_gradient_boosting` + one of random forest/XGBoost), not all twelve.



These run when installed; otherwise the menu uses the scikit-learn models — and `hist_gradient_boosting` is the always-available close cousin of LightGBM, so the *capability* isn't missing, only the specific library.

- **Install on request.** If the user asks for XGBoost/LightGBM, call `ensure_optional("xgboost")` (from `modeling_foundation`) **before importing/using the predictive helpers in that cell**, so the menu detects it (the availability flags are set at import time — install first, then import, or reload). If the install can't run (no network egress), use `hist_gradient_boosting` and tell the user you fell back.
- **Suggest installing when the data is large enough to matter.** As a rough heuristic, around **≥ 50k rows** (or many features, or when accuracy is the explicit priority), XGBoost/LightGBM can meaningfully beat scikit-learn boosting in speed and sometimes accuracy — worth offering to install. Below a few thousand rows the gain over `gradient_boosting`/`hist_gradient_boosting` is negligible; **don't install for marginal gain on small data** (say so — it's a heuristic, not a rule).
- **Always disclose** whether a library was installed on demand or whether you fell back to a scikit-learn equivalent.

## Scope

This is supervised predictive modeling. Forecasting (time-indexed prediction) is its own implemented module — it needs the time-aware treatment, not a plain train/test split, so route series prediction there. Bayesian modeling is its own module; route to it as appropriate.
