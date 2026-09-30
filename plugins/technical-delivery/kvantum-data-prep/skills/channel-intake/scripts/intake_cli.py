#!/usr/bin/env python3
"""CLI wrapper around kvprep.intake -- inspect a raw file without writing code.

    python intake_cli.py describe  <file> [--sheet S]
    python intake_cli.py unpivot   <file> --sheet S [--out out.csv] [--keep-total]
    python intake_cli.py calendar  --start 2024-09-29 [--years 1] [--out cal.csv]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from kvprep import intake                                    # noqa: E402
from kvprep.calendar_fiscal import build_445_calendar        # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("describe"); d.add_argument("file"); d.add_argument("--sheet")
    u = sub.add_parser("unpivot"); u.add_argument("file")
    u.add_argument("--sheet", required=True); u.add_argument("--out")
    u.add_argument("--keep-total", action="store_true")
    c = sub.add_parser("calendar")
    c.add_argument("--start", required=True); c.add_argument("--years", type=int, default=1)
    c.add_argument("--out")
    a = ap.parse_args()

    if a.cmd == "describe":
        layout = intake.detect_layout(a.file, a.sheet)
        info = {"layout": layout, "filename_context": intake.parse_bpm_filename(a.file)}
        if layout == "flat_long":
            r = intake.read_flat(a.file, a.sheet)
            info |= {"rows": len(r.frame), "grain": r.grain,
                     "columns": list(r.frame.columns), **r.metadata}
        else:
            import pandas as pd
            info["sheets"] = pd.ExcelFile(a.file, engine="openpyxl").sheet_names
        print(json.dumps(info, indent=2, default=str))

    elif a.cmd == "unpivot":
        r = intake.read_bpm_crosstab(a.file, a.sheet, drop_total=not a.keep_total)
        print(json.dumps({"rows": len(r.frame), **r.metadata, "notes": r.notes},
                         indent=2, default=str))
        if a.out:
            r.frame.to_csv(a.out, index=False); print(f"wrote {a.out}")

    elif a.cmd == "calendar":
        cal = build_445_calendar(a.start, a.years)
        print(cal.head(12).to_string(index=False))
        print(f"... {len(cal)} weeks, {cal['period'].nunique()} fiscal months")
        if a.out:
            cal.to_csv(a.out, index=False); print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
