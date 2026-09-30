---
name: kvantum-prep
description: Prepare a Kvantum Element X load and the data review that goes with it - raw extract(s) plus the maintained template in, load-ready file out, plus ONE document covering every channel — the input summary in the client's own layout, the exploratory analysis, and the load rules. Self-contained HTML and a matching workbook. Trigger on "prep this for Element X", "run the load", "input review", "input summary", "data review", "EDA", "build the Q3 file".
---

# Kvantum prep — the whole load, in one command

Everything the five step-skills do, driven from the registry in the right order,
for one channel or for every channel the given files can feed. Reach for a step
skill when you need one stage in isolation; reach for this one when the job is
"here is the raw data and the template, give me the file".

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/kvantum-prep/scripts/prep_cli.py" run \
  --client abbott-ensure --channel CASES \
  --raw "Raw data from client/Q3 25 AC ENS GLU BPM Inputs.xlsx" \
  --template "Templates/Cases_Q424_Q325.csv" \
  --out out/
```

Per channel you get the load CSV plus `__validation.json`, `__manifest.json`
and `__report.md`. Across the whole run you get **one document**: a
self-contained HTML page and a matching workbook, covering every channel.
Exit code 0 when the gate is loadable, 2 when BLOCKED.

## The deliverable: one document, not a folder of files

`<client>__data_review_input_summary[__<load>].html` is the thing that gets
sent. It is
self-contained — no external requests, opens from an email attachment on a
laptop with no access to anything of ours — and it carries:

- **Overview** — files received, channels, and the short list of what needs
  the client's attention.
- **A tab per channel** — the input summary laid out the way the client's own
  workbook lays it out: which file and which column each series came from,
  weeks running down, period totals with quarter-on-quarter and year-on-year,
  a coverage grid where a week with no row is a visible state rather than an
  empty cell, and one small-multiple panel per series.
- **Data quality** — every check, grouped into Completeness, Consistency,
  Movement and outliers, Seasonality and Reconciliation. Two kinds sit side by
  side in each group: the **load rules**, which decide whether the file can be
  uploaded, and the **data observations**, which are what a person would notice
  reading the numbers. Failures get a card with their evidence; passes collapse
  to one line per rule naming the channels it passed for, because a wall of
  green hides the one failure as effectively as a wall of red.
- **What we need from you** — every open item in one numbered list.

**Two files, one document.** `…__data_review_input_summary.html` and the
matching `.xlsx` — named after their own file, which carries both words:
*Ensure Data Review Input Summary Q226.xlsx*.

There is no separate client and internal rendering, and no separate data
review. The load rules and the exploratory analysis are about the same
figures, and splitting them meant a reader of either one was missing half the
answer: the input summary did not say a conservation rule had failed, and the
data review did not say a publisher had been renamed. Rule IDs and thresholds
are shown rather than hidden — a finding nobody can look up is one they have
to take on trust, and this document is meant to be argued with.

Period totals in the workbook are **formulas over the week rows**, so a
corrected week re-totals rather than going stale.

## The channel tabs: their workbook, generated

The matching `.xlsx` replaces the file their team assembles by hand every
quarter, and the HTML's channel tabs show the same thing. Laid out the way
`Ensure Data Review Input Summary Q226.xlsx` is laid out, because that is the
file they already know how to read:

| Row | What |
|---|---|
| 1 | what the sheet was updated for, and how it was built |
| 2 `File Name` | the extract each column came from |
| 3 `Unit` | Shipments / Bottles / Impressions / Spend |
| 4 (some sheets) | the group row — DMwC / DMwS / PAB |
| 5 `Channel` | the series name |
| 6+ | the grid: months for HCP, week-ending dates for media |
| footer | quarter totals, then QoQ and YoY — as formulas |
| below | derived rates, then the notes and the questions |

Green fill marks what is new this quarter, which is their convention.

**The figures are the client's own, untransformed.** An HCP sheet shows the
monthly numbers as they arrived — before the redemption lag, before the
coupons-per-shipment multiplier, before the 4.33 divisor. This is the rule the
18 Sep walkthrough set: *"we do not show the processed numbers here. We only
show the raw inputs so that client can validate that this is the correct input
that they have shared with us."* What the model actually consumes is on the
**Modelled series** sheet, where it cannot be mistaken for an input.

Beyond the reproduction, on their own sheets so nothing existing shifts:
`Overview`, `Load checks` (every rule, what it checks and what it found),
`Observations`, `Series profile`, `Coverage`, `Derived rates`, `Series that
move together`, `What we need from you` (with a blank response column, and both
the rule asks and the data asks in it), `Change Log`, `Model & Hypothesis` and
`Modelled series`.

```bash
… run --client abbott-ensure --channel all --raw <the extracts> \
      --prior-summary "Input summary/Ensure Data Review Input Summary Q226.xlsx" \
      --infer-raw "some new channel.xlsx" --out out/
