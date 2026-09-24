"""kvprep.config -- the registry, loaded and validated by code.

Before this module the registry was documentation: ``channels.yaml`` and
``rules.yaml`` described how a client's load should be prepared, and a human
(or an agent) transcribed those decisions into function arguments at the call
site. Two runs of the same load could disagree because two people typed
different numbers, and the ``waivers:`` block had no code path at all.

Everything here exists to close that gap. The registry is parsed, validated
against a schema, and turned into the argument sets the other kvprep functions
already take. Nothing else in the library changed shape to accommodate it --
the functions were already parameterised correctly; they were just being
called by hand.

Three rules the validation enforces, because each one is a way a load can be
wrong while looking right:

* **Unknown keys are errors, not ignored.** A typo in ``significant_figures``
  silently reverts to the default and the output diffs against the maintained
  file for a reason nobody can see.
* **A threshold override must name a channel that exists.** An override on
  ``"OLA "`` never fires, and the report says PASS at the default threshold.
* **An expired waiver does not apply.** It is reported as expired and the
  underlying failure stands. A waiver that outlives its expiry by neglect is
  indistinguishable from a rule that was quietly deleted.
"""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = 2

# Keys accepted at each level. Anything else raises -- see the module docstring.
_CLIENT_KEYS = {"id", "name", "industry", "brand_filter", "brand_label", "notes"}
_CALENDAR_KEYS = {
    "pattern",
    "week_ending_weekday",
    "year_start",
    "n_years",
    "period_label_offset_months",
    "divisor",
    "notes",
}
_SOURCE_KEYS = {
    "file_pattern",
    "layout",
    "sheet",
    "sheet_pattern",
    "header_labels",
    "date_column",
    "week_ending_column",
    "channel_column",
    "grain",
    "notes",
}
_CHANNEL_KEYS = {
    "pipeline",
    "template",
    "label",
    "notes",
    "status",
    "unverified_until",
    "output_columns",
    "metrics",
    "dim_cols",
    "group_cols",
    "grain",
    "significant_figures",
    "date_format",
    "sort",
    "series",
    "source",
    "sheet",
    "sheet_pattern",
    "block",
    "filter",
    "mapping",
    "constants",
    "derived",
    "reconcile_columns",
    "reconcile_output_columns",
    "apply_mechanical_fixes",
    "aggregate",
    "coherence_cols",
    "reference",
    "required_columns",
    "transform",
}
_SERIES_KEYS = {"dims", "from", "notes", "transform"}
_FROM_KEYS = {"source", "sheet", "sheet_pattern", "block", "select", "metrics", "label"}
_PIPELINES = {"crosstab_series", "flat_rows"}
_TRANSFORM_KEYS = {"profile", "multiplier", "multiplier_until", "note"}


class RegistryError(ValueError):
    """A registry file is malformed, inconsistent, or refers to something absent.

    Raised eagerly and with the offending path in the message. A registry that
    half-loads is worse than one that does not load: the missing half becomes a
    default, and a default that nobody chose is how a threshold stops meaning
    anything.
    """


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _reject_unknown(where: str, got: dict, allowed: set[str]) -> None:
    extra = sorted(set(got) - allowed)
    if extra:
        near = {
            k: [a for a in allowed if a.replace("_", "") == str(k).replace("_", "").lower()]
            for k in extra
        }
        hint = {k: v for k, v in near.items() if v}
        raise RegistryError(
            f"{where}: unknown key(s) {extra}. Allowed: {sorted(allowed)}."
            + (f" Did you mean {hint}?" if hint else "")
        )


def _require(where: str, got: dict, keys: list[str]) -> None:
    missing = [k for k in keys if k not in got or got[k] in (None, [], {})]
    if missing:
        raise RegistryError(f"{where}: missing required key(s) {missing}")


