#!/usr/bin/env python3
"""Regression tests for the defects an adversarial review found in v0.1.0.

Every test here corresponds to a case where the library previously returned a
PASS, a match, or a plausible number when it should have refused. A validation
library that greens a broken load is worse than no library, so these are the
tests that matter most.

Run: python tests/test_no_false_pass.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from kvprep import reconcile, template_fill as tf, validate  # noqa: E402
from kvprep.calendar_fiscal import (  # noqa: E402
    UncoveredPeriodError,
    build_445_calendar,
    disaggregate_monthly_to_weekly,
    week_grid_gaps,
)

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name} {detail}")
        FAILURES.append(name)


def weeks(n: int, start: str = "2025-01-05") -> pd.Series:
    return pd.date_range(start, periods=n, freq="7D")


# --------------------------------------------------------------------------
print("\ncalendar / disaggregation")
# --------------------------------------------------------------------------

# The Abbott convention must be reproduced exactly: the block beginning
# 2024-09-29 is labelled 2024-10-01, and the year is 4-4-5.
cal = build_445_calendar("2024-09-29", 1)
check(
    "Abbott FY25 first block labelled 2024-10-01",
    str(cal.loc[0, "period"].date()) == "2024-10-01" and cal.loc[0, "n_weeks_in_month"] == 4,
    f"got {cal.loc[0, 'period']} / {cal.loc[0, 'n_weeks_in_month']}",
)
check(
    "52 weeks over 12 distinct fiscal months",
    len(cal) == 52 and cal["period"].nunique() == 12,
)

# Period labels must never collide, whatever the fiscal anchor. Deriving them
# from the block's start month silently merged two blocks and skipped a month.
ok = True
for anchor in ("2025-01-05", "2025-01-01", "2024-12-29", "2025-06-01", "2023-04-02", "2026-02-01"):
    c = build_445_calendar(anchor, 1)
    if c["period"].nunique() != 12 or len(c) != 52:
        ok = False
check("period labels never collide for any anchor", ok)

# Monthly rows the calendar cannot place must refuse, not vanish.
monthly = pd.DataFrame(
    {"period": pd.date_range("2024-10-01", periods=15, freq="MS"), "Calls": [1000.0] * 15}
)
try:
    disaggregate_monthly_to_weekly(monthly, cal, value_cols=["Calls"])
    check("uncovered periods refuse by default", False, "no exception raised")
except UncoveredPeriodError:
    check("uncovered periods refuse by default", True)

# With on_uncovered='drop', the loss must reach KV-C14 as a FAIL.
_, recon = disaggregate_monthly_to_weekly(
    monthly, cal, value_cols=["Calls"], on_uncovered="drop"
)
r = validate.rule_annual_conservation(recon, "Calls")
check(
    "KV-C14 fails when periods were excluded",
    r.status == "FAIL" and r.detail["n_periods_excluded"] == 3,
    f"got {r.status}, excluded={r.detail.get('n_periods_excluded')}",
)

# The clean case must still pass, at the +0.2% the 4.33 divisor implies.
monthly_ok = pd.DataFrame({"period": cal["period"].unique(), "Calls": [1000.0] * 12})
_, recon_ok = disaggregate_monthly_to_weekly(monthly_ok, cal, value_cols=["Calls"])
r = validate.rule_annual_conservation(recon_ok, "Calls")
check("KV-C14 passes on a fully covered year", r.status == "PASS", r.message)

check(
    "week_grid_gaps always reports duplicated_weeks",
    "duplicated_weeks" in week_grid_gaps(pd.Series(pd.to_datetime(["2025-01-05"] * 2))),
)

# --------------------------------------------------------------------------
print("\nvalidation rules")
# --------------------------------------------------------------------------

base = pd.DataFrame({"Week Starting Date": weeks(13), "Ch": ["A"] * 13, "Spend": [100.0] * 13})

# A metric column that does not exist must not silently green the rules.
try:
    validate.run_standard_suite(
        base.rename(columns={"Spend": "spend"}), dataset="d", channel="c",
        metric_cols=["Spend"], dim_cols=["Ch"],
    )
    check("suite refuses an absent metric column", False, "no exception")
except KeyError:
    check("suite refuses an absent metric column", True)

r = validate.rule_zero_runs(base.rename(columns={"Spend": "spend"}), "Week Starting Date", ["Spend"])
check("KV-C11 SKIPs rather than passing with no metric", r.status == "SKIP", r.message)
r = validate.rule_period_step_change(
    base.rename(columns={"Spend": "spend"}), "Week Starting Date", ["Spend"]
)
check("KV-C12 SKIPs rather than passing with no metric", r.status == "SKIP", r.message)

# A flat fiscal quarter must not fabricate a step change from calendar-quarter
# bucketing. Abbott's fiscal Q4 starts in calendar Q3.
flat = pd.DataFrame(
    {"Week Starting Date": weeks(26, "2024-09-29"), "Spend": [100.0] * 26}
)
r = validate.rule_period_step_change(flat, "Week Starting Date", ["Spend"])
check("KV-C12 does not fabricate a step change on flat data", r.status == "PASS", r.message)

# A 60x spike in a short series must not report "no outliers".
short = pd.DataFrame(
    {"Week Starting Date": weeks(8), "Spend": [100.0] * 7 + [6000.0]}
)
r = validate.rule_weekly_outliers(short, "Week Starting Date", ["Spend"], min_active_weeks=8)
check(
    "KV-C10 does not pass over a spike it could not test",
    r.status in ("FAIL", "SKIP"),
    f"{r.status}: {r.message}",
)
tiny = pd.DataFrame({"Week Starting Date": weeks(5), "Spend": [100.0] * 4 + [6000.0]})
r = validate.rule_weekly_outliers(tiny, "Week Starting Date", ["Spend"])
check("KV-C10 SKIPs when no series is long enough", r.status == "SKIP", r.message)

# An undated row carrying volume must fail, not slip past every rule.
undated = pd.concat(
    [base, pd.DataFrame({"Week Starting Date": [pd.NaT], "Ch": ["A"], "Spend": [99999.0]})],
    ignore_index=True,
)
r = validate.rule_week_grid(undated, "Week Starting Date")
check("KV-C01 fails on a row with no week key", r.status == "FAIL", r.message)

# A long-format load repeats each week per dimension row -- that is not a defect.
longfmt = pd.DataFrame(
    {
        "Week Starting Date": list(weeks(13)) * 2,
        "Ch": ["A"] * 13 + ["B"] * 13,
        "Spend": [100.0] * 26,
    }
)
r = validate.rule_week_grid(longfmt, "Week Starting Date")
check("KV-C01 passes a correctly shaped long-format load", r.status == "PASS", r.message)

# KV-C03 must distinguish a file read twice from two sources that disagree.
g = ["Week Starting Date", "Ch"]
full_dup = pd.DataFrame({"Week Starting Date": list(weeks(3)) * 2, "Ch": ["A"] * 6,
                         "Spend": [100.0] * 6})
r = validate.rule_duplicate_grain(full_dup, g)
check("KV-C03 identifies full-row duplicates",
      r.status == "FAIL" and r.detail["full_row_duplicates"] == 3
      and r.detail["key_only_duplicates"] == 0, str(r.detail))
conflict = pd.DataFrame({"Week Starting Date": list(weeks(3)) * 2, "Ch": ["A"] * 6,
                         "Spend": [100.0, 100.0, 100.0, 250.0, 250.0, 250.0]})
r = validate.rule_duplicate_grain(conflict, g)
check("KV-C03 identifies key-only duplicates separately",
      r.status == "FAIL" and r.detail["key_only_duplicates"] == 3
      and r.detail["full_row_duplicates"] == 0, str(r.detail))
r = validate.rule_duplicate_grain(base, g)
check("KV-C03 passes a clean load", r.status == "PASS", r.message)

# A zero TOTAL against non-zero parts is the loudest failure, not a pass.
parts = pd.DataFrame({"period": ["p1", "p2"], "v": [5_000_000.0, 100.0]})
total = pd.DataFrame({"period": ["p1", "p2"], "v": [0.0, 100.0]})
r = validate.rule_parts_vs_total(parts, total, ["period"], "v")
check("KV-C13 fails on a zero TOTAL with non-zero parts", r.status == "FAIL", r.message)

# A period on one side only must fail, not be dropped from the comparison.
r = validate.rule_parts_vs_total(
    pd.DataFrame({"period": ["p1"], "v": [100.0]}),
    pd.DataFrame({"period": ["p1", "p2"], "v": [100.0, 900000.0]}),
    ["period"], "v",
)
check("KV-C13 fails when a period is missing from one side", r.status == "FAIL", r.message)

# Placeholder values whose metrics cancel out are still unattributed spend.
ph = pd.DataFrame({"Ch": ["UNKNOWN", "UNKNOWN"], "Spend": [5000.0, -5000.0]})
r = validate.rule_unclassified_bucket(ph, ["Ch"], ["Spend"])
check("KV-C07 blocks when placeholder metrics net to zero", r.severity == "BLOCK", r.message)

# A ten-week hole at the append seam is a blocker.
hist = pd.DataFrame({"Week Starting Date": weeks(10, "2024-10-13"), "Ch": ["A"] * 10})
new = pd.DataFrame({"Week Starting Date": weeks(4, "2025-03-09"), "Ch": ["A"] * 4})
r = validate.rule_append_seam(hist, new, "Week Starting Date", ["Ch"])
check("KV-C15 blocks on a multi-week seam gap", r.severity == "BLOCK" and r.status == "FAIL", r.message)

# An empty load must be a loud failure, not a traceback.
try:
    rep = validate.run_standard_suite(
        base.iloc[0:0], dataset="d", channel="c", metric_cols=["Spend"], dim_cols=["Ch"]
    )
    check("empty load blocks cleanly", rep.gate == "BLOCKED", rep.gate)
except Exception as exc:  # noqa: BLE001
    check("empty load blocks cleanly", False, f"raised {type(exc).__name__}")

# --------------------------------------------------------------------------
print("\nvalue reconciliation")
# --------------------------------------------------------------------------

v, t, _, _ = reconcile.classify_value("Ensure 1.5", ["Ensure 15"], {})
check("1.5 is not auto-merged into 15", v == "judgment", f"got {v} -> {t}")

v, _, _, _ = reconcile.classify_value("NON BRAND", ["Non Brand", "Non-Brand"], {})
check("ambiguous canonical target is a judgment call", v == "judgment", f"got {v}")

v, t, _, _ = reconcile.classify_value("OLA - AMAZON", ["OLA AMAZON"], {})
check("genuine separator drift is still mechanical", v == "mechanical" and t == "OLA AMAZON", f"{v} -> {t}")

v, t, _, _ = reconcile.classify_value("SnS ", ["SnS"], {})
check("trailing whitespace is still mechanical", v == "mechanical" and t == "SnS", f"{v} -> {t}")

df = pd.DataFrame({"Ch": ["OLA", "OLA", "Online Audio"]})
f = [reconcile.ValueFinding("Ch", "OLA", 2, "judgment"),
     reconcile.ValueFinding("Ch", "Online Audio", 1, "judgment")]
try:
    reconcile.apply_fixes(df, f, confirmed={("Ch", "OLA"): "Online Audio",
                                            ("Ch", "Online Audio"): "OLA"})
    check("chained substitutions refuse", False, "no exception")
except ValueError:
    check("chained substitutions refuse", True)

try:
    reconcile.apply_fixes(df, f, tier="both")
    check("an unknown tier refuses", False, "silently no-op'd")
except ValueError:
    check("an unknown tier refuses", True)

out = reconcile.split_delimited(pd.DataFrame({"c": ["A_B_C_D"]}), "c", ["x", "y", "z"])
check("split_delimited keeps the tail", out.loc[0, "z"] == "C_D", out.loc[0, "z"])

# --------------------------------------------------------------------------
print("\ntemplate fill")
# --------------------------------------------------------------------------

spec = tf.TemplateSpec("t", "T", ["Brand", "Publisher ", "Impressions", "Spend"],
                       required=["Brand"])
frame = pd.DataFrame({"Brand": ["ENS"], "Publisher": ["Amazon"],
                      "Impressions": [1000], "spend": [5.0]})
try:
    tf.fill_template(frame, spec, {"Brand": "Brand", "Publisher": "Publisher",
                                   "Spend": "spend_usd", "Impressions": "Impressions"})
    check("a mis-keyed mapping refuses", False, "silently blanked the column")
except KeyError:
    check("a mis-keyed mapping refuses", True)

res = tf.fill_template(frame, spec, {"Brand": "Brand", "Publisher ": "Publisher",
                                     "Impressions": "Impressions", "Spend": "spend"})
check(
    "a correct mapping fills every column and keeps template order",
    list(res.frame.columns) == spec.columns and not res.manifest["missing_required"],
)

prod = pd.DataFrame({"w": ["a", "a", "b", "b"], "v": [5.0] * 4})
ref = pd.DataFrame({"w": ["a", "b"], "v": [10.0, 10.0]})
rep = tf.compare_to_reference(prod, ref, key_cols=["w"], value_cols=["v"])
check("compare_to_reference rejects a wrong grain", rep["match"] is False, str(rep.get("failures")))

rep = tf.compare_to_reference(prod, ref, key_cols=["nope"], value_cols=["v"])
check("compare_to_reference always sets 'match'", "match" in rep)

# --------------------------------------------------------------------------
print("\nregistry (kvprep.config)")
# --------------------------------------------------------------------------

import json as _json  # noqa: E402
import tempfile  # noqa: E402
from datetime import date as _date  # noqa: E402

from kvprep import config as cfgmod  # noqa: E402
from kvprep import pipeline as pl  # noqa: E402

_MINIMAL = """
schema_version: 2
client: {id: t, name: T}
fiscal_calendar: {pattern: [4, 4, 5], year_start: 2024-09-29, divisor: 4.33}
sources:
  s: {layout: bpm_crosstab, file_pattern: "*.xlsx"}
