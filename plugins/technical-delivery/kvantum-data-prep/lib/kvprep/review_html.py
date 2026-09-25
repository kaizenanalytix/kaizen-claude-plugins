"""Render a :class:`kvprep.review.Review` as one self-contained HTML document.

One file, no external requests, opens from an email attachment on a laptop with
no access to anything of ours. That constraint is the whole brief: a client who
cannot reach a hosted dashboard still has to be able to check their own data.

Two renderings come out of the same review. The **client** one carries plain
language, the evidence tables, and the asks. The **internal** one adds the rule
IDs, the thresholds each check ran at, the per-series provenance and the run
notes -- everything needed to audit a finding, none of which belongs in a
document going to Abbott.

Charts are small multiples: one series per panel, one hue, so nothing depends
on telling eight colours apart, and every panel's numbers are also present in
the grid above it. Status is never carried by colour alone -- every chip pairs
its colour with a word.
"""

from __future__ import annotations

import html
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .review import Review, _fmt_date, _fmt_number, slug

# Status palette (fixed, never themed) and the chart ramp, from the house
# data-viz reference. Kept as literals here so the file stays self-contained.
_TONE = {
    "good": ("#0ca30c", "Pass"),
    "warning": ("#fab219", "Check"),
    "serious": ("#ec835a", "Accepted"),
    "critical": ("#d03b3b", "Action needed"),
    "muted": ("#898781", "Not tested"),
}
_GATE_TONE = {
    "CLEAR": "good",
    "PROCEED WITH WARNINGS": "warning",
    "BLOCKED": "critical",
}


def _e(v) -> str:
    return html.escape("" if v is None else str(v), quote=True)


def _chip(tone: str, label: str | None = None) -> str:
    color, default = _TONE.get(tone, _TONE["muted"])
    text = label or default
    mark = {"good": "✓", "warning": "!", "serious": "~", "critical": "×", "muted": "–"}[tone]
    return (
        f'<span class="chip" style="--chip:{color}">'
        f'<span class="chip-mark" aria-hidden="true">{mark}</span>{_e(text)}</span>'
    )


def _table(df: pd.DataFrame, *, max_rows: int = 40, numeric_right: bool = True) -> str:
    if df is None or df.empty:
        return ""
    shown = df.head(max_rows)
    head = "".join(f"<th>{_e(c)}</th>" for c in shown.columns)
    body = []
    for _, r in shown.iterrows():
        tds = []
        for c in shown.columns:
            v = r[c]
            txt = "" if (isinstance(v, float) and math.isnan(v)) else str(v)
            num = numeric_right and bool(
                txt and txt.replace(",", "").replace("+", "").replace("-", "")
                .replace(".", "").replace("%", "").isdigit()
            )
            flag = ""
            if isinstance(txt, str) and txt.strip().lower() in {"yes", "no"}:
                tone = "critical" if txt.strip().lower() == "yes" else "good"
                flag = f' class="cell-flag" style="--chip:{_TONE[tone][0]}"'
                tds.append(f"<td{flag}>{_e(txt)}</td>")
                continue
            tds.append(f'<td class="{"num" if num else ""}">{_e(txt)}</td>')
        body.append("<tr>" + "".join(tds) + "</tr>")
    more = (
        f'<p class="more">{len(df) - len(shown):,} further row(s) not shown; '
        "the full list is in the accompanying workbook.</p>"
        if len(df) > len(shown)
        else ""
    )
    return (
        f'<div class="tw"><table><thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table></div>{more}'
    )


# --------------------------------------------------------------------------
# charts
# --------------------------------------------------------------------------


