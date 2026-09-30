"""Non-destructive segmentation helpers: rule/quantile segments, profiling, and
optional exploratory k-means clustering.

Read-only: nothing mutates the input dataframe. Segment label assignments are
returned as new objects aligned to the index; the caller decides what to do with
them. Segmentation is descriptive — segments are constructs, not ground truth, and
not causal. Clustering is exploratory and requires scikit-learn; if it is absent the
clustering helpers return an error dict instead of crashing.

This is UNSUPERVISED / descriptive segmentation. Supervised predictive modeling
(classifiers, XGBoost, etc.) is a separate, not-yet-implemented branch.
"""

import numpy as np
import pandas as pd

try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    _HAS_SKLEARN = True
except Exception:
    _HAS_SKLEARN = False

_NO_SKLEARN = {"error": "scikit-learn is required for clustering but is not installed."}


def quantile_segments(df: pd.DataFrame, column: str, q: int = 4, labels=None) -> dict:
    """Assign quantile-based segments for a numeric column (e.g., income quartiles).

    Returns the label Series (aligned to df.index), the bin edges, and counts.
    Does not modify df. Refuses non-numeric columns rather than converting them.
    """
    if column not in df.columns:
        raise KeyError(f"Column not found: {column}")
    if not pd.api.types.is_numeric_dtype(df[column]):
        return {"note": f"{column} is not numeric; conversion needed before segmenting (see transformation policy)"}
    s = df[column]
    try:
        seg, edges = pd.qcut(s, q=q, labels=labels, duplicates="drop", retbins=True)
    except ValueError as e:
        return {"note": f"could not form {q} quantiles: {e}"}
    return {
        "method": f"{q}-quantile on {column}",
        "labels": seg.astype("object"),
        "bin_edges": [float(x) for x in edges],
        "counts": seg.value_counts(dropna=False).sort_index().to_dict(),
    }


def segment_profile(df: pd.DataFrame, by, metrics=None) -> dict:
    """Profile segments: size, share, and mean/median of numeric metrics per segment.

    `by` is either a column name or a label Series aligned to df.index.
    `metrics` defaults to all numeric columns. Non-destructive.
    """
    if isinstance(by, str):
        if by not in df.columns:
            raise KeyError(f"Column not found: {by}")
        seg = df[by]
        seg_name = by
    else:
        seg = pd.Series(by, index=df.index)
        seg_name = getattr(by, "name", None) or "segment"
    if metrics is None:
        metrics = df.select_dtypes(include="number").columns.tolist()
    else:
        metrics = [m for m in metrics if m in df.columns and pd.api.types.is_numeric_dtype(df[m])]

    n = len(df)
    out = {}
    for level, idx in df.groupby(seg).groups.items():
        sub = df.loc[idx]
        rec = {"count": int(len(sub)), "share_pct": round(100 * len(sub) / n, 2) if n else 0.0}
        for m in metrics:
            vals = pd.to_numeric(sub[m], errors="coerce").dropna()
            if len(vals):
                rec[f"{m}_mean"] = round(float(vals.mean()), 4)
                rec[f"{m}_median"] = round(float(vals.median()), 4)
        out[str(level)] = rec
    return {"segmented_by": seg_name, "n_segments": len(out), "metrics": metrics, "profile": out}


def suggest_k(df: pd.DataFrame, feature_cols, k_range=(2, 6), scale: bool = True) -> dict:
    """Silhouette score across candidate k values to guide cluster-count choice (exploratory)."""
    if not _HAS_SKLEARN:
        return dict(_NO_SKLEARN)
    X = _prep_features(df, feature_cols, scale)
    if isinstance(X, dict):
        return X
    scores = {}
    lo, hi = k_range
    for k in range(max(2, lo), hi + 1):
        if k >= len(X):
            break
        km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(X)
        if np.unique(km.labels_).size < 2:
            continue  # degenerate (e.g., duplicate/constant points); silhouette undefined
        scores[k] = round(float(silhouette_score(X, km.labels_)), 4)
    if not scores:
        return {"note": "could not form well-separated clusters (features may be constant or duplicated)"}
    return {"silhouette_by_k": scores,
            "note": "higher silhouette = better separation, but choose k for interpretability too, not the score alone."}


def kmeans_segments(df: pd.DataFrame, feature_cols, k: int, scale: bool = True) -> dict:
    """Exploratory k-means clustering on selected numeric features.

    Features are standardized on a COPY (the input df is untouched). Returns labels,
    cluster sizes, per-cluster feature means (in original units), inertia, and
    silhouette. Clusters depend on the chosen features, scaling, and k — treat as
    exploratory, not ground truth.
    """
    if not _HAS_SKLEARN:
        return dict(_NO_SKLEARN)
    X = _prep_features(df, feature_cols, scale)
    if isinstance(X, dict):
        return X
    if k < 2 or k >= len(X):
        return {"note": f"k must be >=2 and < n_samples ({len(X)})"}
    km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(X)
    if np.unique(km.labels_).size < 2:
        return {"note": "features produced a single cluster (constant or duplicated values); cannot segment meaningfully"}
    labels = pd.Series(km.labels_, index=_valid_index(df, feature_cols), name="cluster")
    raw = df.loc[labels.index, feature_cols].apply(pd.to_numeric, errors="coerce")
    centers = raw.groupby(labels.values).mean().round(4)
    return {
        "method": f"k-means (k={k}, scaled={scale})",
        "features": list(feature_cols),
        "labels": labels,
        "cluster_sizes": labels.value_counts().sort_index().to_dict(),
        "cluster_feature_means": centers.to_dict("index"),
        "inertia": round(float(km.inertia_), 4),
        "silhouette": round(float(silhouette_score(X, km.labels_)), 4),
        "caveat": "Exploratory: cluster count, feature choice, and scaling are judgment calls; clusters are not ground truth.",
    }


def _valid_index(df, feature_cols):
    sub = df[list(feature_cols)].apply(pd.to_numeric, errors="coerce")
    return sub.dropna().index


def _prep_features(df, feature_cols, scale):
    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise KeyError(f"Columns not found: {missing}")
    sub = df[list(feature_cols)].apply(pd.to_numeric, errors="coerce").dropna()
    if sub.shape[0] < 3 or sub.shape[1] < 1:
        return {"note": "need >=3 rows with all selected numeric features present"}
    X = sub.to_numpy(dtype=float)
    if scale:
        X = StandardScaler().fit_transform(X)
    return X
