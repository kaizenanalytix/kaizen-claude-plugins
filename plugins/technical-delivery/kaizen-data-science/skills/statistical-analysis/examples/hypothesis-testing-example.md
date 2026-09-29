# Hypothesis Testing Example

A worked example for the hypothesis-testing increment.

## Example user request

> Is average income significantly different between countries?

## Expected module path

```
Analysis Planning
Data Understanding
Data Quality
Hypothesis Testing
Reporting
Verification Before Completion
```

## Expected behavior

1. **Analysis Planning** — State it precisely. H0: mean income is equal across countries. H1: at least one country's mean differs. α = 0.05, two-sided. Note assumption of one row per customer.

2. **Data Understanding** — `income` is numeric; `country` is categorical with 7 labels.

3. **Data Quality (first, and decisive here)** — Two issues make a naive test invalid:
   - `country` has inconsistent labels (`US` / `USA` / `United States` / `" usa "`), so a 7-group test compares spellings, not countries.
   - ~11 income values of exactly 5,000,000 (suspected sentinels) distort group means and violate normality.
   The correct move is to **report this and either test on the data as given with explicit caveats or ask the user to confirm consolidation/sentinel handling first** — not to silently clean and then test.

4. **Hypothesis Testing** — Because income is strongly right-skewed with heavy tails, the parametric ANOVA's normality assumption is doubtful, so prefer **Kruskal-Wallis** (or report ANOVA with a stated caveat and η²). On this data both agree: no significant difference (ANOVA p ≈ 0.89, η² ≈ 0.002 — a negligible effect; Kruskal-Wallis p ≈ 0.69). If the user wanted specific pairwise comparisons, run them as a set and apply `p_adjust` (Benjamini-Hochberg), disclosing the number of tests.

5. **Reporting** — Conclusion: fail to reject H0 — no evidence that income differs by country, and the effect size is negligible even if it did. State that "fail to reject" is not "proven identical." No causal language.

6. **Verification Before Completion** — Confirm: H0/H1 and α were stated up front; effect size and the assumption rationale (why Kruskal-Wallis) are reported; the label-fragmentation and sentinel caveats are explicit; no data was transformed without permission; no test beyond what was implemented was implied.

## Key teaching points

- Report the effect size, not just the p-value — with large n, trivial differences can read as "significant."
- Pick the test by its assumptions; don't default to ANOVA on skewed, outlier-laden data.
- Don't p-hack: if many comparisons are made, correct for them and disclose the count.
- Significance is not causation, and failing to reject is not proof of equality.

## Note on future examples

Forecasting and regression-based prediction are available via the modeling skill.
