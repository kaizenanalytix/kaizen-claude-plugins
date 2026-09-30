"""Build the input-review dashboard that replaces the manual input summary.

On the 1 Sep call Nitya's steer was explicit: do not automate the Excel input
summary, replace it with something you can put on screen in the client meeting
and drill into. This module renders exactly that -- one self-contained HTML page
per load, with no external dependencies, so it can be published as an artifact,
emailed, or opened from disk.

What the page shows, in the order a review meeting actually needs it:

1. The validation gate and the rules behind it.
2. Headline totals for the period.
3. Weekly flighting per channel as small multiples, which is where blank
   periods and step changes become obvious without being told about them.
4. A coverage grid: channel x week, so a delivery gap is a hole you can see.
5. Dimension value drift against the historical dictionary -- the questions to
   put back to the client.

Charts are inline SVG built here rather than by a library, so the page stays a
single file. Colors come from the validated reference palette; series identity
is never carried by color alone.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Reference palette (validated) -- light / dark steps.
PALETTE = {
    "series": [
        ("#2a78d6", "#3987e5"),
        ("#eb6834", "#d95926"),
        ("#1baf7a", "#199e70"),
    ],
    "status": {
        "good": "#0ca30c",
        "warning": "#fab219",
        "serious": "#ec835a",
        "critical": "#d03b3b",
    },
    "seq": ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"],
}

_GATE_STYLE = {
    "CLEAR": ("good", "PASS"),
    "PROCEED WITH WARNINGS": ("warning", "WARN"),
    "BLOCKED": ("critical", "BLOCKED"),
}


def _esc(v) -> str:
    return html.escape("" if v is None else str(v))


def _fmt(v, nd=0) -> str:
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return "-"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return _esc(v)
    if abs(f) >= 1_000_000_000:
        return f"{f/1e9:,.2f}B"
    if abs(f) >= 1_000_000:
        return f"{f/1e6:,.2f}M"
    if abs(f) >= 1_000:
        return f"{f:,.0f}"
    return f"{f:,.{nd}f}"


# --------------------------------------------------------------------------
# chart primitives (inline SVG)
# --------------------------------------------------------------------------


def _sparkline(
    weeks: list[str],
    values: list[float],
    *,
    width: int = 520,
    height: int = 96,
    slot: int = 0,
    flagged: set[str] | None = None,
) -> str:
    """A single-series weekly line with a hover crosshair and zero-run shading."""
    if not values:
        return '<div class="empty">no weeks</div>'
    pad_l, pad_r, pad_t, pad_b = 6, 6, 10, 16
    iw = width - pad_l - pad_r
    ih = height - pad_t - pad_b
    vmax = max(values) or 1.0
    n = len(values)
    step = iw / max(n - 1, 1)

    def X(i):
        return pad_l + i * step

    def Y(v):
        return pad_t + ih - (v / vmax) * ih

    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(values))
    area = f"{pad_l},{pad_t+ih} {pts} {pad_l+(n-1)*step:.1f},{pad_t+ih}"

    # Shade only *interior* zero runs, matching rule KV-C11. A trailing or
    # leading run of zeros means the channel had not started or has ended,
    # which KV-C11 deliberately does not flag -- shading it here would make the
    # chart contradict the rule table on the same page.
    nz = [i for i, v in enumerate(values) if v]
    zero_bands = []
    if len(nz) >= 2:
        first, last = nz[0], nz[-1]
        run = 0
        for i in range(first, last + 2):
            v = values[i] if i <= last else None
            if v == 0:
                run += 1
            else:
                if run >= 4:
                    zero_bands.append(
                        f'<rect x="{X(i-run):.1f}" y="{pad_t}" '
                        f'width="{max(step*(run-1),2):.1f}" height="{ih}" class="zrun"/>'
                    )
                run = 0

    marks = []
    for i, w in enumerate(weeks):
        cls = "pt flag" if (flagged and w in flagged) else "pt"
        marks.append(
            f'<circle cx="{X(i):.1f}" cy="{Y(values[i]):.1f}" r="{4.5 if cls.endswith("flag") else 0}" '
            f'class="{cls}"/>'
        )
        marks.append(
            f'<rect class="hit" x="{X(i)-step/2:.1f}" y="{pad_t}" width="{max(step,4):.1f}" '
            f'height="{ih}" data-w="{_esc(w)}" data-v="{_fmt(values[i])}"/>'
        )
    lo, hi = PALETTE["series"][slot % len(PALETTE["series"])]
    return (
        f'<svg class="spark" viewBox="0 0 {width} {height}" preserveAspectRatio="none" '
        f'style="--s:{lo};--sd:{hi}" role="img">'
        f'<line class="base" x1="{pad_l}" y1="{pad_t+ih}" x2="{width-pad_r}" y2="{pad_t+ih}"/>'
        + "".join(zero_bands)
        + f'<polygon class="fill" points="{area}"/>'
        + f'<polyline class="line" points="{pts}"/>'
        + "".join(marks)
        + '<line class="cross" x1="0" y1="0" x2="0" y2="0"/>'
        + "</svg>"
    )


def _coverage_grid(pivot: pd.DataFrame) -> str:
    """Channel x week grid, sequential blue by magnitude, hole = no delivery."""
    if pivot.empty:
        return '<div class="empty">no coverage data</div>'
    weeks = [str(pd.Timestamp(c).date()) for c in pivot.columns]
    steps = PALETTE["seq"]
    rows = []
    for name, row in pivot.iterrows():
        v = row.to_numpy(dtype=float)
        pos = v[v > 0]
        q = np.quantile(pos, np.linspace(0, 1, len(steps) + 1)[1:-1]) if len(pos) > 1 else None
        cells = []
        for i, x in enumerate(v):
            if not np.isfinite(x) or x <= 0:
                cells.append(f'<i class="c zero" data-w="{_esc(weeks[i])}" '
                             f'data-r="{_esc(name)}" data-v="0"></i>')
            else:
                k = int(np.searchsorted(q, x)) if q is not None else len(steps) - 1
                cells.append(
                    f'<i class="c" style="--f:{steps[min(k,len(steps)-1)]}" '
                    f'data-w="{_esc(weeks[i])}" data-r="{_esc(name)}" data-v="{_fmt(x)}"></i>'
                )
        rows.append(
            f'<div class="grow"><span class="glab">{_esc(name)}</span>'
            f'<span class="gcells">{"".join(cells)}</span></div>'
        )
    # The tick row must span exactly the cells' width, not the container's, or
    # the dates drift away from the columns they label.
    track = len(weeks) * 13  # 11px cell + 2px gap
    # A date label is ~72px wide, so only show as many ticks as fit without
    # colliding. Three ticks on a 14-week grid overlap into unreadable mush.
    if track >= 300:
        ticks = [weeks[0], weeks[len(weeks) // 2], weeks[-1]]
    elif track >= 165:
        ticks = [weeks[0], weeks[-1]]
    else:
        ticks = [weeks[0]]
    return (
        '<div class="grid">'
        + "".join(rows)
        + '<div class="grow"><span class="glab"></span>'
        + f'<span class="gticks" style="width:{track}px">'
        + "".join(f"<em>{_esc(t)}</em>" for t in ticks)
        + "</span></div>"
        + "</div>"
    )


def _table(df: pd.DataFrame, *, max_rows: int = 60, numeric_cols: tuple = ()) -> str:
    if df is None or df.empty:
        return '<div class="empty">nothing to report</div>'
    d = df.head(max_rows)
    head = "".join(f"<th>{_esc(c)}</th>" for c in d.columns)
    body = []
    for _, r in d.iterrows():
        tds = []
        for c in d.columns:
            v = r[c]
            cls = ' class="num"' if c in numeric_cols or isinstance(v, (int, float, np.number)) else ""
            tds.append(f"<td{cls}>{_esc(_fmt(v, 2) if isinstance(v, (float, np.floating)) else v)}</td>")
        body.append("<tr>" + "".join(tds) + "</tr>")
    more = (
        f'<p class="more">showing {max_rows} of {len(df)} rows</p>' if len(df) > max_rows else ""
    )
    return f'<div class="tw"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>{more}'


# --------------------------------------------------------------------------
# page
# --------------------------------------------------------------------------


def build_dashboard(
    *,
    title: str,
    subtitle: str,
    report,
    weekly: pd.DataFrame,
    week_col: str,
    metric_cols: list[str],
    channel_col: str | None = None,
    headline: dict | None = None,
    drift: pd.DataFrame | None = None,
    collisions: list[dict] | None = None,
    change_log: pd.DataFrame | None = None,
    recon: pd.DataFrame | None = None,
    out_path: str | Path = "input_review.html",
) -> Path:
    """Render the input-review dashboard to a self-contained HTML file."""
    gate = report.gate if report is not None else "CLEAR"
    tone, badge = _GATE_STYLE.get(gate, ("warning", "WARN"))

    w = weekly.copy()
    w[week_col] = pd.to_datetime(w[week_col], errors="coerce")
    # Rows with no usable week key cannot be placed on any chart. Drop them
    # here and say how much they carried, rather than letting the headline
    # tiles include volume the charts silently omit. KV-C01 fails on them.
    n_undated = int(w[week_col].isna().sum())
    undated_totals = {
        m: float(pd.to_numeric(w.loc[w[week_col].isna(), m], errors="coerce").sum())
        for m in metric_cols
        if m in w.columns
    } if n_undated else {}
    w = w[w[week_col].notna()]
    weeks_all = sorted(w[week_col].unique())
    if not weeks_all:
        raise ValueError("no rows with a usable week key -- nothing to render")

    # headline tiles
    tiles = []
    hl = headline or {}
    for k, v in hl.items():
        tiles.append(f'<div class="tile"><b>{_fmt(v)}</b><span>{_esc(k)}</span></div>')
    for m in metric_cols:
        if m in w.columns:
            tiles.append(
                f'<div class="tile"><b>{_fmt(pd.to_numeric(w[m], errors="coerce").sum())}</b>'
                f'<span>{_esc(m)}, total</span></div>'
            )
    tiles.append(
        f'<div class="tile"><b>{len(weeks_all)}</b><span>weeks '
        f'{pd.Timestamp(weeks_all[0]).date()} to {pd.Timestamp(weeks_all[-1]).date()}</span></div>'
    )
    if n_undated:
        tiles.append(
            f'<div class="tile" style="border-color:var(--crit)"><b>{n_undated}</b>'
            f'<span>rows with no week key, excluded from every chart '
            f'({", ".join(f"{k} {_fmt(v)}" for k, v in undated_totals.items())})</span></div>'
        )

    # Flagged weeks from the outlier rule, keyed by (group, metric) so a spike
    # in one channel does not put a red marker on that week in every other
    # channel's chart. A global set would make the charts disagree with the
    # rule detail on the same page.
    flagged_by: dict[tuple[str, str], set[str]] = {}
    if report is not None:
        for r in report.results:
            if r.rule_id == "KV-C10" and r.status == "FAIL":
                for f in r.detail.get("flagged", []):
                    g = f.get("group") or {}
                    key = (str(next(iter(g.values()), "All")), str(f.get("metric", "")))
                    flagged_by.setdefault(key, set()).add(f.get("week", ""))

    # small multiples: channel x metric
    groups = (
        [(str(g), sub) for g, sub in w.groupby(channel_col, dropna=False)]
        if channel_col and channel_col in w.columns
        else [("All", w)]
    )
    cards = []
    for gi, (gname, sub) in enumerate(groups):
        for mi, m in enumerate([m for m in metric_cols if m in sub.columns]):
            s = (
                sub.groupby(week_col)[m]
                .sum()
                .reindex(weeks_all, fill_value=0.0)
                .astype(float)
            )
            labels = [str(pd.Timestamp(x).date()) for x in s.index]
            flagged = flagged_by.get((gname, m), set())
            cards.append(
                '<figure class="card">'
                f'<figcaption><span class="ct">{_esc(gname)}</span>'
                f'<span class="cm">{_esc(m)} by week</span>'
                f'<span class="cv">{_fmt(s.sum())}</span></figcaption>'
                + _sparkline(labels, s.tolist(), slot=mi, flagged=flagged)
                + "</figure>"
            )

    # coverage grid on the first metric
    cov_metric = next((m for m in metric_cols if m in w.columns), None)
    cov = ""
    if cov_metric and channel_col and channel_col in w.columns:
        piv = (
            w.pivot_table(index=channel_col, columns=week_col, values=cov_metric, aggfunc="sum")
            .reindex(columns=weeks_all)
            .fillna(0.0)
        )
        cov = _coverage_grid(piv)

    # rules
    rule_rows = []
    if report is not None:
        # `.get(..., 9)` rather than `[...]`: a status this module has not seen
        # before (WAIVED was added with the registry's waiver support) must not
        # take the whole dashboard down with a KeyError.
        order = {"FAIL": 0, "WAIVED": 1, "SKIP": 2, "PASS": 3}
        for r in sorted(report.results, key=lambda r: (order.get(r.status, 9), r.rule_id)):
            t = (
                "critical"
                if (r.status == "FAIL" and r.severity == "BLOCK")
                else "warning"
                if r.status in ("FAIL", "WAIVED")
                else "serious"
                if r.status == "SKIP"
                else "good"
            )
            rule_rows.append(
                f'<details class="rule"><summary>'
                f'<span class="pill" data-t="{t}">{_esc(r.status)}</span>'
                f'<code>{_esc(r.rule_id)}</code><b>{_esc(r.name)}</b>'
                f'<span class="sev">{_esc(r.severity)}</span></summary>'
                f'<p>{_esc(r.message)}</p>'
                f'<pre>{_esc(json.dumps(r.detail, indent=2, default=str)[:6000])}</pre>'
                f"</details>"
            )

    coll_rows = []
    for c in collisions or []:
        vs = ", ".join(
            f"{v['value']!r} ({v['n_rows']} rows"
            + (f", {v.get('first_seen')}..{v.get('last_seen')}" if v.get("first_seen") else "")
            + ")"
            for v in c["variants"]
        )
        coll_rows.append(f"<li><code>{_esc(c['column'])}</code> &mdash; {_esc(vs)}</li>")

    sections = [
        ("Validation gate", f'<div class="rules">{"".join(rule_rows) or "<div class=empty>no rules run</div>"}</div>'),
        ("Weekly flighting", f'<div class="cards">{"".join(cards)}</div>'),
    ]
    if cov:
        sections.append(
            (
                "Coverage grid",
                '<p class="note">One cell per channel-week. Shading is scaled '
                "<em>within each row</em>, so it shows each channel's own pattern over "
                "time and is not comparable between rows -- a $1k channel and a $1M "
                "channel look alike here. Hatched means no delivery; a hatched cell "
                "inside an otherwise active row is a gap to raise with the client.</p>"
                + cov,
            )
        )
    if drift is not None and not drift.empty:
        sections.append(
            (
                "Dimension value drift",
                '<p class="note">New or changed dimension values compared with the '
                "historical dictionary. <em>judgment</em> rows need a human decision "
                "before the load proceeds; <em>mechanical</em> rows were fixed "
                "automatically and logged.</p>" + _table(drift),
            )
        )
    if coll_rows:
        sections.append(
            (
                "Within-load spelling collisions",
                '<p class="note">Values in this load that differ only by case, spacing '
                "or punctuation. Left unmerged, the model treats each spelling as its "
                'own variable.</p><ul class="coll">' + "".join(coll_rows) + "</ul>",
            )
        )
    if change_log is not None and not change_log.empty:
        sections.append(("Change log", _table(change_log)))
    if recon is not None and not recon.empty:
        sections.append(
            (
                "Monthly to weekly reconciliation",
                '<p class="note">Kvantum spreads a month across its fiscal weeks using a '
                "flat 4.33 divisor, which conserves the annual total but not the "
                "individual month. Per-period differences below are expected; the "
                "annual total is the figure that must reconcile.</p>" + _table(recon),
            )
        )

    nav = "".join(
        f'<a href="#s{i}">{_esc(t)}</a>' for i, (t, _) in enumerate(sections)
    )
    body = "".join(
        f'<section id="s{i}"><h2>{_esc(t)}</h2>{c}</section>'
        for i, (t, c) in enumerate(sections)
    )

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return _write(
        out_path,
        _CSS,
        f"""