def _as_date(v, where: str) -> str:
    if isinstance(v, (date, datetime)):
        return v.strftime("%Y-%m-%d")
    try:
        return datetime.strptime(str(v), "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError as exc:  # pragma: no cover - message is the point
        raise RegistryError(f"{where}: {v!r} is not a YYYY-MM-DD date") from exc


# --------------------------------------------------------------------------
# dataclasses
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class FiscalConfig:
    pattern: tuple[int, ...]
    year_start: str
    n_years: int = 1
    period_label_offset_months: int = 0
    divisor: float | None = 4.33

    def calendar_kwargs(self) -> dict:
        """Arguments for :func:`kvprep.calendar_fiscal.build_445_calendar`."""
        return {
            "year_start": self.year_start,
            "n_years": self.n_years,
            "pattern": self.pattern,
            "period_label_offset_months": self.period_label_offset_months,
        }


@dataclass(frozen=True)
class SourceConfig:
    name: str
    layout: str
    file_pattern: str | None = None
    sheet: str | None = None
    sheet_pattern: str | None = None
    header_labels: tuple[str, ...] | None = None
    date_column: str | None = None
    week_ending_column: str | None = None
    channel_column: str | None = None
    grain: str | None = None

    def matches(self, path: str | Path) -> bool:
        """True when ``path``'s filename matches this source's pattern."""
        if not self.file_pattern:
            return False
        return fnmatch.fnmatch(Path(path).name, self.file_pattern)


@dataclass
class SeriesConfig:
    """One output block: the dimension values, and where each metric comes from."""

    dims: dict[str, Any]
    source: str
    sheet: str | None = None
    sheet_pattern: str | None = None
    block: str = "latest"
    # {metric: {"select": {...}} | {"constant": value}}
    metrics: dict[str, dict] = field(default_factory=dict)
    notes: str = ""
    transform: dict = field(default_factory=dict)

    def key(self) -> tuple:
        return tuple(self.dims.items())


@dataclass
class ChannelConfig:
    """Everything one channel's load needs, resolved from the registry."""

    client: str
    name: str
    pipeline: str
    template: str
    label: str = ""
    status: str = "verified"
    # Why the channel is unverified, when it is. ``lag_profiles_confirmed``
    # means the only thing holding it back is that the redemption profiles
    # were inferred rather than supplied -- so the moment a confirmed table is
    # loaded, the status lifts on its own. A flag a person has to remember to
    # flip is a flag that gets flipped late, or early.
    unverified_until: str | None = None
    #: Filled in at load time when a conditional status is resolved -- why the
    #: channel is still gated, or why it no longer is.
    status_detail: str = ""
    notes: str = ""
    output_columns: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    dim_cols: list[str] = field(default_factory=list)
    group_cols: list[str] = field(default_factory=list)
    grain: list[str] = field(default_factory=list)
    required_columns: list[str] = field(default_factory=list)
    significant_figures: int | None = None
    date_format: str = "%m/%d/%Y"
    sort: str = "block"
    series: list[SeriesConfig] = field(default_factory=list)
    source: str | None = None
    sheet: str | None = None
    sheet_pattern: str | None = None
    block: str = "latest"
    filter: dict = field(default_factory=dict)
    mapping: dict[str, str] = field(default_factory=dict)
    constants: dict[str, Any] = field(default_factory=dict)
    derived: dict[str, str] = field(default_factory=dict)
    reconcile_columns: list[str] = field(default_factory=list)
    reconcile_output_columns: list[str] = field(default_factory=list)
    apply_mechanical_fixes: bool = False
    aggregate: bool = False
    coherence_cols: tuple = ("Spend", "Impressions", "Clicks")
    reference: str | None = None
    transform: dict = field(default_factory=dict)
    thresholds: dict = field(default_factory=dict)
    waivers: list[dict] = field(default_factory=list)
    fiscal: FiscalConfig | None = None

    # -- what the callers actually ask for --------------------------------

    def block_order(self) -> list[tuple]:
        """Emit order for ``crosstab_series`` loads: the order the series are
        written in the registry. The hand-built files are not sorted
        alphabetically -- Direct Mail puts PAB last -- and a load that
        reproduces every value but not the order still reads as a failure to
        the person diffing it."""
        return [s.key() for s in self.series]

    def suite_kwargs(self, week_col: str = "Week Starting Date") -> dict:
        """Arguments for :func:`kvprep.validate.run_standard_suite`."""
        kw = {
            "channel": self.name,
            "week_col": week_col,
            "metric_cols": list(self.metrics),
            "dim_cols": list(self.dim_cols),
            "thresholds": dict(self.thresholds),
            "coherence_cols": tuple(self.coherence_cols),
        }
        if self.group_cols:
            kw["group_cols"] = list(self.group_cols)
        if self.grain:
            kw["grain"] = list(self.grain)
        if self.required_columns:
            kw["required_cols"] = list(self.required_columns)
        return kw

    def active_waivers(self, today: date | None = None) -> tuple[list[dict], list[dict]]:
        """Split this channel's waivers into ``(active, expired)``."""
        today = today or date.today()
        active, expired = [], []
        for w in self.waivers:
            exp = w.get("expires")
            if exp and _to_date(exp) < today:
                expired.append(w)
            else:
                active.append(w)
        return active, expired


def _to_date(v) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return datetime.strptime(str(v), "%Y-%m-%d").date()


@dataclass
class ClientConfig:
    id: str
    name: str
    brand_filter: str | None
    brand_label: str | None
    fiscal: FiscalConfig
    sources: dict[str, SourceConfig]
    channels: dict[str, ChannelConfig]
    registry_root: Path
    lag_profiles: dict = field(default_factory=dict)
    paths: dict[str, Path] = field(default_factory=dict)

    def channel(self, name: str) -> ChannelConfig:
        key = name if name in self.channels else _resolve_case(name, self.channels)
        if key is None:
            raise RegistryError(
                f"client {self.id!r} has no channel {name!r}. "
                f"Known channels: {sorted(self.channels)}"
            )
        return self.channels[key]

    def source_for(self, path: str | Path) -> SourceConfig | None:
        """The source block whose ``file_pattern`` matches ``path``, if any."""
        for s in self.sources.values():
            if s.matches(path):
                return s
        return None

    def template_spec_path(self, template_id: str) -> Path:
        """``elementx.ola`` -> ``registry/templates/elementx/ola.json``."""
        parts = template_id.split(".")
        return self.registry_root.joinpath("templates", *parts).with_suffix(".json")

    def lag_profiles_path(self) -> Path:
        return self.registry_root / "clients" / self.id / "lag-factors.yaml"

    def value_dictionary_path(self) -> Path:
        """The dictionary of *raw* column values, for pre-mapping drift."""
        return self.registry_root / "clients" / self.id / "value-dictionary.json"

    def template_dictionary_path(self) -> Path:
        """The dictionary of *template* column values, for post-mapping drift.

        A separate file because it answers a different question. The raw
        dictionary catches a partner renaming itself in the extract. This one
        catches the client re-specifying the Element X taxonomy underneath the
        load -- Publisher going from 19 partner names to 4 channel codes,
        Objective from 80 audience descriptors to 4 funnel stages. Those
        columns pass every rule and reconcile to the cent; the only way to see
        them is to diff the load's own vocabulary against the vocabulary the
        previous load used.
        """
        return self.registry_root / "clients" / self.id / "value-dictionary-template.json"


def _resolve_case(name: str, mapping: dict) -> str | None:
    want = str(name).strip().upper().replace(" ", "_")
    for k in mapping:
        if str(k).strip().upper().replace(" ", "_") == want:
            return k
    return None


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------


def default_registry_root(start: str | Path | None = None) -> Path:
    """Find the plugin's ``registry/`` directory from this module's location."""
    here = Path(start or __file__).resolve()
    for p in [here, *here.parents]:
        cand = p / "registry"
        if cand.is_dir() and (cand / "clients").is_dir():
            return cand
    raise RegistryError(
        f"no registry/ directory found above {here}. Pass registry_root explicitly."
    )


def load_client(
    client_id: str,
    registry_root: str | Path | None = None,
    *,
    today: date | None = None,
    lag_factors: str | Path | None = None,
) -> ClientConfig:
    """Load and validate one client's ``channels.yaml`` and ``rules.yaml``.

    ``lag_factors`` replaces the registry's own ``lag-factors.yaml`` for this
    run. That is how the client tests their real redemption table without
    anybody editing the plugin: point the run at the file, and every series
    that names a profile uses theirs instead of ours.
    """
    root = Path(registry_root) if registry_root else default_registry_root()
    cdir = root / "clients" / client_id
    if not cdir.is_dir():
        known = sorted(p.name for p in (root / "clients").glob("*") if p.is_dir())
        raise RegistryError(f"no client {client_id!r} under {root/'clients'}. Known: {known}")

    ch_path = cdir / "channels.yaml"
    rl_path = cdir / "rules.yaml"
    if not ch_path.exists():
        raise RegistryError(f"{ch_path} does not exist")
    channels_doc = yaml.safe_load(ch_path.read_text(encoding="utf-8")) or {}
    rules_doc = yaml.safe_load(rl_path.read_text(encoding="utf-8")) if rl_path.exists() else {}
    rules_doc = rules_doc or {}

    version = channels_doc.get("schema_version")
    if version != SCHEMA_VERSION:
        raise RegistryError(
            f"{ch_path}: schema_version is {version!r}, this kvprep expects "
            f"{SCHEMA_VERSION}. A v1 registry described the load in prose for an "
            "agent to transcribe; v2 is loaded by code and must be explicit."
        )

    # -- client ------------------------------------------------------------
    cl = channels_doc.get("client") or {}
    _reject_unknown(f"{ch_path}:client", cl, _CLIENT_KEYS)
    _require(f"{ch_path}:client", cl, ["id", "name"])
    if cl["id"] != client_id:
        raise RegistryError(
            f"{ch_path}: client.id is {cl['id']!r} but the file lives in "
            f"clients/{client_id}/. One of the two is wrong."
        )

    # -- fiscal calendar ---------------------------------------------------
    fc = channels_doc.get("fiscal_calendar") or {}
    _reject_unknown(f"{ch_path}:fiscal_calendar", fc, _CALENDAR_KEYS)
    _require(f"{ch_path}:fiscal_calendar", fc, ["pattern", "year_start"])
    pattern = tuple(int(x) for x in fc["pattern"])
    if sum(pattern) not in (13,):
        raise RegistryError(
            f"{ch_path}:fiscal_calendar.pattern {pattern} sums to {sum(pattern)} weeks "
            "per quarter; a 52-week fiscal year needs 13."
        )
    divisor = fc.get("divisor", 4.33)
    if divisor is not None:
        divisor = float(divisor)
        if divisor <= 0:
            raise RegistryError(f"{ch_path}:fiscal_calendar.divisor must be > 0")
    fiscal = FiscalConfig(
        pattern=pattern,
        year_start=_as_date(fc["year_start"], f"{ch_path}:fiscal_calendar.year_start"),
        n_years=int(fc.get("n_years", 1)),
        period_label_offset_months=int(fc.get("period_label_offset_months", 0)),
        divisor=divisor,
    )

    # -- sources -----------------------------------------------------------
    sources: dict[str, SourceConfig] = {}
    for name, s in (channels_doc.get("sources") or {}).items():
        where = f"{ch_path}:sources.{name}"
        _reject_unknown(where, s, _SOURCE_KEYS)
        _require(where, s, ["layout"])
        if s["layout"] not in {"bpm_crosstab", "flat_long"}:
            raise RegistryError(
                f"{where}.layout must be 'bpm_crosstab' or 'flat_long', got {s['layout']!r}"
            )
        sources[name] = SourceConfig(
            name=name,
            layout=s["layout"],
            file_pattern=s.get("file_pattern"),
            sheet=s.get("sheet"),
            sheet_pattern=s.get("sheet_pattern"),
            header_labels=tuple(s["header_labels"]) if s.get("header_labels") else None,
            date_column=s.get("date_column"),
            week_ending_column=s.get("week_ending_column"),
            channel_column=s.get("channel_column"),
            grain=s.get("grain"),
        )
    if not sources:
        raise RegistryError(f"{ch_path}: no sources: block -- nothing can be read")

    # -- rules -------------------------------------------------------------
    rule_defaults = dict((rules_doc.get("defaults") or {}))
    overrides = dict((rules_doc.get("overrides") or {}))
    waivers = list(rules_doc.get("waivers") or [])

    # -- channels ----------------------------------------------------------
    raw_channels = channels_doc.get("channels") or {}
    if not raw_channels:
        raise RegistryError(f"{ch_path}: no channels: block")
    channels: dict[str, ChannelConfig] = {}
    for name, c in raw_channels.items():
        channels[name] = _build_channel(
            client_id, name, c, sources, fiscal, rule_defaults, overrides, waivers, ch_path
        )

    # An override or waiver naming a channel that does not exist never fires,
    # and the report then shows a PASS at a threshold nobody chose.
    unknown_over = [k for k in overrides if _resolve_case(k, channels) is None]
    if unknown_over:
        raise RegistryError(
            f"{rl_path}: overrides for channel(s) {unknown_over} that are not in "
            f"{ch_path}. Known channels: {sorted(channels)}"
        )
    unknown_waiv = sorted(
        {
            w.get("channel")
            for w in waivers
            if w.get("channel") and _resolve_case(w["channel"], channels) is None
        }
    )
    if unknown_waiv:
        raise RegistryError(
            f"{rl_path}: waivers for channel(s) {unknown_waiv} that are not in {ch_path}"
        )

    # -- redemption lag profiles ------------------------------------------
    from .lag import load_profiles  # local import: lag is optional per client

    lag_path = Path(lag_factors) if lag_factors else cdir / "lag-factors.yaml"
    if lag_factors and not lag_path.exists():
        raise RegistryError(
            f"no lag table at {lag_path}. Nothing is loaded from the registry as a "
            "fallback on purpose: silently running with our inferred profiles while "
            "the operator believes they supplied their own is the one outcome worth "
            "refusing outright."
        )
    profiles = load_profiles(lag_path)
    for name, ch in channels.items():
        for i, sc in enumerate(ch.series):
            want = (sc.transform or {}).get("profile")
            if want and want not in profiles:
                raise RegistryError(
                    f"{ch_path}:channels.{name}.series[{i}].transform.profile "
                    f"{want!r} is not in {lag_path.name}. Known profiles: "
                    f"{sorted(profiles)}. A series that needs a redemption "
                    "profile must not fall back to running unlagged."
                )

    _resolve_conditional_status(channels, profiles, lag_path)

    return ClientConfig(
        id=cl["id"],
        name=cl["name"],
        brand_filter=cl.get("brand_filter"),
        brand_label=cl.get("brand_label"),
        fiscal=fiscal,
        sources=sources,
        channels=channels,
        registry_root=root,
        lag_profiles=profiles,
        paths={"channels": ch_path, "rules": rl_path, "lag": lag_path},
    )


#: The conditions a channel's ``unverified_until`` may name. An unknown one is
#: an error rather than a condition that never clears, because a status that
#: can never lift is indistinguishable from one nobody noticed was stuck.
_UNVERIFIED_CONDITIONS = {"lag_profiles_confirmed"}


def _resolve_conditional_status(channels: dict, profiles: dict, lag_path: Path) -> None:
    """Lift an ``unverified`` status whose stated reason no longer holds.

    Coupon Drops is unverified for exactly one reason: its redemption profiles
    were inferred from the client's own output rather than supplied by them.
    When a confirmed table is loaded, that reason is gone, and the channel is
    as verified as any other -- so it says so, without anyone having to
    remember to edit ``channels.yaml`` in the same change.

    The condition is checked against the profiles the channel *actually uses*.
    A client who supplies two of three tables gets two-thirds of the way and
    the channel stays gated, which is the correct answer.
    """
    for name, ch in channels.items():
        if ch.status == "verified" or not ch.unverified_until:
            continue
        if ch.unverified_until not in _UNVERIFIED_CONDITIONS:
            raise RegistryError(
                f"channels.{name}.unverified_until is {ch.unverified_until!r}, which is "
                f"not a condition this code can check. Known: "
                f"{sorted(_UNVERIFIED_CONDITIONS)}. A condition that is never evaluated "
                "leaves the channel blocked forever with no way to tell why."
            )
        used = sorted(
            {
                (sc.transform or {}).get("profile")
                for sc in ch.series
                if (sc.transform or {}).get("profile")
            }
        )
        if not used:
            continue
        inferred = [n for n in used if not profiles[n].is_confirmed]
        if inferred:
            ch.status_detail = (
                f"{len(inferred)} of {len(used)} redemption profile(s) in "
                f"{lag_path.name} are inferred rather than supplied by the client "
                f"({', '.join(inferred)}). Supply a confirmed table with "
                "--lag-factors, or set status: supplied in that file, and this "
                "channel verifies itself."
            )
        else:
            ch.status = "verified"
            ch.status_detail = (
                f"Verified on this run: every redemption profile it uses "
                f"({', '.join(used)}) is marked supplied in {lag_path.name}."
            )


def _build_channel(
    client_id, name, c, sources, fiscal, rule_defaults, overrides, waivers, ch_path
) -> ChannelConfig:
    where = f"{ch_path}:channels.{name}"
    if not isinstance(c, dict):
        raise RegistryError(f"{where}: expected a mapping, got {type(c).__name__}")
    _reject_unknown(where, c, _CHANNEL_KEYS)
    _require(where, c, ["pipeline", "template", "metrics", "output_columns"])
    pipeline = c["pipeline"]
    if pipeline not in _PIPELINES:
        raise RegistryError(f"{where}.pipeline must be one of {sorted(_PIPELINES)}")

    metrics = list(c["metrics"])
    out_cols = list(c["output_columns"])
    missing_metrics = [m for m in metrics if m not in out_cols]
    if missing_metrics:
        raise RegistryError(
            f"{where}: metrics {missing_metrics} are not in output_columns. "
            "A metric absent from the output is computed and then thrown away."
        )

    series: list[SeriesConfig] = []
    if pipeline == "crosstab_series":
        _require(where, c, ["series"])
        seen: set[tuple] = set()
        for i, s in enumerate(c["series"]):
            sw = f"{where}.series[{i}]"
            _reject_unknown(sw, s, _SERIES_KEYS)
            _require(sw, s, ["dims", "from"])
            frm = s["from"]
            _reject_unknown(f"{sw}.from", frm, _FROM_KEYS)
            _require(f"{sw}.from", frm, ["source"])
            if frm["source"] not in sources:
                raise RegistryError(
                    f"{sw}.from.source {frm['source']!r} is not in sources: "
                    f"{sorted(sources)}"
                )
            if not frm.get("sheet") and not frm.get("sheet_pattern"):
                raise RegistryError(f"{sw}.from: needs sheet or sheet_pattern")

            # Per-metric selectors. A single-metric channel may write
            # `select:` directly rather than repeating the metric name.
            mspec: dict[str, dict] = {}
            if "metrics" in frm:
                for m, spec in frm["metrics"].items():
                    if m not in metrics:
                        raise RegistryError(
                            f"{sw}.from.metrics.{m}: not one of the channel's "
                            f"metrics {metrics}"
                        )
                    if not isinstance(spec, dict) or not ({"select", "constant"} & set(spec)):
                        raise RegistryError(
                            f"{sw}.from.metrics.{m}: needs 'select' or 'constant'"
                        )
                    mspec[m] = dict(spec)
            elif "select" in frm:
                if len(metrics) != 1:
                    raise RegistryError(
                        f"{sw}.from: a bare 'select' is only allowed when the "
                        f"channel has one metric; {name} has {metrics}. Use "
                        "from.metrics.<metric>.select."
                    )
                mspec[metrics[0]] = {"select": dict(frm["select"])}
            else:
                raise RegistryError(f"{sw}.from: needs 'select' or 'metrics'")
            absent = [m for m in metrics if m not in mspec]
            if absent:
                raise RegistryError(
                    f"{sw}.from: no source for metric(s) {absent}. Give each metric a "
                    "'select' or an explicit 'constant' -- an omitted metric would be "
                    "written as blank and read as a real zero."
                )

            dims = dict(s["dims"])
            unknown_dims = [d for d in dims if d not in out_cols]
            if unknown_dims:
                raise RegistryError(
                    f"{sw}.dims: {unknown_dims} are not in output_columns {out_cols}"
                )
            key = tuple(sorted(dims.items()))
            if key in seen:
                raise RegistryError(
                    f"{sw}.dims duplicates an earlier series: {dims}. Two blocks with "
                    "the same dimension values collapse into one on any groupby."
                )
            seen.add(key)
            tf = dict(frm.get("transform") or s.get("transform") or {})
            if tf:
                _reject_unknown(f"{sw}.transform", tf, _TRANSFORM_KEYS)
                if not tf.get("profile"):
                    raise RegistryError(
                        f"{sw}.transform: needs a 'profile' naming a redemption "
                        "profile in lag-factors.yaml. A transform with no profile "
                        "would silently pass the drops through unlagged."
                    )
                if "multiplier" in tf and float(tf["multiplier"]) <= 0:
                    raise RegistryError(f"{sw}.transform.multiplier must be > 0")
                if tf.get("multiplier_until"):
                    tf["multiplier_until"] = _as_date(
                        tf["multiplier_until"], f"{sw}.transform.multiplier_until"
                    )
            series.append(
                SeriesConfig(
                    dims=dims,
                    source=frm["source"],
                    sheet=frm.get("sheet"),
                    sheet_pattern=frm.get("sheet_pattern"),
                    block=str(frm.get("block", "latest")),
                    metrics=mspec,
                    notes=s.get("notes", ""),
                    transform=tf,
                )
            )
    else:  # flat_rows
        _require(where, c, ["source", "mapping"])
        if c["source"] not in sources:
            raise RegistryError(
                f"{where}.source {c['source']!r} is not in sources: {sorted(sources)}"
            )
        bad = [k for k, v in c["mapping"].items() if not isinstance(v, str)]
        if bad:
            raise RegistryError(f"{where}.mapping: values must be source column names; {bad}")

    unknown_roc = [
        x for x in (c.get("reconcile_output_columns") or []) if x not in out_cols
    ]
    if unknown_roc:
        raise RegistryError(
            f"{where}.reconcile_output_columns: {unknown_roc} are not in output_columns. "
            "These name columns of the *template*, which is the point -- they are how a "
            "taxonomy re-spec is caught -- so a name that is not a template column would "
            "silently check nothing."
        )

    sort = c.get("sort", "block")
    if sort not in {"block", "source"}:
        bad = [x.strip() for x in str(sort).split(",") if x.strip() not in out_cols]
        if bad:
            raise RegistryError(
                f"{where}.sort must be 'block', 'source', or a comma-separated list of "
                f"output_columns; {bad} are none of those."
            )

    thresholds = dict(rule_defaults)
    ov_key = _resolve_case(name, {k: k for k in overrides}) if overrides else None
    if ov_key:
        unknown_t = sorted(set(overrides[ov_key]) - set(rule_defaults))
        if unknown_t:
            raise RegistryError(
                f"rules.yaml:overrides.{ov_key}: {unknown_t} are not thresholds in "
                f"defaults: {sorted(rule_defaults)}"
            )
        thresholds.update(overrides[ov_key])

    ch_waivers = [
        w
        for w in waivers
        if not w.get("channel") or _resolve_case(w["channel"], {name: name}) is not None
    ]

    return ChannelConfig(
        client=client_id,
        name=name,
        pipeline=pipeline,
        template=c["template"],
        label=c.get("label", name),
        status=c.get("status", "verified"),
        unverified_until=c.get("unverified_until"),
        notes=c.get("notes", ""),
        output_columns=out_cols,
        metrics=metrics,
        dim_cols=list(c.get("dim_cols") or [d for d in out_cols if d not in metrics]),
        group_cols=list(c.get("group_cols") or []),
        grain=list(c.get("grain") or []),
        required_columns=list(c.get("required_columns") or []),
        significant_figures=c.get("significant_figures"),
        date_format=c.get("date_format", "%m/%d/%Y"),
        sort=sort,
        series=series,
        source=c.get("source"),
        sheet=c.get("sheet"),
        sheet_pattern=c.get("sheet_pattern"),
        block=str(c.get("block", "latest")),
        filter=dict(c.get("filter") or {}),
        mapping=dict(c.get("mapping") or {}),
        constants=dict(c.get("constants") or {}),
        derived=dict(c.get("derived") or {}),
        reconcile_columns=list(c.get("reconcile_columns") or []),
        reconcile_output_columns=list(c.get("reconcile_output_columns") or []),
        apply_mechanical_fixes=bool(c.get("apply_mechanical_fixes", False)),
        aggregate=bool(c.get("aggregate", False)),
        coherence_cols=tuple(c.get("coherence_cols") or ("Spend", "Impressions", "Clicks")),
        reference=c.get("reference"),
        transform=dict(c.get("transform") or {}),
        thresholds=thresholds,
        waivers=ch_waivers,
        fiscal=fiscal,
    )


# --------------------------------------------------------------------------
# waivers, made binding
# --------------------------------------------------------------------------


def apply_waivers(report, channel: ChannelConfig, load: str | None = None, today=None) -> dict:
    """Downgrade waived failures on ``report`` in place; return what happened.

    A waiver is a documented decision to accept one named rule's failure for
    one named load. Applying it here -- rather than in a person's head while
    reading the report -- is what makes the ``waivers:`` block mean anything.

    Three things this deliberately will not do:

    * apply an **expired** waiver (it is reported as expired and the failure
      stands);
    * apply a waiver scoped to a different ``load`` than the one being run;
    * apply a waiver to a rule that **passed** -- a waiver with nothing to
      waive is reported as stale, because it is usually a rule that was
      renamed.
    """
    today = _to_date(today) if today else date.today()
    active, expired = channel.active_waivers(today)
    applied, unused = [], []
    for w in active:
        if w.get("load") and load and str(w["load"]) != str(load):
            continue
        hit = [
            r
            for r in report.results
            if r.rule_id == w.get("rule_id") and r.status == "FAIL"
        ]
        if not hit:
            unused.append(w)
            continue
        for r in hit:
            r.status = "WAIVED"
            r.detail = dict(r.detail or {})
            r.detail["waiver"] = {
                "reason": w.get("reason", ""),
                "accepted_by": w.get("accepted_by", "UNRECORDED"),
                "expires": str(w.get("expires", "")),
                "load": w.get("load", "any"),
            }
            r.message = f"WAIVED ({w.get('accepted_by', 'UNRECORDED')}): " + r.message
            applied.append({"rule_id": r.rule_id, **r.detail["waiver"]})
    return {
        "applied": applied,
        "expired": [dict(w) for w in expired],
        "unused": [dict(w) for w in unused],
    }


def describe(client: ClientConfig) -> str:
    """A short human-readable summary of what the registry says."""
    lines = [
        f"client   : {client.id} ({client.name})",
        f"registry : {client.registry_root}",
        f"calendar : {client.fiscal.pattern} from {client.fiscal.year_start}, "
        f"divisor {client.fiscal.divisor}",
        f"sources  : " + ", ".join(f"{k} [{v.layout}]" for k, v in client.sources.items()),
        "channels :",
    ]
    for n, ch in client.channels.items():
        extra = f"{len(ch.series)} series" if ch.series else f"{len(ch.mapping)} mapped columns"
        lines.append(
            f"  {n:<14} {ch.pipeline:<16} template={ch.template:<26} "
            f"{extra}, status={ch.status}"
        )
    return "\n".join(lines)


def to_json(client: ClientConfig) -> str:
    """Serialise the resolved configuration, for the run manifest."""

    def _enc(o):
        if isinstance(o, Path):
            return str(o)
        if hasattr(o, "__dict__"):
            return {k: v for k, v in vars(o).items() if k != "fiscal"}
        return str(o)

    return json.dumps(
        {
            "client": client.id,
            "fiscal": vars(client.fiscal),
            "sources": {k: vars(v) for k, v in client.sources.items()},
            "channels": {k: _enc(v) for k, v in client.channels.items()},
        },
        indent=2,
        default=_enc,
    )
