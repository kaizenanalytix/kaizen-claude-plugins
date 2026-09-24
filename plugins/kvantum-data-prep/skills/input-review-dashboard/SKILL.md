---
name: input-review-dashboard
description: Build the client-facing input review dashboard for a Kvantum load - an interactive HTML page showing the validation gate, weekly flighting, a channel-by-week coverage grid, dimension value drift and the questions to put back to the client. Replaces the manual Excel input summary. Trigger on "build the input summary", "input review dashboard", "show me the EDA", "something for the client meeting", "dashboard instead of the Excel". Run after load-validation.
---

# Input review dashboard

> **Building something to send the client?** Use the `kvantum-prep` skill — it
> produces the consolidated data review (one tabbed HTML plus a workbook,
> covering every channel, with findings grouped and translated). This skill
> builds the older single-channel dashboard, kept for internal one-offs.
>
> **Running the whole load?** Use the `kvantum-prep` skill instead — it drives
> every stage from the registry in one command and diffs the result against the
> maintained template. This skill is for when you need this stage on its own.


The client-facing output of the pipeline. It replaces the hand-built Excel input
summary, which was the explicit steer on the 1 Sep requirements call: don't
automate the spreadsheet, replace it with something you can put on screen in the
review meeting and drill into.

```python
import sys; sys.path.insert(0, "${CLAUDE_PLUGIN_ROOT}/lib")
from kvprep.dashboard import build_dashboard
build_dashboard(
    title="Ensure — OLA, Q2 FY26 input review",
    subtitle="Source: ENS_Spark_20250401_20260627.xlsx · 87,401 raw rows",
    report=report,                 # from load-validation
    weekly=weekly, week_col="Week Starting Date",
    metric_cols=["Impressions", "Spend", "Clicks"],
    channel_col="Channel_Detail",
    drift=drift_table,             # from value-reconciliation
    collisions=collisions,
    change_log=changelog,
    recon=recon,                   # from channel-intake, HCP loads only
    out_path="out/input_review.html",
)
```

The page is one self-contained HTML file with no external dependencies, so it can
be published as an artifact, emailed, or opened from disk. Publish it with the
Artifact tool when the user will come back to it or share it with the client;
deliver the file alone when it is a one-off look.

## What the page shows, and why in that order

1. **Validation gate** — the verdict first, with every rule expandable. The
   meeting should start from whether the load is clean, not discover it.
2. **Headline totals** — period, weeks covered, metric totals.
3. **Weekly flighting** — small multiples, one channel × metric per card, with
   flagged weeks marked and four-plus-week zero runs shaded. This is where blank
   periods and step changes become visible without anyone being told about them,
   which is the point Nitya made about the EDA.
4. **Coverage grid** — channel × week, shaded by volume, gaps hatched. A delivery
   hole is a hole you can see.
5. **Dimension value drift** — the questions to put back to the client, with the
   spend at stake beside each one.
6. **Change log and reconciliation** — what was altered and by whose authority.

## Rules for the charts

Follow the `dataviz` skill; the page already implements its defaults. In
particular:

- One y-axis per chart, never two. Two metrics of different scale are two cards.
- Series identity never rests on color alone: each card is titled with its
  channel and metric.
- Flagged weeks use the reserved `critical` status color and are also listed in
  the KV-C10 rule detail, so the chart and the rules cannot disagree.
- The palette in `lib/kvprep/dashboard.py` is the validated reference instance.
  Swap it for Kaizen brand hues only after re-running the dataviz validator.

## Honesty constraints

Every number on the page is computed from the source file at build time — the
footer says so, and that has to stay true. Two consequences:

- Do not build the dashboard from a judgment-cleaned frame whose fixes are not
  yet confirmed. The page looks authoritative and will be screenshared.
- If a validation rule was skipped, it shows as `SKIP` on the page. Leave it
  visible rather than filtering it out; a check nobody ran is exactly what a
  reviewer needs to know.

## What to report back

Where the file is, the gate it shows, and the two or three findings you would
actually raise in the client meeting — not a description of the page's sections.
