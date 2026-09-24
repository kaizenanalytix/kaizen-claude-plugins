#!/usr/bin/env python3
"""Diff a load's dimension values against the historical value dictionary.

    python reconcile_cli.py learn <history.csv> --dict D.json --channel OLA --cols A B C
    python reconcile_cli.py diff  <load.csv>    --dict D.json --channel OLA --cols A B C \
        [--metrics Spend] [--out findings.csv]
"""
import argparse, sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from kvprep import reconcile                                 # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("learn", "diff"):
        p = sub.add_parser(name)
        p.add_argument("file"); p.add_argument("--dict", required=True)
        p.add_argument("--channel", required=True); p.add_argument("--cols", nargs="+", required=True)
        p.add_argument("--metrics", nargs="*", default=[]); p.add_argument("--out")
    a = ap.parse_args()

    df = pd.read_csv(a.file)
    d = reconcile.ValueDictionary.load(a.dict)

    if a.cmd == "learn":
        d.learn(df, a.channel, a.cols, source=Path(a.file).name).save(a.dict)
        for c in a.cols:
            print(f"{c}: {len(d.canonical(a.channel, c))} canonical values")
        print(f"wrote {a.dict}")
        return 0

    findings = reconcile.diff_values(df, d, a.channel, a.cols, metric_cols=a.metrics)
    table = reconcile.findings_frame(findings)
    counts = table["verdict"].value_counts().to_dict() if not table.empty else {}
    print("verdicts:", counts)
    action = table[table["verdict"].isin(["judgment", "new", "retired"])] if not table.empty else table
    if not action.empty:
        print("\nneeds a decision:")
        print(action.head(40).to_string(index=False))
    for c in reconcile.internal_collisions(df, a.cols, a.metrics):
        print(f"\ncollision in {c['column']}: "
              + ", ".join(repr(v["value"]) for v in c["variants"]))
    if a.out and not table.empty:
        table.to_csv(a.out, index=False); print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
