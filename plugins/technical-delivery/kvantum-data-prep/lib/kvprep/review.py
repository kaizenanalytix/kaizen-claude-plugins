"""kvprep.review -- assemble one client-ready data review from a run.

The validation suite answers "is this load safe to upload". That is not the
same question as "can we send this to Abbott and have them check it", and the
gap between the two is most of this module.

Three things are assembled here:

**The input summary.** A grid of week x series per channel, laid out the way
the client's own input summary workbook lays it out: a provenance header saying
which file and which column each series came from, the weeks running down, and
period totals with quarter-on-quarter and year-on-year underneath. Gaps are
part of the point, so a week with no data is a visible state rather than a
blank cell.

**Findings, grouped and translated.** Every rule result is paired with its
entry in ``registry/checks/catalogue.yaml``, which supplies the plain-English
title, what the check looks for, why it matters to the model, what we need back
from the client, and how to turn the rule's own ``detail`` dict into a table
with client-facing column headers. A finding whose evidence cannot be rendered
as a table is a finding somebody has to interpret, which is the thing we are
trying to stop doing.

**The asks.** Every failing check carries one. Collected in one place, deduped
across channels, they are the actual output of a data review -- the list the
client works through.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

WEEK_START = "Week Starting Date"
WEEK_END = "Week Ending Date"

#: Rules whose failure never reaches the client version -- they are ours to fix.
_DEFAULT_INTERNAL_ONLY = {"KV-C04", "KV-C14"}


def catalogue_path(registry_root: str | Path) -> Path:
    return Path(registry_root) / "checks" / "catalogue.yaml"


def load_catalogue(registry_root: str | Path) -> dict:
    p = catalogue_path(registry_root)
    if not p.exists():
        raise FileNotFoundError(
            f"no check catalogue at {p}. The review cannot describe a finding "
            "it has no description for; add the file rather than falling back "
            "to rule IDs in a client document."
        )
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


# --------------------------------------------------------------------------
# findings
# --------------------------------------------------------------------------


@dataclass
class Finding:
    """One check, said in the client's language, with its evidence attached."""

    rule_id: str
    channel: str
    group: str
    title: str
    status: str  # PASS | FAIL | WAIVED | SKIP
    severity: str
    looks_for: str = ""
    why_it_matters: str = ""
    ask: str = ""
    headline: str = ""
    raw_message: str = ""
    internal_only: bool = False
    tables: list = field(default_factory=list)  # [{title, note, frame, empty_note}]
    waiver: dict | None = None

    @property
    def needs_attention(self) -> bool:
        return self.status in {"FAIL", "WAIVED"}

    @property
    def tone(self) -> str:
        if self.status == "PASS":
            return "good"
        if self.status == "SKIP":
            return "muted"
        if self.status == "WAIVED":
            return "serious"
        return "critical" if self.severity == "BLOCK" else "warning"


