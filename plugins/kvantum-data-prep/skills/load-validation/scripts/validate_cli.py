#!/usr/bin/env python3
"""Run the standard validation suite over a prepared CSV load.

    python validate_cli.py load.csv --channel OLA \
        --metrics Impressions Spend Clicks \
        --dims Channel_Detail Funnel_Classification \
        [--week-col "Week Starting Date"] [--group Channel_Detail] [--json out.json]
"""
import argparse, sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from kvprep import validate                                  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file")
    ap.add_argument("--channel", default="unknown")
    ap.add_argument("--week-col", default="Week Starting Date")
    ap.add_argument("--metrics", nargs="+", required=True)
    ap.add_argument("--dims", nargs="+", default=[])
    ap.add_argument("--group", nargs="*", default=[])
    ap.add_argument("--json")
    a = ap.parse_args()

    df = pd.read_csv(a.file)
    rep = validate.run_standard_suite(
        df, dataset=Path(a.file).name, channel=a.channel, week_col=a.week_col,
        metric_cols=a.metrics, dim_cols=a.dims, group_cols=a.group,
    )
    print(rep.summary_text())
    if a.json:
        rep.to_json(a.json); print(f"\nwrote {a.json}")
    return 1 if rep.blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
