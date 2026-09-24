"""kvprep.summary_html -- the input summary and the EDA as one HTML document.

Self-contained: no external requests, no fonts to fetch, no script from a CDN.
It opens from an email attachment, on a plane, on a locked-down laptop. That
constraint is the whole reason this exists rather than a hosted dashboard --
"some clients can't access a Claude Dashboard" was the requirement, and a
report that needs a login is not a report that gets read.

**One document, not two.** It carries the input summary in the client's own
layout, the exploratory analysis, and the load rules that decide whether the
file is safe to upload -- because they are all about the same figures, and a
reader of any one of them alone is missing part of the answer. Rule IDs and
thresholds are included rather than hidden: a finding somebody cannot look up
is a finding they have to take on trust, and this document is meant to be
argued with.

Charts follow the same rules as the rest of the house: small multiples rather
than one axis with twelve colours on it, one hue plus a sequential ramp, a week
with no data drawn rather than omitted, and a table under every chart, because
the number is what gets quoted in the end.
"""

from __future__ import annotations

import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from . import eda
from . import summary as summod
from .review_html import _RAMP, _chip, _e, _sparkpanel
from .review_html import _table as _html_table

TONE_FOR = {"ASK": "warning", "WATCH": "serious", "INFO": "muted"}
GATE_TONE = {"CLEAR": "good", "PROCEED WITH WARNINGS": "warning", "BLOCKED": "critical"}
ORIGIN_TONE = {summod.GENERATED: "good", summod.INFERRED: "serious", summod.CARRIED: "muted"}


def _n(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "" if v is None else str(v)
    if not np.isfinite(f):
        return ""
    if f == int(f) and abs(f) < 1e15:
        return f"{int(f):,}"
    return f"{f:,.2f}"


def _d(v) -> str:
    try:
        return pd.Timestamp(v).strftime("%d %b %Y")
    except Exception:
        return "" if v is None else str(v)


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in str(s).lower()).strip("-") or "x"


# --------------------------------------------------------------------------
# charts
# --------------------------------------------------------------------------


def _distribution(col, *, w=248, h=58) -> str:
    """Where a series' periods actually sit, rather than just its total.

    A quarter total hides everything: two channels with the same quarter can be
    one steady flight and one single burst, and the model fits those very
    differently. This draws the quartiles as a box with the individual periods
    behind it, so the shape is visible at a glance.
    """
    v = pd.to_numeric(col.values, errors="coerce")
    act = v[v.fillna(0) != 0].dropna()
    if len(act) < 4:
        return ""
    lo, q1, med, q3, hi = (float(x) for x in np.percentile(act, [0, 25, 50, 75, 100]))
    span = (hi - lo) or 1.0
    pad = 10

    def x(val: float) -> float:
        return pad + (w - 2 * pad) * ((val - lo) / span)

    dots = "".join(
        f'<circle cx="{x(float(p)):.1f}" cy="{h/2:.0f}" r="2" fill="var(--series-1)" '
        f'opacity=".22"/>'
        for p in act
    )
    box = (
        f'<rect x="{x(q1):.1f}" y="{h/2-11:.0f}" width="{max(x(q3)-x(q1),1.5):.1f}" height="22" '
        f'fill="var(--series-1)" opacity=".16" stroke="var(--series-1)" stroke-opacity=".45"/>'
        f'<line x1="{x(med):.1f}" y1="{h/2-13:.0f}" x2="{x(med):.1f}" y2="{h/2+13:.0f}" '
        f'stroke="var(--series-1)" stroke-width="2.5"/>'
    )
    return (
        f'<figure class="panel"><figcaption>{_e(col.label)}'
        f'<span class="unit">{_e(col.unit)}</span></figcaption>'
        f'<svg viewBox="0 0 {w} {h}" role="img" '
        f'aria-label="Distribution of {_e(col.label)}: median {_n(med)}, '
        f'quartiles {_n(q1)} to {_n(q3)}, range {_n(lo)} to {_n(hi)}">'
        f'<line x1="{pad}" y1="{h/2:.0f}" x2="{w-pad}" y2="{h/2:.0f}" '
        f'stroke="var(--baseline)" stroke-width="1"/>{dots}{box}</svg>'
        f'<div class="panel-foot"><span>median {_n(med)}</span>'
        f'<span>max {_n(hi)}</span></div></figure>'
    )


def _season_panel(series: eda.Series, *, w=248, h=72) -> str:
    """The month-of-year shape, twelve bars, indexed to the series' own average."""
    got = eda.seasonal_index(series if series.grain == "monthly" else eda._as_monthly(series))
    if got is None:
        return ""
    ratio, peak, peak_month, consistency = got
    if peak < 1.2:
        return ""
    pad, base = 8, h - 14
    bw = (w - 2 * pad) / 12 - 2
    bars = []
    for m in range(1, 13):
        r = float(ratio.get(m, 1.0) or 1.0)
        bh = max(1.0, (base - 6) * min(r / max(peak, 1e-9), 1.0))
        x = pad + (m - 1) * ((w - 2 * pad) / 12)
        tone = "var(--series-1)" if m == peak_month else "var(--grid)"
        bars.append(
            f'<rect x="{x:.1f}" y="{base-bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" '
            f'fill="{tone}"/>'
        )
    labels = "".join(
        f'<text x="{pad + (m-1)*((w-2*pad)/12) + bw/2:.1f}" y="{h-3}" '
        f'text-anchor="middle" font-size="7" fill="var(--muted)">'
        f'{"JFMAMJJASOND"[m-1]}</text>'
        for m in range(1, 13)
    )
    name = pd.Timestamp(2000, peak_month, 1).strftime("%B")
    return (
        f'<figure class="panel"><figcaption>{_e(series.label)}'
        f'<span class="unit">peaks in {name}</span></figcaption>'
        f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Month-of-year profile for '
        f'{_e(series.label)}; {name} runs {peak:.1f} times the monthly average">'
        f"{''.join(bars)}{labels}</svg>"
        f'<div class="panel-foot"><span>{peak:,.1f}x average</span>'
        f'<span>{consistency:.0%} of years</span></div></figure>'
    )


