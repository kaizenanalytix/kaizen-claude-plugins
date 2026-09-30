"""Predictive modeling helpers (regression & classification) built ON TOP of the
modeling foundation. Non-destructive: trains on a leakage-safe pipeline (preprocessing
fit on train only), evaluates on a held-out test set, and never mutates the input.

Offers a curated menu of models so the data scientist can compare and choose:
scikit-learn (linear/regularized, tree ensembles, SVM, KNN), plus XGBoost, LightGBM,
and statsmodels — each used only if installed, otherwise reported as unavailable.

A fitted model shows association/pattern, not causation, and a result is only
trustworthy if the held-out evaluation was actually used. Requires scikit-learn.
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import FunctionTransformer
    from sklearn.model_selection import (cross_val_score, GridSearchCV, RandomizedSearchCV,
                                         StratifiedKFold, KFold, GroupKFold, TimeSeriesSplit)
    from sklearn.linear_model import (LinearRegression, Ridge, Lasso, ElasticNet,
                                       LogisticRegression)
    from sklearn.tree import DecisionTreeRegressor, DecisionTreeClassifier
    from sklearn.ensemble import (RandomForestRegressor, RandomForestClassifier,
                                   ExtraTreesRegressor, ExtraTreesClassifier,
                                   GradientBoostingRegressor, GradientBoostingClassifier,
                                   HistGradientBoostingRegressor, HistGradientBoostingClassifier,
                                   AdaBoostRegressor, AdaBoostClassifier)
    from sklearn.svm import SVR, SVC
    from sklearn.neighbors import KNeighborsRegressor, KNeighborsClassifier
    from sklearn.naive_bayes import GaussianNB
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    from sklearn.neural_network import MLPRegressor, MLPClassifier
    from modeling_foundation import (make_split, build_preprocessor,
                                     regression_metrics, classification_metrics, baseline)
    _HAS_SK = True
except Exception:
    _HAS_SK = False

try:
    from xgboost import XGBRegressor, XGBClassifier
    _HAS_XGB = True
except Exception:
    _HAS_XGB = False

try:
    from lightgbm import LGBMRegressor, LGBMClassifier
    _HAS_LGBM = True
except Exception:
    _HAS_LGBM = False

try:
    import statsmodels.api as sm
    _HAS_SM = True
except Exception:
    _HAS_SM = False

_NO_SK = {"error": "scikit-learn is required but is not installed."}


def infer_task(df, target):
    s = df[target]
    if pd.api.types.is_numeric_dtype(s) and s.nunique() > 15:
        return "regression"
    return "classification"


def _feature_types(df, features):
    num = [c for c in features if pd.api.types.is_numeric_dtype(df[c])]
    cat = [c for c in features if c not in num]
    return num, cat


def _to_dense(X):
    return X.toarray() if hasattr(X, "toarray") else X


# models that cannot consume the preprocessor's sparse one-hot output and need dense input
_DENSE_REQUIRED = {"hist_gradient_boosting", "naive_bayes", "lda"}


def _pipe(pre, est, model_name):
    """Leakage-safe pipeline; inserts a sparse->dense step for models that require dense input
    (e.g. HistGradientBoosting), so the fast large-data learner is usable instead of being dropped."""
    steps = [("pre", pre)]
    if model_name in _DENSE_REQUIRED:
        steps.append(("dense", FunctionTransformer(_to_dense, accept_sparse=True)))
    steps.append(("model", est))
    return Pipeline(steps)


def _factory(name, task):
    reg = {
        "linear": LinearRegression, "ridge": Ridge, "lasso": Lasso, "elasticnet": ElasticNet,
        "decision_tree": lambda: DecisionTreeRegressor(random_state=0),
        "random_forest": lambda: RandomForestRegressor(n_estimators=200, random_state=0, n_jobs=-1),
        "extra_trees": lambda: ExtraTreesRegressor(n_estimators=200, random_state=0, n_jobs=-1),
        "gradient_boosting": lambda: GradientBoostingRegressor(random_state=0),
        "hist_gradient_boosting": lambda: HistGradientBoostingRegressor(random_state=0),
        "adaboost": lambda: AdaBoostRegressor(random_state=0),
        "svm": SVR, "knn": lambda: KNeighborsRegressor(n_jobs=-1),
        "mlp": lambda: MLPRegressor(max_iter=1000, random_state=0),
    }
    clf = {
        "logistic": lambda: LogisticRegression(max_iter=1000),
        "lda": LinearDiscriminantAnalysis, "naive_bayes": GaussianNB,
        "decision_tree": lambda: DecisionTreeClassifier(random_state=0),
        "random_forest": lambda: RandomForestClassifier(n_estimators=200, random_state=0, n_jobs=-1),
        "extra_trees": lambda: ExtraTreesClassifier(n_estimators=200, random_state=0, n_jobs=-1),
        "gradient_boosting": lambda: GradientBoostingClassifier(random_state=0),
        "hist_gradient_boosting": lambda: HistGradientBoostingClassifier(random_state=0),
        "adaboost": lambda: AdaBoostClassifier(random_state=0),
        "svm": lambda: SVC(probability=True), "knn": lambda: KNeighborsClassifier(n_jobs=-1),
        "mlp": lambda: MLPClassifier(max_iter=1000, random_state=0),
    }
    if _HAS_XGB:
        reg["xgboost"] = lambda: XGBRegressor(random_state=0, verbosity=0, n_jobs=-1)
        clf["xgboost"] = lambda: XGBClassifier(random_state=0, verbosity=0, n_jobs=-1)
    if _HAS_LGBM:
        reg["lightgbm"] = lambda: LGBMRegressor(random_state=0, verbose=-1, n_jobs=-1)
        clf["lightgbm"] = lambda: LGBMClassifier(random_state=0, verbose=-1, n_jobs=-1)
    table = reg if task == "regression" else clf
    f = table.get(name)
    if f is None:
        return None
    try:
        return f()
    except TypeError:
        return f


def list_models(task):
    """Available model names for the task, plus which optional libraries are present."""
    base = (["linear", "ridge", "lasso", "elasticnet", "decision_tree", "random_forest",
             "extra_trees", "gradient_boosting", "hist_gradient_boosting", "adaboost",
             "svm", "knn", "mlp"]
            if task == "regression" else
            ["logistic", "lda", "naive_bayes", "decision_tree", "random_forest", "extra_trees",
             "gradient_boosting", "hist_gradient_boosting", "adaboost", "svm", "knn", "mlp"])
    if _HAS_XGB:
        base.append("xgboost")
    if _HAS_LGBM:
        base.append("lightgbm")
    return {"task": task, "available_models": base,
            "optional_libs": {"xgboost": _HAS_XGB, "lightgbm": _HAS_LGBM, "statsmodels": _HAS_SM},
            "note": "menu to choose from; start simple (linear/logistic) + a baseline before reaching for ensembles."}


def train_evaluate(df, target, features, task=None, model="random_forest",
                   test_size=0.2, time_col=None, group_col=None):
    """Fit one model in a leakage-safe pipeline and evaluate on a held-out test set."""
    if not _HAS_SK:
        return dict(_NO_SK)
    for c in [target] + list(features):
        if c not in df.columns:
            raise KeyError(f"Column not found: {c}")
    task = task or infer_task(df, target)
    data = df[[target] + list(features)].dropna(subset=[target]).reset_index(drop=True)
    if len(data) < 20:
        return {"note": "too few complete rows to train/evaluate reliably"}
    est = _factory(model, task)
    if est is None:
        return {"note": f"unknown/unavailable model '{model}' for {task}", **list_models(task)}
    num, cat = _feature_types(data, features)
    pre = build_preprocessor(num, cat)["preprocessor"]
    pipe = _pipe(pre, est, model)
    sp = make_split(data, target=target, test_size=test_size,
                    stratify=(task == "classification"), time_col=time_col, group_col=group_col)
    if "train_idx" not in sp:
        return sp
    Xtr, Xte = data.loc[sp["train_idx"], features], data.loc[sp["test_idx"], features]
    ytr, yte = data.loc[sp["train_idx"], target], data.loc[sp["test_idx"], target]
    pipe.fit(Xtr, ytr)
    pred = pipe.predict(Xte)
    if task == "regression":
        scores = regression_metrics(yte, pred)
    else:
        proba = None
        try:
            proba = pipe.predict_proba(Xte)[:, 1] if len(np.unique(ytr)) == 2 else None
        except Exception:
            pass
        scores = classification_metrics(yte, pred, proba)
    return {"model": model, "task": task, "split": sp["strategy"],
            "n_train": len(ytr), "n_test": len(yte),
            "scores": scores, "baseline": baseline(ytr, yte, task),
            "note": "compare scores to the baseline; a model that doesn't beat it isn't useful."}


def compare_models(df, target, features, task=None, models=None,
                   test_size=0.2, time_col=None, group_col=None):
    """Train/evaluate several candidate models on the same split and rank them."""
    if not _HAS_SK:
        return dict(_NO_SK)
    task = task or infer_task(df, target)
    models = models or list_models(task)["available_models"]
    rows = []
    for m in models:
        r = train_evaluate(df, target, features, task, m, test_size, time_col, group_col)
        if "scores" in r:
            key = "R2" if task == "regression" else "f1"
            rows.append({"model": m, **r["scores"], "_sort": r["scores"].get(key, float("-inf"))})
    rows.sort(key=lambda d: d["_sort"], reverse=True)
    for d in rows:
        d.pop("_sort", None)
    b = baseline(df[target].dropna().iloc[:int(len(df)*0.8)],
                 df[target].dropna().iloc[int(len(df)*0.8):], task) if len(df) > 25 else {}
    return {"task": task, "ranking": rows, "baseline_reference": b,
            "note": "ranking is on the holdout; small gaps between models are often noise — prefer the simpler/interpretable one when close."}


def _cv_splitter(task, cv, df=None, group_col=None, time_col=None):
    if time_col is not None:
        return TimeSeriesSplit(n_splits=cv)
    if group_col is not None:
        return GroupKFold(n_splits=cv)
    return (StratifiedKFold(cv, shuffle=True, random_state=0) if task == "classification"
            else KFold(cv, shuffle=True, random_state=0))


def cross_validate_models(df, target, features, task=None, models=None, cv=5,
                          scoring=None, group_col=None, time_col=None):
    """Rank candidate models by cross-validated score (more robust than a single split).

    Preprocessing is inside the pipeline, so it is fit within each fold (leakage-safe).
    Uses StratifiedKFold (classification) / KFold (regression), or grouped/time-aware CV.
    """
    if not _HAS_SK:
        return dict(_NO_SK)
    task = task or infer_task(df, target)
    models = models or list_models(task)["available_models"]
    scoring = scoring or ("f1_weighted" if task == "classification" else "r2")
    data = df[[target] + list(features)].dropna(subset=[target]).reset_index(drop=True)
    num, cat = _feature_types(data, features)
    splitter = _cv_splitter(task, cv, data, group_col, time_col)
    groups = data[group_col] if group_col is not None else None
    rows = []
    for m in models:
        est = _factory(m, task)
        if est is None:
            continue
        pipe = _pipe(build_preprocessor(num, cat)["preprocessor"], est, m)
        try:
            s = cross_val_score(pipe, data[features], data[target], cv=splitter,
                                scoring=scoring, groups=groups, n_jobs=-1)
            rows.append({"model": m, "cv_mean": round(float(s.mean()), 4),
                         "cv_std": round(float(s.std()), 4), "n_folds": int(len(s))})
        except Exception as e:
            rows.append({"model": m, "error": str(e)[:80]})
    rows.sort(key=lambda d: d.get("cv_mean", float("-inf")), reverse=True)
    return {"task": task, "scoring": scoring, "cv": cv, "ranking": rows,
            "note": "mean +/- std across folds; prefer this over a single split. Overlapping std means the gap is likely noise — pick the simpler model."}


def _default_grid(model, task):
    """Small sensible hyperparameter grids (pipeline-prefixed). {} means nothing to tune."""
    g = {
        "ridge": {"alpha": [0.1, 1.0, 10.0, 100.0]},
        "lasso": {"alpha": [0.001, 0.01, 0.1, 1.0]},
        "elasticnet": {"alpha": [0.001, 0.01, 0.1, 1.0], "l1_ratio": [0.2, 0.5, 0.8]},
        "logistic": {"C": [0.01, 0.1, 1.0, 10.0]},
        "decision_tree": {"max_depth": [3, 5, 10, None], "min_samples_leaf": [1, 5, 20]},
        "random_forest": {"n_estimators": [100, 300], "max_depth": [None, 10, 20]},
        "extra_trees": {"n_estimators": [100, 300], "max_depth": [None, 10, 20]},
        "gradient_boosting": {"learning_rate": [0.03, 0.1], "n_estimators": [100, 300], "max_depth": [2, 3]},
        "hist_gradient_boosting": {"learning_rate": [0.03, 0.1], "max_iter": [100, 300]},
        "adaboost": {"n_estimators": [50, 100, 200], "learning_rate": [0.1, 0.5, 1.0]},
        "svm": {"C": [0.1, 1.0, 10.0], "gamma": ["scale", "auto"]},
        "knn": {"n_neighbors": [3, 5, 11, 21]},
        "mlp": {"alpha": [0.0001, 0.001, 0.01], "hidden_layer_sizes": [(50,), (100,), (50, 50)]},
        "xgboost": {"learning_rate": [0.03, 0.1], "n_estimators": [100, 300], "max_depth": [3, 6]},
        "lightgbm": {"learning_rate": [0.03, 0.1], "n_estimators": [100, 300], "num_leaves": [31, 63]},
    }.get(model, {})
    return {f"model__{k}": v for k, v in g.items()}


def tune_model(df, target, features, task=None, model="random_forest", search="grid",
               param_grid=None, cv=5, n_iter=20, test_size=0.2, scoring=None):
    """Tune hyperparameters by cross-validation, then evaluate the best on a held-out test set.

    Returns the **best hyperparameters**, the cross-validated score, and the honest holdout
    score (tuning never touches the test set). param_grid optional — sensible defaults per model.
    """
    if not _HAS_SK:
        return dict(_NO_SK)
    task = task or infer_task(df, target)
    scoring = scoring or ("f1_weighted" if task == "classification" else "r2")
    data = df[[target] + list(features)].dropna(subset=[target]).reset_index(drop=True)
    if len(data) < 30:
        return {"note": "too few rows to tune and still hold out a test set reliably"}
    est = _factory(model, task)
    if est is None:
        return {"note": f"unavailable model '{model}'"}
    num, cat = _feature_types(data, features)
    pipe = _pipe(build_preprocessor(num, cat)["preprocessor"], est, model)
    grid = param_grid or _default_grid(model, task)
    sp = make_split(data, target=target, test_size=test_size, stratify=(task == "classification"))
    Xtr, Xte = data.loc[sp["train_idx"], features], data.loc[sp["test_idx"], features]
    ytr, yte = data.loc[sp["train_idx"], target], data.loc[sp["test_idx"], target]
    splitter = _cv_splitter(task, cv)
    if not grid:
        pipe.fit(Xtr, ytr)
        scores = (regression_metrics(yte, pipe.predict(Xte)) if task == "regression"
                  else classification_metrics(yte, pipe.predict(Xte)))
        return {"model": model, "tuned": False, "note": f"'{model}' has no standard hyperparameters to tune",
                "holdout_scores": scores, "baseline": baseline(ytr, yte, task)}
    if search == "random":
        srch = RandomizedSearchCV(pipe, grid, n_iter=n_iter, cv=splitter, scoring=scoring,
                                  random_state=0, n_jobs=-1)
    else:
        srch = GridSearchCV(pipe, grid, cv=splitter, scoring=scoring, n_jobs=-1)
    srch.fit(Xtr, ytr)
    best = srch.best_estimator_
    scores = (regression_metrics(yte, best.predict(Xte)) if task == "regression"
              else classification_metrics(yte, best.predict(Xte)))
    best_params = {k.replace("model__", ""): (list(v) if isinstance(v, tuple) else v)
                   for k, v in srch.best_params_.items()}
    return {"model": model, "tuned": True, "search": search, "scoring": scoring,
            "best_params": best_params, "cv_best_score": round(float(srch.best_score_), 4),
            "holdout_scores": scores, "baseline": baseline(ytr, yte, task),
            "note": "best_params chosen by cross-validation on the training data; holdout_scores are on the untouched test set. Report the holdout, not the CV score, as the final number."}


def feature_importance(df, target, features, task=None, model="random_forest"):
    """Fit a model and report feature importances or coefficients, with caveats."""
    if not _HAS_SK:
        return dict(_NO_SK)
    task = task or infer_task(df, target)
    data = df[[target] + list(features)].dropna(subset=[target]).reset_index(drop=True)
    est = _factory(model, task)
    if est is None:
        return {"note": f"unavailable model '{model}'"}
    num, cat = _feature_types(data, features)
    pre = build_preprocessor(num, cat)["preprocessor"]
    pipe = _pipe(pre, est, model).fit(data[features], data[target])
    try:
        names = pipe.named_steps["pre"].get_feature_names_out()
    except Exception:
        names = np.array(features)
    m = pipe.named_steps["model"]
    if hasattr(m, "feature_importances_"):
        vals, kind = m.feature_importances_, "tree importance"
    elif hasattr(m, "coef_"):
        vals, kind = np.ravel(m.coef_), "linear coefficient (standardized inputs)"
    else:
        return {"note": f"model '{model}' exposes no importances/coefficients"}
    imp = sorted(zip([str(n).split("__", 1)[-1] for n in names], [float(v) for v in vals]),
                 key=lambda kv: abs(kv[1]), reverse=True)
    return {"model": model, "kind": kind,
            "importances": [{"feature": n, "value": round(v, 4)} for n, v in imp[:20]],
            "note": "importance/coefficient is associative, not causal; correlated features share/split credit."}


def statsmodels_inference(df, target, features, task=None):
    """Interpretable inference (OLS or Logit) with coefficients, p-values, and CIs.

    Uses statsmodels for the inference use-case (effect estimates, not prediction).
    """
    if not _HAS_SM:
        return {"error": "statsmodels not installed; this is the inference path (coefficients with p-values/CIs)."}
    task = task or infer_task(df, target)
    data = df[[target] + list(features)].dropna().reset_index(drop=True)
    X = pd.get_dummies(data[features], drop_first=True).astype(float)
    X = sm.add_constant(X)
    y = data[target]
    model = sm.OLS(y, X).fit() if task == "regression" else sm.Logit(y, X).fit(disp=0)
    params, p, ci = model.params, model.pvalues, model.conf_int()
    out = []
    for name in params.index:
        out.append({"term": str(name), "coef": round(float(params[name]), 4),
                    "p_value": round(float(p[name]), 4),
                    "ci95": [round(float(ci.loc[name, 0]), 4), round(float(ci.loc[name, 1]), 4)]})
    return {"method": "OLS" if task == "regression" else "Logit", "terms": out,
            "note": "inferential estimates; coefficients are associations adjusted for the included terms, not proven causes."}
