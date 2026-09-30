"""Forecasting helpers (ARIMA/SARIMAX, Holt-Winters, Prophet) built on the modeling
foundation and the time-series module.

Non-destructive. Forecasting is prediction over time, so it follows two hard rules:
(1) evaluate with a TIME-BASED backtest (fit on the past, predict a held-out future) —
never in-sample fit; (2) every forecast carries an uncertainty interval, because the
future is uncertain and intervals widen with horizon. Naive/seasonal-naive baselines
are always available (pure pandas); ARIMA/SARIMAX and Holt-Winters use statsmodels if
present; Prophet uses the prophet package if present. Missing libraries degrade to a note.
"""

import numpy as np
import pandas as pd

try:
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    _HAS_SM = True
except Exception:
    _HAS_SM = False

try:
    from prophet import Prophet
    _HAS_PROPHET = True
except Exception:
    _HAS_PROPHET = False


def build_series(df, date_col, value_col, freq="MS", agg="sum"):
    """Construct a regular, sorted time series (DatetimeIndex). Non-destructive."""
    if date_col not in df.columns or value_col not in df.columns:
        raise KeyError("date_col or value_col not found")
    dt = pd.to_datetime(df[date_col], errors="coerce")
    v = pd.to_numeric(df[value_col], errors="coerce")
    s = pd.DataFrame({"dt": dt, "v": v}).dropna().set_index("dt")["v"].sort_index()
    if s.empty:
        return None
    return getattr(s.resample(freq), agg)()


def _to_series(series):
    if isinstance(series, pd.Series):
        s = series.copy()
        s.index = pd.to_datetime(s.index)
        return s.sort_index()
    s = pd.Series(series)
    s.index = pd.to_datetime(s.index)
    return s.sort_index()


def _metrics(actual, pred):
    a, p = np.asarray(actual, float), np.asarray(pred, float)
    mae = float(np.mean(np.abs(a - p)))
    rmse = float(np.sqrt(np.mean((a - p) ** 2)))
    mape = float(np.mean(np.abs((a - p) / np.where(a == 0, np.nan, a))) * 100)
    return {"MAE": round(mae, 4), "RMSE": round(rmse, 4), "MAPE_pct": round(mape, 2)}


def _fit_predict(train, h, model, season, order, seasonal_order):
    """Return (point, lower, upper) arrays of length h for the chosen model."""
    if model == "seasonal_naive":
        if len(train) < season:
            last = float(train.iloc[-1]); return np.full(h, last), None, None
        reps = int(np.ceil(h / season))
        vals = np.tile(train.iloc[-season:].values, reps)[:h]
        return vals, None, None
    if model == "mean":
        return np.full(h, float(train.mean())), None, None
    if model == "naive":
        return np.full(h, float(train.iloc[-1])), None, None
    if model == "drift":
        slope = (train.iloc[-1] - train.iloc[0]) / (len(train) - 1)
        return train.iloc[-1] + slope * np.arange(1, h + 1), None, None
    if model in ("ses", "holt"):
        if not _HAS_SM:
            return None, None, None
        trend = "add" if model == "holt" else None
        res = ExponentialSmoothing(train, trend=trend, seasonal=None).fit()
        return np.asarray(res.forecast(h)), None, None
    if model in ("arima", "sarimax"):
        if not _HAS_SM:
            return None, None, None
        so = seasonal_order if model == "sarimax" else (0, 0, 0, 0)
        res = SARIMAX(train, order=order, seasonal_order=so,
                      enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
        fc = res.get_forecast(steps=h); ci = fc.conf_int()
        return fc.predicted_mean.values, ci.iloc[:, 0].values, ci.iloc[:, 1].values
    if model == "holt_winters":
        if not _HAS_SM:
            return None, None, None
        seasonal = "add" if len(train) >= 2 * season else None
        res = ExponentialSmoothing(train, trend="add",
                                   seasonal=seasonal, seasonal_periods=season).fit()
        return np.asarray(res.forecast(h)), None, None
    return None, None, None


def backtest(series, model="sarimax", h_test=12, season=12,
             order=(1, 1, 1), seasonal_order=(1, 1, 1, 12)):
    """Time-based backtest: fit on all but the last h_test points, predict them, score.

    This is the honest evaluation — never report in-sample fit as forecast accuracy.
    """
    s = _to_series(series)
    if len(s) < h_test + max(season, 3) + 2:
        return {"note": f"series too short for a {h_test}-step backtest"}
    train, test = s.iloc[:-h_test], s.iloc[-h_test:]
    if model in ("arima", "sarimax", "holt_winters") and not _HAS_SM:
        return {"error": "statsmodels not installed for this model; seasonal_naive/naive/drift are available."}
    if model == "prophet" and not _HAS_PROPHET:
        return {"error": "prophet not installed."}
    try:
        point, _, _ = _fit_predict(train, h_test, model, season, order, seasonal_order)
    except Exception as e:
        return {"note": f"{model} failed to fit: {e}"}
    if point is None:
        return {"error": f"{model} unavailable"}
    snaive, _, _ = _fit_predict(train, h_test, "seasonal_naive", season, order, seasonal_order)
    return {"model": model, "h_test": h_test, "n_train": len(train),
            "scores": _metrics(test.values, point),
            "seasonal_naive_baseline": _metrics(test.values, snaive),
            "note": "scores are on a held-out tail; compare to the seasonal-naive baseline. A model that can't beat it isn't worth its complexity."}


def forecast(series, h=12, model="sarimax", season=12,
             order=(1, 1, 1), seasonal_order=(1, 1, 1, 12)):
    """Fit on the full series and forecast h steps ahead WITH an uncertainty interval
    where the model provides one. Always run backtest() first to know if it's any good.
    """
    s = _to_series(series)
    if model in ("arima", "sarimax", "holt_winters") and not _HAS_SM:
        return {"error": "statsmodels not installed; use seasonal_naive/naive/drift or install statsmodels."}
    if model == "prophet" and not _HAS_PROPHET:
        return {"error": "prophet not installed."}
    try:
        point, lo, hi = _fit_predict(s, h, model, season, order, seasonal_order)
    except Exception as e:
        return {"note": f"{model} failed to fit: {e}"}
    if point is None:
        return {"error": f"{model} unavailable"}
    try:
        idx = pd.date_range(s.index[-1], periods=h + 1, freq=pd.infer_freq(s.index))[1:]
        future = [str(d.date()) for d in idx]
    except Exception:
        future = list(range(1, h + 1))
    out = {"model": model, "horizon": h,
           "point": [round(float(v), 4) for v in point],
           "periods": future,
           "has_interval": lo is not None}
    if lo is not None:
        out["lower95"] = [round(float(v), 4) for v in lo]
        out["upper95"] = [round(float(v), 4) for v in hi]
    out["note"] = ("point forecast with 95% interval; intervals widen with horizon and assume the past pattern continues."
                   if lo is not None else
                   "point forecast only (no interval for this method); treat as indicative and prefer a model with intervals for decisions.")
    return out
