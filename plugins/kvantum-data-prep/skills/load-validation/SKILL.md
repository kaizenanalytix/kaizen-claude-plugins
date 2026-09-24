---
name: load-validation
description: Run the rule-based validation gate over a prepared load before it goes into the Kvantum Element X portal, and report a BLOCK/WARN verdict with named rule IDs. Covers blank weeks, duplicates, outliers, unclassified buckets, negative or incoherent metrics, quarter-on-quarter step changes, breakdowns that do not sum to the client TOTAL, and append seams. Trigger on "validate this load", "run the checks", "is this ready to upload", "any outliers", "does this tie to the total".
---

# Load validation

> **Running the whole load?** Use the `kvantum-prep` skill instead — it drives
> every stage from the registry in one command and diffs the result against the
> maintained template. This skill is for when you need this stage on its own.


The gate between a prepared load and the Element X portal. Every check is a named
rule with a stable ID and a severity, so the outcome is auditable and comparable
quarter to quarter — "KV-C03 failed" says something precise that "the data looks
off" does not.

```python
import sys; sys.path.insert(0, "${CLAUDE_PLUGIN_ROOT}/lib")
from kvprep import validate
report = validate.run_standard_suite(
    df, dataset="ENS_Spark Q2-26", channel="OLA",
    week_col="Week Starting Date",
    metric_cols=["Impressions", "Spend", "Clicks"],
    dim_cols=["Channel_Detail", "Funnel_Classification", "Objective_Category_Type"],
    group_cols=["Channel_Detail"],
)
print(report.summary_text())
report.to_json("validation/ola_q226.json")
```

## Severity and the gate

| severity | meaning |
|---|---|
| `BLOCK` | do not upload until resolved |
| `WARN` | may proceed, but it belongs in the client input review and usually needs a question back |
| `INFO` | audit trail only |

`report.gate` returns `CLEAR`, `PROCEED WITH WARNINGS` or `BLOCKED`. Never
describe a load as validated while `report.blockers` is non-empty.

A rule whose inputs are absent returns **`SKIP`**, not `PASS`. Read the skipped
rules out loud — a skipped KV-C13 means nobody checked the breakdown against the
client's own total, which is not the same as it being right.

## The rule catalogue

| ID | Rule | Sev | Catches |
|---|---|---|---|
| KV-C01 | Week grid continuity | BLOCK | missing or off-grid weeks |
| KV-C02 | Period coverage | BLOCK | load does not span the requested period |
| KV-C03 | Grain uniqueness | BLOCK | duplicate rows that would double-count |
| KV-C04 | Required columns present | BLOCK | template columns the portal demands |
| KV-C05 | Metric completeness | BLOCK | null metrics silently dropping spend |
| KV-C06 | Breakdown dimension completeness | WARN | rows carrying spend the model cannot attribute |
| KV-C07 | No unclassified buckets | BLOCK / WARN | `NEEDS CLASSIFICATION` and friends; BLOCK only when they carry non-zero metrics |
| KV-C08 | Non-negative metrics | BLOCK | negative spend or impressions |
| KV-C09 | Metric coherence | WARN | spend without delivery, clicks above impressions |
| KV-C10 | Weekly outliers | WARN | extreme weeks, by robust median/MAD z-score |
| KV-C11 | Interior zero runs | WARN | blank stretches inside an active series |
| KV-C12 | Period step change | WARN | quarter-on-quarter moves worth a client question |
| KV-C13 | Parts reconcile to TOTAL | BLOCK | an unpivot that lost or double-counted a column |
| KV-C14 | Disaggregation conserves annual total | BLOCK | monthly-to-weekly arithmetic |
| KV-C15 | Append seam integrity | BLOCK / WARN | gap, overlap or schema drift where the load joins history |

KV-C13, KV-C14 and KV-C15 are not in `run_standard_suite` because each needs a
second input. Call them directly and append to `report.results`:

```python
report.results.append(validate.rule_parts_vs_total(parts, totals, ["period"], "Calls"))
report.results.append(validate.rule_annual_conservation(recon, "Calls"))
report.results.append(validate.rule_append_seam(history, new, "Week Starting Date", DIMS))
```

## Two rules that are easy to get wrong

**KV-C10 uses a robust z-score** (median and MAD, not mean and standard
deviation) because a single 50× week inflates the standard deviation enough to
hide itself. Default threshold is 5.0. Raise it for genuinely bursty channels
rather than deleting the rule, and say what you raised it to.

**KV-C14 asserts the annual total, not the monthly one.** The flat 4.33 divisor
used in monthly-to-weekly disaggregation conserves the year and deliberately not
the month (see `channel-intake`). Asserting monthly conservation would fail every
load for a reason that is not a bug.

## Thresholds

Defaults live in `run_standard_suite`'s `thresholds`; per-client overrides belong
in `registry/clients/<client>/rules.yaml`, not in the call site. When you change a
threshold for a load, name the old and new value in the report — a silently
loosened threshold is how a check stops meaning anything.

## What to report back

The gate, then the failures ordered by severity, each with the rule ID, what it
found, and the specific action it implies (fix, ask the client, or accept with a
reason). Save the JSON alongside the load. Then hand off to
**elementx-template-fill**, and to **input-review-dashboard** for the client-facing
view.
