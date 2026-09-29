# Time Series Example

A worked example for the time-series increment.

## Example user request

> Are customer signups trending up over time, and is there any seasonality?

## Expected module path

```
Analysis Planning
Data Understanding
Data Quality
Time Series Analysis
Reporting
Verification Before Completion
```

## Expected behavior

1. **Analysis Planning** — Objective: describe the signup trend over time and check for seasonality. Note this is descriptive, not a forecast.

2. **Data Understanding** — `signup_date` is the only time field; there is one row per customer. So the natural series is **signups counted per period** (an event series), not a metric trajectory — state this.

3. **Data Quality (first)** — 15 `signup_date` values are unparseable and are dropped from the series (reported, not silently). Many records share a date (duplicate timestamps) — expected for event data, not an error. Check for missing months in the range.

4. **Time Series Analysis** —
   - `build_series(df, "signup_date", freq="MS")` → ~50 monthly periods spanning 2020-01 to 2024-02, 15 dropped as unparseable.
   - `trend_summary` → slope ≈ 0 (p ≈ 0.90, R² ≈ 0): no meaningful trend; signups are essentially flat, not rising.
   - `seasonality_summary(by="month")` → monthly counts vary only mildly (≈99–145) with no strong, consistent pattern; with ~4 years of data this is suggestive at most.
   - `stationarity_check` → roughly stable mean/variance (ADF if statsmodels is available; otherwise the mean/variance split with a caveat).
   - If the user wanted gaps filled or anomalous months removed, that's a judgment call — show impact and confirm first; don't interpolate silently.

5. **Reporting** — State the series definition (monthly signup counts, 2020–2024, 15 dropped). Conclusion: no upward trend and no strong seasonality. Be explicit that the claim rests on ~50 monthly periods / ~4 cycles. No causal language; no forecast.

6. **Verification Before Completion** — Confirm: results trace to `time_series.py` output; the unparseable-date handling is disclosed; the "event series, not metric trajectory" framing is stated; no forecasting was implied; any gap-filling was confirmed, not silent.

## Key teaching points

- A lone date column on a snapshot supports an event series (counts per period), not a metric trajectory — and never a forecast.
- Distinguish trend from seasonality from noise, and state how many periods/cycles support each claim.
- Resampling is mechanical; interpolation/gap-filling/period-dropping are judgment calls to confirm.

## Note on handoff

This descriptive time-series step feeds the **modeling** skill's forecasting capability. Do not extrapolate within this step and call it a forecast, and do not imply out-of-scope techniques were used.
