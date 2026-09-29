"""Compact, reproducible profiling for pandas DataFrames.

Pure inspection: nothing here cleans, converts, or modifies data. Type and role
inferences are heuristic and clearly named as "likely_*"/"suspected_*" so callers
treat them as inferred, not confirmed.
"""

import warnings

import pandas as pd

# column-name hints used only to *assist* role inference (never decisive alone)
_ID_HINTS = ("id", "key", "uuid", "guid", "code", "number", "no")
_DATE_HINTS = ("date", "time", "datetime", "timestamp", "_at", "day", "month", "year", "dob")


def _safe_describe(df, include):
    """df.describe(include=...) that returns {} instead of raising when no column matches."""
    try:
        return df.describe(include=include).to_dict()
    except ValueError:
        return {}


def _name_hints(col, hints):
    c = str(col).lower()
    return any(h in c for h in hints)


def _parse_fraction_numeric(s: pd.Series) -> float:
    """Fraction of non-null values that parse as numbers after stripping $ , % and spaces."""
    nn = s.dropna().astype(str).str.strip()
    if nn.empty:
        return 0.0
    cleaned = nn.str.replace(r"[$,%\s]", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce").notna().mean()


def _parse_fraction_datetime(s: pd.Series, sample: int = 1000) -> float:
    """Fraction of a sample of non-null values that parse as dates."""
    nn = s.dropna()
    if nn.empty:
        return 0.0
    if len(nn) > sample:
        nn = nn.sample(sample, random_state=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        parsed = pd.to_datetime(nn, errors="coerce")
    return parsed.notna().mean()


def profile_dataframe(df: pd.DataFrame) -> dict:
    """Return a compact, reproducible profile of a pandas DataFrame."""
    n = len(df)
    cardinality, likely_identifiers, likely_datetime, suspected_numeric_as_text = {}, [], [], []
    numeric_ranges = {}

    for col in df.columns:
        s = df[col]
        nonnull = int(s.notna().sum())
        nunique = int(s.nunique(dropna=True))
        ratio = (nunique / nonnull) if nonnull else 0.0
        cardinality[col] = {"n_unique": nunique, "unique_ratio": round(ratio, 4)}

        # classify role first
        is_numeric = pd.api.types.is_numeric_dtype(s)
        is_datetime = pd.api.types.is_datetime64_any_dtype(s)
        is_text_numeric = False
        if is_numeric:
            mn, mx = s.min(), s.max()
            numeric_ranges[col] = {"min": float(mn) if pd.notna(mn) else None,
                                   "max": float(mx) if pd.notna(mx) else None}
        elif is_datetime:
            likely_datetime.append(col)
        else:  # object / text
            if _parse_fraction_numeric(s) >= 0.9:
                suspected_numeric_as_text.append(col)
                is_text_numeric = True
            elif _name_hints(col, _DATE_HINTS) or _parse_fraction_datetime(s) >= 0.9:
                likely_datetime.append(col)

        # likely identifier: near-unique key-like column. Exclude continuous
        # numerics, text-encoded numbers, and dates (those are values, not keys).
        is_key_like = (not is_numeric) and (not is_datetime) and (not is_text_numeric)
        if nonnull and is_key_like and (ratio >= 0.95 or (_name_hints(col, _ID_HINTS) and ratio >= 0.5)):
            likely_identifiers.append(col)

    return {
        "shape": df.shape,
        "columns": list(df.columns),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "missing_values": df.isna().sum().to_dict(),
        "missing_pct": (df.isna().mean() * 100).round(2).to_dict(),
        "duplicate_rows": int(df.duplicated().sum()),
        "cardinality": cardinality,
        "likely_identifiers": likely_identifiers,            # inferred
        "likely_datetime_columns": likely_datetime,          # inferred
        "suspected_numeric_as_text": suspected_numeric_as_text,  # inferred
        "numeric_ranges": numeric_ranges,
        "numeric_summary": _safe_describe(df, include="number"),
        "categorical_summary": _safe_describe(df, include="object"),
    }
