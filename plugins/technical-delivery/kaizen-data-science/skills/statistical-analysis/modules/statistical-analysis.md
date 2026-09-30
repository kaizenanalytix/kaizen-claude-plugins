# Statistical Analysis

Use this module when the user wants to understand **distributions** of variables or **relationships** between them — e.g., "what does the income distribution look like?", "is age related to spend?", "which variables move together?". This is the first statistical increment and covers two sub-areas only:

- **Distribution Analysis**
- **Relationship Discovery**

This module is *descriptive* relationship discovery: it does not run significance tests or report results as confirmatory — that is the (implemented) hypothesis-testing module's job. Segmentation, time-series, and hypothesis testing are now implemented as their own modules; route to them rather than improvising here.

Helpers live in `scripts/statistical_analysis.py` (`distribution_summary`, `numeric_correlations`, `numeric_by_category`, `cramers_v`). All are non-destructive.

## Run data understanding and data quality first

Statistics computed on unclean data are misleading. Before reporting distribution or relationship results, you must have a basic read on quality, because:

- Impossible values distort means, skew, and kurtosis (e.g., an age of 214 or -3 inflates the spread).
- Inconsistent category labels fragment groups (e.g., `US` / `USA` / `United States` split one segment into three), so any "by category" comparison is wrong until the user resolves them.
- Outliers and heavy tails change which correlation method is appropriate.

If these issues are present, **report the statistic with an explicit caveat about how the quality issue affects it**, or note that the result is unreliable until the issue is resolved. Do not silently fix the data to get a cleaner statistic — that violates the non-destructive boundary (data-quality assessment is handled by the data-exploration skill; see `references/data-transformation-policy.md`).

## Distribution Analysis

Describe each relevant numeric column: central tendency (mean, median), spread (std, IQR, min/max), and shape (skew, excess kurtosis, and a plain-language flag). Use `distribution_summary`.

- Report median alongside mean for skewed data; the mean alone misleads.
- Name the shape (approximately symmetric, right/left-skewed, heavy-tailed) and what it implies.
- Treat any normality indicator as a flag, not proof; with large samples, tests reject normality on trivial deviations.
- Only operate on already-numeric columns. If a column is numeric-stored-as-text (e.g., `"$1,234"`), say it needs conversion and ask before analyzing it — do not convert and analyze unprompted.

## Relationship Discovery

Surface associations; never assert causation.

- Numeric–numeric: `numeric_correlations` (Pearson for linear, Spearman for monotonic/rank — prefer Spearman when distributions are skewed or have outliers). Report the coefficient and its strength, and the strongest pairs.
- Numeric–categorical: `numeric_by_category` to compare a numeric across category levels (associative description of group differences).
- Categorical–categorical: `cramers_v` for association strength (0–1).

Behavior:

- **Correlation is not causation.** State relationships associatively ("X is associated with Y"), and note confounding is possible.
- A correlation near zero means no *linear/monotonic* relationship was detected — not that the variables are unrelated (a non-linear relationship can hide).
- Report effect size / strength, not just whether something is "significant." Strength matters more than a threshold.
- Watch for spurious relationships driven by outliers or a few extreme rows; cross-check against the distribution shape.

## Suitability checks

Before running, confirm: enough non-null rows; at least two numeric columns for correlation; low-cardinality categoricals for group comparisons and Cramér's V. If the data can't support the analysis, say so plainly rather than producing a fragile number.
