"""kvprep.pipeline -- raw client files in, load-ready file out, in one call.

The five step modules (:mod:`~kvprep.intake`, :mod:`~kvprep.reconcile`,
:mod:`~kvprep.validate`, :mod:`~kvprep.template_fill`,
:mod:`~kvprep.dashboard`) each do one thing well and are still the right
entry point when you need one stage on its own. This module is the whole
quarterly job: it reads the registry, drives those five in the right order
with the right arguments, and writes the load file, the gate report, the
reference diff and the input-review dashboard.

Two design points worth stating, because both were learned by getting them
wrong first:

**The maintained template is the specification, not the blank export.** The
portal's blank export lists every column the portal will accept. The file the
client's team maintains says which of those columns the load actually uses, at
what grain, in what order, at what precision. A load built from the blank
export reconciled to the cent on every metric while its row count, column set
and six of its mappings were all wrong. So ``template`` here means the
maintained file, and when that file carries history it is also the reference
the output is diffed against.

**Nothing about a channel is hardcoded here.** Which sheet, which columns,
which dimension values, which thresholds, which emit order -- all of it comes
from ``registry/clients/<client>/channels.yaml`` through :mod:`kvprep.config`.
A new channel, or a new client, is a reviewable diff to a YAML file. If you
find yourself wanting to add an ``if channel == ...`` to this module, the
thing you actually want is a new key in the registry schema.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path

import pandas as pd

from . import config as cfgmod
from . import intake, lag, reconcile, template_fill as tf, validate
from .calendar_fiscal import build_445_calendar, disaggregate_monthly_to_weekly

WEEK_START = "Week Starting Date"
WEEK_END = "Week Ending Date"


class PipelineError(RuntimeError):
    """The run cannot proceed and continuing would produce a plausible wrong file."""


# --------------------------------------------------------------------------
# result
# --------------------------------------------------------------------------


@dataclass
class LoadResult:
    client: str
    channel: str
    frame: pd.DataFrame  # formatted, as written
    numeric: pd.DataFrame  # same rows, native dtypes, for validation and charts
    report: validate.ValidationReport | None = None
    waivers: dict = field(default_factory=dict)
    comparison: dict | None = None
    manifest: dict = field(default_factory=dict)
    paths: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    status: str = "verified"
    # Prior periods for the input-summary grid. Defaults to whatever the
    # maintained template carries -- which is usually a rolling year for the
    # HCP files and several years for OLA -- and is replaced by --history when
    # a fuller file is supplied. Without it the review can only show the
    # quarter being loaded, and a flight that stopped last year is invisible.
    history: "pd.DataFrame | None" = None
    history_source: str = ""
    lag_profiles: dict = field(default_factory=dict)
    # The client's own monthly figures, exactly as they arrived: full history,
    # before the window filter, before the redemption lag, before the 4.33
    # divisor. This is what the input summary shows. The walkthrough was
    # explicit about it -- "we only show the raw inputs so that client can
    # validate that this is the correct input that they have shared with us"
    # -- and it is the right rule anyway: a client cannot confirm a number
    # they have never seen.
    raw_monthly: "pd.DataFrame | None" = None

    @property
    def gate(self) -> str:
        """The gate, which two things outside the rule suite can veto.

        A load that passes every rule and still does not reproduce the file it
        is meant to reproduce is not a passing load. Totals agreeing is not
        evidence a load is right; only a row-for-row diff is.

        And a channel the registry marks unverified must never report a
        loadable gate, whatever the rules say. Coupon Drops passes ten rules
        and is 3.3x too small; the rules cannot see that, and a green gate on
        a file named ``__UNVERIFIED`` is exactly the mixed signal that gets
        one loaded anyway.
        """
        if self.status != "verified":
            return f"BLOCKED ({self.status.upper()} CHANNEL)"
        base = self.report.gate if self.report else "CLEAR"
        if self.comparison is not None and not self.comparison.get("match"):
            # Say which of the two things blocked it. "BLOCKED" alone reads as
            # "a rule failed", and somebody testing a redemption table against
            # the maintained file goes looking through the rules for a failure
            # that is not there.
            return "BLOCKED (DIFFERS FROM THE MAINTAINED FILE)"
        return base

    def summary_text(self) -> str:
        lines = [
            f"{self.client} / {self.channel}",
            f"rows        : {len(self.frame):,}",
            f"gate        : {self.gate}",
        ]
        if self.report:
            counts = {
                s: sum(1 for r in self.report.results if r.status == s)
                for s in ("PASS", "FAIL", "WAIVED", "SKIP")
            }
            lines.append("rules       : " + ", ".join(f"{k} {v}" for k, v in counts.items() if v))
        if self.comparison is None:
            # Silence here would be the worst outcome. The whole argument of
            # this pipeline is that agreeing totals prove nothing and only a
            # diff against the maintained file does -- so a run with no diff
            # has to say so where it cannot be missed, not in a note halfway
            # down a list. The commonest cause is passing the portal's blank
            # export as --template: it has the columns but no rows, so it can
            # specify the load and cannot check it.
            lines.append(
                "vs reference: NOT CHECKED -- no reference carried any rows. "
                "Pass the maintained template (the file the client's team keeps) "
                "as --template or --reference; a diff against it is the only real "
                "evidence this load is right."
            )
        else:
            c = self.comparison
            lines.append(
                "vs reference: "
                + ("MATCH" if c.get("match") else "DIFFERS")
                + f" ({c.get('produced_rows')} produced vs {c.get('reference_rows')} reference"
                + (f", {c['mismatched']} values differ" if c.get("mismatched") else "")
                + ")"
            )
            if c.get("byte_identical") is not None:
                lines.append(
                    f"byte-diff   : {'identical' if c['byte_identical'] else 'differs'}"
                )
            # How far off, per metric, in one line. "DIFFERS" alone is the
            # wrong headline when somebody is testing a redemption table
            # against the file their team built by hand: the question is not
            # whether it differs -- it will -- but by how much, and a reader
            # should not have to open the manifest to find out.
            for col, d in (c.get("per_column") or {}).items():
                ours, theirs = d.get("produced_total"), d.get("reference_total")
                if not isinstance(ours, (int, float)) or not isinstance(theirs, (int, float)):
                    continue
                if not theirs:
                    continue
                gap = (ours - theirs) / abs(theirs) * 100.0
                lines.append(
                    f"  {col:<10}: {ours:,.0f} against {theirs:,.0f} in the maintained "
                    f"file ({gap:+.2f}%), {d.get('mismatched', 0):,} row(s) differ"
                )
        if self.waivers.get("applied"):
            lines.append(f"waivers     : {len(self.waivers['applied'])} applied")
        if self.waivers.get("expired"):
            lines.append(
                f"waivers     : {len(self.waivers['expired'])} EXPIRED and not applied"
            )
        for k, v in self.paths.items():
            lines.append(f"  {k:<10} {v}")
        return "\n".join(lines)


# --------------------------------------------------------------------------
# derived-column vocabulary
#
# A registry entry must not be able to run arbitrary code -- channels.yaml is
# a config file that gets reviewed as a diff, not a program. So derived
# columns are written as `fn(args)` from this fixed vocabulary and parsed,
# never eval'd.
# --------------------------------------------------------------------------

_CALL = re.compile(r"^\s*([a-z_]+)\s*\(([^)]*)\)\s*$")


def _derive(expr: str, frame: pd.DataFrame, where: str):
    m = _CALL.match(str(expr))
    if not m:
        raise PipelineError(
            f"{where}: derived expression {expr!r} is not `fn(args)`. "
            f"Available: {sorted(_DERIVATIONS)}"
        )
    fn, argstr = m.group(1), m.group(2)
    args = [a.strip() for a in argstr.split(",") if a.strip()]
    if fn not in _DERIVATIONS:
        raise PipelineError(
            f"{where}: unknown derivation {fn!r}. Available: {sorted(_DERIVATIONS)}"
        )
    col = args[0] if args else None
    if col and col not in frame.columns:
        raise PipelineError(
            f"{where}: derived {expr!r} needs column {col!r}, which the frame does "
            f"not have. Columns: {list(frame.columns)[:25]}"
        )
    return _DERIVATIONS[fn](frame, *args)


_DERIVATIONS = {
    "minus_days": lambda f, col, n: pd.to_datetime(f[col]) - pd.Timedelta(days=int(n)),
    "plus_days": lambda f, col, n: pd.to_datetime(f[col]) + pd.Timedelta(days=int(n)),
    "iso_week": lambda f, col: pd.to_datetime(f[col]).dt.isocalendar().week.astype(int),
    "year": lambda f, col: pd.to_datetime(f[col]).dt.year,
    "copy": lambda f, col: f[col],
    "upper": lambda f, col: f[col].astype(str).str.upper(),
    "strip": lambda f, col: f[col].astype(str).str.strip(),
}


# --------------------------------------------------------------------------
# input resolution
# --------------------------------------------------------------------------


def assign_sources(client: cfgmod.ClientConfig, raw_paths: list[str | Path]) -> dict[str, Path]:
    """Map each raw file onto the source block whose ``file_pattern`` it matches.

    A file matching nothing, or two files matching the same source, both stop
    the run. Guessing which of two workbooks is "the" outpatient extract is
    how a load silently uses last quarter's file.
    """
    out: dict[str, Path] = {}
    unmatched: list[str] = []
    for p in raw_paths:
        p = Path(p)
        src = client.source_for(p)
        if src is None:
            unmatched.append(p.name)
            continue
        if src.name in out and out[src.name] != p:
            raise PipelineError(
                f"two files match source {src.name!r} ({src.file_pattern}): "
                f"{out[src.name].name} and {p.name}. Pass one."
            )
        out[src.name] = p
    if unmatched:
        raise PipelineError(
            f"raw file(s) {unmatched} match no source in the registry. Patterns: "
            + ", ".join(f"{k}={v.file_pattern!r}" for k, v in client.sources.items())
        )
    return out


def _need(files: dict[str, Path], source: str, channel: str) -> Path:
    if source not in files:
        raise PipelineError(
            f"channel {channel} needs source {source!r} but no raw file matching it "
            f"was passed. Got: {sorted(files)}"
        )
    return files[source]


# --------------------------------------------------------------------------
# the two shapes
# --------------------------------------------------------------------------


def _crosstab_series(
    ch: cfgmod.ChannelConfig,
    client: cfgmod.ClientConfig,
    files: dict[str, Path],
    calendar: pd.DataFrame,
    notes: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Build a weekly load from cross-tab series named in the registry."""
    sheets: dict[tuple[str, str], intake.CrosstabSheet] = {}

    def sheet_for(s: cfgmod.SeriesConfig) -> intake.CrosstabSheet:
        src = client.sources[s.source]
        path = _need(files, s.source, ch.name)
        name = intake.resolve_sheet(
            path, sheet=s.sheet or src.sheet, sheet_pattern=s.sheet_pattern or src.sheet_pattern
        )
        key = (str(path), name)
        if key not in sheets:
            sheets[key] = intake.read_crosstab(path, name, header_labels=src.header_labels)
            notes.append(f"read {path.name}:{name} -- {sheets[key].notes[0]}")
        return sheets[key]

    monthly_parts, raw_parts, provenance, warmups = [], [], [], []
    cal_start = pd.Timestamp(calendar["period"].min())
    for i, s in enumerate(ch.series):
        sh = sheet_for(s)
        block = sh.latest_block() if s.block == "latest" else s.block
        cols: dict[str, pd.Series] = {}
        # What the client actually sent, before any transform and before the
        # window filter. The input summary shows this, not the modelled
        # series: the client is validating that we received what they sent,
        # and a number they have never seen cannot be validated by them.
        raw_cols: dict[str, pd.Series] = {}
        for metric, spec in s.metrics.items():
            if "constant" in spec:
                # An explicit constant, not an omission. The DMwC rows have no
                # bottles column in the raw file at all, and the maintained
                # file holds 0 there.
                cols[metric] = pd.Series(spec["constant"], index=sh.values.index, dtype="float64")
                raw_cols[metric] = cols[metric]
                provenance.append(
                    {"series": i, "metric": metric, "source": "constant", "value": spec["constant"]}
                )
            else:
                ser = sh.series(spec["select"], block=block)
                raw_cols[metric] = ser.copy()
                prov = {
                    "series": i,
                    "dims": s.dims,
                    "metric": metric,
                    "file": Path(sh.path).name,
                    "sheet": sh.sheet,
                    "block": block,
                    "column": ser.attrs["col"],
                    "label": ser.name,
                }
                # The redemption lag runs HERE -- on the full monthly history,
                # before the window filter below. Convolving a series that has
                # already been cut to the load window understates every month
                # at the start of it by however much of the profile reaches
                # back past the cut, and nothing downstream can tell.
                tf = s.transform or {}
                if tf.get("profile"):
                    prof = (client.lag_profiles or {}).get(tf["profile"])
                    if prof is None:
                        raise PipelineError(
                            f"series {i} of {ch.name} needs redemption profile "
                            f"{tf['profile']!r}, which is not loaded"
                        )
                    lagged = lag.apply_lag(
                        ser,
                        prof,
                        multiplier=float(tf.get("multiplier", 1.0)),
                        multiplier_until=tf.get("multiplier_until"),
                    )
                    warm = lag.warmup_shortfall(ser, prof, cal_start)
                    warmups.append({"series": i, "dims": s.dims, **warm})
                    prov.update(
                        {
                            "transform": "redemption lag",
                            "profile": prof.name,
                            "profile_status": prof.status,
                            "multiplier": float(tf.get("multiplier", 1.0)),
                            "multiplier_until": tf.get("multiplier_until"),
                            "drops_total": float(
                                pd.to_numeric(ser, errors="coerce").sum()
                            ),
                            "redemptions_total": float(lagged.sum()),
                        }
                    )
                    ser = lagged
                cols[metric] = ser
                provenance.append(prov)
        part = pd.DataFrame(cols)
        part.index.name = "period"
        part = part.reset_index()
        for k, v in s.dims.items():
            part[k] = v
        part["__block"] = i
        monthly_parts.append(part)

        raw_part = pd.DataFrame(raw_cols)
        raw_part.index.name = "period"
        raw_part = raw_part.reset_index()
        for k, v in s.dims.items():
            raw_part[k] = v
        raw_part["__series"] = i
        raw_parts.append(raw_part)

    monthly = pd.concat(monthly_parts, ignore_index=True)
    raw_monthly = pd.concat(raw_parts, ignore_index=True)
    dim_cols = [c for c in ch.output_columns if c in monthly.columns and c not in ch.metrics]

    # Filter to the load window before disaggregating. The disaggregator
    # refuses to drop uncovered periods silently, and it is right to -- but
    # the excluding should be visible here, with the excluded volume stated,
    # rather than showing up as an exception.
    covered = set(pd.to_datetime(calendar["period"]).unique())
    inside = monthly[pd.to_datetime(monthly["period"]).isin(covered)]
    excluded = monthly[~pd.to_datetime(monthly["period"]).isin(covered)]
    if inside.empty:
        raise PipelineError(
            f"no raw period falls inside the fiscal window "
            f"{calendar['period'].min():%Y-%m} .. {calendar['period'].max():%Y-%m}. "
            f"The file covers {monthly['period'].min():%Y-%m} .. "
            f"{monthly['period'].max():%Y-%m}. Check fiscal_calendar.year_start "
            "or pass --fy-start."
        )
    if not excluded.empty:
        notes.append(
            f"period filter: {len(monthly)} -> {len(inside)} monthly rows; excluded "
            + ", ".join(
                f"{m} {pd.to_numeric(excluded[m], errors='coerce').sum():,.2f}"
                for m in ch.metrics
            )
            + " outside the window (retained as history, not part of this load)"
        )

    grouped = inside.groupby(["period", "__block"] + dim_cols, as_index=False, dropna=False)[
        ch.metrics
    ].sum()
    weekly, recon = disaggregate_monthly_to_weekly(
        grouped,
        calendar,
        value_cols=list(ch.metrics),
        dim_cols=["__block"] + dim_cols,
        divisor=ch.fiscal.divisor if ch.fiscal else 4.33,
    )
    weekly = weekly.rename(
        columns={"week_starting_date": WEEK_START, "week_ending_date": WEEK_END}
    )
    weekly = weekly.sort_values(["__block", WEEK_START], kind="stable").drop(columns="__block")
    notes.append(
        f"disaggregated {len(grouped)} monthly rows -> {len(weekly)} weekly rows "
        f"(divisor {ch.fiscal.divisor if ch.fiscal else 4.33})"
    )
    return (
        weekly.reset_index(drop=True),
        recon,
        {
            "series_provenance": provenance,
            "lag_warmup": warmups,
            "raw_monthly": raw_monthly,
        },
    )


