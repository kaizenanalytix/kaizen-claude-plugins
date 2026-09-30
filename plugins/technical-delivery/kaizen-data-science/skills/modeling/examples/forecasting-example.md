# Forecasting Example

A worked example, using the classic monthly airline-passengers series (the `flights` benchmark dataset).

## Example user request

> Forecast passenger numbers for the next 12 months, and tell me how reliable it is.

## Expected module path

```
Analysis Planning
Data Understanding
Data Quality
Time Series Analysis
Modeling Foundation
Forecasting
Reporting
Verification Before Completion
```

## Expected behavior

1. **Confirm forecastability** — 144 monthly points over 12 years, with strong trend and yearly seasonality (from the time-series step). That's ample history (12 cycles) for monthly seasonality, so a forecast is supported. Confirm horizon (12 months) and seasonal period (12).

2. **Build the series** (`build_series`) — combine year + month into a monthly date index; one value per month.

3. **Backtest first, against the baseline** (`backtest`, 12-month holdout):
   - seasonal-naive baseline ≈ MAE 48 / MAPE 10%.
   - SARIMAX ≈ MAE 17 / MAPE 3.8%; Holt-Winters ≈ MAE 13 / MAPE 2.8%.
   - Both clearly beat seasonal-naive, so the model is worth using. Report this *before* the forward forecast.

4. **Forecast with intervals** (`forecast`, h=12, SARIMAX) — point forecast per month **with 95% bounds** that widen with horizon (e.g., early-1961 ≈ 447 [424, 470] rising to a summer peak). Present the interval, not just the point.

5. **Report honestly** — lead with backtest accuracy vs baseline, then the forward forecast with its band. State that it assumes the historical trend and seasonality persist; a shock or regime change would break it and isn't captured by the interval. It's a projection under assumptions, not a guarantee or a causal claim.

6. **Verification** — backtest is time-based (not in-sample); the forecast carries an interval; the model beat the seasonal-naive baseline; horizon/season were confirmed; no certainty implied.

## Contrast: when to still refuse

If the same request came against a single snapshot (e.g., the penguins or mall-customers data) or a flat event series with no signal and little history, the module declines — exactly as the skill did before forecasting existed — and explains that the data can't support a forecast, offering descriptive analysis instead.

## Key teaching points

- Forecasting is now available but guarded: real series + enough history, backtest vs baseline, mandatory intervals.
- Beating the seasonal-naive baseline is the bar; report backtest accuracy before the forward number.
- A forecast assumes the past pattern continues; state that, and never present a point without its uncertainty.

## Note on scope

The full planned hierarchy is now implemented; the skill should not imply out-of-scope techniques were used.
