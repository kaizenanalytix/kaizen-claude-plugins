# Distribution & Relationship Example

A worked example for the statistical-analysis increment (distribution analysis + relationship discovery).

## Example user request

> Look at the income distribution and tell me whether income is related to age or country.

## Expected module path

```
Analysis Planning
Data Understanding
Data Quality
Statistical Analysis   (distribution + relationship discovery)
Reporting
Verification Before Completion
```

## Expected behavior

1. **Analysis Planning** — Objective: describe income's distribution and test (descriptively) whether it relates to age or country. Note assumption of one row per customer.

2. **Data Understanding** — Confirm `income` and `age` are numeric and `country` is categorical. Flag that `monthly_spend` is numeric-stored-as-text (not used here unless asked).

3. **Data Quality (first)** — Surface issues that would distort the statistics: impossible ages (e.g., -3, 214) inflate age's spread; a cluster of identical extreme incomes skews the distribution; `country` has inconsistent labels (`US` / `USA` / `United States` / `" usa "`) that **fragment any by-country comparison**. Report these as caveats; do **not** silently clean them.

4. **Statistical Analysis** —
   - *Distribution:* income is strongly right-skewed and heavy-tailed, so report the median (~45k) alongside the mean (which the extreme values pull far higher). Name the shape and its implication.
   - *Relationship (income~age):* near-zero correlation — no linear/monotonic relationship detected (prefer Spearman given the skew). State associatively; absence of linear correlation does not rule out a non-linear link.
   - *Relationship (income~country):* compare income across country levels — **but caveat heavily** that the comparison is unreliable until the duplicate country labels are consolidated, because the same country is split across several groups.

5. **Reporting** — Distinguish observed findings from caveats. No causal language.

6. **Verification Before Completion** — Confirm every statistic traces to script output, the skew caveat is stated, the country-label caveat is explicit, no data was transformed without permission, and no hypothesis test or segmentation was implied (neither was requested here — this is descriptive relationship discovery).

## Key teaching point

Statistics on unclean data mislead. The correct behavior is to compute on the data as given, report the numbers, and explicitly caveat how known quality issues affect them — not to quietly clean the data to produce a tidier-looking result.

## Note on future examples

The skill should not imply out-of-scope techniques were used.
