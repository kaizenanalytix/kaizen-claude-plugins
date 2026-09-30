#!/usr/bin/env python3
"""Does the EDA find what is there, and stay quiet about what is not?

A detector suite has two ways to fail and only one of them is obvious. Missing
a real defect is the one everybody tests for. Reporting a defect that is not
there is the one that kills the product: a review with forty findings in it,
half of them noise, gets skimmed, and the two that mattered get skimmed with
the rest. The client's feedback was exactly this -- "if it takes significant
interpretation to understand the AI output, it reduces the value".

So every detector here is tested twice: once on a series built to contain the
thing, and once on a clean series that must produce nothing at all.

    python3 tests/test_eda_and_summary.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402
from kvprep import eda, summary as sm  # noqa: E402

REGISTRY = Path(__file__).resolve().parents[1] / "registry"
FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"  {'PASS' if condition else 'FAIL'}  {name}" + (f" -- {detail}" if detail else ""))
    if not condition:
        FAILURES.append(name)


def months(n: int, start="2022-01-01") -> pd.DatetimeIndex:
    return pd.date_range(start, periods=n, freq="MS")


def quarters(idx) -> pd.Series:
    return pd.Series([f"Q{((t.month-1)//3)+1} {t.year}" for t in idx], index=idx)


def clean(n=48, level=1000.0, seed=3) -> pd.Series:
    rng = np.random.default_rng(seed)
    return pd.Series(level + rng.normal(0, level * 0.04, n), index=months(n))


def S(values, label="A", unit="Impressions", channel="X", grain="monthly"):
    return eda.Series(channel=channel, label=label, unit=unit, values=values, grain=grain)


def kinds(series_list, **kw) -> list[str]:
    idx = series_list[0].values.index
    r = eda.run_channel(series_list, quarters(idx), channel="X", label="X", **kw)
    return [o.kind for o in r.observations]


# --------------------------------------------------------------------------


def test_quiet_on_clean_data() -> None:
    print("\nA clean series produces no findings at all")
    # The single most important test here. Everything else is a trade against
    # this one: a detector that fires on well-behaved data costs more than it
    # is worth however many real defects it also finds.
    for seed in range(6):
        got = kinds([S(clean(seed=seed))])
        check(f"clean series, seed {seed}: silent", got == [], str(got))
    # Several clean series together must not produce a divergence or a
    # correlation finding either.
    group = [S(clean(seed=i), label=f"S{i}") for i in range(5)]
    got = kinds(group)
    check("five clean series: no divergence", "divergence" not in got, str(got))


def test_finds_what_is_there() -> None:
    print("\nEach detector finds its own defect")
    idx = months(48)

    stopped = clean(); stopped.iloc[-8:] = 0
    check("a series that stops is reported", "stopped" in kinds([S(stopped)]))

    started = clean(); started.iloc[:40] = 0
    check("a series that starts is reported", "started" in kinds([S(started)]))

    spike = clean(); spike.iloc[20] = 9000
    check("a one-off spike is reported", "outlier" in kinds([S(spike)]))

    # A run of high but *varying* periods. Setting them all to one number
    # would be a flat run, which is a different finding and correctly reported
    # as one -- the thing under test here is that ten raised periods produce
    # one level-shift finding rather than ten outliers.
    shift = clean()
    shift.iloc[24:34] = shift.iloc[24:34].to_numpy() * 4.0
    got = kinds([S(shift)])
    check("a sustained level change is reported as a level shift, not spikes",
          "level_shift" in got and got.count("outlier") == 0, str(got))

    flat = clean(); flat.iloc[10:22] = 1234.0
    check("a carried-forward constant is reported", "flat_run" in kinds([S(flat)]))

    unit = clean(); unit.iloc[24:] *= 10
    check("an order-of-magnitude unit change is reported",
          "magnitude_shift" in kinds([S(unit)]))

    step = clean(); step.iloc[-3:] *= 3
    check("a big quarter-on-quarter move is reported", "qoq_step" in kinds([S(step)]))

    seasonal = clean(n=48)
    seasonal[seasonal.index.month == 12] *= 2.4
    check("a repeating annual peak is reported", "seasonality" in kinds([S(seasonal)]))


def test_seasonality_is_not_reported_as_outliers() -> None:
    print("\nA reliable season is a pattern, not four anomalies")
    s = clean(n=48)
    s[s.index.month == 5] *= 2.3
    got = kinds([S(s)])
    check("a seasonal peak is reported once as seasonality", got.count("seasonality") == 1, str(got))
    check("...and not once per year as an outlier", got.count("outlier") == 0, str(got))

    # ... but a genuine spike inside a seasonal series must still be found,
    # which is the case a naive deseasonalise-then-test gets wrong.
    s2 = s.copy()
    s2.iloc[30] = 9000
    got2 = kinds([S(s2)])
    check("a real spike inside a seasonal series is still found",
          "outlier" in got2, str(got2))


def test_one_event_is_one_finding() -> None:
    print("\nOne event is reported once")
    idx = months(48)
    shipments = clean()
    shipments.iloc[-8:] = 0
    bottles = shipments * 24  # derived, so it moves identically
    r = eda.run_channel(
        [S(shipments, label="BAR", unit="Shipments"), S(bottles, label="BAR", unit="Bottles")],
        quarters(idx), channel="X", label="X",
    )
    stops = [o for o in r.observations if o.kind == "stopped"]
    check("a stop in two measures of one series is one finding", len(stops) == 1,
          f"{len(stops)} findings")
    check("...and the finding names both measures",
          bool(stops) and "Shipments" in stops[0].observation and "Bottles" in stops[0].observation)

    # Measures that move by genuinely different amounts are NOT merged: that
    # divergence is itself the finding.
    a = clean(); a.iloc[-8:] = 0
    b = clean(seed=9)  # unrelated, keeps running
    r2 = eda.run_channel(
        [S(a, label="C", unit="Shipments"), S(b, label="C", unit="Bottles")],
        quarters(idx), channel="X", label="X",
    )
    check("one measure stopping while the other runs stays one finding about one measure",
          len([o for o in r2.observations if o.kind == "stopped"]) == 1)


def test_channel_wide_facts_roll_up() -> None:
    print("\nA fact true of every series is stated once")
    idx = months(48)
    group = []
    for i in range(10):
        v = clean(seed=i)
        v.iloc[-8:] = 0  # the whole channel stops reporting
        group.append(S(v, label=f"S{i}"))
    r = eda.run_channel(group, quarters(idx), channel="X", label="Direct Mail")
    stops = [o for o in r.observations if o.kind == "stopped"]
    check("ten series stopping together is one finding", len(stops) == 1, f"{len(stops)}")
    check("...and it says how many series it covers",
          bool(stops) and "10 of the 10" in stops[0].observation,
          stops[0].observation[:80] if stops else "")

    # Two of ten stopping is the interesting case and must NOT be rolled up,
    # because a rollup would describe it as a fact about the channel.
    group2 = []
    for i in range(10):
        v = clean(seed=i + 20)
        if i < 2:
            v.iloc[-8:] = 0
        group2.append(S(v, label=f"T{i}"))
    r2 = eda.run_channel(group2, quarters(idx), channel="X", label="Direct Mail")
    stops2 = [o for o in r2.observations if o.kind == "stopped"]
    check("two of ten stopping stays two per-series findings", len(stops2) == 2, f"{len(stops2)}")


def test_renames() -> None:
    print("\nA series ending as another begins is a rename, not a stop and a start")
    idx = months(48)
    old = clean(); old.iloc[24:] = 0
    new = clean(seed=4); new.iloc[:24] = 0
    r = eda.run_channel(
        [S(old, label="Amazon OLA"), S(new, label="OLA AMAZON"), S(clean(seed=5), label="Steady")],
        quarters(idx), channel="X", label="OLA",
    )
    got = [o.kind for o in r.observations]
    check("the pair is reported as a rename", "rename" in got, str(got))
    check("...and not also as a stop", "stopped" not in got, str(got))
    check("...and not also as a start", "started" not in got, str(got))

    # A stop with no replacement must still be a stop.
    r2 = eda.run_channel(
        [S(old, label="Amazon OLA"), S(clean(seed=5), label="Steady"),
         S(clean(seed=6), label="Other"), S(clean(seed=7), label="More")],
        quarters(idx), channel="X", label="OLA",
    )
    check("a stop with nothing replacing it is still a stop",
          "stopped" in [o.kind for o in r2.observations])


def test_restatement() -> None:
    print("\nA figure that has changed since the last summary is reported")
    idx = months(48)
    ours = clean()
    theirs = ours.copy()
    theirs.iloc[5:9] *= 1.4
    r = eda.run_channel(
        [S(ours, label="A")], quarters(idx), channel="X", label="X",
        prior={"A (Impressions)": theirs},
    )
    got = [o.kind for o in r.observations]
    check("a restatement is reported", "restated" in got, str(got))
    r2 = eda.run_channel(
        [S(ours, label="A")], quarters(idx), channel="X", label="X",
        prior={"A (Impressions)": ours.copy()},
    )
    check("an unchanged series is not reported as restated",
          "restated" not in [o.kind for o in r2.observations])


def test_outlier_needs_size_as_well_as_score() -> None:
    print("\nAn outlier has to be big, not merely unusual")
    # A very steady series has a tiny MAD, so a 10% wobble clears any z
    # threshold. Reporting it tells the client their data is 0.9x its usual,
    # which is the kind of output that makes a report get ignored.
    rng = np.random.default_rng(11)
    steady = pd.Series(1000 + rng.normal(0, 1.0, 48), index=months(48))
    steady.iloc[20] = 1100  # 10% high: statistically wild, practically nothing
    got = kinds([S(steady)])
    check("a 10% wobble on a very steady series is not an outlier",
          "outlier" not in got, str(got))
    steady.iloc[21] = 3000
    check("a 3x value on the same series is an outlier", "outlier" in kinds([S(steady)]))


def test_rates_catch_unit_changes() -> None:
    print("\nA derived rate catches what the raw series hides")
    idx = months(48)
    impressions = clean(level=1_000_000)
    spend = impressions / 1000 * 3.0  # CPM of exactly 3
    spend.iloc[36:] *= 12  # the spend column changes meaning
    r = eda.run_channel(
        [S(impressions, label="P", unit="Impressions"), S(spend, label="P", unit="Spend")],
        quarters(idx), channel="X", label="X",
        rates=[{"name": "CPM", "numerator": "Spend", "denominator": "Impressions", "scale": 1000}],
    )
    check("a CPM that jumps is reported", "rate_shift" in [o.kind for o in r.observations])
    check("the rate table is produced", not r.rates.empty)


def test_capping_is_honest() -> None:
    print("\nCapping ranks and counts; it never silently drops")
    obs = [
        eda.Observation(kind="outlier", channel="X", series=f"s{i}", observation="x",
                        group="Outliers", evidence={"value": float(i)})
        for i in range(30)
    ]
    kept, dropped = eda.rank_and_cap(obs, 8)
    check("the cap is applied", len(kept) == 8, str(len(kept)))
    check("the number dropped is reported", dropped.get("Outliers") == 22, str(dropped))
    check("the biggest are the ones kept",
          {int(float(o.evidence["value"])) for o in kept} == set(range(22, 30)))
    ren = eda.Observation(kind="rename", channel="X", series="r", observation="x",
                          group="Outliers", evidence={})
    kept2, _ = eda.rank_and_cap(obs + [ren], 8)
    check("a rename is never the thing that gets cut",
          any(o.kind == "rename" for o in kept2))


def test_summary_spec_refuses_nonsense() -> None:
    print("\nThe summary spec refuses what it does not understand")
    tmp = Path(tempfile.mkdtemp())

    def write(doc) -> Path:
        p = tmp / "summary.yaml"
        p.write_text(yaml.safe_dump(doc), encoding="utf-8")
        return p

    base = {"schema_version": 1, "title": "t",
            "sheets": [{"sheet": "A", "channels": ["C"], "grain": "monthly"}]}
    check("a valid spec loads", bool(sm.load_spec(write(base)).sheets))

    for name, doc in [
        ("an unknown top-level key", {**base, "sheeets": []}),
        ("an unknown sheet key", {**base, "sheets": [{"sheet": "A", "grian": "monthly"}]}),
        ("a sheet with no name", {**base, "sheets": [{"channels": ["C"]}]}),
        ("an unknown grain", {**base, "sheets": [{"sheet": "A", "grain": "daily"}]}),
        ("two sheets with one name",
         {**base, "sheets": [{"sheet": "A"}, {"sheet": "A"}]}),
        ("a rate with no denominator",
         {**base, "sheets": [{"sheet": "A", "rates": [{"name": "CPM", "numerator": "Spend"}]}]}),
    ]:
        try:
            sm.load_spec(write(doc))
            check(f"{name} is refused", False, "it was accepted")
        except sm.SummaryError:
            check(f"{name} is refused", True)


def test_real_spec_is_valid() -> None:
    print("\nThe shipped spec parses and matches the registry")
    from kvprep import config as cfg

    p = sm.spec_path(REGISTRY, "abbott-ensure")
    check("summary.yaml exists", p.exists(), str(p))
    if not p.exists():
        return
    spec = sm.load_spec(p)
    cl = cfg.load_client("abbott-ensure", registry_root=REGISTRY)
    named = {c for s in spec.sheets for c in s.channels}
    known = set(cl.channels)
    check("every channel a sheet claims exists in channels.yaml",
          named <= known, str(sorted(named - known)))
    check("every registry channel has a sheet to live on",
          known <= named, str(sorted(known - named)))
    # A monthly sheet needs a channel that can produce raw monthly figures.
    for s in spec.sheets:
        if s.grain != "monthly":
            continue
        for ch in s.channels:
            check(f"{ch} can supply raw monthly figures for {s.sheet!r}",
                  cl.channel(ch).pipeline == "crosstab_series",
                  cl.channel(ch).pipeline)


def test_prior_reader_handles_their_quirks() -> None:
    print("\nThe previous-summary reader survives the real file's quirks")
    import openpyxl

    tmp = Path(tempfile.mkdtemp()) / "prior.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Direct Mail"
    ws["C2"], ws["C3"], ws["C5"] = "File Name", "Unit", "Channel"
    ws["D2"], ws["D3"], ws["D5"] = "src.xlsx", "Shipments", "DMwS - PCP"
    for i in range(36):
        r = 6 + i
        t = pd.Timestamp("2022-01-01") + pd.DateOffset(months=i)
        ws.cell(r, 2, str(t.year))  # a YEAR STORED AS TEXT, as their file does
        ws.cell(r, 3, t.strftime("%b"))
        ws.cell(r, 4, 100 + i)
    wb.save(tmp)

    prior = sm.read_prior(tmp)
    check("a sheet whose Year column is text is still read", "Direct Mail" in prior.sheets,
          str(sorted(prior.sheets)))
    if "Direct Mail" in prior.sheets:
        s = prior.sheets["Direct Mail"]
        check("...with its full index", len(s.index) == 36, str(len(s.index)))
        check("...and its column", len(s.columns) == 1, str(len(s.columns)))


def test_prior_matching_is_on_the_numbers() -> None:
    print("\nSeries are matched to the previous summary by their values, not their names")
    idx = months(48)
    v = clean()
    cols = [sm.SheetColumn(label="ENS DMwS HR - ONC", unit="Shipments", values=v)]
    ps = sm.PriorSheet(
        name="Direct Mail", grain="monthly", index=idx,
        # Their heading for the same series, which shares no words with ours.
        columns={("Shipments", "DMwS - ONC Hand Raisers"): v.copy()},
        files={}, notes=[], header_row=5, data_row=6,
    )
    got = sm.match_prior(cols, ps)
    check("a differently-named identical series is matched", len(got) == 1, str(list(got)))

    # An unrelated series must not be matched to anything.
    ps2 = sm.PriorSheet(
        name="Direct Mail", grain="monthly", index=idx,
        columns={("Shipments", "Something Else"): clean(level=77, seed=12)},
        files={}, notes=[], header_row=5, data_row=6,
    )
    check("an unrelated series is not matched", sm.match_prior(cols, ps2) == {})


def test_generic_reader_is_loud_about_guessing() -> None:
    print("\nThe generic reader says what it guessed")
    from kvprep import generic

    tmp = Path(tempfile.mkdtemp())
    p = tmp / "unknown_channel.csv"
    idx = months(40)
    pd.DataFrame(
        {"Week": idx, "Partner": ["A", "B"] * 20, "Impressions": range(40), "Spend": range(40)}
    ).to_csv(p, index=False)
    sheets = generic.read_any(p)
    check("a file with a date column and numbers is read", len(sheets) == 1)
    if sheets:
        sh = sheets[0]
        check("the sheet is marked inferred", sh.origin == sm.INFERRED, sh.origin)
        check("it states that the layout was guessed",
              bool(sh.notes) and "guessed" in sh.notes[0].lower(), sh.notes[0][:70] if sh.notes else "")

    bad = tmp / "no_axis.csv"
    pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}).to_csv(bad, index=False)
    try:
        generic.read_any(bad)
        check("a file with no time axis is refused", False, "it was accepted")
    except generic.InferenceError as exc:
        check("a file with no time axis is refused", True)
        check("...with a reason that says why", "time" in str(exc).lower())


def test_observations_never_expose_internals() -> None:
    print("\nAn EDA observation reads as a sentence, not as a log line")
    # The document as a whole does carry rule IDs -- deliberately, so a finding
    # can be looked up and argued with. What must never carry them is the
    # observation text itself: those are the sentences that get read aloud in
    # the review meeting and pasted into an email to the client.
    idx = months(48)
    series = []
    for i in range(6):
        v = clean(seed=i)
        if i == 0:
            v.iloc[20] = 9000
        if i == 1:
            v.iloc[-8:] = 0
        series.append(S(v, label=f"S{i}"))
    r = eda.run_channel(series, quarters(idx), channel="X", label="X")
    banned = ["KV-C", "robust_z", "z-score", "qoq_pct", "threshold", "NaN", "dtype", "None"]
    bad = [
        (o.kind, w)
        for o in r.observations
        for w in banned
        if w.lower() in (o.observation + " " + o.question).lower()
    ]
    check("no observation leaks an internal name", not bad, str(bad[:4]))
    check("every finding that asks something has a question",
          all(o.question for o in r.observations if o.severity == "ASK"))
    check("every finding names its group",
          all(o.group for o in r.observations))


def test_one_document_carries_both_engines() -> None:
    """The load rules and the EDA end up in one model, grouped together."""
    print("\nThe rules and the EDA land in one document")
    import inspect

    from kvprep import summary_html

    src = inspect.getsource(summary_html)
    check("the renderer takes no audience argument", "audience" not in src)
    check("the summary model carries rule findings",
          "findings" in sm.SummarySheet.__dataclass_fields__)
    check("the summary model carries a gate", "gate" in sm.InputSummary.__dataclass_fields__)
    check("rule asks and data asks are both exposed",
          hasattr(sm.InputSummary, "rule_asks") and hasattr(sm.InputSummary, "asks"))
    # Every EDA group has somewhere to live among the catalogue's groups, or a
    # finding silently lands in the wrong section of the document.
    import yaml as _yaml

    cat = _yaml.safe_load((REGISTRY / "checks" / "catalogue.yaml").read_text())
    known = set(cat.get("groups") or {})
    missing = {v for v in sm.EDA_GROUP_KEY.values()} - known
    check("every EDA group maps to a catalogue group", not missing, str(missing))
    used = {o.group for o in [
        eda.Observation(kind="x", channel="c", series="s", observation="o", group=g)
        for g in ["Coverage", "Consistency", "Movement", "Outliers", "Seasonality",
                  "Reconciliation"]
    ]}
    check("every group the detectors emit is mapped",
          used <= set(sm.EDA_GROUP_KEY), str(used - set(sm.EDA_GROUP_KEY)))


def test_supplied_lag_table_verifies_the_channel() -> None:
    """The client supplies their own redemption table and the gate follows.

    This is the path Kvantum tests on, so it is the path that must not need
    anybody to edit the plugin. Three things have to hold: their file is used
    instead of ours, the channel stops being gated when every profile it uses
    is marked supplied, and it stays gated when any of them is not.
    """
    print("\nA supplied redemption table verifies the channel on its own")
    from kvprep import config as cfg

    tmp = Path(tempfile.mkdtemp())

    def table(status_a: str, status_b: str) -> Path:
        p = tmp / f"lag-{status_a}-{status_b}.yaml"
        months = [round(x, 6) for x in [0.05] * 12]
        p.write_text(
            yaml.safe_dump(
                {
                    "version": 1,
                    "profiles": {
                        "hcp_fsf": {"status": status_a, "months": months},
                        "direct_mail_samples": {"status": status_b, "months": months},
                    },
                }
            ),
            encoding="utf-8",
        )
        return p

    shipped = cfg.load_client("abbott-ensure", registry_root=REGISTRY)
    check("as shipped, Coupon Drops is gated",
          shipped.channel("COUPON_DROPS").status == "unverified",
          shipped.channel("COUPON_DROPS").status)
    check("...and says why, naming the profiles",
          "inferred" in shipped.channel("COUPON_DROPS").status_detail
          and "hcp_fsf" in shipped.channel("COUPON_DROPS").status_detail,
          shipped.channel("COUPON_DROPS").status_detail[:90])

    both = cfg.load_client(
        "abbott-ensure", registry_root=REGISTRY, lag_factors=table("supplied", "supplied")
    )
    ch = both.channel("COUPON_DROPS")
    check("with both profiles supplied, the channel verifies itself",
          ch.status == "verified", ch.status)
    check("...and the numbers used are theirs, not ours",
          both.lag_profiles["hcp_fsf"].months[0] == 0.05,
          str(both.lag_profiles["hcp_fsf"].months[:2]))
    check("...and it records why it verified",
          "supplied" in ch.status_detail, ch.status_detail[:80])

    # Half a table is not a table: two of three supplied leaves it gated.
    half = cfg.load_client(
        "abbott-ensure", registry_root=REGISTRY, lag_factors=table("supplied", "recovered")
    )
    check("one profile still inferred keeps the channel gated",
          half.channel("COUPON_DROPS").status == "unverified",
          half.channel("COUPON_DROPS").status)

    # A path that does not exist must fail loudly rather than falling back to
    # ours -- running on our inferred profiles while the operator believes
    # they supplied their own is the worst available outcome.
    try:
        cfg.load_client("abbott-ensure", registry_root=REGISTRY,
                        lag_factors=tmp / "does-not-exist.yaml")
        check("a missing lag file is refused", False, "it fell back silently")
    except cfg.RegistryError as exc:
        check("a missing lag file is refused", True)
        check("...rather than falling back to ours", "fallback" in str(exc).lower()
              or "refusing" in str(exc).lower() or "silently" in str(exc).lower())

    # And the shipped example must itself be valid, or the thing we tell them
    # to copy does not run.
    ex = REGISTRY / "clients" / "abbott-ensure" / "lag-factors.EXAMPLE.yaml"
    check("the example table ships", ex.exists(), str(ex))
    if ex.exists():
        c = cfg.load_client("abbott-ensure", registry_root=REGISTRY, lag_factors=ex)
        check("the example table loads and verifies the channel",
              c.channel("COUPON_DROPS").status == "verified")

    # An unverified_until nobody can evaluate is an error, not a permanent gate.
    try:
        cfg._resolve_conditional_status(
            {"X": cfg.ChannelConfig(client="c", name="X", pipeline="crosstab_series",
                                    template="t", status="unverified",
                                    unverified_until="something_nobody_checks")},
            {}, Path("lag.yaml"),
        )
        check("an uncheckable condition is refused", False, "it was accepted")
    except cfg.RegistryError:
        check("an uncheckable condition is refused", True)


def main() -> int:
    for fn in [
        test_supplied_lag_table_verifies_the_channel,
        test_one_document_carries_both_engines,
        test_quiet_on_clean_data,
        test_finds_what_is_there,
        test_seasonality_is_not_reported_as_outliers,
        test_one_event_is_one_finding,
        test_channel_wide_facts_roll_up,
        test_renames,
        test_restatement,
        test_outlier_needs_size_as_well_as_score,
        test_rates_catch_unit_changes,
        test_capping_is_honest,
        test_summary_spec_refuses_nonsense,
        test_real_spec_is_valid,
        test_prior_reader_handles_their_quirks,
        test_prior_matching_is_on_the_numbers,
        test_generic_reader_is_loud_about_guessing,
        test_observations_never_expose_internals,
    ]:
        fn()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("all EDA and summary checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
