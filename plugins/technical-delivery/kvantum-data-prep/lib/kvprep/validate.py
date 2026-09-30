"""Rule-based validation gate for a load headed to Element X.

Every check is a named rule with a stable ID, a severity, and a machine-readable
result, so a load's outcome is auditable and comparable quarter to quarter. The
rule IDs are the vocabulary the team can use in email: "KV-C03 failed" is
precise in a way that "the data looks off" is not.

Severity semantics
------------------
``BLOCK``  The load must not go to Element X until resolved.
``WARN``   The load can proceed, but the finding belongs in the client's
           input review and usually needs a question back to the client.
``INFO``   Recorded for the audit trail; no action implied.

A rule that cannot be evaluated (its inputs are absent) returns ``SKIP`` and
says why. A skipped rule is never reported as a pass.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .calendar_fiscal import week_grid_gaps

BLOCK, WARN, INFO = "BLOCK", "WARN", "INFO"


@dataclass
class RuleResult:
    rule_id: str
    name: str
    severity: str
    status: str  # PASS | FAIL | SKIP
    message: str
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ValidationReport:
    dataset: str
    channel: str
    results: list[RuleResult] = field(default_factory=list)
    created_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    # -- summary -----------------------------------------------------------

    @property
    def failures(self) -> list[RuleResult]:
        return [r for r in self.results if r.status == "FAIL"]

    @property
    def blockers(self) -> list[RuleResult]:
        return [r for r in self.failures if r.severity == BLOCK]

    @property
    def gate(self) -> str:
        if self.blockers:
            return "BLOCKED"
        if self.failures:
            return "PROCEED WITH WARNINGS"
        return "CLEAR"

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame([r.to_dict() for r in self.results])

    def to_json(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(
                {
                    "dataset": self.dataset,
                    "channel": self.channel,
                    "created_utc": self.created_utc,
                    "gate": self.gate,
                    "counts": {
                        s: sum(1 for r in self.results if r.status == s)
                        for s in ("PASS", "FAIL", "WAIVED", "SKIP")
                    },
                    "results": [r.to_dict() for r in self.results],
                },
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        return p

    def summary_text(self) -> str:
        lines = [
            f"Validation gate: {self.gate}",
            f"dataset={self.dataset} channel={self.channel}",
            "",
        ]
        for r in sorted(
            self.results,
            key=lambda r: (
                {"FAIL": 0, "WAIVED": 1, "SKIP": 2, "PASS": 3}.get(r.status, 4),
                {BLOCK: 0, WARN: 1, INFO: 2}[r.severity],
                r.rule_id,
            ),
        ):
            lines.append(f"[{r.status:4}] {r.rule_id} {r.severity:5} {r.name}: {r.message}")
        return "\n".join(lines)


# --------------------------------------------------------------------------
# individual rules
# --------------------------------------------------------------------------


def rule_week_grid(df: pd.DataFrame, week_col: str) -> RuleResult:
    """KV-C01 - the weekly date grid is contiguous with no gaps."""
    if week_col not in df.columns:
        return RuleResult("KV-C01", "Week grid continuity", BLOCK, "SKIP",
                          f"no '{week_col}' column")
    g = week_grid_gaps(df[week_col])
    problems = []
    if g["missing"]:
        problems.append(f"{len(g['missing'])} missing week(s)")
    if g["irregular"]:
        problems.append(f"{len(g['irregular'])} off-grid date(s)")
    # An unparseable or blank week key is worse than a gap: the row still
    # carries volume, and every other rule that groups by week drops it
    # silently, so the grid would look clean over data it never saw.
    if g["n_unparseable"]:
        problems.append(f"{g['n_unparseable']} row(s) with no usable week key")
    # `duplicated_weeks` is reported but NOT failed on. A long-format load has
    # one row per week x dimension, so every week legitimately repeats. Row
    # level uniqueness is KV-C03's job, against the declared grain; failing it
    # here would fail every correctly shaped load.
    g["duplicated_weeks_note"] = (
        "informational only - repeated weeks are expected in a long-format load; "
        "KV-C03 checks uniqueness at the declared grain"
    )
    return RuleResult(
        "KV-C01",
        "Week grid continuity",
        BLOCK,
        "PASS" if not problems else "FAIL",
        (
            f"{g['n_weeks']} distinct weeks {g.get('first')}..{g.get('last')}, "
            "contiguous, all rows dated"
            if not problems
            else "; ".join(problems)
        ),
        g,
    )


def rule_period_coverage(
    df: pd.DataFrame, week_col: str, expected_start: str, expected_end: str
) -> RuleResult:
    """KV-C02 - the load covers exactly the requested reporting period."""
    if week_col not in df.columns:
        return RuleResult("KV-C02", "Period coverage", BLOCK, "SKIP", f"no '{week_col}'")
    s = pd.to_datetime(df[week_col])
    lo, hi = s.min(), s.max()
    e_lo, e_hi = pd.Timestamp(expected_start), pd.Timestamp(expected_end)
    ok = lo <= e_lo and hi >= e_hi
    return RuleResult(
        "KV-C02",
        "Period coverage",
        BLOCK,
        "PASS" if ok else "FAIL",
        f"load spans {lo.date()}..{hi.date()}; requested {e_lo.date()}..{e_hi.date()}",
        {"actual": [str(lo.date()), str(hi.date())],
         "expected": [str(e_lo.date()), str(e_hi.date())]},
    )


def rule_duplicate_grain(df: pd.DataFrame, grain: list[str]) -> RuleResult:
    """KV-C03 - one row per load grain; duplicates would double-count.

    Separates two kinds of duplicate, because they mean different things and
    imply different fixes. This distinction is taken from
    ``duplicate_key_count`` in the data-science plugin's ``quality_checks.py``:

    * **Full-row duplicates** -- identical in every column. Almost always a
      file appended twice, or a sheet read twice. Deduplicating is safe.
    * **Key-only duplicates** -- same grain, different metric values. A genuine
      conflict: two sources disagree about the same week, and someone has to
      decide which is right. Deduplicating silently picks a winner.
    """
    missing = [c for c in grain if c not in df.columns]
    if missing:
        return RuleResult("KV-C03", "Grain uniqueness", BLOCK, "SKIP",
                          f"missing grain column(s): {missing}")

    dup_key_rows = int(df.duplicated(subset=grain).sum())
    full_row_dups = int(df.duplicated().sum())
    key_only = max(dup_key_rows - full_row_dups, 0)
    affected = df.duplicated(subset=grain, keep=False)

    detail = {
        "grain": grain,
        "duplicate_key_rows": dup_key_rows,
        "full_row_duplicates": full_row_dups,
        "key_only_duplicates": key_only,
        "unique_keys": int(df[grain].drop_duplicates().shape[0]),
        "rows_involved": int(affected.sum()),
        "examples": (
            df.loc[affected, grain].drop_duplicates().head(10).astype(str).to_dict("records")
            if dup_key_rows else []
        ),
    }
    if not dup_key_rows:
        msg = f"no duplicate rows across {len(df)} rows at the declared grain"
    else:
        parts = []
        if full_row_dups:
            parts.append(f"{full_row_dups} full-row duplicate(s) - likely a file read twice")
        if key_only:
            parts.append(
                f"{key_only} key-only duplicate(s) - same grain, different values, "
                "so two sources disagree and deduplicating would pick a winner silently"
            )
        # The commonest cause of this failing on a *correct* load: the grain is
        # the week plus whatever you declared, and the template drops the
        # columns that actually distinguish the rows (creative name, ad id).
        # Without saying so the message reads like a broken tool, and the fix
        # someone reaches for -- deduplicating -- is the one that loses data.
        parts.append(
            f"grain declared as {len(grain)} column(s) over {len(df)} rows "
            f"({detail['unique_keys']} distinct). If the template drops columns that "
            "distinguish these rows (creative, ad id), the duplicates are real and "
            "expected: check the maintained file for the same profile, then waive "
            "KV-C03 in rules.yaml with the figures recorded rather than deduplicating"
        )
        msg = "; ".join(parts)
    return RuleResult(
        "KV-C03", "Grain uniqueness", BLOCK,
        "PASS" if not dup_key_rows else "FAIL", msg, detail,
    )


def rule_required_columns(df: pd.DataFrame, required: list[str]) -> RuleResult:
    """KV-C04 - every column Element X requires is present."""
    missing = [c for c in required if c not in df.columns]
    return RuleResult(
        "KV-C04",
        "Required columns present",
        BLOCK,
        "PASS" if not missing else "FAIL",
        "all required columns present" if not missing else f"missing: {missing}",
        {"required": required, "missing": missing},
    )


def rule_metric_nulls(df: pd.DataFrame, metric_cols: list[str]) -> RuleResult:
    """KV-C05 - metrics are populated; a null metric silently drops spend."""
    cols = [c for c in metric_cols if c in df.columns]
    if not cols:
        return RuleResult("KV-C05", "Metric completeness", BLOCK, "SKIP", "no metric columns")
    detail = {c: int(pd.to_numeric(df[c], errors="coerce").isna().sum()) for c in cols}
    bad = {k: v for k, v in detail.items() if v}
    return RuleResult(
        "KV-C05",
        "Metric completeness",
        BLOCK,
        "PASS" if not bad else "FAIL",
        "no null metric values" if not bad else f"null metric values: {bad}",
        detail,
    )


def rule_dimension_nulls(
    df: pd.DataFrame, dim_cols: list[str], threshold_pct: float = 5.0
) -> RuleResult:
    """KV-C06 - model breakdown dimensions are populated.

    A null in a breakdown dimension is not harmless: the row still carries
    spend, so the model gets pressure it cannot attribute.
    """
    cols = [c for c in dim_cols if c in df.columns]
    if not cols:
        return RuleResult("KV-C06", "Breakdown dimension completeness", WARN, "SKIP",
                          "no breakdown dimensions configured")
    n = len(df)
    if n == 0:
        return RuleResult("KV-C06", "Breakdown dimension completeness", BLOCK, "FAIL",
                          "the load is empty -- no rows to validate", {"n_rows": 0})
    detail = {
        c: round(100.0 * float(df[c].isna().sum() + (df[c].astype(str).str.strip() == "").sum()) / n, 2)
        for c in cols
    }
    bad = {k: v for k, v in detail.items() if v > threshold_pct}
    return RuleResult(
        "KV-C06",
        "Breakdown dimension completeness",
        WARN,
        "PASS" if not bad else "FAIL",
        (
            f"all breakdown dimensions under {threshold_pct}% null"
            if not bad
            else f"null rate above {threshold_pct}%: {bad}"
        ),
        {"null_pct": detail, "threshold_pct": threshold_pct},
    )


def rule_unclassified_bucket(
    df: pd.DataFrame,
    dim_cols: list[str],
    metric_cols: list[str],
    tokens: tuple[str, ...] = ("NEEDS CLASSIFICATION", "UNKNOWN", "UNCLASSIFIED", "OTHER - TBD", "#N/A"),
) -> RuleResult:
    """KV-C07 - no placeholder classification values carrying real metrics."""
    hits = []
    for c in [c for c in dim_cols if c in df.columns]:
        vals = df[c].astype(str).str.strip().str.upper()
        mask = vals.isin([t.upper() for t in tokens])
        if mask.any():
            present = [m for m in metric_cols if m in df.columns]
            row = {"column": c, "n_rows": int(mask.sum()), "metrics_measured": present}
            for m in present:
                v = pd.to_numeric(df.loc[mask, m], errors="coerce")
                # Absolute, unrounded: a +5,000 and a -5,000 row net to zero but
                # are still 10,000 of unattributable spend, and 0.004 is not zero.
                row[m] = float(v.sum())
                row[f"{m}__abs"] = float(v.abs().sum())
            hits.append(row)
    measured = any(h["metrics_measured"] for h in hits)
    material = [
        h for h in hits
        if any(v > 0 for k, v in h.items() if k.endswith("__abs"))
    ]
    if not hits:
        status, sev, msg = "PASS", WARN, "no placeholder classification values"
    elif material:
        status, sev, msg = "FAIL", BLOCK, f"placeholder values carry non-zero metrics: {material}"
    elif not measured:
        status, sev, msg = ("SKIP", BLOCK,
                            f"placeholder values present in {[h['column'] for h in hits]} but "
                            "none of the metric columns are in this frame, so materiality "
                            "was not measured")
    else:
        status, sev, msg = "FAIL", WARN, f"placeholder values present but carry zero metrics: {hits}"
    return RuleResult("KV-C07", "No unclassified buckets", sev, status, msg, {"hits": hits})


def rule_non_negative(df: pd.DataFrame, metric_cols: list[str]) -> RuleResult:
    """KV-C08 - metrics are non-negative unless the channel allows credits."""
    cols = [c for c in metric_cols if c in df.columns]
    if not cols:
        return RuleResult("KV-C08", "Non-negative metrics", BLOCK, "SKIP", "no metric columns")
    detail = {c: int((pd.to_numeric(df[c], errors="coerce") < 0).sum()) for c in cols}
    bad = {k: v for k, v in detail.items() if v}
    return RuleResult(
        "KV-C08",
        "Non-negative metrics",
        BLOCK,
        "PASS" if not bad else "FAIL",
        "no negative metric values" if not bad else f"negative values: {bad}",
        detail,
    )


def rule_metric_coherence(
    df: pd.DataFrame,
    spend_col: str | None = "Spend",
    impression_col: str | None = "Impressions",
    click_col: str | None = "Clicks",
) -> RuleResult:
    """KV-C09 - spend without delivery, or clicks above impressions.

    Column names are parameters rather than constants because HCP loads and
    renamed templates carry the same quantities under different names; hard-
    coding them makes the rule SKIP silently on every non-media dataset.
    """
    if not spend_col or not impression_col or spend_col not in df.columns or impression_col not in df.columns:
        return RuleResult("KV-C09", "Metric coherence", WARN, "SKIP",
                          f"spend/impression columns not both present "
                          f"(looked for {spend_col!r} and {impression_col!r})")
    sp = pd.to_numeric(df[spend_col], errors="coerce").fillna(0)
    im = pd.to_numeric(df[impression_col], errors="coerce").fillna(0)
    detail = {
        "spend_without_impressions": int(((sp > 0) & (im <= 0)).sum()),
        "impressions_without_spend": int(((im > 0) & (sp <= 0)).sum()),
    }
    if click_col and click_col in df.columns:
        cl = pd.to_numeric(df[click_col], errors="coerce").fillna(0)
        detail["clicks_exceed_impressions"] = int((cl > im).sum())
    bad = {k: v for k, v in detail.items() if v}
    return RuleResult(
        "KV-C09",
        "Metric coherence",
        WARN,
        "PASS" if not bad else "FAIL",
        "spend, impressions and clicks are mutually coherent" if not bad else str(bad),
        detail,
    )


def rule_weekly_outliers(
    df: pd.DataFrame,
    week_col: str,
    metric_cols: list[str],
    *,
    group_cols: list[str] | None = None,
    z_threshold: float = 5.0,
    min_active_weeks: int = 8,
) -> RuleResult:
    """KV-C10 - flag extreme weeks using a robust (median/MAD) z-score.

    A robust score is used rather than mean/sd because a single 50x week
    inflates the sd enough to hide itself.
    """
    if week_col not in df.columns:
        return RuleResult("KV-C10", "Weekly outliers", WARN, "SKIP", f"no '{week_col}'")
    cols = [c for c in metric_cols if c in df.columns]
    if not cols:
        return RuleResult("KV-C10", "Weekly outliers", WARN, "SKIP", "no metric columns")
    group_cols = [c for c in (group_cols or []) if c in df.columns]
    keys = group_cols + [week_col]
    series = df.groupby(keys, dropna=False)[cols].sum().reset_index()

    flagged: list[dict] = []
    not_examined: list[dict] = []
    n_examined = 0
    grouper = series.groupby(group_cols, dropna=False) if group_cols else [((), series)]
    for gkey, g in grouper:
        gd = dict(zip(group_cols, np.atleast_1d(gkey))) if group_cols else {}
        for c in cols:
            active = pd.to_numeric(g[c], errors="coerce").dropna()
            active = active[active != 0]
            if len(active) < min_active_weeks:
                # Silently skipping here and still reporting "no outliers" would
                # green-light a 60x spike in a short series. Record it instead.
                not_examined.append({"group": gd, "metric": c,
                                     "active_weeks": int(len(active)),
                                     "reason": f"fewer than {min_active_weeks} active weeks"})
                continue
            med = float(active.median())
            mad = float((active - med).abs().median())
            if mad == 0:
                not_examined.append({"group": gd, "metric": c,
                                     "active_weeks": int(len(active)),
                                     "reason": "zero MAD (series is flat)"})
                continue
            n_examined += 1
            # Score only the active weeks. A zero week scores a huge negative z
            # against a non-zero median, but a gap is KV-C11's finding, not an
            # outlier -- reporting it here would double-count and mislabel it.
            z = 0.6745 * (active - med) / mad
            for idx in active.index[np.abs(z) > z_threshold]:
                flagged.append(
                    {
                        "group": gd,
                        "metric": c,
                        "week": str(pd.Timestamp(g.at[idx, week_col]).date()),
                        "value": round(float(g.at[idx, c]), 2),
                        "median": round(med, 2),
                        "robust_z": round(float(z.loc[idx]), 1),
                    }
                )
    if not n_examined:
        return RuleResult(
            "KV-C10", "Weekly outliers", WARN, "SKIP",
            f"no series had {min_active_weeks}+ active weeks, so no series was tested "
            f"({len(not_examined)} series skipped)",
            {"z_threshold": z_threshold, "not_examined": not_examined[:60],
             "n_not_examined": len(not_examined)},
        )
    msg = (
        f"no week exceeds robust z={z_threshold} across {n_examined} series"
        if not flagged
        else f"{len(flagged)} week/metric point(s) exceed robust z={z_threshold}"
    )
    if not_examined:
        msg += f"; {len(not_examined)} series too short or too flat to test"
    return RuleResult(
        "KV-C10", "Weekly outliers", WARN,
        "PASS" if not flagged else "FAIL", msg,
        {"z_threshold": z_threshold, "n_series_examined": n_examined,
         "flagged": flagged[:60], "n_flagged": len(flagged),
         "not_examined": not_examined[:60], "n_not_examined": len(not_examined)},
    )


def rule_zero_runs(
    df: pd.DataFrame,
    week_col: str,
    metric_cols: list[str],
    *,
    group_cols: list[str] | None = None,
    min_run: int = 4,
) -> RuleResult:
    """KV-C11 - flag blank/zero stretches inside an otherwise active series.

    This is the "blank time periods" check from step 7 of the media process:
    a channel that ran all quarter but has four consecutive zero weeks in the
    middle is usually a delivery gap in the file, not in the market.

    Leading and trailing zero runs are a different thing -- a channel that had
    not launched yet, or one that has stopped -- so they do not fail the rule.
    They are still reported, under ``detail["edges"]``, because a channel going
    silent for the last month of a load is equally often a missing final file.
    """
    if week_col not in df.columns:
        return RuleResult("KV-C11", "Interior zero runs", WARN, "SKIP", f"no '{week_col}'")
    cols = [c for c in metric_cols if c in df.columns]
    if not cols:
        # Without this guard the metric loop never runs, `flagged` stays empty
        # and the rule reports PASS -- a false green from a column rename.
        return RuleResult("KV-C11", "Interior zero runs", WARN, "SKIP",
                          f"none of {metric_cols} are columns of this frame")
    group_cols = [c for c in (group_cols or []) if c in df.columns]
    series = df.groupby(group_cols + [week_col], dropna=False)[cols].sum().reset_index()

    # A gap in a media extract is usually an *absent row*, not a zero. Without
    # reindexing each group onto the load's full week grid, this rule can only
    # ever see explicit zeros and would silently miss the case it exists for.
    all_weeks = pd.Index(sorted(pd.to_datetime(series[week_col]).unique()), name=week_col)
    series[week_col] = pd.to_datetime(series[week_col])

    flagged: list[dict] = []
    edges: list[dict] = []
    grouper = series.groupby(group_cols, dropna=False) if group_cols else [((), series)]
    for gkey, g in grouper:
        g = (
            g.set_index(week_col)[cols]
            .reindex(all_weeks, fill_value=0.0)
            .fillna(0.0)
            .reset_index()
        )
        gd = dict(zip(group_cols, np.atleast_1d(gkey))) if group_cols else {}
        for c in cols:
            v = pd.to_numeric(g[c], errors="coerce").fillna(0).to_numpy()
            nz = np.nonzero(v)[0]
            if len(nz) < 2:
                continue
            first, last = int(nz[0]), int(nz[-1])
            run = 0
            for i in range(first, last + 1):
                if v[i] == 0:
                    run += 1
                else:
                    if run >= min_run:
                        flagged.append(
                            {
                                "group": gd,
                                "metric": c,
                                "run_weeks": int(run),
                                "from": str(pd.Timestamp(g.at[i - run, week_col]).date()),
                                "to": str(pd.Timestamp(g.at[i - 1, week_col]).date()),
                            }
                        )
                    run = 0
            # leading / trailing inactivity: reported, not failed
            if first >= min_run:
                edges.append({"group": gd, "metric": c, "edge": "leading",
                              "run_weeks": first,
                              "from": str(pd.Timestamp(g.at[0, week_col]).date()),
                              "to": str(pd.Timestamp(g.at[first - 1, week_col]).date())})
            trail = len(v) - 1 - last
            if trail >= min_run:
                edges.append({"group": gd, "metric": c, "edge": "trailing",
                              "run_weeks": int(trail),
                              "from": str(pd.Timestamp(g.at[last + 1, week_col]).date()),
                              "to": str(pd.Timestamp(g.at[len(v) - 1, week_col]).date())})
    msg = (
        f"no interior zero run of {min_run}+ weeks"
        if not flagged
        else f"{len(flagged)} interior zero run(s) of {min_run}+ weeks"
    )
    if edges:
        n_trail = sum(1 for e in edges if e["edge"] == "trailing")
        msg += (
            f"; {len(edges)} edge run(s) reported not failed "
            f"({n_trail} trailing - confirm the flight ended rather than the file being short)"
        )
    return RuleResult(
        "KV-C11",
        "Interior zero runs",
        WARN,
        "PASS" if not flagged else "FAIL",
        msg,
        {"min_run": min_run, "flagged": flagged[:60], "n_flagged": len(flagged),
         "edges": edges[:60], "n_edges": len(edges)},
    )


def rule_period_step_change(
    df: pd.DataFrame,
    week_col: str,
    metric_cols: list[str],
    *,
    group_cols: list[str] | None = None,
    pct_threshold: float = 50.0,
    n_periods: int = 4,
    period_col: str | None = None,
    weeks_per_period: int = 13,
) -> RuleResult:
    """KV-C12 - quarter-on-quarter step changes worth a client question."""
    if week_col not in df.columns:
        return RuleResult("KV-C12", "Period step change", WARN, "SKIP", f"no '{week_col}'")
    cols = [c for c in metric_cols if c in df.columns]
    if not cols:
        return RuleResult("KV-C12", "Period step change", WARN, "SKIP",
                          f"none of {metric_cols} are columns of this frame")
    group_cols = [c for c in (group_cols or []) if c in df.columns]
    d = df.copy()
    d[week_col] = pd.to_datetime(d[week_col])
    if period_col and period_col in d.columns:
        d["_q"] = d[period_col].astype(str)
    else:
        # Calendar quarters do NOT align to a 4-4-5 fiscal year: Abbott's Q4'24
        # starts 2024-09-29, whose first week falls in calendar Q3. Bucketing on
        # dt.to_period("Q") therefore compares a one-week stub against a full
        # quarter and fabricates a four-figure percentage on flat data.
        # Bucket into consecutive `weeks_per_period` blocks from the series
        # start instead, and drop any trailing partial block.
        weeks = pd.Index(sorted(d[week_col].dropna().unique()))
        idx = {w: i for i, w in enumerate(weeks)}
        d["_wi"] = d[week_col].map(idx)
        d = d[d["_wi"].notna()]
        d["_b"] = (d["_wi"] // weeks_per_period).astype(int)
        complete = [
            b for b in sorted(d["_b"].unique())
            if len(weeks) - b * weeks_per_period >= weeks_per_period
        ]
        dropped = sorted(set(d["_b"].unique()) - set(complete))
        d = d[d["_b"].isin(complete)]
        first = weeks[0] if len(weeks) else None
        d["_q"] = d["_b"].map(
            lambda b: f"P{b+1} ({(first + pd.Timedelta(days=7*b*weeks_per_period)).date()})"
            if first is not None else str(b)
        )
    agg = d.groupby(group_cols + ["_q"], dropna=False)[cols].sum().reset_index()
    flagged = []
    grouper = agg.groupby(group_cols, dropna=False) if group_cols else [((), agg)]
    for gkey, g in grouper:
        g = g.sort_values("_q").tail(n_periods + 1)
        for c in cols:
            v = pd.to_numeric(g[c], errors="coerce").fillna(0).to_numpy()
            qs = g["_q"].astype(str).tolist()
            for i in range(1, len(v)):
                if v[i - 1] == 0:
                    continue
                pct = 100.0 * (v[i] - v[i - 1]) / v[i - 1]
                if abs(pct) >= pct_threshold:
                    flagged.append(
                        {
                            "group": dict(zip(group_cols, np.atleast_1d(gkey))) if group_cols else {},
                            "metric": c,
                            "from_period": qs[i - 1],
                            "to_period": qs[i],
                            "pct_change": round(float(pct), 1),
                            "from_value": round(float(v[i - 1]), 2),
                            "to_value": round(float(v[i]), 2),
                        }
                    )
    return RuleResult(
        "KV-C12",
        "Period step change",
        WARN,
        "PASS" if not flagged else "FAIL",
        (
            f"no quarter-on-quarter move beyond {pct_threshold}%"
            if not flagged
            else f"{len(flagged)} quarter-on-quarter move(s) beyond {pct_threshold}%"
        ),
        {"pct_threshold": pct_threshold, "flagged": flagged[:60], "n_flagged": len(flagged)},
    )


def rule_parts_vs_total(
    parts: pd.DataFrame,
    total: pd.DataFrame,
    key_cols: list[str],
    value_col: str,
    *,
    tolerance_pct: float = 0.5,
    abs_tolerance: float = 1e-6,
) -> RuleResult:
    """KV-C13 - the breakdown columns sum to the raw TOTAL column."""
    p = parts.groupby(key_cols, dropna=False)[value_col].sum()
    t = total.groupby(key_cols, dropna=False)[value_col].sum()
    j = pd.concat([p.rename("parts"), t.rename("total")], axis=1)
    if j.empty:
        return RuleResult("KV-C13", "Parts reconcile to TOTAL", BLOCK, "SKIP",
                          "no keys on either side")

    # A key present on only one side is the loudest possible signal -- a whole
    # period missing from the breakdown, or a TOTAL column that was not read.
    # dropna()-ing it away would report PASS over the periods that survived.
    parts_only = j.index[j["total"].isna()].tolist()
    total_only = j.index[j["parts"].isna()].tolist()
    both = j.dropna()

    # pct_diff is undefined when total == 0, and NaN never trips an
    # `abs() > tol` comparison -- so a zero TOTAL against non-zero parts would
    # pass. Compare on absolute difference in that case.
    both = both.assign(
        abs_diff=(both["parts"] - both["total"]).abs(),
        pct_diff=100.0 * (both["parts"] - both["total"]) / both["total"].replace(0, np.nan),
    )
    zero_total_bad = both[(both["total"] == 0) & (both["abs_diff"] > abs_tolerance)]
    pct_bad = both[both["pct_diff"].abs() > tolerance_pct]
    bad = pd.concat([zero_total_bad, pct_bad]).drop_duplicates()

    problems = []
    if parts_only:
        problems.append(f"{len(parts_only)} key(s) present in the breakdown but not in TOTAL")
    if total_only:
        problems.append(f"{len(total_only)} key(s) present in TOTAL but not in the breakdown")
    if not bad.empty:
        problems.append(f"{len(bad)} key(s) where the breakdown does not sum to TOTAL")

    return RuleResult(
        "KV-C13",
        "Parts reconcile to TOTAL",
        BLOCK,
        "PASS" if not problems else "FAIL",
        (
            f"breakdown sums to TOTAL within {tolerance_pct}% for all {len(both)} keys, "
            "and both sides carry the same keys"
            if not problems
            else "; ".join(problems)
        ),
        {
            "tolerance_pct": tolerance_pct,
            "abs_tolerance": abs_tolerance,
            "n_keys_compared": int(len(both)),
            "keys_in_parts_only": [str(k) for k in parts_only[:20]],
            "keys_in_total_only": [str(k) for k in total_only[:20]],
            "worst": bad.reindex(bad["abs_diff"].sort_values(ascending=False).index)
            .head(10)
            .round(4)
            .reset_index()
            .astype(str)
            .to_dict("records"),
        },
    )


def rule_annual_conservation(
    recon: pd.DataFrame,
    value_col: str,
    *,
    tolerance_pct: float = 0.5,
    weeks_by_period: dict | pd.Series | None = None,
    divisor: float | None = None,
) -> RuleResult:
    """KV-C14 - disaggregation conserves the annual total.

    Deliberately annual, not monthly: the flat 4.33 divisor conserves the year
    and not the month by design (see ``calendar_fiscal``). Asserting the
    monthly identity here would fail every load for a reason that is not a bug.

    **The divisor's own drift is not a failure, and calling it one is worse
    than not checking.** A flat divisor conserves the year only when the
    monthly values are evenly spread: a month landing in a 5-week block is
    scaled by 5/4.33, one in a 4-week block by 4/4.33, so a real load whose
    volume sits in the 4-week blocks lands a percent or so low. The Direct
    Mail load that reproduces the client's own file *byte for byte* comes out
    at -1.11%. Failing that as a BLOCK teaches everyone to ignore KV-C14,
    which is how the rule stops catching the thing it exists for.

    So when ``weeks_by_period`` and ``divisor`` are supplied, the rule
    re-derives what each period's weekly total *should* be, straight from the
    calendar, and compares period by period. That still catches the failure
    that matters -- rows lost in a merge, a period silently duplicated or
    dropped -- while the arithmetic the divisor was chosen for passes.
    Without them it falls back to the flat annual tolerance.
    """
    a, b = f"{value_col}__monthly_in", f"{value_col}__weekly_out"
    if a not in recon.columns or b not in recon.columns:
        return RuleResult("KV-C14", "Disaggregation conserves annual total", BLOCK, "SKIP",
                          f"reconciliation frame lacks {a}/{b}")

    if weeks_by_period is not None:
        return _conservation_against_calendar(
            recon, value_col, a, b, weeks_by_period, divisor
        )

    # `tin` MUST be the total of everything supplied, covered or not. Summing
    # only the covered rows would let a calendar that misses three months
    # report conservation against the truncated input it happened to keep.
    tin = float(recon[a].sum())
    tout = float(recon[b].sum())
    uncovered = (
        recon[~recon["covered"]] if "covered" in recon.columns else recon.iloc[0:0]
    )
    lost = float(uncovered[a].sum()) if len(uncovered) else 0.0
    pct = 100.0 * (tout - tin) / tin if tin else np.nan

    # The worst *per-period* difference is only meaningful for periods that were
    # actually disaggregated; an excluded period is -100% by construction and
    # would drown out the real 4.33 signal (+15.5% / -7.6%).
    pd_col = f"{value_col}__pct_diff"
    covered_rows = recon[recon["covered"]] if "covered" in recon.columns else recon
    worst = (
        float(covered_rows[pd_col].abs().max())
        if pd_col in recon.columns and len(covered_rows)
        else float("nan")
    )
    problems = []
    if len(uncovered):
        periods = [str(pd.Timestamp(p).date()) for p in uncovered.iloc[:, 0]]
        problems.append(
            f"{len(uncovered)} period(s) fell outside the fiscal calendar and were "
            f"excluded, taking {lost:,.2f} ({100.0*lost/tin:.1f}% of input) with them: "
            f"{periods[:6]}"
        )
    if not (abs(pct) <= tolerance_pct):
        problems.append(f"annual total moved {pct:+.3f}% (tolerance {tolerance_pct}%)")
    return RuleResult(
        "KV-C14",
        "Disaggregation conserves annual total",
        BLOCK,
        "PASS" if not problems else "FAIL",
        (
            f"annual in={tin:,.2f} out={tout:,.2f} ({pct:+.3f}%), every period covered; "
            f"worst single period {worst:+.1f}% (expected, from the 4.33 divisor)"
            if not problems
            else "; ".join(problems)
        ),
        {"monthly_in": tin, "weekly_out": tout, "pct_diff": pct,
         "excluded_input_total": lost, "n_periods_excluded": int(len(uncovered)),
         "worst_period_pct": worst, "tolerance_pct": tolerance_pct},
    )


def _conservation_against_calendar(
    recon: pd.DataFrame,
    value_col: str,
    a: str,
    b: str,
    weeks_by_period,
    divisor,
) -> RuleResult:
    """KV-C14, re-derived from the calendar rather than trusted.

    ``expected = monthly_in * n_weeks / divisor`` (or ``monthly_in`` exactly
    when ``divisor`` is None, the month-conserving mode). Any period whose
    weekly output does not equal its own expectation is a defect in the
    disaggregation, and it fails whatever the annual total happens to say.
    """
    period_col = recon.columns[0]
    weeks = pd.Series(weeks_by_period)
    weeks.index = pd.to_datetime(weeks.index)
    covered = recon[recon["covered"]] if "covered" in recon.columns else recon
    uncovered = recon[~recon["covered"]] if "covered" in recon.columns else recon.iloc[0:0]

    tin = float(recon[a].sum())
    tout = float(recon[b].sum())
    pct = 100.0 * (tout - tin) / tin if tin else np.nan

    rows, worst_rel, unknown = [], 0.0, []
    for _, r in covered.iterrows():
        key = pd.Timestamp(r[period_col])
        if key not in weeks.index:
            unknown.append(str(key.date()))
            continue
        w = float(weeks.loc[key])
        expected = float(r[a]) * (w / float(divisor) if divisor else 1.0)
        got = float(r[b])
        denom = max(abs(expected), 1e-9)
        rel = abs(got - expected) / denom
        worst_rel = max(worst_rel, rel)
        if rel > 1e-9:
            rows.append(
                {"period": str(key.date()), "n_weeks": w, "expected": expected,
                 "weekly_out": got, "rel_diff": rel}
            )

    expected_total = sum(
        float(r[a]) * (float(weeks.loc[pd.Timestamp(r[period_col])]) / float(divisor)
                       if divisor else 1.0)
        for _, r in covered.iterrows()
        if pd.Timestamp(r[period_col]) in weeks.index
    )
    expected_pct = 100.0 * (expected_total - tin) / tin if tin else np.nan

    problems = []
    if len(uncovered):
        lost = float(uncovered[a].sum())
        periods = [str(pd.Timestamp(p).date()) for p in uncovered[period_col]]
        problems.append(
            f"{len(uncovered)} period(s) fell outside the fiscal calendar and were "
            f"excluded, taking {lost:,.2f} ({100.0*lost/tin:.1f}% of input) with them: "
            f"{periods[:6]}"
        )
    if unknown:
        problems.append(
            f"{len(unknown)} disaggregated period(s) are not in the calendar at all: "
            f"{unknown[:6]} -- the reconciliation and the calendar disagree about "
            "which periods exist"
        )
    if rows:
        problems.append(
            f"{len(rows)} period(s) do not equal monthly x weeks/divisor; worst "
            f"{max(r['rel_diff'] for r in rows):.2e} relative: {rows[:4]}"
        )

    return RuleResult(
        "KV-C14",
        "Disaggregation conserves annual total",
        BLOCK,
        "PASS" if not problems else "FAIL",
        (
            f"annual in={tin:,.2f} out={tout:,.2f} ({pct:+.3f}%), which is exactly the "
            f"{expected_pct:+.3f}% the divisor {divisor} predicts for this month mix; "
            f"every period covered and every period equals monthly x weeks/divisor "
            f"(worst {worst_rel:.2e} relative)"
            if not problems
            else "; ".join(problems)
        ),
        {
            "monthly_in": tin,
            "weekly_out": tout,
            "pct_diff": pct,
            "expected_pct_diff": expected_pct,
            "divisor": divisor,
            "worst_period_rel_diff": worst_rel,
            "n_periods_excluded": int(len(uncovered)),
            "offending_periods": rows[:20],
        },
    )


def rule_lag_warmup(warmups: list[dict], *, max_understated_pct: float = 1.0) -> RuleResult:
    """KV-C16 - the redemption lag has enough drop history behind the window.

    Redemptions in the first month of a load depend on coupons dropped up to
    eighteen months earlier. If the extract begins where the load begins, the
    opening months are computed from a profile whose tail has nothing behind
    it, and they come out low -- smoothly, plausibly, and by an amount nothing
    else in the suite can see. This is the only check that looks.
    """
    if not warmups:
        return RuleResult("KV-C16", "Lag has enough drop history", BLOCK, "SKIP",
                          "no series on this load applies a redemption lag")
    worst = max(warmups, key=lambda w: w.get("first_month_understated_pct", 0.0))
    bad = [w for w in warmups
           if w.get("first_month_understated_pct", 0.0) > max_understated_pct]
    detail = {
        "n_series": len(warmups),
        "max_understated_pct": worst.get("first_month_understated_pct"),
        "tolerance_pct": max_understated_pct,
        "series": sorted(
            warmups, key=lambda w: -w.get("first_month_understated_pct", 0.0)
        )[:20],
    }
    if not bad:
        return RuleResult(
            "KV-C16", "Lag has enough drop history", BLOCK, "PASS",
            f"every lagged series has the {worst['months_the_profile_needs']} months of "
            f"drop history the profile needs before {worst['window_start']} "
            f"(worst series understated by {worst['first_month_understated_pct']:.2f}%)",
            detail,
        )
    return RuleResult(
        "KV-C16", "Lag has enough drop history", BLOCK, "FAIL",
        f"{len(bad)} lagged series start too close to the beginning of the extract: "
        f"the first month of the load is understated by up to "
        f"{worst['first_month_understated_pct']:.1f}% because the redemption profile "
        f"reaches back {worst['months_the_profile_needs']} months and only "
        f"{worst['months_of_history_before_window']} are present",
        detail,
    )


def rule_append_seam(
    historical: pd.DataFrame, new: pd.DataFrame, week_col: str, dim_cols: list[str]
) -> RuleResult:
    """KV-C15 - the new load joins the historical file without gap or overlap."""
    h = pd.to_datetime(historical[week_col])
    n = pd.to_datetime(new[week_col])
    gap_days = (n.min() - h.max()).days
    overlap_weeks = sorted(set(n) & set(h))
    overlap = len(overlap_weeks)
    schema_new = [c for c in new.columns if c not in historical.columns]
    schema_lost = [c for c in historical.columns if c not in new.columns]
    problems = {}
    if gap_days != 7 and overlap == 0:
        problems["gap_days"] = gap_days
    if overlap:
        problems["overlapping_weeks"] = overlap
        problems["overlapping_week_dates"] = [str(pd.Timestamp(w).date()) for w in overlap_weeks[:12]]
    if schema_new:
        problems["columns_new_in_load"] = schema_new
    if schema_lost:
        problems["columns_missing_from_load"] = schema_lost
    dim_new = {}
    for c in dim_cols:
        if c in historical.columns and c in new.columns:
            fresh = sorted(set(new[c].dropna().astype(str)) - set(historical[c].dropna().astype(str)))
            if fresh:
                dim_new[c] = fresh
    if dim_new:
        problems["dimension_values_new_in_load"] = dim_new
    return RuleResult(
        "KV-C15",
        "Append seam integrity",
        # A gap wider than one week is a hole in the model input, not a note:
        # nothing else catches it, because KV-C01/C02 only look inside the load.
        BLOCK
        if (
            "overlapping_weeks" in problems
            or "columns_missing_from_load" in problems
            or problems.get("gap_days", 7) > 7
        )
        else WARN,
        "PASS" if not problems else "FAIL",
        (
            f"load starts {gap_days} day(s) after history ends; schema and dimensions align"
            if not problems
            else f"seam issues: {list(problems)}"
        ),
        {"history_last_week": str(h.max().date()), "load_first_week": str(n.min().date()), **problems},
    )


# --------------------------------------------------------------------------
# runner
# --------------------------------------------------------------------------


def run_standard_suite(
    df: pd.DataFrame,
    *,
    dataset: str,
    channel: str,
    week_col: str = "Week Starting Date",
    metric_cols: list[str],
    dim_cols: list[str],
    grain: list[str] | None = None,
    required_cols: list[str] | None = None,
    expected_period: tuple[str, str] | None = None,
    group_cols: list[str] | None = None,
    thresholds: dict | None = None,
    coherence_cols: tuple[str | None, str | None, str | None] = ("Spend", "Impressions", "Clicks"),
    strict_columns: bool = True,
) -> ValidationReport:
    """Run the standard rule suite over a prepared load.

    ``strict_columns`` (the default) raises when a configured metric column is
    not in the frame. A silently ignored metric column turns several rules into
    unconditional passes, so a typo or a rename between the config and the
    frame should stop the run rather than colour the report green.
    """
    t = {
        "dimension_null_pct": 5.0,
        "outlier_z": 5.0,
        "zero_run_weeks": 4,
        "step_change_pct": 50.0,
    }
    t.update(thresholds or {})
    grain = grain or ([week_col] + dim_cols)

    if strict_columns:
        absent = [c for c in metric_cols if c not in df.columns]
        if absent:
            raise KeyError(
                f"metric_cols not present in the frame: {absent}. "
                "Several rules would silently pass without them; fix the column "
                "names or pass strict_columns=False to accept SKIPs."
            )
    if df.empty:
        return ValidationReport(
            dataset=dataset,
            channel=channel,
            results=[
                RuleResult("KV-C00", "Load is non-empty", BLOCK, "FAIL",
                           "the prepared load has zero rows -- nothing was validated",
                           {"n_rows": 0})
            ],
        )

    results = [
        rule_week_grid(df, week_col),
        rule_duplicate_grain(df, grain),
        rule_metric_nulls(df, metric_cols),
        rule_dimension_nulls(df, dim_cols, t["dimension_null_pct"]),
        rule_unclassified_bucket(df, dim_cols, metric_cols),
        rule_non_negative(df, metric_cols),
        rule_metric_coherence(df, *coherence_cols),
        rule_weekly_outliers(df, week_col, metric_cols, group_cols=group_cols,
                             z_threshold=t["outlier_z"]),
        rule_zero_runs(df, week_col, metric_cols, group_cols=group_cols,
                       min_run=t["zero_run_weeks"]),
        rule_period_step_change(df, week_col, metric_cols, group_cols=group_cols,
                                pct_threshold=t["step_change_pct"]),
    ]
    if required_cols:
        results.insert(0, rule_required_columns(df, required_cols))
    if expected_period:
        results.insert(1, rule_period_coverage(df, week_col, *expected_period))
    return ValidationReport(dataset=dataset, channel=channel, results=results)