<header class="hd">
  <div>
    <p class="eyebrow">Kvantum input review</p>
    <h1>{_esc(title)}</h1>
    <p class="sub">{_esc(subtitle)}</p>
  </div>
  <div class="gate" data-t="{tone}">
    <span class="pill" data-t="{tone}">{_esc(badge)}</span>
    <b>{_esc(gate)}</b>
    <span>{len(report.failures) if report else 0} rule(s) failed &middot;
      {len(report.blockers) if report else 0} blocking</span>
  </div>
</header>
<nav class="nav">{nav}</nav>
<div class="tiles">{''.join(tiles)}</div>
{body}
<footer>Generated {stamp} by kvantum-data-prep. Every figure on this page was
computed from the source file named above; none is estimated.</footer>
<div id="tip" role="status"></div>
""",
        _JS,
    )


def _write(out_path, css: str, body: str, js: str) -> Path:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        f"<title>Kvantum Input Review</title>\n<style>{css}</style>\n{body}\n<script>{js}</script>",
        encoding="utf-8",
    )
    return p


_CSS = """
:root{
  --surface-1:#fcfcfb; --surface-2:#f4f3f0; --line:#e3e1dc;
  --text-1:#0b0b0b; --text-2:#52514e; --text-3:#84837d;
  --s1:#2a78d6; --good:#0ca30c; --warn:#fab219; --serious:#ec835a; --crit:#d03b3b;
  --zrun:#f0efec;
}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
  --surface-1:#1a1a19; --surface-2:#232322; --line:#383835;
  --text-1:#fff; --text-2:#c3c2b7; --text-3:#8f8e86; --s1:#3987e5; --zrun:#2a2a28;
}}
:root[data-theme=dark]{
  --surface-1:#1a1a19; --surface-2:#232322; --line:#383835;
  --text-1:#fff; --text-2:#c3c2b7; --text-3:#8f8e86; --s1:#3987e5; --zrun:#2a2a28;
}
*{box-sizing:border-box}
body{background:var(--surface-1);color:var(--text-1);
  font:14px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  margin:0;padding:28px clamp(16px,4vw,56px) 64px;max-width:1280px;margin-inline:auto}
