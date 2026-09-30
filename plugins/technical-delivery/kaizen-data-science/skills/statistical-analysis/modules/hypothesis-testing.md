# Hypothesis Testing

Use this module when the user wants to test a **specific, pre-stated claim** — e.g., "is average spend higher for group A than B?", "is conversion related to channel?", "do these groups differ?". This is confirmatory analysis and is easy to misuse, so the guardrails below are mandatory, not optional.

Helpers live in `scripts/hypothesis_testing.py` (`welch_ttest`, `mann_whitney`, `one_way_anova`, `kruskal_wallis`, `chi_square_independence`, `two_proportion_test`, `p_adjust`). They are non-destructive and require SciPy; if SciPy is unavailable they return an error dict rather than crashing — report that testing is unavailable rather than improvising a p-value.

## Mandatory guardrails

- **State the hypothesis first — in the output.** Write the null (H0) and alternative (H1) explicitly, and fix the significance level (default α = 0.05, two-sided) *before* looking at the result, and **open the response with them** (e.g., "H0: mean income is equal across countries; H1: at least one differs; α = 0.05, two-sided"). Stating H0 only in the conclusion, or omitting α, is not sufficient. Do not adjust α after seeing the p-value.
- **No p-hacking / fishing.** Do not run many tests and report only the significant one. If the user's question implies multiple comparisons (e.g., all pairwise group differences), run them as a set, **correct for multiple comparisons** with `p_adjust` (Benjamini-Hochberg or Bonferroni), and disclose how many tests were run.
- **Report effect size and a confidence interval, not just the p-value.** A p-value answers "is there evidence of *some* effect," not "is the effect *big enough to matter*." With large n, trivial differences become "significant." Always state the effect size (Cohen's d, η², rank-biserial, Cramér's V, risk difference) and interpret its practical size.
- **Check and state assumptions.** Independence, sample size, normality (for parametric tests), equal variance, and expected cell counts (for chi-square). Pick the test accordingly; if assumptions are doubtful, use the non-parametric alternative or caveat the result. Do not present a parametric result whose assumptions clearly fail.
- **Significance is not causation.** A significant test shows an association or group difference, not that one variable causes another. Note plausible confounders.
- **Data quality first, and confirm cleaning before testing.** Sentinels, impossible values, and fragmented category labels invalidate tests. If they are present, the test is unreliable until resolved — say so, and do **not** silently clean the data to run the test. Crucially, do **not** run the test on a judgment-cleaned copy and present the result "conditionally" pending sign-off: ask first, wait, then test. You may show the *impact* of a proposed fix (e.g., "dropping these 11 sentinels moves the mean from 87k to 51k") to help the user decide, but withhold the test conclusion until they confirm. (See `references/data-transformation-policy.md`; data-quality assessment is handled by the data-exploration skill.)
- **An omnibus test does not identify which pair differs.** A significant ANOVA/Kruskal-Wallis means "some groups differ"; pairwise follow-up (with correction) is needed to say which — flag this rather than asserting a specific pair.

## Test selection guide

- **Two groups, compare means:** `welch_ttest` (Welch's, unequal variance by default). If strongly non-normal, ordinal, or small n: `mann_whitney`.
- **More than two groups, compare means:** `one_way_anova`. If normality/variance assumptions are doubtful: `kruskal_wallis`.
- **Two categorical variables, association:** `chi_square_independence` (watch the expected-count warning; if many cells have expected < 5, recommend Fisher's exact instead).
- **Two proportions:** `two_proportion_test`.
- **Many tests at once:** wrap the p-values with `p_adjust`.

This increment does not implement paired tests, regression-based inference, or Bayesian alternatives — do not imply it did. If the user needs those, say they are not yet available.

## Output shape

For each test, report: the hypotheses (H0/H1) and α; the test chosen and why (including assumptions checked); the statistic and p-value; the **effect size and CI**; a plain-language interpretation; and caveats (assumptions, multiple comparisons, data-quality limitations, no-causation). State whether you reject or fail to reject H0 — and remember "fail to reject" is not "proven equal."