def _coverage_grid(sheet: summod.SummarySheet, *, max_cols: int = 160) -> str:
    """Series down, periods across; a period with no row is a visible state.

    The distinction this grid exists for: a cell that is pale because the
    number was small, and a cell that is marked because there was no row at
    all. Those look identical in a spreadsheet and mean opposite things.
    """
    if not sheet.columns or not len(sheet.index):
        return ""
    idx = sheet.index
    step = max(1, math.ceil(len(idx) / max_cols))
    shown = list(range(0, len(idx), step))
    head = "".join(
        f'<th class="rot"><span>{_d(idx[i]) if sheet.grain == "weekly" else idx[i].strftime("%b %y")}</span></th>'
        if k % max(1, len(shown) // 12) == 0
        else "<th></th>"
        for k, i in enumerate(shown)
    )
    rows = []
    for col in sheet.columns[:60]:
        v = pd.to_numeric(col.values, errors="coerce")
        act = v[v.fillna(0) != 0]
        top = float(act.max()) if len(act) else 0.0
        cells = []
        for i in shown:
            x = v.iloc[i] if i < len(v) else np.nan
            if pd.isna(x):
                cells.append('<td class="c gapc" title="no row for this period"></td>')
            elif x == 0:
                cells.append('<td class="c zero" title="reported as zero"></td>')
            else:
                k = min(len(_RAMP) - 1, int((float(x) / top) * (len(_RAMP) - 1))) if top else 0
                cells.append(
                    f'<td class="c" style="background:{_RAMP[k]}" '
                    f'title="{_e(_d(idx[i]))}: {_e(_n(x))}"></td>'
                )
        rows.append(
            f'<tr><th class="rowh">{_e(col.label)}'
            f'<span class="unit">{_e(col.unit)}</span></th>{"".join(cells)}</tr>'
        )
    legend = (
        '<p class="legend">Darker means a bigger period for that row. '
        '<span class="sw zero"></span> reported as zero &nbsp; '
        '<span class="sw gapc"></span> no row at all — which is not the same thing, '
        "and is the distinction this grid exists to make.</p>"
    )
    return (
        f'<div class="tw grid-wrap"><table class="grid"><thead><tr><th></th>{head}</tr>'
        f'</thead><tbody>{"".join(rows)}</tbody></table></div>{legend}'
    )


# --------------------------------------------------------------------------
# panes
# --------------------------------------------------------------------------


#: Roughly, how much of the channel a finding speaks for. A structural rename
#: affects every series at once and a single spike affects one period of one,
#: so listing them in the order the channels happened to run puts the biggest
#: thing in the document somewhere in the middle.
_KIND_RANK = {
    "rename": 0,
    "stopped": 1,
    "started": 2,
    "restated": 3,
    "magnitude_shift": 4,
    "divergence": 5,
    "resumed": 6,
    "rate_shift": 7,
    "qoq_step": 8,
    "level_shift": 9,
    "flat_run": 10,
    "yoy_step": 11,
    "outlier": 12,
    "seasonality": 13,
}


def _rank(items: list[tuple]) -> list[tuple]:
    return sorted(items, key=lambda so: (_KIND_RANK.get(so[1].kind, 99), so[0].name))


def _span(s: summod.InputSummary) -> str:
    """The earliest and latest period anywhere in the summary."""
    lo = min((x.index.min() for x in s.sheets if len(x.index)), default=None)
    hi = max((x.index.max() for x in s.sheets if len(x.index)), default=None)
    if lo is None:
        return "—"
    return f"{pd.Timestamp(lo).strftime('%b %Y')} – {pd.Timestamp(hi).strftime('%b %Y')}"


def _tiles(items: list[tuple[str, str, str]]) -> str:
    return (
        '<div class="tiles">'
        + "".join(
            f'<div class="tile {cls}"><b>{_e(v)}</b><span>{_e(k)}</span></div>'
            for k, v, cls in items
        )
        + "</div>"
    )


def _overview(s: summod.InputSummary, gate: str) -> str:
    asks = s.asks()
    n_series = sum(len(x.columns) for x in s.sheets)
    n_gen = sum(1 for x in s.sheets if x.origin == summod.GENERATED)
    n_inf = sum(1 for x in s.sheets if x.origin == summod.INFERRED)
    rules = s.all_findings()
    n_rules = len(rules)
    n_pass = sum(1 for f in rules if f.status == "PASS")
    n_fail = sum(1 for f in rules if f.status == "FAIL")
    parts = [
        "<h2>Overview</h2>",
        '<p class="lede">Everything below was produced from the raw extracts listed at the '
        "bottom of this page. Each channel tab shows the figures as you sent them, with the "
        "file and column each one came from; the tabs after those show what the checks found "
        "and what we need back from you.</p>",
        _tiles(
            [
                ("Channels", str(len(s.sheets)), ""),
                ("Series tracked", f"{n_series:,}", ""),
                # A span, not a count. The count would be the longest sheet's
                # number of rows, which mixes 341 weeks with 48 months and
                # means nothing on either scale.
                ("History covered", _span(s), ""),
                (
                    "Load checks passed",
                    f"{n_pass} of {n_rules}" if n_rules else "—",
                    "t-warning" if n_fail else "",
                ),
                (
                    "Questions for you",
                    str(len(asks) + len(s.rule_asks())),
                    "t-warning" if asks or s.rule_asks() else "",
                ),
            ]
        ),
    ]
    if n_inf:
        parts.append(
            f'<p class="note">{n_gen} sheet(s) came from registry channels and are '
            f"reproducible; {n_inf} were read by the generic reader and every column "
            "grouping on them is a guess. Worth converting to registry channels before "
            "this goes out again.</p>"
        )

    if asks:
        parts.append("<h3>What needs your attention</h3>")
        parts.append(
            '<p class="sub">Ordered by what matters most, not by channel: findings that '
            "cover several series at once come first, then the rest.</p>"
        )
        lis = []
        for sh, o in _rank(asks)[:14]:
            # The observation already opens with the series name, so repeating
            # it in bold in front reads as a stutter: "VA (Cases) — VA (Cases)
            # in Jan 2023 is...".
            lis.append(
                f'<li>{_chip(TONE_FOR.get(o.severity, "muted"), sh.name)}'
                f'<span class="sub">{_e(o.observation)}</span></li>'
            )
        parts.append(f'<ul class="attention">{"".join(lis)}</ul>')
        if len(asks) > 14:
            parts.append(
                f'<p class="more">{len(asks)-14} more on the '
                "<b>What we need from you</b> tab.</p>"
            )
    else:
        parts.append(
            '<ul class="attention"><li class="ok">'
            + _chip("good", "Nothing to query")
            + '<span class="sub">No check produced a question this quarter.</span></li></ul>'
        )

    rows = []
    for sh in s.sheets:
        a = sh.analysis
        rows.append(
            {
                "Sheet": sh.name,
                "Built": sh.origin,
                "Grain": sh.grain,
                "Series": len(sh.columns),
                "Periods": len(sh.index),
                "Covers": f"{_d(sh.index.min())} – {_d(sh.index.max())}" if len(sh.index) else "",
                "Questions": len(a.asks) if a else 0,
            }
        )
    parts += ["<h3>Channels in this review</h3>", _html_table(pd.DataFrame(rows))]
    if s.source_files:
        parts += [
            "<h3>Files this run read</h3>",
            _html_table(pd.DataFrame({"File": s.source_files})),
        ]
    if s.prior_path:
        parts.append(
            f'<p class="note">Compared against <b>{_e(Path(s.prior_path).name)}</b>: '
            "any figure that has changed since that file is reported as a restatement on "
            "the channel tab it belongs to.</p>"
        )
    return "".join(parts)


def _channel_pane(sheet: summod.SummarySheet) -> str:
    a = sheet.analysis
    parts = [f"<h2>{_e(sheet.name)}</h2>"]
    parts.append(
        f'<p class="lede">'
        + (
            _chip(GATE_TONE.get(sheet.gate, "muted"), sheet.gate.title())
            if sheet.gate
            else ""
        )
        + f' {_chip(ORIGIN_TONE.get(sheet.origin, "muted"), sheet.origin)} '
        f"{_e(summod.ORIGIN_NOTE[sheet.origin])}</p>"
    )
    failed = [f for f in sheet.findings if f.needs_attention]
    if failed:
        parts.append("<h3>Load checks that did not pass</h3>")
        parts.append(
            '<p class="sub">These decide whether the file can be uploaded. The observations '
            "further down are what a person would notice reading the numbers — different "
            "question, same data.</p>"
        )
        parts.append("".join(_finding_card(f) for f in failed))
    if any(c.transformed_note for c in sheet.columns):
        parts.append(
            '<p class="note"><b>These are the figures as you sent them.</b> Some of them are '
            "processed before the model sees them — the processing is described against the "
            "column below and the processed series is on the <b>Modelled series</b> tab of the "
            "workbook. Nothing on this tab has been altered.</p>"
        )

    # movement
    tot = sheet.period_totals()
    if not tot.empty:
        order = sheet.period_order
        active = [p for p in order if p in tot.index and float(tot.loc[p].abs().sum()) > 0]
        if active:
            latest = active[-1]
            li = order.index(latest)
            prior = order[li - 1] if li >= 1 else None
            yr = order[li - 4] if li >= 4 else None
            rows = []
            for (unit, label) in tot.columns:
                cur = float(tot.loc[latest, (unit, label)])
                row = {"Measure": unit, "Series": label}
                if yr:
                    row[yr] = _n(tot.loc[yr, (unit, label)])
                if prior:
                    row[prior] = _n(tot.loc[prior, (unit, label)])
                row[f"{latest} (latest)"] = _n(cur)
                if prior:
                    p = float(tot.loc[prior, (unit, label)])
                    row["QoQ"] = f"{(cur-p)/abs(p)*100:+.0f}%" if p else "—"
                if yr:
                    y = float(tot.loc[yr, (unit, label)])
                    row["YoY"] = f"{(cur-y)/abs(y)*100:+.0f}%" if y else "—"
                rows.append(row)
            parts += ["<h3>Quarter totals</h3>", _html_table(pd.DataFrame(rows), max_rows=60)]
            if latest != order[-1]:
                parts.append(
                    f'<p class="note">Compared against <b>{_e(latest)}</b>, the last quarter '
                    f"with any activity — {_e(', '.join(order[li+1:]))} carries none. "
                    "Comparing against an empty quarter would report every series as down "
                    "100%: true, and useless.</p>"
                )

    if a and a.not_shown:
        more = ", ".join(f"{n} more in {g.lower()}" for g, n in sorted(a.not_shown.items()))
        parts.append(
            f'<p class="note">The largest findings in each group are shown below; {more}. '
            "Every one of them is on the <b>Observations</b> sheet of the accompanying "
            "workbook — nothing is dropped, only ranked.</p>"
        )
    if a and a.observations:
        parts.append("<h3>What we noticed</h3>")
        cards = []
        for o in sorted(a.observations, key=lambda x: _KIND_RANK.get(x.kind, 99)):
            extra = ""
            if o.evidence:
                bits = ", ".join(
                    f"{k}={_n(v) if isinstance(v,(int,float)) else v}"
                    for k, v in list(o.evidence.items())[:6]
                    if not isinstance(v, (list, dict))
                )
                extra = f'<p class="tech">{_e(o.kind)} · {_e(bits)}</p>'
            cards.append(
                f'<div class="finding" data-tone="{TONE_FOR.get(o.severity,"muted")}">'
                f'<h4>{_chip(TONE_FOR.get(o.severity,"muted"), o.group)} {_e(o.series)}</h4>'
                f"<p>{_e(o.observation)}</p>"
                + (f'<p class="ask"><b>What we need:</b> {_e(o.question)}</p>' if o.question else "")
                + extra
                + "</div>"
            )
        parts.append("".join(cards))

    parts += ["<h3>Coverage</h3>", _coverage_grid(sheet)]

    panels = "".join(_sparkpanel(c, sheet.index) for c in sheet.columns[:24])
    if panels:
        parts += [
            "<h3>Each series over time</h3>",
            '<p class="legend">One panel per series, each on its own scale — the only way a '
            "3,000-unit series and a 3,000,000-unit one can be read on the same page. A red "
            "line marks a period with no row at all.</p>",
            f'<div class="panels">{panels}</div>',
        ]

    dists = "".join(_distribution(c) for c in sheet.columns[:24])
    if dists:
        parts += [
            "<h3>How each series is distributed</h3>",
            '<p class="legend">The box spans the middle half of the periods, the thick line is '
            "the median, and every period is a dot behind it. Two series with the same total "
            "can look completely different here, and the model treats them differently.</p>",
            f'<div class="panels">{dists}</div>',
        ]

    if a:
        seasons = "".join(
            _season_panel(
                eda.Series(
                    channel=sheet.name, label=c.label, unit=c.unit, values=c.values,
                    grain=sheet.grain,
                )
            )
            for c in sheet.columns[:24]
        )
        if seasons.strip():
            parts += [
                "<h3>Month-of-year pattern</h3>",
                '<p class="legend">Only series with a repeating annual shape are shown. The '
                "highlighted bar is the month that leads most years. We can see the pattern; "
                "we cannot see the reason, which is what the question on it is for.</p>",
                f'<div class="panels">{seasons}</div>',
            ]
        if not a.rates.empty:
            parts += [
                "<h3>Efficiency rates</h3>",
                '<p class="legend">Computed from the quarter totals. A rate that jumps by an '
                "order of magnitude almost always means one of its two inputs changed unit, "
                "not that the activity got dearer.</p>",
                _html_table(a.rates.round(2), max_rows=30),
            ]
        if not a.correlations.empty:
            parts += [
                "<h3>Series that move together</h3>",
                _html_table(a.correlations.round(2), max_rows=20),
            ]
        if a.skipped:
            parts += [
                "<h4>Checks that could not run</h4>",
                '<ul class="mini">'
                + "".join(f"<li>{_e(x)}</li>" for x in a.skipped[:20])
                + "</ul>",
            ]

    if sheet.carried_notes:
        parts += [
            "<h3>Notes carried from the previous summary</h3>",
            '<ul class="mini">'
            + "".join(f"<li>{_e(n)}</li>" for n in sheet.carried_notes[:20])
            + "</ul>",
        ]

    # Provenance last. It is the thing that makes the rest checkable rather
    # than the thing anyone opens the document for, and putting sixty-nine
    # rows of it at the top pushes the findings below the fold.
    files = sorted({c.source_file for c in sheet.columns if c.source_file})
    prov_cols = {
        "Series": [c.label for c in sheet.columns],
        "Measure": [c.unit for c in sheet.columns],
        "Column in that file": [c.source_detail or "—" for c in sheet.columns],
        "Total": [_n(c.total) for c in sheet.columns],
    }
    if len(files) != 1:
        prov_cols["From file"] = [c.source_file or "—" for c in sheet.columns]
    if any(c.transformed_note for c in sheet.columns):
        prov_cols["Processing before modelling"] = [
            c.transformed_note or "none" for c in sheet.columns
        ]
    parts += [
        "<h3>Where each series came from</h3>",
        (
            f'<p class="sub">Every series on this tab comes from '
            f"<b>{_e(files[0])}</b>.</p>"
            if len(files) == 1
            else ""
        ),
        _html_table(pd.DataFrame(prov_cols), max_rows=80),
    ]
    return "".join(parts)


#: Display order and one-line purpose for each group. The keys are the check
#: catalogue's, so a rule finding and an EDA observation about the same kind of
#: problem land in the same section.
_GROUP_ORDER = ["completeness", "consistency", "movement", "seasonality", "reconciliation"]
_GROUP_ASKS = {
    "completeness": "Is everything here — every period, every breakdown, a number in every cell that should have one?",
    "consistency": "Do the numbers keep meaning the same thing over time?",
    "movement": "What moved, or sits outside its own normal range, by enough to be worth explaining?",
    "seasonality": "Which series repeat an annual shape?",
    "reconciliation": "Do the numbers add up, and does this agree with what was published last time?",
}


def _finding_card(f) -> str:
    """One rule result, with its evidence and its rule ID."""
    bits = [
        f'<div class="finding" data-tone="{f.tone}">'
        f'<h4>{_chip(f.tone, f.status.title())} {_e(f.title)}'
        f'<span class="count">{_e(f.channel)} · {_e(f.rule_id)}</span></h4>'
    ]
    # The rule's own message is written for a log, and some of them carry a
    # dict literal. When the catalogue produced a readable headline, or an
    # evidence table below says the same thing in columns, the raw message is
    # noise with braces in it.
    has_table = any(
        (tb.get("frame") is not None and not tb["frame"].empty) for tb in f.tables
    )
    if f.headline:
        bits.append(f"<p>{_e(f.headline)}</p>")
    elif f.raw_message and not (has_table and "{" in f.raw_message):
        bits.append(f"<p>{_e(f.raw_message)}</p>")
    if f.looks_for:
        bits.append(f'<p class="sub"><b>What we checked:</b> {_e(f.looks_for)}</p>')
    if f.why_it_matters:
        bits.append(f'<p class="sub"><b>Why it matters:</b> {_e(f.why_it_matters)}</p>')
    if f.needs_attention and f.ask:
        bits.append(f'<p class="ask"><b>What we need:</b> {_e(f.ask)}</p>')
    if f.internal_only:
        bits.append(
            '<p class="tech">Ours to fix, not a question for the client.</p>'
        )
    if f.waiver:
        bits.append(
            f'<p class="tech">Waived: {_e(str(f.waiver.get("reason", ""))[:300])} '
            f'(accepted by {_e(str(f.waiver.get("accepted_by", "TBC")))})</p>'
        )
    for tbl in f.tables[:2]:
        frame = tbl.get("frame")
        if frame is not None and not frame.empty:
            if tbl.get("title"):
                bits.append(f'<h5>{_e(tbl["title"])}</h5>')
            bits.append(_html_table(frame, max_rows=12))
    bits.append("</div>")
    return "".join(bits)


def _quality_pane(s: summod.InputSummary) -> str:
    """Every check, from both engines, in one place.

    The rule suite asks "is this safe to load"; the EDA asks "what is going on
    in this data". Both are about the same figures, and a reader should not
    have to know which engine found something in order to find it. Grouped by
    what the check looks for, not by which engine ran it.
    """
    obs_by_group: dict[str, list] = {}
    for sh, o in s.observations():
        obs_by_group.setdefault(summod.EDA_GROUP_KEY.get(o.group, "movement"), []).append((sh, o))
    rules_by_group: dict[str, list] = {}
    for sh in s.sheets:
        for f in sh.findings:
            rules_by_group.setdefault(f.group or "movement", []).append(f)

    n_rules = sum(len(v) for v in rules_by_group.values())
    n_pass = sum(1 for v in rules_by_group.values() for f in v if f.status == "PASS")
    parts = [
        "<h2>Data quality</h2>",
        '<p class="lede">Every check that ran, grouped by what it looks for. Two kinds sit '
        "side by side: the <b>load rules</b>, which decide whether the file is safe to upload, "
        "and the <b>data observations</b>, which are what a person would notice reading the "
        f"numbers. A check with nothing to report is still listed — {n_pass} of {n_rules} "
        "rules came back clear, and a check that passed and a check that never ran are "
        "different things.</p>",
    ]
    seen = set(_GROUP_ORDER)
    for g in _GROUP_ORDER + [k for k in {**obs_by_group, **rules_by_group} if k not in seen]:
        rules = rules_by_group.get(g, [])
        obs = obs_by_group.get(g, [])
        if not rules and not obs:
            continue
        title = (s.groups.get(g) or {}).get("title") or g.title()
        blurb = (s.groups.get(g) or {}).get("blurb") or _GROUP_ASKS.get(g, "")
        parts.append(
            f'<div class="group"><h3>{_e(title)} '
            f'<span class="count">{len(rules)} rule(s), {len(obs)} observation(s)</span></h3>'
            f'<p class="sub">{_e(blurb.strip())}</p>'
        )
        if rules:
            order = {"FAIL": 0, "WAIVED": 1, "SKIP": 2}
            # Failures and waivers get a card each, with their evidence. Passes
            # get one line per rule naming the channels it passed for: the same
            # rule passing on five channels is five identical cards, and a wall
            # of green is exactly as unreadable as a wall of red -- it pushes
            # the one failure off the screen.
            attention = [f for f in rules if f.status != "PASS"]
            passes = [f for f in rules if f.status == "PASS"]
            for f in sorted(attention, key=lambda x: (order.get(x.status, 9), x.rule_id)):
                parts.append(_finding_card(f))
            if passes:
                by_title: dict[str, list] = {}
                for f in passes:
                    by_title.setdefault(f.title, []).append(f)
                items = "".join(
                    f'<li>{_chip("good", "Pass")}<span class="sub">{_e(title)} '
                    f'<span class="count">{_e(", ".join(sorted({g.channel for g in grp})))} '
                    f'· {_e(grp[0].rule_id)}</span></span></li>'
                    for title, grp in sorted(by_title.items())
                )
                parts.append(
                    f'<details class="passes"><summary>{len(passes)} check(s) came back '
                    f"clear here</summary>"
                    f'<ul class="attention">{items}</ul></details>'
                )
        if obs:
            parts.append("<h5>What the data showed</h5>")
            parts.append(
                _html_table(
                    pd.DataFrame(
                        [
                            {
                                "Channel": sh.name,
                                "Series": o.series,
                                "Period": o.period,
                                "What we saw": o.observation,
                                "What we need": o.question,
                            }
                            for sh, o in obs
                        ]
                    ),
                    max_rows=40,
                )
            )
        parts.append("</div>")
    return "".join(parts)


def _profile_pane(s: summod.InputSummary) -> str:
    frames = [sh.analysis.profile for sh in s.sheets if sh.analysis is not None]
    if not frames:
        return "<h2>Series profile</h2><p>Nothing profiled.</p>"
    df = pd.concat(frames, ignore_index=True)
    keep = {
        "channel": "Channel", "series": "Series", "measure": "Measure",
        "periods": "Periods", "periods_with_activity": "With activity",
        "periods_at_zero": "At zero", "periods_with_no_row": "No row",
        "total": "Total", "median_when_active": "Median", "max_when_active": "Max",
        "spread_ratio": "Max / median", "variability_pct": "Variability %",
        "share_integer": "Whole numbers",
    }
    out = df[[c for c in keep if c in df.columns]].rename(columns=keep)
    for c in ["Total", "Median", "Max"]:
        if c in out:
            out[c] = out[c].map(_n)
    for c in ["Max / median", "Variability %"]:
        if c in out:
            out[c] = out[c].map(lambda v: "" if pd.isna(v) else f"{v:,.1f}")
    if "Whole numbers" in out:
        out["Whole numbers"] = out["Whole numbers"].map(
            lambda v: "" if pd.isna(v) else f"{v:.0%}"
        )
    return (
        "<h2>Series profile</h2>"
        '<p class="lede">One row per series per measure — how much history it has, how much of '
        "that history is actually populated, and how spread out it is. <b>At zero</b> and "
        "<b>No row</b> are deliberately separate columns: the first means the file said zero, "
        "the second means the file said nothing, and the model treats them differently."
        "</p>" + _html_table(out, max_rows=200)
    )


def _asks_pane(s: summod.InputSummary) -> str:
    asks = s.asks()
    rule_asks = s.rule_asks()
    parts = [
        "<h2>What we need from you</h2>",
        '<p class="lede">Every open question, in one place — from the load rules and from '
        "reading the data. Each one names where it came from and states what was seen before "
        "what is being asked, so nothing here needs anything else open to answer.</p>",
    ]
    if rule_asks:
        parts.append("<h3>From the load checks</h3>")
        parts.append(
            _html_table(
                pd.DataFrame(
                    [
                        {
                            "#": i + 1,
                            "Check": a["title"],
                            "Channels": ", ".join(a["sheets"]),
                            "What we need": a["ask"],
                        }
                        for i, a in enumerate(rule_asks)
                    ]
                ),
                max_rows=30,
            )
        )
        parts.append("<h3>From reading the data</h3>")
    if not asks:
        parts.append(
            '<p class="ok">' + _chip("good", "Nothing outstanding")
            + " No check produced a question this quarter.</p>"
        )
        return "".join(parts)
    items = []
    for i, (sh, o) in enumerate(_rank(asks), 1):
        items.append(
            f'<li class="ask-item"><span class="num">{i}</span>'
            f"<div><h4>{_e(o.series)} <span class=\"count\">{_e(sh.name)}"
            f"{' · ' + _e(o.period) if o.period else ''}</span></h4>"
            f"<p>{_e(o.observation)}</p>"
            f'<p class="ask"><b>What we need:</b> {_e(o.question)}</p></div></li>'
        )
    parts.append(f'<ol class="asks">{"".join(items)}</ol>')
    return "".join(parts)


def _method_pane(s: summod.InputSummary, spec) -> str:
    parts = [
        "<h2>How this was built</h2>",
        '<p class="lede">So that a number in this document can be traced back to the cell it '
        "came from, and a check can be argued with.</p>",
    ]
    if s.change_log:
        parts += [
            "<h3>Change log</h3>",
            '<p class="sub">Carried from the previous input summary. This is the memory of the '
            "engagement — why a figure moved two years ago and whose decision it was.</p>",
            _html_table(
                pd.DataFrame(s.change_log, columns=["BPM", "Change"]).iloc[::-1], max_rows=45
            ),
        ]
    proposed = summod.proposed_change_log(s)
    if proposed:
        parts += [
            "<h3>Proposed change-log entries</h3>",
            '<p class="sub">Detected by this run. A change-log entry is a claim about intent, '
            "and only a person knows the intent — so these are proposals to accept, reword or "
            "drop, never entries.</p>",
            _html_table(pd.DataFrame(proposed, columns=["BPM", "Proposed entry"]), max_rows=30),
        ]
    if s.breakdowns:
        parts += [
            "<h3>How each channel is broken down for the model</h3>",
            _html_table(
                pd.DataFrame(
                    [{"Channel": k, "Breakdowns": " · ".join(v)} for k, v in s.breakdowns.items()]
                ),
                max_rows=40,
            ),
        ]
    if s.considerations:
        parts += [
            "<h3>Standing considerations</h3>",
            '<ul class="mini">' + "".join(f"<li>{_e(c)}</li>" for c in s.considerations) + "</ul>",
        ]
    th = {**eda.DEFAULT_THRESHOLDS, **(spec.thresholds if spec else {})}
    if True:
        parts += [
            "<h3>Thresholds these findings fired on</h3>",
            '<p class="sub">Every one of these lives in <code>summary.yaml</code>. Quietening a '
            "noisy check is a text edit, not a code change.</p>",
            _html_table(
                pd.DataFrame(
                    [{"Setting": k, "Value": v} for k, v in sorted(th.items())]
                ),
                max_rows=40,
            ),
        ]
    return "".join(parts)


# --------------------------------------------------------------------------
# the document
# --------------------------------------------------------------------------


def render(
    s: summod.InputSummary,
    out_path: str | Path,
    *,
    gate: str = "CLEAR",
    spec=None,
) -> Path:
    tabs = [("overview", "Overview")]
    panes = [("overview", _overview(s, gate))]
    for sh in s.sheets:
        key = _slug(sh.name)
        tabs.append((key, sh.name))
        panes.append((key, _channel_pane(sh)))
    tabs += [
        ("quality", "Data quality"),
        ("profile", "Series profile"),
        ("asks", "What we need from you"),
        ("method", "How this was built"),
    ]
    panes += [
        ("quality", _quality_pane(s)),
        ("profile", _profile_pane(s)),
        ("asks", _asks_pane(s)),
        ("method", _method_pane(s, spec)),
    ]

    nav = "".join(
        f'<button class="tab{" on" if i == 0 else ""}" data-t="{k}">{_e(label)}</button>'
        for i, (k, label) in enumerate(tabs)
    )
    body = "".join(
        f'<section class="pane{" on" if i == 0 else ""}" id="p-{k}">{h}</section>'
        for i, (k, h) in enumerate(panes)
    )
    title = f"{s.client_name} — data review" + (f" — {s.load_label}" if s.load_label else "")
    banner = ""
    html_doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_e(title)}</title><style>{_CSS}</style></head>
