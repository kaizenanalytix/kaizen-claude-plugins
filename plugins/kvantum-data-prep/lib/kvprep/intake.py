"""Read a client's raw file into a canonical long frame.

Two raw layouts are supported, and the layout is detected rather than assumed.

**Flat long** (media / Spark extracts). One row per date x dimension, metrics
in columns. Read directly.

**BPM cross-tab** (HCP / Abbott BPM extracts). A stacked header block
describes each column, and the data rows are keyed by a monthly date in the
second column::

    A1  'AC CALLS'   B1 'Q3 2025'
    B2  'BPM PERIOD' C2..  "Q3'25" ...
    B3  'UNITS'      C3..  'Calls' ...
    B4  'FSF'        C4..  'AC' ...
    B5  'BRAND'      C5..  'ENS' | 'GLU' ...
    B6  'HCP'        C6..  'Hospital' | 'TOTAL' ...
    B7  'LABEL'      C7..  'ENS AC - Hospital (Calls)' ...
    B8  2022-11-01   C8..  1594 ...

The header block is read as metadata, so ``BRAND``, ``FSF`` (field sales
force: AC = acute care, OP = outpatient) and ``HCP`` become dimension columns
on the unpivoted frame and no information is lost to a hand-typed mapping.
"""

from __future__ import annotations

import datetime as _dt
import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

#: Row labels of the BPM cross-tab header block, in the order they appear.
#: A default, not a fact about the world -- a client whose extract carries a
#: different header block passes its own list through ``header_labels``. The
#: Abbott outpatient DM sheet already needs ``DM TYPE`` and ``HANDRAISER``.
BPM_HEADER_LABELS = ("BPM PERIOD", "UNITS", "FSF", "BRAND", "HCP", "LABEL")


@dataclass
class IntakeResult:
    """A canonical long frame plus everything learned while reading it."""

    frame: pd.DataFrame
    layout: str
    source: str
    sheet: str | None = None
    grain: str = "unknown"
    metadata: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def __repr__(self) -> str:  # pragma: no cover - convenience only
        return (
            f"IntakeResult(layout={self.layout!r}, grain={self.grain!r}, "
            f"rows={len(self.frame)}, cols={len(self.frame.columns)}, "
            f"sheet={self.sheet!r})"
        )


