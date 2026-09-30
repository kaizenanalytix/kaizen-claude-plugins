# Forecasting

Use this module when the user wants to **predict future values of a time series** — the "what comes next" question. It builds on `modules/modeling-foundation.md` (time-aware evaluation) and on descriptive time-series findings (trend/seasonality/stationarity, which inform model choice — produced by the statistical-analysis skill's time-series capability). Establish those descriptive findings first.

Helpers live in `scripts/forecasting.py` (`build_series`, `backtest`, `forecast`, plus naive/seasonal-naive/drift baselines). ARIMA/SARIMAX and Holt-Winters use statsmodels if present; Prophet uses the prophet package if present; naive baselines are always available. Missing libraries degrade to a clear note.

## Scope change: forecasting is now available — but guarded

Earlier the skill **declined to forecast** because the capability did not exist. That has changed: this module forecasts. It does **not** lift the discipline behind the old refusal — it channels it. The previous instinct ("don't eyeball a line forward and call it a forecast") is exactly right; the difference now is that there is a real method, a real evaluation, and real uncertainty bounds behind any number produced.

So: forecast when asked **and** the data supports it, with the guardrails below. If the data does not support it, decline as before and say why.

## First: can this series actually be forecast?

- There must be a **real time series** — a value measured over many regular periods (the time-series module's "is this a time series at all?" check applies). A single snapshot or an event-count with no signal cannot be forecast.
- There must be **enough history**, especially relative to seasonality: you need several full seasonal cycles to model a seasonal pattern (e.g., 2+ years for monthly seasonality; more is better). With too little history, say so and offer only a naive baseline with heavy caveats.
- Confirm the **frequency, horizon, and seasonal period** with the user — these are judgment calls that shape the result (per the transformation policy). Forecasting far beyond the horizon the history can support is not meaningful.

## Two hard rules

1. **Evaluate with a time-based backtest, never in-sample fit** (`backtest`): fit on the earlier part of the series, predict a held-out tail, and score (MAE/RMSE/MAPE) **against the seasonal-naive baseline**. A model that cannot beat seasonal-naive is not worth its complexity. Report the backtest result before presenting a forward forecast.
2. **Every forecast carries an uncertainty interval** (`forecast` returns 95% bounds for ARIMA/SARIMAX). Intervals **widen with horizon** and assume the past pattern continues. Never present a single point number as if the future were certain; if a method gives no interval (the naive baselines), say so and treat it as indicative only.

## Choosing a method (advise, don't anoint)

See `references/model-catalog.md` for the annotated forecasting menu (when each method fits).


- **Seasonal-naive / naive / drift** — always-available baselines; the bar every model must clear.
- **ARIMA / SARIMAX** (statsmodels) — strong for trend + seasonality; SARIMAX with a seasonal order handles the classic monthly pattern. Stationarity/differencing (from the time-series ADF check) informs the order.
- **Holt-Winters** (exponential smoothing) — robust for trend + seasonal data, often a strong simple competitor.
- **Prophet** — handles trend, multiple seasonalities, and holidays with minimal tuning; useful for business series with calendar effects.

Show the candidates and their backtest scores so the data scientist can choose; when scores are close, prefer the simpler/more interpretable model.

## Honest reporting

- Lead with the **backtest accuracy vs the baseline**, then the forward forecast **with its interval**.
- State the assumptions plainly: the forecast assumes the historical trend/seasonality **persists**; structural change, shocks, or regime shifts will break it, and the interval does not capture those.
- A forecast is **not a causal claim** and not a guarantee — it is a model-based projection with quantified uncertainty under stated assumptions.
- If the history is too short or the backtest can't beat naive, **say the series isn't reliably forecastable** rather than producing a confident-looking number.