def _sparkpanel(col, weeks: pd.DatetimeIndex, *, w=248, h=68) -> str:
    """One small-multiple panel: a single series, one hue, its own scale.

    Small multiples rather than a multi-series line: with eight or more
    breakdowns on one axis nothing is legible and the colours stop being
    distinguishable. One panel per series also means each keeps its own scale,
    which is the only way a 3,000-impression series and a 3,000,000 one can be
    read on the same page.
    """
    v = pd.to_numeric(col.values, errors="coerce")
    vals = v.to_numpy(dtype="float64")
    n = len(vals)
    if n == 0:
        return ""
    finite = vals[np.isfinite(vals)]
    vmax = float(finite.max()) if finite.size else 0.0
    vmin = min(0.0, float(finite.min()) if finite.size else 0.0)
    span = (vmax - vmin) or 1.0
    pad = 6
    def x(i): return pad + (w - 2 * pad) * (i / max(n - 1, 1))
    def y(val): return h - pad - (h - 2 * pad) * ((val - vmin) / span)

    pts, gaps = [], []
    run: list[str] = []
    for i, val in enumerate(vals):
        if np.isfinite(val):
            run.append(f"{x(i):.1f},{y(val):.1f}")
        else:
            gaps.append(i)
            if len(run) > 1:
                pts.append(" ".join(run))
            run = []
    if len(run) > 1:
        pts.append(" ".join(run))
    paths = "".join(
        f'<polyline points="{p}" fill="none" stroke="var(--series-1)" '
        f'stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
        for p in pts
    )
    # Weeks with no row at all are drawn, not omitted: a gap in the line is the
    # single most useful thing on this panel.
    gapmarks = "".join(
        f'<rect x="{x(i)-1.2:.1f}" y="{pad}" width="2.4" height="{h-2*pad}" '
        f'fill="var(--gap)" />'
        for i in gaps
    )
    last = None
    for i in range(n - 1, -1, -1):
        if np.isfinite(vals[i]):
            last = i
            break
    dot = (
        f'<circle cx="{x(last):.1f}" cy="{y(vals[last]):.1f}" r="3" fill="var(--series-1)" '
        f'stroke="var(--surface-1)" stroke-width="2"/>'
        if last is not None
        else ""
    )
    title = f"{col.label} — {col.unit}"
    return (
        f'<figure class="panel"><figcaption>{_e(col.label)}'
        f'<span class="unit">{_e(col.unit)}</span></figcaption>'
        f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{_e(title)}" preserveAspectRatio="none">'
        f'<line x1="{pad}" y1="{h-pad:.1f}" x2="{w-pad}" y2="{h-pad:.1f}" '
        f'stroke="var(--baseline)" stroke-width="1"/>'
        f"{gapmarks}{paths}{dot}</svg>"
        f'<div class="panel-foot"><span>{_e(_fmt_number(col.total))} total</span>'
        f'<span>{col.active_weeks} active wks</span>'
        f'{f"<span class=warn>{col.missing_weeks} no row</span>" if col.missing_weeks else ""}'
        "</div></figure>"
    )


# The light half of the sequential blue ramp only. A full-strength ramp turns
# a dense grid into a wall of saturated blocks -- unreadable, and the numbers
# are the point here, not the shading. The tint is a wash behind text that
# stays at full contrast.
_RAMP = ["#f2f7fe", "#e6f0fd", "#daeafc", "#cde2fb", "#c2dbf9", "#b7d3f6", "#accbf5"]


def _grid(ch, *, max_weeks: int = 200) -> str:
    """The input-summary grid: provenance header, weeks down, values across.

    Laid out the way the client's own workbook lays it out, because that is the
    layout their team already reads: which file each column came from, what
    unit it is, what the series is, then the weeks. The cell tint is magnitude
    within its own column; a week with no row is marked, not left blank, since
    blank and zero are the two states this whole document exists to tell apart.
    """
    cols = ch.columns
    if not cols:
        return '<p class="empty">No series to summarise for this channel.</p>'
    weeks = ch.weeks[-max_weeks:] if len(ch.weeks) > max_weeks else ch.weeks
    trimmed = len(ch.weeks) - len(weeks)

    norm = []
    for c in cols:
        v = pd.to_numeric(c.values, errors="coerce").reindex(weeks)
        nz = v[v.fillna(0) != 0]
        # Rank, not magnitude: media and HCP series are heavily skewed, and a
        # linear tint puts every week except the peak in the palest step.
        ranks = nz.rank(pct=True) if len(nz) else nz
        norm.append((c, v, ranks))

    head_file = "".join(f'<th class="prov">{_e(c.source_file or "—")}</th>' for c, _, _ in norm)
    head_det = "".join(
        f'<th class="prov" title="{_e(c.source_detail)}">{_e(c.source_detail or "—")}</th>'
        for c, _, _ in norm
    )
    head_unit = "".join(f"<th>{_e(c.unit)}</th>" for c, _, _ in norm)
    head_series = "".join(f'<th class="ser">{_e(c.label)}</th>' for c, _, _ in norm)

    body = []
    prev_period = None
    for wk in weeks:
        period = ch.periods.get(wk, "")
        sep = ' class="pstart"' if period != prev_period else ""
        prev_period = period
        tds = []
        for c, v, mx in norm:
            val = v.get(wk)
            if val is None or (isinstance(val, float) and math.isnan(val)):
                tds.append('<td class="nodata" title="no row for this week">·</td>')
                continue
            f = float(val)
            if f == 0:
                tds.append('<td class="zero" title="reported as zero">0</td>')
                continue
            r = float(mx.get(wk, 1.0)) if len(mx) else 1.0
            step = _RAMP[min(int(r * (len(_RAMP) - 1) + 0.5), len(_RAMP) - 1)]
            tds.append(f'<td class="num" style="--tint:{step}">{_e(_fmt_number(f))}</td>')
        body.append(
            f"<tr{sep}><th class='wk'>{_e(_fmt_date(wk))}</th>"
            f"<td class='per'>{_e(period)}</td>" + "".join(tds) + "</tr>"
        )

    note = (
        f'<p class="more">Showing the most recent {len(weeks)} weeks; '
        f"{trimmed:,} earlier week(s) are in the accompanying workbook.</p>"
        if trimmed > 0
        else ""
    )
    return (
        '<div class="gridwrap"><table class="grid">'
        f'<thead><tr><th class="wk">Source file</th><th class="per"></th>{head_file}</tr>'
        f'<tr><th class="wk">Source column</th><th class="per"></th>{head_det}</tr>'
        f'<tr><th class="wk">Unit</th><th class="per"></th>{head_unit}</tr>'
        f'<tr><th class="wk">Week</th><th class="per">Period</th>{head_series}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table></div>{note}'
        '<p class="legend"><span class="sw nodata">·</span> no row for that week '
        '<span class="sw zero">0</span> reported as zero '
        '<span class="sw tint"></span> darker means larger within its own column</p>'
    )


