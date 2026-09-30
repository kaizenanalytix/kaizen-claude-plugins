# Predictive Modeling Example

A worked example building on the modeling foundation.

## Example user request

> Build a model to predict Titanic survival and tell me how good it is.

## Expected module path

```
Analysis Planning
Data Understanding
Data Quality
Modeling Foundation
Predictive Modeling
Reporting
Verification Before Completion
```

## Expected behavior

1. **Frame & confirm** — binary classification on `survived`. Confirm the success metric (overall accuracy vs. catching survivors) since survival is imbalanced (~38%), and the feature set, before producing headline numbers.

2. **Leakage check** (foundation) — exclude `alive` (exact re-encoding of `survived`); treat `class`/`who`/`adult_male` as redundant, not independent signal.

3. **Baseline** — most-frequent class ≈ 61.5% accuracy. The bar to beat.

4. **Compare candidates** (`compare_models`, stratified split) — e.g., logistic ≈ 0.78, random forest ≈ 0.79, gradient boosting ≈ 0.84 accuracy on the holdout. Show the menu (`list_models`) and note that XGBoost/LightGBM would be available if installed.

5. **Report honestly** — pick a model *with the DS* (gradient boosting is strongest here, but logistic is far more interpretable and close-ish); report accuracy **and** precision/recall/F1/AUC against the 61.5% baseline, not accuracy alone. State the split and that the test set was untouched until the end.

6. **Drivers, carefully** — `feature_importance` highlights sex, fare, age, class. Frame these as **associative, not causal** (correlated features share credit); for an interpretable, adjusted view use `statsmodels_inference` (logistic coefficients with p-values/CIs), making clear they are associations adjusted for the included terms, not proven causes.

7. **Verification** — numbers reconcile to the holdout; baseline reported; leakage excluded; preprocessing fit on train only; no causal claims; "validated" only because a real test set was used.

## Key teaching points

- Start simple + baseline; compare candidates on the same holdout; let the DS choose.
- Prediction (ensembles) and explanation (statsmodels/linear) answer different questions.
- Importance/coefficients are associative; "validated" requires a real holdout; accuracy misleads under imbalance.

## Note on scope

Forecasting and Bayesian modeling are separate capabilities within the modeling skill.
