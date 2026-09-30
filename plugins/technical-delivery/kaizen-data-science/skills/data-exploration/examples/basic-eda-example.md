# Basic EDA Example

A worked example showing how the skill behaves on a typical data quality request. This is illustrative — actual outputs depend on the real dataset.

## Example user request

> Please inspect this customer dataset and tell me if there are any major data quality issues.

## Expected module path

```
Analysis Planning
Data Understanding
Data Quality
Reporting
Verification Before Completion
```

Note that **Statistical Analysis, Forecasting, and Modeling are not used** — the request does not call for them.

## Expected behavior

1. **Analysis Planning** — Identify the objective (assess data quality of a customer dataset), the likely unit of analysis (one row per customer — labeled as an assumption until confirmed), and the expected output (a summary of major quality issues). Note any essential ambiguity; otherwise proceed.

2. **Data Understanding** — Inspect shape, column names, data types, and a few sample rows. Identify likely identifier, date, and categorical columns. Flag obvious schema issues (e.g., dates stored as strings). Confirm the dataset looks like customer-level data.

3. **Data Quality** — Check missing values (counts and percentages), duplicate rows, duplicate customer IDs if an ID column exists, whitespace/formatting issues, inconsistent category labels, invalid values, and numeric outliers via IQR where appropriate. Use `scripts/quality_checks.py` and `scripts/profile_dataframe.py` to make this fast and repeatable.

4. **Reporting** — Summarize the findings at the requested level of detail. Separate observed findings from assumptions. State the impact of each issue on the dataset's usability.

5. **Verification Before Completion** — Confirm every claim is backed by an observed number or output, assumptions (like "one row per customer") are labeled, limitations are disclosed, and no analysis was implied that wasn't actually run.

### Illustrative final answer shape

```
Objective: Assess major data quality issues in the customer dataset.
Data Reviewed: 12,480 rows × 9 columns; one row per customer (assumed).
Methods / Checks Performed: profiling, missingness, duplicate detection, whitespace
  and category-consistency checks, IQR outlier scan on numeric columns.
Key Findings:
  - email missing in 7.2% of rows (901 rows)
  - 38 fully duplicated rows
  - signup_date stored as text, not a date type
  - "country" has inconsistent labels ("US", "USA", "United States")
Assumptions: Unit of analysis is one customer per row.
Limitations: No data dictionary provided; column meanings partly inferred.
Recommendations / Next Steps: Standardize country labels; parse signup_date;
  investigate duplicate rows before any deduplication.
```

## Note on future examples

Segmentation, forecasting, and predictive modeling are handled by the statistical-analysis and modeling skills.