def detect_layout(
    path: str | Path,
    sheet: str | None = None,
    *,
    header_labels: tuple[str, ...] | list[str] | None = None,
) -> str:
    """Return ``'flat_long'`` or ``'bpm_crosstab'`` for a workbook sheet.

    ``header_labels`` overrides the Abbott-shaped default, so a client whose
    cross-tab uses a different header block is a configuration entry rather
    than a patch to this module.
    """
    labels = tuple(header_labels or BPM_HEADER_LABELS)
    path = Path(path)
    if path.suffix.lower() in {".csv", ".txt"}:
        return "flat_long"
    head = pd.read_excel(path, sheet_name=sheet or 0, header=None, nrows=14)
    col_b = [str(v).strip().upper() for v in head.iloc[:, 1].tolist()]
    hits = sum(1 for lab in labels if str(lab).strip().upper() in col_b)
    # Two thirds of the block, or four rows, whichever is smaller: a five-label
    # block should not need a fifth match to be recognised.
    need = min(4, max(2, (2 * len(labels)) // 3))
    return "bpm_crosstab" if hits >= need else "flat_long"


def read_flat(
    path: str | Path,
    sheet: str | None = None,
    *,
    date_col: str | None = None,
    week_ending_col: str | None = None,
) -> IntakeResult:
    """Read a flat long extract and normalise its date columns."""
    path = Path(path)
    if path.suffix.lower() in {".csv", ".txt"}:
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path, sheet_name=sheet or 0, engine="openpyxl")
    notes = []
    date_col = date_col or _first_present(df, ["Date", "date", "DATE"])
    week_ending_col = week_ending_col or _first_present(
        df,
        ["Sat_Week_End_Date", "Week Ending Date", "week_ending_date", "Week_End_Date"],
    )
    for c in (date_col, week_ending_col):
        if c:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    grain = "unknown"
    if week_ending_col:
        grain = "weekly"
    elif date_col:
        nunique_dom = df[date_col].dt.day.dropna().nunique()
        grain = "monthly" if nunique_dom == 1 else "daily"
        notes.append(f"grain inferred from day-of-month cardinality ({nunique_dom})")
    return IntakeResult(
        frame=df,
        layout="flat_long",
        source=str(path),
        sheet=sheet,
        grain=grain,
        metadata={"date_col": date_col, "week_ending_col": week_ending_col},
        notes=notes,
    )


def read_bpm_crosstab(
    path: str | Path,
    sheet: str,
    *,
    value_name: str | None = None,
    drop_total: bool = True,
) -> IntakeResult:
    """Unpivot a BPM cross-tab sheet into a long monthly frame.

    Returns a frame with columns ``period``, one column per header-block row
    (``bpm_period, units, fsf, brand, hcp, label``) and a single ``value``
    column named after ``UNITS`` unless ``value_name`` overrides it.
    """
    raw = pd.read_excel(path, sheet_name=sheet, header=None, engine="openpyxl")
    labels = [str(v).strip().upper() for v in raw.iloc[:, 1].tolist()]

    header_rows: dict[str, int] = {}
    for lab in BPM_HEADER_LABELS:
        if lab in labels:
            header_rows[lab] = labels.index(lab)
    if "LABEL" not in header_rows:
        raise ValueError(f"{path}:{sheet} has no LABEL row in column B")
    first_data_row = header_rows["LABEL"] + 1

    header = {
        lab.lower().replace(" ", "_"): raw.iloc[idx].tolist()
        for lab, idx in header_rows.items()
    }
    title = str(raw.iloc[0, 0]) if pd.notna(raw.iloc[0, 0]) else sheet

    data = raw.iloc[first_data_row:].copy()
    # Coerce rather than isinstance-filter: clients sometimes type the monthly
    # key as text ("Nov-22", "2022-11-01"), and an isinstance test would drop
    # every row and take the whole sheet out of the load.
    keys = pd.to_datetime(data.iloc[:, 1], errors="coerce")
    n_unparseable = int(keys.isna().sum() - data.iloc[:, 1].isna().sum())
    data = data[keys.notna()].copy()
    data["__period"] = keys[keys.notna()]
    if data.empty:
        raise ValueError(
            f"{path}:{sheet} has no parseable date in column B below the header block"
        )

    records = []
    dropped_total: list[str] = []
    synthesised: list[str] = []
    skipped_empty: list[int] = []
    for col in range(2, raw.shape[1]):
        label = header["label"][col] if col < len(header["label"]) else None
        hcp = _cell(header.get("hcp"), col)
        unit = _cell(header.get("units"), col)
        col_values = pd.to_numeric(data.iloc[:, col], errors="coerce") if col < raw.shape[1] else None
        has_values = col_values is not None and bool(col_values.notna().any())

        if label is None or str(label).strip() == "" or str(label) == "nan":
            # A blank LABEL is usually a broken concatenation formula. Dropping
            # a column that still holds values would silently remove a series
            # from the load and the manifest would agree with the loss.
            if not has_values:
                skipped_empty.append(col)
                continue
            label = " ".join(
                str(_cell(header.get(k), col))
                for k in ("brand", "fsf", "hcp", "units")
                if _cell(header.get(k), col) is not None
            ) or f"UNLABELLED_COL_{col}"
            synthesised.append(str(label))

        # Subtotals appear on more than one axis of a BPM cross-tab. Checking
        # only the HCP row lets a BRAND=TOTAL or FSF=TOTAL column through as an
        # ordinary series, which then double-counts in any groupby.
        if drop_total:
            axes = {k: _cell(header.get(k), col) for k in ("fsf", "brand", "hcp")}
            is_total = any(
                str(v).strip().upper() in {"TOTAL", "ALL", "GRAND TOTAL"}
                for v in axes.values()
                if v is not None
            ) or "- TOTAL" in str(label).upper()
            if is_total:
                dropped_total.append(str(label).strip())
                continue
        for _, r in data.iterrows():
            v = r.iloc[col]
            records.append(
                {
                    "period": pd.Timestamp(r["__period"]).normalize(),
                    "bpm_period": _cell(header.get("bpm_period"), col),
                    "units": unit,
                    "fsf": _cell(header.get("fsf"), col),
                    "brand": _cell(header.get("brand"), col),
                    "hcp": hcp,
                    "label": str(label).strip(),
                    "value": pd.to_numeric(v, errors="coerce"),
                }
            )
    out = pd.DataFrame.from_records(records)
    if out.empty:
        raise ValueError(f"{path}:{sheet} produced no labelled series")
    unit_names = [u for u in out["units"].dropna().unique() if str(u) != "nan"]
    vname = value_name or (str(unit_names[0]) if len(unit_names) == 1 else "value")
    out = out.rename(columns={"value": vname})
    return IntakeResult(
        frame=out,
        layout="bpm_crosstab",
        source=str(path),
        sheet=sheet,
        grain="monthly",
        metadata={
            "title": title,
            "value_col": vname,
            "header_rows": header_rows,
            "total_columns_dropped": dropped_total,
            "labels_synthesised": synthesised,
            "empty_columns_skipped": skipped_empty,
            "unparseable_date_rows": n_unparseable,
            "n_series": int(out["label"].nunique()),
        },
        notes=[
            f"unpivoted {out['label'].nunique()} labelled series from '{title}'",
            (f"dropped {len(dropped_total)} TOTAL/subtotal column(s): {dropped_total}"
             if dropped_total else "no TOTAL columns found to drop")
            if drop_total else "TOTAL columns retained",
        ]
        + ([f"synthesised {len(synthesised)} label(s) for columns with values but no "
            f"LABEL cell: {synthesised}"] if synthesised else [])
        + ([f"{n_unparseable} row(s) had an unparseable date in column B and were "
            "excluded"] if n_unparseable else []),
    )


def read_bpm_workbook(
    path: str | Path,
    sheets: list[str] | None = None,
    *,
    strict: bool = True,
    **kw,
) -> tuple[dict[str, IntakeResult], dict[str, str]]:
    """Unpivot every (or the named) cross-tab sheet in a BPM workbook.

    Returns ``(results, failures)``. Failures are **returned, not swallowed**:
    a sheet that silently vanished from the dict would take a whole quarter of
    calls or cases out of the load with nothing to notice it by. With
    ``strict=True`` (the default) an explicitly named sheet that fails raises.
    """
    xl = pd.ExcelFile(path, engine="openpyxl")
    targets = sheets or xl.sheet_names
    out: dict[str, IntakeResult] = {}
    failures: dict[str, str] = {}
    for s in targets:
        try:
            out[s] = read_bpm_crosstab(path, s, **kw)
        except (ValueError, KeyError) as exc:
            failures[s] = str(exc)
            if sheets and strict:
                raise
    return out, failures


def read(path: str | Path, sheet: str | None = None, **kw) -> IntakeResult:
    """Read any supported raw file, detecting the layout."""
    layout = detect_layout(path, sheet)
    if layout == "bpm_crosstab":
        if sheet is None:
            raise ValueError("bpm_crosstab layout requires an explicit sheet name")
        return read_bpm_crosstab(path, sheet, **kw)
    return read_flat(path, sheet, **kw)


def parse_bpm_filename(path: str | Path) -> dict:
    """Pull channel context out of a BPM filename.

    Kvantum's step 1 for HCP data reads the channel (acute care vs outpatient)
    and the quarter off the filename, so that is encoded here rather than left
    to eyeballing:

    >>> parse_bpm_filename("Q3 25 AC ENS GLU BPM Inputs (Liz Ropelewski 110525).xlsx")
    {'fsf': 'AC', 'quarter': 'Q3', 'year': '25', 'brands': ['ENS', 'GLU'], ...}
    """
    name = Path(path).stem
    upper = name.upper()
    fsf = None
    if re.search(r"\bOUTPATIENT\b|\bOP\b", upper):
        fsf = "OP"
    elif re.search(r"\bACUTE CARE\b|\bAC\b", upper):
        fsf = "AC"
    qm = re.search(r"\bQ([1-4])\s*'?\s*(\d{2,4})\b", upper) or re.search(
        r"\b(\d{4})\s*Q([1-4])\b", upper
    )
    quarter = year = None
    if qm:
        g = qm.groups()
        if len(g[0]) == 4:
            year, quarter = g[0][-2:], f"Q{g[1]}"
        else:
            quarter, year = f"Q{g[0]}", g[1][-2:]
    brands = [b for b in ("ENS", "GLU", "PED", "SIM") if re.search(rf"\b{b}\b", upper)]
    sender = None
    sm = re.search(r"\(([^)0-9]+?)\s*\d*\)", name)
    if sm:
        sender = sm.group(1).strip()
    return {
        "filename": Path(path).name,
        "fsf": fsf,
        "quarter": quarter,
        "year": year,
        "brands": brands,
        "sender": sender,
    }


def _cell(row: list | None, idx: int):
    if row is None or idx >= len(row):
        return None
    v = row[idx]
    return None if (v is None or str(v) == "nan") else v


def _first_present(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


# --------------------------------------------------------------------------
# Column-addressable cross-tab reading
#
# ``read_bpm_crosstab`` above unpivots a sheet into one long frame, which is
# the right shape for profiling and for the parts-vs-total rule. It is the
# wrong shape for building a load, for two reasons found the hard way:
#
# * **Labels collide.** The outpatient workbook restates prior quarters side
#   by side -- 428 data columns on the DM sheet -- and several labels repeat
#   across blocks. Selecting a series by label alone can pick a restated
#   quarter and double-count with nothing to notice it by.
# * **Subtotals are sometimes the series you want.** Acute-care Calls is
#   loaded at ``HCP = TOTAL``; ``drop_total`` throws exactly that column away.
#
# So the reader below keeps every column addressable by its full set of
# header axes plus its column index, and selection is an explicit match that
# fails loudly when it is not unique.
# --------------------------------------------------------------------------


def normalise_label(value) -> str | None:
    """Collapse internal whitespace so a wrapped header cell still matches.

    The DM sheet stores ``'ENS DMwS \\nHR - PCP (Shipments)'``; the same series
    is written ``'ENS DMwS HR - PCP (Shipments)'`` everywhere a person refers
    to it. Comparing raw strings makes that a mismatch nobody can see.
    """
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    s = re.sub(r"\s+", " ", str(value)).strip()
    return s or None


class SheetResolutionError(ValueError):
    """A sheet pattern matched no sheets, or more than one."""


def resolve_sheet(
    path: str | Path,
    *,
    sheet: str | None = None,
    sheet_pattern: str | None = None,
) -> str:
    """Resolve a configured sheet name or glob against a workbook.

    Sheet names carry the quarter (``"Q3'25 DM"``), so pinning them exactly in
    the registry means editing the registry every quarter -- and an edit that
    has to happen every quarter is an edit that eventually does not. A pattern
    survives the rename; an ambiguous pattern raises rather than picking the
    first match, because the first match is usually a restated quarter.
    """
    names = pd.ExcelFile(path, engine="openpyxl").sheet_names
    if sheet:
        if sheet not in names:
            raise SheetResolutionError(
                f"{Path(path).name} has no sheet {sheet!r}. Sheets: {names}"
            )
        return sheet
    if not sheet_pattern:
        raise SheetResolutionError("give either sheet or sheet_pattern")
    hits = [n for n in names if fnmatch.fnmatch(n.strip().upper(), sheet_pattern.strip().upper())]
    if not hits:
        raise SheetResolutionError(
            f"{Path(path).name}: no sheet matches {sheet_pattern!r}. Sheets: {names}"
        )
    if len(hits) > 1:
        raise SheetResolutionError(
            f"{Path(path).name}: {sheet_pattern!r} matches {hits}. Narrow the pattern -- "
            "picking the first would silently choose one quarter's block over another."
        )
    return hits[0]


@dataclass
class CrosstabSheet:
    """One cross-tab sheet, addressable by header axes.

    ``axes`` has one row per data column: its ``col`` index and one column per
    header row (``BPM PERIOD``, ``UNITS``, ``BRAND``, ``HCP``, ``LABEL``, and
    whatever else the client's block carries). ``values`` is indexed by the
    monthly period with the same ``col`` indices as columns.
    """

    path: str
    sheet: str
    axes: pd.DataFrame
    values: pd.DataFrame
    header_rows: dict
    notes: list = field(default_factory=list)

    # -- inspection --------------------------------------------------------

    @property
    def axis_names(self) -> list[str]:
        return [c for c in self.axes.columns if c != "col"]

    def blocks(self, axis: str = "BPM PERIOD") -> list[str]:
        """Distinct values of the block axis, in sheet order (leftmost first)."""
        if axis not in self.axes.columns:
            return []
        seen, out = set(), []
        for v in self.axes[axis]:
            if v is not None and v not in seen:
                seen.add(v)
                out.append(v)
        return out

    def latest_block(self, axis: str = "BPM PERIOD") -> str | None:
        """The leftmost block on the sheet.

        The outpatient workbook writes the current quarter first and restates
        older quarters to its right, so leftmost is newest. This is a fact
        about the file's layout, not a date comparison -- ``Q3'25`` and
        ``Q3'24`` do not sort usefully as strings.
        """
        b = self.blocks(axis)
        return b[0] if b else None

    # -- selection ---------------------------------------------------------

    def match(self, select: dict, *, block: str | None = None,
              block_axis: str = "BPM PERIOD") -> pd.DataFrame:
        """Rows of ``axes`` matching every ``{axis: value}`` in ``select``."""
        m = self.axes
        crit = dict(select)
        if block and block_axis in m.columns:
            crit.setdefault(block_axis, block)
        for axis, want in crit.items():
            if axis not in m.columns:
                raise KeyError(
                    f"{self.sheet}: no header row {axis!r}. Available axes: "
                    f"{self.axis_names}"
                )
            want_s = normalise_label(want)
            m = m[m[axis].map(lambda v, w=want_s: _axis_eq(v, w))]
        return m

    def series(
        self,
        select: dict,
        *,
        block: str | None = None,
        block_axis: str = "BPM PERIOD",
        what: str = "series",
    ) -> pd.Series:
        """The single column matching ``select``, as ``period -> value``.

        Raises when the match is not exactly one column, and says which
        columns it did find. An ambiguous match resolved by taking the first
        is the double-count this whole module exists to prevent.
        """
        hits = self.match(select, block=block, block_axis=block_axis)
        if len(hits) == 0:
            raise LookupError(
                f"{Path(self.path).name}:{self.sheet}: no column matches {select}"
                + (f" in block {block!r}" if block else "")
                + f". Axes available: {self.axis_names}."
            )
        if len(hits) > 1:
            shown = hits.head(6).to_dict("records")
            raise LookupError(
                f"{Path(self.path).name}:{self.sheet}: {len(hits)} columns match "
                f"{select}" + (f" in block {block!r}" if block else "")
                + f" -- the match must be unique. Candidates: {shown}. "
                "Add another axis (UNITS, HANDRAISER, DM TYPE) to disambiguate."
            )
        col = int(hits.iloc[0]["col"])
        s = pd.to_numeric(self.values[col], errors="coerce")
        s.name = str(hits.iloc[0].get("LABEL") or f"col{col}")
        s.attrs["col"] = col
        s.attrs["axes"] = {k: hits.iloc[0][k] for k in self.axis_names}
        s.attrs["what"] = what
        return s


def _axis_eq(value, want) -> bool:
    if want is None:
        return value is None
    if value is None:
        return False
    return str(value).strip().upper() == str(want).strip().upper()


def read_crosstab(
    path: str | Path,
    sheet: str,
    *,
    header_labels: tuple[str, ...] | list[str] | None = None,
) -> CrosstabSheet:
    """Read a cross-tab sheet keeping every column addressable by its axes."""
    labels = [str(x).strip().upper() for x in (header_labels or BPM_HEADER_LABELS)]
    raw = pd.read_excel(path, sheet_name=sheet, header=None, engine="openpyxl")
    if raw.shape[1] < 3:
        raise ValueError(f"{path}:{sheet} has fewer than three columns")
    col_b = [str(v).strip().upper() for v in raw.iloc[:, 1].tolist()]

    header_rows: dict[str, int] = {}
    for lab in labels:
        if lab in col_b:
            header_rows[lab] = col_b.index(lab)
    if "LABEL" not in header_rows:
        raise ValueError(
            f"{path}:{sheet} has no LABEL row in column B. Found {sorted(header_rows)}; "
            f"looked for {labels}. Pass header_labels for a differently shaped extract."
        )
    first_data_row = max(header_rows.values()) + 1

    data = raw.iloc[first_data_row:].copy()
    keys = pd.to_datetime(data.iloc[:, 1], errors="coerce")
    n_bad = int(keys.isna().sum() - data.iloc[:, 1].isna().sum())
    data = data[keys.notna()]
    if data.empty:
        raise ValueError(f"{path}:{sheet} has no parseable monthly date in column B")
    periods = pd.DatetimeIndex(keys[keys.notna()]).normalize()

    records, values = [], {}
    for col in range(2, raw.shape[1]):
        rec = {"col": col}
        for lab, idx in header_rows.items():
            rec[lab] = normalise_label(raw.iat[idx, col]) if col < raw.shape[1] else None
        series = pd.to_numeric(data.iloc[:, col], errors="coerce")
        if all(rec[l] is None for l in header_rows) and not series.notna().any():
            continue  # a spacer column, present in every one of these sheets
        records.append(rec)
        values[col] = series.to_numpy()

    axes = pd.DataFrame.from_records(records)
    vals = pd.DataFrame(values, index=periods)
    vals.index.name = "period"
    notes = [
        f"{len(axes)} addressable columns, {len(vals)} monthly rows, "
        f"{periods.min().date()} .. {periods.max().date()}"
    ]
    if n_bad:
        notes.append(f"{n_bad} row(s) had an unparseable date in column B and were excluded")
    return CrosstabSheet(
        path=str(path),
        sheet=sheet,
        axes=axes,
        values=vals,
        header_rows=header_rows,
        notes=notes,
    )
