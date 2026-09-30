"""kvprep.eda -- the exploratory pass a person used to do by eye.

The validation suite answers "is this load safe to upload". This module
answers the other half of a data review: *what is actually going on in this
data, and what should we ask the client about it.*

That question was being answered by hand. Somebody opened the input summary
workbook, scrolled the quarter columns, noticed that Walmart was up while
Instacart and Kroger were down, and typed a sentence at the bottom of the
sheet::

    Walmart seems to have a rise in activities in this qtr compared to
    previous, also the spend has incresed for Walmart only

    Bing activities seem to fall compared to Google in paid search, any reason
    for decreased spend on Bing?

    It seems like we are not continuing with Pinterest anymore from May end,
    any reason?

Those three sentences are the output of three different pieces of analysis --
a within-channel divergence, a between-series comparison, and a stop
detection -- and every one of them is mechanical. This module runs them.

**What is generated and what is not.** Each detector produces an
:class:`Observation`: what was seen, stated as a fact with the numbers in it,
and the question that follows from it. The fact is derived; the *explanation*
is not, and is never invented. When the client's own file said "The activities
seem to increase specially during the month of May. It is for Memorial day",
the second sentence is knowledge from Abbott, not from the data, and this
module will produce the first sentence and ask for the second.

**Thresholds live in the registry**, in ``checks/catalogue.yaml`` under
``eda:``, so tuning what counts as "worth a sentence" is a text edit rather
than a code change. A detector with no configured threshold does not run and
says so, rather than falling back to a number nobody chose.

Everything here works on a :class:`Series` -- a named vector on a period
index, monthly or weekly -- so the same detectors run over the client's raw
monthly HCP figures and over weekly media, and over a channel this pipeline
has never seen whose sheet was read by the generic reader.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# Detectors that compare "this period" with history need a minimum amount of
# history to say anything. Below these they report SKIPPED rather than
# producing a confident sentence from three data points.
MIN_PERIODS_TREND = 6
MIN_PERIODS_SEASONAL = 24
MIN_YEARS_SEASONAL = 2


DEFAULT_THRESHOLDS = {
    "qoq_pct": 35.0,
    "yoy_pct": 50.0,
    "divergence_pct": 25.0,
    "robust_z": 3.5,
    # A z-score alone is not enough: a steady series has a tiny MAD and a 10%
    # wobble clears any threshold. A flagged period must also be this many
    # times its own median, or the client reads "0.9x its usual" as a defect.
    "outlier_min_ratio": 1.5,
    "flat_run": 6,
    "dormant_periods": 2,
    "new_series_periods": 6,
    "rate_shift_pct": 40.0,
    "magnitude_shift_ratio": 5.0,
    "correlation": 0.85,
    "restatement_pct": 0.5,
    "seasonal_index": 1.4,
}


# --------------------------------------------------------------------------
# the unit of analysis
# --------------------------------------------------------------------------


@dataclass
class Series:
    """One named vector on a period index, plus where it came from."""

    channel: str
    label: str
    unit: str
    values: pd.Series
    grain: str = "weekly"  # weekly | monthly
    source_file: str = ""
    source_detail: str = ""
    transformed: bool = False

    def __post_init__(self) -> None:
        v = pd.Series(self.values).copy()
        v.index = pd.to_datetime(v.index)
        self.values = pd.to_numeric(v, errors="coerce").sort_index()

    @property
    def name(self) -> str:
        return f"{self.label} ({self.unit})" if self.unit else self.label

    @property
    def filled(self) -> pd.Series:
        return self.values.fillna(0.0)

    # -- shape -------------------------------------------------------------

    @property
    def n(self) -> int:
        return int(len(self.values))

    @property
    def n_active(self) -> int:
        return int((self.filled != 0).sum())

    @property
    def n_zero(self) -> int:
        return int(((self.filled == 0) & self.values.notna()).sum())

    @property
    def n_missing(self) -> int:
        return int(self.values.isna().sum())

    @property
    def total(self) -> float:
        return float(self.filled.sum())

    @property
    def first_activity(self) -> pd.Timestamp | None:
        act = self.values[self.filled != 0]
        return act.index.min() if len(act) else None

    @property
    def last_activity(self) -> pd.Timestamp | None:
        act = self.values[self.filled != 0]
        return act.index.max() if len(act) else None

    def describe(self) -> dict:
        """The profile row. Every number here is stated, never inferred."""
        act = self.filled[self.filled != 0]
        d = {
            "channel": self.channel,
            "series": self.label,
            "measure": self.unit,
            "grain": self.grain,
            "periods": self.n,
            "periods_with_activity": self.n_active,
            "periods_at_zero": self.n_zero,
            "periods_with_no_row": self.n_missing,
            "total": self.total,
            "first_activity": self.first_activity,
            "last_activity": self.last_activity,
            "source_file": self.source_file,
            "source_detail": self.source_detail,
        }
        if len(act):
            q1, med, q3 = (float(x) for x in np.percentile(act, [25, 50, 75]))
            mean = float(act.mean())
            d.update(
                {
                    "mean_when_active": mean,
                    "median_when_active": med,
                    "p25": q1,
                    "p75": q3,
                    "min_when_active": float(act.min()),
                    "max_when_active": float(act.max()),
                    "spread_ratio": (float(act.max()) / med) if med else np.nan,
                    "variability_pct": (
                        float(act.std(ddof=0)) / mean * 100.0 if mean else np.nan
                    ),
                    "share_integer": float((act == act.round()).mean()),
                }
            )
        return d


def robust_z(values: pd.Series) -> pd.Series:
    """Median-absolute-deviation z-score, NaN where it cannot be computed.

    The mean and standard deviation are the wrong tools for finding an outlier
    in a series that contains one: a single spike drags both, and the spike
    ends up two standard deviations from a mean it created. MAD does not move.

    A series whose MAD is zero -- a flat line, or one where more than half the
    periods are identical -- has no scale to measure against, and this returns
    NaN rather than infinity. A flat line with one different value is a job
    for :func:`detect_flat_runs`, not for an outlier score.
    """
    v = pd.to_numeric(values, errors="coerce")
    med = v.median()
    mad = (v - med).abs().median()
    if not np.isfinite(mad) or mad == 0:
        return pd.Series(np.nan, index=v.index)
    return 0.6745 * (v - med) / mad


# --------------------------------------------------------------------------
# what a detector produces
# --------------------------------------------------------------------------


@dataclass
class Observation:
    """One thing worth saying, with the question that follows from it."""

    kind: str
    channel: str
    series: str
    observation: str
    question: str = ""
    severity: str = "INFO"  # INFO | WATCH | ASK
    period: str = ""
    evidence: dict = field(default_factory=dict)
    group: str = "Movement"
    #: The series without its measure, and the measure on its own. Kept apart
    #: so that the same event found in two measures of one series can be
    #: recognised as one event -- see :func:`merge_measures`.
    series_label: str = ""
    unit: str = ""

    @property
    def note(self) -> str:
        """The sentence as it would be typed at the bottom of a sheet."""
        return (self.observation + " " + self.question).strip()


def _pct(a: float, b: float) -> float:
    """Percent change from ``b`` to ``a``; NaN when the base is zero."""
    if b in (0, None) or not np.isfinite(b):
        return np.nan
    return (a - b) / abs(b) * 100.0


def _num(v: float) -> str:
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "n/a"
    a = abs(v)
    if a >= 1_000_000_000:
        return f"{v/1_000_000_000:,.1f}bn"
    if a >= 1_000_000:
        return f"{v/1_000_000:,.1f}m"
    if a >= 10_000:
        return f"{v/1_000:,.0f}k"
    if a == int(a):
        return f"{int(v):,}"
    return f"{v:,.1f}"


def _signed(v: float) -> str:
    if v is None or not np.isfinite(v):
        return "n/a"
    return f"{v:+,.0f}%" if abs(v) >= 10 else f"{v:+,.1f}%"


def _times(ratio: float) -> str:
    """"twice", "half", "about 7 times" -- rather than "about 0.5x".

    A multiplier below one reads as a decimal and the reader has to do the
    arithmetic to see it means "less". Client-ready means the sentence lands
    without a second pass.
    """
    if ratio is None or not np.isfinite(ratio) or ratio <= 0:
        return "far from"
    if ratio >= 1:
        if abs(ratio - 2) < 0.15:
            return "twice"
        if abs(ratio - 3) < 0.2:
            return "three times"
        return f"about {ratio:,.1f} times"
    inv = 1 / ratio
    if abs(inv - 2) < 0.15:
        return "half"
    if abs(inv - 3) < 0.2:
        return "a third of"
    if abs(inv - 4) < 0.3:
        return "a quarter of"
    # Anything else below one is said as a percentage. Ordinals invented from
    # a ratio produce "a 2th of", and a fraction the reader has to inverte
    # mentally is not client-ready either.
    return f"{ratio:.0%} of"


def _when(ts) -> str:
    try:
        return pd.Timestamp(ts).strftime("%b %Y")
    except Exception:
        return str(ts)


# --------------------------------------------------------------------------
# detectors
# --------------------------------------------------------------------------


def detect_stops(series: Series, periods: pd.Series, th: dict) -> list[Observation]:
    """A series that was running and has gone to nothing.

    This is the single most valuable thing the review can catch, because a
    channel that stops is indistinguishable from a channel whose file was not
    delivered, and the model treats the two completely differently. It is also
    the one the eye catches last, because zero looks like data.
    """
    out: list[Observation] = []
    need = int(th.get("dormant_periods", 2))
    tot = series.filled.groupby(periods.values).sum()
    order = list(dict.fromkeys(periods.tolist()))
    tot = tot.reindex([p for p in order if p in tot.index])
    if len(tot) < need + 2:
        return out
    tail = tot.iloc[-need:]
    before = tot.iloc[:-need]
    if float(tail.abs().sum()) == 0 and float(before.abs().sum()) > 0:
        last = series.last_activity
        ran_for = int((before != 0).sum())
        out.append(
            Observation(
                kind="stopped",
                channel=series.channel,
                series=series.name,
                series_label=series.label,
                unit=series.unit,
                severity="ASK",
                group="Coverage",
                period=str(tot.index[-1]),
                observation=(
                    f"{series.label} stops after {_when(last)}. It had reported in "
                    f"{ran_for} of the {len(before)} periods before that, and the last "
                    f"{need} carry nothing at all."
                ),
                question=(
                    "Has this activity ended, or is the file for these periods still "
                    "to come? A channel that stopped and a channel whose file is "
                    "missing look identical here and are modelled differently."
                ),
                evidence={
                    "last_activity": last,
                    "empty_periods": list(tail.index),
                    "periods_active_before": ran_for,
                },
            )
        )
    return out


def detect_starts(series: Series, periods: pd.Series, th: dict) -> list[Observation]:
    """A series appearing for the first time, or coming back after a long gap."""
    out: list[Observation] = []
    tot = series.filled.groupby(periods.values).sum()
    order = [p for p in dict.fromkeys(periods.tolist()) if p in tot.index]
    tot = tot.reindex(order)
    active = [i for i, v in enumerate(tot) if v != 0]
    if not active or len(tot) < 3:
        return out
    first = active[0]
    window = int(th.get("new_series_periods", 6))
    if first >= len(tot) - window and first > 0:
        out.append(
            Observation(
                kind="started",
                channel=series.channel,
                series=series.name,
                series_label=series.label,
                unit=series.unit,
                severity="ASK",
                group="Coverage",
                period=str(tot.index[first]),
                observation=(
                    f"{series.label} is new -- first activity in {tot.index[first]}, "
                    f"nothing in the {first} earlier periods on file."
                ),
                question=(
                    "Is this a genuinely new activity, or an existing one that has "
                    "been renamed or re-classified? If it is a rename, the model "
                    "needs to know what it used to be called so the history joins up."
                ),
                evidence={"first_period": tot.index[first], "total": float(tot.iloc[first])},
            )
        )
        return out
    # A gap in the middle, then a return.
    gaps = []
    run = 0
    for i, v in enumerate(tot):
        if i < first:
            continue
        if v == 0:
            run += 1
        else:
            if run >= 4:
                gaps.append((i - run, i, run))
            run = 0
    for start, end, length in gaps[-1:]:
        out.append(
            Observation(
                kind="resumed",
                channel=series.channel,
                series=series.name,
                series_label=series.label,
                unit=series.unit,
                severity="ASK",
                group="Coverage",
                period=str(tot.index[end]),
                observation=(
                    f"{series.label} restarts in {tot.index[end]} after {length} "
                    f"periods with no activity ({tot.index[start]} to {tot.index[end-1]})."
                ),
                question=(
                    "What changed? A restart after a break of this length usually "
                    "means either a new campaign or a reporting gap, and the model "
                    "reads those two very differently."
                ),
                evidence={"gap_periods": length, "resumed": tot.index[end]},
            )
        )
    return out


def detect_step_changes(series: Series, periods: pd.Series, th: dict) -> list[Observation]:
    """Quarter-on-quarter and year-on-year moves big enough to be worth a sentence."""
    out: list[Observation] = []
    tot = series.filled.groupby(periods.values).sum()
    order = [p for p in dict.fromkeys(periods.tolist()) if p in tot.index]
    tot = tot.reindex(order)
    active = [i for i, v in enumerate(tot) if v != 0]
    if not active:
        return out
    li = active[-1]
    latest = tot.index[li]
    cur = float(tot.iloc[li])

    if li >= 1:
        prev = float(tot.iloc[li - 1])
        q = _pct(cur, prev)
        if np.isfinite(q) and abs(q) >= float(th.get("qoq_pct", 35.0)):
            direction = "up" if q > 0 else "down"
            out.append(
                Observation(
                    kind="qoq_step",
                    channel=series.channel,
                    series=series.name,
                    series_label=series.label,
                    unit=series.unit,
                    severity="ASK",
                    group="Movement",
                    period=str(latest),
                    observation=(
                        f"{series.label} is {direction} {_signed(q)} in {latest} -- "
                        f"{_num(cur)} against {_num(prev)} in {tot.index[li-1]}."
                    ),
                    question=(
                        f"Is the {direction}ward move expected? A shift this size "
                        "changes the fitted response for this driver, so it is worth "
                        "knowing whether it is real activity or a reporting change."
                    ),
                    evidence={"latest": cur, "prior": prev, "qoq_pct": q},
                )
            )
    if li >= 4:
        yr = float(tot.iloc[li - 4])
        y = _pct(cur, yr)
        if np.isfinite(y) and abs(y) >= float(th.get("yoy_pct", 50.0)):
            out.append(
                Observation(
                    kind="yoy_step",
                    channel=series.channel,
                    series=series.name,
                    series_label=series.label,
                    unit=series.unit,
                    severity="WATCH",
                    group="Movement",
                    period=str(latest),
                    observation=(
                        f"{series.label} is {_signed(y)} against the same quarter last "
                        f"year ({_num(cur)} against {_num(yr)} in {tot.index[li-4]})."
                    ),
                    question=(
                        "Does this reflect a change in plan, or a change in how the "
                        "activity is reported?"
                    ),
                    evidence={"latest": cur, "year_ago": yr, "yoy_pct": y},
                )
            )
    return out


def detect_outliers(
    series: Series, periods: pd.Series, th: dict, score_on: Series | None = None
) -> list[Observation]:
    """Individual periods far outside the series' own normal range.

    ``score_on`` lets the *scoring* run on a deseasonalised copy while the
    *reporting* still quotes the real figures. Flagging a week and then
    printing a number the reader cannot find in the file is worse than not
    flagging it.
    """
    out: list[Observation] = []
    act = series.filled[series.filled != 0]
    if len(act) < MIN_PERIODS_TREND:
        return out
    basis = (score_on or series).filled.reindex(act.index)
    z = robust_z(basis)
    limit = float(th.get("robust_z", 3.5))
    hits = z[z.abs() >= limit]
    if hits.empty:
        return out
    med = float(act.median())
    min_ratio = float(th.get("outlier_min_ratio", 1.5))

    # A z-score says "unusual for this series". It does not say "worth a
    # sentence": a very steady series has a tiny MAD, and a value 10% off its
    # median clears any z threshold. Both tests have to pass, so that nothing
    # reaches the client reading "0.9x its usual".
    keep = [ts for ts in hits.index
            if not (med and (1 / min_ratio) < abs(float(act.loc[ts]) / med) < min_ratio)]
    if not keep:
        return out

    # Collapse *consecutive* flagged periods into one finding, whether or not
    # they carry the same value. Two different shapes both arrive as a run: a
    # monthly figure spread across the weeks of a fiscal block repeats the same
    # number four or five times, and a genuine change in level flags every
    # period until the median catches up. Reporting a six-month level shift as
    # six anomalies is the single fastest way to make a review unreadable --
    # and it also describes it wrongly, because a level shift and a spike are
    # different things with different causes.
    idx = list(act.index)
    pos = {ts: i for i, ts in enumerate(idx)}
    runs: list[list] = []
    for ts in keep:
        if runs and pos[ts] == pos[runs[-1][-1]] + 1:
            runs[-1].append(ts)
        else:
            runs.append([ts])

    for run in runs[:6]:
        vals = [float(act.loc[t]) for t in run]
        lo, hi = min(vals), max(vals)
        first = vals[0]
        ratio = first / med if med else np.nan
        way = "above" if first > med else "below"
        sustained = len(run) > 1 and (hi - lo) > 1e-6
        repeated = len(run) > 1 and not sustained

        if len(run) == 1:
            span = _when(run[0])
            what = (
                f"{series.label} in {span} is {_num(first)}, {_times(ratio)} its usual "
                f"{_num(med)} -- well {way} anything else in the series."
            )
            ask = (
                "Is this a real one-off, or a double-count, a restatement, or a "
                "catch-up posting landing in the wrong period?"
            )
            kind = "outlier"
        elif repeated:
            span = f"{_when(run[0])} to {_when(run[-1])} ({len(run)} periods)"
            what = (
                f"{series.label} holds {_num(first)} across {span}, {_times(ratio)} its "
                f"usual {_num(med)}."
            )
            ask = (
                "This is one unusual figure repeated across the periods it was spread "
                "over, rather than several separate ones. Is the underlying figure right?"
            )
            kind = "outlier"
        else:
            span = f"{_when(run[0])} to {_when(run[-1])}"
            what = (
                f"{series.label} runs {way} its usual level for {len(run)} periods in a row "
                f"({span}), between {_num(lo)} and {_num(hi)} against a usual {_num(med)}. "
                "That is a sustained change in level rather than a one-off."
            )
            ask = (
                "What changed over this period? A shift that lasts this long is usually a "
                "change in plan, in classification, or in what the file counts -- and each "
                "of those is handled differently in the model."
            )
            kind = "level_shift"

        out.append(
            Observation(
                kind=kind,
                channel=series.channel,
                series=series.name,
                series_label=series.label,
                unit=series.unit,
                severity="ASK",
                group="Outliers",
                period=span,
                observation=what,
                question=ask,
                evidence={
                    "value": first,
                    "range": [lo, hi],
                    "typical": med,
                    "ratio": ratio,
                    "periods": [str(x.date()) for x in run],
                },
            )
        )
    return out


def detect_flat_runs(series: Series, th: dict) -> list[Observation]:
    """The same number, repeated, for longer than a real driver usually is.

    A repeated value is normal for a monthly figure spread across a fiscal
    block. It is not normal across blocks, and when it happens it usually
    means a carried-forward cell rather than a measurement.
    """
    out: list[Observation] = []
    need = int(th.get("flat_run", 6))
    v = series.filled
    if len(v) < need + 2:
        return out
    run_val, run_len, run_start = None, 0, None
    best = (0, None, None, None)
    for ts, x in v.items():
        if run_val is not None and abs(x - run_val) < 1e-9 and x != 0:
            run_len += 1
            if run_len > best[0]:
                best = (run_len, run_start, ts, run_val)
        else:
            run_val, run_len, run_start = x, 1, ts
    if best[0] >= need:
        out.append(
            Observation(
                kind="flat_run",
                channel=series.channel,
                series=series.name,
                series_label=series.label,
                unit=series.unit,
                severity="ASK",
                group="Consistency",
                period=f"{_when(best[1])} to {_when(best[2])}",
                observation=(
                    f"{series.label} holds exactly {_num(best[3])} for {best[0]} "
                    f"consecutive periods ({_when(best[1])} to {_when(best[2])})."
                ),
                question=(
                    "Is this a genuinely constant activity, or a value that has been "
                    "carried forward because the actual figure was not available?"
                ),
                evidence={"value": best[3], "length": best[0]},
            )
        )
    return out


def detect_magnitude_shift(series: Series, periods: pd.Series, th: dict) -> list[Observation]:
    """A series whose scale changes by an order of magnitude.

    Almost always a unit change -- dollars becoming thousands of dollars,
    impressions becoming thousands of impressions -- and almost always silent,
    because every individual number still looks plausible.
    """
    out: list[Observation] = []
    tot = series.filled.groupby(periods.values).sum()
    order = [p for p in dict.fromkeys(periods.tolist()) if p in tot.index]
    tot = tot.reindex(order)
    nz = tot[tot != 0]
    if len(nz) < 4:
        return out
    ratio_limit = float(th.get("magnitude_shift_ratio", 5.0))
    half = len(nz) // 2
    early, late = float(nz.iloc[:half].median()), float(nz.iloc[half:].median())
    if early <= 0 or late <= 0:
        return out
    ratio = late / early
    if ratio >= ratio_limit or ratio <= 1 / ratio_limit:
        # Only worth raising when it looks like a unit change rather than
        # growth: a clean power of ten, or close to one.
        log = math.log10(ratio)
        if abs(log - round(log)) > 0.15:
            return out
        out.append(
            Observation(
                kind="magnitude_shift",
                channel=series.channel,
                series=series.name,
                series_label=series.label,
                unit=series.unit,
                severity="ASK",
                group="Consistency",
                period=str(nz.index[half]),
                observation=(
                    f"{series.label} changes scale around {nz.index[half]}: the typical "
                    f"period runs {_num(early)} before and {_num(late)} after -- "
                    + (
                        f"about {10**round(log):,.0f} times larger."
                        if log > 0
                        else f"about {10**round(-log):,.0f} times smaller."
                    )
                ),
                question=(
                    "Has the unit changed -- for example a figure now reported in "
                    "thousands that used to be reported in units? A factor of ten is "
                    "rarely a real change in activity."
                ),
                evidence={"before": early, "after": late, "ratio": ratio},
            )
        )
    return out


def detect_divergence(
    group: list[Series], periods: pd.Series, th: dict, group_name: str
) -> list[Observation]:
    """Series in the same family moving in opposite directions.

    This is the note the client's analyst writes most often, and the one that
    no single-series check can produce: "Walmart seems to have a rise in
    activities in this qtr compared to previous... While, Spend has decreased
    for Instacart and Kroger". It only exists in the comparison.
    """
    out: list[Observation] = []
    limit = float(th.get("divergence_pct", 25.0))
    moves: list[tuple[str, float, float]] = []
    latest = None
    for s in group:
        tot = s.filled.groupby(periods.values).sum()
        order = [p for p in dict.fromkeys(periods.tolist()) if p in tot.index]
        tot = tot.reindex(order)
        active = [i for i, v in enumerate(tot) if v != 0]
        if len(active) < 1 or active[-1] < 1:
            continue
        li = active[-1]
        latest = tot.index[li]
        cur, prev = float(tot.iloc[li]), float(tot.iloc[li - 1])
        q = _pct(cur, prev)
        if np.isfinite(q):
            moves.append((s.label, q, cur))
    if len(moves) < 3:
        return out
    up = [m for m in moves if m[1] >= limit]
    down = [m for m in moves if m[1] <= -limit]
    if not up or not down:
        return out
    up.sort(key=lambda m: -m[1])
    down.sort(key=lambda m: m[1])
    up_txt = ", ".join(f"{l} {_signed(q)}" for l, q, _ in up[:3])
    dn_txt = ", ".join(f"{l} {_signed(q)}" for l, q, _ in down[:3])
    out.append(
        Observation(
            kind="divergence",
            channel=group[0].channel,
            series=group_name,
            severity="ASK",
            group="Movement",
            period=str(latest),
            observation=(
                f"Within {group_name}, {latest} moves in both directions at once: "
                f"{up_txt} up, while {dn_txt} down."
            ),
            question=(
                "Was budget moved between these, or are they reported differently "
                "from each other? If spend shifted, the model should see that as a "
                "reallocation rather than as independent changes."
            ),
            evidence={"up": up[:5], "down": down[:5]},
        )
    )
    return out


def seasonal_index(series: Series) -> tuple[pd.Series, float, int, float] | None:
    """The month-of-year shape of a series, when it has a consistent one.

    Returns ``(index_by_month, peak_ratio, peak_month, consistency)`` or None.
    Used twice: once to report the pattern, and once to divide it out before
    looking for outliers, so that a reliable December does not get reported
    every year as an anomaly.
    """
    v = series.filled
    if len(v) < MIN_PERIODS_SEASONAL:
        return None
    df = pd.DataFrame({"v": v})
    df["month"] = df.index.month
    df["year"] = df.index.year
    yearly = df.groupby("year")["v"].sum()
    full_years = [y for y, t in yearly.items() if t > 0]
    if len(full_years) < MIN_YEARS_SEASONAL:
        return None
    monthly = df[df["year"].isin(full_years)].groupby(["year", "month"])["v"].sum()
    if monthly.empty or monthly.sum() == 0:
        return None
    # Median across years, not mean. With a mean, one spike in one July makes
    # July the "peak month" of the whole series, the real season stops being
    # detected, and every year's genuine peak is then reported as an anomaly.
    # That is the failure this function exists to prevent, so it must not be
    # vulnerable to it itself.
    idx = monthly.groupby("month").median()
    overall = idx.median()
    if overall <= 0:
        return None
    ratio = idx / overall
    peak_month = int(ratio.idxmax())
    leaders = monthly.groupby("year").idxmax().map(lambda t: t[1])
    consistency = float((leaders == peak_month).mean())
    return ratio, float(ratio.max()), peak_month, consistency


def deseasonalise(series: Series) -> Series:
    """The series with its own month-of-year shape divided out.

    An outlier test on a seasonal series finds the season, once per year, and
    calls it an anomaly. The client's file has exactly one sentence about the
    May peak in OLV; it does not have one per May.
    """
    got = seasonal_index(series)
    if got is None:
        return series
    ratio, peak, _, consistency = got
    if peak < 1.25 or consistency < 0.6:
        return series
    v = series.filled
    # Only correct the months that genuinely differ. A factor estimated from
    # two or three observations is noisy, and applying a noisy 1.03 to nine
    # quiet months shrinks the spread the outlier test measures against --
    # which manufactures outliers rather than removing them.
    def factor(month: int) -> float:
        f = float(ratio.get(month, 1.0) or 1.0)
        return f if abs(f - 1.0) >= 0.15 else 1.0

    factors = pd.Series([factor(t.month) for t in v.index], index=v.index)
    return Series(
        channel=series.channel,
        label=series.label,
        unit=series.unit,
        values=v / factors,
        grain=series.grain,
        source_file=series.source_file,
        source_detail=series.source_detail,
    )


def detect_renames(
    group: list[Series], periods: pd.Series, th: dict
) -> tuple[list[Observation], set[str]]:
    """One series stopping exactly as another starts, at a similar level.

    This is the most consequential thing that happens to a driver and the
    easiest to miss. When the OLA extract changed publisher naming, ``Amazon
    OLA`` ended and ``OLA AMAZON`` began in the same week at the same volume.
    Nothing is missing and every total still reconciles, so no completeness or
    conservation check fires -- but the model now sees two drivers with half
    the history each, and it will happily fit a different coefficient to each
    half of one channel.

    Reported as a pair with the evidence, and asked rather than asserted: two
    series can also start and stop together because budget genuinely moved.
    The paired stop and start findings are suppressed, because "X stopped" and
    "Y started" said separately is how this gets missed in the first place.

    Returns the observations and the set of series names whose own stop/start
    findings should be dropped.
    """
    out: list[Observation] = []
    consumed: set[str] = set()
    order = list(dict.fromkeys(periods.tolist()))
    if len(order) < 3:
        return out, consumed

    # One representative per series label -- its largest measure. A publisher
    # renamed in the extract is renamed in impressions, clicks and spend at
    # once; running this per measure finds the same rename three times and
    # then crosses the measures with each other.
    rep: dict[str, Series] = {}
    for s in group:
        key = s.label
        if key not in rep or s.total > rep[key].total:
            rep[key] = s

    profile: dict[str, tuple[int, int, float]] = {}
    for label, s in rep.items():
        tot = s.filled.groupby(periods.values).sum().reindex(order).fillna(0.0)
        active = [i for i, v in enumerate(tot) if v != 0]
        if not active:
            continue
        profile[label] = (active[0], active[-1], float(tot.iloc[active].median()))

    # Group by the boundary they share, rather than pairing every ending
    # series with every starting one. Four publishers ending and five starting
    # in the same week is one taxonomy change, not twenty renames -- and the
    # twenty would each be a plausible-sounding sentence that nobody could
    # act on.
    boundaries: dict[int, tuple[list, list]] = {}
    for label, (a0, a1, lev) in profile.items():
        if a1 < len(order) - 1 and lev > 0:
            boundaries.setdefault(a1 + 1, ([], []))[0].append((label, lev))
        if a0 > 0 and lev > 0:
            boundaries.setdefault(a0, ([], []))[1].append((label, lev))

    for at, (ended, began) in sorted(boundaries.items()):
        if not ended or not began:
            continue
        lev_out = sum(l for _, l in ended)
        lev_in = sum(l for _, l in began)
        if lev_out <= 0 or lev_in <= 0:
            continue
        ratio = lev_in / lev_out
        carried = 0.5 <= ratio <= 2.0
        names_out = sorted(l for l, _ in ended)
        names_in = sorted(l for l, _ in began)
        if not carried and not (len(ended) >= 2 and len(began) >= 3):
            # Volume did not carry across and it is not a crowd: a real stop
            # and a real start, already reported as such. But several series
            # ending and several starting at the same boundary is a structural
            # change whatever the volumes did -- the pieces may have been
            # re-cut as well as renamed, which is if anything a bigger problem
            # for the model, and saying nothing because the totals did not
            # match is the wrong way round.
            continue
        consumed.update(
            s.name for s in group if s.label in set(names_out) | set(names_in)
        )
        one_to_one = len(ended) == 1 and len(began) == 1 and carried
        if not carried:
            what = (
                f"At {order[at]} the set of series changes: {len(names_out)} stop "
                f"({', '.join(names_out[:5])}"
                + (f" and {len(names_out)-5} more" if len(names_out) > 5 else "")
                + f") and {len(names_in)} start ({', '.join(names_in[:5])}"
                + (f" and {len(names_in)-5} more" if len(names_in) > 5 else "")
                + f"). The volume does not carry across cleanly -- {_num(lev_out)} a period "
                f"before against {_num(lev_in)} after -- so this looks like the breakdown "
                "being re-cut rather than simply renamed."
            )
            ask = (
                "What changed at this point: the names, the way activity is grouped, or "
                "the activity itself? We need the mapping from the old breakdown to the "
                "new one. Without it each series carries only half the history, and the "
                "model fits the two halves separately."
            )
        elif one_to_one:
            what = (
                f"{names_out[0]} stops after {order[at-1]} and {names_in[0]} starts in "
                f"{order[at]}, the very next period, at a similar level "
                f"({_num(lev_out)} against {_num(lev_in)} a period). Nothing is missing "
                "overall, so every total still reconciles."
            )
            ask = (
                "Is this the same activity under a new name? If it is, we will join them "
                "into one driver. Left as two, the model sees two drivers with half the "
                "history each and can fit a different effect to each half of one channel."
            )
        else:
            what = (
                f"At {order[at]} the naming changes wholesale: {len(names_out)} "
                f"series stop ({', '.join(names_out[:5])}"
                + (f" and {len(names_out)-5} more" if len(names_out) > 5 else "")
                + f") and {len(names_in)} start ({', '.join(names_in[:5])}"
                + (f" and {len(names_in)-5} more" if len(names_in) > 5 else "")
                + f"), carrying almost the same volume across the boundary "
                f"({_num(lev_out)} a period before, {_num(lev_in)} after). Every total "
                "reconciles, which is why no other check sees this."
            )
            ask = (
                "Please confirm the mapping from the old names to the new ones. We can see "
                "that the volume carried across, but not which old name became which new "
                "one -- and guessing it wrong splits a driver's history in a way the model "
                "cannot recover from."
            )
        out.append(
            Observation(
                kind="rename",
                channel=group[0].channel,
                series=(
                    f"{names_out[0]} → {names_in[0]}" if one_to_one
                    else f"{len(names_out)} series replaced by {len(names_in)}"
                ),
                severity="ASK",
                group="Consistency",
                period=str(order[at]),
                observation=what,
                question=ask,
                evidence={
                    "ended": names_out, "began": names_in, "at": order[at],
                    "level_before": lev_out, "level_after": lev_in, "ratio": ratio,
                },
            )
        )
    return out, consumed


def detect_seasonality(series: Series, th: dict) -> list[Observation]:
    """A month that is reliably bigger every year.

    Reported as a pattern, never as a cause. The client's own file says "The
    activities seem to increase specially during the month of May. It is for
    Memorial day" -- the first sentence is in the data and the second is not,
    and this produces only the first.
    """
    out: list[Observation] = []
    got = seasonal_index(series)
    if got is None:
        return out
    ratio, peak, peak_month, consistency = got
    full_years = len(set(pd.to_datetime(series.filled.index).year))
    if peak >= float(th.get("seasonal_index", 1.4)) and consistency >= 0.6:
        name = pd.Timestamp(2000, peak_month, 1).strftime("%B")
        out.append(
            Observation(
                kind="seasonality",
                channel=series.channel,
                series=series.name,
                series_label=series.label,
                unit=series.unit,
                severity="INFO",
                group="Seasonality",
                period=name,
                observation=(
                    f"{series.label} peaks in {name} in {int(round(consistency*full_years))} "
                    f"of {full_years} years, running about {peak:,.1f}x its own "
                    "monthly average."
                ),
                question=(
                    f"Is there a recurring {name} driver behind this? Naming it lets "
                    "the model treat it as seasonality rather than as a response to "
                    "spend."
                ),
                evidence={"peak_month": name, "index": peak, "consistency": consistency},
            )
        )
    return out


def _as_monthly(series: Series) -> Series:
    """The same series summed into calendar months, for month-of-year tests."""
    v = series.filled
    if v.empty:
        return series
    m = v.groupby(pd.to_datetime(v.index).to_period("M").to_timestamp()).sum()
    return Series(
        channel=series.channel,
        label=series.label,
        unit=series.unit,
        values=m,
        grain="monthly",
        source_file=series.source_file,
        source_detail=series.source_detail,
    )


def derive_rates(
    group: list[Series], periods: pd.Series, rates: list[dict], th: dict
) -> tuple[pd.DataFrame, list[Observation]]:
    """Efficiency rates -- CPM, CPC, cost per point -- by period, with their moves.

    Their workbook computes these by hand under the quarter totals. They are
    the fastest way to catch a unit error that survives every other check: a
    CPM of $3.20 becoming $3,200 says the impressions column changed meaning,
    and no completeness or conservation rule will notice.
    """
    obs: list[Observation] = []
    by_label: dict[str, dict[str, pd.Series]] = {}
    for s in group:
        by_label.setdefault(s.label, {})[s.unit] = s.filled.groupby(periods.values).sum()
    order = list(dict.fromkeys(periods.tolist()))
    rows = []
    for label, units in by_label.items():
        for spec in rates:
            num, den = spec.get("numerator"), spec.get("denominator")
            if num not in units or den not in units:
                continue
            n = units[num].reindex(order).fillna(0.0)
            d = units[den].reindex(order).fillna(0.0)
            scale = float(spec.get("scale", 1))
            with np.errstate(divide="ignore", invalid="ignore"):
                r = np.where(d > 0, n / d * scale, np.nan)
            ser = pd.Series(r, index=order)
            if ser.notna().sum() < 2:
                continue
            row = {"Series": label, "Rate": spec["name"]}
            for p in order:
                row[p] = float(ser.get(p, np.nan))
            rows.append(row)
            valid = ser.dropna()
            if len(valid) >= 3:
                cur = float(valid.iloc[-1])
                base = float(valid.iloc[:-1].median())
                ch = _pct(cur, base)
                if np.isfinite(ch) and abs(ch) >= float(th.get("rate_shift_pct", 40.0)):
                    obs.append(
                        Observation(
                            kind="rate_shift",
                            channel=group[0].channel,
                            series=f"{label} {spec['name']}",
                            severity="ASK",
                            group="Consistency",
                            period=str(valid.index[-1]),
                            observation=(
                                f"{spec['name']} for {label} is {cur:,.2f} in "
                                f"{valid.index[-1]}, against a usual {base:,.2f} -- "
                                f"{_signed(ch)}."
                            ),
                            question=(
                                f"Did the cost of this activity really move that far, or "
                                f"has one of the two inputs to {spec['name']} changed "
                                "meaning or unit?"
                            ),
                            evidence={"rate": cur, "typical": base, "change_pct": ch},
                        )
                    )
    return pd.DataFrame(rows), obs


def detect_correlations(group: list[Series], periods: pd.Series, th: dict) -> pd.DataFrame:
    """Pairs of series that move together almost exactly.

    Two drivers with a correlation above about 0.9 cannot be separated by the
    model: whatever it attributes to one it could equally attribute to the
    other, and the split it lands on is an artefact of the fit. Better to know
    before the model runs than to explain an implausible coefficient after.
    """
    tots = {}
    for s in group:
        t = s.filled.groupby(periods.values).sum()
        order = [p for p in dict.fromkeys(periods.tolist()) if p in t.index]
        t = t.reindex(order)
        if (t != 0).sum() >= MIN_PERIODS_TREND:
            tots[s.name] = t
    if len(tots) < 2:
        return pd.DataFrame()
    df = pd.DataFrame(tots)
    c = df.corr(min_periods=MIN_PERIODS_TREND)
    limit = float(th.get("correlation", 0.85))
    rows = []
    names = list(c.columns)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            v = c.loc[a, b]
            if pd.notna(v) and abs(v) >= limit:
                rows.append(
                    {
                        "Series A": a,
                        "Series B": b,
                        "Correlation": float(v),
                        "What it means": (
                            "These two move together closely enough that the model "
                            "cannot tell their effects apart. Consider combining them, "
                            "or expect the split between them to be unstable."
                            if v > 0
                            else "These two move in opposite lockstep, which usually "
                            "means one is being substituted for the other."
                        ),
                    }
                )
    return pd.DataFrame(rows).sort_values("Correlation", key=abs, ascending=False) if rows else pd.DataFrame()


def compare_to_prior(
    series: Series, prior: pd.Series, periods: pd.Series, th: dict
) -> list[Observation]:
    """Periods whose value has changed since the last published summary.

    A restatement is legitimate and common -- their Change Log is largely a
    record of them. What is not acceptable is an unannounced one, and the only
    way to tell them apart is to compare.
    """
    out: list[Observation] = []
    if prior is None or prior.empty:
        return out
    p = pd.to_numeric(pd.Series(prior), errors="coerce")
    p.index = pd.to_datetime(p.index)
    cur = series.filled
    shared = cur.index.intersection(p.index)
    if len(shared) < 3:
        return out
    a, b = cur.reindex(shared), p.reindex(shared).fillna(0.0)
    limit = float(th.get("restatement_pct", 0.5))
    with np.errstate(divide="ignore", invalid="ignore"):
        diff = np.where(np.abs(b) > 0, (a - b) / np.abs(b) * 100.0, np.nan)
    d = pd.Series(diff, index=shared).dropna()
    changed = d[d.abs() >= limit]
    if changed.empty:
        return out
    tot_a, tot_b = float(a.sum()), float(b.sum())
    out.append(
        Observation(
            kind="restated",
            channel=series.channel,
            series=series.name,
            series_label=series.label,
            unit=series.unit,
            severity="ASK",
            group="Reconciliation",
            period=f"{_when(changed.index.min())} to {_when(changed.index.max())}",
            observation=(
                f"{series.label} differs from the last published summary in "
                f"{len(changed)} of {len(shared)} shared periods; over the overlap the "
                f"total moves from {_num(tot_b)} to {_num(tot_a)} ({_signed(_pct(tot_a, tot_b))})."
            ),
            question=(
                "Is this an intended restatement? If so it belongs in the change log, "
                "so that a future run can tell it apart from an error."
            ),
            evidence={
                "periods_changed": int(len(changed)),
                "periods_compared": int(len(shared)),
                "prior_total": tot_b,
                "current_total": tot_a,
                "largest": {
                    str(k.date()): float(v)
                    for k, v in changed.abs().sort_values(ascending=False).head(5).items()
                },
            },
        )
    )
    return out


# --------------------------------------------------------------------------
# the pass
# --------------------------------------------------------------------------


#: Detectors whose finding is usually about the *channel* rather than the
#: series, so N series firing it on the same period is one fact, not N.
_ROLLUP_KINDS = {
    "stopped": (
        "reporting stops",
        "Has reporting for this channel ended, or is the file for these periods still "
        "to come? A channel that stopped and a channel whose file is missing look "
        "identical here and are modelled differently.",
    ),
    "started": (
        "first appears",
        "Is this genuinely new activity, or an existing set of series that has been "
        "renamed or re-classified? If it is a rename, the model needs to know what "
        "these used to be called so the history joins up.",
    ),
}


def merge_measures(obs: list[Observation]) -> list[Observation]:
    """One event found in two measures of the same series is one event.

    Direct Mail reports Shipments and Bottles, and Bottles is Shipments times a
    bottles-per-shipment factor. So every movement in one is the same movement
    in the other, to the same percentage, and reporting both doubles the length
    of the review while adding nothing: the reader compares the two sentences,
    finds they say the same thing, and trusts the document a little less.

    Merged only when the *relative* size matches, because two measures that
    move by genuinely different amounts is a finding in itself -- shipments
    flat while bottles double means the pack changed.
    """
    out: list[Observation] = []
    buckets: dict[tuple, list[Observation]] = {}
    for o in obs:
        if not o.series_label or o.kind == "divergence":
            out.append(o)
            continue
        ratio = o.evidence.get("ratio") or o.evidence.get("qoq_pct") or o.evidence.get("yoy_pct")
        key = (
            o.kind,
            o.series_label,
            o.period,
            round(float(ratio), 2) if isinstance(ratio, (int, float)) and np.isfinite(ratio) else None,
        )
        buckets.setdefault(key, []).append(o)
    for group in buckets.values():
        first = group[0]
        if len(group) == 1:
            out.append(first)
            continue
        units = [g.unit for g in group if g.unit]
        if len(units) == 2:
            phrase = f"Both {units[0]} and {units[1]} move together here"
        else:
            phrase = (
                f"{', '.join(units[:-1])} and {units[-1]} all move together here"
            )
        first.observation = first.observation.rstrip(".") + (
            f". {phrase}, by the same proportion, so this is one event rather than "
            f"{'two' if len(units) == 2 else str(len(units))}."
        )
        first.evidence = {**first.evidence, "measures": units}
        out.append(first)
    return out


def roll_up(obs: list[Observation], label: str, n_series: int) -> list[Observation]:
    """Collapse one fact reported once per series into one finding.

    Direct Mail's reporting stops in June, so every one of its twenty-four
    series stops in June. Listing that twenty-four times is not thoroughness:
    it buries the three findings that are actually about individual series, and
    it tells the reader something they only needed told once.

    The rule is a majority: when more than half a channel's series report the
    same thing in the same period, it is a fact about the channel. Below that
    it stays per-series, because two series stopping out of twenty is the
    interesting case and must not be rolled into a sentence about the channel.
    """
    if n_series < 4:
        return obs
    out: list[Observation] = []
    buckets: dict[tuple[str, str], list[Observation]] = {}
    for o in obs:
        if o.kind in _ROLLUP_KINDS:
            buckets.setdefault((o.kind, o.period), []).append(o)
        else:
            out.append(o)
    for (kind, period), group in buckets.items():
        if len(group) <= max(3, n_series // 2):
            out += group
            continue
        verb, ask = _ROLLUP_KINDS[kind]
        # The bare series names, without their measure: these have already been
        # merged across measures, so printing "X (Shipments) (Redemptions)"
        # would name a column that does not exist.
        distinct = sorted({g.series_label or g.series for g in group})
        names = ", ".join(distinct[:4])
        more = len(distinct) - 4
        out.append(
            Observation(
                kind=kind,
                channel=group[0].channel,
                series=f"{label} -- {len(group)} series",
                severity="ASK",
                group="Coverage",
                period=period,
                observation=(
                    f"{verb.capitalize()} for {len(distinct)} of the {n_series} series on "
                    f"this channel at the same point ({period}), including {names}"
                    + (f" and {more} more" if more > 0 else "")
                    + ". Because they all move together, this is one fact about the "
                    "channel rather than a problem with individual series."
                ),
                question=ask,
                evidence={"series": distinct, "count": len(distinct), "of": n_series},
            )
        )
    return out


def rank_and_cap(obs: list[Observation], per_group: int) -> tuple[list[Observation], dict]:
    """Keep the largest few findings in each group, and count the rest.

    A channel with seventy publishers produces seventy true findings, and a
    document with seventy findings on one tab gets read as far as the fourth.
    Capping is not hiding as long as two things hold: the ones kept are the
    biggest rather than the first, and the number dropped is stated where the
    reader can see it. Both hold here, and the full set is always in the
    workbook.

    Ranked by the size of the effect, not by the score -- a 9x outlier on a
    series worth 400 impressions matters less than a 2x one on the channel's
    largest driver, and a z-score cannot tell the difference.
    """

    def weight(o: Observation) -> float:
        ev = o.evidence or {}
        for key in ("value", "latest", "level_before", "rate", "current_total", "total"):
            v = ev.get(key)
            if isinstance(v, (int, float)) and np.isfinite(v):
                return abs(float(v))
        return 0.0

    kept: list[Observation] = []
    dropped: dict[str, int] = {}
    buckets: dict[str, list[Observation]] = {}
    for o in obs:
        buckets.setdefault(o.group, []).append(o)
    for group, items in buckets.items():
        # A rollup or a rename speaks for many series at once, so it is never
        # the thing that gets cut.
        always = [o for o in items if o.kind in {"rename", "restated", "divergence"}]
        rest = sorted(
            [o for o in items if o not in always], key=weight, reverse=True
        )
        room = max(0, per_group - len(always))
        kept += always + rest[:room]
        if len(rest) > room:
            dropped[group] = len(rest) - room
    return kept, dropped


@dataclass
class ChannelEDA:
    channel: str
    label: str
    profile: pd.DataFrame
    observations: list[Observation]
    rates: pd.DataFrame
    correlations: pd.DataFrame
    period_totals: pd.DataFrame
    skipped: list[str] = field(default_factory=list)
    #: group -> how many further findings of that group are in the workbook
    #: but not on the page. Always rendered; a cap nobody is told about is
    #: indistinguishable from a check that did not run.
    not_shown: dict = field(default_factory=dict)
    all_observations: list = field(default_factory=list)

    @property
    def asks(self) -> list[Observation]:
        return [o for o in self.observations if o.severity == "ASK"]


def run_channel(
    series: list[Series],
    periods: pd.Series,
    *,
    channel: str,
    label: str,
    thresholds: dict | None = None,
    rates: list[dict] | None = None,
    prior: dict[str, pd.Series] | None = None,
    max_per_group: int = 8,
) -> ChannelEDA:
    """Run every detector over one channel's series."""
    th = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    obs: list[Observation] = []
    skipped: list[str] = []

    for s in series:
        if s.n_active == 0:
            skipped.append(f"{s.name}: no activity in any period, so nothing to test")
            continue
        obs += detect_stops(s, periods, th)
        obs += detect_starts(s, periods, th)
        obs += detect_step_changes(s, periods, th)
        # Seasonality is a month-of-year effect, so a weekly series is summed
        # into months for the test rather than skipped. Testing it week by week
        # would find the fiscal block pattern instead of the seasonal one.
        monthly_view = s if s.grain == "monthly" else _as_monthly(s)
        obs += detect_seasonality(monthly_view, th)
        # Outliers are looked for in what is left once the season is removed,
        # so a reliable peak is reported once as a pattern rather than every
        # year as an anomaly. This runs off the shape itself rather than off
        # whether the pattern cleared the reporting threshold: a series with a
        # strong season *and* a genuine spike may not report as seasonal at
        # all, and that is exactly the series where the correction matters.
        obs += detect_outliers(s, periods, th, score_on=deseasonalise(s))
        obs += detect_flat_runs(s, th)
        obs += detect_magnitude_shift(s, periods, th)
        if prior and s.name in prior:
            obs += compare_to_prior(s, prior[s.name], periods, th)

    # Group by measure, so impressions are compared with impressions.
    by_unit: dict[str, list[Series]] = {}
    for s in series:
        by_unit.setdefault(s.unit, []).append(s)
    for unit, grp in by_unit.items():
        if len(grp) >= 3:
            obs += detect_divergence(grp, periods, th, f"{label} {unit}".strip())
    # Renames are detected once across the whole channel, not per measure: a
    # publisher renamed in the extract is renamed in every measure at once.
    ren, renamed = detect_renames(series, periods, th)
    obs += ren

    # A series that stopped because it was renamed has been reported as a
    # rename. Reporting it again as a stop, and its replacement again as a
    # start, is how the rename gets lost among the stops.
    if renamed:
        obs = [
            o
            for o in obs
            if not (o.kind in {"stopped", "started"} and o.series in renamed)
        ]

    obs = merge_measures(obs)
    # Counted in distinct series, not in series-times-measures. Direct Mail has
    # sixteen columns but eight series, each reported in Shipments and Bottles;
    # measuring the majority against sixteen means a fact true of every series
    # never reaches the majority and never gets rolled up.
    obs = roll_up(obs, label, len({s.label for s in series}))

    rate_df, rate_obs = derive_rates(series, periods, rates or [], th)
    obs += rate_obs
    corr = detect_correlations(series, periods, th)

    everything = list(obs)
    obs, not_shown = rank_and_cap(obs, max_per_group)

    prof = pd.DataFrame([s.describe() for s in series])
    order = list(dict.fromkeys(periods.tolist()))
    tot = pd.DataFrame(
        {s.name: s.filled.groupby(periods.values).sum().reindex(order) for s in series}
    )
    return ChannelEDA(
        channel=channel,
        label=label,
        profile=prof,
        observations=obs,
        rates=rate_df,
        correlations=corr,
        period_totals=tot,
        skipped=skipped,
        not_shown=not_shown,
        all_observations=everything,
    )