```

`--prior-summary` earns its place three times over: it reports which figures
have been **restated** since that file, carries its notes and its change log
forward, and proposes new change-log entries for this quarter. Series are
matched to it **by their values, not their names** — their headings are
hand-written and ours come from the extract, so a name match finds almost
nothing and the restatement check then appears to pass while never running.

`--infer-raw` reads a file no registry channel describes. Those sheets are
marked `inferred` everywhere they appear and say what was guessed. They are
there to get a channel into the conversation, not to be trusted.

## Testing your own coupon redemption table

The one thing Coupon Drops still needs from Kvantum is the real lag table. You
can drop it in and run, without editing anything in the plugin:

```bash
… run --client abbott-ensure --channel COUPON_DROPS \
      --raw <the BPM workbooks> \
      --template "Templates/Coupon_Drops_Q424_Q325.csv" \
      --lag-factors my-lag-table.yaml --out out/
```

Copy `registry/clients/abbott-ensure/lag-factors.EXAMPLE.yaml`, put your
monthly shares in it, and mark each profile `status: supplied`.

**The gate follows the table, not a flag.** Coupon Drops carries
`unverified_until: lag_profiles_confirmed` — the single reason it is gated is
that its profiles were inferred. Supply a table where every profile it uses is
`supplied` and the channel verifies itself: the `__UNVERIFIED` suffix comes off
the filename, the "not yet verified" finding disappears, and the gate becomes
whatever the rules actually say. Supply two of three and it stays gated, which
is the right answer. Nobody edits `channels.yaml`; a status somebody has to
remember to flip gets flipped late, or early.

**What you get back is one line.** The run prints how far your table's output
lands from the file your team built by hand:

```
gate        : BLOCKED (DIFFERS FROM THE MAINTAINED FILE)
  Redemptions: 52,203,986 against 52,074,323 in the maintained file (+0.25%), 555 row(s) differ
