# Modeling Foundation Example

A worked example of the advisory/governance behavior — the skill helping a data scientist set up modeling soundly, before any specific family is invoked.

## Example user request

> I want to predict which passengers survived on the Titanic. How should I approach it?

## Expected module path

```
Analysis Planning
Data Understanding
Data Quality
Modeling Foundation   (+ Predictive Modeling once the model is actually built)
Reporting
Verification Before Completion
```

## Expected behavior

1. **Frame the task** — this is binary classification (survived 0/1). State the target and ask what "good" means (overall accuracy vs. catching survivors — i.e., which errors matter), since the metric choice shapes everything. Confirm before proceeding.

2. **Advise on candidates, don't pick silently** — lay out the options with trade-offs: logistic regression / `statsmodels` for interpretability; tree ensembles (XGBoost/LightGBM) for accuracy. Let the DS choose, or recommend starting simple (logistic + a baseline) and noting where more complex models would help.

3. **Leakage check first** (`check_target_leakage`) — flag that `alive` is an exact re-encoding of `survived` and **must be excluded**; note `class`/`who`/`adult_male` are redundant/derived (drop or keep deliberately, not as independent signal).

4. **Baseline** (`baseline`) — most-frequent-class predicts "did not survive" and scores ~61.5% accuracy. Any model must beat this to be worth anything.

5. **Split** (`make_split`, stratified on `survived`) — preserve the ~38% survival rate in both sets; keep the test set untouched until the end.

6. **Leakage-safe preprocessing** (`build_preprocessor`) — impute age, scale numerics, one-hot encode `sex`/`embarked` **inside a pipeline fit on train only**, so nothing learns from the test rows.

7. **Report honestly** — once a model is built (Predictive Modeling step), report test accuracy *and* precision/recall (survival is imbalanced, so accuracy alone misleads), against the baseline, with the note that this predicts association, not the cause of survival.

## Key teaching points

- Modeling is opt-in and starts with a target + metric + baseline, not a model.
- Advise and let the DS choose; confirm target/metric/features/split before headline results.
- Leakage is the first thing to check; preprocessing must be fit on train only.
- A predictive model is not a causal explanation, and "validated" requires a real holdout.

## Note on scope

Predictive Modeling, Forecasting, Bayesian Modeling, and Optimization are built on this foundation.