def _movement(ch) -> str:
    mv = ch.movement()
    if mv.empty:
        return ""
    disp = mv.copy()
    for c in disp.columns:
        if c in ("Measure", "Breakdown"):
            continue
        if c in ("QoQ", "YoY"):
            disp[c] = disp[c].map(lambda v: "" if pd.isna(v) else f"{v:+,.1f}%")
        else:
            disp[c] = disp[c].map(_fmt_number)
    head = "".join(f"<th>{_e(c)}</th>" for c in disp.columns)
    rows = []
    for i, r in disp.iterrows():
        tds = []
        for c in disp.columns:
            cls = "num" if c not in ("Measure", "Breakdown") else ""
            style = ""
            if c in ("QoQ", "YoY"):
                raw = mv.loc[i, c]
                if pd.notna(raw) and abs(float(raw)) >= 35:
                    style = f' style="--chip:{_TONE["warning"][0]}"'
                    cls += " cell-flag"
            tds.append(f'<td class="{cls}"{style}>{_e(r[c])}</td>')
        rows.append("<tr>" + "".join(tds) + "</tr>")
    dormant = ""
    if getattr(ch, "dormant_periods", None):
        dormant = (
            " <b>"
            + _e(", ".join(ch.dormant_periods))
            + "</b> carries no activity at all in the files supplied, so the"
            " comparison is made against the last period that does."
        )
    return (
        '<div class="tw"><table><thead><tr>'
        f'{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
        '<p class="more">Quarters beyond &plusmn;35% are marked. '
        "Blank means there is no comparable earlier period in the data supplied."
        f"{dormant}</p>"
    )


# --------------------------------------------------------------------------
# sections
# --------------------------------------------------------------------------


