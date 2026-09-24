---
name: elementx-template-fill
description: Populate a Kvantum Element X upload template from a prepared load and append it to the historical consolidated file. Use when data needs putting into the portal's template format, mapping to template columns, appending to a previous quarter's file, or checking against a hand-built reference. Trigger on "fill the Element X template", "map this to the template", "append to the historical file", "does this match what we did by hand". Run after load-validation.
---

# Element X template fill

> **Running the whole load?** Use the `kvantum-prep` skill instead — it drives
> every stage from the registry in one command and diffs the result against the
> maintained template. This skill is for when you need this stage on its own.


The last step before upload. Element X templates are fixed-schema: the header row
must appear exactly as the portal published it, in the same order, and columns the
channel does not use stay present but empty.

So the file is built **from the template spec outward** — start with the full
column list, drop nothing, fill only what the mapping covers. Building it from the
data inward is how a column quietly goes missing and the upload is rejected.

```python
import sys; sys.path.insert(0, "${CLAUDE_PLUGIN_ROOT}/lib")
from kvprep import template_fill as tf
spec = tf.TemplateSpec.load("${CLAUDE_PLUGIN_ROOT}/registry/templates/elementx/ola.json")
result = tf.fill_template(df, spec, mapping=MAPPING, constants={"Market": "US"})
print(result.manifest_text())
result.to_csv("out/OLA_Q226.csv")
```

## Capture the spec, never retype it

```python
spec = tf.spec_from_blank_template(
    "Sample templates in app/OLA.csv", template_id="elementx.ola", label="OLA",
    date_columns={"Week Starting Date": "%m/%d/%Y", "Week Ending Date": "%m/%d/%Y"},
    numeric_columns=["Impressions", "Clicks", "Spend"],
)
spec.save("${CLAUDE_PLUGIN_ROOT}/registry/templates/elementx/ola.json")
```

Column names are taken verbatim, trailing spaces included — the portal's OLA
template really does ship a column called `'Publisher '`, and the upload matches
on the exact string. A spec captured from a blank export cannot get this wrong; a
hand-typed one will.

Re-capture the spec whenever the portal changes a template, and note the date.

## The mapping

`mapping` is `{template_column: source_column}`. Keep it in
`registry/clients/<client>/channels.yaml`, keyed by channel, so the same channel
maps the same way every quarter and the mapping is reviewable as a diff.

Three sources fill a template column:

- **`mapping`** — a source column carries it.
- **`constants`** — the template needs it and the raw file does not carry it
  (`Market = "US"`). A constant is a claim about the data; state each one.
- **`derived`** — computed (`Week` from the week-ending date). Compute it, do not
  hand-fill it.

Everything else stays blank. `result.manifest` records which columns were filled,
which were intentionally blank, and which **source** columns were not carried
across — read that last list before shipping. A dimension the model breaks down by
that appears there is a mapping gap, not a blank column.

`manifest["missing_required"]` must be empty. If it is not, stop.

## Appending to history

```python
combined, report = tf.append_to_history("Templates/Calls_Q424_Q325.csv", new_rows,
                                        out_path="out/Calls_Q424_Q426.csv")
```

The historical file is never modified in place; the combined file is a new
artifact. The report names schema disagreement and any weeks already present in
history rather than silently duplicating them. Pair it with rule KV-C15 in
`load-validation`, which checks the seam itself.

## Proving it against a hand-built quarter

This is the acceptance test for the whole pipeline, and it is worth running before
anyone trusts the automation with a live load:

```python
rep = tf.compare_to_reference(produced, reference,
                              key_cols=["Week Starting Date", "Brand", "Call Type"],
                              value_cols=["Call"])
```

It reports schema differences, rows present on only one side, and per-value drift
with the worst mismatches named. `rep["match"]` is the only claim worth making. If
it is `False`, report the mismatches — do not describe the output as matching
"apart from" something.

## What to report back

The template and channel, rows written, the mapping and constants applied, source
columns not carried across, the append seam, and — when a reference exists — the
comparison verdict. Say where the file is and that it is ready to upload; do not
upload it.
