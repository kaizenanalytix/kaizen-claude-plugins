---
name: project-export
description: Package the analysis from this conversation into a reproducible Jupyter notebook inside the mandatory Kaizen Analytix data-science project structure. Use this skill when the user asks — at any point after some analysis has been done (data understanding, statistics, and/or modeling) — to "export this as a notebook", "make a reproducible notebook", "create the project", "package this analysis", "turn this into a Jupyter notebook", "give me the project structure", or "let me recreate these values". It produces a single consolidated notebook that re-runs from the raw data to regenerate every reported value and tells the storyline, with the plugin's own helper scripts placed in src/ so the results come from the same vetted code.
---

# Project Export — Reproducible Notebook + Kaizen Structure

Turn whatever analysis happened in this conversation — anywhere from data understanding only, up through statistics and modeling — into a **reproducible** Kaizen Analytix data-science project: one consolidated Jupyter notebook that re-executes from the raw data to regenerate every value, telling the storyline as it goes, inside the mandatory directory structure.

## Core principles

- **Reproducible, not transcribed.** The notebook must *re-run* to produce the numbers — load `data/raw/`, call the helper functions, compute. Do not paste previously-computed values into markdown as if they were outputs. Every figure in the narrative must be produced by a code cell that runs.
- **Use the plugin's own helpers.** Copy the vetted helper modules this skill bundles (`assets/src/`) into the project's `src/` and import them in the notebook, so reproduced values come from the same code that produced them originally — never hand-reimplement a computation.
- **Non-destructive.** `data/raw/` is immutable. Any joins/cleaning write to `data/interim/` or `data/processed/`. Set a fixed random seed so model splits reproduce.
- **Faithful scope.** Reproduce only what actually happened in the conversation. Do not invent analyses, and do not include the "suggested next steps" that were never run as if they were.
- **Verify before delivering** — see the verification step below; this is mandatory.

## Workflow

1. **Ask for the creator's initials** (required for the notebook filename) if the user hasn't given them. Do not guess.
2. **Inventory the session.** List the phases that actually occurred (data understanding, data quality, distributions/relationships, hypothesis tests, segmentation, time series, modeling, etc.), the datasets used, the key transformations (joins, derived columns, filters), and the headline values/findings — the storyline.
3. **Scaffold the structure** with `scripts/scaffold_project.py` → `create_project(root, project_name, description, author=<initials>)`. This creates the entire mandatory tree (see `references/kaizen-project-structure.md`), with `.gitkeep` in empty folders and templated `LICENSE`, `README.md`, `config`, `setup.py`, `src/__init__.py`. The layout is fixed — never alter it.
4. **Stage data and code.**
   - Copy the original data files into `data/raw/` (immutable).
   - Copy the helper modules that were actually used from this skill's `assets/src/` into the project's `src/` — profiling/quality/statistics helpers into `src/data/`, modeling helpers into `src/models/`. Copy only what's used.
   - **Visualization:** if the conversation produced **any** charts (the `visualization` skill was used, or plots were shown at any point), you **must** copy `visualize.py` from `assets/src/visualization/` into the project's `src/visualization/`, and reproduce those charts as inline cells in the notebook (step 5). The charts came from a separate skill during the session, but they are part of this project's storyline — don't drop them. (If genuinely no charts were shown and none would help, leave `src/visualization/` empty with its `.gitkeep`.)
   - If the session built a non-trivial analytical table (e.g. multi-table joins), put that code in `src/data/make_dataset.py` so the notebook calls it; small glue can live inline in the notebook.
5. **Build the consolidated notebook** with `scripts/build_notebook.py`, following `references/notebook-style.md` **exactly** — the fixed section order, heading levels, the standard setup cell, narrative-before-code, and the conventions there are mandatory so exports are consistent across analysts. Assemble an ordered cell list:
   - Title + overview (markdown): what the project is, the dataset, the storyline in brief.
   - Setup (code): the standard setup cell from the style guide (imports → add `src/data`, `src/models`, `src/visualization` to `sys.path` → set seed → load raw data from `data/raw/`).
   - For **each phase that occurred**, in the style guide's order: a **markdown** cell telling that part of the story, followed by **code** cells that call the `src` helpers to recompute the values. **Reproduce every chart that was shown during the conversation** (and any that clearly aid the storyline) as an inline cell — `import visualize as viz` and call it with a **trailing semicolon** (e.g. `viz.histogram(df, "price");`) so the figure renders once inline, per `references/notebook-style.md`. The chart images live **inline in the notebook** (the mandatory structure has no figures folder — `src/visualization/visualize.py` holds the plotting code, the notebook holds the rendered charts); re-running the notebook regenerates them.
   - Closing (markdown): limitations and the genuine next steps.
   - Name the file `notebooks/<n>.<m>-<initials>-<short-hyphenated-description>.ipynb` (one consolidated notebook → `1.0-<initials>-<description>`, e.g. `1.0-ab-olist-eda-and-modeling`).
6. **Generate requirements** with `pip-chill > requirements.txt` at the project root (install `pip-chill` if absent). This lists the environment needed to reproduce the analysis.
7. **Verify (mandatory).** Use `build_notebook.build_and_verify` (or `execute_notebook`) to run the notebook end to end. It must execute with **no errors**. Then **reconcile**: confirm the executed outputs match the values reported in the conversation. If a number differs, fix the *code* (or pin the seed), never the narrative; if a value is genuinely seed-dependent, say so. Do not deliver a notebook that didn't run clean. **If a chart cell errors, fix the setup — confirm `src/visualization` is on `sys.path`, `%matplotlib inline` is set, `import visualize as viz` ran, and `viz.ensure_seaborn()` was called — never drop the chart to make the notebook pass.** Every chart shown in the session must survive into the delivered notebook and render on execution.
8. **Deliver** the project folder (and note the notebook path). Briefly state what was reproduced and confirm the verification run passed.

## Notes

- This skill bundles its own copies of the helper modules (`assets/src/`) so the exported project is self-contained and reproduces values from vetted code.
- If the conversation produced no actual computed analysis yet, say so and offer to run an analysis first rather than exporting an empty project.
- Keep the structure exactly as specified in `references/kaizen-project-structure.md` — folders present even when empty.