h1{font-size:1.5rem;margin:.15em 0 .1em;letter-spacing:-.01em}
h2{font-size:.82rem;text-transform:uppercase;letter-spacing:.07em;color:var(--text-2);
  margin:38px 0 12px;padding-bottom:7px;border-bottom:1px solid var(--line)}
.eyebrow{font-size:.7rem;text-transform:uppercase;letter-spacing:.1em;color:var(--text-3);margin:0}
.sub{color:var(--text-2);margin:.2em 0 0;font-size:.86rem}
.hd{display:flex;gap:24px;justify-content:space-between;align-items:flex-start;flex-wrap:wrap}
.gate{display:flex;flex-direction:column;gap:3px;align-items:flex-end;text-align:right;
  padding:10px 14px;border:1px solid var(--line);border-radius:10px;background:var(--surface-2)}
.gate b{font-size:.95rem}
.gate span:last-child{font-size:.74rem;color:var(--text-2)}
.pill{font-size:.66rem;font-weight:700;letter-spacing:.06em;padding:2px 7px;border-radius:5px;
  color:#fff;background:var(--text-3);white-space:nowrap}
.pill[data-t=good]{background:var(--good)}
.pill[data-t=warning]{background:var(--warn);color:#241a00}
.pill[data-t=serious]{background:var(--serious);color:#25100a}
.pill[data-t=critical]{background:var(--crit)}
.nav{display:flex;gap:6px;flex-wrap:wrap;margin:20px 0 4px}
.nav a{font-size:.76rem;color:var(--text-2);text-decoration:none;padding:4px 10px;
  border:1px solid var(--line);border-radius:99px}
.nav a:hover{color:var(--text-1);border-color:var(--text-3)}
.tiles{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin-top:18px}
.tile{border:1px solid var(--line);border-radius:10px;padding:12px 14px;background:var(--surface-2)}
.tile b{display:block;font-size:1.32rem;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.tile span{font-size:.72rem;color:var(--text-2)}
.cards{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(330px,1fr))}
.card{margin:0;border:1px solid var(--line);border-radius:10px;padding:11px 13px 6px;background:var(--surface-2)}
figcaption{display:flex;align-items:baseline;gap:8px;margin-bottom:6px}
.ct{font-weight:650;font-size:.82rem}
.cm{font-size:.7rem;color:var(--text-3)}
.cv{margin-left:auto;font-size:.78rem;color:var(--text-2);font-variant-numeric:tabular-nums}
.spark{display:block;width:100%;height:96px;overflow:visible}
.spark .line{fill:none;stroke:var(--s);stroke-width:2;vector-effect:non-scaling-stroke;
  stroke-linejoin:round}
.spark .fill{fill:var(--s);opacity:.13;stroke:none}
.spark .base{stroke:var(--line);stroke-width:1;vector-effect:non-scaling-stroke}
.spark .zrun{fill:var(--zrun)}
.spark .pt{fill:none}
.spark .pt.flag{fill:var(--crit);stroke:var(--surface-2);stroke-width:2;vector-effect:non-scaling-stroke}
.spark .hit{fill:transparent}
.spark .cross{stroke:var(--text-3);stroke-width:1;stroke-dasharray:2 2;opacity:0;
  vector-effect:non-scaling-stroke}
.spark.on .cross{opacity:1}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]) .spark .line{stroke:var(--sd)}
 :root:not([data-theme=light]) .spark .fill{fill:var(--sd)}}