def _overview(rv: Review, audience: str) -> str:
    att = rv.attention(audience)
    crit = sum(1 for f in att if f.tone == "critical")
    warn = sum(1 for f in att if f.tone == "warning")
    passed = sum(1 for f in rv.findings(audience) if f.status == "PASS")
    weeks = max((len(c.weeks) for c in rv.channels), default=0)

    tiles = [
        ("Channels reviewed", f"{len(rv.channels)}", ""),
        ("Weeks covered", f"{weeks}", ""),
        ("Rows prepared", f"{sum(c.rows for c in rv.channels):,}", ""),
        ("Checks passed", f"{passed}", ""),
        ("Need your confirmation", f"{warn}", "warning" if warn else ""),
        ("Need action before load", f"{crit}", "critical" if crit else ""),
    ]
    tile_html = "".join(
        f'<div class="tile{" t-"+t if t else ""}"><b>{_e(v)}</b><span>{_e(k)}</span></div>'
        for k, v, t in tiles
    )

    files = pd.DataFrame(
        [
            {
                "File received": f["name"],
                "Size": f["size"],
                "Modified": f["modified"],
                "Used for": ", ".join(f["channels"]),
            }
            for f in rv.files
        ]
    )

    chrows = []
    for c in rv.channels:
        tone = _GATE_TONE.get(c.gate.split(" (")[0], "warning")
        if c.status != "verified":
            tone = "critical"
        n_att = sum(
            1 for f in c.findings
            if f.needs_attention and not (audience == "client" and f.internal_only)
        )
        chrows.append(
            f"<tr><td><a href='#t-{slug(c.name)}'>{_e(c.label)}</a></td>"
            f"<td class='num'>{c.rows:,}</td>"
            f"<td>{_e(c.load_span)}</td>"
            f"<td>{_e(c.history_span)}</td>"
            f"<td class='num'>{len(c.columns)}</td>"
            f"<td class='num'>{n_att}</td>"
            f"<td>{_chip(tone, 'Ready to load' if tone=='good' else ('Confirm items below' if tone=='warning' else 'Hold'))}</td></tr>"
        )

    att_html = (
        "".join(
            f'<li><span class="lead">{_chip(f.tone)}</span>'
            f"<b>{_e(f.channel)} — {_e(f.title)}</b>"
            f'<span class="sub">{_e(f.headline or f.raw_message)}</span></li>'
            for f in att[:12]
        )
        or '<li class="ok">Nothing needs your attention. Every check passed.</li>'
    )

    return f"""
<section class="pane" id="p-overview">
  <h2>Overview</h2>
  <p class="lede">This document is the data review for <b>{_e(rv.client_name)}</b>
    {f"— {_e(rv.load_label)}" if rv.load_label else ""}. It covers what we received,
    what we prepared from it, and the specific things we need confirmed before any
    of it goes into the model. Prepared {_e(rv.generated)}.</p>
  <div class="tiles">{tile_html}</div>

  <h3>Needs your attention</h3>
  <ol class="attention">{att_html}</ol>

  <h3>Files received</h3>
  {_table(files) or '<p class="empty">No source files recorded.</p>'}

  <h3>Channels</h3>
  <div class="tw"><table><thead><tr>
    <th>Channel</th><th>Rows prepared</th><th>Period loaded</th>
    <th>Shown in summary</th><th>Series</th><th>Items to confirm</th><th>Status</th>
  </tr></thead><tbody>{"".join(chrows)}</tbody></table></div>
  <p class="more">{_e(rv.calendar_note)}</p>
</section>"""


def _channel_pane(ch, audience: str) -> str:
    panels = "".join(_sparkpanel(c, ch.weeks) for c in ch.columns[:24])
    if ch.history_source:
        hist = f"Earlier periods in this grid come from <b>{_e(ch.history_source)}</b>. "
    elif getattr(ch, "history_note", ""):
        hist = f"{_e(ch.history_note)} "
    else:
        hist = (
            "This grid shows only the period loaded — no history file was supplied, "
            "so there is nothing here to compare a year back against. "
        )
    ch_findings = [
        f for f in ch.findings
        if f.needs_attention and not (audience == "client" and f.internal_only)
    ]
    fin = (
        "<ul class='mini'>"
        + "".join(
            f"<li>{_chip(f.tone)}<b>{_e(f.title)}</b> — {_e(f.headline or f.raw_message)}</li>"
            for f in ch_findings
        )
        + "</ul>"
        if ch_findings
        else "<p class='ok'>Every check passed for this channel.</p>"
    )
    return f"""
<section class="pane" id="p-{slug(ch.name)}">
  <h2>{_e(ch.label)}</h2>
  <p class="lede">{hist}{_fmt_number(ch.rows)} rows prepared for {_e(ch.load_span)},
     across {len(ch.columns)} series. Each column below names the file and the
     column it came from.</p>

  <h3>What this channel flagged</h3>
  {fin}

  <h3>Period totals, quarter on quarter and year on year</h3>
  {_movement(ch)}

  <h3>Coverage by week</h3>
  {_grid(ch)}

  <h3>Each series over time</h3>
  <p class="more">One panel per series, each on its own scale. A vertical mark
     is a week with no row at all.</p>
  <div class="panels">{panels}</div>
</section>"""


