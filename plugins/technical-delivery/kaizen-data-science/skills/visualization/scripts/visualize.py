"""Code-generated visualizations for EDA, relationships, time series, and model
diagnostics. Real plots via matplotlib (+ seaborn when available) — never image
generation. Non-destructive: reads data, returns a matplotlib Figure, and optionally
saves a PNG.

Usage patterns:
- Live session: pass `save_path` to get a PNG to present.
- Exported notebook: call the function as a cell's last expression; the returned
  Figure renders inline (works under the Agg backend too).

Be intentional: choose the charts that suit the variable types and the question — do
not produce every possible plot. See references/chart-selection.md.
"""

import importlib
import subprocess
import sys

import matplotlib.pyplot as plt  # global backend left untouched: notebooks render inline via
# %matplotlib inline; file saving goes through an explicit Agg canvas in _save (always non-blank,
# regardless of the active backend) — so we never force a backend at import.
import numpy as np
import pandas as pd

_FIGSIZE = (8, 5)
_DPI = 110


def ensure_seaborn(attempt_install=True):
    """Return the seaborn module if available (installing on demand), else None."""
    try:
        return importlib.import_module("seaborn")
    except Exception:
        if not attempt_install:
            return None
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "seaborn",
                            "--break-system-packages", "-q"], check=True,
                           capture_output=True, timeout=600)
            return importlib.import_module("seaborn")
        except Exception:
            return None


def set_style():
    """Apply a consistent house style (seaborn whitegrid if available)."""
    sns = ensure_seaborn(attempt_install=False)
    if sns is not None:
        sns.set_theme(style="whitegrid", context="notebook")
    else:
        plt.rcParams.update({"axes.grid": True, "grid.alpha": 0.3,
                             "axes.spines.top": False, "axes.spines.right": False})
    plt.rcParams.update({"figure.dpi": _DPI, "figure.autolayout": True})


def _fig(ax=None):
    if ax is None:
        f, ax = plt.subplots(figsize=_FIGSIZE)
        return f, ax
    return ax.figure, ax


def _save(fig, save_path):
    if save_path:
        # render through an explicit Agg canvas so the file is never blank, even if the
        # active backend is interactive (a common cause of blank saved figures)
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        FigureCanvasAgg(fig)
        fig.savefig(save_path, dpi=_DPI, bbox_inches="tight")
        plt.close(fig)  # free memory when saving many charts in one script run
    return fig


# ---------- distributions ----------

def histogram(df, col, bins=30, hue=None, save_path=None, title=None):
    set_style(); f, ax = _fig()
    sns = ensure_seaborn(attempt_install=False)
    if sns is not None:
        sns.histplot(data=df, x=col, hue=hue, bins=bins, kde=True, ax=ax)
    else:
        ax.hist(df[col].dropna(), bins=bins, edgecolor="white")
    ax.set_title(title or f"Distribution of {col}"); ax.set_xlabel(col)
    return _save(f, save_path)


def boxplot(df, col, by=None, save_path=None, title=None):
    set_style(); f, ax = _fig()
    sns = ensure_seaborn(attempt_install=False)
    if by is not None and sns is not None:
        sns.boxplot(data=df, x=by, y=col, ax=ax)
    elif by is not None:
        df.boxplot(column=col, by=by, ax=ax)
    else:
        ax.boxplot(df[col].dropna(), vert=True)
        ax.set_ylabel(col)
    ax.set_title(title or (f"{col} by {by}" if by else f"Boxplot of {col}"))
    return _save(f, save_path)


def violinplot(df, col, by=None, save_path=None, title=None):
    sns = ensure_seaborn()
    if sns is None:
        return boxplot(df, col, by, save_path, title)  # graceful fallback
    set_style(); f, ax = _fig()
    sns.violinplot(data=df, x=by, y=col, ax=ax)
    ax.set_title(title or (f"{col} by {by}" if by else f"Distribution of {col}"))
    return _save(f, save_path)


# ---------- categorical ----------

def countplot(df, col, hue=None, save_path=None, title=None, top=None):
    set_style(); f, ax = _fig()
    order = df[col].value_counts()
    if top:
        order = order.head(top)
    sns = ensure_seaborn(attempt_install=False)
    if sns is not None:
        sns.countplot(data=df[df[col].isin(order.index)], x=col, hue=hue,
                      order=order.index, ax=ax)
    else:
        ax.bar(order.index.astype(str), order.values)
    ax.set_title(title or f"Counts of {col}")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    return _save(f, save_path)


# ---------- relationships ----------

def scatter(df, x, y, hue=None, save_path=None, title=None, alpha=0.5):
    set_style(); f, ax = _fig()
    sns = ensure_seaborn(attempt_install=False)
    if sns is not None:
        sns.scatterplot(data=df, x=x, y=y, hue=hue, alpha=alpha, ax=ax)
    else:
        ax.scatter(df[x], df[y], alpha=alpha)
        ax.set_xlabel(x); ax.set_ylabel(y)
    ax.set_title(title or f"{y} vs {x}")
    return _save(f, save_path)