:root[data-theme=dark] .spark .line{stroke:var(--sd)}
:root[data-theme=dark] .spark .fill{fill:var(--sd)}
.grid{display:flex;flex-direction:column;gap:3px;overflow-x:auto}
.grow{display:flex;align-items:center;gap:10px;min-width:max-content}
.glab{flex:0 0 190px;font-size:.74rem;color:var(--text-2);text-align:right;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.gcells{display:flex;gap:2px}
.c{width:11px;height:17px;border-radius:2px;background:var(--f);display:block}
.c.zero{background:repeating-linear-gradient(45deg,var(--line) 0 2px,transparent 2px 4px)}
.gticks{display:flex;justify-content:space-between;font-size:.66rem;color:var(--text-3);
  padding-top:3px;min-width:max-content}
.gticks em{font-style:normal;white-space:nowrap}
.rules{display:flex;flex-direction:column;gap:5px}
.rule{border:1px solid var(--line);border-radius:8px;background:var(--surface-2)}
.rule summary{display:flex;align-items:center;gap:9px;padding:8px 12px;cursor:pointer;
  list-style:none;font-size:.83rem}
.rule summary::-webkit-details-marker{display:none}
.rule code{font-size:.72rem;color:var(--text-2)}
.rule b{font-weight:600}
.sev{margin-left:auto;font-size:.66rem;color:var(--text-3);letter-spacing:.06em}
.rule p{margin:0 12px 8px;color:var(--text-2);font-size:.82rem}
.rule pre{margin:0 12px 12px;padding:10px;background:var(--surface-1);border:1px solid var(--line);
  border-radius:6px;font-size:.7rem;overflow-x:auto;color:var(--text-2)}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:8px}