def _fmt_number(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "" if v is None else str(v)
    if math.isnan(f):
        return ""
    if f == int(f) and abs(f) < 1e15:
        return f"{int(f):,}"
    return f"{f:,.2f}"


def _fmt_date(v) -> str:
    try:
        return pd.Timestamp(v).strftime("%d %b %Y")
    except Exception:
        return "" if v is None else str(v)


def _fmt_dims(v) -> str:
    if isinstance(v, dict):
        return " · ".join(str(x) for x in v.values() if x not in (None, ""))
    return "" if v is None else str(v)


def _fmt_zscore(v) -> str:
    """Say what a robust z-score means instead of printing it.

    "-5.7" is precise and unreadable. The direction and the magnitude in
    plain words are what the person confirming the week actually needs.
    """
    try:
        z = float(v)
    except (TypeError, ValueError):
        return ""
    direction = "below" if z < 0 else "above"
    return f"{abs(z):.1f}x normal variation, {direction} typical"


def _fmt_percent(v) -> str:
    try:
        return f"{float(v):,.1f}%"
    except (TypeError, ValueError):
        return "" if v is None else str(v)


def _fmt_signed_percent(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "" if v is None else str(v)
    return f"{f:+,.1f}%"


def _fmt_week_span(row_value, row: dict | None = None) -> str:
    return _fmt_date(row_value)



_PERIOD_RE = re.compile(r"^P(\d+)\s*\((\d{4}-\d{2}-\d{2})\)$")


def _fmt_period(v) -> str:
    """Render the suite's internal period key as a date a person can place.

    "P2 (2024-12-29)" is how the rule names the second fiscal block. Nobody
    outside this codebase counts blocks from the fiscal year start, so the
    report says which quarter it means by the week it begins.
    """
    m = _PERIOD_RE.match(str(v or "").strip())
    if not m:
        return "" if v is None else str(v)
    return f"Quarter beginning {_fmt_date(m.group(2))}"


#: Plain-English readings of the reasons a series could not be tested.
_REASONS = {
    "zero MAD (series is flat)": "every week carries the same value — nothing to compare",
    "fewer than 8 active weeks": "fewer than 8 weeks with any activity",
}


def _fmt_reason(v) -> str:
    t = str(v or "").strip()
    return _REASONS.get(t, t)


_FORMATTERS = {
    "number": _fmt_number,
    "date": _fmt_date,
    "dims": _fmt_dims,
    "zscore": _fmt_zscore,
    "percent": _fmt_percent,
    "signed_percent": _fmt_signed_percent,
    "period": _fmt_period,
    "reason": _fmt_reason,
}


def _render_evidence(spec: dict, detail: dict, channel: str) -> pd.DataFrame | None:
    """Turn one rule's detail dict into a table with client-facing headers."""
    if not spec:
        return None
    kind = spec.get("kind", "records")
    src = spec.get("from")

    if kind == "values":
        vals = detail.get(src) or []
        if not isinstance(vals, (list, tuple)):
            vals = [vals]
        if not vals:
            return pd.DataFrame(columns=[spec.get("label", "Value")])
        label = spec.get("label", "Value")
        rendered = [_fmt_date(v) if "week" in label.lower() or "date" in label.lower()
                    else str(v) for v in vals]
        return pd.DataFrame({label: rendered})

    if kind == "counts":
        rows = [
            {spec.get("label", "Measure"): k, spec.get("value_label", "Count"): _fmt_number(v)}
            for k, v in detail.items()
            if isinstance(v, (int, float))
        ]
        return pd.DataFrame(rows)

    if kind == "labelled_counts":
        labels = spec.get("labels", {})
        rows = [
            {"What we found": labels.get(k, k), "Rows": _fmt_number(v)}
            for k, v in detail.items()
            if k in labels and isinstance(v, (int, float)) and v
        ]
        return pd.DataFrame(rows)

    if kind == "percent_map":
        m = detail.get(src) or {}
        thr = detail.get(spec.get("threshold_from", ""), None)
        rows = []
        for k, v in m.items():
            row = {
                spec.get("label", "Breakdown"): k,
                spec.get("value_label", "Share"): _fmt_percent(v),
            }
            if thr is not None:
                row["Above threshold"] = "yes" if float(v) > float(thr) else "no"
            rows.append(row)
        rows.sort(key=lambda r: r.get("Above threshold") != "yes")
        return pd.DataFrame(rows)

    if kind == "pair":
        fields = spec.get("fields", [])
        labels = spec.get("labels", fields)
        return pd.DataFrame(
            [{lab: _fmt_date(detail.get(f)) for f, lab in zip(fields, labels)}]
        )

    if kind == "records_auto":
        recs = detail.get(src) or []
        if not recs:
            return pd.DataFrame()
        df = pd.DataFrame(recs)
        maxc = int(spec.get("max_columns", 8))
        if len(df.columns) > maxc:
            df = df.iloc[:, :maxc]
        return df

    if kind == "turnover":
        recs = detail.get(src) or []
        return pd.DataFrame(
            [{c["label"]: r.get(c["field"], "") for c in spec.get("columns", [])} for r in recs]
        )

    if kind == "comparison":
        per = detail.get("per_column") or {}
        rows = []
        for col, v in per.items():
            if not isinstance(v, dict):
                continue
            rows.append(
                {
                    "Column": col,
                    "Values compared": _fmt_number(v.get("compared")),
                    "Values that differ": _fmt_number(v.get("mismatched")),
                    "Our total": _fmt_number(v.get("produced_total")),
                    "Your file's total": _fmt_number(v.get("reference_total")),
                }
            )
        return pd.DataFrame(rows)

    # default: records with an explicit column spec
    recs = detail.get(src) or []
    if not isinstance(recs, list):
        return None
    if spec.get("collapse_weeks"):
        recs = _collapse_week_runs(recs)
    cols = spec.get("columns") or []
    out = []
    for r in recs:
        if not isinstance(r, dict):
            continue
        row = {}
        for c in cols:
            kind = c.get("kind", "")
            if kind == "week_span":
                a = _fmt_date(r.get("week"))
                b = r.get("week_to")
                row[c["label"]] = (
                    f"{a} to {_fmt_date(b)} ({r.get('n_weeks')} weeks)" if b else a
                )
                continue
            v = r.get(c["field"])
            fmt = _FORMATTERS.get(kind, lambda x: "" if x is None else str(x))
            row[c["label"]] = fmt(v)
        out.append(row)
    return pd.DataFrame(out, columns=[c["label"] for c in cols] if cols else None)



def _collapse_week_runs(recs: list[dict]) -> list[dict]:
    """Fold consecutive weeks carrying the same value into one row.

    A monthly source spread across the weeks of a fiscal block gives every week
    in that block the same number, so one unusual *month* arrives as five
    identical "unusual week" rows. Five rows that say the same thing is exactly
    the kind of output that has to be interpreted before it can be sent, so the
    run is collapsed into a single row with its span and a week count.
    """
    if not recs or "week" not in recs[0]:
        return recs
    def key(r):
        return (str(r.get("group")), r.get("metric"), round(float(r.get("value", 0)), 6))
    out, run = [], []

    def flush():
        if not run:
            return
        first, last = run[0], run[-1]
        row = dict(first)
        if len(run) > 1:
            row["week"] = first["week"]
            row["week_to"] = last["week"]
            row["n_weeks"] = len(run)
        out.append(row)

    for r in recs:
        if run and key(run[-1]) == key(r):
            prev = pd.Timestamp(run[-1]["week"])
            cur = pd.Timestamp(r["week"])
            if (cur - prev).days == 7:
                run.append(r)
                continue
        flush()
        run = [r]
    flush()
    return out


def _headline(template: str, detail: dict) -> str:
    if not template:
        return ""
    try:
        return template.format(**{k: v for k, v in detail.items()})
    except Exception:
        return ""


def findings_for(result, catalogue: dict, channel_label: str) -> list[Finding]:
    """Pair every rule result with its catalogue entry."""
    checks = catalogue.get("checks", {})
    out: list[Finding] = []
    for r in (result.report.results if result.report else []):
        entry = checks.get(r.rule_id, {})
        detail = dict(r.detail or {})
        f = Finding(
            rule_id=r.rule_id,
            channel=channel_label,
            group=entry.get("group", "consistency"),
            title=entry.get("title", r.name),
            status=r.status,
            severity=r.severity,
            looks_for=(entry.get("looks_for") or "").strip(),
            why_it_matters=(entry.get("why_it_matters") or "").strip(),
            ask=(entry.get("ask") or "").strip(),
            headline=_headline(entry.get("headline", ""), detail),
            raw_message=r.message,
            internal_only=bool(entry.get("internal_only", r.rule_id in _DEFAULT_INTERNAL_ONLY)),
            waiver=detail.get("waiver"),
        )
        for spec, title in [(entry.get("evidence"), None), (entry.get("also"), None)]:
            if not spec:
                continue
            frame = _render_evidence(spec, detail, channel_label)
            if frame is None:
                continue
            f.tables.append(
                {
                    "title": spec.get("title", title),
                    "note": (spec.get("note") or "").strip(),
                    "frame": frame,
                    "empty_note": spec.get("empty_note", ""),
                }
            )
        out.append(f)

    # Two findings that are not rules: the reference diff and taxonomy turnover.
    if result.comparison is not None:
        entry = checks.get("REFERENCE", {})
        matched = bool(result.comparison.get("match"))
        f = Finding(
            rule_id="REFERENCE",
            channel=channel_label,
            group=entry.get("group", "reconciliation"),
            title=entry.get("title", "Reproduces the maintained file"),
            status="PASS" if matched else "FAIL",
            severity="BLOCK",
            looks_for=(entry.get("looks_for") or "").strip(),
            why_it_matters=(entry.get("why_it_matters") or "").strip(),
            ask=(entry.get("ask") or "").strip(),
            headline=(
                "matches row for row"
                if matched
                else f"{_fmt_number(result.comparison.get('mismatched'))} values differ"
            ),
            raw_message=f"compared against {Path(str(result.comparison.get('reference',''))).name}",
        )
        frame = _render_evidence(entry.get("evidence", {}), result.comparison, channel_label)
        if frame is not None and not frame.empty:
            f.tables.append({"title": None, "note": "", "frame": frame, "empty_note": ""})
        out.append(f)

    if getattr(result, "status", "verified") != "verified":
        # A channel the registry has not verified must appear in the findings,
        # not only in the filename. Otherwise the cover reads "0 need action"
        # over a document whose overall status is "not ready to load".
        out.append(
            Finding(
                rule_id="STATUS",
                channel=channel_label,
                group="reconciliation",
                title="This channel is not yet verified",
                status="FAIL",
                severity="BLOCK",
                looks_for=(
                    "Whether we can reproduce the file your team maintains for this "
                    "channel from the raw extract."
                ),
                why_it_matters=(
                    "We can identify which raw column each row comes from, but the "
                    "values in the maintained file carry a transformation that is not "
                    "documented anywhere we can see. Until that is confirmed, anything "
                    "we produce for this channel is a guess that looks like an answer."
                ),
                ask=(
                    "Confirm how this channel's figures are derived from the raw "
                    "numbers, and where the factors used live."
                ),
                headline="output withheld from the load",
                raw_message=f"registry status: {result.status}",
            )
        )

    # Where a redemption profile was inferred rather than supplied, say so as
    # a finding with an ask, not as a footnote.
    prov = (result.manifest or {}).get("series_provenance") or []
    recovered: dict[str, dict] = {}
    for p in prov:
        if p.get("profile_status") == "recovered":
            e = recovered.setdefault(
                p["profile"], {"profile": p["profile"], "series": 0}
            )
            e["series"] += 1
    if recovered:
        entry = (catalogue.get("checks") or {}).get("LAG_PROFILE", {})
        lp = getattr(result, "lag_profiles", None) or {}
        recs = []
        for name, e in recovered.items():
            pr = lp.get(name)
            recs.append(
                {
                    "profile": name,
                    "series": e["series"],
                    "months": pr.length if pr else "",
                    "total": (pr.total * 100.0) if pr else "",
                    "heldout": (pr.heldout_error_pct if pr else ""),
                }
            )
        f = Finding(
            rule_id="LAG_PROFILE",
            channel=channel_label,
            group=entry.get("group", "reconciliation"),
            title=entry.get("title", "The redemption profile is ours, not yours"),
            status="FAIL",
            severity="WARN",
            looks_for=(entry.get("looks_for") or "").strip(),
            why_it_matters=(entry.get("why_it_matters") or "").strip(),
            ask=(entry.get("ask") or "").strip(),
            headline=f"{len(recs)} inferred profile(s) in use",
            raw_message="; ".join(f"{r['profile']} on {r['series']} series" for r in recs),
        )
        frame = _render_evidence(entry.get("evidence", {}), {"profiles": recs}, channel_label)
        if frame is not None:
            f.tables.append({"title": None, "note": "", "frame": frame, "empty_note": ""})
        out.append(f)

    turnover = (result.manifest or {}).get("template_turnover") or {}
    if turnover:
        entry = checks.get("TAXONOMY", {})
        recs = [
            {"column": c, **{k: v for k, v in val.items() if k in
                             ("previous", "now", "n_retired", "n_new")}}
            for c, val in turnover.items()
        ]
        changed = [r for r in recs if r.get("n_retired") or r.get("n_new")]
        f = Finding(
            rule_id="TAXONOMY",
            channel=channel_label,
            group=entry.get("group", "consistency"),
            title=entry.get("title", "Breakdown values match previous loads"),
            status="FAIL" if changed else "PASS",
            severity="WARN",
            looks_for=(entry.get("looks_for") or "").strip(),
            why_it_matters=(entry.get("why_it_matters") or "").strip(),
            ask=(entry.get("ask") or "").strip(),
            headline=f"{len(changed)} of {len(recs)} breakdowns changed",
            raw_message="compared against the previous load's vocabulary",
        )
        frame = _render_evidence(entry.get("evidence", {}), {"turnover": recs}, channel_label)
        if frame is not None:
            f.tables.append({"title": None, "note": "", "frame": frame, "empty_note": ""})
        out.append(f)
    return out


# --------------------------------------------------------------------------
# the input summary grid
# --------------------------------------------------------------------------


@dataclass
class SeriesColumn:
    """One column of the input-summary grid: a series and where it came from."""

    key: tuple
    label: str
    unit: str
    source_file: str = ""
    source_detail: str = ""
    values: pd.Series = field(default_factory=lambda: pd.Series(dtype="float64"))

    @property
    def total(self) -> float:
        return float(pd.to_numeric(self.values, errors="coerce").sum())

    @property
    def active_weeks(self) -> int:
        v = pd.to_numeric(self.values, errors="coerce").fillna(0)
        return int((v != 0).sum())

    @property
    def missing_weeks(self) -> int:
        return int(pd.to_numeric(self.values, errors="coerce").isna().sum())


def _series_columns(frame: pd.DataFrame, by: list[str], metrics: list[str],
                    weeks: pd.DatetimeIndex, max_series: int) -> list[SeriesColumn]:
    """Pivot a load into one column per (breakdown, measure), on a common week index."""
    cols: list[SeriesColumn] = []
    if frame is None or frame.empty:
        return cols
    work = frame.copy()
    work[WEEK_START] = pd.to_datetime(work[WEEK_START], errors="coerce")
    by = [c for c in by if c in work.columns]
    for metric in metrics:
        if metric not in work.columns:
            continue
        work[metric] = pd.to_numeric(work[metric], errors="coerce")
        if by:
            g = work.groupby([WEEK_START] + by, dropna=False)[metric].sum().reset_index()
            keys = (
                g.groupby(by, dropna=False)[metric].sum().sort_values(ascending=False).index
            )
        else:
            g = work.groupby([WEEK_START], dropna=False)[metric].sum().reset_index()
            keys = [()]
        n = 0
        for key in keys:
            ktup = key if isinstance(key, tuple) else (key,)
            if n >= max_series:
                break
            sub = g
            for col, val in zip(by, ktup):
                sub = sub[sub[col].astype(str) == str(val)]
            s = sub.set_index(WEEK_START)[metric].reindex(weeks)
            cols.append(
                SeriesColumn(
                    key=ktup,
                    label=" · ".join(str(x) for x in ktup) if by else "All",
                    unit=metric,
                    values=s,
                )
            )
            n += 1
    return cols


def _attach_provenance(cols: list[SeriesColumn], result, by: list[str]) -> None:
    """Fill each column's source file and source detail from the run manifest."""
    man = result.manifest or {}
    prov = man.get("series_provenance") or []
    raw_files = man.get("raw_files") or {}
    if prov:
        index = {}
        for p in prov:
            dims = p.get("dims") or {}
            key = tuple(str(dims.get(c)) for c in by)
            index.setdefault((key, p.get("metric")), p)
        for c in cols:
            p = index.get((tuple(str(x) for x in c.key), c.unit))
            if p:
                c.source_file = Path(str(p.get("file", ""))).name
                bits = [p.get("sheet"), p.get("block"), p.get("label")]
                detail = " · ".join(str(b) for b in bits if b)
                # A transformed series must say so in the header. Otherwise the
                # provenance row names a shipments column beside a number that
                # is not shipments, which is worse than saying nothing.
                if p.get("transform"):
                    mult = p.get("multiplier", 1.0)
                    steps = []
                    if mult and abs(float(mult) - 1.0) > 1e-9:
                        steps.append(f"x {float(mult):,.2f} coupons per shipment")
                    steps.append(f"{p.get('profile')} redemption lag")
                    detail = detail + "  [" + ", then ".join(steps) + "]"
                c.source_detail = detail
            elif p is None:
                # A constant, or a series the provenance list did not name.
                c.source_detail = "not sourced from the extract"
    else:
        fill = man.get("fill_manifest") or {}
        mapping = fill.get("mapping") or {}
        # The file this channel's own source resolved to -- not simply the
        # first file of the run. A run that reads three extracts would
        # otherwise label every OLA column with the acute-care workbook, which
        # is a provenance row that is checkable and wrong: worse than blank,
        # because somebody will open that file looking for the column.
        src = getattr(getattr(result, "channel_cfg", None), "source", None) or man.get("source")
        chosen = raw_files.get(src) if src else None
        if chosen is None and len(raw_files) == 1:
            chosen = next(iter(raw_files.values()))
        src_file = Path(str(chosen)).name if chosen else ""
        for c in cols:
            c.source_file = src_file or "see the load manifest"
            c.source_detail = mapping.get(c.unit, c.unit)



def _shorten_labels(cols: list[SeriesColumn]) -> None:
    """Drop the parts of a series name that every series shares.

    "Ensure · Samples & Coupons · Direct Mail w Samples & Coupons · PC" carries
    one word of information. The constant parts are true and useless, and they
    push the part that identifies the series off the edge of the column.
    """
    if len(cols) < 2:
        return
    depth = max(len(c.key) for c in cols)
    constant = []
    for i in range(depth):
        vals = {str(c.key[i]) for c in cols if len(c.key) > i}
        if len(vals) == 1:
            constant.append(i)
    if not constant or len(constant) == depth:
        return
    for c in cols:
        kept = [str(v) for i, v in enumerate(c.key) if i not in constant]
        if kept:
            c.label = " · ".join(kept)


def fiscal_periods(weeks: pd.DatetimeIndex, year_start: str | None) -> pd.Series:
    """Label each week with a fiscal quarter, e.g. ``Q1 FY25``.

    Falls back to calendar quarters when no fiscal year start is known, and
    says which it used, because "Q3" means two different things to the two
    teams in the room.
    """
    idx = pd.DatetimeIndex(weeks)
    if not year_start:
        return pd.Series(
            [f"Q{t.quarter} {t.year}" for t in idx], index=idx, name="period"
        )
    start = pd.Timestamp(year_start)
    labels = []
    for t in idx:
        n_weeks = int((t - start).days // 7)
        yr_off, wk = divmod(n_weeks, 52)
        if n_weeks < 0:
            yr_off = -((-n_weeks + 51) // 52)
            wk = n_weeks - yr_off * 52
        q = min(wk // 13 + 1, 4)
        fy = (start.year + 1 + yr_off) % 100
        labels.append(f"Q{q} FY{fy:02d}")
    return pd.Series(labels, index=idx, name="period")


@dataclass
class ChannelReview:
    name: str
    label: str
    status: str
    gate: str
    rows: int
    weeks: pd.DatetimeIndex
    columns: list[SeriesColumn]
    periods: pd.Series
    findings: list[Finding]
    metrics: list[str]
    notes: list[str] = field(default_factory=list)
    comparison: dict | None = None
    manifest: dict = field(default_factory=dict)
    history_span: str = ""
    load_span: str = ""
    history_source: str = ""
    history_note: str = ""
    latest_period: str = ""
    dormant_periods: list = field(default_factory=list)

    # -- period arithmetic -------------------------------------------------

    def period_totals(self) -> pd.DataFrame:
        """Series x fiscal period totals, newest period last."""
        if not self.columns:
            return pd.DataFrame()
        data = {}
        for c in self.columns:
            v = pd.to_numeric(c.values, errors="coerce").fillna(0.0)
            data[(c.unit, c.label)] = v.groupby(self.periods.values).sum()
        df = pd.DataFrame(data)
        order = list(dict.fromkeys(self.periods.tolist()))
        return df.reindex([p for p in order if p in df.index])

    def movement(self) -> pd.DataFrame:
        """Latest active period against the one before it and the year before.

        "Latest" means the last period that carries any activity, not simply
        the last period on the grid. A channel whose reporting stops in August
        has an empty final quarter, and comparing against it turns every series
        into -100% -- which is arithmetically true and tells the reader nothing
        except that the check is naive.
        """
        tot = self.period_totals()
        if tot.empty:
            return pd.DataFrame()
        periods = list(tot.index)
        active = [p for p in periods if float(tot.loc[p].abs().sum()) > 0]
        if not active:
            return pd.DataFrame()
        latest = active[-1]
        li = periods.index(latest)
        prior = periods[li - 1] if li >= 1 else None
        yr_ago = periods[li - 4] if li >= 4 else None
        self.latest_period = latest
        self.dormant_periods = [p for p in periods[li + 1:]]
        rows = []
        for (unit, label) in tot.columns:
            cur = float(tot.loc[latest, (unit, label)])
            row = {"Measure": unit, "Breakdown": label}
            if yr_ago is not None:
                row[f"{yr_ago}"] = float(tot.loc[yr_ago, (unit, label)])
            if prior is not None:
                row[f"{prior}"] = float(tot.loc[prior, (unit, label)])
            row[f"{latest} (latest)"] = cur
            if prior is not None:
                p = float(tot.loc[prior, (unit, label)])
                row["QoQ"] = ((cur - p) / p * 100.0) if p else np.nan
            if yr_ago is not None:
                y = float(tot.loc[yr_ago, (unit, label)])
                row["YoY"] = ((cur - y) / y * 100.0) if y else np.nan
            rows.append(row)
        return pd.DataFrame(rows)

    def gaps(self) -> pd.DataFrame:
        """Every series' coverage: weeks with data, at zero, and with no row at all."""
        rows = []
        for c in self.columns:
            v = pd.to_numeric(c.values, errors="coerce")
            rows.append(
                {
                    "Measure": c.unit,
                    "Breakdown": c.label,
                    "Weeks in grid": len(v),
                    "Weeks with activity": int((v.fillna(0) != 0).sum()),
                    "Weeks at zero": int((v.fillna(0) == 0).sum() - v.isna().sum()),
                    "Weeks with no row": int(v.isna().sum()),
                    "First activity": _fmt_date(v[v.fillna(0) != 0].index.min())
                    if (v.fillna(0) != 0).any() else "",
                    "Last activity": _fmt_date(v[v.fillna(0) != 0].index.max())
                    if (v.fillna(0) != 0).any() else "",
                }
            )
        return pd.DataFrame(rows)


@dataclass
class Review:
    client_id: str
    client_name: str
    load_label: str
    generated: str
    channels: list[ChannelReview]
    groups: dict
    files: list[dict] = field(default_factory=list)
    calendar_note: str = ""

    @property
    def gate(self) -> str:
        gates = [c.gate for c in self.channels]
        if any(g.startswith("BLOCKED") for g in gates):
            return "BLOCKED"
        if any(g != "CLEAR" for g in gates):
            return "PROCEED WITH WARNINGS"
        return "CLEAR"

    def findings(self, audience: str = "client") -> list[Finding]:
        out = []
        for ch in self.channels:
            for f in ch.findings:
                if audience == "client" and f.internal_only:
                    continue
                out.append(f)
        return out

    def attention(self, audience: str = "client") -> list[Finding]:
        order = {"critical": 0, "warning": 1, "serious": 2}
        items = [f for f in self.findings(audience) if f.needs_attention]
        return sorted(items, key=lambda f: (order.get(f.tone, 3), f.channel, f.rule_id))

    def asks(self, audience: str = "client") -> list[dict]:
        """One row per distinct ask, with the channels it applies to."""
        by_ask: dict[str, dict] = {}
        for f in self.attention(audience):
            if not f.ask or f.ask.lower().startswith("none"):
                continue
            e = by_ask.setdefault(
                f.ask, {"ask": f.ask, "title": f.title, "channels": [], "tone": f.tone}
            )
            if f.channel not in e["channels"]:
                e["channels"].append(f.channel)
            if f.tone == "critical":
                e["tone"] = "critical"
        return list(by_ask.values())


# --------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------


def build_review(
    results: list,
    *,
    client_cfg,
    registry_root: str | Path,
    load_label: str = "",
    max_series: int = 40,
    today: date | None = None,
) -> Review:
    """Assemble one review across every channel that ran."""
    cat = load_catalogue(registry_root)
    channels: list[ChannelReview] = []
    files: dict[str, dict] = {}

    for res in results:
        ch_cfg = client_cfg.channel(res.channel)
        label = ch_cfg.label or res.channel
        load = res.numeric
        hist = getattr(res, "history", None)

        by = list(getattr(ch_cfg, "summary_by", None) or [])
        if not by:
            by = list(ch_cfg.dim_cols) if ch_cfg.pipeline == "crosstab_series" else list(
                ch_cfg.group_cols or ch_cfg.dim_cols
            )
        by = [c for c in by if c in load.columns]

        frames = [load]
        history_source = ""
        history_note = ""
        src_name = getattr(res, "history_source", "") or "the maintained template"
        if hist is not None and not hist.empty:
            h = hist.copy()
            if WEEK_START in h.columns:
                h[WEEK_START] = pd.to_datetime(h[WEEK_START], errors="coerce")
                shared = [c for c in load.columns if c in h.columns]
                load_weeks = set(pd.to_datetime(load[WEEK_START]).dropna().unique())
                h = h[~pd.to_datetime(h[WEEK_START]).isin(load_weeks)]
                if not h.empty:
                    frames.insert(0, h[shared])
                    history_source = src_name
                else:
                    # The history file covers exactly the weeks being loaded, so
                    # it adds nothing to the grid. Saying "no history supplied"
                    # here would be wrong and would send someone looking for a
                    # file that was in fact provided.
                    history_note = (
                        f"{src_name} was supplied as history but covers the same "
                        "weeks as this load, so it adds no earlier periods."
                    )
            else:
                history_note = (
                    f"{src_name} has no '{WEEK_START}' column, so it could not be "
                    "used as history."
                )
        combined = pd.concat(frames, ignore_index=True)
        combined[WEEK_START] = pd.to_datetime(combined[WEEK_START], errors="coerce")
        weeks = pd.DatetimeIndex(
            sorted(combined[WEEK_START].dropna().unique())
        )

        cols = _series_columns(combined, by, list(ch_cfg.metrics), weeks, max_series)
        _attach_provenance(cols, res, by)
        _shorten_labels(cols)

        year_start = (res.manifest.get("fiscal") or {}).get("year_start")
        periods = fiscal_periods(weeks, year_start)

        lw = pd.DatetimeIndex(pd.to_datetime(load[WEEK_START], errors="coerce").dropna().unique())
        channels.append(
            ChannelReview(
                name=res.channel,
                label=label,
                status=getattr(res, "status", "verified"),
                gate=res.gate,
                rows=int(len(res.frame)),
                weeks=weeks,
                columns=cols,
                periods=periods,
                findings=findings_for(res, cat, label),
                metrics=list(ch_cfg.metrics),
                notes=list(res.notes),
                comparison=res.comparison,
                manifest=res.manifest,
                load_span=f"{_fmt_date(lw.min())} to {_fmt_date(lw.max())}" if len(lw) else "",
                history_span=(
                    f"{_fmt_date(weeks.min())} to {_fmt_date(weeks.max())}" if len(weeks) else ""
                ),
                history_source=history_source,
                history_note=history_note,
            )
        )

        for name, path in (res.manifest.get("raw_files") or {}).items():
            p = Path(str(path))
            e = files.setdefault(
                str(p),
                {"name": p.name, "source": name, "channels": [], "size": "", "modified": ""},
            )
            if label not in e["channels"]:
                e["channels"].append(label)
            try:
                st = p.stat()
                e["size"] = (
                    f"{st.st_size/1_048_576:,.1f} MB" if st.st_size >= 1_048_576
                    else f"{st.st_size/1024:,.0f} KB"
                )
                e["modified"] = datetime.fromtimestamp(st.st_mtime).strftime("%d %b %Y")
            except OSError:
                pass

    fy = client_cfg.fiscal
    return Review(
        client_id=client_cfg.id,
        client_name=client_cfg.name,
        load_label=load_label or "",
        generated=(today or date.today()).strftime("%d %B %Y"),
        channels=channels,
        groups=cat.get("groups", {}),
        files=list(files.values()),
        calendar_note=(
            f"Fiscal quarters are {'-'.join(str(x) for x in fy.pattern)} weeks from "
            f"{fy.year_start}; monthly sources are spread across weeks using a divisor "
            f"of {fy.divisor}."
        ),
    )


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-") or "x"
