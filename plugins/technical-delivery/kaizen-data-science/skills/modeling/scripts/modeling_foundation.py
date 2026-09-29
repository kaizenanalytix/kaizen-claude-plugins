"""Shared, non-destructive modeling foundation helpers: leakage checks, proper
splits (random / stratified / grouped / time-aware), task-appropriate metrics,
baselines, and a leakage-safe preprocessing builder.

These support the *workflow* every model family relies on — they do not train or
recommend a specific model. Nothing here mutates the input dataframe. Preprocessing
is built so it is fit on TRAIN ONLY (inside a pipeline), which is the core defense
against data leakage. Requires scikit-learn; if absent, helpers return an error note.
"""

import importlib
import subprocess
import sys

import numpy as np
import pandas as pd

try:
    from sklearn.model_selection import train_test_split, GroupShuffleSplit
    from sklearn.compose import ColumnTransformer
    from sklearn.pipeline import Pipeline
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler, OneHotEncoder
    from sklearn.dummy import DummyRegressor, DummyClassifier
    from sklearn import metrics as _m
    _HAS_SK = True
except Exception:
    _HAS_SK = False

_NO_SK = {"error": "scikit-learn is required but is not installed."}


def ensure_optional(library, attempt_install=True, timeout=900):
    """Make a heavy optional library available, installing on demand if needed.

    Tries to import `library` (e.g. 'xgboost', 'lightgbm', 'pymc'); if missing and
    `attempt_install`, runs pip. Degrades gracefully when there is no network/egress —
    in that case use the always-available scikit-learn equivalent (e.g. the
    'hist_gradient_boosting' model is the closest cousin to LightGBM) and say so.

    Only call this when the user asked for the library or the data is large enough that
    it would meaningfully help — not for marginal gains on small data.
    """
    try:
        importlib.import_module(library)
        return {"library": library, "available": True, "installed_now": False}
    except Exception:
        pass
    if not attempt_install:
        return {"library": library, "available": False, "installed_now": False,
                "note": "not installed and install not attempted; use the scikit-learn equivalent."}
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", library, "--break-system-packages", "-q"],
                       check=True, capture_output=True, timeout=timeout)
        importlib.import_module(library)
        return {"library": library, "available": True, "installed_now": True,
                "note": f"installed {library} on demand."}
    except Exception:
        return {"library": library, "available": False, "installed_now": False,
                "note": f"could not install {library} (likely no network egress in this environment). "
                        f"Fall back to the scikit-learn equivalent (e.g. hist_gradient_boosting for boosting) and tell the user."}


def check_target_leakage(df: pd.DataFrame, target: str, threshold: float = 0.98) -> dict:
    """Flag features that almost perfectly determine the target (likely leakage).

    Catches duplicate-encodings of the target (e.g. an 'alive' column that mirrors
    'survived') and near-perfect single-feature predictors. Reports, never drops.
    """
    if target not in df.columns:
        raise KeyError(f"Target not found: {target}")
    y = df[target]
    suspects = []
    for col in df.columns:
        if col == target:
            continue
        s = df[[col, target]].dropna()
        if s.empty:
            continue
        # categorical/identical encoding: each feature value maps to one target value
        if not pd.api.types.is_numeric_dtype(s[col]) or s[col].nunique() <= 20:
            purity = s.groupby(col)[target].apply(lambda g: g.value_counts(normalize=True).max()).mean()
            if purity >= threshold:
                suspects.append({"feature": col, "type": "near-perfect category->target mapping",
                                 "purity": round(float(purity), 4)})
        # numeric: near-perfect correlation with a numeric target
        if pd.api.types.is_numeric_dtype(s[col]) and pd.api.types.is_numeric_dtype(s[target]):
            r = abs(s[col].corr(s[target]))
            if pd.notna(r) and r >= threshold:
                suspects.append({"feature": col, "type": "near-perfect correlation", "abs_corr": round(float(r), 4)})
    return {"target": target, "n_suspects": len(suspects), "suspects": suspects,
            "note": "suspected leakage — verify each; a feature that encodes the outcome must be excluded, not used."}


