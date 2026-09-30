# Kvantum Data Prep

**Version 0.7.0** · Kaizen Analytix LLC

Automates the pre-load data preparation for the **Kvantum Element X** portal and the data review
that goes with it. Raw client extracts plus the maintained template go in; a load-ready file comes
out, together with a validation verdict, a row-for-row diff against the template, and an
input-review dashboard (self-contained HTML plus a matching workbook).

## Skills

| Skill | What it does |
|---|---|
| `kvantum-prep` | **Entry point.** Runs the whole load in one pass. Start here. |
| `channel-intake` | Reads a raw extract into a canonical weekly long frame: period/channel filtering, unpivoting, monthly-to-weekly. |
| `value-reconciliation` | Matches this load's dimension values against previous loads so a respelled label doesn't split one driver in two. |
| `load-validation` | Rule-based BLOCK/WARN gate: blank weeks, duplicates, outliers, unclassified buckets, step changes, totals that don't tie, append seams. |
| `elementx-template-fill` | Maps the prepared load into the Element X upload template and appends it to the historical file. |
| `input-review-dashboard` | The client-facing input review page: gate verdict, flighting, coverage grid, value drift, open questions. |

## Layout

```
kvantum-data-prep/
├── lib/kvprep/     shared Python library the skill scripts import
├── registry/       channel, rule and template definitions (plus per-client config)
├── skills/         one folder per skill, each with a SKILL.md and a CLI script
└── tests/          pytest suite
```

## Requirements

Python 3 with `pandas`, `numpy`, `openpyxl` and `pyyaml` available to the session.

## Development

```bash
cd plugins/technical-delivery/kvantum-data-prep
python -m pytest tests
```
