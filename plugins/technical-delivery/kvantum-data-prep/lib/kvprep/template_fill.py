"""Populate an Element X upload template from a canonical frame.

Element X templates are fixed-schema: the header row must appear exactly as
the portal published it, in the same order, and columns the channel does not
use stay present but empty. So the emitted file is built *from the template
spec outward* -- start with the full column list, drop nothing, and fill only
what the mapping covers. Building it from the data inward is how a column
quietly goes missing and the upload is rejected.

A template spec is a small JSON document::

    {
      "template_id": "elementx.ola",
      "label": "OLA",
      "columns": ["Brand", "Market", ..., "Week"],
      "required": ["Brand", "Week Starting Date", "Week Ending Date"],
      "date_columns": {"Week Starting Date": "%m/%d/%Y"},
      "numeric_columns": ["Impressions", "Spend", "Clicks"],
      "grain": ["Week Starting Date", "Brand", "Publisher ", "Campaign Name"]
    }

Specs are captured from a blank template downloaded from the portal with
:func:`spec_from_blank_template`, so the column list is never retyped.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class TemplateSpec:
    template_id: str
    label: str
    columns: list[str]
    required: list[str] = field(default_factory=list)
    date_columns: dict[str, str] = field(default_factory=dict)
    numeric_columns: list[str] = field(default_factory=list)
    grain: list[str] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def load(cls, path: str | Path) -> "TemplateSpec":
        """Load a spec, keeping fields this class does not declare.

        ``significant_figures`` and ``block_columns`` are part of the
        maintained file's contract but were added after the first specs were
        written. Dropping them on load would silently reformat the output;
        raising on them would make an older spec unloadable. So they are kept
        as attributes and an unrecognised key is reported rather than lost.
        """
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        known = {f for f in cls.__dataclass_fields__}
        spec = cls(**{k: v for k, v in d.items() if k in known})
        for k, v in d.items():
            if k not in known:
                setattr(spec, k, v)
        return spec

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.__dict__, indent=2), encoding="utf-8")
        return p


def spec_from_blank_template(
    path: str | Path,
    template_id: str,
    label: str,
    *,
    required: list[str] | None = None,
    date_columns: dict[str, str] | None = None,
    numeric_columns: list[str] | None = None,
    grain: list[str] | None = None,
) -> TemplateSpec:
    """Derive a spec from a blank template exported from the portal.

    Column names are taken verbatim, including any trailing spaces the portal
    ships (``'Publisher '`` really does have one), because the upload matches
    on the exact string.
    """
    p = Path(path)
    if p.suffix.lower() == ".csv":
        cols = list(pd.read_csv(p, nrows=0).columns)
    else:
        cols = list(pd.read_excel(p, nrows=0, engine="openpyxl").columns)
    cols = [c for c in cols if not str(c).startswith("Unnamed:")]
    return TemplateSpec(
        template_id=template_id,
        label=label,
        columns=cols,
        required=required or [],
        date_columns=date_columns or {},
        numeric_columns=numeric_columns or [],
        grain=grain or [],
        notes=f"captured from {p.name}",
    )


@dataclass
class FillResult:
    frame: pd.DataFrame
    manifest: dict

    def to_csv(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self.frame.to_csv(p, index=False)
        return p

    def manifest_text(self) -> str:
        m = self.manifest
        lines = [
            f"Template : {m['template_id']} ({m['label']})",
            f"Rows     : {m['n_rows']}",
            f"Columns  : {m['n_columns']} ({len(m['columns_filled'])} filled, "
            f"{len(m['columns_blank'])} intentionally blank)",
            "",
            "Mapping applied:",
        ]
        for tgt, src in m["mapping"].items():
            lines.append(f"  {tgt:<28} <- {src}")
        if m["constants"]:
            lines.append("")
            lines.append("Constants applied:")
            for k, v in m["constants"].items():
                lines.append(f"  {k:<28} =  {v!r}")
        if m["unmapped_source_columns"]:
            lines.append("")
            lines.append(
                "Source columns not carried into the template "
                f"({len(m['unmapped_source_columns'])}): "
                + ", ".join(m["unmapped_source_columns"][:25])
            )
        return "\n".join(lines)


def fill_template(
    frame: pd.DataFrame,
    spec: TemplateSpec,
    mapping: dict[str, str],
    *,
    constants: dict[str, object] | None = None,
    derived: dict[str, callable] | None = None,
    keep_blank_columns: bool = True,
) -> FillResult:
    """Project ``frame`` onto ``spec``'s columns.

    Parameters
    ----------
    mapping:
        ``{template_column: source_column}``.
    constants:
        ``{template_column: literal}`` for values the template needs that the
        raw file does not carry (e.g. ``Market = 'US'``).
    derived:
        ``{template_column: fn(frame) -> Series}`` for computed columns.
    keep_blank_columns:
        Keep unmapped template columns as empty strings. Element X expects the
        full header, so the default is ``True``.
    """
    constants = constants or {}
    derived = derived or {}

    # A mapping entry that does not resolve is the single most dangerous thing
    # here: falling through to a blank column ships a fixed-schema upload with
    # $0 spend, and the failed mapping would not even appear in the manifest.
    # Both halves of every entry are checked up front.
    bad_targets = [k for k in mapping if k not in spec.columns]
    bad_sources = {k: v for k, v in mapping.items() if v not in frame.columns}
    bad_const = [k for k in constants if k not in spec.columns]
    bad_derived = [k for k in derived if k not in spec.columns]
    problems = []
    if bad_targets:
        near = {
            k: [c for c in spec.columns if c.strip().lower() == str(k).strip().lower()]
            for k in bad_targets
        }
        problems.append(
            f"mapping targets not in template {spec.template_id}: {bad_targets}"
            + (f" (did you mean {near}? note the portal ships trailing spaces)" if any(near.values()) else "")
        )
    if bad_sources:
        problems.append(f"mapping sources not in the frame: {bad_sources}")
    if bad_const:
        problems.append(f"constants targeting columns not in the template: {bad_const}")
    if bad_derived:
        problems.append(f"derived targeting columns not in the template: {bad_derived}")
    if problems:
        raise KeyError("; ".join(problems))

    out = pd.DataFrame(index=frame.index)
    filled, blank = [], []
    for col in spec.columns:
        if col in mapping:
            out[col] = frame[mapping[col]]
            filled.append(col)
        elif col in constants:
            out[col] = constants[col]
            filled.append(col)
        elif col in derived:
            out[col] = derived[col](frame)
            filled.append(col)
        elif keep_blank_columns:
            out[col] = ""
            blank.append(col)

    for col, fmt in spec.date_columns.items():
        if col in out.columns and col in filled:
            out[col] = pd.to_datetime(out[col], errors="coerce").dt.strftime(fmt)
    for col in spec.numeric_columns:
        if col in out.columns and col in filled:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    out = out[[c for c in spec.columns if c in out.columns]]

    # Only sources whose target actually landed in the output count as used;
    # otherwise a dropped source column never shows up as unmapped.
    used = {v for k, v in mapping.items() if k in filled}
    manifest = {
        "template_id": spec.template_id,
        "label": spec.label,
        "n_rows": int(len(out)),
        "n_columns": int(len(out.columns)),
        "columns_filled": filled,
        "columns_blank": blank,
        "mapping": dict(mapping),
        "constants": dict(constants),
        "derived": list(derived),
        "unmapped_source_columns": [c for c in frame.columns if c not in used],
        "missing_required": [c for c in spec.required if c not in filled],
    }
    return FillResult(frame=out, manifest=manifest)


def append_to_history(
    history_path: str | Path,
    new: pd.DataFrame,
    *,
    week_col: str = "Week Starting Date",
    out_path: str | Path | None = None,
    force: bool = False,
) -> tuple[pd.DataFrame, dict]:
    """Append a new load to a historical consolidated file, safely.

    The historical file is never modified in place. Schema disagreement is
    reported rather than papered over, and weeks already present in history
    are reported rather than silently duplicated.
    """
    hp = Path(history_path)
    hist = pd.read_csv(hp) if hp.suffix.lower() == ".csv" else pd.read_excel(hp, engine="openpyxl")
    report = {
        "history_file": str(hp),
        "history_rows": int(len(hist)),
        "new_rows": int(len(new)),
        "columns_only_in_history": [c for c in hist.columns if c not in new.columns],
        "columns_only_in_new": [c for c in new.columns if c not in hist.columns],
        "column_order_matches": list(hist.columns) == list(new.columns),
    }
    h_weeks = set(pd.to_datetime(hist[week_col], errors="coerce").dropna())
    n_weeks = set(pd.to_datetime(new[week_col], errors="coerce").dropna())
    report["overlapping_weeks"] = sorted(str(d.date()) for d in (h_weeks & n_weeks))

    unsafe = []
    if report["overlapping_weeks"]:
        unsafe.append(f"{len(report['overlapping_weeks'])} week(s) already in history")
    if report["columns_only_in_history"] or report["columns_only_in_new"]:
        unsafe.append("schema disagreement between history and the load")
    report["unsafe"] = unsafe
    if unsafe and not force:
        report["written"] = False
        raise ValueError(
            "refusing to append: " + "; ".join(unsafe) + ". Appending anyway would "
            "duplicate weeks or break the fixed schema for the next load. Resolve it, "
            "or pass force=True having decided to accept it."
        )

    # Align to history's column order. Skipping this when the orders disagree
    # would leave the one case that needed normalising un-normalised.
    combined = pd.concat([hist, new], ignore_index=True)
    combined = combined.reindex(columns=list(hist.columns))
    report["combined_rows"] = int(len(combined))
    if out_path:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(p, index=False)
        report["output_file"] = str(p)
        report["written"] = True
    return combined, report


def compare_to_reference(
    produced: pd.DataFrame,
    reference: pd.DataFrame,
    *,
    key_cols: list[str],
    value_cols: list[str],
    tolerance: float = 1e-6,
    rel_tolerance: float = 0.0,
) -> dict:
    """Diff a generated template against a hand-built reference file.

    This is the acceptance test for the automation: run the agent over a
    quarter that was done by hand, then prove the output matches. Reports
    schema differences, rows present in one side only, and per-value drift.

    A value matches when it is within ``tolerance`` absolute **or**
    ``rel_tolerance`` relative. The relative allowance exists because a
    hand-built reference is usually stored at the precision Excel displayed,
    not at full float precision, and a 4e-06 difference on a 49,571 figure is
    the reference's rounding rather than a defect in the pipeline. Set
    ``rel_tolerance`` to the reference's actual precision and say what you set
    it to -- do not widen it until the diff disappears.
    """
    rep = {
        "columns_only_in_produced": [c for c in produced.columns if c not in reference.columns],
        "columns_only_in_reference": [c for c in reference.columns if c not in produced.columns],
        "produced_rows": int(len(produced)),
        "reference_rows": int(len(reference)),
    }
    kp = [c for c in key_cols if c in produced.columns and c in reference.columns]
    if not kp:
        rep["error"] = "no shared key columns"
        rep["match"] = False
        return rep

    p = produced.copy()
    r = reference.copy()
    for k in kp:
        p[k] = p[k].astype(str).str.strip()
        r[k] = r[k].astype(str).str.strip()
    vc = [c for c in value_cols if c in p.columns and c in r.columns]
    if not vc:
        rep["error"] = (
            "no shared value columns between produced and reference; "
            f"asked for {value_cols}, produced has "
            f"{[c for c in value_cols if c in p.columns]}, reference has "
            f"{[c for c in value_cols if c in r.columns]}"
        )
        rep["match"] = False
        return rep
    for c in vc:
        p[c] = pd.to_numeric(p[c], errors="coerce")
        r[c] = pd.to_numeric(r[c], errors="coerce")

    pg = p.groupby(kp, dropna=False)[vc].sum()
    rg = r.groupby(kp, dropna=False)[vc].sum()
    j = pg.join(rg, how="outer", lsuffix="_produced", rsuffix="_reference")

    rep["rows_only_in_produced"] = int(
        j[[f"{c}_reference" for c in vc]].isna().all(axis=1).sum()
    )
    rep["rows_only_in_reference"] = int(
        j[[f"{c}_produced" for c in vc]].isna().all(axis=1).sum()
    )
    rep["matched_keys"] = int(len(j) - rep["rows_only_in_produced"] - rep["rows_only_in_reference"])

    # The comparison aggregates by key, so two half-value rows sum to the same
    # total as one full row. Without a grain check this function would sign off
    # an output at the wrong grain -- exactly what KV-C03 treats as a blocker.
    rep["produced_rows_per_key_max"] = int(p.groupby(kp, dropna=False).size().max())
    rep["reference_rows_per_key_max"] = int(r.groupby(kp, dropna=False).size().max())
    rep["row_counts_agree"] = bool(len(produced) == len(reference))
    rep["grain_agrees"] = bool(
        rep["produced_rows_per_key_max"] == 1 and rep["reference_rows_per_key_max"] == 1
    )

    def _within(a, b):
        d = (a - b).abs()
        allow = tolerance + rel_tolerance * b.abs()
        return d <= allow

    per_col = {}
    for c in vc:
        a, b = j[f"{c}_produced"], j[f"{c}_reference"]
        both = a.notna() & b.notna()
        diff = (a[both] - b[both]).abs()
        ok = _within(a[both], b[both])
        rel = (diff / b[both].abs().replace(0, pd.NA)).max()
        per_col[c] = {
            "compared": int(both.sum()),
            "matched": int(ok.sum()),
            "mismatched": int((~ok).sum()),
            "max_abs_diff": float(diff.max()) if len(diff) else 0.0,
            "max_rel_diff": float(rel) if pd.notna(rel) else 0.0,
            "produced_total": float(a[both].sum()),
            "reference_total": float(b[both].sum()),
            "total_rel_diff": (
                float(abs(a[both].sum() - b[both].sum()) / abs(b[both].sum()))
                if b[both].sum()
                else 0.0
            ),
        }
    rep["per_column"] = per_col
    rep["tolerance"] = {"absolute": tolerance, "relative": rel_tolerance}
    rep["match"] = bool(
        rep["rows_only_in_produced"] == 0
        and rep["rows_only_in_reference"] == 0
        and not rep["columns_only_in_produced"]
        and not rep["columns_only_in_reference"]
        and rep["row_counts_agree"]
        and rep["grain_agrees"]
        and all(v["mismatched"] == 0 for v in per_col.values())
    )
    if not rep["row_counts_agree"]:
        rep.setdefault("failures", []).append(
            f"row counts differ: produced {len(produced)}, reference {len(reference)}"
        )
    if not rep["grain_agrees"]:
        rep.setdefault("failures", []).append(
            "more than one row per key on at least one side -- the outputs are at "
            "different grains even where the totals agree"
        )
    if not rep["match"]:
        worst = []
        for c in vc:
            a, b = j[f"{c}_produced"], j[f"{c}_reference"]
            both = a.notna() & b.notna()
            bad = ~_within(a[both], b[both])
            d = (a[both][bad] - b[both][bad]).abs().sort_values(ascending=False).head(5)
            for k, v in d.items():
                worst.append({"key": str(k), "column": c, "abs_diff": float(v),
                              "produced": float(a.loc[k]), "reference": float(b.loc[k])})
        rep["worst_mismatches"] = sorted(worst, key=lambda x: -x["abs_diff"])[:15]
    return rep


# --------------------------------------------------------------------------
# Capturing a spec from the maintained load, and formatting the output
#
# The most expensive mistake in this project's history was building a load
# from the blank template exported by the portal. The blank export has every
# column the portal *accepts* -- 54 for OLA. The load the client's team
# actually maintains uses 22 of them, at a different grain, with six mappings
# that the blank export cannot tell you. The load reconciled to the cent on
# impressions, clicks and spend the whole time it was wrong.
#
# So: capture the spec from the maintained file. Use the blank export only to
# confirm that every column the maintained file uses still exists in the
# portal, which is what ``check_against_blank`` below is for.
# --------------------------------------------------------------------------


def spec_from_history(
    path: str | Path,
    template_id: str,
    label: str,
    *,
    sheet: str | int | None = None,
    required: list[str] | None = None,
    date_columns: dict[str, str] | None = None,
    numeric_columns: list[str] | None = None,
    grain: list[str] | None = None,
    significant_figures: int | None = None,
    block_columns: list[str] | None = None,
) -> TemplateSpec:
    """Capture a template spec from the file the client's team maintains.

    ``block_columns`` names the dimensions whose distinct combinations form
    the file's blocks; their order of first appearance becomes the emit order
    (see :func:`block_order_from`). ``significant_figures`` records how the
    maintained file stores its numbers. Both are part of the contract: a load
    that reproduces every value but writes them in a different order, or at a
    different precision, still produces a diff a person reads as a failure.
    """
    p = Path(path)
    if p.suffix.lower() in {".csv", ".txt"}:
        head = pd.read_csv(p, nrows=0)
    else:
        head = pd.read_excel(p, sheet_name=sheet if sheet is not None else 0,
                             nrows=0, engine="openpyxl")
    cols = [c for c in head.columns if not str(c).startswith("Unnamed:")]
    spec = TemplateSpec(
        template_id=template_id,
        label=label,
        columns=list(cols),
        required=required or [],
        date_columns=date_columns or {},
        numeric_columns=numeric_columns or [],
        grain=grain or [],
        notes=f"captured from the maintained load {p.name}"
        + (f" [{sheet}]" if sheet is not None else ""),
    )
    # Carried on the instance so ``fill_template`` callers can pass them on;
    # kept out of TemplateSpec's constructor so an older spec JSON still loads.
    spec.significant_figures = significant_figures  # type: ignore[attr-defined]
    spec.block_columns = list(block_columns or [])  # type: ignore[attr-defined]
    return spec


def check_against_blank(spec: TemplateSpec, blank_path: str | Path) -> dict:
    """Confirm every column the maintained load uses still exists in the portal.

    This is the blank export's only job. A column the maintained file writes
    that the portal no longer accepts fails the upload; a column the portal
    added that the maintained file ignores is simply unused, and is reported
    separately rather than treated as a problem.
    """
    p = Path(blank_path)
    if p.suffix.lower() in {".csv", ".txt"}:
        blank = list(pd.read_csv(p, nrows=0).columns)
    else:
        blank = list(pd.read_excel(p, nrows=0, engine="openpyxl").columns)
    blank = [c for c in blank if not str(c).startswith("Unnamed:")]
    missing = [c for c in spec.columns if c not in blank]
    return {
        "blank_columns": len(blank),
        "template_columns": len(spec.columns),
        "used_but_not_in_blank": missing,
        "in_blank_but_unused": [c for c in blank if c not in spec.columns],
        "ok": not missing,
    }


def format_significant(value, sig: int) -> str:
    """Render one number at ``sig`` significant figures, trailing zeros stripped.

    ``f"{v:.10g}"`` is exactly how the hand-built consolidated files store
    their numbers: ``49571.54734`` and ``652.886836`` are both this format,
    at 10 significant figures, and a plain ``round(v, 5)`` reproduces neither.
    """
    if value is None:
        return ""
    v = pd.to_numeric(value, errors="coerce")
    if pd.isna(v):
        return ""
    return f"{float(v):.{sig}g}"


def format_output(
    df: pd.DataFrame,
    *,
    date_columns: dict[str, str] | None = None,
    numeric_columns: list[str] | None = None,
    significant_figures: int | None = None,
) -> pd.DataFrame:
    """Apply the maintained file's date and number formatting to a copy of ``df``.

    Formatting is part of the contract, not presentation. Returns strings for
    every formatted column, because that is what gets written to the CSV and
    what a byte-level diff against the reference compares.
    """
    out = df.copy()
    for col, fmt in (date_columns or {}).items():
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce").dt.strftime(fmt)
    if significant_figures:
        for col in numeric_columns or []:
            if col in out.columns:
                out[col] = out[col].map(lambda v: format_significant(v, significant_figures))
    return out


def block_order_from(reference: pd.DataFrame, block_columns: list[str]) -> list[tuple]:
    """The distinct block keys of ``reference``, in order of first appearance.

    Direct Mail puts ``PAB All`` last and Calls orders outpatient
    Bar/IM/Onc/Other; neither is alphabetical, and neither is derivable from
    the raw extract. Reading the order off the maintained file is how a
    regenerated load stops producing a diff that is purely cosmetic.
    """
    missing = [c for c in block_columns if c not in reference.columns]
    if missing:
        raise KeyError(f"reference has no column(s) {missing}; has {list(reference.columns)}")
    seen, out = set(), []
    for key in reference[block_columns].itertuples(index=False, name=None):
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def order_blocks(
    df: pd.DataFrame,
    block_columns: list[str],
    order: list[tuple],
    *,
    within: str | list[str] | None = "Week Starting Date",
    on_unknown: str = "raise",
) -> pd.DataFrame:
    """Sort ``df`` into ``order`` by its block key, ascending ``within`` inside.

    ``on_unknown="raise"`` (the default) refuses when the frame holds a block
    the order does not name. Appending it silently at the end would put a real
    series in a place the reference never has one, and the diff would read as
    a formatting difference rather than the extra series it is.
    """
    if not block_columns or not order:
        return df
    rank = {k: i for i, k in enumerate(order)}
    keys = list(df[block_columns].itertuples(index=False, name=None))
    unknown = sorted({k for k in keys if k not in rank}, key=str)
    if unknown:
        if on_unknown == "raise":
            raise KeyError(
                f"block(s) {unknown} are in the load but not in the expected order "
                f"{order}. Add them to the registry's series list, in the position "
                "the maintained file puts them."
            )
        for k in unknown:
            rank[k] = len(rank)
    work = df.copy()
    work["__rank"] = [rank[k] for k in keys]
    sort_cols = ["__rank"] + (
        [within] if isinstance(within, str) else list(within or [])
    )
    sort_cols = [c for c in sort_cols if c == "__rank" or c in work.columns]
    work = work.sort_values(sort_cols, kind="stable").drop(columns="__rank")
    return work.reset_index(drop=True)


#: Strings that mean "no value". A column the load deliberately leaves empty
#: is ``""`` on the produced side and NA on the reference side, and under
#: pandas' string dtype ``astype(str)`` keeps NA as NA rather than turning it
#: into the text "nan" -- so a plain string replace misses it and every row of
#: a blank column reads as a difference.
EMPTY_TOKENS = ("", "nan", "NaN", "None", "NaT", "<NA>", "null", "NULL")


def as_text(series: pd.Series) -> pd.Series:
    """Render a column as comparable text, with every flavour of null as ``""``."""
    out = series.astype("object").where(series.notna(), "")
    out = out.map(lambda v: "" if v is None else str(v).strip())
    return out.replace(list(EMPTY_TOKENS), "")


def compare_rowwise(
    produced: pd.DataFrame,
    reference: pd.DataFrame,
    *,
    key_cols: list[str],
    value_cols: list[str],
    tolerance: float = 1e-6,
    rel_tolerance: float = 0.0,
    max_examples: int = 10,
) -> dict:
    """Diff two loads as multisets of rows, when the keys are not unique.

    :func:`compare_to_reference` joins on a key and is the right tool when one
    row means one key. Some maintained loads are not like that. The OLA
    template carries 22 columns while the raw extract distinguishes rows by
    ``Creative_Name`` and ``Ad_ID``, so 140 rows can share a key on *both*
    sides -- legitimately, and identically. A keyed join sees that and refuses,
    which is correct behaviour for a keyed join and useless as an answer.

    So this compares the two files as bags of rows: sort both by every column,
    then compare cell by cell. It is the strongest claim available -- "row for
    row identical" -- and it is the one that catches a wrong mapping, which
    agreeing totals never will.
    """
    cols = [c for c in key_cols + value_cols if c in produced.columns and c in reference.columns]
    missing = [c for c in key_cols + value_cols if c not in cols]
    rep = {
        "mode": "rowwise",
        "produced_rows": int(len(produced)),
        "reference_rows": int(len(reference)),
        "columns_compared": cols,
        "columns_missing_on_one_side": missing,
    }
    if len(produced) != len(reference):
        rep["match"] = False
        rep["failures"] = [
            f"row counts differ: {len(produced):,} produced vs {len(reference):,} reference"
        ]
        return rep

    def prep(df):
        w = pd.DataFrame(index=range(len(df)))
        for c in cols:
            s = df[c].reset_index(drop=True)
            if c in value_cols:
                w[c] = pd.to_numeric(s, errors="coerce")
            else:
                w[c] = as_text(s)
        return w

    p, r = prep(produced), prep(reference)
    # Sort on rounded metrics so a 1e-12 difference cannot reorder two rows
    # that are otherwise identical and turn a match into a false mismatch.
    sort_p = p.copy()
    sort_r = r.copy()
    for c in value_cols:
        if c in cols:
            sort_p[c] = sort_p[c].round(6)
            sort_r[c] = sort_r[c].round(6)
    order_p = sort_p.sort_values(cols, kind="stable").index
    order_r = sort_r.sort_values(cols, kind="stable").index
    p = p.loc[order_p].reset_index(drop=True)
    r = r.loc[order_r].reset_index(drop=True)

    per_column, examples, total_diff = {}, [], 0
    for c in cols:
        if c in value_cols:
            a = p[c].to_numpy(dtype="float64")
            b = r[c].to_numpy(dtype="float64")
            both_nan = np.isnan(a) & np.isnan(b)
            absd = np.abs(np.nan_to_num(a) - np.nan_to_num(b))
            with np.errstate(divide="ignore", invalid="ignore"):
                rel = np.where(b != 0, absd / np.abs(b), np.inf)
            bad = ~((absd <= tolerance) | (rel <= rel_tolerance)) & ~both_nan
            n_bad = int(bad.sum())
            per_column[c] = {
                "compared": int(len(a)),
                "mismatched": n_bad,
                "max_abs_diff": float(np.nanmax(absd)) if len(absd) else 0.0,
                "max_rel_diff": float(np.nanmax(rel[np.isfinite(rel)])) if np.isfinite(rel).any() else 0.0,
                "produced_total": float(np.nansum(a)),
                "reference_total": float(np.nansum(b)),
            }
        else:
            bad = (p[c] != r[c]).to_numpy()
            n_bad = int(bad.sum())
            per_column[c] = {"compared": int(len(p)), "mismatched": n_bad}
        total_diff += n_bad
        if n_bad:
            idx = list(pd.Series(range(len(p)))[bad][:max_examples])
            for i in idx:
                examples.append(
                    {"row": int(i), "column": c, "produced": p[c].iloc[i], "reference": r[c].iloc[i]}
                )
    rep["per_column"] = per_column
    rep["mismatched"] = int(total_diff)
    rep["cells_compared"] = int(len(p) * len(cols))
    rep["examples"] = examples[: max_examples * 2]
    rep["tolerance"] = {"absolute": tolerance, "relative": rel_tolerance}
    rep["match"] = total_diff == 0
    if total_diff:
        rep["failures"] = [
            f"{total_diff:,} of {len(p) * len(cols):,} cells differ across "
            f"{sum(1 for v in per_column.values() if v['mismatched'])} column(s)"
        ]
    return rep