```

That is the answer to "does our table reproduce what we do today". An exact
byte match will not happen with any real table — the maintained file carries
its own rounding — so the percentage is the number to read, and the gate says
which of the two things blocked it rather than leaving you hunting the rules
for a failure that is not there. `--rel-tolerance 0.03` accepts a 3% per-cell
difference if that is the agreed bar.

The loader refuses a table in the wrong unit (percentages as whole numbers), a
negative share, a profile summing above 1.5, a profile a series names but the
file does not contain, and a `--lag-factors` path that does not exist — that
last one because running on our inferred profiles while you believe you
supplied your own is the worst outcome available.

## What the EDA looks for

`kvprep/eda.py` runs the pass a person used to do by eye. Every finding states
what was seen, with the numbers, and asks the question that follows — never
the explanation, which is the client's to give.

| Looks for | Why it is worth a sentence |
|---|---|
| a series that **stops** | a channel that ended and a file that did not arrive look identical |
| a series that **starts**, or resumes after a gap | usually a rename; sometimes genuinely new |
| **renames** — one series ending as another begins at the same level | every total still reconciles, so no other check sees it; the model gets two drivers with half the history each |
| **level shifts** — several periods high or low in a row | reported once as a shift, not once per period |
| **outliers** — a period outside the series' own range | must also be at least 1.5x its median, or a steady series reports a 10% wobble |
| **flat runs** — one value repeated | a carried-forward cell rather than a measurement |
| **magnitude shifts** — a clean factor of ten | a unit change, silent because every number still looks plausible |
| **divergence** — series in one family moving opposite ways | the note their analyst writes most often, and no single-series check can produce it |
| **seasonality** — a month that leads most years | so the model treats it as a season rather than a response to spend |
| **rate shifts** — CPM, CPC | the fastest way to catch a unit change that survives every other check |
| **correlation** above 0.85 | two drivers the model cannot tell apart |
| **restatements** against the previous summary | legitimate and common; unannounced ones are not |

Thresholds live in `registry/clients/<id>/summary.yaml`, so quietening a noisy
check is a text edit. Four rules keep the output readable, and each is tested:
one event in two measures is one finding; a fact true of most of a channel is
stated once about the channel; a rename suppresses its own stop and start; and
each group shows its largest few findings with the rest counted and carried in
full in the workbook.

## Saying what a flag means

Every check's client-facing wording lives in
`registry/checks/catalogue.yaml`, not in code — the title, what the check
looks for, why it matters, what we need back, and the mapping from the rule's
own fields to readable column headers. That file is why the report says
"5.7x normal variation, below typical" rather than `robust_z: -5.7`, and
"Quarter beginning 29 Dec 2024" rather than `P2 (2024-12-29)`.

Two behaviours in there worth knowing:

- **Consecutive weeks carrying the same value collapse into one row.** A
  monthly figure spread across a fiscal block gives every week in that block
  the same number, so one unusual month otherwise arrives as five identical
  findings. It is shown once, with its span.
- **A check with no ask is not shown as a finding.** Anything internal —
  a missing template column, the disaggregation arithmetic — is marked
  `internal_only` and never reaches the client rendering.

Editing the wording is a diff to that YAML. Adding a check without an entry
fails the test suite, on purpose: a finding the catalogue does not know about
falls back to the rule's own phrasing, which is what this layer exists to keep
out of a client document.

## The two things to get right

**`--template` is the file the client's team maintains, not the portal's blank
export.** This is the single most expensive mistake available here. The blank
export lists every column Element X will *accept* — 54 for OLA. The maintained
file says which 22 the load actually uses, at what grain, in what order, at
what precision. A load built from the blank export reconciled to the cent on
impressions, clicks and spend while its row count, its column set and six of
its mappings were all wrong. Pass the blank export to `--blank-export` if you
want it checked; it is good for one thing, confirming that every column the
maintained file writes still exists in the portal.

**Totals agreeing is not evidence a load is right.** When `--template` carries
history, the run diffs the output against it — by key where keys are unique,
row for row where they are not — and a load that fails that diff is reported
BLOCKED however clean its rules came out. That diff is the only real evidence.

## What a run does

1. Loads and validates `registry/clients/<client>/channels.yaml` and
   `rules.yaml`. A bad registry stops the run before anything is written.
2. Matches each `--raw` file to a source by filename pattern. A file matching
   nothing, or two files matching one source, is an error, not a guess.
3. Builds the load. Cross-tab channels select each series by its header axes
   within the current block and disaggregate monthly to weekly on the client's
   fiscal grid; flat channels filter, reconcile values against the dictionary
   and map columns. Which one is a registry key, not a flag here.
4. Projects onto the template, orders the blocks the way the maintained file
   orders them, and formats dates and significant figures to match.
5. Runs the rule suite at the registry's thresholds and applies any waiver
   that is in date. An expired waiver is reported as expired and does **not**
   apply.
6. Checks the template's own columns for **taxonomy turnover** — values the
   previous load used that this one does not, and vice versa.
7. Diffs against the maintained file and writes the per-channel manifest and
   report.
8. Assembles every channel into one data review and writes it four ways
   (see above).

## The check the rules cannot make

Step 6 is worth its own paragraph, because it catches the one class of
problem that every other check here is blind to. Against Abbott's real
previous OLA load, `Publisher ` went from 19 partner names to 4 channel
codes, `Objective` from 80 audience descriptors to 4 funnel stages, and
`Campaign Name` turned over 264 of 267 values. The columns were not drifting;
they had been **redefined**. Impressions, clicks and spend reconciled to the
cent throughout, every rule passed, and the load joined to nothing in
history.

Seeing it needs a memory of what the previous load's vocabulary was:

```bash
python3 …/prep_cli.py seed-dictionary --client abbott-ensure --channel OLA \
  --history "Templates/OLA.xlsx" --sheet "Previous template"
```

Every later run then reports the turnover in its markdown report and manifest.
Nothing is ever auto-corrected here — a redefinition is a judgment call by
construction, and the point is to put it in front of a person.

## Coupons: drops are not redemptions

Coupon channels need one transform the others do not. A coupon dropped in
month *m* is redeemed across the following 16–18 months, so the figure the
model wants is redemptions, not drops:

```
redemptions(t) = SUM over k of  profile[k] x drops(t - k)
```

The profile lives in `registry/clients/<client>/lag-factors.yaml` and a series
opts in through its `transform:` block:

```yaml
- dims: {HCP Type: Outpatient FSF Coupons, Specialty Group: PC}
  from: {source: outpatient, sheet_pattern: "*COUP DROPS*", select: {BRAND: ENS, HCP: PCP}}
  transform: {profile: hcp_fsf, multiplier: 1.0}