def _quality(rv: Review, audience: str) -> str:
    groups = rv.groups
    order = ["completeness", "consistency", "movement", "reconciliation"]
    findings = rv.findings(audience)
    out = []
    for gid in order + [g for g in groups if g not in order]:
        meta = groups.get(gid, {})
        items = [f for f in findings if f.group == gid]
        if not items:
            continue
        att = [f for f in items if f.needs_attention]
        ok = [f for f in items if not f.needs_attention]
        cards = "".join(_finding_card(f, audience) for f in att)
        okrows = "".join(
            f"<tr><td>{_e(f.channel)}</td><td>{_e(f.title)}</td>"
            f"<td>{_chip(f.tone, 'Passed' if f.status=='PASS' else 'Not tested')}</td>"
            f"<td class='sub'>{_e(f.headline or f.raw_message)}</td></tr>"
            for f in ok
        )
        out.append(
            f"""<div class="group">
  <h3>{_e(meta.get('title', gid.title()))}
    <span class="count">{len(att)} to confirm · {len(ok)} clear</span></h3>
  <p class="lede">{_e((meta.get('blurb') or '').strip())}</p>
  {cards or '<p class="ok">Nothing in this group needs attention.</p>'}
  {f'<details class="cleared"><summary>{len(ok)} check(s) that came back clear</summary>'
   f'<div class="tw"><table><thead><tr><th>Channel</th><th>Check</th><th>Result</th>'
   f'<th>Detail</th></tr></thead><tbody>{okrows}</tbody></table></div></details>' if ok else ''}
</div>"""
        )
    return f"""
<section class="pane" id="p-quality">
  <h2>Data quality</h2>
  <p class="lede">Every check we run, grouped by what it is looking for. Anything
    needing a decision is shown in full, with the actual rows behind it. Checks
    that came back clear are collapsed underneath each group.</p>
  {''.join(out)}
</section>"""


def _finding_card(f, audience: str) -> str:
    tables = []
    for t in f.tables:
        frame = t["frame"]
        if frame is None:
            continue
        if frame.empty:
            if t.get("empty_note"):
                tables.append(f'<p class="ok">{_e(t["empty_note"])}</p>')
            continue
        head = f'<h5>{_e(t["title"])}</h5>' if t.get("title") else ""
        note = f'<p class="more">{_e(t["note"])}</p>' if t.get("note") else ""
        tables.append(head + note + _table(frame))
    waiver = ""
    if f.waiver:
        waiver = (
            f'<div class="waiver"><b>Accepted by {_e(f.waiver.get("accepted_by","—"))}'
            f'</b> until {_e(f.waiver.get("expires","—"))}. {_e(f.waiver.get("reason",""))}</div>'
        )
    internal = ""
    if audience == "internal":
        internal = (
            f'<div class="internal"><code>{_e(f.rule_id)}</code> '
            f'severity {_e(f.severity)} · status {_e(f.status)}<br>{_e(f.raw_message)}</div>'
        )
    ask = (
        f'<div class="ask"><b>What we need from you</b><p>{_e(f.ask)}</p></div>'
        if f.ask and not f.ask.lower().startswith("none")
        else ""
    )
    return f"""<article class="finding" data-tone="{f.tone}">
  <header>{_chip(f.tone)}<h4>{_e(f.channel)} — {_e(f.title)}</h4>
    <span class="headline">{_e(f.headline)}</span></header>
  <div class="why">
    <p><b>What we checked.</b> {_e(f.looks_for)}</p>
    <p><b>Why it matters.</b> {_e(f.why_it_matters)}</p>
  </div>
  {waiver}
  {''.join(tables)}
  {ask}
  {internal}
</article>"""


def _asks(rv: Review, audience: str) -> str:
    rows = rv.asks(audience)
    if not rows:
        body = '<p class="ok">Nothing outstanding. Every check passed.</p>'
    else:
        items = "".join(
            f'<li data-tone="{r["tone"]}"><div class="asktop">{_chip(r["tone"])}'
            f'<b>{_e(r["title"])}</b>'
            f'<span class="sub">{_e(", ".join(r["channels"]))}</span></div>'
            f"<p>{_e(r['ask'])}</p></li>"
            for r in rows
        )
        body = f'<ol class="asks">{items}</ol>'
    return f"""
<section class="pane" id="p-asks">
  <h2>What we need from you</h2>
  <p class="lede">Every open item in one place. Each one is a question about your
    data that we cannot answer from the files alone — a line of confirmation
    against each is enough to close it.</p>
  {body}
</section>"""


