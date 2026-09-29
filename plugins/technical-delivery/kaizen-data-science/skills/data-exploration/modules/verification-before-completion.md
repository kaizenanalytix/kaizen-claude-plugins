# Verification Before Completion

**Mandatory before finalizing any analysis output.** This is a quality gate inspired by evidence-based QA: it exists to catch unsupported claims before they reach the user.

## Purpose

Prevent unsupported claims, overgeneralization, fabricated findings, and conclusions that are not grounded in evidence.

## Required verification checks

Run through each of these before returning your answer:

1. Does each major claim have evidence from data, code output, user-provided context, or cited reference material?
2. Are assumptions clearly labeled as assumptions?
3. Are limitations or missing data disclosed?
4. Are recommendations tied to observed findings?
5. **Every numeric value reported was produced by code actually executed in this session — not estimated, recalled, or computed mentally.** Accuracies, error metrics, p-values, effect sizes, coefficients, credible intervals, forecasts and their intervals, optima, shadow prices, sample sizes, counts, and percentages must all come from running the helper scripts (or other executed code) and must match that output exactly — no rounding drift, no invented or "approximately remembered" numbers. If a figure was not computed by code this session, either run the computation or omit the number; never state a quantitative result you did not actually compute.
6. Are column names, filters, and time periods referenced accurately?
7. Did the analysis answer the user's actual question?
8. Did the workflow avoid irrelevant modules (smallest sufficient path)?
9. Does the response avoid claiming an analysis was performed when it was not actually run? (The full hierarchy is implemented, but a result counts only if the relevant helper was actually executed with proper evaluation/diagnostics/validity checks — never assert metrics, forecasts, posteriors, optima, or experiment outcomes that weren't computed. Techniques a module marks as out of scope must not be implied to exist.)
10. Are caveats included wherever the dataset is insufficient to support a conclusion?
11. **Does every reported figure respect the transformation policy?** Any figure derived from cleaning, deduplication, label normalization, type conversion, imputation, or outlier removal must rest on user consent and have been computed on a copy (source intact). If it relied on a **judgment call** (synonym labels, which rows to drop, imputation choice), that judgment must have been **confirmed before the result was produced** — presenting a judgment-based result "conditionally" or "pending sign-off" does not count and must be removed. Before confirmation you may state the *impact* of a proposed step, but not the finished analytical conclusion. If a result violates this, withhold it, report on raw data with caveats, or ask and wait. (See `references/data-transformation-policy.md`.)

## Required behavior

If a claim cannot be verified, you must do one of:

- **remove it**,
- **qualify it** (state the uncertainty),
- **mark it as an assumption**, or
- **state what additional data is required** to support it.

Do not let an unverifiable claim through unmodified.

## Final response requirements

Where relevant, the final response should include:

- **Findings**
- **Evidence**
- **Assumptions**
- **Limitations**
- **Recommendations or next steps**