<body>{banner}
<header class="top">
  <div><h1>{_e(title)}</h1>
  <p class="sub">Input summary and data review · generated {_e(s.generated)}
  {" · " + _e(str(len(s.source_files))) + " source file(s)" if s.source_files else ""}</p></div>
  <div>{_chip(GATE_TONE.get(gate, "muted"), gate.title() if gate != "CLEAR" else "Ready to load")}</div>
</header>
<nav class="tabs">{nav}</nav>
<main>{body}</main>
<script>{_JS}</script>
</body></html>"""
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html_doc, encoding="utf-8")
    return p


_CSS = """
:root{color-scheme:light;
 --surface-1:#fcfcfb; --plane:#f9f9f7; --text-1:#0b0b0b; --text-2:#52514e;
 --muted:#898781; --grid:#e1e0d9; --baseline:#c3c2b7; --border:rgba(11,11,11,.10);
 --series-1:#2a78d6; --gap:#d03b3b;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
 color-scheme:dark; --surface-1:#1a1a19; --plane:#0d0d0d; --text-1:#fff;
 --text-2:#c3c2b7; --grid:#2c2c2a; --baseline:#383835; --border:rgba(255,255,255,.10);
 --series-1:#3987e5;}}
*{box-sizing:border-box}
body{margin:0;background:var(--plane);color:var(--text-1);
 font:14px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
.internal{background:#7a3d12;color:#fff;padding:6px 24px;font-size:12.5px;font-weight:600}
.top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;
 padding:22px 24px 14px;background:var(--surface-1);border-bottom:1px solid var(--border);
 flex-wrap:wrap}
h1{font-size:20px;margin:0 0 2px}
h2{font-size:18px;margin:0 0 6px}
h3{font-size:15px;margin:26px 0 8px;display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
h4{font-size:14px;margin:0 0 4px;display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
p{margin:6px 0}
.sub,.legend,.more,.note{color:var(--text-2);font-size:12.5px}
.note{background:var(--surface-1);border:1px solid var(--border);border-left:3px solid
 var(--series-1);border-radius:8px;padding:9px 12px;margin:10px 0;max-width:92ch}
.lede{color:var(--text-2);max-width:80ch}
.count{font-weight:400;color:var(--muted);font-size:12px}
.tabs{display:flex;gap:2px;overflow-x:auto;padding:0 16px;background:var(--surface-1);
 border-bottom:1px solid var(--border);position:sticky;top:0;z-index:5}
.tab{appearance:none;background:none;border:0;border-bottom:2px solid transparent;
 padding:10px 12px;font:inherit;font-size:13px;color:var(--text-2);cursor:pointer;
 white-space:nowrap}
.tab:hover{color:var(--text-1)}
.tab.on{color:var(--text-1);border-bottom-color:var(--series-1);font-weight:600}
main{padding:22px 24px 48px;max-width:1500px}
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
.tile.t-warning{border-color:#fab219}
.tw{overflow:auto;background:var(--surface-1);border:1px solid var(--border);
 border-radius:10px;max-height:78vh}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{text-align:left;padding:7px 11px;border-bottom:1px solid var(--grid);vertical-align:top}
thead th{position:sticky;top:0;background:var(--surface-1);color:var(--text-2);
 font-weight:600;font-size:12px;white-space:nowrap;z-index:1}
tbody tr:last-child td{border-bottom:0}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.cell-flag{box-shadow:inset 3px 0 0 var(--chip)}
.attention{margin:8px 0;padding:0;list-style:none}
.attention li{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;padding:8px 0;
 border-bottom:1px solid var(--grid)}
.attention li.ok{color:var(--text-2)}
.attention .sub{flex:1 1 340px}
.mini{margin:6px 0 0;padding-left:18px}
.mini li{padding:3px 0;color:var(--text-2);font-size:12.5px}
.ok{color:var(--text-2)}
.group{margin:22px 0 28px;padding-top:6px;border-top:1px solid var(--grid)}
.finding{background:var(--surface-1);border:1px solid var(--border);
 border-left:3px solid var(--muted);border-radius:10px;padding:13px 15px;margin:10px 0;
 max-width:96ch}
.finding[data-tone=warning]{border-left-color:#fab219}
.finding[data-tone=serious]{border-left-color:#ec835a}
.finding[data-tone=critical]{border-left-color:#d03b3b}
.ask{color:var(--text-2);font-size:13px}
.tech{color:var(--muted);font-size:11.5px;font-family:ui-monospace,SFMono-Regular,monospace}
.panels{display:grid;grid-template-columns:repeat(auto-fill,minmax(248px,1fr));gap:14px;
 margin-top:8px}
.panel{margin:0;background:var(--surface-1);border:1px solid var(--border);
 border-radius:10px;padding:10px 10px 8px}
.panel figcaption{font-size:12.5px;font-weight:600;display:flex;justify-content:space-between;
 gap:8px;margin-bottom:6px}
.panel .unit{font-weight:400;color:var(--muted);font-size:11px}
.panel svg{width:100%;height:auto;display:block}
.panel-foot{display:flex;justify-content:space-between;gap:8px;color:var(--muted);
 font-size:11px;margin-top:5px}
.panel-foot .warn{color:var(--gap)}
.grid-wrap{max-height:70vh}
table.grid{font-size:11px}
table.grid th.rowh{position:sticky;left:0;background:var(--surface-1);white-space:nowrap;
 font-weight:600;font-size:12px;display:flex;flex-direction:column;min-width:190px;
 border-bottom:1px solid var(--grid)}
table.grid th.rowh .unit{font-weight:400;color:var(--muted);font-size:10.5px}
table.grid th.rot{height:64px;vertical-align:bottom;padding:0 2px 4px}
table.grid th.rot span{display:block;writing-mode:vertical-rl;transform:rotate(180deg);
 font-size:10px;color:var(--muted);font-weight:400}
table.grid td.c{width:9px;min-width:9px;padding:0;height:17px;border:1px solid var(--surface-1)}
td.zero,.sw.zero{background:repeating-linear-gradient(45deg,transparent,transparent 2px,
 var(--grid) 2px,var(--grid) 3px)}
td.gapc,.sw.gapc{background:var(--gap);opacity:.5}
.sw{display:inline-block;width:11px;height:11px;border:1px solid var(--border);
 vertical-align:-1px;margin:0 2px}
.asks{list-style:none;margin:10px 0;padding:0;counter-reset:a}
.ask-item{display:flex;gap:12px;background:var(--surface-1);border:1px solid var(--border);
 border-radius:10px;padding:13px 15px;margin:10px 0;max-width:96ch}
.ask-item .num{flex:0 0 26px;height:26px;border-radius:50%;background:var(--series-1);
 color:#fff;display:grid;place-items:center;font-size:12px;font-weight:700}
code{font-family:ui-monospace,SFMono-Regular,monospace;font-size:12px}
details.passes{background:var(--surface-1);border:1px solid var(--border);
 border-radius:10px;padding:10px 14px;margin:10px 0;max-width:96ch}
details.passes summary{cursor:pointer;color:var(--text-2);font-size:13px}
details.passes .attention li{border-bottom:0;padding:4px 0}
h5{font-size:13px;margin:14px 0 4px;color:var(--text-2)}
@media (max-width:640px){main{padding:16px}.top{padding:16px}}
"""

_JS = """
document.querySelectorAll('.tab').forEach(function(b){
  b.addEventListener('click', function(){
    document.querySelectorAll('.tab').forEach(function(x){x.classList.remove('on')});
    document.querySelectorAll('.pane').forEach(function(x){x.classList.remove('on')});
    b.classList.add('on');
    var el = document.getElementById('p-' + b.dataset.t);
    if (el) el.classList.add('on');
    window.scrollTo(0,0);
  });
});
"""
