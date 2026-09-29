# Time Series Analysis

Use this module when the user wants to understand how something **behaves over time** — trend, seasonality, cyclicality, stationarity, or gaps in a dated series. Part of the Statistical Analysis group, and the last of its sub-areas.

This is **descriptive** time-series analysis. It does **not** itself forecast — projecting the future is the job of the **modeling** skill's forecasting capability (ARIMA/Prophet), which these trend/seasonality/stationarity findings feed (they inform model choice). Within this descriptive step, do not extrapolate and call it a forecast; if the user wants a forecast, hand off to the modeling skill (and only if the data supports it).

Helpers live in `scripts/time_series.py` (`build_series`, `trend_summary`, `seasonality_summary`, `stationarity_check`, `decompose`, `detect_time_gaps`). All are read-only. They use pandas/NumPy/SciPy; the ADF stationarity test uses statsmodels if present and falls back to a rough mean/variance check with a note if not.

## First: does the data actually support time-series analysis?

A time series needs a **time dimension with repeated observations** — a date/time column plus a value measured across many periods, or datable events to count per period. Check before proceeding:

- A single cross-sectional **snapshot** is not a time series. One row per customer with one value each cannot show a trend over time. The most you can build from a lone date column (e.g., `signup_date`) is an **event series** — counts per period (signups per month) — which is legitimate; say that's what you're doing.
- If the user wants a metric's trajectory (e.g., revenue over time) and the data has no repeated measurement of it over time, state that the data can't support the request, and explain what would be needed (the metric recorded across multiple periods).

This mirrors the honest "this can't be forecast" reasoning: don't manufacture a time axis that isn't there.

## Building the series

Use `build_series(df, date_col, value_col=None, freq=..., agg=...)`. It parses dates (coercing bad ones and reporting how many failed), then resamples to a frequency. Aggregating events/values into periods is analysis on a copy (the source is untouched) — fine to do with the frequency stated. Choosing the **frequency** (daily/weekly/monthly) is a parameter that affects the picture; pick a reasonable default for the span and state it, and offer to change it.

## What to examine

- **Trend** (`trend_summary`): slope per period, its significance, direction, and a monotonic (Spearman) check. A trend is *description*, not a cause; with few periods, significance is weak.
- **Seasonality** (`seasonality_summary`): average level by month or day-of-week. You need at least a few full cycles to claim seasonality; fewer is suggestive only — say which.
- **Stationarity** (`stationarity_check`): ADF if statsmodels is available, otherwise a rough mean/variance split with a clear caveat.
- **Decomposition** (`decompose`): a simple additive trend/seasonal/residual split — exploratory, not a fitted model.
- **Gaps and irregularities** (`detect_time_gaps`): unparseable dates, duplicate timestamps (often expected for event data — many records can share a date), missing periods.

## Data quality and transformation first

- Unparseable dates, duplicate or out-of-order timestamps, and missing periods distort every series statistic — surface them first.
- Resampling to a frequency is mechanical analysis (state the frequency). **Filling gaps / imputing missing periods, dropping anomalous periods, or smoothing are judgment calls** — show their impact and confirm before producing the headline result, per `references/data-transformation-policy.md`. Don't interpolate silently.

## Reporting

State the series definition (date column, value/aggregation, frequency, span, periods). Distinguish trend from seasonality from noise. Be explicit about how many cycles/periods support any seasonality or trend claim. No causal language, and no forecast — describe what happened, not what will happen.
