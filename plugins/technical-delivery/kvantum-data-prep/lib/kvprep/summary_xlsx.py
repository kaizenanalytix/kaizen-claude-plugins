"""kvprep.summary_xlsx -- write the input summary workbook.

Their layout, their fonts, their conventions, their sheet order. The rule
followed throughout is the one that applies to editing somebody else's
spreadsheet: the file's own conventions beat any general guideline. So this
writes Calibri 11 rather than Arial, accounting number formats rather than
plain ones, and green fill on new rows -- because that is what the workbook
their team reads every quarter already does.

Two things are deliberately not hardcoded.

**Every total is a formula.** The quarter totals are ``SUM`` over the week or
month rows above them, and the quarter-on-quarter and year-on-year rows divide
one total cell by another. If the client corrects a month in their copy, the
footer follows. A workbook whose totals are Python-computed constants looks
identical and silently stops agreeing with itself the moment anyone edits it.

**Nothing is written twice.** The analysis sheets reference the channel sheets
rather than restating their numbers, so there is one copy of each figure in
the file and no way for two of them to disagree.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from . import summary as summod

# Their conventions, read off the Q226 workbook.
BODY = Font(name="Calibri", size=11)
BOLD = Font(name="Calibri", size=11, bold=True)
TITLE = Font(name="Calibri", size=14, bold=True)
SMALL = Font(name="Calibri", size=9, color="FF595959")
HEAD_FILL = PatternFill("solid", fgColor="FFD9D9D9")
NEW_FILL = PatternFill("solid", fgColor="FF92D050")  # their green = new this quarter
ASK_FILL = PatternFill("solid", fgColor="FFFFF2CC")
BAD_FILL = PatternFill("solid", fgColor="FFF8CBAD")
OK_FILL = PatternFill("solid", fgColor="FFE2EFDA")
THIN = Side(style="thin", color="FFBFBFBF")
BOX = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)

NUM = '_ * #,##0_ ;_ * \\-#,##0_ ;_ * "-"??_ ;_ @_ '
MONEY = '_("$"* #,##0_);_("$"* \\(#,##0\\);_("$"* "-"??_);_(@_)'
MONEY2 = '_("$"* #,##0.00_);_("$"* \\(#,##0.00\\);_("$"* "-"??_);_(@_)'
PCT = "0%"
DATE = "mm-dd-yy"

MONEY_UNITS = {"spend", "cost", "investment", "dollars"}


def _is_money(unit: str) -> bool:
    return any(w in str(unit).lower() for w in MONEY_UNITS)


def _put(ws, r, c, value, *, font=BODY, fmt=None, fill=None, align=None, wrap=False):
    cell = ws.cell(r, c, value)
    cell.font = font
    if fmt:
        cell.number_format = fmt
    if fill:
        cell.fill = fill
    if align or wrap:
        cell.alignment = Alignment(horizontal=align or "general", wrap_text=wrap, vertical="top")
    return cell


def _autosize(ws, widths: dict):
    for col, w in widths.items():
        ws.column_dimensions[col].width = w


# --------------------------------------------------------------------------
# a channel sheet
# --------------------------------------------------------------------------


def write_channel_sheet(wb: Workbook, sheet: summod.SummarySheet) -> None:
    """One channel sheet, laid out the way their workbook lays it out."""
    ws = wb.create_sheet(sheet.name[:31])
    monthly = sheet.grain == "monthly"
    first_col = 4 if monthly else 3
    label_col = first_col - 1

    # Row 1 -- what this sheet is and where it came from.
    origin_text = summod.ORIGIN_NOTE[sheet.origin]
    _put(ws, 1, 1, f"Updated for {sheet.updated_for}" if sheet.updated_for else "Updated", font=BOLD)
    _put(ws, 1, label_col + 1, origin_text, font=SMALL, wrap=True)

    r_file, r_unit = 2, 3
    r_group = 4 if sheet.group_row else None
    r_head = 5 if sheet.group_row else 4

    _put(ws, r_file, label_col, "File Name", font=BOLD)
    _put(ws, r_unit, label_col, "Unit", font=BOLD)
    if r_group:
        _put(ws, r_group, label_col, "", font=BOLD)
    _put(ws, r_head, label_col, "Channel", font=BOLD)
    if monthly:
        _put(ws, r_head, 2, "Year", font=BOLD)
        _put(ws, r_head, 3, "Month", font=BOLD)
    else:
        _put(ws, r_head, 2, "Week Ending", font=BOLD)

    for j, col in enumerate(sheet.columns):
        c = first_col + j
        _put(ws, r_file, c, col.source_file or "-", font=SMALL, wrap=False)
        _put(ws, r_unit, c, col.unit, font=BOLD)
        if r_group:
            _put(ws, r_group, c, col.group or "")
        _put(ws, r_head, c, col.label, font=BOLD, fill=HEAD_FILL, wrap=True)

    # -- the grid ----------------------------------------------------------
    idx = sheet.index
    data_start = r_head + 1
    # New rows: everything inside the period being loaded gets their green.
    new_from = None
    if sheet.periods is not None and len(sheet.periods):
        order = sheet.period_order
        if order:
            last = order[-1]
            marks = [t for t, p in zip(idx, sheet.periods) if p == last]
            new_from = min(marks) if marks else None

    for i, ts in enumerate(idx):
        r = data_start + i
        fresh = NEW_FILL if (new_from is not None and ts >= new_from) else None
        if monthly:
            _put(ws, r, 1, f"{ts.year}{ts.strftime('%b')}", font=SMALL, fill=fresh)
            _put(ws, r, 2, ts.year, fill=fresh)
            _put(ws, r, 3, ts.strftime("%b"), fill=fresh)
        else:
            _put(ws, r, 1, i + 1, font=SMALL, fill=fresh)
            _put(ws, r, 2, ts.to_pydatetime(), fmt=DATE, fill=fresh)
        for j, col in enumerate(sheet.columns):
            v = col.values.iloc[i] if i < len(col.values) else np.nan
            fmt = MONEY if _is_money(col.unit) else NUM
            _put(
                ws,
                r,
                first_col + j,
                None if pd.isna(v) else float(v),
                fmt=fmt,
                fill=fresh,
            )
    data_end = data_start + len(idx) - 1

    # -- the footer: quarter totals, then the two change rows --------------
    if sheet.periods is None or not len(idx):
        return
    order = sheet.period_order
    spans: dict[str, tuple[int, int]] = {}
    for p in order:
        rows = [data_start + i for i, q in enumerate(sheet.periods) if q == p]
        if rows:
            spans[p] = (min(rows), max(rows))

    r = data_end + 2
    _put(ws, r, label_col, "Quarter totals", font=BOLD)
    total_rows: dict[str, int] = {}
    for p in order[-8:]:
        r += 1
        lo, hi = spans[p]
        _put(ws, r, label_col, p, font=BOLD)
        total_rows[p] = r
        for j, col in enumerate(sheet.columns):
            L = get_column_letter(first_col + j)
            fmt = MONEY if _is_money(col.unit) else NUM
            _put(ws, r, first_col + j, f"=SUM({L}{lo}:{L}{hi})", fmt=fmt, font=BOLD)

    # The comparison rows point at the last period that actually carries
    # activity, not simply the last on the grid. A channel whose reporting
    # stops in August has an empty final quarter, and comparing against it
    # reports every series as -100%: true, and useless.
    tot = sheet.period_totals()
    active = [p for p in order if p in tot.index and float(tot.loc[p].abs().sum()) > 0]
    if active:
        latest = active[-1]
        li = order.index(latest)
        prior = order[li - 1] if li >= 1 else None
        yr = order[li - 4] if li >= 4 else None
        r += 2
        if prior and prior in total_rows:
            _put(ws, r, label_col, f"QoQ Change ({latest} vs {prior})", font=BOLD)
            for j in range(len(sheet.columns)):
                L = get_column_letter(first_col + j)
                _put(
                    ws, r, first_col + j,
                    f"=IFERROR(({L}{total_rows[latest]}-{L}{total_rows[prior]})"
                    f"/ABS({L}{total_rows[prior]}),\"\")",
                    fmt=PCT, font=BOLD,
                )
            r += 1
        if yr and yr in total_rows:
            _put(ws, r, label_col, f"YoY Change ({latest} vs {yr})", font=BOLD)
            for j in range(len(sheet.columns)):
                L = get_column_letter(first_col + j)
                _put(
                    ws, r, first_col + j,
                    f"=IFERROR(({L}{total_rows[latest]}-{L}{total_rows[yr]})"
                    f"/ABS({L}{total_rows[yr]}),\"\")",
                    fmt=PCT, font=BOLD,
                )
            r += 1
        if latest != order[-1]:
            r += 1
            _put(
                ws, r, label_col,
                f"Compared against {latest}, the last quarter with activity -- "
                f"{', '.join(order[li+1:])} carries none.",
                font=SMALL, wrap=True,
            )
            r += 1

    # -- derived rates, computed from the total cells above ---------------
    if sheet.rates and total_rows:
        by_label: dict[str, dict[str, int]] = {}
        for j, col in enumerate(sheet.columns):
            by_label.setdefault(col.label, {})[col.unit] = first_col + j
        r += 2
        _put(ws, r, label_col, "Derived rates", font=BOLD)
        _put(
            ws, r, label_col + 1,
            "Computed from the quarter totals above. A rate that jumps usually means "
            "one of its two inputs changed unit, not that the activity got dearer.",
            font=SMALL, wrap=True,
        )
        shown = [p for p in order[-8:] if p in total_rows]
        r += 1
        _put(ws, r, label_col, "Rate", font=BOLD)
        for k, p in enumerate(shown):
            _put(ws, r, first_col + k, p, font=BOLD, fill=HEAD_FILL)
        for rate in sheet.rates:
            num = rate["numerator"]
            den = rate["denominator"]
            scale = float(rate.get("scale", 1))
            for label, units in by_label.items():
                if num not in units or den not in units:
                    continue
                r += 1
                _put(ws, r, label_col, f"{rate['name']} -- {label}", font=BOLD)
                for k, p in enumerate(shown):
                    tr = total_rows[p]
                    N = get_column_letter(units[num])
                    D = get_column_letter(units[den])
                    _put(
                        ws, r, first_col + k,
                        f"=IFERROR({N}{tr}/{D}{tr}*{scale:g},\"\")",
                        fmt=MONEY2,
                    )

    # -- the notes: generated observations, then anything carried ---------
    r += 2
    _put(ws, r, label_col, "Note:", font=BOLD)
    if sheet.analysis and sheet.analysis.observations:
        for o in sheet.analysis.observations:
            r += 1
            _put(ws, r, label_col, "Ask" if o.severity == "ASK" else o.group, font=SMALL)
            _put(
                ws, r, label_col + 1, o.note,
                wrap=True, fill=ASK_FILL if o.severity == "ASK" else None,
            )
    else:
        r += 1
        _put(ws, r, label_col + 1, "Nothing in this channel needed a question this quarter.")
    if sheet.carried_notes:
        r += 2
        _put(ws, r, label_col, "From the previous summary", font=BOLD)
        for n in sheet.carried_notes[:20]:
            r += 1
            _put(ws, r, label_col + 1, n, font=SMALL, wrap=True)

    widths = {"A": 12, "B": 14, "C": 16} if monthly else {"A": 6, "B": 14}
    widths[get_column_letter(label_col + 1)] = 60
    for j in range(len(sheet.columns)):
        widths.setdefault(get_column_letter(first_col + j), 17)
    _autosize(ws, widths)
    ws.freeze_panes = ws.cell(data_start, first_col)


# --------------------------------------------------------------------------
# the surrounding sheets
# --------------------------------------------------------------------------


def _table(ws, r0: int, frame: pd.DataFrame, *, formats: dict | None = None, width=18) -> int:
    """Write a dataframe as a bordered table starting at row ``r0``. Returns last row."""
    if frame is None or frame.empty:
        _put(ws, r0, 1, "Nothing to report here.", font=SMALL)
        return r0
    formats = formats or {}
    for j, name in enumerate(frame.columns):
        _put(ws, r0, j + 1, str(name), font=BOLD, fill=HEAD_FILL, wrap=True).border = BOX
    for i, (_, row) in enumerate(frame.iterrows()):
        for j, name in enumerate(frame.columns):
            v = row[name]
            if isinstance(v, (pd.Timestamp,)):
                v = v.to_pydatetime()
            elif isinstance(v, (np.integer,)):
                v = int(v)
            elif isinstance(v, (np.floating,)):
                v = None if not np.isfinite(v) else float(v)
            elif isinstance(v, (list, dict, tuple)):
                v = str(v)
            c = _put(ws, r0 + 1 + i, j + 1, v, fmt=formats.get(name), wrap=isinstance(v, str) and len(str(v)) > 60)
            c.border = BOX
    for j, name in enumerate(frame.columns):
        ws.column_dimensions[get_column_letter(j + 1)].width = (
            52 if str(name).lower() in {"observation", "question", "what it means", "note", "ask"} else width
        )
    return r0 + len(frame)


def write_overview(wb: Workbook, s: summod.InputSummary, gate: str) -> None:
    ws = wb.create_sheet("Overview", 0)
    _put(ws, 1, 1, f"{s.client_name} -- {s.load_label or 'input summary'}", font=TITLE)
    _put(ws, 2, 1, f"Generated {s.generated}", font=SMALL)
    _put(
        ws, 3, 1,
        "This workbook replaces the hand-built input summary. Every figure on a generated "
        "sheet traces to a cell in a file you sent us, and every note on it was produced by "
        "the checks listed on 'Data quality' -- none of it is typed by hand.",
        wrap=True,
    )
    ws.merge_cells(start_row=3, start_column=1, end_row=4, end_column=8)

    fill = {"CLEAR": OK_FILL, "PROCEED WITH WARNINGS": ASK_FILL}.get(gate, BAD_FILL)
    _put(ws, 6, 1, "Overall", font=BOLD)
    _put(ws, 6, 2, gate, font=BOLD, fill=fill)

    rows = []
    for sh in s.sheets:
        a = sh.analysis
        rows.append(
            {
                "Sheet": sh.name,
                "How it was built": sh.origin,
                "Grain": sh.grain,
                "Series": len(sh.columns),
                "Periods": len(sh.index),
                "From": sh.index.min() if len(sh.index) else None,
                "To": sh.index.max() if len(sh.index) else None,
                "Questions for you": len(a.asks) if a else 0,
            }
        )
    _put(ws, 8, 1, "Sheets in this workbook", font=BOLD)
    last = _table(ws, 9, pd.DataFrame(rows), formats={"From": DATE, "To": DATE})

    r = last + 2
    _put(ws, r, 1, "What needs your attention", font=BOLD)
    asks = s.asks()
    if asks:
        from .summary_html import _rank

        df = pd.DataFrame(
            [
                {"#": i + 1, "Sheet": sh.name, "What we saw": o.observation,
                 "What we need": o.question}
                for i, (sh, o) in enumerate(_rank(asks))
            ]
        )
        r = _table(ws, r + 1, df)
    else:
        _put(ws, r + 1, 1, "Nothing this quarter.", font=SMALL)
        r += 1

    r += 2
    _put(ws, r, 1, "Files this run read", font=BOLD)
    _table(ws, r + 1, pd.DataFrame({"File": s.source_files}))
    _autosize(ws, {"A": 30, "B": 20, "C": 52, "D": 52, "E": 12, "F": 12, "G": 14, "H": 18})


def write_model_hypothesis(wb: Workbook, s: summod.InputSummary, spec) -> None:
    ws = wb.create_sheet(spec.cover_sheet[:31], 1)
    _put(ws, 1, 1, "Channel", font=BOLD, fill=HEAD_FILL)
    n = max((len(v) for v in s.breakdowns.values()), default=0)
    for i in range(n):
        _put(ws, 1, 2 + i, f"Breakdown {i+1}", font=BOLD, fill=HEAD_FILL)
    r = 1
    for ch, bks in s.breakdowns.items():
        r += 1
        _put(ws, r, 1, ch)
        for i, b in enumerate(bks):
            _put(ws, r, 2 + i, b)
    r += 2
    _put(ws, r, 1, "Considerations", font=BOLD)
    for c in s.considerations:
        r += 1
        _put(ws, r, 1, c, wrap=True)
    ws.column_dimensions["A"].width = 46
    for i in range(n):
        ws.column_dimensions[get_column_letter(2 + i)].width = 22


def write_change_log(wb: Workbook, s: summod.InputSummary, spec) -> None:
    ws = wb.create_sheet(spec.change_log_sheet[:31], 2)
    _put(ws, 1, 1, "BPM", font=BOLD, fill=HEAD_FILL)
    _put(ws, 1, 2, "Change", font=BOLD, fill=HEAD_FILL)
    _put(ws, 1, 3, "Recorded", font=BOLD, fill=HEAD_FILL)
    r = 1
    for bpm, text in s.change_log:
        r += 1
        _put(ws, r, 1, bpm)
        _put(ws, r, 2, text, wrap=True)
        _put(ws, r, 3, "carried forward", font=SMALL)
    proposed = summod.proposed_change_log(s)
    if proposed:
        r += 2
        _put(ws, r, 1, "Proposed for this quarter", font=BOLD)
        _put(
            ws, r, 2,
            "Detected by this run. A change log entry is a claim about intent, so these "
            "are proposals for a person to accept, reword or drop -- not entries.",
            font=SMALL, wrap=True,
        )
        for bpm, text in proposed:
            r += 1
            _put(ws, r, 1, bpm)
            _put(ws, r, 2, text, wrap=True, fill=ASK_FILL)
            _put(ws, r, 3, "needs confirming", font=SMALL)
    _autosize(ws, {"A": 14, "B": 110, "C": 18})


def write_checks_sheet(wb: Workbook, s: summod.InputSummary) -> None:
    """The load rules: what each one checks, what it found, and what it needs.

    In the same workbook as the figures, not a separate file. The rule suite
    decides whether the load can go to Element X; keeping that verdict in a
    different document from the numbers it is a verdict about is how a file
    gets uploaded while its gate says BLOCKED.
    """
    rules = s.all_findings()
    if not rules:
        return
    ws = wb.create_sheet("Load checks")
    _put(ws, 1, 1, "Load checks", font=TITLE)
    _put(
        ws, 2, 1,
        "These decide whether the file is safe to upload. The 'Observations' sheet is the "
        "other half — what a person would notice reading the numbers. Different question, "
        "same data.",
        font=SMALL, wrap=True,
    )
    order = {"FAIL": 0, "WAIVED": 1, "SKIP": 2, "PASS": 3}
    rows = []
    for f in sorted(rules, key=lambda x: (order.get(x.status, 9), x.channel, x.rule_id)):
        rows.append(
            {
                "Status": f.status,
                "Check": f.title,
                "Channel": f.channel,
                "Group": (s.groups.get(f.group) or {}).get("title", f.group),
                "What we checked": f.looks_for,
                "Why it matters": f.why_it_matters,
                "What we found": f.headline or f.raw_message,
                "What we need": "" if not f.needs_attention else f.ask,
                "Rule": f.rule_id,
            }
        )
    last = _table(ws, 4, pd.DataFrame(rows), width=22)
    fills = {"FAIL": BAD_FILL, "WAIVED": ASK_FILL, "PASS": OK_FILL}
    for i, r in enumerate(rows):
        if r["Status"] in fills:
            ws.cell(5 + i, 1).fill = fills[r["Status"]]
    ws.column_dimensions["E"].width = 46
    ws.column_dimensions["F"].width = 46
    ws.column_dimensions["G"].width = 52
    ws.column_dimensions["H"].width = 46


def write_analysis_sheets(wb: Workbook, s: summod.InputSummary) -> None:
    """Everything beyond the reproduction, each on its own sheet."""
    # -- every series, profiled -------------------------------------------
    prof = pd.concat([sh.analysis.profile for sh in s.sheets if sh.analysis is not None],
                     ignore_index=True) if any(sh.analysis is not None for sh in s.sheets) else pd.DataFrame()
    ws = wb.create_sheet("Series profile")
    _put(ws, 1, 1, "Every series, profiled", font=TITLE)
    _put(
        ws, 2, 1,
        "One row per series per measure. 'Periods with no row' is not the same as 'periods "
        "at zero': the first means the file had nothing to say about that period, the second "
        "means it said zero. The model treats them differently and so should a review.",
        font=SMALL, wrap=True,
    )
    if not prof.empty:
        show = prof.rename(
            columns={
                "channel": "Sheet", "series": "Series", "measure": "Measure", "grain": "Grain",
                "periods": "Periods", "periods_with_activity": "With activity",
                "periods_at_zero": "At zero", "periods_with_no_row": "No row",
                "total": "Total", "first_activity": "First", "last_activity": "Last",
                "mean_when_active": "Mean when active", "median_when_active": "Median when active",
                "min_when_active": "Min", "max_when_active": "Max",
                "spread_ratio": "Max / median", "variability_pct": "Variability %",
                "share_integer": "Share whole numbers", "source_file": "Source file",
                "source_detail": "Source detail",
            }
        )
        keep = [c for c in [
            "Sheet", "Series", "Measure", "Grain", "Periods", "With activity", "At zero",
            "No row", "Total", "First", "Last", "Median when active", "Min", "Max",
            "Max / median", "Variability %", "Share whole numbers", "Source file", "Source detail",
        ] if c in show.columns]
        _table(ws, 4, show[keep], formats={"First": DATE, "Last": DATE, "Total": NUM})

    # -- observations ------------------------------------------------------
    ws = wb.create_sheet("Observations")
    _put(ws, 1, 1, "What the data showed, and what we are asking", font=TITLE)
    _put(
        ws, 2, 1,
        "Each row is one thing found in the data, stated with the numbers behind it, and the "
        "question that follows. The observation is derived; the explanation is not, and is "
        "never guessed -- that is what the question is for.",
        font=SMALL, wrap=True,
    )
    # The workbook carries every finding, including the ones the HTML ranked
    # below its per-group cap. The page is for reading and the workbook is the
    # record; a cap on the record would be hiding.
    rows = []
    for sh in s.sheets:
        if sh.analysis is None:
            continue
        shown = {id(o) for o in sh.analysis.observations}
        for o in sh.analysis.all_observations or sh.analysis.observations:
            rows.append(
                {
                    "Sheet": sh.name, "Group": o.group, "Series": o.series,
                    "Period": o.period, "Severity": o.severity,
                    "What we saw": o.observation, "What we need": o.question,
                    "On the report": "yes" if id(o) in shown else "no",
                }
            )
    if rows:
        df = pd.DataFrame(rows).sort_values(
            ["Severity", "Sheet", "Group"], key=lambda c: c.map({"ASK": 0, "WATCH": 1, "INFO": 2}).fillna(3)
            if c.name == "Severity" else c
        )
        last = _table(ws, 4, df)
        for i in range(len(df)):
            if df.iloc[i]["Severity"] == "ASK":
                ws.cell(5 + i, 5).fill = ASK_FILL
    else:
        _put(ws, 4, 1, "Nothing to report.", font=SMALL)

    # -- coverage ----------------------------------------------------------
    ws = wb.create_sheet("Coverage")
    _put(ws, 1, 1, "Coverage by series", font=TITLE)
    _put(
        ws, 2, 1,
        "Where each series starts, where it stops, and what is missing in between. A series "
        "that ends before the others is the single most common reason a model input is wrong "
        "without anything looking wrong.",
        font=SMALL, wrap=True,
    )
    cov = []
    for sh in s.sheets:
        if sh.analysis is None:
            continue
        for c in sh.columns:
            v = pd.to_numeric(c.values, errors="coerce")
            act = v.fillna(0) != 0
            cov.append(
                {
                    "Sheet": sh.name, "Series": c.label, "Measure": c.unit,
                    "First activity": v[act].index.min() if act.any() else None,
                    "Last activity": v[act].index.max() if act.any() else None,
                    "Periods with activity": int(act.sum()),
                    "Periods at zero": int(((v.fillna(0) == 0) & v.notna()).sum()),
                    "Periods with no row": int(v.isna().sum()),
                    "Complete?": "yes" if v.isna().sum() == 0 else "no",
                }
            )
    _table(ws, 4, pd.DataFrame(cov), formats={"First activity": DATE, "Last activity": DATE})

    # -- rates and correlations -------------------------------------------
    rate_frames = [
        sh.analysis.rates.assign(Sheet=sh.name)
        for sh in s.sheets
        if sh.analysis is not None and not sh.analysis.rates.empty
    ]
    if rate_frames:
        ws = wb.create_sheet("Derived rates")
        _put(ws, 1, 1, "Efficiency rates by period", font=TITLE)
        _put(
            ws, 2, 1,
            "Cost per thousand impressions, cost per click, and the like. These are the "
            "fastest way to catch a unit change that every other check survives: a CPM that "
            "moves from $3 to $3,000 says the impressions column changed meaning.",
            font=SMALL, wrap=True,
        )
        df = pd.concat(rate_frames, ignore_index=True)
        cols = ["Sheet"] + [c for c in df.columns if c != "Sheet"]
        _table(ws, 4, df[cols], formats={c: MONEY2 for c in df.columns if c not in {"Sheet", "Series", "Rate"}})

    corr_frames = [
        sh.analysis.correlations.assign(Sheet=sh.name)
        for sh in s.sheets
        if sh.analysis is not None and not sh.analysis.correlations.empty
    ]
    if corr_frames:
        ws = wb.create_sheet("Series that move together")
        _put(ws, 1, 1, "Series the model may not be able to separate", font=TITLE)
        _put(
            ws, 2, 1,
            "Two drivers that move together this closely cannot be told apart by the model: "
            "whatever it credits to one it could equally credit to the other, and the split "
            "it lands on is an artefact of the fit rather than a finding. Better known before "
            "the model runs than explained afterwards.",
            font=SMALL, wrap=True,
        )
        df = pd.concat(corr_frames, ignore_index=True)
        _table(ws, 4, df[["Sheet", "Series A", "Series B", "Correlation", "What it means"]],
               formats={"Correlation": "0.00"})

    # -- the asks, with a response column ---------------------------------
    ws = wb.create_sheet("What we need from you")
    _put(ws, 1, 1, "What we need from you", font=TITLE)
    _put(ws, 2, 1, "Please write in the last column. Nothing else here needs editing.",
         font=SMALL)
    from .summary_html import _rank

    rows = [
        {
            "#": i + 1, "From": "Load check", "Sheet": ", ".join(a["sheets"]),
            "Series": a["title"], "Period": "",
            "What we saw": a["title"], "What we need": a["ask"], "Your response": "",
        }
        for i, a in enumerate(s.rule_asks())
    ]
    n = len(rows)
    rows += [
        {
            "#": n + i + 1, "From": "Data review", "Sheet": sh.name, "Series": o.series,
            "Period": o.period, "What we saw": o.observation, "What we need": o.question,
            "Your response": "",
        }
        for i, (sh, o) in enumerate(_rank(s.asks()))
    ]
    asks = rows
    df = pd.DataFrame(rows)
    _table(ws, 4, df)
    if not df.empty:
        ws.column_dimensions[get_column_letter(len(df.columns))].width = 46
        for i in range(len(df)):
            ws.cell(5 + i, len(df.columns)).fill = ASK_FILL


def write_modelled_sheet(wb: Workbook, s: summod.InputSummary) -> None:
    """The weekly series that actually goes to Element X, kept well away from the inputs."""
    parts = [sh.modelled.assign(__sheet=sh.name) for sh in s.sheets if sh.modelled is not None]
    if not parts:
        return
    ws = wb.create_sheet("Modelled series")
    _put(ws, 1, 1, "The modelled series -- not an input", font=TITLE)
    _put(
        ws, 2, 1,
        "The channel sheets show what you sent us. This shows what the model consumes after "
        "processing: monthly figures spread across fiscal weeks, coupon drops convolved with "
        "a redemption profile, and so on. It is here so the two can be compared, and kept on "
        "its own sheet so neither is ever mistaken for the other.",
        font=SMALL, wrap=True,
    )
    df = pd.concat(parts, ignore_index=True)
    keep = [c for c in df.columns if not c.startswith("__")]
    df = df[["__sheet"] + keep].rename(columns={"__sheet": "Sheet"})
    if len(df) > 20000:
        _put(ws, 3, 1, f"{len(df):,} rows; the first 20,000 are shown. The full set is in the "
                       "load CSVs delivered alongside this workbook.", font=SMALL)
        df = df.head(20000)
    _table(ws, 5, df)


# --------------------------------------------------------------------------
# the whole workbook
# --------------------------------------------------------------------------


def write_workbook(
    summary: summod.InputSummary, spec, path: str | Path, *, gate: str = "CLEAR"
) -> Path:
    wb = Workbook()
    wb.remove(wb.active)
    for sheet in summary.sheets:
        write_channel_sheet(wb, sheet)
    write_overview(wb, summary, gate)
    write_model_hypothesis(wb, summary, spec)
    write_change_log(wb, summary, spec)
    write_checks_sheet(wb, summary)
    write_analysis_sheets(wb, summary)
    write_modelled_sheet(wb, summary)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    wb.save(p)
    return p
