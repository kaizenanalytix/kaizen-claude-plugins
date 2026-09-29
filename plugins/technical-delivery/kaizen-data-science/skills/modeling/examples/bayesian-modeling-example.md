# Bayesian Modeling Example

A worked example showing the analytic Bayesian path (no PyMC needed).

## Example user request

> Among Titanic passengers, how confident can we be that women survived at a higher rate than men — as a probability, not a p-value?

## Expected module path

```
Analysis Planning
Data Understanding
Data Quality
Bayesian Modeling
Reporting
Verification Before Completion
```

## Expected behavior

1. **Recognize the Bayesian framing** — the user wants a probability statement about the difference in rates, which is a Bayesian question. Note this is the Bayesian counterpart to the frequentist two-proportion test (either is valid).

2. **State the model and prior** — independent Beta posteriors for each group's survival rate with a weak uniform prior (Beta(1,1)); say so, and note that with these sample sizes the prior barely matters.

3. **Compute** (`bayesian_two_proportions`) — female ≈ 0.74, male ≈ 0.19, posterior mean difference ≈ 0.55 with a 95% credible interval of roughly [0.49, 0.61], and **P(women's rate > men's) ≈ 1.0**.

4. **Report as a posterior probability** — "Given the data and a weak prior, it's essentially certain (P ≈ 1.0) that women survived at a higher rate, with the gap most plausibly 49–61 points." Make clear this is a probability about the parameter, not a p-value, and that it's an association (the mechanism — loading protocol — is not proven by the model).

5. **(If asked to model drivers)** — `bayesian_linear_regression` gives standardized coefficients with credible intervals; for hierarchical structure or custom priors, `pymc_glm` (if PyMC is installed) with convergence checks (R-hat, divergences) before trusting it.

6. **Verification** — prior stated; posterior (interval + probability) reported, not just a point; no causal claim; credible interval not described as a confidence interval.

## Key teaching points

- Bayesian answers "P(hypothesis | data)" directly; state the prior and (for small data) show sensitivity.
- Report credible intervals and posterior probabilities, not point estimates; a credible interval ≠ a confidence interval.
- Analytic conjugate helpers cover proportions/means/linear regression without MCMC; PyMC is for general/hierarchical models and needs convergence checks.

## Note on scope

Optimization is also available in this skill. The skill should not imply out-of-scope techniques were used.