def _method(rv: Review) -> str:
    rows = []
    for ch in rv.channels:
        man = ch.manifest or {}
        rows.append(
            f"<tr><td>{_e(ch.label)}</td><td><code>{_e(man.get('template_id',''))}</code></td>"
            f"<td>{_e(Path(str(man.get('template_source',''))).name)}</td>"
            f"<td>{_e(Path(str(man.get('reference') or '')).name or '—')}</td>"
            f"<td class='num'>{_e(man.get('significant_figures') or '—')}</td>"
            f"<td><code>{_e(man.get('thresholds'))}</code></td></tr>"
        )
    notes = "".join(
        f"<details><summary>{_e(ch.label)} — run notes</summary><ul>"
        + "".join(f"<li>{_e(n)}</li>" for n in ch.notes)
        + "</ul></details>"
        for ch in rv.channels
    )
    return f"""
<section class="pane" id="p-method">
  <h2>Method</h2>
  <p class="lede">Internal rendering. How each channel was prepared, at what
    thresholds, and what it was checked against.</p>
  <div class="tw"><table><thead><tr><th>Channel</th><th>Template</th>
    <th>Spec from</th><th>Diffed against</th><th>Sig figs</th><th>Thresholds</th>
  </tr></thead><tbody>{"".join(rows)}</tbody></table></div>
  <h3>Run notes</h3>{notes}
</section>"""


# --------------------------------------------------------------------------


def render_html(rv: Review, out_path: str | Path, *, audience: str = "client") -> Path:
    """Write the review as one self-contained HTML file."""
    tabs = [("overview", "Overview")]
    tabs += [(slug(c.name), c.label) for c in rv.channels]
    tabs += [("quality", "Data quality"), ("asks", "What we need from you")]
    if audience == "internal":
        tabs.append(("method", "Method"))

    nav = "".join(
        f'<button class="tab{" on" if i == 0 else ""}" data-pane="p-{tid}" '
        f'id="t-{tid}">{_e(label)}</button>'
        for i, (tid, label) in enumerate(tabs)
    )
    panes = [_overview(rv, audience)]
    panes += [_channel_pane(c, audience) for c in rv.channels]
    panes += [_quality(rv, audience), _asks(rv, audience)]
    if audience == "internal":
        panes.append(_method(rv))

    gate_tone = _GATE_TONE.get(rv.gate, "warning")
    gate_word = {
        "CLEAR": "Ready to load",
        "PROCEED WITH WARNINGS": "Ready once confirmed",
        "BLOCKED": "Not ready to load",
    }[rv.gate]

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(rv.client_name)} — data review{f" — {_e(rv.load_label)}" if rv.load_label else ""}</title>
<style>{_CSS}</style></head>
<body class="viz-root{' internal' if audience == 'internal' else ''}">
<header class="top">
  <div>
    <h1>Data review{f" — {_e(rv.load_label)}" if rv.load_label else ""}</h1>
    <p class="sub">{_e(rv.client_name)} · prepared {_e(rv.generated)}
      {' · internal copy' if audience == 'internal' else ''}</p>
  </div>
  <div class="gate">{_chip(gate_tone, gate_word)}</div>
</header>
<nav class="tabs" role="tablist">{nav}</nav>
<main>{''.join(panes)}</main>
<footer>
  <p>Prepared by Kaizen Analytix for the Kvantum Element X marketing-mix model.
     This file is self-contained — it can be saved, emailed and opened offline.</p>
