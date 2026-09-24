#!/usr/bin/env python3
"""Capture an Element X template spec, or compare output to a reference.

    python template_cli.py capture <blank.csv> --id elementx.ola --label OLA --out ola.json
    python template_cli.py compare <produced.csv> <reference.csv> \
        --keys "Week Starting Date" Brand --values Call \
        [--tolerance 1e-6] [--rel-tolerance 1e-9]

--rel-tolerance exists because a hand-built reference is stored at the precision
Excel displayed, not at full float precision. Set it to the reference file's
actual precision and say what you set it to; do not widen it until the diff
disappears.
"""
import argparse, json, sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from kvprep import template_fill as tf                       # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("capture"); c.add_argument("file")
    c.add_argument("--id", required=True); c.add_argument("--label", required=True)
    c.add_argument("--out", required=True)
    m = sub.add_parser("compare"); m.add_argument("produced"); m.add_argument("reference")
    m.add_argument("--keys", nargs="+", required=True); m.add_argument("--values", nargs="+", required=True)
    m.add_argument("--tolerance", type=float, default=1e-6,
                   help="absolute tolerance per value (default 1e-6)")
    m.add_argument("--rel-tolerance", type=float, default=0.0,
                   help="relative tolerance per value; use the reference file's "
                        "stored precision, e.g. 1e-9 (default 0.0)")
    a = ap.parse_args()

    if a.cmd == "capture":
        spec = tf.spec_from_blank_template(a.file, a.id, a.label)
        spec.save(a.out)
        print(f"{len(spec.columns)} columns captured -> {a.out}")
        print(json.dumps(spec.columns, indent=2))
    else:
        rep = tf.compare_to_reference(pd.read_csv(a.produced), pd.read_csv(a.reference),
                                     key_cols=a.keys, value_cols=a.values,
                                     tolerance=a.tolerance, rel_tolerance=a.rel_tolerance)
        print(json.dumps(rep, indent=2, default=str))
        print("MATCH" if rep.get("match") else "NO MATCH",
              f"(abs tol {a.tolerance:g}, rel tol {a.rel_tolerance:g})")
        return 0 if rep.get("match") else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
