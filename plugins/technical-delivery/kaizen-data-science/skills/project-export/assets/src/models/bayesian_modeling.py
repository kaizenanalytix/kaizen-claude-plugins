"""Bayesian modeling helpers. Two layers:

1. Always-available analytic/conjugate inference (scipy/numpy): a proportion
   (Beta-Binomial), a difference of two proportions (Monte Carlo over Beta
   posteriors), a mean (Normal), and Bayesian linear regression (Gaussian prior,
   closed-form posterior). Exact, fast, no heavy dependencies.
2. An optional PyMC path for general/hierarchical MCMC models, used only if pymc
   (and arviz) are installed; otherwise it returns a note pointing at the helpers above.

Bayesian inference reports the full posterior — credible intervals and posterior
probabilities, not just point estimates. Priors are explicit assumptions and must be
stated; with little data they dominate. A credible interval is not a confidence
interval, and none of this implies causation. Nothing here mutates the input.
"""

import numpy as np
import pandas as pd

try:
    from scipy import stats as _st
    _HAS_SCIPY = True
except Exception:
    _HAS_SCIPY = False

try:
    import pymc as _pm
    import arviz as _az
    _HAS_PYMC = True
except Exception:
    _HAS_PYMC = False


def bayesian_proportion(successes, n, prior_alpha=1.0, prior_beta=1.0, ref=0.5, cred=0.95):
    """Beta-Binomial conjugate posterior for a probability. Exact."""
    if not _HAS_SCIPY:
        return {"error": "scipy required"}
    a, b = prior_alpha + successes, prior_beta + (n - successes)
    lo, hi = _st.beta.ppf([(1 - cred) / 2, 1 - (1 - cred) / 2], a, b)
    return {"posterior": f"Beta({a:.1f}, {b:.1f})",
            "posterior_mean": round(float(a / (a + b)), 4),
            f"cred_interval_{int(cred*100)}": [round(float(lo), 4), round(float(hi), 4)],
            f"P(theta>{ref})": round(float(1 - _st.beta.cdf(ref, a, b)), 4),
            "prior": f"Beta({prior_alpha}, {prior_beta})",
            "note": "conjugate posterior; with small n the prior matters — try a different prior to test sensitivity."}


def bayesian_two_proportions(s1, n1, s2, n2, prior_alpha=1.0, prior_beta=1.0, draws=200000, seed=0):
    """Posterior over the difference p1 - p2 via Monte Carlo from two Beta posteriors."""
    if not _HAS_SCIPY:
        return {"error": "scipy required"}
    rng = np.random.default_rng(seed)
    d1 = rng.beta(prior_alpha + s1, prior_beta + (n1 - s1), draws)
    d2 = rng.beta(prior_alpha + s2, prior_beta + (n2 - s2), draws)
    diff = d1 - d2
    return {"p1_mean": round(float(d1.mean()), 4), "p2_mean": round(float(d2.mean()), 4),
            "diff_mean": round(float(diff.mean()), 4),
            "diff_cred_interval_95": [round(float(np.percentile(diff, 2.5)), 4),
                                       round(float(np.percentile(diff, 97.5)), 4)],
            "P(p1>p2)": round(float((diff > 0).mean()), 4),
            "note": "posterior probability, not a p-value; P(p1>p2) is the chance group 1's rate exceeds group 2's under the model."}


def bayesian_poisson_rate(counts, exposure=None, prior_shape=1.0, prior_rate=0.0, cred=0.95):
    """Gamma-Poisson conjugate posterior for an event rate (counts per unit exposure). Exact."""
    if not _HAS_SCIPY:
        return {"error": "scipy required"}
    counts = np.asarray(counts, float)
    total = float(counts.sum())
    expo = float(len(counts)) if exposure is None else float(np.sum(exposure))
    a, b = prior_shape + total, prior_rate + expo
    lo, hi = _st.gamma.ppf([(1 - cred) / 2, 1 - (1 - cred) / 2], a, scale=1 / b)
    return {"posterior": f"Gamma(shape={a:.2f}, rate={b:.2f})",
            "posterior_mean_rate": round(float(a / b), 4),
            f"cred_interval_{int(cred*100)}": [round(float(lo), 4), round(float(hi), 4)],
            "note": "rate = events per unit exposure; conjugate Gamma-Poisson, exact. With little exposure the prior matters."}


def bayesian_mean(data, prior_mean=0.0, prior_sd=1e6, cred=0.95):
    """Normal model for a population mean (variance estimated from data). Approximate-conjugate."""
    if not _HAS_SCIPY:
        return {"error": "scipy required"}
    x = pd.to_numeric(pd.Series(data), errors="coerce").dropna().values
    n = len(x)
    if n < 2:
        return {"note": "need >=2 values"}
    xbar, s = float(x.mean()), float(x.std(ddof=1))
    lik_prec = n / (s ** 2)
    prior_prec = 1 / (prior_sd ** 2)
    post_var = 1 / (lik_prec + prior_prec)
    post_mean = post_var * (lik_prec * xbar + prior_prec * prior_mean)
    half = _st.norm.ppf(1 - (1 - cred) / 2) * np.sqrt(post_var)
    return {"posterior_mean": round(post_mean, 4),
            f"cred_interval_{int(cred*100)}": [round(post_mean - half, 4), round(post_mean + half, 4)],
            "n": n, "data_sd": round(s, 4),
            "note": "weak prior by default, so this approximates the sample mean's uncertainty; set prior_mean/prior_sd to encode real prior knowledge."}


