"""Non-destructive hypothesis-testing helpers.

Read-only: nothing here cleans, converts, or modifies data. Each test returns the
statistic, p-value, an effect size, sample sizes, and assumption notes — because a
p-value alone is not a finding. Results are associations/differences, never proof
of causation. Requires SciPy; if it is unavailable each function returns an error
dict instead of crashing.

Public API (names match modules/hypothesis-testing.md):
  welch_ttest, mann_whitney, one_way_anova, kruskal_wallis,
  chi_square_independence, two_proportion_test, p_adjust, correlation_test
"""

import numpy as np
import pandas as pd

try:
    from scipy import stats as st
    _HAS_SCIPY = True
except Exception:
    _HAS_SCIPY = False

_NO_SCIPY = {"error": "SciPy is required for hypothesis tests but is not installed."}


def _two_numeric_groups(df, value_col, group_col, a, b):
    for c in (value_col, group_col):
        if c not in df.columns:
            raise KeyError(f"Column not found: {c}")
    x = pd.to_numeric(df.loc[df[group_col] == a, value_col], errors="coerce").dropna()
    y = pd.to_numeric(df.loc[df[group_col] == b, value_col], errors="coerce").dropna()
    return x.to_numpy(), y.to_numpy()


def _cohens_d(x, y):
    nx, ny = len(x), len(y)
    if nx < 2 or ny < 2:
        return None
    sp = np.sqrt(((nx - 1) * x.var(ddof=1) + (ny - 1) * y.var(ddof=1)) / (nx + ny - 2))
    return float((x.mean() - y.mean()) / sp) if sp > 0 else None


def welch_ttest(df, value_col, group_col, group_a, group_b):
    """Welch's two-sample t-test (unequal variances) on a numeric column between two groups."""
    if not _HAS_SCIPY:
        return dict(_NO_SCIPY)
    x, y = _two_numeric_groups(df, value_col, group_col, group_a, group_b)
    if len(x) < 2 or len(y) < 2:
        return {"note": "each group needs >=2 non-null numeric values", "n_a": len(x), "n_b": len(y)}
    t, p = st.ttest_ind(x, y, equal_var=False)
    diff = float(x.mean() - y.mean())
    se = np.sqrt(x.var(ddof=1) / len(x) + y.var(ddof=1) / len(y))
    dfree = (x.var(ddof=1)/len(x) + y.var(ddof=1)/len(y))**2 / (
        (x.var(ddof=1)/len(x))**2/(len(x)-1) + (y.var(ddof=1)/len(y))**2/(len(y)-1))
    tcrit = st.t.ppf(0.975, dfree)
    return {
        "test": "Welch's t-test", "statistic": round(float(t), 4), "p_value": round(float(p), 6),
        "mean_a": round(float(x.mean()), 4), "mean_b": round(float(y.mean()), 4),
        "mean_difference": round(diff, 4),
        "ci95_difference": [float(round(diff - tcrit*se, 4)), float(round(diff + tcrit*se, 4))],
        "cohens_d": None if _cohens_d(x, y) is None else round(_cohens_d(x, y), 4),
        "n_a": len(x), "n_b": len(y),
        "assumptions": "Welch relaxes equal-variance; check approx normality or prefer mann_whitney for small/skewed samples.",
    }


def mann_whitney(df, value_col, group_col, group_a, group_b):
    """Mann-Whitney U test (non-parametric) — robust to skew/outliers."""
    if not _HAS_SCIPY:
        return dict(_NO_SCIPY)
    x, y = _two_numeric_groups(df, value_col, group_col, group_a, group_b)
    if len(x) < 1 or len(y) < 1:
        return {"note": "each group needs >=1 value", "n_a": len(x), "n_b": len(y)}
    u, p = st.mannwhitneyu(x, y, alternative="two-sided")
    rank_biserial = 1 - (2 * u) / (len(x) * len(y))
    return {"test": "Mann-Whitney U", "statistic": round(float(u), 4), "p_value": round(float(p), 6),
            "rank_biserial_effect": round(float(rank_biserial), 4),
            "median_a": float(np.median(x)), "median_b": float(np.median(y)),
            "n_a": len(x), "n_b": len(y)}


def _grouped_numeric(df, value_col, group_col, min_per_group):
    if value_col not in df.columns or group_col not in df.columns:
        raise KeyError("value_col or group_col not found")
    groups, labels = [], []
    for lvl, sub in df.groupby(group_col):
        v = pd.to_numeric(sub[value_col], errors="coerce").dropna().to_numpy()
        if len(v) >= min_per_group:
            groups.append(v); labels.append(str(lvl))
    return groups, labels


def one_way_anova(df, value_col, group_col, min_per_group=2):
    """One-way ANOVA (parametric) across >2 groups, with eta-squared effect size."""
    if not _HAS_SCIPY:
        return dict(_NO_SCIPY)
    groups, labels = _grouped_numeric(df, value_col, group_col, min_per_group)
    if len(groups) < 2:
        return {"note": f"need >=2 groups with >={min_per_group} values"}
    f, p = st.f_oneway(*groups)
    grand = np.concatenate(groups)
    ss_between = sum(len(g) * (g.mean() - grand.mean())**2 for g in groups)
    ss_total = ((grand - grand.mean())**2).sum()
    eta_sq = float(ss_between / ss_total) if ss_total > 0 else None
    return {"test": "one-way ANOVA", "f_statistic": round(float(f), 4), "p_value": round(float(p), 6),
            "eta_squared": None if eta_sq is None else round(eta_sq, 4),
            "groups": labels, "n_per_group": [len(g) for g in groups],
            "note": "omnibus test: a significant result means some groups differ, not which pair."}


