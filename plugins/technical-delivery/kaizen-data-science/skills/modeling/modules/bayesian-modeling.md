# Bayesian Modeling

Use this module when the user wants **full uncertainty quantification**, wants to **encode prior knowledge**, has **small data**, or has **hierarchical / multilevel structure** — situations where a posterior distribution and credible intervals are more honest than a single point estimate or p-value. It builds on `modules/modeling-foundation.md` and is the Bayesian counterpart to the frequentist inference in `modules/predictive-modeling.md` (`statsmodels_inference`).

Helpers live in `scripts/bayesian_modeling.py`. Two layers: always-available **analytic/conjugate** helpers (`bayesian_proportion`, `bayesian_two_proportions`, `bayesian_mean`, `bayesian_linear_regression`) using scipy/numpy, and an optional **PyMC** path (`pymc_glm`) for general/hierarchical MCMC models that returns a note if pymc/arviz aren't installed.

See `references/model-catalog.md` for the annotated Bayesian menu.

## When Bayesian over frequentist?

Both are valid; choose by need, don't default. Reach for Bayesian when:
- you want a **probability statement about a parameter** ("P(this rate exceeds that one) = 0.97") rather than a p-value;
- you have **genuine prior information** worth encoding;
- the data is **small** and you want honest, prior-regularized uncertainty;
- the structure is **hierarchical** (groups within groups) — PyMC's strength.

If none of those apply, the frequentist test/model is simpler and fine. Say which you're using and why.

## Priors are assumptions — state them

- Every prior is a modeling choice. **State the prior explicitly** and justify it; with little data the prior can dominate the posterior, so for small samples **show prior sensitivity** (re-run with a different reasonable prior and report whether the conclusion holds). The conjugate helpers take prior parameters precisely so this is easy.
- Default to weak/uninformative priors unless the user supplies real knowledge — and confirm the model structure, likelihood, and priors before presenting a headline result (per `references/data-transformation-policy.md`).

## Report the posterior, not a point

- Report **credible intervals** (the 95% most plausible parameter values) and **posterior probabilities** of the questions asked — not just a posterior mean.
- A **credible interval is not a confidence interval**: it is a direct probability statement about the parameter given data and prior. Don't conflate the two.
- None of this is causal — coefficients and differences are associations under the model.

## MCMC discipline (the PyMC path)

When `pymc_glm` is used, the result is only trustworthy if the sampler converged:
- **R-hat ≈ 1.0** (the helper flags > 1.01), **zero divergences**, and adequate effective sample size.
- Run **posterior predictive checks** (does data simulated from the posterior resemble the real data?) before believing the model.
- MCMC is **computationally expensive** — flag the cost, and prefer the analytic helpers when the problem is a simple proportion/mean/linear regression.
- **PyMC is a heavy optional library.** The conjugate/analytic helpers need only scipy and cover proportions, means, rates, and linear regression with no PyMC. Only when a **hierarchical/multilevel or custom-prior model is genuinely required** should you reach for it: call `ensure_optional("pymc")` (from `modeling_foundation`) first, and if it can't install (no network egress), say the hierarchical/custom model isn't available here and offer the analytic helpers or a simpler model instead. Don't install PyMC for a problem the conjugate helpers already solve.
- If it didn't converge, say so and do not report the estimates as final.

## Honest reporting (hard rules)

- Bayesian inference is **not magic for tiny data** — it quantifies uncertainty honestly; it does not manufacture certainty the data doesn't support. Wide credible intervals are a finding, not a failure.
- State the prior, the likelihood, and (for MCMC) the convergence status alongside any estimate.
- Don't present a posterior as proof of a mechanism; it's an association under a stated model.

## Scope

This covers conjugate/analytic Bayesian inference and (optionally) PyMC GLMs/hierarchical models. Note that `bayesian_two_proportions` answers an A/B-style comparison in a Bayesian way.