</footer>
<script>{_JS}</script>
</body></html>"""
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(doc, encoding="utf-8")
    return p


_CSS = """
:root{color-scheme:light;
 --surface-1:#fcfcfb; --plane:#f9f9f7; --text-1:#0b0b0b; --text-2:#52514e;
 --muted:#898781; --grid:#e1e0d9; --baseline:#c3c2b7; --border:rgba(11,11,11,.10);
 --series-1:#2a78d6; --gap:#d03b3b; --tint:transparent;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
 color-scheme:dark; --surface-1:#1a1a19; --plane:#0d0d0d; --text-1:#fff;
 --text-2:#c3c2b7; --grid:#2c2c2a; --baseline:#383835; --border:rgba(255,255,255,.10);
 --series-1:#3987e5;}}
:root[data-theme="dark"]{color-scheme:dark; --surface-1:#1a1a19; --plane:#0d0d0d;
 --text-1:#fff; --text-2:#c3c2b7; --grid:#2c2c2a; --baseline:#383835;
 --border:rgba(255,255,255,.10); --series-1:#3987e5;}
*{box-sizing:border-box}
body{margin:0;background:var(--plane);color:var(--text-1);
 font:14px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;}
.top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;
 padding:22px 24px 14px;background:var(--surface-1);border-bottom:1px solid var(--border);
 flex-wrap:wrap}
h1{font-size:20px;margin:0 0 2px}
h2{font-size:18px;margin:0 0 6px}
h3{font-size:15px;margin:26px 0 8px;display:flex;align-items:baseline;gap:10px}
h4{font-size:14px;margin:0}
h5{font-size:13px;margin:14px 0 4px;color:var(--text-2)}
p{margin:6px 0}
.sub{color:var(--text-2);font-size:12.5px}
.lede{color:var(--text-2);max-width:78ch}
.more,.legend{color:var(--muted);font-size:12px;margin-top:6px}
.count{font-weight:400;color:var(--muted);font-size:12px}
.tabs{display:flex;gap:2px;overflow-x:auto;padding:0 16px;background:var(--surface-1);
 border-bottom:1px solid var(--border);position:sticky;top:0;z-index:5}
.tab{appearance:none;background:none;border:0;border-bottom:2px solid transparent;
 padding:10px 12px;font:inherit;font-size:13px;color:var(--text-2);cursor:pointer;
 white-space:nowrap}
.tab:hover{color:var(--text-1)}
.tab.on{color:var(--text-1);border-bottom-color:var(--series-1);font-weight:600}
main{padding:22px 24px 40px;max-width:1500px}
.pane{display:none}.pane.on{display:block}
.chip{display:inline-flex;align-items:center;gap:5px;border:1px solid var(--chip);
 color:var(--chip);border-radius:999px;padding:1px 9px 1px 6px;font-size:11.5px;
 font-weight:600;white-space:nowrap}
.chip-mark{display:inline-grid;place-items:center;width:13px;height:13px;border-radius:50%;
 background:var(--chip);color:var(--surface-1);font-size:9px;font-weight:700;line-height:1}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;
 margin:14px 0 4px}
.tile{background:var(--surface-1);border:1px solid var(--border);border-radius:10px;
 padding:12px 14px}
