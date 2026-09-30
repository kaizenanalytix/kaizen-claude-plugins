# Data Understanding

Use this module when the dataset structure, schema, column meanings, or dataframe profile need to be understood. The goal is to know what you are working with before drawing any conclusions.

## What this covers

- Dataset profiling
- Schema analysis
- Metadata analysis
- Column meaning inference
- Identifying likely numeric, categorical, date/time, identifier, target, and text columns
- Understanding row-level meaning (the unit of analysis)
- Checking whether the dataset appears suitable for the user's requested analysis

## Required checks

Inspect, at minimum:

- Dataframe **shape** (rows × columns)
- **Column names**
- **Data types**
- **Sample rows** when appropriate (e.g., `df.head()`)
- Likely **identifier** columns (high-cardinality keys, IDs)
- Likely **date/time** fields
- Likely **target/outcome** fields, if the task involves an outcome
- **Cardinality** of categorical columns (number of distinct values)
- **Ranges** of numeric columns (min/max, basic spread)
- Obvious **schema issues** (e.g., numbers stored as text, dates stored as strings, mixed types)

`scripts/profile_dataframe.py` produces most of this in one call — use it where helpful. Its output now includes reproducible, clearly-labeled inferences you should prefer over eyeballing:

- `cardinality` — per-column distinct count and unique ratio
- `likely_identifiers` — near-unique, key-like columns (inferred)
- `likely_datetime_columns` — datetime-typed or date-parsing columns (inferred)
- `suspected_numeric_as_text` — object columns that are really numbers (e.g., `"$1,234"`) (inferred)
- `numeric_ranges` — min/max per numeric column (surfaces impossible values like a negative or 200+ age)

Treat every `likely_*` / `suspected_*` field as **inferred, not confirmed**, and say so when you report it.

## Behavior

- Do not assume a column's meaning with certainty unless it was explicitly provided.
- If you infer a column's meaning from its name or data pattern, **label it as inferred**.
- Prefer concise profiling output unless the user asks for a detailed report.
- Use scripts where they improve accuracy, repeatability, or speed.
- After profiling, state plainly whether the dataset appears suitable for what the user asked — and if not, why.
