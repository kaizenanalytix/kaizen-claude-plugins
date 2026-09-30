# Kaizen Notebook Style Guide

The exported notebook's **format is standardized** so that two analysts running similar analyses on the same data produce similarly-shaped notebooks. Follow this exactly when assembling cells. The file structure is already mandatory (see `kaizen-project-structure.md`); this governs the notebook's *internal* style, ordering, and conventions.

## Fixed section order

The consolidated notebook always follows this order; omit a section only if that phase didn't occur, never reorder:

1. **Title & overview** (markdown)
2. **Setup** (code)
3. **Data understanding** (markdown + code) — if done
4. **Data quality** (markdown + code) — if done
5. **Statistical analysis** (markdown + code) — distributions, relationships, hypothesis tests, segmentation, time-series, each as a labeled subsection — if done
6. **Modeling** (markdown + code) — foundation/leakage → baseline → models → evaluation → drivers, in that order — if done
7. **Limitations** (markdown)
8. **Next steps** (markdown)

## Section 1 — Title & overview (one markdown cell)

```
# <Project Title>

**Author:** <initials>  ·  **Generated:** <YYYY-MM-DD>  ·  © <year> Kaizen Analytix LLC — CONFIDENTIAL & PROPRIETARY

## Overview
<2–4 sentences: the dataset, the question(s), and the headline storyline.>

## Contents
<bulleted list of the sections actually included>
```

## Section 2 — Setup (one code cell)

Always this shape, in this order: imports → path wiring → seed → load raw data.

```python
import sys, os
import numpy as np
import pandas as pd
%matplotlib inline   # render charts inline

# make the project's src helpers importable
sys.path.insert(0, os.path.abspath(os.path.join("..", "src", "data")))
sys.path.insert(0, os.path.abspath(os.path.join("..", "src", "models")))
sys.path.insert(0, os.path.abspath(os.path.join("..", "src", "visualization")))

# import the plotting helper and make sure seaborn is ready, so chart cells run cleanly
import visualize as viz
viz.ensure_seaborn()   # installs seaborn on demand if missing (no-op if present)

RANDOM_SEED = 0
np.random.seed(RANDOM_SEED)

RAW = os.path.join("..", "data", "raw")
# load the raw tables, e.g.:
# df = pd.read_csv(os.path.join(RAW, "<file>.csv"))
```

Include the `import visualize as viz` and `viz.ensure_seaborn()` lines **only if the project has charts** (i.e. `src/visualization/visualize.py` was copied in). They make every later chart cell run without import/seaborn errors during verification.

## Cell conventions

- **Heading levels:** `#` only for the title; `##` for sections 3–8; `###` for subsections (e.g. `### Distributions`, `### Hypothesis tests`). Never skip levels.
- **Narrative-before-code:** every code cell is preceded by a markdown cell that says what it does and what to look for. Every result is followed by a one- or two-sentence takeaway in markdown.
- **One idea per code cell.** Keep cells short and focused (load, transform, one analysis, one chart). Don't combine unrelated steps.
- **Call the `src` helpers**, don't reimplement: e.g. `import hypothesis_testing as ht`, `import predictive_modeling as pm`, `import visualize as viz`. Custom data-building (joins, derived columns) goes through `src/data/make_dataset.py` (imported), or a clearly-labeled "Build analytical table" subsection.
- **Transformations are non-destructive:** read from `data/raw/`; write any transformed data to `data/interim/` or `data/processed/`; never modify raw.
- **Print, don't hide:** show the computed values (`print(...)` or a returned DataFrame as the cell's last expression) so the notebook's outputs *are* the evidence.
- **Charts:** call a `viz` function with a **trailing semicolon** (e.g. `viz.histogram(df, "fare");`) so the figure renders **once** inline under `%matplotlib inline` (omitting the semicolon double-renders it). Precede with a markdown line stating the question and follow with the takeaway. Be selective (see the visualization skill's chart-selection guide).
- **Modeling cells**, in fixed order: leakage check → baseline → model(s) via the leakage-safe pipeline → held-out / cross-validated evaluation → drivers (associative). State that importances/coefficients are associations, not causes.
- **Tone of narrative:** concise and factual; lead with the finding, then the number; flag association-not-causation, skew, and small-n where relevant. Mirror the analysis's own reporting voice.

## Closing sections

- **Limitations** (`## Limitations`): bulleted, honest — skew, sample size, unobserved factors, seasonality coverage, generalization bounds; whatever actually applied.
- **Next steps** (`## Next steps`): only genuine, unrun follow-ups — never presented as if already done.

## Determinism

Set the seed in setup and use it for any split/model so re-runs reproduce. If a reported value is inherently seed-dependent, say so in the takeaway rather than implying exactness.
