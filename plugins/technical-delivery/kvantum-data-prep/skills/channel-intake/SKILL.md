---
name: channel-intake
description: Read a raw client data file into a canonical weekly long frame ready for Element X preparation. Use for a raw Kvantum/Element X extract - media or Spark files, Abbott BPM cross-tabs, HCP calls/cases/samples/coupon files - that needs filtering to a period and channel, unpivoting, or converting from monthly to weekly. Trigger on "prep this raw file", "load the Q3 data", "unpivot the BPM file", "convert this to weekly", "filter to the OLA channel". Run before the other step skills.
---

# Channel intake

> **Running the whole load?** Use the `kvantum-prep` skill instead — it drives
> every stage from the registry in one command and diffs the result against the
> maintained template. This skill is for when you need this stage on its own.


The first step of the Kvantum pre-load pipeline: turn whatever the client sent
into one canonical long frame, and record what you learned doing it. Every later
skill in this plugin assumes intake has run.

## Before you start

```python
import sys; sys.path.insert(0, "${CLAUDE_PLUGIN_ROOT}/lib")
from kvprep import intake
from kvprep.calendar_fiscal import build_445_calendar, disaggregate_monthly_to_weekly
```

Never retype a raw file's contents into code. Read it with these helpers so the
numbers in the output provably came from the file.

## Routing by layout

Call `intake.detect_layout(path, sheet)` first. Do not assume.

**`flat_long`** — media / Spark extracts. One row per date × dimension.
`intake.read_flat(path, sheet)` normalises the date columns and infers the grain.
Then:

1. Filter the period the client asked for. State the row count before and after.
2. Filter the channel. In Abbott Spark extracts the channel lives in `Channel`
   (spreadsheet column AM) with a finer `Channel_Detail`; confirm which the
   channel's template keys on rather than guessing.
3. Leave everything else alone. Cleaning belongs to `value-reconciliation`,
   which logs it.

**`bpm_crosstab`** — HCP / BPM extracts. A stacked header block
(`BPM PERIOD / UNITS / FSF / BRAND / HCP / LABEL`) sits above monthly rows keyed
on the first of the month. `intake.read_bpm_crosstab(path, sheet)` unpivots it and
promotes the header block to real dimension columns, so `BRAND`, `FSF` and `HCP`
survive as data. `intake.read_bpm_workbook(path)` does every cross-tab sheet at
once.

Two things to decide explicitly, not silently:

- **TOTAL columns.** `drop_total=True` (the default) drops them. Keep them in a
  separate frame when you intend to run rule KV-C13, which reconciles the
  breakdown back to the client's own TOTAL — that check is the cheapest
  protection against an unpivot that quietly lost a column.
- **Which HCP grain the historical template uses.** Abbott's Ensure acute-care
  calls are consolidated at TOTAL level and labelled `Blank`, while outpatient
  calls keep the specialty breakdown. Read the historical consolidated file and
  match it; do not infer the grain from the raw file alone.

`intake.parse_bpm_filename(path)` recovers the FSF (AC/OP), quarter and brands
from the filename, which is where Kvantum's process genuinely encodes them.

## Monthly to weekly

Only BPM/HCP data needs this; media already arrives weekly.

```python
cal = build_445_calendar("2024-09-29", n_years=1)   # fiscal week grid
weekly, recon = disaggregate_monthly_to_weekly(monthly, cal, value_cols=["Calls"])
```

Read `lib/kvprep/calendar_fiscal.py`'s module docstring before changing anything
here. Three points matter:

1. The grid is a **4-4-5 fiscal calendar of Saturday-ending weeks**, not calendar
   months. Abbott FY2025 starts the week of 2024-09-29.
2. A raw month labelled `2024-10-01` maps to the block that **starts** in the
   previous calendar month (2024-09-29). That one-month offset is real; get it
   wrong and every series is shifted a month.
3. The divisor is the flat constant **4.33**, not the true 4 or 5 weeks in the
   block. This is deliberate: dividing by the true length would make five-week
   fiscal months 25% taller than their neighbours as a pure calendar artefact,
   which an MMM reads as real media pressure. 4.33 conserves the *year*
   (52 / 4.33 = 12.009) at the cost of the individual month.

So a single month will **not** reconciles to its weeks, by design. Report that
from the `recon` frame rather than treating it as a defect, and let rule KV-C14
assert the annual identity. If the user wants exact monthly conservation instead,
pass `divisor=None` — but say plainly that it breaks comparability with every
historical load, and get confirmation first.

When the fiscal year start is unknown, recover the grid from a historical
consolidated file with `intake`-adjacent `infer_calendar_from_reference`.

## What to report back

- Layout detected, sheet(s) read, and the grain.
- Rows in, rows out, and what each filter removed.
- For a cross-tab: how many labelled series were unpivoted, and whether TOTAL
  columns were kept or dropped.
- For a disaggregation: the annual in/out totals and the worst per-period
  difference, with the 4.33 convention named.

Then hand off to **value-reconciliation**. Do not clean values here.
