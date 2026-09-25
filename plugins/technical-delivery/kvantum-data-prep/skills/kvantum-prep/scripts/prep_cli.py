#!/usr/bin/env python3
"""One command: raw client files + the maintained template -> the load file.

    prep_cli.py run --client abbott-ensure --channel CASES \
        --raw "Q3 25 AC ENS GLU BPM Inputs.xlsx" \
        --template "Templates/Cases_Q424_Q325.csv" \
        --out out/

    prep_cli.py run --client abbott-ensure --channel all --raw *.xlsx --out out/
    prep_cli.py channels --client abbott-ensure
    prep_cli.py check --client abbott-ensure

Every decision about how a channel is prepared lives in
``registry/clients/<client>/channels.yaml``; this script only reads arguments
and calls :func:`kvprep.pipeline.run_load`. Exit code is 0 when every channel
run reached a loadable gate, 2 when any was BLOCKED, 1 on an error.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PLUGIN = Path(os.environ.get("KVPREP_PLUGIN", Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(PLUGIN / "lib"))

from kvprep import config as cfgmod  # noqa: E402
from kvprep import pipeline  # noqa: E402


def _registry(args) -> Path:
    return Path(args.registry) if args.registry else PLUGIN / "registry"


def cmd_channels(args) -> int:
    cl = cfgmod.load_client(
        args.client, _registry(args), lag_factors=getattr(args, "lag_factors", None)
    )
    print(cfgmod.describe(cl))
    return 0


def cmd_check(args) -> int:
    """Load and validate the registry without running anything.

    Worth having as its own command: a registry error found here is a
    reviewable diff, while the same error found mid-run has already written
    half an output directory.
    """
    cl = cfgmod.load_client(
        args.client, _registry(args), lag_factors=getattr(args, "lag_factors", None)
    )
    print(f"registry OK: {len(cl.channels)} channel(s), {len(cl.sources)} source(s)")
    problems = []
    for name, ch in cl.channels.items():
        sp = cl.template_spec_path(ch.template)
        if not sp.exists():
            problems.append(f"{name}: no captured template spec at {sp}")
        active, expired = ch.active_waivers()
        for w in expired:
            problems.append(
                f"{name}: waiver on {w.get('rule_id')} expired {w.get('expires')} "
                "and will not be applied"
            )
        for w in active:
            if str(w.get("accepted_by", "")).strip().upper() in {"", "TBC", "TBD"}:
                problems.append(
                    f"{name}: waiver on {w.get('rule_id')} has no named owner "
                    f"(accepted_by={w.get('accepted_by')!r})"
                )
        if ch.status != "verified":
            problems.append(
                f"{name}: status is {ch.status!r} -- output is not loadable. "
                + (ch.status_detail or (ch.notes or "").strip()[:200])
            )
    for p in problems:
        print(f"  ! {p}")
    print(f"{len(problems)} thing(s) to look at")
    return 0


def cmd_run(args) -> int:
    cl = cfgmod.load_client(args.client, _registry(args), lag_factors=args.lag_factors)
    if args.lag_factors:
        print(f"redemption table: {Path(args.lag_factors).name} (supplied for this run)")
        for name, ch in cl.channels.items():
            if ch.status_detail:
                print(f"  {name}: {ch.status_detail}")
        print()
    if args.channel.lower() == "all":
        # A template belongs to one channel. Silently handing the Cases
        # template to every channel would either error five times or, worse,
        # quietly diff a load against the wrong file.
        per_channel = [f for f in ("template", "template_sheet", "reference",
                                   "history", "history_sheet")
                       if getattr(args, f)]
        if per_channel:
            print(
                f"--channel all cannot take {['--' + f.replace('_', '-') for f in per_channel]}: "
                "a template belongs to one channel. Run each channel separately with its "
                "own --template, or drop the flag and the registry's captured specs are "
                "used (they reproduce the maintained files exactly).",
                file=sys.stderr,
            )
            return 1
        files = pipeline.assign_sources(cl, args.raw)
        wanted = [
            n
            for n, ch in cl.channels.items()
            if _sources_needed(ch) <= set(files)
        ]
        skipped = [n for n in cl.channels if n not in wanted]
        if not wanted:
            print("no channel's sources are satisfied by the files given", file=sys.stderr)
            return 1
        if skipped:
            print(f"skipping {skipped}: their sources were not among the files given\n")
    else:
        wanted = [cl.channel(args.channel).name]

    window = tuple(args.window) if args.window else None
    results, worst = [], 0
    for name in wanted:
        print("=" * 72)
        print(name)
        print("=" * 72)
        try:
            r = pipeline.run_load(
                client=args.client,
                channel=name,
                raw=args.raw,
                template=args.template,
                template_sheet=args.template_sheet,
                reference=args.reference,
                history=args.history or _history_for(args, name, cl),
                history_sheet=args.history_sheet,
                out_dir=args.out,
                registry_root=_registry(args),
                fy_start=args.fy_start,
                n_years=args.n_years,
                window=window,
                load_label=args.load,
                blank_export=args.blank_export,
                dashboard=bool(args.dashboard),
                artefacts=not args.review_only,
                apply_fixes=True if args.apply_fixes else None,
                rel_tolerance=args.rel_tolerance,
                lag_factors=args.lag_factors,
            )
        except Exception as exc:
            print(f"FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
            worst = max(worst, 1)
            continue
        for n in r.notes:
            print(f"  - {n}")
        print()
        print(r.summary_text())
        print()
        results.append(r)
        if r.gate.startswith("BLOCKED"):
            worst = max(worst, 2)

    if len(results) > 1:
        print("=" * 72)
        for r in results:
            ref = (
                ""
                if r.comparison is None
                else ("  vs reference: MATCH" if r.comparison.get("match") else "  vs reference: DIFFERS")
            )
            print(f"{r.channel:<14} {len(r.frame):>7,} rows  {r.gate:<30}{ref}")
    if results and not args.no_review:
        try:
            _build_summary(args, cl, results)
        except FileNotFoundError as exc:
            print(f"input summary not built: {exc}", file=sys.stderr)
        except Exception as exc:
            print(f"input summary not built: {type(exc).__name__}: {exc}", file=sys.stderr)
            worst = max(worst, 1)
    if args.json:
        print(json.dumps([r.manifest for r in results], indent=2, default=str))
    return worst


def _history_for(args, channel: str, cl) -> str | None:
    """Pick this channel's history file out of --history-dir by its label.

    Matched on the label the channel's own outputs are named with, so the
    folder can simply be last quarter's output directory. An unmatched channel
    is not an error -- it falls back to whatever the template carries -- but it
    is worth saying so, since a silently missing history is indistinguishable
    from a channel that genuinely has none.
    """
    if not args.history_dir:
        return None
    ch = cl.channel(channel)
    stem = (ch.label or ch.name).replace(" ", "_")
    folder = Path(args.history_dir)
    hits = sorted(
        p for p in folder.glob(f"{stem}*")
        if p.is_file() and p.suffix.lower() in {".csv", ".xlsx", ".txt"}
        and "__" not in p.name[len(stem):]
    )
    if not hits:
        print(f"  (no history file starting with {stem!r} in {folder})")
        return None
    return str(hits[0])


def _build_summary(args, cl, results) -> int:
    """The input summary workbook, in the client's own layout, plus the EDA."""
    from kvprep import summary as sm
    from kvprep import summary_html, summary_xlsx

    spec_file = sm.spec_path(_registry(args), cl.id)
    if not spec_file.exists():
        raise FileNotFoundError(
            f"no summary.yaml for {cl.id} at {spec_file}. The input summary needs to know "
            "which sheet each channel belongs on and at what grain; without it the workbook "
            "would be a guess at their layout rather than a reproduction of it."
        )
    spec = sm.load_spec(spec_file)

    prior = None
    if args.prior_summary:
        prior = sm.read_prior(args.prior_summary)
        print(f"  read {len(prior.sheets)} sheets and {len(prior.change_log)} change-log "
              f"entries from {Path(args.prior_summary).name}")

    inferred = []
    if args.infer_raw:
        from kvprep import generic

        for path in args.infer_raw:
            try:
                inferred += generic.read_any(path)
            except Exception as exc:
                print(f"  could not infer a sheet from {Path(path).name}: {exc}",
                      file=sys.stderr)

    s = sm.build_summary(
        results,
        client_cfg=cl,
        spec=spec,
        registry_root=_registry(args),
        prior=prior,
        load_label=args.load or "",
        inferred=inferred,
    )
    gates = [r.gate for r in results]
    gate = (
        "BLOCKED" if any(g.startswith("BLOCKED") for g in gates)
        else "PROCEED WITH WARNINGS" if any(g != "CLEAR" for g in gates)
        else "CLEAR"
    )
    out = Path(args.out)
    # Named after their own file, which carries both words: "Ensure Data
    # Review Input Summary Q226.xlsx". One document, one name.
    stem = f"{cl.id}__data_review_input_summary" + (
        f"__{_slug(args.load)}" if args.load else ""
    )
    written = [
        summary_html.render(s, out / f"{stem}.html", gate=gate, spec=spec),
        summary_xlsx.write_workbook(s, spec, out / f"{stem}.xlsx", gate=gate),
    ]
    asks = s.asks()
    rule_asks = s.rule_asks()
    rules = s.all_findings()
    print("=" * 72)
    print("DATA REVIEW & INPUT SUMMARY")
    print("=" * 72)
    print(f"  gate           {gate}")
    print(f"  load checks    {sum(1 for f in rules if f.status == 'PASS')} passed, "
          f"{sum(1 for f in rules if f.status == 'FAIL')} failed, "
          f"{sum(1 for f in rules if f.status == 'SKIP')} skipped")
    print(f"  sheets         {len(s.sheets)} "
          f"({sum(1 for x in s.sheets if x.origin == sm.GENERATED)} generated, "
          f"{sum(1 for x in s.sheets if x.origin == sm.INFERRED)} inferred, "
          f"{sum(1 for x in s.sheets if x.origin == sm.CARRIED)} carried)")
    print(f"  series         {sum(len(x.columns) for x in s.sheets)}")
    print(f"  observations   {len(s.observations())}")
    print(f"  questions      {len(asks) + len(rule_asks)} "
          f"({len(rule_asks)} from the checks, {len(asks)} from the data)")
    for w in written:
        print(f"  {w}")
    return 0


