"""Reconcile a new load's dimension values against the historical dictionary.

This is the module that addresses the problem Anushree raised on the 1 Sep
call: a value spelled ``Awareness`` in every previous quarter arrives spelled
slightly differently, the MMM treats it as a new variable, and the model
silently splits one driver into two.

The design separates *detection* from *repair*, and repair into two tiers,
because the Kaizen data-science plugin's transformation policy requires it:

* **Mechanical** variants -- pure whitespace or case differences, and
  differences only in separator punctuation -- are unambiguous and lossless.
  ``apply_fixes(..., tier="mechanical")`` applies them on a copy and logs them.
* **Judgment** variants -- a plausible misspelling, a renamed value, a value
  that has genuinely never been seen -- are *proposed only*. They are returned
  as a decision list for a human to confirm. Nothing downstream should consume
  a judgment fix that has not been signed off.

The dictionary itself is the accumulated memory of previous loads, keyed by
client, channel and column, and is versioned on disk so a mapping decision is
made once and then reused.
"""

from __future__ import annotations

import difflib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

#: Punctuation treated as interchangeable separators when comparing values.
#:
#: Deliberately excludes ``.`` and ``,``: in a marketing dimension those are
#: semantic, not decorative. Treating them as separators makes "Ensure 1.5"
#: and "Ensure 15" -- or "1,500" and "1.500" -- look like the same value, and
#: this module would then merge two distinct product strengths into one model
#: variable automatically, which is the exact failure it exists to prevent.
SEPARATORS = r"[\s\-_/|]+"

#: Accepted values for ``apply_fixes(tier=...)``.
_TIERS = {"mechanical", "all", "none"}


