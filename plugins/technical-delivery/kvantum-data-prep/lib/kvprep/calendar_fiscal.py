"""Fiscal week calendar and monthly-to-weekly disaggregation.

Kvantum's client data arrives on two different clocks:

* Media data arrives weekly, already keyed to a Saturday week-ending date.
* HCP / BPM data arrives monthly, in a cross-tab whose row key is the first
  of the calendar month.

Element X consumes a single weekly grain, so the monthly series has to be
disaggregated. The convention actually in use at Kvantum (reverse-engineered
from, and verified against, Calls_Q424_Q325.csv / Cases_Q424_Q325.csv) is:

1.  The week grid is a 4-4-5 fiscal calendar of Saturday-ending weeks.
2.  A fiscal block is labelled with the calendar month holding the majority of
    its days -- the block 2024-09-29..2024-10-26 is labelled ``2024-10-01``,
    which is how Abbott's BPM extracts key it.
3.  Every week in the block carries ``monthly_value / WEEKS_PER_MONTH`` where
    ``WEEKS_PER_MONTH`` is the flat constant 4.33 -- not the 4 or 5 weeks
    actually in the block.

Point 3 is deliberate and worth understanding before anyone "fixes" it.
Dividing by the true block length would make a 5-week block 25% taller than
its 4-week neighbours purely as a calendar artefact, which an MMM would read
as real media pressure. Dividing by 4.33 instead trades per-month accuracy
for a flat weekly series, and still conserves the annual total, because a
4-4-5 year is 52 weeks and 52 / 4.33 = 12.009 months. The cost is that a
single month does not reconcile: a 5-week block overstates its month by
5/4.33 = 1.155x and a 4-week block understates it by 4/4.33 = 0.924x.

``disaggregate_monthly_to_weekly`` therefore reports the reconciliation error
it introduces, and ``rule_annual_conservation`` in ``validate.py`` asserts the
annual identity rather than the monthly one.

**Silent loss is the failure mode this module guards hardest against.** A
monthly row whose period the calendar does not cover would otherwise vanish
from the output *and* from the reconciliation, so the conservation rule would
certify a truncated total as balanced. Uncovered periods therefore raise by
default; a caller that means to drop them must say so, and the dropped periods
stay in the reconciliation frame marked ``covered=False`` so the rule can fail
on them.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

import pandas as pd

#: The flat divisor Kvantum applies when spreading a month across its weeks.
WEEKS_PER_MONTH = 4.33

#: Weeks per fiscal month in the standard 4-4-5 pattern, by month of quarter.
PATTERN_445 = (4, 4, 5)


class UncoveredPeriodError(ValueError):
    """Monthly data was supplied for periods the fiscal calendar does not cover."""


@dataclass(frozen=True)
class FiscalBlock:
    """One fiscal month: a run of consecutive weeks."""

    period: pd.Timestamp  # the raw monthly key this block receives
    start: pd.Timestamp  # week-starting date of the first week
    end: pd.Timestamp  # week-ending date of the last week
    n_weeks: int


def _dominant_month(start: pd.Timestamp, n_weeks: int) -> pd.Timestamp:
    """The calendar month holding the majority of a block's days.

    Deriving the label from the block's *start* month instead would break for
    any fiscal year anchored near the start of a month: two blocks would claim
    the same label and another month would never be emitted at all.
    """
    days = pd.date_range(start, periods=7 * n_weeks, freq="D")
    counts = pd.Series(days).dt.to_period("M").value_counts()
    top = counts.sort_values(ascending=False)
    # Ties resolve to the later month, which is the direction a 4-4-5 block drifts.
    best = max(counts.index[counts == top.iloc[0]])
    return pd.Timestamp(best.start_time)


def build_445_calendar(
    year_start: str | _dt.date | pd.Timestamp,
    n_years: int = 1,
    pattern: tuple[int, ...] = PATTERN_445,
    period_label_offset_months: int = 0,
) -> pd.DataFrame:
    """Build a 4-4-5 fiscal week grid.

    Parameters
    ----------
    year_start:
        Week-starting date (a Sunday, for Saturday-ending weeks) of fiscal
        week 1. For Abbott FY2025 this is 2024-09-29.
    n_years:
        Number of 52-week fiscal years to emit.
    pattern:
        Weeks per fiscal month within a quarter. Defaults to 4-4-5.
    period_label_offset_months:
        Shift every period label by this many months. The default 0 labels each
        block with its dominant calendar month, which matches Abbott's BPM
        keying. Only set this for a client whose extracts key differently.

    Returns
    -------
    DataFrame with one row per week and columns
    ``fiscal_year, fiscal_month, week_of_month, week_index,
    week_starting_date, week_ending_date, period, n_weeks_in_month``.

    Raises
    ------
    ValueError
        If the resulting labels are not one per block. That can only happen
        through a bad ``pattern`` or offset, and it would silently corrupt
        every disaggregation downstream, so it fails loudly here.
    """
    start = pd.Timestamp(year_start).normalize()
    rows: list[dict] = []
    cursor = start
    week_index = 1
    n_blocks = 0
    for fy in range(n_years):
        for month_of_year in range(12):
            n_weeks = pattern[month_of_year % len(pattern)]
            block_start = cursor
            block_end = cursor + pd.Timedelta(days=7 * n_weeks - 1)
            period = _dominant_month(block_start, n_weeks)
            if period_label_offset_months:
                period = period + pd.DateOffset(months=period_label_offset_months)
            n_blocks += 1
            for w in range(n_weeks):
                ws = cursor + pd.Timedelta(days=7 * w)
                rows.append(
                    {
                        "fiscal_year": fy + 1,
                        "fiscal_month": month_of_year + 1,
                        "week_of_month": w + 1,
                        "week_index": week_index,
                        "week_starting_date": ws,
                        "week_ending_date": ws + pd.Timedelta(days=6),
                        "period": pd.Timestamp(period),
                        "n_weeks_in_month": n_weeks,
                    }
                )
                week_index += 1
            cursor = block_end + pd.Timedelta(days=1)
    cal = pd.DataFrame(rows)
    n_labels = cal["period"].nunique()
    if n_labels != n_blocks:
        raise ValueError(
            f"4-4-5 calendar from {start.date()} produced {n_labels} distinct period "
            f"labels for {n_blocks} fiscal blocks -- labels collide, so monthly data "
            "would be mis-assigned. Check the pattern and period_label_offset_months."
        )
    return cal


def blocks_from_calendar(cal: pd.DataFrame) -> list[FiscalBlock]:
    """Collapse a week grid into its fiscal blocks."""
    out = []
    for period, g in cal.groupby("period", sort=True):
        out.append(
            FiscalBlock(
                period=pd.Timestamp(period),
                start=g["week_starting_date"].min(),
                end=g["week_ending_date"].max(),
                n_weeks=len(g),
            )
        )
    return out


def infer_calendar_from_reference(
    reference: pd.DataFrame,
    *,
    start_col: str = "Week Starting Date",
    end_col: str = "Week Ending Date",
    strict: bool = True,
) -> pd.DataFrame:
    """Recover the week grid from an existing consolidated template.

    Use this on a historical load (e.g. ``Calls_Q424_Q325.csv``) when the
    fiscal year start is not known a priori.

    The two date columns are paired **row-wise** and then validated, rather
    than sorted independently and zipped: a single mistyped week-ending date
    would otherwise shift every subsequent pairing and silently produce a
    calendar that drives the whole disaggregation wrong.
    """
    pairs = (
        reference[[start_col, end_col]]
        .apply(pd.to_datetime, errors="coerce")
        .drop_duplicates()
        .dropna()
        .sort_values(start_col)
        .reset_index(drop=True)
    )
    delta = (pairs[end_col] - pairs[start_col]).dt.days
    bad = pairs[delta != 6]
    if len(bad) and strict:
        raise ValueError(
            f"{len(bad)} week(s) in the reference are not 6 days long, e.g. "
            f"{bad.iloc[0][start_col].date()}..{bad.iloc[0][end_col].date()}. "
            "Fix the reference or pass strict=False to accept it."
        )
    gaps = pairs[start_col].diff().dt.days.dropna()
    irregular = sorted({int(g) for g in gaps if g != 7})
    cal = pd.DataFrame(
        {
            "week_index": range(1, len(pairs) + 1),
            "week_starting_date": pairs[start_col],
            "week_ending_date": pairs[end_col],
        }
    )
    cal.attrs["irregular_gaps_days"] = irregular
    cal.attrs["weeks_not_6_days"] = len(bad)
    return cal


def disaggregate_monthly_to_weekly(
    monthly: pd.DataFrame,
    calendar: pd.DataFrame,
    *,
    period_col: str = "period",
    value_cols: list[str],
    dim_cols: list[str] | None = None,
    divisor: float | None = WEEKS_PER_MONTH,
    on_uncovered: str = "raise",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Spread monthly values across the fiscal weeks of their block.

    Parameters
    ----------
    monthly:
        Long frame with one row per (period, dimensions) and one or more
        numeric value columns.
    calendar:
        Week grid from :func:`build_445_calendar`, keyed on ``period``.
    value_cols:
        The metric columns to disaggregate. **Required and explicit** -- an
        auto-detected list would sweep in numeric keys (a year, a territory
        code, a merged ``week_index``) and quietly divide them by 4.33 too.
    divisor:
        ``None`` divides each month by the true number of weeks in its block,
        which conserves the month exactly. The default 4.33 reproduces
        Kvantum's current output and conserves the year instead.
    on_uncovered:
        What to do about monthly periods the calendar does not cover.
        ``"raise"`` (the default) refuses, because dropping them silently
        removes real volume from the load. ``"drop"`` proceeds and marks them
        ``covered=False`` in the reconciliation frame, where
        ``rule_annual_conservation`` will fail on them.

    Returns
    -------
    ``(weekly, reconciliation)``. The reconciliation frame has one row per
    period -- covered and uncovered alike -- with the monthly input total, the
    weekly output total, the percentage difference, and a ``covered`` flag.
    """
    if not value_cols:
        raise ValueError("value_cols must be given explicitly and non-empty")
    if on_uncovered not in {"raise", "drop"}:
        raise ValueError(f"on_uncovered must be 'raise' or 'drop', got {on_uncovered!r}")

    dim_cols = dim_cols or [
        c for c in monthly.columns if c not in value_cols and c != period_col
    ]
    missing = [c for c in value_cols if c not in monthly.columns]
    if missing:
        raise KeyError(f"value_cols not present in monthly frame: {missing}")

    cal = calendar.copy()
    cal[period_col] = pd.to_datetime(cal[period_col])
    m = monthly.copy()
    m[period_col] = pd.to_datetime(m[period_col])
    if m[period_col].isna().any():
        raise ValueError(
            f"{int(m[period_col].isna().sum())} monthly row(s) have an unparseable "
            f"{period_col!r}; they carry volume that would be lost silently"
        )

    covered = set(cal[period_col].unique())
    uncovered = sorted(set(m[period_col].unique()) - covered)
    if uncovered and on_uncovered == "raise":
        raise UncoveredPeriodError(
            f"{len(uncovered)} monthly period(s) fall outside the calendar "
            f"({str(pd.Timestamp(uncovered[0]).date())} .. "
            f"{str(pd.Timestamp(uncovered[-1]).date())}). Filter the monthly frame to "
            "the load period first, or pass on_uncovered='drop' to proceed knowing "
            "their volume is excluded."
        )

    m_cov = m[m[period_col].isin(covered)].copy()
    merged = m_cov.merge(
        cal[[period_col, "week_starting_date", "week_ending_date", "n_weeks_in_month"]],
        on=period_col,
        how="inner",
    )
    div = merged["n_weeks_in_month"] if divisor is None else float(divisor)
    for c in value_cols:
        merged[c] = pd.to_numeric(merged[c], errors="coerce") / div

    weekly = merged[
        ["week_starting_date", "week_ending_date", period_col] + dim_cols + value_cols
    ].sort_values(["week_starting_date"] + dim_cols)

    # Reconciliation covers EVERY period supplied, so dropped volume is visible.
    recon = (
        m.groupby(period_col)[value_cols]
        .sum()
        .rename(columns={c: f"{c}__monthly_in" for c in value_cols})
        .join(
            weekly.groupby(period_col)[value_cols]
            .sum()
            .rename(columns={c: f"{c}__weekly_out" for c in value_cols})
        )
        .reset_index()
    )
    recon["covered"] = recon[period_col].isin(covered)
    for c in value_cols:
        recon[f"{c}__weekly_out"] = recon[f"{c}__weekly_out"].fillna(0.0)
        recon[f"{c}__pct_diff"] = (
            100.0
            * (recon[f"{c}__weekly_out"] - recon[f"{c}__monthly_in"])
            / recon[f"{c}__monthly_in"].replace(0, pd.NA)
        )
    recon.attrs["periods_dropped"] = [str(pd.Timestamp(p).date()) for p in uncovered]
    recon.attrs["periods_covered"] = int(recon["covered"].sum())
    return weekly.reset_index(drop=True), recon


def week_grid_gaps(dates: pd.Series) -> dict:
    """Report missing, duplicated, off-grid and unparseable weeks."""
    raw = pd.Series(dates)
    s = pd.to_datetime(raw, errors="coerce")
    n_null = int(s.isna().sum())
    s = s.dropna().sort_values()
    u = s.drop_duplicates()
    if u.empty:
        return {
            "n_weeks": 0,
            "n_unparseable": n_null,
            "missing": [],
            "duplicated_weeks": [],
            "irregular": [],
        }
    expected = pd.date_range(u.min(), u.max(), freq="7D")
    counts = s.value_counts()
    return {
        "n_weeks": int(len(u)),
        "n_unparseable": n_null,
        "first": str(u.min().date()),
        "last": str(u.max().date()),
        "expected_weeks": int(len(expected)),
        "missing": [str(d.date()) for d in expected if d not in set(u)],
        "duplicated_weeks": [
            str(pd.Timestamp(d).date()) for d in counts[counts > 1].index
        ],
        "irregular": [str(d.date()) for d in u if d not in set(expected)],
    }
