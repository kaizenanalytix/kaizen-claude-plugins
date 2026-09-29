# Model Catalog

An annotated menu of the models relevant to each modeling family, to **advise from** — lay out the relevant options and their trade-offs so the data scientist can choose, rather than asserting one. Always pair with a **baseline** and **start simple**. Every entry is an *association/decision tool*, never a causal claim. "Runnable" marks models with a helper in the scripts; others are described so they can be discussed or added.

Guidance that applies everywhere: prefer the simplest model that does the job; complexity needs to earn its place against a baseline and a simpler model on a held-out set; more flexible models (boosting, MLP) need more data and careful validation; interpretable models (linear/logistic, single trees) are preferable when the goal is understanding.

## Predictive — Regression (`scripts/predictive_modeling.py`, all runnable)

- **linear** — OLS. Use as the first model/benchmark. Strength: simple, interpretable coefficients. Watch: assumes linearity, sensitive to outliers/multicollinearity. Params: none.
- **ridge** — L2-regularized linear. Use with many/correlated features. Watch: keeps all features (no selection). Param: `alpha`.
- **lasso** — L1-regularized. Use for sparse feature selection. Watch: unstable among correlated features. Param: `alpha`.
- **elasticnet** — L1+L2 blend. Use when you want selection *and* stability with correlated features. Params: `alpha`, `l1_ratio`.
- **decision_tree** — single tree. Use for interpretable non-linear rules. Watch: high variance, overfits alone. Params: `max_depth`, `min_samples_leaf`.
- **random_forest** — bagged trees. Strong general-purpose default; handles non-linearity/interactions, little tuning. Watch: less interpretable, large. Params: `n_estimators`, `max_depth`.
- **extra_trees** — extremely randomized trees. Like RF, faster, sometimes lower variance. Params: as RF.
- **gradient_boosting** — sequential boosted trees. High accuracy. Watch: slower, tuning-sensitive, can overfit. Params: `learning_rate`, `n_estimators`, `max_depth`.
- **hist_gradient_boosting** — histogram-based boosting. Fast, strong on large/tabular data, native NaN handling. Params: `learning_rate`, `max_iter`.
- **adaboost** — adaptive boosting. Decent on clean data; sensitive to noise/outliers. Param: `n_estimators`.
- **xgboost / lightgbm** *(optional libs)* — state-of-the-art gradient boosting for tabular; LightGBM is fast on large data. Watch: many hyperparameters; validate carefully.
- **svm** (SVR) — kernel regression. Use for medium-sized non-linear problems. Watch: scales poorly to large n; needs scaling. Params: `C`, `kernel`, `gamma`.
- **knn** — neighbor averaging. Simple, non-parametric. Watch: poor in high dimensions, needs scaling. Param: `n_neighbors`.
- **mlp** — neural network. Use for complex non-linear patterns with ample data. Watch: data-hungry, tuning/scaling sensitive, opaque. Params: `hidden_layer_sizes`, `alpha`.

## Predictive — Classification (`scripts/predictive_modeling.py`, all runnable)

- **logistic** — logistic regression. First model/benchmark; interpretable (log-odds), gives calibrated-ish probabilities. Watch: assumes linear decision boundary in feature space.
- **lda** — linear discriminant analysis. Use with roughly Gaussian classes; fast, interpretable. Watch: assumes shared covariance.
- **naive_bayes** (Gaussian) — very fast baseline; good with many features/small data. Watch: assumes feature independence.
- **decision_tree / random_forest / extra_trees** — as in regression; RF a strong default classifier.
- **gradient_boosting / hist_gradient_boosting / adaboost / xgboost / lightgbm** — boosted trees; top tabular accuracy, more tuning.
- **svm** (SVC) — kernel classifier for medium non-linear problems; needs scaling; set `probability=True` for scores.
- **knn / mlp** — as in regression.
- For **class imbalance**, accuracy misleads — use precision/recall/F1/AUC and consider class weights or resampling (confirm, don't default).

## Inference (interpretable effects, not prediction)

- **statsmodels OLS / Logit** (`statsmodels_inference`) — coefficients with p-values and confidence intervals, adjusted for the other terms. Use when the goal is *which factors matter and how much*, not predictive accuracy. Associations adjusted for included terms, not proven causes.

## Forecasting (`scripts/forecasting.py`)

- **mean / naive / seasonal_naive / drift** *(runnable, always available)* — baselines to beat; seasonal_naive is the bar for seasonal data.
- **ses** (simple exponential smoothing) *(runnable, statsmodels)* — level only; for series with no trend/seasonality.
- **holt** (linear trend) *(runnable)* — trend, no seasonality.
- **holt_winters** (triple ES) *(runnable)* — trend + seasonality; robust strong competitor.
- **arima / sarimax** *(runnable, statsmodels)* — autoregressive/integrated/MA, with seasonal order; gives **uncertainty intervals**. Use differencing per the stationarity check.
- **prophet** *(runnable if installed)* — trend + multiple seasonalities + holidays, low tuning; good for business calendar effects.
- Out of scope here: Theta, TBATS, multivariate VAR — discuss but note they aren't built.
- Always: evaluate with a time-based backtest vs. the baseline; report intervals.

## Bayesian (`scripts/bayesian_modeling.py`)

- **Beta-Binomial** (`bayesian_proportion`, `bayesian_two_proportions`) *(runnable)* — a probability or a difference of two; exact conjugate.
- **Gamma-Poisson** (`bayesian_poisson_rate`) *(runnable)* — an event rate (counts per exposure); exact conjugate.
- **Normal** (`bayesian_mean`) *(runnable)* — a population mean.
- **Bayesian linear regression** (`bayesian_linear_regression`) *(runnable)* — coefficients with credible intervals (closed-form Gaussian prior).
- **PyMC GLM** (`pymc_glm`, gaussian/bernoulli/poisson) and **hierarchical/multilevel models** *(runnable if PyMC installed)* — general models with custom priors; require MCMC convergence checks (R-hat, divergences, ESS) and posterior predictive checks.
- Use Bayesian for probability statements about parameters, real priors, small data, or hierarchical structure; state priors and show sensitivity on small data.

## Optimization (`scripts/optimization.py`)

- **Linear program (LP)** (`solve_lp`) *(runnable)* — linear objective + constraints, continuous vars; **global** optimum; reports shadow prices.
- **Mixed-integer LP (MILP)** (`solve_milp`) *(runnable)* — integer/binary decisions (yes/no, counts); **global**, but NP-hard (can be slow/large).
- **Non-linear program (NLP)** (`solve_nonlinear`) *(runnable)* — non-linear objective/constraints; **local** optimum only for non-convex problems (use restarts); quadratic programs are a convex special case.
- Out of scope: stochastic/robust optimization, specialized large-scale solvers.
- Always: confirm the formulation first; report solver status (infeasible/unbounded is not an answer).

## Quick selector

- Predict a number → start `linear`/`ridge`, then tree ensembles / boosting if justified.
- Predict a class/probability → start `logistic`, then ensembles/boosting; mind imbalance.
- Understand drivers (effects) → `statsmodels` inference or Bayesian regression.
- Predict the future of a series → forecasting (backtest vs seasonal-naive; intervals).
- Probability statements / priors / small data / hierarchy → Bayesian.
- Best decision under constraints → optimization (LP → MILP → NLP by structure).
