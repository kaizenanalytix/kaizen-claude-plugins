# Data Quality

Use this module when checking missing values, duplicates, outliers, consistency, cleanliness, or imputation considerations. The goal is to surface issues that could affect the requested analysis — not to clean the data.

## What this covers

- Missing value analysis
- Duplicate detection
- Outlier investigation
- Consistency checks
- Cleanliness checks
- Imputation strategy — offered as an **optional recommendation, not an automatic action**

## Required checks

Where applicable to the dataset:

- **Missing values** — counts and percentages per column
- **Duplicate rows** — full-row duplicates
- **Duplicate keys** — if key columns are known or inferable
- **Unexpected data types** — e.g., numeric data stored as text
- **Invalid or impossible values** — e.g., negative ages, future birthdates, out-of-range codes
- **Whitespace or formatting issues** — leading/trailing spaces, inconsistent casing
- **Inconsistent category labels** — e.g., "NY" vs "New York" vs "new york"
- **Date parsing issues** — unparseable or ambiguous date formats
- **Numeric outliers** — using a reasonable method such as IQR or z-score when appropriate
- **Potential data leakage indicators** — only relevant if modeling is requested later (e.g., a column that encodes the target)

`scripts/quality_checks.py` provides reusable, non-destructive helpers: `missing_value_summary`, `duplicate_row_count`, `duplicate_key_count` (returns the explicit subset breakdown — duplicate-key rows, of which full-row vs. key-only), `iqr_outliers`, `whitespace_check`, `inconsistent_category_labels`, and `unparseable_dates`.

Note the limit of `inconsistent_category_labels`: it only detects labels that collapse under case/whitespace normalization (e.g., `"USA"` vs `" usa "`). It cannot know that `"US"`, `"USA"`, and `"United States"` are the same place — that is a **semantic** judgment requiring domain knowledge. Flag such suspected synonyms as an inference for the user to confirm, never as an established fact.

## Transformation boundary

Modifying data is governed by the tiered consent model in `references/data-transformation-policy.md`. The short version for data quality work:

- **Default to inspection and measurement** (Tier 1) — count and locate issues, and *measure* what a fix would change, without altering anything. Most quality work lives here.
- **Do not silently clean.** Applying deduplication, label normalization, type conversion (e.g., stripping `$`), imputation, or outlier removal and then reporting results from the cleaned state is only allowed with consent — and then on a **copy**, logged, written to a **new** file, never overwriting the source (Tier 2).
- **Judgment calls need confirmation before any result that uses them.** Treating `US` / `USA` / `United States` as one country, deciding which rows are "placeholder" values to drop, or choosing an imputation method are lossy/semantic judgments — ask first and wait, then compute. Do not run the analysis on the judgment-cleaned copy and present the conclusion "conditionally"; you may show the *impact* of the proposed step to help the user decide, but withhold the dependent result until they confirm.
- **When a request needs cleaning you're not yet authorized for**, either report on the raw data with explicit caveats (e.g., "this count includes 37 duplicate-ID rows, so it overstates unique customers"), or propose the specific steps and ask first. State which path you took. Transparency about a transformation is not a substitute for consent.
- **Measuring impact is fine** (Tier 1): showing "excluding these 11 values the mean would be X" to quantify a problem is allowed, as long as it is labeled as impact-measurement, not presented as the headline result.

## Behavior

- **Do not automatically clean, impute, deduplicate, normalize, or convert data unless the user asks** — and when they do, follow the tiered policy (copy, log, new file, confirm judgment calls).
- Distinguish between **data quality issues** (errors, inconsistencies) and **data characteristics** (legitimate variation). A skewed distribution is a characteristic, not necessarily a problem.
- Outliers should be **flagged for investigation, not automatically removed**.
- Imputation strategies depend on business context and the missingness pattern (MCAR/MAR/MNAR-style reasoning) — present options and tradeoffs rather than silently filling values.
- Always state the **impact** of each data quality issue on the requested analysis. An issue in an irrelevant column matters less than one in a key column.
- **Report counts precisely, making subset relationships explicit.** When categories overlap, do not list them in a way that reads as additive. For duplicates specifically, full-row duplicates are a *subset* of duplicate-key rows — state it as, e.g., "37 rows share a duplicate `customer_id`, of which 25 are full-row duplicates and 12 differ on other fields," not "25 full duplicates and 37 duplicate IDs" (which implies 62).