@dataclass
class ValueFinding:
    """One new value and what the dictionary thinks of it."""

    column: str
    raw_value: str
    n_rows: int
    verdict: str  # known | mechanical | judgment | new | retired
    proposed_value: str | None = None
    reason: str = ""
    similarity: float | None = None
    metric_share: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def normalise(value) -> str:
    """Case-fold, strip accents, and collapse separators to a single space."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = unicodedata.normalize("NFKD", str(value))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(SEPARATORS, " ", s).strip().lower()
    return s


def squash(value) -> str:
    """Normalise and additionally drop every non-alphanumeric character."""
    return re.sub(r"[^a-z0-9]", "", normalise(value))


# --------------------------------------------------------------------------
# dictionary
# --------------------------------------------------------------------------


class ValueDictionary:
    """Canonical dimension values per channel and column, persisted as JSON."""

    def __init__(self, data: dict | None = None, path: str | Path | None = None):
        self.data = data or {"version": 1, "channels": {}}
        self.path = Path(path) if path else None

    # -- persistence -------------------------------------------------------

    @classmethod
    def load(cls, path: str | Path) -> "ValueDictionary":
        p = Path(path)
        if not p.exists():
            return cls(path=p)
        return cls(json.loads(p.read_text(encoding="utf-8")), path=p)

    def save(self, path: str | Path | None = None) -> Path:
        p = Path(path or self.path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self.data["updated_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        p.write_text(json.dumps(self.data, indent=2, sort_keys=True), encoding="utf-8")
        return p

    # -- build / query -----------------------------------------------------

    def learn(
        self,
        frame: pd.DataFrame,
        channel: str,
        columns: list[str],
        *,
        source: str = "",
    ) -> "ValueDictionary":
        """Add every distinct value in ``columns`` to the dictionary."""
        ch = self.data["channels"].setdefault(channel, {"columns": {}})
        for col in columns:
            if col not in frame.columns:
                continue
            entry = ch["columns"].setdefault(col, {"canonical": [], "aliases": {}, "sources": []})
            known = set(entry["canonical"])
            for v in frame[col].dropna().astype(str).unique():
                if v not in known:
                    entry["canonical"].append(v)
                    known.add(v)
            entry["canonical"].sort()
            if source and source not in entry["sources"]:
                entry["sources"].append(source)
        return self

    def canonical(self, channel: str, column: str) -> list[str]:
        return (
            self.data.get("channels", {})
            .get(channel, {})
            .get("columns", {})
            .get(column, {})
            .get("canonical", [])
        )

    def aliases(self, channel: str, column: str) -> dict:
        return (
            self.data.get("channels", {})
            .get(channel, {})
            .get("columns", {})
            .get(column, {})
            .get("aliases", {})
        )

    def record_alias(self, channel: str, column: str, alias: str, canonical: str) -> None:
        """Persist a confirmed judgment decision so it is never asked again."""
        entry = (
            self.data["channels"]
            .setdefault(channel, {"columns": {}})["columns"]
            .setdefault(column, {"canonical": [], "aliases": {}, "sources": []})
        )
        entry["aliases"][alias] = canonical
        if canonical not in entry["canonical"]:
            entry["canonical"].append(canonical)
            entry["canonical"].sort()


# --------------------------------------------------------------------------
# diffing
# --------------------------------------------------------------------------


def classify_value(
    value: str,
    canon: list[str],
    aliases: dict,
    *,
    fuzzy_threshold: float = 0.86,
) -> tuple[str, str | None, str, float | None]:
    """Classify one value against the dictionary.

    Returns ``(verdict, proposed_value, reason, similarity)``.

    Only the ``mechanical`` verdict is safe to apply without a human, so the
    bar for it is high: the value must normalise to exactly one canonical
    value. Two cases that look mechanical but are not:

    * **Ambiguous target.** If two canonical values share a normal form
      (``Non Brand`` and ``Non-Brand`` both live in history), picking one is an
      arbitrary choice that decides which historical rows the new load joins
      to. That is a judgment call, and it is returned as one.
    * **Punctuation-only match beyond the separator set.** Collapsing every
      non-alphanumeric character can merge genuinely distinct values, so a
      match found only that way is a proposal, never an automatic fix.
    """
    if value in canon:
        return "known", value, "exact match in dictionary", 1.0
    if value in aliases:
        return "known", aliases[value], "resolved via confirmed alias", 1.0

    by_norm: dict[str, list[str]] = {}
    for c in canon:
        by_norm.setdefault(normalise(c), []).append(c)
    by_squash: dict[str, list[str]] = {}
    for c in canon:
        by_squash.setdefault(squash(c), []).append(c)

    n, s = normalise(value), squash(value)

    if n in by_norm:
        targets = by_norm[n]
        if len(targets) > 1:
            return (
                "judgment",
                targets[0],
                f"normalises onto {len(targets)} existing values ({targets}) - "
                "which one this joins to is a decision, not a rule",
                1.0,
            )
        target = targets[0]
        if value.strip() != value:
            reason = "leading/trailing whitespace"
        elif value.lower() == target.lower():
            reason = "letter case differs"
        else:
            reason = "separator punctuation differs (space/hyphen/underscore/slash/pipe)"
        return "mechanical", target, reason, 1.0

    if s in by_squash:
        targets = by_squash[s]
        return (
            "judgment",
            targets[0],
            "matches an existing value only after removing all punctuation "
            f"({targets}) - could be a real distinction (e.g. 1.5 vs 15), so "
            "this is not applied automatically",
            1.0,
        )

    if canon:
        match = difflib.get_close_matches(n, list(by_norm), n=1, cutoff=fuzzy_threshold)
        if match:
            target = by_norm[match[0]][0]
            sim = difflib.SequenceMatcher(None, n, match[0]).ratio()
            return (
                "judgment",
                target,
                f"close to existing value (ratio {sim:.2f}) - likely a spelling variant",
                sim,
            )
    return "new", None, "no comparable value in dictionary", None


def diff_values(
    frame: pd.DataFrame,
    dictionary: ValueDictionary,
    channel: str,
    columns: list[str],
    *,
    metric_cols: list[str] | None = None,
    fuzzy_threshold: float = 0.86,
    report_retired: bool = True,
) -> list[ValueFinding]:
    """Compare every distinct value in ``columns`` against the dictionary."""
    findings: list[ValueFinding] = []
    metric_cols = [c for c in (metric_cols or []) if c in frame.columns]

    for col in columns:
        if col not in frame.columns:
            continue
        canon = dictionary.canonical(channel, col)
        alias = dictionary.aliases(channel, col)
        counts = frame[col].dropna().astype(str).value_counts()
        for value, n in counts.items():
            verdict, proposed, reason, sim = classify_value(
                value, canon, alias, fuzzy_threshold=fuzzy_threshold
            )
            share = {}
            if metric_cols:
                sub = frame[frame[col].astype(str) == value]
                for m in metric_cols:
                    tot = pd.to_numeric(frame[m], errors="coerce").sum()
                    part = pd.to_numeric(sub[m], errors="coerce").sum()
                    share[m] = round(float(part), 2)
                    if tot:
                        share[f"{m}_pct"] = round(100.0 * float(part) / float(tot), 3)
            findings.append(
                ValueFinding(
                    column=col,
                    raw_value=value,
                    n_rows=int(n),
                    verdict=verdict,
                    proposed_value=proposed,
                    reason=reason,
                    similarity=sim,
                    metric_share=share,
                )
            )
        if report_retired:
            seen = set(counts.index.astype(str))
            for c in canon:
                if c not in seen:
                    findings.append(
                        ValueFinding(
                            column=col,
                            raw_value=c,
                            n_rows=0,
                            verdict="retired",
                            proposed_value=None,
                            reason="in dictionary but absent from this load",
                        )
                    )
    return findings


def internal_collisions(
    frame: pd.DataFrame, columns: list[str], metric_cols: list[str] | None = None
) -> list[dict]:
    """Find values *within one load* that collapse to the same normal form.

    This catches drift that happens mid-file -- e.g. ``OLA - AMAZON`` in one
    month and ``OLA AMAZON`` in the next -- which a dictionary diff alone can
    miss when both spellings are new.
    """
    out = []
    metric_cols = [c for c in (metric_cols or []) if c in frame.columns]
    for col in columns:
        if col not in frame.columns:
            continue
        groups: dict[str, list[str]] = {}
        for v in frame[col].dropna().astype(str).unique():
            groups.setdefault(squash(v), []).append(v)
        for key, variants in groups.items():
            if len(variants) < 2:
                continue
            detail = []
            for v in variants:
                sub = frame[frame[col].astype(str) == v]
                d = {"value": v, "n_rows": int(len(sub))}
                dc = _date_col(frame)
                if dc:
                    d["first_seen"] = str(pd.to_datetime(sub[dc]).min().date())
                    d["last_seen"] = str(pd.to_datetime(sub[dc]).max().date())
                for m in metric_cols:
                    d[m] = round(float(pd.to_numeric(sub[m], errors="coerce").sum()), 2)
                detail.append(d)
            out.append({"column": col, "normal_form": key, "variants": detail})
    return out


# --------------------------------------------------------------------------
# repair
# --------------------------------------------------------------------------


def apply_fixes(
    frame: pd.DataFrame,
    findings: list[ValueFinding],
    *,
    tier: str = "mechanical",
    confirmed: dict[tuple[str, str], str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply fixes to a **copy** of ``frame`` and return it with a change log.

    ``tier="mechanical"`` applies only the unambiguous fixes. Judgment fixes
    are applied only when passed explicitly in ``confirmed`` as
    ``{(column, raw_value): canonical_value}``, which is where a human
    sign-off enters the pipeline. There is deliberately no tier that applies
    judgment fixes in bulk; ``tier="none"`` applies nothing but ``confirmed``.

    An unrecognised ``tier`` raises rather than quietly applying nothing --
    a silent no-op would leave the caller believing the load was repaired.
    """
    if tier not in _TIERS:
        raise ValueError(
            f"tier must be one of {sorted(_TIERS)}, got {tier!r}. "
            "Judgment fixes are never applied by tier -- pass them in `confirmed`."
        )
    work = frame.copy()
    log: list[dict] = []
    confirmed = confirmed or {}

    # Collect the substitutions per column first, then apply each column in ONE
    # pass. Applying them one at a time against the frame being modified makes
    # them chain: a rule mapping A->B followed by one mapping B->C silently
    # turns the original A rows into C, and the second rule's row count then
    # includes rows the first rule created.
    plans: dict[str, dict[str, dict]] = {}
    for f in findings:
        target = None
        source = ""
        if tier in ("mechanical", "all") and f.verdict == "mechanical":
            target, source = f.proposed_value, "mechanical rule"
        key = (f.column, f.raw_value)
        if key in confirmed:
            target, source = confirmed[key], "human-confirmed"
        if not target or target == f.raw_value:
            continue
        plans.setdefault(f.column, {})[f.raw_value] = {
            "to": target,
            "authority": source,
            "reason": f.reason,
        }

    for col, plan in plans.items():
        if col not in work.columns:
            continue
        # Reject a plan whose target is itself a source: it is ambiguous which
        # of the two mappings the caller meant, and applying either order
        # silently merges values that were meant to stay distinct.
        chained = {src: p["to"] for src, p in plan.items() if p["to"] in plan}
        if chained:
            raise ValueError(
                f"chained substitutions in column {col!r}: {chained}. "
                "Each value must map to a final target that is not itself being "
                "remapped, or two distinct values collapse into one."
            )
        original = work[col].astype("string")
        for src, p in plan.items():
            n = int((original == src).sum())
            if not n:
                continue
            log.append(
                {
                    "column": col,
                    "from": src,
                    "to": p["to"],
                    "rows_changed": n,
                    "authority": p["authority"],
                    "reason": p["reason"],
                }
            )
        work[col] = original.replace({src: p["to"] for src, p in plan.items()})

    for col in {f.column for f in findings}:
        if col in work.columns:
            before = work[col].astype("string")
            stripped = before.str.strip()
            n = int((stripped.fillna("") != before.fillna("")).sum())
            if n:
                work[col] = stripped
                log.append(
                    {
                        "column": col,
                        "from": "<leading/trailing whitespace>",
                        "to": "<stripped>",
                        "rows_changed": n,
                        "authority": "mechanical rule",
                        "reason": "residual whitespace",
                    }
                )
    return work, pd.DataFrame(log)


