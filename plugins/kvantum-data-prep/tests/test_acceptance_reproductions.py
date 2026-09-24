#!/usr/bin/env python3
"""Acceptance tests: does the pipeline still reproduce the files built by hand?

``test_no_false_pass.py`` proves the library refuses what it should refuse.
This proves it produces what it should produce -- which is the claim the whole
project rests on, and the one that a change to the fiscal calendar, the 4.33
divisor, a mapping or the output formatting will break first.

These need the client's own files, which are not in the repository. Point
``KVPREP_CLIENT_FILES`` at the folder that holds ``Raw data from client/`` and
``Templates/`` and they run; without it they skip loudly rather than passing
on nothing::

    KVPREP_CLIENT_FILES="/path/to/AI Agent support files" \\
        python3 tests/test_acceptance_reproductions.py

The OLA case reads a 39 MB workbook and takes about 90 seconds; pass
``--fast`` to run only the HCP channels.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import pandas as pd  # noqa: E402
from kvprep import pipeline  # noqa: E402

REGISTRY = Path(__file__).resolve().parents[1] / "registry"
SRC = os.environ.get("KVPREP_CLIENT_FILES")
FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"  {'PASS' if condition else 'FAIL'}  {name}" + (f" {detail}" if detail else ""))
    if not condition:
        FAILURES.append(name)


def norm(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip()


def main() -> int:
    if not SRC:
        print(
            "SKIPPED: set KVPREP_CLIENT_FILES to the client folder to run these.\n"
            "         These are the tests that prove the pipeline still reproduces\n"
            "         the hand-built files; a green run without them means nothing."
        )
        return 0
    src = Path(SRC)
    raw = src / "Raw data from client"
    tpl = src / "Templates"
    ac = next(raw.glob("Q* AC ENS*BPM Inputs*.xlsx"), None)
    op = next(raw.glob("*BPM - OUTPATIENT*.xlsx"), None)
    spark = next(raw.glob("ENS_Spark_*.xlsx"), None)
    if not (ac and op):
        print(f"SKIPPED: no BPM workbooks under {raw}")
        return 0

    out = Path(tempfile.mkdtemp()) / "acceptance"
    fast = "--fast" in sys.argv

    print("\nHCP channels reproduce the hand-built files byte for byte")
    hcp = [
        ("CASES", "Cases_Q424_Q325.csv", [ac], "Cases.csv", 104, "CLEAR"),
        ("CALLS", "Calls_Q424_Q325.csv", [ac, op], "Calls.csv", 260, "PROCEED WITH WARNINGS"),
        ("DIRECT_MAIL", "Direct_Mail_Q424_Q325.csv", [ac, op], "Direct_Mail.csv", 416,
         "PROCEED WITH WARNINGS"),
    ]
    for channel, ref_name, files, out_name, n_rows, gate in hcp:
        ref = tpl / ref_name
        if not ref.exists():
            check(f"{channel}: reference present", False, str(ref))
            continue
        r = pipeline.run_load(
            client="abbott-ensure", channel=channel, raw=[str(f) for f in files],
            template=str(ref), out_dir=out, registry_root=REGISTRY, dashboard=False,
        )
        check(f"{channel}: {n_rows} rows", len(r.frame) == n_rows, str(len(r.frame)))
        check(f"{channel}: byte-identical to {ref_name}",
              bool(r.comparison and r.comparison.get("byte_identical")))
        check(f"{channel}: gate is {gate}", r.gate == gate, r.gate)

        # The same load with no --template at all must be identical too: the
        # registry's captured spec carries the column set, the block order and
        # the number format, so dropping the template must change nothing.
        r2 = pipeline.run_load(
            client="abbott-ensure", channel=channel, raw=[str(f) for f in files],
            out_dir=out / "nospec", registry_root=REGISTRY, dashboard=False,
        )
        check(f"{channel}: identical without --template", norm(r2.paths["load"]) == norm(ref))

    print("\nCoupon Drops reproduces closely, and is still not signed off")
    # Before the redemption lag was understood this channel came out 3.3x too
    # small. It now lands within a fraction of a percent -- but on a profile we
    # inferred rather than one the client supplied, so it stays gated. Both
    # halves of that are asserted here: the arithmetic has to keep working, and
    # the gate has to keep refusing.
    ref = tpl / "Coupon_Drops_Q424_Q325.csv"
    if ref.exists():
        import numpy as _np

        r = pipeline.run_load(
            client="abbott-ensure", channel="COUPON_DROPS", raw=[str(ac), str(op)],
            template=str(ref), out_dir=out, registry_root=REGISTRY, dashboard=False,
        )
        ours = pd.read_csv(r.paths["load"])
        theirs = pd.read_csv(ref)
        keys = ["Week Starting Date", "Week Ending Date", "HCP Type", "Specialty Group"]
        m = ours.merge(theirs, on=keys, suffixes=("_o", "_t"))
        check("COUPON_DROPS: every row lines up with the maintained file",
              len(m) == len(theirs), f"{len(m)} of {len(theirs)}")
        tot_o, tot_t = m["Redemptions_o"].sum(), m["Redemptions_t"].sum()
        annual = abs(tot_o / tot_t - 1) * 100
        check(f"COUPON_DROPS: annual total within 1% ({annual:.2f}%)", annual < 1.0)
        g = m.groupby(["HCP Type", "Specialty Group"])[["Redemptions_o", "Redemptions_t"]].sum()
        g = g[g["Redemptions_t"] > 0]
        worst = float((g["Redemptions_o"] / g["Redemptions_t"] - 1).abs().max() * 100)
        check(f"COUPON_DROPS: every series within 3% ({worst:.2f}% worst)", worst < 3.0)
        check("COUPON_DROPS: still BLOCKED while the profile is unconfirmed",
              r.gate.startswith("BLOCKED"), r.gate)
        check("COUPON_DROPS: the filename still says UNVERIFIED",
              "UNVERIFIED" in r.paths["load"].name, r.paths["load"].name)
        check("COUPON_DROPS: the run reports using an inferred profile",
              any(p.get("profile_status") == "recovered"
                  for p in (r.manifest.get("series_provenance") or [])))
        check("COUPON_DROPS: KV-C16 confirms the drop history is long enough",
              any(x.rule_id == "KV-C16" and x.status == "PASS" for x in r.report.results))

    if fast or not spark:
        print("\nOLA skipped" + ("" if spark else ": no ENS_Spark_*.xlsx found"))
    else:
        print("\nOLA reproduces the maintained template row for row (slow: ~90s)")
        ola = tpl / "OLA.xlsx"
        if not ola.exists():
            check("OLA: Templates/OLA.xlsx present", False)
        else:
            r = pipeline.run_load(
                client="abbott-ensure", channel="OLA", raw=[str(spark)],
                template=str(ola), template_sheet="Updated template",
                window=("2025-12-28", "2026-07-04"), out_dir=out,
                registry_root=REGISTRY, load_label="Q2-FY26", dashboard=False,
            )
            c = r.comparison or {}
            check("OLA: 52,107 rows", len(r.frame) == 52107, str(len(r.frame)))
            check("OLA: row-for-row identical to the Updated template",
                  c.get("match") is True, str(c.get("mismatched")))
            check("OLA: every cell compared", c.get("mismatched") == 0,
                  f"{c.get('mismatched')} of {c.get('cells_compared')}")
            check("OLA: the KV-C03 waiver applied", len(r.waivers.get("applied", [])) == 1,
                  str(r.waivers.get("applied")))
            check("OLA: gate is PROCEED WITH WARNINGS", r.gate == "PROCEED WITH WARNINGS", r.gate)

            # Mechanical fixes are off by default for a reason: applying them
            # rewrites 604 'OLA - AMAZON' rows and the maintained file keeps
            # them. If this ever starts matching, the default has changed.
            r3 = pipeline.run_load(
                client="abbott-ensure", channel="OLA", raw=[str(spark)],
                template=str(ola), template_sheet="Updated template",
                window=("2025-12-28", "2026-07-04"), out_dir=out / "fixed",
                registry_root=REGISTRY, apply_fixes=True, dashboard=False,
            )
            check("OLA: --apply-fixes makes it differ from the maintained file",
                  not (r3.comparison or {}).get("match", True))

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: {FAILURES}")
        return 1
    print("all acceptance reproductions passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
