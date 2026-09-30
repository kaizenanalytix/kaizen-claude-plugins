# Data Transformation Policy

The authoritative rule for when and how this skill may modify data. The principle is **not** "never transform" — many analyses (segmentation, forecasting, modeling, even correlating a currency column stored as text) require it. The principle is: **transform only with consent, always on a copy, never mutating the source, and always logged.**

Three ideas are kept separate: whether a step *transforms* data, whether the user *consented*, and whether it *mutates the original*. The behavior to avoid is the specific combination of transform + no consent + presented as the answer.

## Tier 1 — Inspection & measurement (always allowed, no permission)

Reading, profiling, counting issues, computing statistics on already-valid columns, and *measuring* what a transformation would change (e.g., "excluding these 11 values, the mean would drop to X — shown to quantify impact, not as the answer"). Touches no data. This is the default mode.

## Tier 2 — Analytical transformation (allowed, on a copy, with consent)

Cleaning, type conversion, deduplication, label normalization, imputation, outlier handling, feature engineering — the work that makes most analysis possible.

Rules whenever a Tier 2 step is performed:

1. **Consent.** Either the user explicitly asked ("clean this", "segment by country", "forecast revenue" — which implies the parsing/cleaning it requires), or you proposed the specific step and the user confirmed.
2. **On a copy.** Operate on a derived dataframe (`df_work = df.copy()`); never modify the original dataframe or source file in place.
3. **New artifact.** If you output transformed data, write a **new** file (e.g., `customers_cleaned.csv`); never overwrite the input.
4. **Change log.** Record each change — what, why, and how many rows/values were affected — so it is auditable and reversible.
5. **State it.** Tell the user what was transformed and that the original is intact.

### Mechanical vs. judgment steps (the key distinction within Tier 2)

- **Mechanical / unambiguous / lossless** steps needed to fulfill an explicit request may proceed on the copy with a stated note — e.g., parsing `"$1,234.50"` to a number, stripping whitespace, casting a date string to a datetime.
- **Judgment-based or lossy** steps must be **confirmed before you produce any result that depends on them** — e.g., deciding that `US` / `USA` / `United States` are the same country, choosing which rows are "placeholder" values to drop, picking an imputation method, or removing outliers. Surface them as inferences and ask first; do **not** run the analysis on the judgment-cleaned copy and present its conclusion "conditionally" or "pending sign-off." Computing the finished result and then asking is still presenting an unconfirmed result — ask, wait, then compute.
  - *What you may show before confirmation:* the **impact** of the proposed step, to help the user decide — e.g., "those 11 values move the mean from 87k to 51k," or "these labels collapse to 3 groups of sizes X/Y/Z." That is Tier 1 impact-measurement.
  - *What you must withhold until confirmation:* the actual analytical answer that depends on the judgment call — the test result, the segment comparison, the ranking, the headline conclusion.

When a request cannot be answered without a Tier 2 step you are not yet authorized for, do not proceed silently and do not proceed "conditionally": report on the raw data with caveats, **or** propose the specific step (with its impact) and ask first — then wait for the answer before computing the result.

## Tier 3 — Destructive in place / irreversible (avoid, even when asked)

Overwriting or deleting the original data — overwriting the source file, hard-deleting rows from it, dropping columns from the canonical dataset. Prefer producing a new artifact instead. If a user insists on in-place destruction, confirm explicitly and still default to writing a new file rather than mutating the source.

## Quick reference

| Action | Tier | Default |
|---|---|---|
| Profile, count, measure impact | 1 | Proceed |
| Parse text→number to fulfill a request | 2 (mechanical) | Proceed on copy, state it |
| Consolidate ambiguous labels, drop "placeholder" rows, impute | 2 (judgment) | Ask first, wait, then compute (no conditional results) |
| Clean/dedupe and save output | 2 | New file + change log, original intact |
| Overwrite source file / hard-delete rows | 3 | Avoid; write a new file instead |