```

`multiplier` converts the driver into a coupon count. Field force uses the raw
drop count, so it is 1. Direct mail before 2026 has no coupon column at all —
only shipments — so the count is shipments × a coupons-per-shipment factor.
From 2026 the client supplies actual DM coupon counts: point the series at the
coupon column and set `multiplier: 1`. That is a registry diff, not a code
change; `multiplier_until` handles a mid-series cutover.

Three things this gets right that are easy to get wrong:

- **The lag runs on the full history, before the window filter.** Convolving a
  series already cut to the load window understates every month at the start
  of it, silently. **KV-C16** measures exactly that and fails on it — pass the
  drops extract starting at least eighteen months before the load.
- **A profile is either `supplied` or `recovered`.** Recovered means we
  inferred it from the client's own consolidated file because their lag table
  had not arrived. It reproduces their numbers; that is not the same as being
  their profile. The run says so as a finding with an ask, and the channel
  stays unverified.
- **A series pointing at a missing profile refuses.** It does not fall back to
  running unlagged, which would look like an answer.

## Arguments worth knowing

| Argument | When you need it |
|---|---|
| `--channel all` | Run every channel whose sources are among the files given. Channels that need a file you did not pass are listed as skipped, not silently dropped. |
| `--template-sheet` | The maintained file is a workbook: `--template-sheet "Updated template"`. |
| `--window START END` | Week-ending window for a flat extract. Filter on the *week*, not the daily date — the last week of a load usually runs past the nominal end, and a date filter drops its tail. |
| `--fy-start`, `--n-years` | Load a different fiscal year than the registry's default. |
| `--load Q2-FY26` | Scopes waivers written for one specific load. |
| `--apply-fixes` | Off by default, deliberately. The maintained OLA load carries `OLA AMAZON` and `OLA - AMAZON` as separate values; auto-correcting the 604 minority rows makes the output differ from the file it is meant to reproduce. Drift is always reported; fixing it is a decision. |
| `--reference` | Diff against a different file than the template. |
| `--history` / `--history-dir` | Prior consolidated files, so the summary grid shows earlier quarters and a real year-on-year. `--history-dir` takes a folder — usually last quarter's output — and matches each channel by its label. Without either, the grid shows whatever history `--template` carries, and says so. |
| `--dashboard` | Also write the older per-channel dashboard. Off by default; the consolidated review replaces it. |
| `--review-only` | Write the load CSVs and the review, and skip the per-channel JSON and markdown. |

`prep_cli.py seed-dictionary` teaches a channel what the previous load's
template vocabulary was; see below.

`prep_cli.py channels --client <id>` lists what the registry knows.
`prep_cli.py check --client <id>` validates the registry and reports expired
waivers, waivers with no named owner, unverified channels and missing template
specs, without running anything.

## Reading the result

The gate is `CLEAR`, `PROCEED WITH WARNINGS` or `BLOCKED`. `BLOCKED` means the
load must not go to Element X. Two specific things to look for:

- **`status: unverified` in the channel's registry entry.** The output filename
  carries `__UNVERIFIED` so it cannot be loaded by accident. Abbott's Coupon
  Drops is the live example: the dimension mapping is right, the values carry
  an undocumented transformation, and the open question is with Kvantum.
- **A waiver with `accepted_by: TBC`.** It still applies, and `check` reports
  it. A waiver with no owner is a decision nobody made.

## Adding a channel or a client

A new channel is a `channels:` entry: which source, which sheet pattern, which
header axes identify each series, the output columns, the emit order. A new
client is a new folder under `registry/clients/`. If you find yourself wanting
to edit `kvprep/pipeline.py` for a channel, the thing you actually want is a
new key in the registry schema — `kvprep/config.py` rejects unknown keys
precisely so that a typo cannot become a silent default.

Two mappings per client are typically not inferable from the raw file at all
and must be written down. For Abbott: raw `PCP` maps to `IM` in Calls but to
`PC` in Coupon Drops, and Direct Mail's `ONC`/`PC` rows take the **Non-HR**
column rather than the Total, with HR carried separately. Taking the Total
there would double-count and still look entirely plausible.

## Verified reproductions

Run against the client's own files, these reproduce what the team built by
hand. Keep them passing.

| Channel | Rows | Result |
|---|---|---|
| Cases | 104 | byte-identical to `Cases_Q424_Q325.csv` |
| Calls | 260 | byte-identical to `Calls_Q424_Q325.csv` |
| Direct Mail | 416 | byte-identical to `Direct_Mail_Q424_Q325.csv` |
| OLA | 52,107 | row-for-row identical to `Templates/OLA.xlsx` `Updated template` — 0 of 1,146,354 cells differ |
| Coupon Drops | 676 | annual total within **0.25%**, worst series 2.2% — on an inferred profile, so still gated |

`tests/test_no_false_pass.py` pins these plus the rules that must not pass on a
broken load.

## Using the library directly

```python
import sys; sys.path.insert(0, "${CLAUDE_PLUGIN_ROOT}/lib")
from kvprep import pipeline

result = pipeline.run_load(
    client="abbott-ensure", channel="OLA",
    raw=["ENS_Spark_20250401_20260627.xlsx"],
    template="Templates/OLA.xlsx", template_sheet="Updated template",
    window=("2025-12-28", "2026-07-04"), out_dir="out",
)
print(result.gate, result.comparison["match"])
```
