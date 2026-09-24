"""kvprep.generic -- reading a file nothing in the registry describes.

The registry is the right way to read a channel: every decision written down,
reviewable, and reproducible. It is also the reason a new channel takes a
configuration change before it can appear in a review at all, and a data review
that silently omits the three channels nobody has configured yet is worse than
one that includes them with a warning.

So this reads an arbitrary tabular file as well as it can, and is loud about
every guess it made. A sheet produced here is marked ``inferred`` everywhere it
appears, carries the list of what was guessed, and is never compared against a
reference or used to reproduce anything. It exists to get a channel onto the
page and into the conversation, at which point somebody writes twelve lines of
``channels.yaml`` and it becomes ``generated``.

What it works out:

* **the time axis** -- a column of dates, or a Year column beside a Month one;
* **the grain** -- from the spacing of the axis, not from the file name;
* **the shape** -- wide (one column per series) or long (a category column and
  one value column), decided by whether the axis repeats;
* **the measures** -- numeric columns, with a spend-like name treated as money.

What it refuses to do is guess a dimension hierarchy, a mapping to Element X
columns, or a unit. Those are decisions, and a decision made by inference and
presented as a fact is exactly what this whole pipeline exists to avoid.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from .summary import INFERRED, SheetColumn, SummarySheet

MONTHS = {
    m: i + 1
    for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    )
}

MAX_SERIES = 40


class InferenceError(RuntimeError):
    """The file could not be read well enough to be worth showing."""


def _read_frames(path: str | Path) -> list[tuple[str, pd.DataFrame]]:
    p = Path(path)
    if p.suffix.lower() in {".csv", ".txt", ".tsv"}:
        sep = "\t" if p.suffix.lower() == ".tsv" else None
        return [(p.stem, pd.read_csv(p, sep=sep, engine="python"))]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        book = pd.read_excel(p, sheet_name=None)
    return [(name, df) for name, df in book.items() if len(df) > 4]


def _date_column(df: pd.DataFrame) -> str | None:
    best, best_hits = None, 0
    for c in df.columns:
        s = df[c]
        if pd.api.types.is_datetime64_any_dtype(s):
            hits = int(s.notna().sum())
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    hits = int(pd.to_datetime(s, errors="coerce").notna().sum())
                except Exception:
                    hits = 0
        if hits > best_hits and hits >= max(5, 0.6 * len(df)):
            best, best_hits = c, hits
    return best


def _year_month_columns(df: pd.DataFrame) -> tuple[str, str] | None:
    ycol = mcol = None
    for c in df.columns:
        s = df[c]
        nums = pd.to_numeric(s, errors="coerce")
        if nums.between(1990, 2100).sum() >= max(5, 0.6 * len(df)):
            ycol = c
        text = s.astype(str).str.strip().str.lower().str[:3]
        if text.isin(MONTHS).sum() >= max(5, 0.6 * len(df)):
            mcol = c
    return (ycol, mcol) if ycol and mcol else None


def _axis(df: pd.DataFrame) -> tuple[pd.Series, list[str], str]:
    """The period for each row, the columns consumed by it, and how it was found."""
    dc = _date_column(df)
    if dc is not None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return pd.to_datetime(df[dc], errors="coerce"), [dc], f"dates in column {dc!r}"
    ym = _year_month_columns(df)
    if ym:
        y, m = ym
        years = pd.to_numeric(df[y], errors="coerce").ffill()
        months = df[m].astype(str).str.strip().str.lower().str[:3].map(MONTHS)
        per = [
            pd.Timestamp(int(yy), int(mm), 1) if pd.notna(yy) and pd.notna(mm) else pd.NaT
            for yy, mm in zip(years, months)
        ]
        return pd.Series(per, index=df.index), [y, m], f"columns {y!r} and {m!r}"
    raise InferenceError(
        "no time axis found -- no column of dates, and no Year column beside a Month one. "
        "A series without a period cannot go on a summary sheet."
    )


def read_any(path: str | Path, *, sheet: str | None = None) -> list[SummarySheet]:
    """Read every usable table in a file into inferred summary sheets."""
    out: list[SummarySheet] = []
    for name, df in _read_frames(path):
        if sheet and name != sheet:
            continue
        try:
            out.append(_one(Path(path), name, df))
        except InferenceError:
            continue
    if not out:
        raise InferenceError(
            f"{Path(path).name}: nothing in this file looks like a time series. Every sheet "
            "was missing either a time axis or a numeric column."
        )
    return out


def _one(path: Path, name: str, df: pd.DataFrame) -> SummarySheet:
    df = df.dropna(how="all").copy()
    df.columns = [str(c).strip() for c in df.columns]
    period, used, how = _axis(df)
    df = df[period.notna()].copy()
    period = period[period.notna()]
    if df.empty:
        raise InferenceError("no rows carry a readable period")

    idx = pd.DatetimeIndex(sorted(pd.unique(period)))
    deltas = pd.Series(idx).diff().dt.days.dropna()
    grain = "weekly" if len(deltas) and deltas.median() <= 10 else "monthly"

    numeric = [
        c
        for c in df.columns
        if c not in used and pd.to_numeric(df[c], errors="coerce").notna().sum() >= max(3, 0.3 * len(df))
    ]
    if not numeric:
        raise InferenceError("no numeric column to plot")

    text_cols = [
        c
        for c in df.columns
        if c not in used and c not in numeric and df[c].astype(str).nunique() <= 60
    ]
    guesses = [f"the time axis came from {how}", f"the grain was read as {grain} from the spacing"]

    columns: list[SheetColumn] = []
    long_shape = period.duplicated().any() and bool(text_cols)
    if long_shape:
        # One category column and one value column per row: pick the category
        # that best explains the repeats, which is the one whose distinct count
        # is closest to how many rows share a period.
        per_period = int(period.value_counts().median())
        key = min(text_cols, key=lambda c: abs(df[c].astype(str).nunique() - per_period))
        guesses.append(
            f"rows repeat within a period, so {key!r} was taken as the breakdown "
            f"({df[key].astype(str).nunique()} values)"
        )
        work = df.assign(__p=period.values)
        for metric in numeric[:6]:
            g = work.groupby(["__p", key], dropna=False)[metric].sum().reset_index()
            keys = g.groupby(key)[metric].sum().sort_values(ascending=False).index
            for k in list(keys)[:MAX_SERIES]:
                s = g[g[key].astype(str) == str(k)].set_index("__p")[metric].reindex(idx)
                columns.append(
                    SheetColumn(label=str(k), unit=metric, values=s, source_file=path.name,
                                source_detail=f"{name} · grouped by {key}")
                )
    else:
        guesses.append("each numeric column was taken as its own series")
        work = df.assign(__p=period.values)
        for metric in numeric[:MAX_SERIES]:
            s = work.groupby("__p")[metric].sum().reindex(idx)
            columns.append(
                SheetColumn(label=metric, unit=metric, values=s, source_file=path.name,
                            source_detail=name)
            )

    from . import eda
    from .review import fiscal_periods

    periods = fiscal_periods(idx, None)
    series = [
        eda.Series(channel=name, label=c.label, unit=c.unit, values=c.values, grain=grain,
                   source_file=c.source_file, source_detail=c.source_detail)
        for c in columns
    ]
    analysis = eda.run_channel(series, periods, channel=name, label=name)

    return SummarySheet(
        name=name[:31],
        grain=grain,
        origin=INFERRED,
        index=idx,
        columns=columns,
        channels=[],
        updated_for="",
        notes=[
            "This sheet was read without a registry configuration. What was guessed: "
            + "; ".join(guesses)
            + ". Quarters are calendar quarters here, not fiscal ones, because no fiscal "
            "calendar is configured for this file."
        ]
        + [o.note for o in analysis.observations if o.severity == "ASK"],
        analysis=analysis,
        periods=periods,
    )
