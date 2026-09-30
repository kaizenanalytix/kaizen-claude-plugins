"""Non-destructive time-series analysis helpers: build a series, trend, seasonality,
stationarity, simple decomposition, and gap detection.

Read-only: nothing mutates the input dataframe. This is DESCRIPTIVE time-series
analysis — trend, seasonality, stationarity, gaps. It does NOT forecast or project
the future; forecasting (ARIMA/Prophet) is a separate, not-yet-implemented branch.

Dependency-light: pandas + numpy + SciPy. statsmodels is used only if present (for
the ADF stationarity test); otherwise a simpler check is reported instead.
"""

import numpy as np
import pandas as pd

try:
    from scipy import stats as _st
    _HAS_SCIPY = True
except Exception:
    _HAS_SCIPY = False

try:
    from statsmodels.tsa.stattools import adfuller as _adfuller
    _HAS_SM = True
except Exception:
    _HAS_SM = False


def build_series(df, date_col, value_col=None, freq="MS", agg="count"):
    """Aggregate rows into a regular time series. Parses dates (coerce), reports how
    many failed, and resamples to `freq` using `agg`. If value_col is None, counts
    events per period. Aggregation is analysis on a copy; the input df is untouched.

    freq examples: 'D' daily, 'W' weekly, 'MS' month-start, 'QS' quarter, 'YS' year.
    """
    if date_col not in df.columns:
        raise KeyError(f"Column not found: {date_col}")
    dt = pd.to_datetime(df[date_col], errors="coerce")
    n_unparseable = int(dt.isna().sum())
    n_dupe_ts = int(dt[dt.notna()].duplicated().sum())
    work = pd.DataFrame({"_dt": dt})
    if value_col is not None:
        if value_col not in df.columns:
            raise KeyError(f"Column not found: {value_col}")
        work["_v"] = pd.to_numeric(df[value_col], errors="coerce")
    work = work.dropna(subset=["_dt"]).set_index("_dt").sort_index()
    if len(work) == 0:
        return {"note": "no parseable dates", "n_unparseable_dropped": n_unparseable}
    if value_col is None:
        series = work.resample(freq).size()
    else:
        series = getattr(work["_v"].resample(freq), agg)()
    return {
        "freq": freq, "agg": ("count" if value_col is None else agg),
        "n_periods": int(series.shape[0]),
        "date_range": [str(series.index.min().date()), str(series.index.max().date())],
        "n_unparseable_dropped": n_unparseable,
        "n_duplicate_timestamps": n_dupe_ts,
        "series": {str(k.date()): (float(v) if pd.notna(v) else None) for k, v in series.items()},
    }


def _series_from_dict(series_dict):
    s = pd.Series(series_dict, dtype="float64")
    s.index = pd.to_datetime(s.index)
    return s.sort_index()


def trend_summary(series_dict):
    """Linear trend (slope per period), its significance, and a monotonic-trend check."""
    s = _series_from_dict(series_dict).dropna()
    if s.shape[0] < 3:
        return {"note": "need >=3 periods for a trend"}
    t = np.arange(len(s))
    out = {"n_periods": int(len(s))}
    if _HAS_SCIPY:
        lr = _st.linregress(t, s.values)
        rho, rho_p = _st.spearmanr(t, s.values)
        out.update({
            "slope_per_period": round(float(lr.slope), 6),
            "r_squared": round(float(lr.rvalue**2), 4),
            "slope_p_value": round(float(lr.pvalue), 6),
            "direction": "increasing" if lr.slope > 0 else "decreasing" if lr.slope < 0 else "flat",
            "spearman_monotonic": round(float(rho), 4), "spearman_p": round(float(rho_p), 6),
        })
    else:
        out["slope_per_period"] = round(float(np.polyfit(t, s.values, 1)[0]), 6)
    out["start_value"], out["end_value"] = float(s.iloc[0]), float(s.iloc[-1])
    out["note"] = "a time trend is description, not a cause; significance with few periods is weak."
    return out


