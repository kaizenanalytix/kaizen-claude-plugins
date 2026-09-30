"""Reusable, non-destructive data quality helpers for pandas DataFrames.

None of these functions modify, clean, or impute data. They only inspect and
report. Cleaning decisions are left to the user and the business context.
"""

import pandas as pd


def missing_value_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Return per-column missing counts and percentages, worst first."""
    counts = df.isna().sum()
    pct = (df.isna().mean() * 100).round(2)
    summary = pd.DataFrame({"missing_count": counts, "missing_pct": pct})
    return summary.sort_values("missing_count", ascending=False)


def duplicate_row_count(df: pd.DataFrame) -> int:
    """Return the number of fully duplicated rows."""
    return int(df.duplicated().sum())


def duplicate_key_count(df: pd.DataFrame, key_columns) -> dict:
    """Summarize duplication on the given key column(s), making the subset relationship explicit.

    `key_columns` may be a single column name or a list of column names.
    Returns counts for: rows sharing a duplicate key, of which how many are
    full-row duplicates vs. key-only duplicates (same key, differing elsewhere).
    """
    if isinstance(key_columns, str):
        key_columns = [key_columns]
    missing = [c for c in key_columns if c not in df.columns]
    if missing:
        raise KeyError(f"Key columns not found in dataframe: {missing}")
    dup_key_rows = int(df.duplicated(subset=key_columns).sum())
    full_dup_rows = int(df.duplicated().sum())
    return {
        "key_columns": list(key_columns),
        "duplicate_key_rows": dup_key_rows,                 # extra rows sharing a key
        "full_row_duplicates": full_dup_rows,               # subset of the above
        "key_only_duplicates": max(dup_key_rows - full_dup_rows, 0),  # same key, differ elsewhere
        "unique_keys": int(df[key_columns].drop_duplicates().shape[0]),
    }


def iqr_outliers(df: pd.DataFrame, column: str, multiplier: float = 1.5) -> dict:
    """Detect numeric outliers in a column using the IQR method.

    Flags outliers for investigation; removes nothing. Note IQR over-flags on
    skewed distributions, so treat the count as a prompt to investigate.
    """
    if column not in df.columns:
        raise KeyError(f"Column not found: {column}")
    series = pd.to_numeric(df[column], errors="coerce")
    if series.notna().sum() == 0:
        return {"column": column, "lower_bound": None, "upper_bound": None,
                "outlier_count": 0, "outlier_indices": [], "note": "no numeric values"}
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - multiplier * iqr, q3 + multiplier * iqr
    mask = (series < lower) | (series > upper)
    return {
        "column": column,
        "lower_bound": lower,
        "upper_bound": upper,
        "outlier_count": int(mask.sum()),
        "outlier_indices": df.index[mask.fillna(False)].tolist(),
    }


def whitespace_check(df: pd.DataFrame) -> dict:
    """Count values in object columns with leading/trailing whitespace."""
    result = {}
    for col in df.select_dtypes(include="object").columns:
        s = df[col].dropna().astype(str)
        has_ws = int((s != s.str.strip()).sum())
        if has_ws:
            result[col] = has_ws
    return result


def inconsistent_category_labels(df: pd.DataFrame, max_cardinality: int = 100) -> dict:
    """Detect categorical labels that collapse to the same value once normalized.

    Normalization = strip + casefold. Reports, per column, the groups of raw
    labels that appear to mean the same thing (e.g., 'US', 'USA ', 'us').
    Does not change anything. Skips high-cardinality (free-text-like) columns.
    """
    result = {}
    for col in df.select_dtypes(include="object").columns:
        s = df[col].dropna().astype(str)
        if s.nunique() > max_cardinality:
            continue
        norm = s.str.strip().str.casefold()
        groups = {}
        for raw, key in zip(s, norm):
            groups.setdefault(key, set()).add(raw)
        collapsing = {k: sorted(v) for k, v in groups.items() if len(v) > 1}
        if collapsing:
            result[col] = collapsing
    return result


def unparseable_dates(df: pd.DataFrame, column: str) -> dict:
    """Count values in a column that fail to parse as dates (non-destructive)."""
    if column not in df.columns:
        raise KeyError(f"Column not found: {column}")
    nonnull = df[column].dropna()
    parsed = pd.to_datetime(nonnull, errors="coerce")
    bad_mask = parsed.isna()
    return {
        "column": column,
        "unparseable_count": int(bad_mask.sum()),
        "examples": nonnull[bad_mask].astype(str).unique()[:5].tolist(),
    }