def _slug(s: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-") or "x"


def _sources_needed(ch) -> set:
    if ch.series:
        return {s.source for s in ch.series}
    return {ch.source} if ch.source else set()


def cmd_seed_dictionary(args) -> int:
    """Learn the template-column vocabulary from a maintained load's history.

    This is what makes post-mapping drift detectable. Point it at the tab of
    the maintained template that holds the *previous* load -- for Abbott OLA
    that is ``Templates/OLA.xlsx`` sheet ``Previous template``, 28,603 rows
    back to 2019 -- and the next run can say which of those values the client
    has since retired and which are new. Without it, a column redefined
    underneath the load passes every rule silently.
    """
    import pandas as pd

    from kvprep import reconcile

    cl = cfgmod.load_client(args.client, _registry(args))
    ch = cl.channel(args.channel)
    cols = args.columns or ch.reconcile_output_columns
    if not cols:
        print(
            f"channel {ch.name} has no reconcile_output_columns in the registry and "
            "none were given with --columns -- nothing to learn",
            file=sys.stderr,
        )
        return 1
    path = Path(args.history)
    if path.suffix.lower() in {".csv", ".txt"}:
        hist = pd.read_csv(path)
    else:
        hist = pd.read_excel(path, sheet_name=args.sheet or 0, engine="openpyxl")
    absent = [c for c in cols if c not in hist.columns]
    if absent:
        print(f"{path.name} has no column(s) {absent}; it has {list(hist.columns)}",
              file=sys.stderr)
        return 1

    out = cl.template_dictionary_path()
    d = reconcile.ValueDictionary.load(out)
    d.learn(hist, ch.name, cols, source=f"{path.name}" + (f" [{args.sheet}]" if args.sheet else ""))
    d.save(out)
    print(f"learned {len(hist):,} rows of {ch.name} history into {out}")
    for c in cols:
        print(f"  {c:<30} {len(d.canonical(ch.name, c)):>4} canonical values")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="prep_cli.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--client", required=True, help="registry client id")
    common.add_argument("--registry", help="registry root (default: the plugin's)")
    common.add_argument("--lag-factors", metavar="FILE",
                        help="the client's own coupon redemption table, in place of the "
                             "inferred profiles shipped with the plugin")

    p = sub.add_parser("run", parents=[common], help="prepare a load")
    p.add_argument("--channel", required=True,
                   help="channel name, or 'all' for every channel the given files can feed")
    p.add_argument("--raw", nargs="+", required=True,
                   help="raw client extract(s); each is matched to a source by filename")
    p.add_argument("--template",
                   help="THE MAINTAINED TEMPLATE FILE -- the load the client's team keeps, "
                        "not the portal's blank export. Gives the column set, the block "
                        "order and the number format, and is diffed against when it holds "
                        "rows. Falls back to the registry's captured spec if omitted.")
    p.add_argument("--template-sheet", help="sheet in --template (e.g. 'Updated template')")
    p.add_argument("--reference", help="diff against this file instead of --template")
    p.add_argument("--history",
                   help="prior consolidated file for this channel, to show earlier quarters "
                        "and year-on-year in the input summary. Single channel only. "
                        "Without it the summary shows whatever history --template carries.")
    p.add_argument("--history-sheet", help="sheet in --history")
    p.add_argument("--history-dir",
                   help="folder of prior consolidated files; each channel takes the file whose "
                        "name starts with its label. Use this with --channel all.")
    p.add_argument("--prior-summary",
                   help="last quarter's input summary workbook. Read for three things: "
                        "to report which figures have been restated since it, to carry its "
                        "notes and answers forward, and to keep the change log accreting")
    p.add_argument("--infer-raw", nargs="+", metavar="FILE",
                   help="raw files with no registry channel: read them with the generic "
                        "reader and add a best-effort sheet, marked as inferred")
    p.add_argument("--no-review", action="store_true",
                   help="skip the consolidated data review (HTML + workbook)")
    p.add_argument("--review-only", action="store_true",
                   help="write only the consolidated review, not the per-channel artefacts")
    p.add_argument("--blank-export",
                   help="the portal's blank export, used only to confirm every column the "
                        "maintained template writes still exists in the portal")
    p.add_argument("--out", default="out", help="output directory (default: out)")
    p.add_argument("--fy-start", help="override the registry's fiscal year start (YYYY-MM-DD)")
    p.add_argument("--n-years", type=int, help="override the number of fiscal years")
    p.add_argument("--window", nargs=2, metavar=("START", "END"),
                   help="week-ending window for flat extracts (YYYY-MM-DD YYYY-MM-DD)")
    p.add_argument("--load", help="load label, e.g. Q2-FY26 -- scopes load-specific waivers")
    p.add_argument("--apply-fixes", action="store_true",
                   help="apply mechanical value fixes. Off by default: the maintained load "
                        "usually carries the drift unfixed, so applying it makes the output "
                        "differ from the file it is meant to reproduce.")
    p.add_argument("--rel-tolerance", type=float, default=1e-9,
                   help="relative tolerance for the reference diff (default 1e-9, the "
                        "maintained files' own stored precision)")
    p.add_argument("--dashboard", action="store_true",
                   help="also write the older single-channel dashboard per channel. Off by "
                        "default: the consolidated review replaces it.")
    p.add_argument("--json", action="store_true", help="also print the run manifest(s)")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("channels", parents=[common], help="list what the registry knows")
    p.set_defaults(func=cmd_channels)

    p = sub.add_parser("check", parents=[common], help="validate the registry, run nothing")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("seed-dictionary", parents=[common],
                       help="learn a channel's template-column vocabulary from history")
    p.add_argument("--channel", required=True)
    p.add_argument("--history", required=True,
                   help="the maintained template's PREVIOUS load (file, or workbook + --sheet)")
    p.add_argument("--sheet", help="sheet holding the previous load, e.g. 'Previous template'")
    p.add_argument("--columns", nargs="+",
                   help="template columns to learn (default: the registry's "
                        "reconcile_output_columns)")
    p.set_defaults(func=cmd_seed_dictionary)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except cfgmod.RegistryError as exc:
        print(f"registry error: {exc}", file=sys.stderr)
        return 1
    except pipeline.PipelineError as exc:
        print(f"pipeline error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