def seasonality_summary(df, date_col, value_col=None, by="month"):
    """Average level by calendar bucket ('month' or 'dayofweek') to surface periodicity."""
    dt = pd.to_datetime(df[date_col], errors="coerce")
    work = pd.DataFrame({"_dt": dt}).dropna(subset=["_dt"])
    if value_col is not None:
        work["_v"] = pd.to_numeric(df[value_col], errors="coerce")
    if work.empty:
        return {"note": "no parseable dates"}
    key = work["_dt"].dt.month if by == "month" else work["_dt"].dt.dayofweek
    if value_col is None:
        agg = work.groupby(key).size()
        what = "event_count"
    else:
        agg = work.groupby(key)["_v"].mean()
        what = f"mean_{value_col}"
    n_cycles = work["_dt"].dt.to_period("Y").nunique()
    return {"by": by, "measure": what, "by_bucket": {str(k): round(float(v), 4) for k, v in agg.items()},
            "n_years_covered": int(n_cycles),
            "note": "need at least a few full cycles to claim seasonality; fewer is suggestive only."}


def stationarity_check(series_dict):
    """Augmented Dickey-Fuller if statsmodels is present; otherwise a rough mean/variance split."""
    s = _series_from_dict(series_dict).dropna()
    if s.shape[0] < 6:
        return {"note": "need >=6 periods"}
    if _HAS_SM:
        stat, p, *_ = _adfuller(s.values)
        return {"test": "ADF", "statistic": round(float(stat), 4), "p_value": round(float(p), 6),
                "stationary_at_0.05": bool(p < 0.05),
                "note": "low p suggests stationarity (no unit root)."}
    half = len(s) // 2
    a, b = s.iloc[:half], s.iloc[half:]
    return {"test": "rough mean/variance split (statsmodels not installed for ADF)",
            "mean_first_half": round(float(a.mean()), 4), "mean_second_half": round(float(b.mean()), 4),
            "var_first_half": round(float(a.var()), 4), "var_second_half": round(float(b.var()), 4),
            "note": "large differences between halves suggest non-stationarity; install statsmodels for a formal ADF test."}


def decompose(series_dict, period):
    """Simple additive decomposition (trend=centered rolling mean, seasonal, residual).

    No statsmodels needed. Returns summaries of each component, not full arrays.
    """
    s = _series_from_dict(series_dict)
    if s.shape[0] < 2 * period:
        return {"note": f"need >= 2*period ({2*period}) points to decompose"}
    trend = s.rolling(window=period, center=True, min_periods=period).mean()
    detrended = s - trend
    seasonal_idx = detrended.groupby(np.arange(len(s)) % period).mean()
    seasonal = pd.Series([seasonal_idx[i % period] for i in range(len(s))], index=s.index)
    resid = s - trend - seasonal
    return {"period": period,
            "trend_direction": "increasing" if trend.dropna().iloc[-1] > trend.dropna().iloc[0] else "decreasing",
            "seasonal_amplitude": round(float(seasonal.max() - seasonal.min()), 4),
            "residual_std": round(float(resid.std()), 4),
            "note": "additive decomposition; treat as exploratory, not a model."}


def detect_time_gaps(df, date_col, freq="MS"):
    """Report unparseable dates, duplicate timestamps, and missing periods in the range."""
    dt = pd.to_datetime(df[date_col], errors="coerce")
    n_bad = int(dt.isna().sum())
    valid = dt.dropna().sort_values()
    if valid.empty:
        return {"note": "no parseable dates", "n_unparseable": n_bad}
    full = pd.date_range(valid.min(), valid.max(), freq=freq)
    present = set(valid.dt.to_period(freq[0]).astype(str))
    expected = set(pd.Series(full).dt.to_period(freq[0]).astype(str))
    missing = sorted(expected - present)
    return {"freq": freq, "n_unparseable": n_bad,
            "n_duplicate_timestamps": int(valid.duplicated().sum()),
            "date_range": [str(valid.min().date()), str(valid.max().date())],
            "n_expected_periods": len(expected), "n_missing_periods": len(missing),
            "missing_periods_sample": missing[:10]}
