# Chart Selection Guide

Choose charts by what you're trying to see, not by habit. Pick the few that earn their place; each should answer a question and carry a one-line takeaway. Functions are in `scripts/visualize.py`.

## By intent

| You want to see… | Variable(s) | Chart | Function |
|---|---|---|---|
| Shape of one numeric variable | 1 numeric | histogram (+ KDE) | `histogram` |
| Spread / outliers of one numeric | 1 numeric | box plot | `boxplot` |
| A numeric compared across groups | 1 numeric × 1 categorical | box or violin by group | `boxplot(by=)`, `violinplot` |
| Relationship between two numerics | 2 numeric | scatter (optional hue) | `scatter` |
| Many pairwise numeric relationships | several numeric | correlation heatmap; pairplot for a small set | `correlation_heatmap`, `pairplot` |
| Frequency of categories / class balance | 1 categorical | count / bar (optionally by hue) | `countplot` |
| Behaviour over time | time + numeric | line plot (+ rolling mean) | `line_plot` |
| Where data is missing | whole frame | missingness bar | `missingness_bar` |
| Classifier quality | y_true, scores | ROC and PR curves | `roc_curve_plot`, `pr_curve_plot` |
| Classifier errors | y_true, y_pred | confusion matrix | `confusion_matrix_plot` |
| Regression fit quality | y_true, y_pred | residuals vs predicted | `residual_plot` |
| What drives predictions | names, importances | importance bar (associative) | `importance_bar` |
| A forecast with uncertainty | history + forecast + interval | forecast plot | `forecast_plot` |

## Intentionality rules

- **Few, well-chosen.** A strong EDA visual pass is typically 3–7 charts, not one per column. Prefer a correlation heatmap over 20 scatterplots; prefer box-by-group over many separate histograms.
- **Match the variable type.** Don't scatter two categoricals (use a count plot / crosstab); don't histogram a high-cardinality ID.
- **Respect skew and scale.** For heavy-tailed monetary variables, a histogram may need a log scale or you lead with the box plot; say so.
- **Imbalanced classification:** lead with the PR curve, not just ROC, and show the confusion matrix at the chosen threshold.
- **Time series:** only plot as a series if there's a real time index; add a rolling mean to reveal trend through noise.
- **Always caption.** Every chart gets a one-line takeaway in the narrative; a chart without a point shouldn't be shown.