.tile b{display:block;font-size:24px;line-height:1.1}
.tile span{color:var(--text-2);font-size:12px}
.tile.t-warning{border-color:#fab219}.tile.t-critical{border-color:#d03b3b}
.tw{overflow-x:auto;background:var(--surface-1);border:1px solid var(--border);
 border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{text-align:left;padding:7px 11px;border-bottom:1px solid var(--grid);
 vertical-align:top}
thead th{position:sticky;top:0;background:var(--surface-1);color:var(--text-2);
 font-weight:600;font-size:12px;white-space:nowrap;z-index:1}
tbody tr:last-child td{border-bottom:0}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.cell-flag{box-shadow:inset 3px 0 0 var(--chip)}
.attention{margin:8px 0;padding:0;list-style:none}
.attention li{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;
 padding:8px 0;border-bottom:1px solid var(--grid)}
.attention li.ok{color:var(--text-2)}
.attention .sub{flex:1 1 320px}
.mini{margin:6px 0;padding:0;list-style:none}
.mini li{display:flex;gap:9px;align-items:baseline;padding:5px 0;flex-wrap:wrap}
.ok{color:var(--text-2)}
.group{margin:24px 0 30px;padding-top:6px;border-top:1px solid var(--grid)}
.finding{background:var(--surface-1);border:1px solid var(--border);
 border-left:3px solid var(--muted);border-radius:10px;padding:14px 16px;margin:12px 0}
.finding[data-tone=critical]{border-left-color:#d03b3b}
.finding[data-tone=warning]{border-left-color:#fab219}
.finding[data-tone=serious]{border-left-color:#ec835a}
.finding header{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;
 margin-bottom:8px}
.finding .headline{color:var(--muted);font-size:12.5px}
.why p{max-width:82ch;color:var(--text-2);margin:4px 0}
.why b{color:var(--text-1)}
.ask{margin-top:12px;padding:10px 12px;background:var(--plane);border-radius:8px}
.ask b{font-size:12.5px}.ask p{margin:3px 0 0;color:var(--text-2);max-width:80ch}
.waiver{margin:8px 0;padding:9px 11px;border-radius:8px;background:var(--plane);
 font-size:12.5px;color:var(--text-2)}
.internal{margin-top:10px;font-size:12px;color:var(--muted);
 border-top:1px dashed var(--grid);padding-top:8px}
.internal code{font-size:11.5px}
body:not(.internal) .internal{display:none}
details.cleared{margin-top:10px}
details summary{cursor:pointer;color:var(--text-2);font-size:12.5px;padding:4px 0}
.asks{margin:10px 0;padding-left:0;list-style:none;counter-reset:a}
.asks li{counter-increment:a;background:var(--surface-1);border:1px solid var(--border);
 border-left:3px solid var(--muted);border-radius:10px;padding:12px 14px;margin:9px 0}
.asks li[data-tone=critical]{border-left-color:#d03b3b}
.asks li[data-tone=warning]{border-left-color:#fab219}
.asks li::before{content:counter(a) ".";color:var(--muted);font-weight:700;margin-right:8px}
.asktop{display:inline-flex;gap:9px;align-items:baseline;flex-wrap:wrap}
.asks p{margin:6px 0 0;color:var(--text-2);max-width:82ch}
.gridwrap{overflow:auto;max-height:70vh;background:var(--surface-1);
 border:1px solid var(--border);border-radius:10px}
table.grid{font-size:12px}
table.grid th.wk{position:sticky;left:0;background:var(--surface-1);z-index:2;
 white-space:nowrap;font-weight:400;color:var(--text-2)}
table.grid thead th{z-index:3}
table.grid thead th.wk{z-index:4}
table.grid td,table.grid th{padding:3px 8px;border-bottom:1px solid var(--grid)}
table.grid td.num{background:var(--tint);color:#0b0b0b}
table.grid td.zero{text-align:right;color:var(--muted)}
table.grid td.nodata{text-align:center;color:#d03b3b;font-weight:700}
table.grid td.per{color:var(--muted);white-space:nowrap}
table.grid tr.pstart td,table.grid tr.pstart th{border-top:1px solid var(--baseline)}
table.grid th.prov{font-weight:400;color:var(--muted);font-size:11px;max-width:150px;
 overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
table.grid th.ser{white-space:nowrap}
.legend .sw{display:inline-grid;place-items:center;width:18px;height:16px;
 border:1px solid var(--grid);border-radius:4px;margin:0 4px 0 12px;vertical-align:-3px;
 font-size:10px;font-weight:700}
.legend .sw.nodata{color:#d03b3b}.legend .sw.zero{color:var(--muted)}
.legend .sw.tint{background:linear-gradient(90deg,#cde2fb,#3987e5)}
.panels{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;
 margin-top:10px}
.panel{margin:0;background:var(--surface-1);border:1px solid var(--border);
 border-radius:10px;padding:10px 12px}
.panel figcaption{font-size:12.5px;font-weight:600;display:flex;justify-content:space-between;
 gap:8px;margin-bottom:4px}
.panel .unit{font-weight:400;color:var(--muted);font-size:11.5px}
.panel svg{width:100%;height:68px;display:block}
.panel-foot{display:flex;gap:12px;color:var(--muted);font-size:11.5px;margin-top:4px;
 flex-wrap:wrap}
.panel-foot .warn{color:#d03b3b}
.empty{color:var(--muted)}
footer{padding:16px 24px 30px;color:var(--muted);font-size:12px;
 border-top:1px solid var(--border);background:var(--surface-1)}
@media print{
  .tabs{display:none}.pane{display:block!important;page-break-before:always}
  .gridwrap{max-height:none}body{background:#fff}
  details{display:block}details summary{display:none}details[open],details{}
}
@media (max-width:640px){main{padding:16px 12px 30px}.top{padding:16px 12px 12px}}
"""

_JS = """
(function(){
  var tabs=[].slice.call(document.querySelectorAll('.tab'));
  var panes=[].slice.call(document.querySelectorAll('.pane'));
  function show(id){
    panes.forEach(function(p){p.classList.toggle('on',p.id===id);});
    tabs.forEach(function(t){t.classList.toggle('on',t.dataset.pane===id);});
    try{history.replaceState(null,'','#'+id);}catch(e){}
  }
  tabs.forEach(function(t){t.addEventListener('click',function(){show(t.dataset.pane);});});
  document.addEventListener('click',function(e){
    var a=e.target.closest('a[href^="#t-"]'); if(!a)return;
    e.preventDefault();
    var t=document.getElementById(a.getAttribute('href').slice(1));
    if(t){show(t.dataset.pane);window.scrollTo(0,0);}
  });
  var initial=(location.hash||'').slice(1);
  show(panes.some(function(p){return p.id===initial;})?initial:panes[0].id);
})();
"""
