# Segmentation Example

A worked example for the segmentation increment.

## Example user request

> Segment these customers into meaningful groups and tell me what each looks like.

## Expected module path

```
Analysis Planning
Data Understanding
Data Quality
Segmentation Analysis
Reporting
Verification Before Completion
```

## Expected behavior

1. **Analysis Planning** — Objective: define interpretable customer segments and profile them. Clarify the basis if essential, otherwise proceed with a transparent default (e.g., income tiers) and log the assumption. Note one row per customer (assumption).

2. **Data Understanding** — `income` and `age` numeric; `monthly_spend` is numeric-stored-as-text; `country` categorical with fragmented labels.

3. **Data Quality (first)** — Surface what would distort segments: the 11 income values of exactly 5,000,000 (suspected sentinels) will form a spurious top segment; `country` labels are fragmented; `monthly_spend` can't be used until parsed. Report these; do not silently clean.

4. **Segmentation Analysis** —
   - Prefer a transparent method first: **income quartiles** via `quantile_segments`, then `segment_profile` for size, share, and per-segment age/income. Flag that the top quartile's *mean* is inflated by the sentinels while its *median* is reasonable — a quality artifact, not a real spread.
   - If clustering is wanted: standardize features (on a copy), use `suggest_k` to look at silhouette across k, and note that on this raw data a 2–3 cluster solution mostly just isolates the 11 sentinel rows — i.e., it's surfacing bad data, not a real segment. Recommend resolving the sentinels first, and **confirm** the feature set / k before presenting clusters as the answer.
   - Choosing to consolidate the country labels, drop the sentinels, or parse spend are judgment calls — show their impact and ask before producing the cleaned segmentation, rather than computing it conditionally.

5. **Reporting** — Describe each segment (size, share, defining traits, metric levels). Method and choices (which column, how many bins) stated for reproducibility. No causal language.

6. **Verification Before Completion** — Confirm: segments traced to script output; sentinel/label caveats explicit; any cleaning was confirmed before the segmented result was produced (not conditional); method and choices disclosed; no supervised modeling implied.

## Key teaching points

- Prefer the simplest segmentation that answers the question; clustering is exploratory, not ground truth.
- Segmentation amplifies data-quality issues — sentinels and fragmented labels create fake segments.
- Bins/features/k are judgment calls; confirm them before the headline result.

## Note on future increments

Time-series description is in this skill; forecasting and predictive modeling are in the modeling skill.
