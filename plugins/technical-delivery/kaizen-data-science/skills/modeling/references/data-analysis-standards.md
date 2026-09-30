# Data Analysis Standards

Concise conventions that apply across all analysis tasks in this skill.

- **Claims must be evidence-backed.** Every statement about the data should trace to observed data, code output, or user-provided context.
- **Assumptions must be labeled.** If something is inferred rather than known, say so explicitly.
- **Correlation should not be described as causation.** Use associative language unless the analysis design supports a causal claim.
- **Outliers should be investigated before removal.** A flagged outlier may be a data error or a genuine extreme value; treat removal as a decision, not a default.
- **Missing values should be analyzed before imputation.** Understand the pattern and likely cause of missingness before choosing how (or whether) to fill.
- **Dataset context and unit of analysis should be understood before recommendations.** Know what a row represents and what the data covers before advising action.
- **Recommendations should be linked to observed findings.** No recommendation should appear without a finding behind it.
- **Use the smallest sufficient analysis path.** Prefer the minimal set of modules that answers the question.
- **Keep high-impact recommendations human-reviewed.** Decisions with material consequences should be surfaced for human judgment, not asserted as final.
- **Transform only with consent, on a copy, source intact.** Modifying data (cleaning, conversion, dedup, imputation, feature engineering) is allowed when requested or confirmed — performed on a derived copy, logged, written to a new file, never overwriting the source. Confirm lossy/semantic judgment calls before relying on them. See `data-transformation-policy.md`.

## Hypothesis testing standards

- Pre-specify the hypothesis (H0/H1) and significance level before seeing the result; never adjust α post hoc.
- Report an effect size and confidence interval, not just a p-value. Statistical significance is not practical importance.
- Correct for multiple comparisons and disclose how many tests were run; do not report only the significant one.
- State and check test assumptions; use a non-parametric alternative or caveat when they fail.
- A significant result is an association or group difference, not proof of causation.
- "Fail to reject H0" is not "proven no effect" — absence of evidence is not evidence of absence.
