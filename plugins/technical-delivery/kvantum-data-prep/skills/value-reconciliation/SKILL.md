---
name: value-reconciliation
description: Reconcile a new load's dimension values against those used in previous loads, so the model does not split one driver in two because a label was respelled. Use when preparing Element X data and matching to history, consistency across quarters, spelling or case drift, new campaign or channel names, or cleaning dimension values comes up. Trigger on "match this to what we loaded before", "did any names change", "clean the dimension values". Run after channel-intake.
---

# Value reconciliation

> **Running the whole load?** Use the `kvantum-prep` skill instead — it drives
> every stage from the registry in one command and diffs the result against the
> maintained template. This skill is for when you need this stage on its own.


This skill exists because of a specific failure mode: a dimension value spelled
one way in every previous quarter arrives spelled slightly differently, Element X
treats it as a new variable, and the model silently splits one marketing driver
into two. Nothing in the file is missing, no total is wrong, and the error is
invisible until the model coefficients look strange.

```python
import sys; sys.path.insert(0, "${CLAUDE_PLUGIN_ROOT}/lib")
from kvprep import reconcile
d = reconcile.ValueDictionary.load("${CLAUDE_PLUGIN_ROOT}/registry/clients/<client>/value-dictionary.json")
```

## The dictionary is the memory

The dictionary holds, per client → channel → column, the canonical values that
previous loads used, plus a set of **confirmed aliases** — decisions a human has
already made. It lives in `registry/clients/<client>/value-dictionary.json` and is
committed, so a mapping question is answered once rather than every quarter.

Seed it from history, never by hand:

```python
d.learn(historical_frame, channel="OLA", columns=DIMS, source="Q3-25 load").save()
```

## Two independent checks — run both

**1. Against history.** `reconcile.diff_values(...)` classifies every distinct
value:

| verdict | meaning |
|---|---|
| `known` | exact match, or resolved through a confirmed alias |
| `mechanical` | differs only in case, whitespace or separator punctuation |
| `judgment` | close to an existing value — probably a respelling, possibly not |
| `new` | nothing comparable in the dictionary |
| `retired` | in the dictionary but absent from this load |

**2. Within the load.** `reconcile.internal_collisions(...)` finds values *inside
this one file* that collapse to the same normal form. This catches drift that
starts mid-file — a partner renamed halfway through the quarter — where both
spellings are new and a history diff sees nothing wrong. The output includes each
variant's first and last date, which usually shows the changeover immediately.

Pass `metric_cols=["Impressions","Spend"]` to both so each finding carries the
spend at stake. A variant holding 0.001% of spend and one holding 30% are not the
same conversation.

## Repairing: two tiers, and the line between them matters

This follows the Kaizen data-science plugin's transformation policy. Read
`references/data-transformation-policy.md` in the `data-science` plugin if the
distinction is unfamiliar.

```python
fixed, changelog = reconcile.apply_fixes(df, findings, tier="mechanical")
```

- **Mechanical** fixes — whitespace, case, separator punctuation — are lossless
  and unambiguous. Apply them on the copy, keep the change log, say what changed.
- **Judgment** fixes are **proposals only**. `apply_fixes` will not touch them
  unless passed explicitly in `confirmed={(column, raw_value): canonical}`.
  Present them with the spend at stake and the dates each spelling appeared, then
  **wait**. Do not compute a validated template, a chart, or a total on a
  judgment-fixed frame and describe it as provisional — that is still presenting
  an unconfirmed result.

Once a judgment call is confirmed, persist it so it is never asked again:

```python
d.record_alias("OLA", "Channel_Detail", "OLA - AMAZON", "OLA AMAZON"); d.save()
```

A `retired` value is a question, not a fix. A channel that ran every quarter and
appears nowhere in this load is usually a missing file, and that belongs in the
client email — not in a silent deletion.

## Compound fields

Creative names in media extracts are packed records
(`ENS_EMP_Vanilla Tetra_Buy now_160x600_HTML5_ENG_Q2 2025_SN_Org_Amazon`).
Kvantum's manual step is "remove the underscores"; the better move is
`reconcile.split_delimited(df, "Creative_Name", parts=[...])`, which names the
parts and is reversible. Only flatten the delimiter when the template genuinely
wants the whole string, and say so.

## What to report back

A short table of `judgment` and `new` findings with spend at stake, the
collisions found within the load, the mechanical change log, and an explicit list
of the decisions you need before the load can proceed. Then hand off to
**load-validation**.