def correlation_heatmap(df, cols=None, method="spearman", save_path=None, title=None):
    set_style()
    num = df[cols] if cols else df.select_dtypes("number")
    corr = num.corr(method=method)
    f, ax = plt.subplots(figsize=(max(6, len(corr) * 0.7),) * 2)
    sns = ensure_seaborn(attempt_install=False)
    if sns is not None:
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0,
                    square=True, cbar_kws={"shrink": .8}, ax=ax)
    else:
        im = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
        ax.set_xticks(range(len(corr))); ax.set_xticklabels(corr.columns, rotation=45, ha="right")
        ax.set_yticks(range(len(corr))); ax.set_yticklabels(corr.columns)
        f.colorbar(im, shrink=.8)
    ax.set_title(title or f"{method.title()} correlation")
    return _save(f, save_path)


def pairplot(df, cols, hue=None, save_path=None):
    sns = ensure_seaborn()
    if sns is None:
        return correlation_heatmap(df, cols, save_path=save_path)  # fallback
    set_style()
    g = sns.pairplot(df[cols + ([hue] if hue else [])], hue=hue, corner=True)
    if save_path:
        g.figure.savefig(save_path, dpi=_DPI, bbox_inches="tight")
    return g.figure


# ---------- time series ----------

def line_plot(df, time_col, value_col, save_path=None, title=None, rolling=None):
    set_style(); f, ax = _fig()
    d = df[[time_col, value_col]].dropna().sort_values(time_col)
    ax.plot(d[time_col], d[value_col], label=value_col)
    if rolling:
        ax.plot(d[time_col], d[value_col].rolling(rolling).mean(),
                label=f"{rolling}-period rolling mean")
        ax.legend()
    ax.set_title(title or f"{value_col} over time"); ax.set_xlabel(time_col); ax.set_ylabel(value_col)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    return _save(f, save_path)


# ---------- data quality ----------

def missingness_bar(df, save_path=None, title=None):
    set_style(); f, ax = _fig()
    miss = (df.isna().mean() * 100).sort_values(ascending=False)
    miss = miss[miss > 0]
    if len(miss) == 0:
        ax.text(0.5, 0.5, "No missing values", ha="center", va="center")
    else:
        ax.barh(miss.index[::-1], miss.values[::-1])
        ax.set_xlabel("% missing")
    ax.set_title(title or "Missingness by column")
    return _save(f, save_path)


# ---------- model diagnostics ----------

def roc_curve_plot(y_true, y_score, save_path=None, title=None):
    from sklearn.metrics import roc_curve, roc_auc_score
    set_style(); f, ax = _fig()
    fpr, tpr, _ = roc_curve(y_true, y_score)
    ax.plot(fpr, tpr, label=f"AUC = {roc_auc_score(y_true, y_score):.3f}")
    ax.plot([0, 1], [0, 1], "--", color="gray")
    ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
    ax.set_title(title or "ROC curve"); ax.legend()
    return _save(f, save_path)


def pr_curve_plot(y_true, y_score, save_path=None, title=None):
    from sklearn.metrics import precision_recall_curve, average_precision_score
    set_style(); f, ax = _fig()
    p, r, _ = precision_recall_curve(y_true, y_score)
    ax.plot(r, p, label=f"AP = {average_precision_score(y_true, y_score):.3f}")
    ax.set_xlabel("Recall"); ax.set_ylabel("Precision")
    ax.set_title(title or "Precision–Recall curve"); ax.legend()
    return _save(f, save_path)


def confusion_matrix_plot(y_true, y_pred, labels=None, save_path=None, title=None):
    from sklearn.metrics import confusion_matrix
    set_style(); f, ax = _fig()
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    im = ax.imshow(cm, cmap="Blues")
    for (i, j), v in np.ndenumerate(cm):
        ax.text(j, i, str(v), ha="center", va="center")
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual"); ax.set_title(title or "Confusion matrix")
    f.colorbar(im, shrink=.8)
    return _save(f, save_path)


def residual_plot(y_true, y_pred, save_path=None, title=None):
    set_style(); f, ax = _fig()
    resid = np.asarray(y_true) - np.asarray(y_pred)
    ax.scatter(y_pred, resid, alpha=0.5)
    ax.axhline(0, color="gray", linestyle="--")
    ax.set_xlabel("Predicted"); ax.set_ylabel("Residual"); ax.set_title(title or "Residuals vs predicted")
    return _save(f, save_path)


def importance_bar(names, importances, top=15, save_path=None, title=None):
    set_style(); f, ax = _fig()
    s = pd.Series(np.asarray(importances), index=names).sort_values(ascending=False).head(top)
    ax.barh(s.index[::-1], s.values[::-1])
    ax.set_xlabel("Importance"); ax.set_title(title or "Feature importance (associative)")
    return _save(f, save_path)


def forecast_plot(history_index, history_values, fc_index, fc_values,
                  lower=None, upper=None, save_path=None, title=None):
    set_style(); f, ax = _fig()
    ax.plot(history_index, history_values, label="history")
    ax.plot(fc_index, fc_values, label="forecast")
    if lower is not None and upper is not None:
        ax.fill_between(fc_index, lower, upper, alpha=0.2, label="95% interval")
    ax.set_title(title or "Forecast"); ax.legend()
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    return _save(f, save_path)
