# Kaizen Analytix — Mandatory Data-Science Project Structure

This is the directory structure that must be followed for any data-science project at/by Kaizen Analytix LLC. **It is mandatory and cannot be in any other format.** Reproduce it exactly; `scripts/scaffold_project.py` creates it deterministically.

```
├── LICENSE
├── README.md          <- The top-level README for developers using this project.
├── config             <- Project config file
├── data
│   ├── external       <- Data from third party sources.
│   ├── interim        <- Intermediate data that has been transformed.
│   ├── processed      <- The final, canonical data sets for modeling.
│   └── raw            <- The original, immutable data dump.
│
├── models             <- Trained and serialized models, model predictions, or model summaries
│
├── notebooks          <- Jupyter notebooks. Naming convention is a number (for ordering),
│                         the creator's initials, and a short `-` delimited description, e.g.
│                         `1.0-jqp-initial-data-exploration`.
│
├── scripts
│
├── requirements.txt   <- The requirements file for reproducing the analysis environment, e.g.
│                         generated with `pip freeze > requirements.txt` or `conda list --export > requirements.txt`
│
├── setup.py           <- makes project pip installable (pip install -e .) so src can be imported
├── src                <- Source code for use in this project.
    ├── __init__.py    <- Makes src a Python module
    │
    ├── data           <- Scripts to download or generate data
    │   └── make_dataset.py
    │
    ├── models         <- Scripts to train models and then use trained models to make
    │   │                 predictions
    │   └── train_model.py
    │
    └── visualization  <- Scripts to create exploratory and results oriented visualizations
        └── visualize.py
```

Listing development requirements:

```
pip-chill > requirements.txt
```

## Non-negotiables

- **The folder layout above is mandatory and fixed.** Do not add, rename, or omit folders.
- **Every folder must exist even if empty.** A session may not produce files for every section (e.g. `visualization`), but users may add their own later, so the folder must still be present — preserve empties with a `.gitkeep`.
- The example files shown inside `src/` subfolders (`make_dataset.py`, `train_model.py`, `visualize.py`) are *illustrative*; create them only when the session produced corresponding code. The **folders** are mandatory regardless.
- `config` is a top-level **file** ("Project config file"), not a folder.
- `data/raw/` is the original, **immutable** data dump — never write transformed data there. Transformed/intermediate data goes to `data/interim/`; final modeling datasets to `data/processed/`.
- Requirements are generated with `pip-chill > requirements.txt` (install `pip-chill` if absent).