def bayesian_linear_regression(df, target, features, prior_sd=10.0, cred=0.95):
    """Bayesian linear regression with a Gaussian prior on standardized coefficients.

    Closed-form Gaussian posterior (noise variance estimated from an OLS fit). Reports
    each coefficient's posterior mean and credible interval. Standardized inputs, so
    coefficients are comparable in size. Exact given the estimated noise.
    """
    if not _HAS_SCIPY:
        return {"error": "scipy required"}
    data = df[[target] + list(features)].dropna()
    Xraw = pd.get_dummies(data[features], drop_first=True).astype(float)
    cols = list(Xraw.columns)
    X = Xraw.values
    X = (X - X.mean(0)) / np.where(X.std(0) == 0, 1, X.std(0))  # standardize features
    y = data[target].values.astype(float)
    y_sd = y.std() if y.std() != 0 else 1.0
    y = (y - y.mean()) / y_sd  # standardize target so coefficients are standardized betas
    if len(y) < len(cols) + 2:
        return {"note": "too few rows for the number of features"}
    # estimate noise variance from OLS residuals
    beta_ols, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta_ols
    sigma2 = float(resid.var(ddof=max(1, len(cols))))
    tau2 = prior_sd ** 2
    A = X.T @ X / sigma2 + np.eye(len(cols)) / tau2
    cov = np.linalg.inv(A)
    mean = cov @ X.T @ y / sigma2
    z = _st.norm.ppf(1 - (1 - cred) / 2)
    sd = np.sqrt(np.diag(cov))
    terms = []
    for i, c in enumerate(cols):
        terms.append({"feature": c, "post_mean": round(float(mean[i]), 4),
                      f"cred_{int(cred*100)}": [round(float(mean[i] - z * sd[i]), 4),
                                                 round(float(mean[i] + z * sd[i]), 4)],
                      "P(>0)": round(float(_st.norm.cdf(mean[i] / sd[i])), 4)})
    terms.sort(key=lambda d: abs(d["post_mean"]), reverse=True)
    return {"method": "analytic Bayesian linear regression (Gaussian prior, standardized X and y)",
            "prior_sd": prior_sd, "n": len(y), "terms": terms,
            "note": "standardized coefficients (SDs of target per SD of feature) — comparable in size, associative not causal; credible interval = the 95% most plausible coefficient values given data + prior."}


def pymc_glm(df, target, features, family="gaussian", draws=1000, tune=1000, seed=0):
    """General Bayesian GLM via PyMC with convergence diagnostics — if PyMC is installed.

    family: 'gaussian' (linear), 'bernoulli' (logistic), or 'poisson' (counts). Returns posterior summary
    (mean, 94% HDI), R-hat, ESS, and divergence count. Always check convergence before
    trusting the result.
    """
    if not _HAS_PYMC:
        return {"error": "pymc/arviz not installed. Use bayesian_linear_regression / bayesian_proportion "
                         "for analytic cases, or install pymc for general/hierarchical MCMC models."}
    data = df[[target] + list(features)].dropna()
    X = pd.get_dummies(data[features], drop_first=True).astype(float)
    Xz = (X - X.mean()) / X.std().replace(0, 1)
    y = data[target].values.astype(float)
    with _pm.Model() as m:
        b0 = _pm.Normal("intercept", 0, 10)
        b = _pm.Normal("beta", 0, 10, shape=Xz.shape[1])
        mu = b0 + _pm.math.dot(Xz.values, b)
        if family == "bernoulli":
            _pm.Bernoulli("y", logit_p=mu, observed=y)
        elif family == "poisson":
            _pm.Poisson("y", mu=_pm.math.exp(mu), observed=y)
        else:
            sigma = _pm.HalfNormal("sigma", 5)
            _pm.Normal("y", mu=mu, sigma=sigma, observed=y)
        idata = _pm.sample(draws=draws, tune=tune, chains=4, random_seed=seed,
                           progressbar=False, idata_kwargs={"log_likelihood": False})
    summ = _az.summary(idata, var_names=["intercept", "beta"], hdi_prob=0.94)
    div = int(idata.sample_stats["diverging"].sum())
    rhat_max = float(summ["r_hat"].max())
    return {"family": family, "features": list(X.columns),
            "summary": summ.reset_index().to_dict(orient="records"),
            "max_r_hat": rhat_max, "divergences": div,
            "converged": bool(rhat_max < 1.01 and div == 0),
            "note": "trust only if converged (R-hat<1.01, 0 divergences, adequate ESS); HDI is the 94% credible interval. Not causal."}