channels:
  A:
    pipeline: crosstab_series
    template: t.a
    output_columns: [Week Starting Date, Week Ending Date, Dim, V]
    metrics: [V]
    series:
      - dims: {Dim: x}
        from: {source: s, sheet: S, select: {HCP: X}}
"""


def _registry(channels_yaml: str, rules_yaml: str = "") -> Path:
    root = Path(tempfile.mkdtemp()) / "registry"
    (root / "clients" / "t").mkdir(parents=True)
    (root / "clients" / "t" / "channels.yaml").write_text(channels_yaml)
    if rules_yaml:
        (root / "clients" / "t" / "rules.yaml").write_text(rules_yaml)
    return root


def _refuses(name: str, channels_yaml: str, rules_yaml: str = "", needle: str = "") -> None:
    try:
        cfgmod.load_client("t", _registry(channels_yaml, rules_yaml))
        check(name, False, "loaded without complaint")
    except cfgmod.RegistryError as exc:
        check(name, (needle in str(exc)) if needle else True, str(exc)[:120])


cl = cfgmod.load_client("t", _registry(_MINIMAL))
check("a minimal registry loads", cl.channels["A"].metrics == ["V"])

# A typo in a key silently reverts to a default, and the output then differs
# from the maintained file for a reason nobody can see.
_refuses("an unknown channel key refuses",
         _MINIMAL.replace("    metrics: [V]", "    metrics: [V]\n    significant_figure: 10"),
         needle="unknown key")
_refuses("a v1 registry refuses rather than half-loading",
         _MINIMAL.replace("schema_version: 2", "schema_version: 1"),
         needle="schema_version")
_refuses("a metric absent from output_columns refuses",
         _MINIMAL.replace("metrics: [V]", "metrics: [V, W]"),
         needle="not in output_columns")
_refuses("a series naming an unknown source refuses",
         _MINIMAL.replace("{source: s, sheet: S", "{source: nope, sheet: S"),
         needle="not in sources")
_refuses("a series with no sheet refuses",
         _MINIMAL.replace("{source: s, sheet: S, select: {HCP: X}}", "{source: s, select: {HCP: X}}"),
         needle="sheet")
_refuses("two series with the same dims refuse",
         _MINIMAL + "      - dims: {Dim: x}\n        from: {source: s, sheet: S, select: {HCP: Y}}\n",
         needle="duplicates an earlier series")
_refuses("an override on a channel that does not exist refuses",
         _MINIMAL, "defaults: {outlier_z: 5.0}\noverrides:\n  NOPE: {outlier_z: 4.0}\n",
         needle="not in")
_refuses("an override of a threshold that does not exist refuses",
         _MINIMAL, "defaults: {outlier_z: 5.0}\noverrides:\n  A: {outlier_zz: 4.0}\n",
         needle="not thresholds")

# A multi-metric series must say where every metric comes from. An omitted
# metric would be written blank and read as a real zero.
_multi = _MINIMAL.replace(
    "output_columns: [Week Starting Date, Week Ending Date, Dim, V]",
    "output_columns: [Week Starting Date, Week Ending Date, Dim, V, W]",
).replace("metrics: [V]", "metrics: [V, W]").replace(
    "select: {HCP: X}}", "metrics: {V: {select: {HCP: X}}}}")
_refuses("a series missing one metric's source refuses", _multi, needle="no source for metric")

cl = cfgmod.load_client(
    "t", _registry(_MINIMAL, "defaults: {outlier_z: 5.0}\noverrides:\n  A: {outlier_z: 4.0}\n")
)
_refuses("reconcile_output_columns naming a non-template column refuses",
         _MINIMAL.replace("    metrics: [V]",
                          "    metrics: [V]\n    reconcile_output_columns: [Nope]"),
         needle="not in output_columns")

check("an override actually reaches the suite arguments",
      cl.channel("A").suite_kwargs()["thresholds"]["outlier_z"] == 4.0)

# --------------------------------------------------------------------------
print("\nwaivers are binding, and expire")
# --------------------------------------------------------------------------

def _failing_report():
    return validate.ValidationReport(
        dataset="d", channel="A",
        results=[validate.RuleResult("KV-C03", "Grain uniqueness", validate.BLOCK,
                                     "FAIL", "duplicates", {})],
    )


_w = ("defaults: {outlier_z: 5.0}\nwaivers:\n  - rule_id: KV-C03\n    channel: A\n"
      "    reason: r\n    accepted_by: someone\n    expires: 2099-01-01\n")
cl = cfgmod.load_client("t", _registry(_MINIMAL, _w))
rep = _failing_report()
out = cfgmod.apply_waivers(rep, cl.channel("A"))
check("an in-date waiver downgrades the failure", rep.gate == "CLEAR" and len(out["applied"]) == 1,
      rep.gate)

_w_exp = _w.replace("2099-01-01", "2020-01-01")
cl = cfgmod.load_client("t", _registry(_MINIMAL, _w_exp))
rep = _failing_report()
out = cfgmod.apply_waivers(rep, cl.channel("A"))
check("an EXPIRED waiver does not apply and is reported",
      rep.gate == "BLOCKED" and len(out["expired"]) == 1 and not out["applied"], rep.gate)

_w_load = _w.replace("    reason: r", "    load: Q1\n    reason: r")
cl = cfgmod.load_client("t", _registry(_MINIMAL, _w_load))
rep = _failing_report()
cfgmod.apply_waivers(rep, cl.channel("A"), load="Q2")
check("a waiver scoped to another load does not apply", rep.gate == "BLOCKED", rep.gate)

cl = cfgmod.load_client("t", _registry(_MINIMAL, _w))
rep = validate.ValidationReport(
    dataset="d", channel="A",
    results=[validate.RuleResult("KV-C03", "Grain", validate.BLOCK, "PASS", "clean", {})],
)
out = cfgmod.apply_waivers(rep, cl.channel("A"))
check("a waiver with nothing to waive is reported as stale", len(out["unused"]) == 1)

# --------------------------------------------------------------------------
print("\nKV-C14 against the calendar")
# --------------------------------------------------------------------------

_cal = build_445_calendar("2024-09-29", n_years=1)
_wk = _cal.groupby("period")["n_weeks_in_month"].first()
_monthly = pd.DataFrame({"period": _wk.index, "V": [1000.0] * len(_wk)})
_weekly, _recon = disaggregate_monthly_to_weekly(_monthly, _cal, value_cols=["V"], dim_cols=[])

r = validate.rule_annual_conservation(_recon, "V", weeks_by_period=_wk, divisor=4.33)
check("KV-C14 passes the divisor's own arithmetic drift", r.status == "PASS", r.message[:100])

# The same load judged by the flat annual tolerance -- what the rule used to
# do -- and a real defect. One must pass and the other must not.
_skewed = _monthly.copy()
_skewed.loc[_skewed.index % 3 == 2, "V"] = 100.0  # push volume out of the 5-week blocks
_wo, _ro = disaggregate_monthly_to_weekly(_skewed, _cal, value_cols=["V"], dim_cols=[])
r_flat = validate.rule_annual_conservation(_ro, "V", tolerance_pct=0.5)
r_cal = validate.rule_annual_conservation(_ro, "V", weeks_by_period=_wk, divisor=4.33)
check("the flat tolerance fails a correct skewed load (why the calendar mode exists)",
      r_flat.status == "FAIL", r_flat.message[:80])
check("the calendar mode passes that same correct load", r_cal.status == "PASS", r_cal.message[:80])

_broken = _recon.copy()
_broken.loc[_broken.index[0], "V__weekly_out"] *= 0.5
r = validate.rule_annual_conservation(_broken, "V", weeks_by_period=_wk, divisor=4.33)
check("KV-C14 still fails a period that does not equal monthly x weeks/divisor",
      r.status == "FAIL", r.message[:100])

_short = _recon.iloc[:-1].copy()
_short["covered"] = _short["covered"].astype(bool)
_short.loc[_short.index[0], "covered"] = False
r = validate.rule_annual_conservation(_short, "V", weeks_by_period=_wk, divisor=4.33)
check("KV-C14 still fails an excluded period", r.status == "FAIL", r.message[:80])

# --------------------------------------------------------------------------
print("\nrow-wise comparison, ordering and null handling")
# --------------------------------------------------------------------------

_p = pd.DataFrame({"k": ["a", "a", "b"], "v": [1.0, 1.0, 2.0]})
_r = pd.DataFrame({"k": ["a", "b", "a"], "v": [1.0, 2.0, 1.0]})
rep = tf.compare_rowwise(_p, _r, key_cols=["k"], value_cols=["v"])
check("compare_rowwise matches the same bag of rows in a different order", rep["match"] is True)

_r2 = _r.copy()
_r2.loc[0, "v"] = 9.0
rep = tf.compare_rowwise(_p, _r2, key_cols=["k"], value_cols=["v"])
check("compare_rowwise catches one changed value", rep["match"] is False and rep["mismatched"] == 1,
      str(rep.get("mismatched")))

rep = tf.compare_rowwise(_p, _r.iloc[:2], key_cols=["k"], value_cols=["v"])
check("compare_rowwise refuses on different row counts", rep["match"] is False)

# A blank column is "" on one side and NA on the other, and under pandas'
# string dtype astype(str) keeps NA as NA -- so a plain string replace misses
# it and every row of a blank column reads as a difference.
_na = pd.Series(pd.array([None, "x", float("nan")], dtype="object"))
check("as_text turns every flavour of null into an empty string",
      list(tf.as_text(_na)) == ["", "x", ""], list(tf.as_text(_na)))

_blocks = pd.DataFrame({
    "g": ["z", "z", "a", "a"],
    "Week Starting Date": pd.to_datetime(["2025-01-12", "2025-01-05"] * 2),
    "v": [1, 2, 3, 4],
})
ordered = tf.order_blocks(_blocks, ["g"], [("z",), ("a",)])
check("order_blocks emits blocks in the given order, weeks ascending inside",
      list(ordered["g"]) == ["z", "z", "a", "a"]
      and list(ordered["Week Starting Date"].dt.day) == [5, 12, 5, 12])
try:
    tf.order_blocks(_blocks, ["g"], [("z",)])
    check("order_blocks refuses a block the order does not name", False, "appended silently")
except KeyError:
    check("order_blocks refuses a block the order does not name", True)

check("format_significant reproduces the maintained files' 10 sig figs",
      tf.format_significant(49571.547340000004, 10) == "49571.54734"
      and tf.format_significant(652.8868360000001, 10) == "652.886836",
      tf.format_significant(49571.547340000004, 10))

# --------------------------------------------------------------------------
print("\npipeline guards")
# --------------------------------------------------------------------------

cl = cfgmod.load_client("t", _registry(_MINIMAL))
try:
    pl.assign_sources(cl, ["nothing-matches-this.csv"])
    check("a raw file matching no source refuses", False, "accepted it")
except pl.PipelineError:
    check("a raw file matching no source refuses", True)
try:
    pl.assign_sources(cl, ["a.xlsx", "b.xlsx"])
    check("two files matching one source refuse", False, "picked one")
except pl.PipelineError:
    check("two files matching one source refuse", True)

_f = pd.DataFrame({"d": pd.to_datetime(["2025-01-11"])})
check("a derived expression from the vocabulary works",
      str(pl._derive("minus_days(d, 6)", _f, "w").iloc[0].date()) == "2025-01-05")
for expr in ("__import__('os').system('true')", "eval(d)", "minus_days(nope, 6)"):
    try:
        pl._derive(expr, _f, "w")
        check(f"derived {expr!r} refuses", False, "it ran")
    except pl.PipelineError:
        check(f"derived {expr!r} refuses", True)

_res = pl.LoadResult(client="t", channel="A", frame=pd.DataFrame({"a": [1]}),
                     numeric=pd.DataFrame({"a": [1]}), status="unverified")
check("an unverified channel can never report a loadable gate",
      _res.gate.startswith("BLOCKED"), _res.gate)
_res = pl.LoadResult(client="t", channel="A", frame=pd.DataFrame({"a": [1]}),
                     numeric=pd.DataFrame({"a": [1]}),
                     report=validate.ValidationReport("d", "A", []),
                     comparison={"match": False})
check("a load that fails its reference diff is BLOCKED however clean the rules",
      _res.gate.startswith("BLOCKED"), _res.gate)
check("...and the gate says which of the two things blocked it",
      "MAINTAINED FILE" in _res.gate, _res.gate)

# --------------------------------------------------------------------------
print("\nthe client review")
# --------------------------------------------------------------------------

from kvprep import review as rvw  # noqa: E402

_REG = Path(__file__).resolve().parents[1] / "registry"
_cat = rvw.load_catalogue(_REG)

# Every rule the suite can emit must have an entry. A finding the catalogue
# does not know about falls back to the rule's own wording, which is the exact
# thing this whole layer exists to stop reaching a client document.
_emitted = set()
for _line in (Path(__file__).resolve().parents[1] / "lib/kvprep/validate.py").read_text().split("\n"):
    for _m in re.findall(r'"(KV-C\d+)"', _line):
        _emitted.add(_m)
_missing = sorted(_emitted - set(_cat.get("checks", {})))
check("every rule the suite emits is in the check catalogue", not _missing, str(_missing))

for _rid, _entry in _cat.get("checks", {}).items():
    _has = all(_entry.get(k) for k in ("group", "title", "looks_for", "why_it_matters", "ask"))
    check(f"{_rid} says what it checks, why it matters and what is needed", _has)
    check(f"{_rid} belongs to a declared group", _entry.get("group") in _cat.get("groups", {}),
          str(_entry.get("group")))

# A client document must never carry a rule ID or an internal threshold name.
_jargon = ("robust_z", "KV-C", "pct_threshold", "n_flagged", "MAD")
_bad = []
for _rid, _e2 in _cat.get("checks", {}).items():
    _prose = " ".join(str(_e2.get(k, "")) for k in ("title", "looks_for", "why_it_matters", "ask"))
    for _j in _jargon:
        if _j in _prose:
            _bad.append((_rid, _j))
check("no rule IDs or internal field names in the client-facing prose", not _bad, str(_bad))

# The z-score is translated, not printed.
check("a robust z-score is rendered in words",
      rvw._fmt_zscore(-5.7) == "5.7x normal variation, below typical", rvw._fmt_zscore(-5.7))
check("an internal period key is rendered as a date",
      rvw._fmt_period("P2 (2024-12-29)") == "Quarter beginning 29 Dec 2024")

# Consecutive weeks carrying the same value collapse into one row: a monthly
# figure spread over a block must not arrive as five identical findings.
_recs = [{"group": {"a": "x"}, "metric": "Call", "week": w, "value": 10.0}
         for w in ("2025-01-04", "2025-01-11", "2025-01-18")]
_recs.append({"group": {"a": "x"}, "metric": "Call", "week": "2025-03-01", "value": 10.0})
_col = rvw._collapse_week_runs(_recs)
check("consecutive identical weeks collapse into one row",
      len(_col) == 2 and _col[0].get("n_weeks") == 3, str(_col))
check("a non-consecutive week is not folded in", _col[1].get("n_weeks") is None)

# Fiscal labelling must agree with the registry's own calendar.
_w = pd.date_range("2024-09-29", periods=52, freq="7D")
_p = rvw.fiscal_periods(_w, "2024-09-29")
check("the fiscal year splits into four quarters", list(dict.fromkeys(_p)) ==
      ["Q1 FY25", "Q2 FY25", "Q3 FY25", "Q4 FY25"], str(list(dict.fromkeys(_p))))

# Labels drop the parts every series shares.
_cols = [rvw.SeriesColumn(key=("Ensure", "PC"), label="Ensure · PC", unit="u"),
         rvw.SeriesColumn(key=("Ensure", "ONC"), label="Ensure · ONC", unit="u")]
rvw._shorten_labels(_cols)
check("a dimension constant across every series is dropped from the label",
      [c.label for c in _cols] == ["PC", "ONC"], str([c.label for c in _cols]))

_cols2 = [rvw.SeriesColumn(key=("Ensure",), label="Ensure", unit="u")]
rvw._shorten_labels(_cols2)
check("the last distinguishing part is never dropped", _cols2[0].label == "Ensure")

# --------------------------------------------------------------------------
print("\ncoupon redemption lag")
# --------------------------------------------------------------------------

from kvprep import lag as lagmod  # noqa: E402

_months = pd.date_range("2024-01-01", periods=24, freq="MS")
_prof = lagmod.LagProfile("t", (0.5, 0.3, 0.2))

# The arithmetic itself: one unit dropped in month 0 and nothing after must
# come back out as the profile, month by month.
_impulse = pd.Series([0.0] * 24, index=_months)
_impulse.iloc[6] = 100.0
_r = lagmod.apply_lag(_impulse, _prof)
check("a single drop is spread over the profile",
      [round(v, 6) for v in _r.iloc[6:9]] == [50.0, 30.0, 20.0], str(list(_r.iloc[6:9])))
check("nothing is redeemed before the drop", _r.iloc[:6].sum() == 0)
check("a full profile conserves the drop total",
      abs(_r.sum() - 100.0) < 1e-9, str(_r.sum()))

# The multiplier converts shipments into coupons before the lag, not after.
_r2 = lagmod.apply_lag(_impulse, _prof, multiplier=10.0)
check("the multiplier scales the result", abs(_r2.sum() - 1000.0) < 1e-9)

# The 2026 cutover: from the month after `multiplier_until` the source is
# already a coupon count, so the multiplier must stop applying.
_two = pd.Series([0.0] * 24, index=_months)
_two.iloc[3] = 1.0      # before the cutover -> multiplied
_two.iloc[20] = 1.0     # after  the cutover -> not
_r3 = lagmod.apply_lag(_two, _prof, multiplier=10.0, multiplier_until="2025-06-01")
check("the multiplier stops at the cutover month",
      abs(_r3.sum() - 11.0) < 1e-9, str(_r3.sum()))

# Warm-up: a window that starts where the data starts is understated, and the
# check has to say by how much rather than reporting a clean number.
_short = pd.Series([100.0] * 24, index=_months)
_w = lagmod.warmup_shortfall(_short, _prof, "2024-01-01")
check("no history before the window is reported as a shortfall",
      _w["first_month_understated_pct"] > 0, str(_w))
_w2 = lagmod.warmup_shortfall(_short, _prof, "2025-06-01")
check("ample history before the window reports no shortfall",
      _w2["first_month_understated_pct"] == 0, str(_w2))
check("KV-C16 fails on a short warm-up",
      validate.rule_lag_warmup([{**_w, "dims": {}}]).status == "FAIL")
check("KV-C16 passes on an ample warm-up",
      validate.rule_lag_warmup([{**_w2, "dims": {}}]).status == "PASS")
check("KV-C16 SKIPs rather than passing when nothing is lagged",
      validate.rule_lag_warmup([]).status == "SKIP")

# A profile file that would multiply every figure by a hundred must refuse.
import tempfile as _tf  # noqa: E402
def _prof_file(body: str) -> Path:
    d = Path(_tf.mkdtemp()) / "lag-factors.yaml"
    d.write_text(body)
    return d

for _body, _why in [
    ("profiles:\n  p:\n    months: [50, 30, 20]\n", "percentages rather than fractions"),
    ("profiles:\n  p:\n    months: [0.5, -0.2]\n", "a negative share"),
    ("profiles:\n  p:\n    status: guessed\n    months: [1.0]\n", "an unknown status"),
]:
    try:
        lagmod.load_profiles(_prof_file(_body))
        check(f"a profile with {_why} refuses", False, "it loaded")
    except lagmod.LagError:
        check(f"a profile with {_why} refuses", True)

_ok = lagmod.load_profiles(_prof_file(
    "profiles:\n  p:\n    status: recovered\n    heldout_error_pct: 1.2\n"
    "    months: [0.5, 0.3, 0.2]\n"))
check("a recovered profile loads and is not treated as confirmed",
      _ok["p"].status == "recovered" and not _ok["p"].is_confirmed)
check("a recovered profile says so when described",
      "RECOVERED" in _ok["p"].describe(), _ok["p"].describe())

# The registry must refuse a series pointing at a profile that is not there,
# rather than silently running it unlagged.
_refuses("a series naming an unknown redemption profile refuses",
         _MINIMAL.replace("        from: {source: s, sheet: S, select: {HCP: X}}",
                          "        from: {source: s, sheet: S, select: {HCP: X}}\n"
                          "        transform: {profile: nope}"),
         needle="not in lag-factors")
_refuses("a transform with no profile refuses",
         _MINIMAL.replace("        from: {source: s, sheet: S, select: {HCP: X}}",
                          "        from: {source: s, sheet: S, select: {HCP: X}}\n"
                          "        transform: {multiplier: 2}"),
         needle="profile")

# --------------------------------------------------------------------------
print("\nskill manifests")
# --------------------------------------------------------------------------

# Both of these have now bitten once. A ": " inside an unquoted YAML scalar
# makes the whole frontmatter unparseable, and the skill then loads with no
# name and no description at all -- which looks like nothing being wrong. The
# 500-character limit is enforced by the marketplace uploader, so failing it
# here is cheaper than failing it at publish time.
import yaml as _yaml  # noqa: E402

_ROOT = Path(__file__).resolve().parents[1]
for _sk in sorted(_ROOT.glob("skills/*/SKILL.md")):
    _fm_m = re.match(r"^---\n(.*?)\n---", _sk.read_text(encoding="utf-8"), re.S)
    _name = _sk.parent.name
    if not _fm_m:
        check(f"{_name}: has YAML frontmatter", False)
        continue
    try:
        _fm = _yaml.safe_load(_fm_m.group(1))
    except Exception as _exc:
        check(f"{_name}: frontmatter parses as YAML", False, str(_exc).splitlines()[0])
        continue
    check(f"{_name}: frontmatter parses as YAML", True)
    check(f"{_name}: declares an explicit name", _fm.get("name") == _name, str(_fm.get("name")))
    _d = _fm.get("description") or ""
    check(f"{_name}: description is under 500 characters", 0 < len(_d) <= 500, str(len(_d)))

_pj = _json.loads((_ROOT / ".claude-plugin/plugin.json").read_text())
check("plugin name is kebab-case and at most 64 characters",
      bool(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", _pj["name"])) and len(_pj["name"]) <= 64)
check("plugin description is under 500 characters", len(_pj.get("description", "")) <= 500,
      str(len(_pj.get("description", ""))))
check("no top-level bin/ directory (rejected for org distribution)",
      not (_ROOT / "bin").exists())

# --------------------------------------------------------------------------
print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED: {FAILURES}")
    sys.exit(1)
print("all regression checks passed")
