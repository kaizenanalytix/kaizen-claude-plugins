"""Non-destructive statistical helpers: distribution analysis and relationship discovery.

Descriptive only. Nothing here cleans, converts, or modifies data, and nothing
here performs formal hypothesis testing (that is a separate, later module).
Relationships reported are associative, never causal. Dependency-light: pandas
+ numpy only; SciPy is used opportunistically if available but never required.
"""

import numpy as np
import pandas as pd

try:
    from scipy import stats as _scipy_stats  # optional
except Exception:
    _scipy_stats = None


def _shape_flag(skew: float, excess_kurt: float) -> str:
    if pd.isna(skew):
        return "undetermined"
    parts = []
    if skew > 1:
        parts.append("strongly right-skewed")
    elif skew > 0.5:
        parts.append("right-skewed")
    elif skew < -1:
        parts.append("strongly left-skewed")
    elif skew < -0.5:
        parts.append("left-skewed")
    else:
        parts.append("approximately symmetric")
    if not pd.isna(excess_kurt) and excess_kurt > 1:
        parts.append("heavy-tailed")
    return ", ".join(parts)


def distribution_summary(df: pd.DataFrame, columns=None) -> dict:
    """Per-numeric-column distribution description (count, central tendency, spread, shape).

    Only operates on columns that are already numeric. Object columns that look
    numeric (e.g. "$1,234") are intentionally NOT converted here — report them as
    needing conversion and ask before analyzing.
    """
    if columns is None:
        cols = df.select_dtypes(include="number").columns.tolist()
    else:
        cols = [c for c in columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    out = {}
    for c in cols:
        s = df[c].dropna()
        if s.empty:
            out[c] = {"count": 0, "note": "no numeric values"}
            continue
        skew = float(s.skew()) if s.shape[0] > 2 else np.nan
        kurt = float(s.kurt()) if s.shape[0] > 3 else np.nan  # pandas kurt is excess kurtosis
        rec = {
            "count": int(s.shape[0]),
            "mean": float(s.mean()), "median": float(s.median()), "std": float(s.std()),
            "min": float(s.min()), "q1": float(s.quantile(0.25)),
            "q3": float(s.quantile(0.75)), "max": float(s.max()),
            "skew": None if pd.isna(skew) else round(skew, 4),
            "excess_kurtosis": None if pd.isna(kurt) else round(kurt, 4),
            "shape": _shape_flag(skew, kurt),
        }
        if _scipy_stats is not None and 8 <= s.shape[0] <= 5000:
            try:
                rec["normality_p"] = round(float(_scipy_stats.normaltest(s)[1]), 4)
            except Exception:
                pass
        out[c] = rec
    return out


def numeric_correlations(df: pd.DataFrame, method: str = "pearson", min_abs: float = 0.3) -> dict:
    """Correlation matrix among numeric columns plus the strongest pairs.

    `method`: 'pearson' (linear) or 'spearman' (monotonic/rank). Correlation is
    association, not causation; report it that way.
    """
    num = df.select_dtypes(include="number")
    num = num.loc[:, num.notna().sum() > 1]
    if num.shape[1] < 2:
        return {"method": method, "note": "need >=2 numeric columns with data",
                "matrix": {}, "top_pairs": []}
    corr = num.corr(method=method)
    pairs = []
    cols = corr.columns.tolist()
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            v = corr.iloc[i, j]
            if pd.notna(v) and abs(v) >= min_abs:
                pairs.append({"a": cols[i], "b": cols[j], "corr": round(float(v), 4)})
    pairs.sort(key=lambda p: abs(p["corr"]), reverse=True)
    return {"method": method, "matrix": corr.round(4).to_dict(), "top_pairs": pairs}


def numeric_by_category(df: pd.DataFrame, num_col: str, cat_col: str, max_groups: int = 30) -> dict:
    """Describe a numeric column across the levels of a categorical column (associative)."""
    for c in (num_col, cat_col):
        if c not in df.columns:
            raise KeyError(f"Column not found: {c}")
    if not pd.api.types.is_numeric_dtype(df[num_col]):
        return {"note": f"{num_col} is not numeric; conversion needed before analysis"}
    if df[cat_col].nunique(dropna=True) > max_groups:
        return {"note": f"{cat_col} has too many levels (>{max_groups}); not a low-cardinality category"}
    g = df.groupby(cat_col)[num_col]
    summary = pd.DataFrame({"count": g.count(), "mean": g.mean(), "median": g.median(), "std": g.std()})
    return {"num_col": num_col, "cat_col": cat_col, "by_group": summary.round(4).to_dict("index")}


def cramers_v(df: pd.DataFrame, col1: str, col2: str, max_levels: int = 50) -> dict:
    """Association strength between two categorical columns (Cramer's V, 0-1).

    Computed from the chi-square statistic without requiring SciPy. Association,
    not causation.
    """
    for c in (col1, col2):
        if c not in df.columns:
            raise KeyError(f"Column not found: {c}")
    if col1 == col2:
        return {"note": "col1 and col2 are the same column"}
    # build from individual series to avoid duplicate-label selection issues
    sub = pd.DataFrame({"a": df[col1].values, "b": df[col2].values}).dropna()
    if sub.empty or sub["a"].nunique() > max_levels or sub["b"].nunique() > max_levels:
        return {"note": f"unsuitable: empty after dropna or too many levels (> {max_levels})"}
    ct = pd.crosstab(sub["a"], sub["b"])
    n = ct.to_numpy().sum()
    if n == 0 or min(ct.shape) < 2:
        return {"note": "insufficient data for association"}
    row = ct.sum(axis=1).to_numpy()[:, None]
    col = ct.sum(axis=0).to_numpy()[None, :]
    expected = row @ col / n
    chi2 = float(((ct.to_numpy() - expected) ** 2 / expected).sum())
    r, k = ct.shape
    v = np.sqrt((chi2 / n) / (min(r - 1, k - 1)))
    return {"col1": col1, "col2": col2, "cramers_v": round(float(v), 4),
            "interpretation": "0=no association, 1=perfect association"}
