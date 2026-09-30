# Segmentation Analysis

Use this module when the user wants to **divide the dataset into meaningful groups and profile them** — e.g., "segment customers by spend", "what are the natural customer groups?", "break this down into tiers and compare". Part of the Statistical Analysis group.

This is **unsupervised / descriptive** segmentation. Supervised predictive modeling (classifiers, XGBoost, etc.) is a separate module — route there if the user wants to predict a labeled outcome rather than discover groups.

Helpers live in `scripts/segmentation.py` (`quantile_segments`, `segment_profile`, `suggest_k`, `kmeans_segments`). All are read-only and never modify the input dataframe. Clustering requires scikit-learn; if it is absent the clustering helpers return an error note rather than crashing.

## Three approaches (prefer the simplest that answers the question)

1. **Rule-based** — segments defined by the user's criteria (e.g., "spend > $500 = high value"). Most interpretable; use when the user already has a definition.
2. **Quantile / binning** — split a numeric column into tiers (e.g., income quartiles) with `quantile_segments`. Simple, transparent, reproducible.
3. **Clustering (k-means)** — exploratory, for when groups aren't pre-defined. Use `suggest_k` then `kmeans_segments`. Treat as a starting point, not truth.

In all cases, **profile the segments** with `segment_profile`: size, share, and the distribution of key metrics per segment, so the groups are described, not just labeled.

## Data quality and transformation first

Segmentation amplifies data-quality problems, so resolve or caveat them before reporting segments:

- **Fragmented category labels fragment segments** — `US` / `USA` / `United States` become separate groups. Consolidating them is a judgment call: confirm it before producing the segmented result (see `references/data-transformation-policy.md`), don't merge silently.
- **Sentinels and outliers create fake segments** — clustering will happily isolate a handful of placeholder values (e.g., incomes of exactly 5,000,000) into their own "segment." If a cluster or top bin is dominated by suspected bad values, say so; it is a data-quality artifact, not a real group.
- **Binning and scaling are transformations.** Deriving quantile bins or standardizing features for clustering is a mechanical step done on a copy (the source is untouched) — fine to do with a stated note. But the *choices* — how many bins, which features, how many clusters — are judgment calls; if they materially drive the headline, surface the options and confirm rather than deciding silently.

## Clustering specifics

- **Standardize features** before k-means (done on a copy) so large-scale variables don't dominate.
- **Choose k deliberately.** Use `suggest_k` (silhouette across candidate k) plus the elbow idea, but pick k for **interpretability**, not the score alone — surface 2–3 candidate k values and what each implies rather than asserting one.
- **Report cluster sizes and per-cluster feature means**, and name what distinguishes each cluster in plain language.
- **Caveat instability.** Clusters depend on the chosen features, scaling, and k; a different reasonable choice can give different groups. They are constructs for exploration, not ground truth, and not causal.
- Don't over-interpret tiny clusters — a cluster of a few rows is often noise or bad data.

## Reporting

Describe each segment (size, share, defining characteristics, key metric levels). Distinguish observed segment differences from assumptions and from any cleaning that was confirmed. No causal claims ("this segment spends more" — not "being in this segment causes higher spend"). State the method and its choices (bins / features / k) so the segmentation is reproducible.