def kruskal_wallis(df, value_col, group_col, min_per_group=2):
    """Kruskal-Wallis H test (non-parametric) across >2 groups."""
    if not _HAS_SCIPY:
        return dict(_NO_SCIPY)
    groups, labels = _grouped_numeric(df, value_col, group_col, min_per_group)
    if len(groups) < 2:
        return {"note": f"need >=2 groups with >={min_per_group} values"}
    h, p = st.kruskal(*groups)
    return {"test": "Kruskal-Wallis", "H_statistic": round(float(h), 4), "p_value": round(float(p), 6),
            "groups": labels, "n_per_group": [len(g) for g in groups],
            "note": "omnibus test: a significant result means some groups differ, not which pair."}


def chi_square_independence(df, col1, col2, max_levels=50):
    """Chi-square test of independence between two categorical columns, with Cramer's V."""
    if not _HAS_SCIPY:
        return dict(_NO_SCIPY)
    if col1 == col2:
        return {"note": "col1 and col2 are the same column"}
    sub = pd.DataFrame({"a": df[col1].values, "b": df[col2].values}).dropna()
    if sub.empty or sub["a"].nunique() > max_levels or sub["b"].nunique() > max_levels:
        return {"note": f"unsuitable: empty or >{max_levels} levels"}
    ct = pd.crosstab(sub["a"], sub["b"])
    if min(ct.shape) < 2:
        return {"note": "each variable needs >=2 levels"}
    chi2, p, dof, expected = st.chi2_contingency(ct)
    n = ct.to_numpy().sum()
    v = np.sqrt((chi2 / n) / min(ct.shape[0]-1, ct.shape[1]-1))
    return {"test": "chi-square independence", "chi2": round(float(chi2), 4), "dof": int(dof),
            "p_value": round(float(p), 6), "cramers_v": round(float(v), 4), "n": int(n),
            "min_expected_count": round(float(expected.min()), 2),
            "assumptions": "expected counts should be >=5; if min_expected_count < 5, prefer Fisher's exact and caveat."}


def two_proportion_test(count_a, n_a, count_b, n_b):
    """Two-proportion z-test for comparing rates between two groups."""
    if not _HAS_SCIPY:
        return dict(_NO_SCIPY)
    if n_a == 0 or n_b == 0:
        return {"note": "group sizes must be > 0"}
    pa, pb = count_a / n_a, count_b / n_b
    pooled = (count_a + count_b) / (n_a + n_b)
    se = np.sqrt(pooled * (1 - pooled) * (1/n_a + 1/n_b))
    if se == 0:
        return {"note": "zero standard error"}
    z = (pa - pb) / se
    p = 2 * (1 - st.norm.cdf(abs(z)))
    return {"test": "two-proportion z-test", "z": round(float(z), 4), "p_value": round(float(p), 6),
            "prop_a": round(pa, 4), "prop_b": round(pb, 4), "risk_difference": round(pa - pb, 4),
            "n_a": n_a, "n_b": n_b}


def correlation_test(df, x_col, y_col, method="pearson"):
    """Correlation with a p-value (pearson=linear, spearman=monotonic). Association, not cause."""
    if not _HAS_SCIPY:
        return dict(_NO_SCIPY)
    x = pd.to_numeric(df[x_col], errors="coerce")
    y = pd.to_numeric(df[y_col], errors="coerce")
    mask = x.notna() & y.notna()
    x, y = x[mask].to_numpy(), y[mask].to_numpy()
    if len(x) < 3:
        return {"note": "need >=3 paired values"}
    r, p = (st.spearmanr(x, y) if method == "spearman" else st.pearsonr(x, y))
    return {"test": f"{method} correlation", "r": round(float(r), 4), "p_value": round(float(p), 6),
            "n": int(len(x)), "note": "correlation is association, not causation"}


def p_adjust(pvalues, method="bh"):
    """Adjust a list of p-values for multiple comparisons.

    method: 'bh' (Benjamini-Hochberg FDR) or 'bonferroni'. Always report how many
    tests were run; never present only the significant one without this context.
    """
    p = np.asarray(pvalues, dtype=float)
    m = len(p)
    if m == 0:
        return {"method": method, "adjusted": []}
    if method == "bonferroni":
        adj = np.minimum(p * m, 1.0)
    else:  # Benjamini-Hochberg
        order = np.argsort(p)
        ranked = p[order] * m / (np.arange(m) + 1)
        ranked = np.minimum.accumulate(ranked[::-1])[::-1]
        adj = np.empty(m); adj[order] = np.minimum(ranked, 1.0)
    return {"method": method, "n_tests": m, "raw": [round(float(v), 6) for v in p],
            "adjusted": [round(float(v), 6) for v in adj]}