def split_delimited(
    frame: pd.DataFrame, column: str, parts: list[str], sep: str = "_"
) -> pd.DataFrame:
    """Split a delimited compound field (e.g. ``Creative_Name``) into columns.

    Kvantum's step 8 "remove the underscores" is really this: the creative name
    is a packed record. Splitting it into named parts on a copy is reversible;
    blanket-stripping the delimiter is not.
    """
    work = frame.copy()
    # n=len(parts)-1 puts everything past the last named part INTO the last
    # part rather than discarding it. Splitting without n silently drops the
    # tail, which would make this lossy -- the one thing it claims not to be.
    exploded = work[column].astype("string").str.split(sep, n=len(parts) - 1, expand=True)
    for i, name in enumerate(parts):
        work[name] = exploded[i] if i in exploded.columns else pd.NA
    n_short = int(exploded.isna().any(axis=1).sum())
    work.attrs["split_delimited"] = {
        "column": column, "parts": parts, "separator": sep,
        "rows_with_fewer_fields_than_parts": n_short,
    }
    return work


def findings_frame(findings: list[ValueFinding]) -> pd.DataFrame:
    """Flatten findings for review or export."""
    rows = []
    for f in findings:
        d = f.to_dict()
        share = d.pop("metric_share", {}) or {}
        d.update(share)
        rows.append(d)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    order = {"judgment": 0, "new": 1, "mechanical": 2, "retired": 3, "known": 4}
    return df.assign(_o=df["verdict"].map(order)).sort_values(
        ["_o", "column", "n_rows"], ascending=[True, True, False]
    ).drop(columns="_o").reset_index(drop=True)


def _date_col(frame: pd.DataFrame) -> str | None:
    for c in ("Date", "date", "week_starting_date", "Week Starting Date", "period"):
        if c in frame.columns:
            return c
    return None