def make_split(df, target=None, test_size=0.2, stratify=False,
               time_col=None, group_col=None, random_state=0) -> dict:
    """Produce train/test row indices using the right strategy. Non-destructive.

    - time_col: time-aware split (earliest rows train, latest test) — no shuffling.
    - group_col: grouped split (no group appears in both sets) — prevents group leakage.
    - stratify + target: class-balanced split for classification.
    - otherwise: random split.
    """
    if not _HAS_SK:
        return dict(_NO_SK)
    n = len(df)
    if n < 5:
        return {"note": "too few rows to split meaningfully"}
    if time_col is not None:
        if time_col not in df.columns:
            raise KeyError(f"time_col not found: {time_col}")
        order = pd.to_datetime(df[time_col], errors="coerce").sort_values().index
        k = int(round(n * (1 - test_size)))
        return {"strategy": "time-aware (no shuffle)", "train_idx": list(order[:k]), "test_idx": list(order[k:]),
                "note": "train = earliest rows, test = latest; never shuffle a temporal split."}
    if group_col is not None:
        if group_col not in df.columns:
            raise KeyError(f"group_col not found: {group_col}")
        gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
        tr, te = next(gss.split(df, groups=df[group_col]))
        return {"strategy": f"grouped on {group_col} (no group in both sets)",
                "train_idx": df.index[tr].tolist(), "test_idx": df.index[te].tolist()}
    strat = df[target] if (stratify and target in (df.columns if hasattr(df, "columns") else [])) else None
    tr, te = train_test_split(df.index, test_size=test_size, random_state=random_state, stratify=strat)
    return {"strategy": "stratified random" if strat is not None else "random",
            "train_idx": list(tr), "test_idx": list(te)}


def regression_metrics(y_true, y_pred) -> dict:
    if not _HAS_SK:
        return dict(_NO_SK)
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    return {"MAE": round(float(_m.mean_absolute_error(y_true, y_pred)), 4),
            "RMSE": round(float(np.sqrt(_m.mean_squared_error(y_true, y_pred))), 4),
            "R2": round(float(_m.r2_score(y_true, y_pred)), 4)}


def classification_metrics(y_true, y_pred, y_proba=None) -> dict:
    if not _HAS_SK:
        return dict(_NO_SK)
    out = {"accuracy": round(float(_m.accuracy_score(y_true, y_pred)), 4),
           "precision": round(float(_m.precision_score(y_true, y_pred, average="weighted", zero_division=0)), 4),
           "recall": round(float(_m.recall_score(y_true, y_pred, average="weighted", zero_division=0)), 4),
           "f1": round(float(_m.f1_score(y_true, y_pred, average="weighted", zero_division=0)), 4)}
    try:
        if y_proba is not None and len(np.unique(y_true)) == 2:
            out["roc_auc"] = round(float(_m.roc_auc_score(y_true, y_proba)), 4)
    except Exception:
        pass
    out["note"] = "with class imbalance, accuracy misleads — read precision/recall/F1 and the base rate."
    return out


def baseline(y_train, y_test, task="regression") -> dict:
    """Naive baseline to beat: mean (regression) or most-frequent class (classification)."""
    if not _HAS_SK:
        return dict(_NO_SK)
    if task == "regression":
        dr = DummyRegressor(strategy="mean").fit(np.zeros((len(y_train), 1)), y_train)
        pred = dr.predict(np.zeros((len(y_test), 1)))
        return {"baseline": "predict mean", **regression_metrics(y_test, pred)}
    dc = DummyClassifier(strategy="most_frequent").fit(np.zeros((len(y_train), 1)), y_train)
    pred = dc.predict(np.zeros((len(y_test), 1)))
    return {"baseline": "predict most-frequent class", **classification_metrics(y_test, pred)}


def build_preprocessor(numeric_cols, categorical_cols) -> dict:
    """Return a leakage-safe sklearn preprocessor (impute+scale numerics, impute+one-hot
    categoricals). Use it INSIDE a Pipeline with the estimator so it is fit on train only.
    """
    if not _HAS_SK:
        return dict(_NO_SK)
    num = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    cat = Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                    ("onehot", OneHotEncoder(handle_unknown="ignore"))])
    pre = ColumnTransformer([("num", num, list(numeric_cols)), ("cat", cat, list(categorical_cols))])
    return {"preprocessor": pre,
            "usage": "Pipeline([('pre', preprocessor), ('model', estimator)]).fit(X_train, y_train) — "
                     "this fits imputation/scaling/encoding on TRAIN only, preventing leakage."}