table{border-collapse:collapse;width:100%;font-size:.78rem}
th,td{padding:6px 10px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}
th{background:var(--surface-2);font-weight:600;font-size:.7rem;text-transform:uppercase;
  letter-spacing:.05em;color:var(--text-2);position:sticky;top:0}
td.num{text-align:right;font-variant-numeric:tabular-nums}
tr:last-child td{border-bottom:none}
.note{color:var(--text-2);font-size:.8rem;margin:0 0 10px;max-width:76ch}
.more{font-size:.72rem;color:var(--text-3);margin:6px 0 0}
.empty{color:var(--text-3);font-size:.8rem;padding:10px 0}
.coll{margin:0;padding-left:20px;font-size:.8rem;color:var(--text-2)}
.coll code{color:var(--text-1)}
footer{margin-top:44px;padding-top:14px;border-top:1px solid var(--line);
  font-size:.72rem;color:var(--text-3);max-width:78ch}
#tip{position:fixed;pointer-events:none;opacity:0;transform:translate(-50%,-140%);
  background:var(--text-1);color:var(--surface-1);font-size:.72rem;padding:4px 8px;
  border-radius:5px;white-space:nowrap;z-index:9;transition:opacity .08s}
#tip.on{opacity:1}
"""

_JS = """
(function(){
 var tip=document.getElementById('tip');
 function show(e,txt){tip.textContent=txt;tip.style.left=e.clientX+'px';
   tip.style.top=e.clientY+'px';tip.classList.add('on');}
 function hide(){tip.classList.remove('on');}
 document.querySelectorAll('.spark').forEach(function(svg){
  var cross=svg.querySelector('.cross');
  svg.addEventListener('pointermove',function(e){
   var t=e.target.closest('.hit'); if(!t){return;}
   var x=+t.getAttribute('x')+ +t.getAttribute('width')/2;
   cross.setAttribute('x1',x);cross.setAttribute('x2',x);
   cross.setAttribute('y1',t.getAttribute('y'));
   cross.setAttribute('y2',+t.getAttribute('y')+ +t.getAttribute('height'));
   svg.classList.add('on');
   show(e,t.dataset.w+'  '+t.dataset.v);
  });
  svg.addEventListener('pointerleave',function(){svg.classList.remove('on');hide();});
 });
 document.querySelectorAll('.grid .c').forEach(function(c){
  c.addEventListener('pointerenter',function(e){show(e,c.dataset.r+'  '+c.dataset.w+'  '+c.dataset.v);});
  c.addEventListener('pointerleave',hide);
 });
})();
"""