def _flat_rows(
    ch: cfgmod.ChannelConfig,
    client: cfgmod.ClientConfig,
    files: dict[str, Path],
    window: tuple[str, str] | None,
    notes: list[str],
    apply_fixes: bool | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Build a weekly load from a flat long extract."""
    src = client.sources[ch.source]
    path = _need(files, ch.source, ch.name)
    res = intake.read_flat(
        path,
        ch.sheet or src.sheet,
        date_col=src.date_column,
        week_ending_col=src.week_ending_column,
    )
    df = res.frame
    notes.append(f"read {path.name}:{res.sheet} -- {len(df):,} rows x {len(df.columns)} columns")

    week_end_col = res.metadata.get("week_ending_col") or src.week_ending_column
    if not week_end_col or week_end_col not in df.columns:
        raise PipelineError(
            f"{path.name}: no week-ending column. The registry says "
            f"{src.week_ending_column!r}; the file has {list(df.columns)[:20]}"
        )

    for col, want in ch.filter.items():
        if col not in df.columns:
            raise PipelineError(f"{path.name}: filter column {col!r} not in the extract")
        wants = want if isinstance(want, list) else [want]
        n0 = len(df)
        df = df[df[col].astype(str).str.strip().isin([str(w).strip() for w in wants])]
        notes.append(f"filter {col} in {wants}: {n0:,} -> {len(df):,} rows")

    if window:
        # Filter on the *week*, not the daily date. The maintained load's final
        # week runs past the nominal window end; a date filter silently drops
        # the tail of that week.
        lo, hi = pd.Timestamp(window[0]), pd.Timestamp(window[1])
        n0 = len(df)
        wk = pd.to_datetime(df[week_end_col])
        df = df[(wk >= lo) & (wk <= hi)]
        notes.append(
            f"week filter {week_end_col} in [{lo.date()}, {hi.date()}]: "
            f"{n0:,} -> {len(df):,} rows"
        )
    if df.empty:
        raise PipelineError("no rows left after filtering -- nothing to load")

    extra = {}
    if ch.reconcile_columns:
        dict_path = client.value_dictionary_path()
        d = reconcile.ValueDictionary.load(dict_path)
        findings = reconcile.diff_values(
            df, d, ch.name, ch.reconcile_columns, metric_cols=ch.metrics[:1]
        )
        table = reconcile.findings_frame(findings)
        collisions = reconcile.internal_collisions(df, ch.reconcile_columns, ch.metrics[:1])
        counts = table["verdict"].value_counts().to_dict() if not table.empty else {}
        # Reporting drift and *fixing* it are different decisions. The
        # maintained OLA load carries 'OLA AMAZON' and 'OLA - AMAZON' as
        # separate values; auto-correcting the 604 minority rows makes the
        # output differ from the file it is meant to reproduce, on a change
        # nobody asked for. So the default is to report and let a person
        # decide -- apply_mechanical_fixes in the registry, or --apply-fixes,
        # turns it on deliberately.
        if apply_fixes if apply_fixes is not None else ch.apply_mechanical_fixes:
            df, changelog = reconcile.apply_fixes(df, findings, tier="mechanical")
            notes.append(
                f"value reconciliation vs {dict_path.name}: {counts}; "
                f"{len(changelog)} mechanical fix(es) APPLIED"
            )
        else:
            changelog = reconcile.apply_fixes(df, findings, tier="none")[1]
            n_mech = int((table["verdict"] == "mechanical").sum()) if not table.empty else 0
            notes.append(
                f"value reconciliation vs {dict_path.name}: {counts}; "
                f"{n_mech} mechanical fix(es) reported but NOT applied "
                "(--apply-fixes to apply them)"
            )
        extra = {
            "verdicts": counts,
            "drift": table,
            "collisions": collisions,
            "changelog": changelog,
            "judgment": (
                table[table["verdict"] == "judgment"] if not table.empty else pd.DataFrame()
            ),
        }

    df = df.copy()
    df[WEEK_END] = pd.to_datetime(df[week_end_col])
    if WEEK_START not in df.columns:
        df[WEEK_START] = df[WEEK_END] - pd.Timedelta(days=6)

    if ch.aggregate:
        keys = [c for c in (ch.grain or [WEEK_START, WEEK_END]) if c in df.columns]
        n0 = len(df)
        df = df.groupby(keys, as_index=False, dropna=False)[ch.metrics].sum()
        notes.append(f"aggregated to {len(keys)} declared dimensions: {n0:,} -> {len(df):,} rows")
    else:
        notes.append(
            "no aggregation -- the maintained load carries one row per raw row "
            "(aggregate: true in the registry to change this)"
        )
    return df, extra


# --------------------------------------------------------------------------
# the run
# --------------------------------------------------------------------------


def run_load(
    *,
    client: str,
    channel: str,
    raw: list[str | Path],
    template: str | Path | None = None,
    reference: str | Path | None = None,
    history: str | Path | None = None,
    history_sheet: str | int | None = None,
    template_sheet: str | int | None = None,
    out_dir: str | Path = "out",
    registry_root: str | Path | None = None,
    fy_start: str | None = None,
    n_years: int | None = None,
    window: tuple[str, str] | None = None,
    load_label: str | None = None,
    blank_export: str | Path | None = None,
    dashboard: bool = False,
    artefacts: bool = True,
    apply_fixes: bool | None = None,
    rel_tolerance: float = 1e-9,
    lag_factors: str | Path | None = None,
    today: date | None = None,
) -> LoadResult:
    """Prepare one channel's load end to end.

    Parameters
    ----------
    client, channel:
        Keys into ``registry/clients/<client>/channels.yaml``.
    raw:
        The client's raw extracts. Each is matched to a source block by its
        filename pattern; order does not matter.
    template:
        **The maintained template file** -- the load the client's team keeps,
        not the portal's blank export. Its header gives the column set and
        order, its data gives the block order, its stored precision gives the
        number format, and when it carries rows it is also the reference the
        output is diffed against. Falls back to the registry's captured spec
        when omitted.
    reference:
        A different file to diff against, when the reference is not the same
        file as the template.
    blank_export:
        Optional. The portal's blank export, used only to confirm that every
        column the maintained template writes still exists in the portal.
    window:
        ``(start, end)`` on the week-ending date, for flat extracts.
    """
    notes: list[str] = []
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cl = cfgmod.load_client(
        client, registry_root, today=today, lag_factors=lag_factors
    )
    ch = cl.channel(channel)
    if fy_start or n_years:
        ch.fiscal = cfgmod.FiscalConfig(
            pattern=cl.fiscal.pattern,
            year_start=fy_start or cl.fiscal.year_start,
            n_years=int(n_years or cl.fiscal.n_years),
            period_label_offset_months=cl.fiscal.period_label_offset_months,
            divisor=cl.fiscal.divisor,
        )
    files = assign_sources(cl, list(raw))

    if ch.status != "verified":
        notes.append(
            f"CHANNEL STATUS: {ch.status}. {ch.status_detail or ch.notes or ''}".strip()
        )

    # -- template spec: the maintained file, not the blank export ----------
    ref_path = Path(reference) if reference else (Path(template) if template else None)
    ref_df = None
    if ref_path is not None and ref_path.exists():
        ref_df = _read_tabular(ref_path, template_sheet)
        if ref_df.empty:
            ref_df = None
            notes.append(
                f"NO REFERENCE DIFF: {ref_path.name} has a header but no rows, so it "
                "can specify the load but cannot check it. If this is the portal's "
                "blank export, that is the known trap -- pass the maintained "
                "template instead, and give the blank export to --blank-export."
            )

    if template:
        spec = tf.spec_from_history(
            template,
            template_id=ch.template,
            label=ch.label or ch.name,
            sheet=template_sheet,
            required=ch.required_columns,
            numeric_columns=list(ch.metrics),
        )
        notes.append(f"template spec from the maintained file {Path(template).name}: "
                     f"{len(spec.columns)} columns")
    else:
        sp = cl.template_spec_path(ch.template)
        if not sp.exists():
            raise PipelineError(
                f"no --template given and no captured spec at {sp}. Pass the maintained "
                "template file; it is the specification."
            )
        spec = tf.TemplateSpec.load(sp)
        notes.append(f"template spec from the registry: {sp.name}, {len(spec.columns)} columns")

    missing_out = [c for c in ch.output_columns if c not in spec.columns]
    if missing_out:
        raise PipelineError(
            f"the registry's output_columns {missing_out} are not in the template "
            f"{spec.template_id} ({list(spec.columns)}). One of the two is out of date -- "
            "most likely the template changed and the registry has not caught up."
        )

    # -- history for the input summary ------------------------------------
    hist_df, hist_source = None, ""
    if history:
        hp = Path(history)
        if not hp.exists():
            raise PipelineError(f"--history {hp} does not exist")
        hist_df = _read_tabular(hp, history_sheet)
        hist_source = hp.name + (f" [{history_sheet}]" if history_sheet else "")
        notes.append(f"history for the input summary: {hist_source}, {len(hist_df):,} rows")
    elif ref_df is not None:
        hist_df = ref_df
        hist_source = (ref_path.name if ref_path else "") + (
            f" [{template_sheet}]" if template_sheet else ""
        )
        notes.append(
            f"history for the input summary comes from {hist_source or 'the template'} "
            "-- pass --history to supply a longer one"
        )
    else:
        notes.append(
            "no history available for the input summary: the grid shows only the "
            "period being loaded. Pass --history with a prior consolidated file to "
            "show earlier quarters and year-on-year."
        )

    blank_check = None
    if blank_export:
        blank_check = tf.check_against_blank(spec, blank_export)
        if not blank_check["ok"]:
            notes.append(
                "PORTAL SCHEMA: the maintained template writes column(s) "
                f"{blank_check['used_but_not_in_blank']} that the blank export no longer "
                "has. The upload will reject them."
            )

    # -- build -------------------------------------------------------------
    recon = None
    cal = None
    extra: dict = {}
    if ch.pipeline == "crosstab_series":
        cal = build_445_calendar(**(ch.fiscal or cl.fiscal).calendar_kwargs())
        notes.append(
            f"fiscal grid: {len(cal)} weeks, {cal['period'].nunique()} periods, "
            f"{cal['week_starting_date'].min():%Y-%m-%d} .. "
            f"{cal['week_ending_date'].max():%Y-%m-%d}"
        )
        built, recon, extra = _crosstab_series(ch, cl, files, cal, notes)
    else:
        built, extra = _flat_rows(ch, cl, files, window, notes, apply_fixes)

    # -- project onto the template ----------------------------------------
    derived = {
        k: (lambda f, e=v, w=f"channels.{ch.name}.derived.{k}": _derive(e, f, w))
        for k, v in ch.derived.items()
    }
    mapping = {k: v for k, v in ch.mapping.items() if v in built.columns}
    for c in ch.output_columns:
        if c in built.columns and c not in mapping and c not in ch.constants and c not in derived:
            mapping[c] = c
    # Fill against a copy of the spec with its date formatting stripped. The
    # pipeline formats dates once, at the end, in `format_output` -- and it
    # must, because ordering happens in between: a Week Starting Date already
    # rendered as "1/12/2025" sorts as a string, which puts January before
    # the previous September and quietly rearranges every block.
    fill_spec = replace(spec, date_columns={})
    for attr in ("significant_figures", "block_columns"):
        if hasattr(spec, attr):
            setattr(fill_spec, attr, getattr(spec, attr))
    fill = tf.fill_template(
        built,
        fill_spec,
        mapping,
        constants=ch.constants,
        derived=derived,
        keep_blank_columns=False,
    )
    out = fill.frame[[c for c in ch.output_columns if c in fill.frame.columns]].copy()
    if fill.manifest["missing_required"]:
        raise PipelineError(
            f"required template column(s) {fill.manifest['missing_required']} were not filled"
        )

    # -- emit order --------------------------------------------------------
    block_cols = [c for c in ch.dim_cols if c in out.columns]
    order = None
    if ch.sort == "block" and block_cols:
        if ref_df is not None and all(c in ref_df.columns for c in block_cols):
            order = tf.block_order_from(ref_df, block_cols)
            notes.append(f"block order taken from {ref_path.name}: {len(order)} blocks")
        elif ch.series:
            order = [
                tuple(s.dims.get(c) for c in block_cols)
                for s in ch.series
                if all(c in s.dims for c in block_cols)
            ]
            seen: set = set()
            deduped = []
            for k in order:
                if k not in seen:
                    seen.add(k)
                    deduped.append(k)
            order = deduped
            notes.append(f"block order taken from the registry: {len(order)} blocks")
        if order:
            out = tf.order_blocks(out, block_cols, order, within=WEEK_START)
    elif ch.sort == "source":
        # The maintained OLA load is one row per raw row in the extract's own
        # order. Sorting it would produce a diff on every row while every
        # value matched, which is the least useful kind of failure.
        out = out.reset_index(drop=True)
    elif ch.sort:
        cols = [c.strip() for c in ch.sort.split(",") if c.strip() in out.columns]
        if cols:
            out = out.sort_values(cols, kind="stable").reset_index(drop=True)

    # -- post-mapping drift: has the client re-specified the taxonomy? -----
    #
    # The raw-column reconciliation above catches a partner renaming itself
    # in the extract. This catches something the rules cannot see at all: the
    # client changing what the template's own columns mean. Against the real
    # previous OLA load, `Publisher ` went from 19 partner names to 4 channel
    # codes and `Objective` from 80 audience descriptors to 4 funnel stages --
    # not drift, a redefinition. Every metric reconciled perfectly throughout.
    # Nothing here is ever auto-fixed: a redefinition is a judgment call by
    # construction, and the point is to put it in front of a person.
    if ch.reconcile_output_columns:
        tdict_path = cl.template_dictionary_path()
        if not tdict_path.exists():
            notes.append(
                f"no template value dictionary at {tdict_path.name} -- post-mapping "
                "drift not checked. Seed one with `prep_cli.py seed-dictionary` from "
                "the maintained template's history."
            )
        else:
            td = reconcile.ValueDictionary.load(tdict_path)
            tfindings = reconcile.diff_values(
                out, td, ch.name, ch.reconcile_output_columns,
                metric_cols=[m for m in ch.metrics[:1] if m in out.columns],
            )
            ttable = reconcile.findings_frame(tfindings)
            tcounts = ttable["verdict"].value_counts().to_dict() if not ttable.empty else {}
            extra["template_drift"] = ttable
            extra["template_drift_counts"] = tcounts
            turnover = {}
            for col in ch.reconcile_output_columns:
                canon = td.canonical(ch.name, col)
                if not canon:
                    continue
                now = set(out[col].dropna().astype(str).unique()) if col in out.columns else set()
                retired = sorted(set(canon) - now)
                added = sorted(now - set(canon))
                if retired or added:
                    turnover[col] = {
                        "previous": len(canon), "now": len(now),
                        "retired": retired[:40], "n_retired": len(retired),
                        "new": added[:40], "n_new": len(added),
                    }
            extra["template_turnover"] = turnover
            notes.append(
                f"template-column drift vs {tdict_path.name}: {tcounts}"
                + (
                    "; TAXONOMY TURNOVER in "
                    + ", ".join(
                        f"{c} ({v['previous']}->{v['now']} values, {v['n_retired']} retired)"
                        for c, v in turnover.items()
                    )
                    if turnover
                    else "; no column redefined"
                )
            )

    numeric = out.copy()
    for m in ch.metrics:
        if m in numeric.columns:
            numeric[m] = pd.to_numeric(numeric[m], errors="coerce")
    for c in (WEEK_START, WEEK_END):
        if c in numeric.columns:
            numeric[c] = pd.to_datetime(numeric[c], errors="coerce")

    sig = ch.significant_figures
    if sig is None:
        sig = getattr(spec, "significant_figures", None)
    if sig is None and ref_df is not None:
        sig = _infer_significant_figures(ref_path, ch.metrics)
        if sig:
            notes.append(f"number format inferred from the reference: {sig} significant figures")
    formatted = tf.format_output(
        numeric,
        date_columns={c: ch.date_format for c in (WEEK_START, WEEK_END) if c in numeric.columns},
        numeric_columns=list(ch.metrics),
        significant_figures=sig,
    )

    # -- validate ----------------------------------------------------------
    suite = ch.suite_kwargs(week_col=WEEK_START)
    suite["dataset"] = ", ".join(sorted(p.name for p in files.values()))
    report = validate.run_standard_suite(numeric, **suite)
    if recon is not None:
        # Hand KV-C14 the calendar so it re-derives what each period's weekly
        # total should be, instead of judging the divisor's designed-in drift
        # as a failure. See rule_annual_conservation's docstring: the Direct
        # Mail load that reproduces the client's file byte for byte lands at
        # -1.11%, and blocking that would teach everyone to ignore the rule.
        weeks = (
            cal.groupby("period")["n_weeks_in_month"].first()
            if cal is not None and "n_weeks_in_month" in cal.columns
            else None
        )
        if extra.get("lag_warmup"):
            report.results.append(validate.rule_lag_warmup(extra["lag_warmup"]))
        for m in ch.metrics:
            report.results.append(
                validate.rule_annual_conservation(
                    recon,
                    m,
                    tolerance_pct=float(ch.thresholds.get("annual_conservation_pct", 0.5)),
                    weeks_by_period=weeks,
                    divisor=(ch.fiscal or cl.fiscal).divisor,
                )
            )
    waivers = cfgmod.apply_waivers(report, ch, load=load_label, today=today)
    if waivers["expired"]:
        notes.append(
            f"{len(waivers['expired'])} waiver(s) have expired and were NOT applied: "
            + ", ".join(f"{w.get('rule_id')} (expired {w.get('expires')})" for w in waivers["expired"])
        )
    if waivers["unused"]:
        notes.append(
            f"{len(waivers['unused'])} waiver(s) matched no failing rule (stale?): "
            + ", ".join(str(w.get("rule_id")) for w in waivers["unused"])
        )

    # -- write -------------------------------------------------------------
    stem = f"{ch.label or ch.name}".replace(" ", "_").replace("/", "-")
    if ch.status != "verified":
        stem += f"__{ch.status.upper()}"
    elif ch.status_detail:
        # Verified because a condition cleared on this run -- worth a note in
        # the manifest, not a suffix on a filename.
        notes.append(ch.status_detail)
    paths = {}
    load_path = out_dir / f"{stem}.csv"
    formatted.to_csv(load_path, index=False)
    paths["load"] = load_path
    if artefacts:
        paths["validation"] = report.to_json(out_dir / f"{stem}__validation.json")

    # -- diff against the maintained file ----------------------------------
    comparison = None
    if ref_df is not None:
        key_cols = [c for c in ch.output_columns if c not in ch.metrics]
        prod_cmp, ref_cmp = _align_for_compare(formatted, ref_df, key_cols)
        comparison = tf.compare_to_reference(
            prod_cmp,
            ref_cmp,
            key_cols=key_cols,
            value_cols=list(ch.metrics),
            tolerance=1e-6,
            rel_tolerance=rel_tolerance,
        )
        # A keyed join is the right check only when one row means one key. The
        # OLA template drops Creative_Name and Ad_ID, so 140 rows share a key
        # on BOTH sides -- legitimately and identically -- and the join
        # correctly refuses to answer. Fall back to comparing the two files as
        # bags of rows, which is the stronger claim anyway.
        if not comparison.get("match") and not comparison.get("grain_agrees", True):
            rowwise = tf.compare_rowwise(
                prod_cmp,
                ref_cmp,
                key_cols=key_cols,
                value_cols=list(ch.metrics),
                tolerance=1e-6,
                rel_tolerance=rel_tolerance,
            )
            rowwise["keyed"] = {
                k: comparison.get(k)
                for k in ("grain_agrees", "produced_rows_per_key_max", "failures")
            }
            notes.append(
                "keys are not unique on either side (max "
                f"{comparison.get('produced_rows_per_key_max')} rows per key, the same on "
                "both sides) -- compared row for row instead of by key"
            )
            comparison = rowwise
            comparison["produced_rows"] = int(len(prod_cmp))
            comparison["reference_rows"] = int(len(ref_cmp))
        comparison["rel_tolerance"] = rel_tolerance
        comparison["byte_identical"] = _byte_identical(load_path, ref_path)
        comparison["reference"] = str(ref_path)

    # -- dashboard ---------------------------------------------------------
    if dashboard:
        try:
            from .dashboard import build_dashboard

            paths["dashboard"] = build_dashboard(
                title=f"{cl.name} - {ch.label or ch.name} input review",
                subtitle=(
                    f"{suite['dataset']} | {len(numeric):,} rows | gate "
                    f"{report.gate}"
                    + (
                        f" | vs {ref_path.name}: "
                        + ("MATCH" if comparison.get("match") else "DIFFERS")
                        if comparison
                        else ""
                    )
                ),
                report=report,
                weekly=numeric,
                week_col=WEEK_START,
                metric_cols=[m for m in ch.metrics if m in numeric.columns],
                channel_col=(block_cols[-1] if block_cols else None),
                headline={"rows": len(numeric), "blocks": len(order) if order else 0},
                drift=extra.get("template_drift")
                if extra.get("template_drift") is not None
                else extra.get("drift"),
                collisions=extra.get("collisions"),
                change_log=extra.get("changelog"),
                recon=recon,
                out_path=out_dir / f"{stem}__input_review.html",
            )
        except Exception as exc:  # a dashboard is a nice-to-have, not the load
            notes.append(f"dashboard not rendered: {type(exc).__name__}: {exc}")

    manifest = {
        "client": cl.id,
        "channel": ch.name,
        "status": ch.status,
        "pipeline": ch.pipeline,
        "template_id": ch.template,
        "template_source": str(template) if template else str(cl.template_spec_path(ch.template)),
        "reference": str(ref_path) if ref_df is not None else None,
        "raw_files": {k: str(v) for k, v in files.items()},
        # Which of those files is this channel's own, so a review can name the
        # right one when the run read several.
        "source": ch.source,
        "fiscal": vars(ch.fiscal or cl.fiscal),
        "thresholds": ch.thresholds,
        "significant_figures": sig,
        "rows": int(len(formatted)),
        "columns": list(formatted.columns),
        "gate": report.gate,
        "waivers": waivers,
        "fill_manifest": fill.manifest,
        "blank_export_check": blank_check,
        "comparison": comparison,
        "notes": notes,
        "lag_warmup": extra.get("lag_warmup"),
        "template_turnover": extra.get("template_turnover"),
        "template_drift_counts": extra.get("template_drift_counts"),
        **{k: v for k, v in extra.items() if k == "series_provenance"},
    }
    if artefacts:
        paths["manifest"] = out_dir / f"{stem}__manifest.json"
        paths["manifest"].write_text(
            json.dumps(manifest, indent=2, default=str), encoding="utf-8"
        )

    result = LoadResult(
        client=cl.id,
        channel=ch.name,
        frame=formatted,
        numeric=numeric,
        report=report,
        waivers=waivers,
        comparison=comparison,
        manifest=manifest,
        paths=paths,
        notes=notes,
        status=ch.status,
        history=hist_df,
        history_source=hist_source,
        lag_profiles=dict(cl.lag_profiles or {}),
        raw_monthly=extra.get("raw_monthly"),
    )
    if artefacts:
        paths["report"] = _write_markdown(result, cl, ch, out_dir / f"{stem}__report.md")
    return result


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------




def _align_for_compare(
    produced: pd.DataFrame, reference: pd.DataFrame, key_cols: list[str]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Put both sides' key columns into one comparable form.

    Two ways a correct load looks like a total mismatch, both seen here:

    * **Dates.** The output writes ``12/28/2025`` because that is what the
      portal wants; the maintained file is read back as a Timestamp. Compared
      as strings they share no keys at all, and the diff reports every row as
      present in one side only.
    * **Blanks.** A column the load leaves deliberately empty is ``""`` on the
      produced side and ``NaN`` on the reference side. ``str(nan)`` is
      ``'nan'``, which matches nothing.

    Neither is a difference in the data, so neither should read as one. Values
    are left alone -- only the keys are normalised.
    """
    p, r = produced.copy(), reference.copy()
    for c in key_cols:
        if c not in p.columns or c not in r.columns:
            continue
        looks_datetime = pd.api.types.is_datetime64_any_dtype(r[c]) or pd.api.types.is_datetime64_any_dtype(p[c])
        if not looks_datetime:
            # A column of date strings on both sides still needs aligning when
            # the two sides wrote different date formats.
            probe_p = pd.to_datetime(p[c], errors="coerce", format="mixed")
            probe_r = pd.to_datetime(r[c], errors="coerce", format="mixed")
            looks_datetime = bool(probe_p.notna().all() and probe_r.notna().all() and len(p))
        if looks_datetime:
            p[c] = pd.to_datetime(p[c], errors="coerce", format="mixed").dt.strftime("%Y-%m-%d")
            r[c] = pd.to_datetime(r[c], errors="coerce", format="mixed").dt.strftime("%Y-%m-%d")
        p[c] = tf.as_text(p[c])
        r[c] = tf.as_text(r[c])
    return p, r


def _read_tabular(path: Path, sheet=None) -> pd.DataFrame:
    if path.suffix.lower() in {".csv", ".txt"}:
        return pd.read_csv(path)
    return pd.read_excel(path, sheet_name=sheet if sheet is not None else 0, engine="openpyxl")


def _infer_significant_figures(path: Path, metrics: list[str], cap: int = 15) -> int | None:
    """Read the reference's stored precision off the file, as text.

    The maintained files store 10 significant figures. Guessing lower rounds
    real digits away; guessing higher writes digits the reference does not
    have. Both produce a diff, and neither is a defect in the data.
    """
    if path.suffix.lower() not in {".csv", ".txt"}:
        return None
    try:
        raw = pd.read_csv(path, dtype=str)
    except Exception:
        return None
    best = 0
    for m in metrics:
        if m not in raw.columns:
            continue
        for v in raw[m].dropna().astype(str).head(5000):
            text = v.strip().lstrip("-")
            if not re.fullmatch(r"[0-9]*\.?[0-9]+", text):
                continue
            sig = len(re.sub(r"^0+", "", text.replace(".", "")).rstrip("0")) or 1
            best = max(best, sig)
    return min(best, cap) if best else None


def _byte_identical(produced: Path, reference: Path) -> bool | None:
    """Compare the two files as text, normalising line endings only."""
    if reference.suffix.lower() not in {".csv", ".txt"}:
        return None
    try:
        a = produced.read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip()
        b = reference.read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip()
    except Exception:
        return None
    return a == b


def _write_markdown(result: LoadResult, cl, ch, path: Path) -> Path:
    r, c = result.report, result.comparison
    L = [
        f"# {cl.name} — {ch.label or ch.name} load",
        "",
        f"Gate: **{result.gate}**  ",
        f"Rows: {len(result.frame):,}  ",
        f"Template: `{result.manifest['template_source']}`  ",
    ]
    if c:
        L.append(
            "Reference diff: **"
            + ("MATCH" if c.get("match") else "DIFFERS")
            + f"** against `{Path(c['reference']).name}`"
            + (" (byte-identical)" if c.get("byte_identical") else "")
            + "  "
        )
    else:
        L.append(
            "Reference diff: **NOT CHECKED** — no reference file carried any rows, "
            "so nothing here confirms the load reproduces what the client's team "
            "maintains. Agreeing totals are not that evidence.  "
        )
    L += ["", "## Validation", "", "| Rule | Severity | Status | Message |", "|---|---|---|---|"]
    for x in sorted(
        r.results, key=lambda x: ({"FAIL": 0, "WAIVED": 1, "SKIP": 2, "PASS": 3}.get(x.status, 4),)
    ):
        msg = str(x.message).replace("|", "\\|")[:220]
        L.append(f"| {x.rule_id} {x.name} | {x.severity} | {x.status} | {msg} |")
    if c and not c.get("match"):
        L += ["", "## Differences against the maintained file", "", "```json",
              json.dumps({k: v for k, v in c.items() if k != "rows"}, indent=2, default=str)[:4000],
              "```"]
    turn = (result.manifest or {}).get("template_turnover") or {}
    if turn:
        L += ["", "## Taxonomy turnover in the template's own columns", "",
              "Values the previous load used that this one does not, and vice versa. "
              "These pass every rule and reconcile to the cent; a column redefined "
              "underneath the load is only visible here.", "",
              "| Column | Previous | Now | Retired | New |", "|---|---|---|---|---|"]
        for c, v in turn.items():
            L.append(
                f"| `{c}` | {v['previous']} | {v['now']} | {v['n_retired']} | {v['n_new']} |"
            )
        for c, v in turn.items():
            if v["retired"]:
                L += ["", f"**`{c}` retired:** " + ", ".join(f"`{x}`" for x in v["retired"][:25])]
            if v["new"]:
                L += [f"**`{c}` new:** " + ", ".join(f"`{x}`" for x in v["new"][:25])]
    L += ["", "## Run notes", ""] + [f"- {n}" for n in result.notes]
    L += ["", "## Files", ""] + [f"- `{k}`: {v}" for k, v in result.paths.items()]
    path.write_text("\n".join(L), encoding="utf-8")
    return path
