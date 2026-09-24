"""Coupon redemption lag -- turning drops into the number the model wants.

A coupon dropped in January is not redeemed in January. It carries a 16-18
month expiry and is redeemed gradually across that window, so the figure the
model needs for month *t* is not "coupons dropped in *t*" but "coupons
redeemed in *t*", summed over every earlier drop that is still live::

    redemptions(t) = SUM over k of  profile[k] x drops(t - k)

which is a convolution of the drop series with a redemption profile. The
profile is an assumption the client supplies and updates; it varies by brand
and by channel family (outpatient field force, acute care, direct mail).

Two further wrinkles, both from how Abbott's files actually arrive:

**Before 2026 the direct-mail drop count did not exist.** Only shipments were
reported, and the coupon count was estimated as shipments x a flat
coupons-per-shipment factor. From 2026 the client supplies the actual drop
count, and the multiplier becomes 1 -- the same arithmetic with a different
input, which is why it is a registry value and not a branch in this file.

**The profile needs history the load window does not contain.** Redemptions in
the first month of a load depend on drops up to eighteen months earlier. Run
this on a window that starts where the extract starts and the opening months
are understated by however much of the profile has no drops behind it, which
is a quiet, plausible, entirely wrong answer. :func:`warmup_shortfall` measures
exactly that, and KV-C16 fails on it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


class LagError(ValueError):
    """A redemption profile is missing, malformed, or does not apply here."""


@dataclass(frozen=True)
class LagProfile:
    """One redemption profile: the share redeemed k months after the drop."""

    name: str
    months: tuple[float, ...]
    status: str = "supplied"          # supplied | recovered
    source: str = ""
    note: str = ""
    heldout_error_pct: float | None = None

    @property
    def length(self) -> int:
        return len(self.months)

    @property
    def total(self) -> float:
        return float(sum(self.months))

    @property
    def is_confirmed(self) -> bool:
        """A recovered profile is a hypothesis until somebody confirms it."""
        return self.status == "supplied"

    def describe(self) -> str:
        bits = [
            f"{self.length} months",
            f"{self.total:.1%} of drops redeemed over its life",
        ]
        if self.status == "recovered":
            bits.append(
                "RECOVERED from the client's own consolidated file, not supplied"
                + (
                    f" (held-out error {self.heldout_error_pct:.1f}%)"
                    if self.heldout_error_pct is not None
                    else ""
                )
            )
        return "; ".join(bits)


def load_profiles(path: str | Path) -> dict[str, LagProfile]:
    """Load and validate ``lag-factors.yaml``."""
    p = Path(path)
    if not p.exists():
        return {}
    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    out: dict[str, LagProfile] = {}
    for name, entry in (doc.get("profiles") or {}).items():
        months = entry.get("months")
        if not months:
            raise LagError(f"{p}: profile {name!r} has no months list")
        vals = [float(x) for x in months]
        if any(v < 0 for v in vals):
            raise LagError(
                f"{p}: profile {name!r} has a negative share. A redemption "
                "profile is a share of the drop; it cannot be negative."
            )
        total = sum(vals)
        if not 0 < total <= 1.5:
            # Above 1 is possible for a profile that also carries a scale, but
            # far above it means somebody has entered percentages as whole
            # numbers, which would multiply every figure by a hundred.
            raise LagError(
                f"{p}: profile {name!r} sums to {total:.3f}. Shares are "
                "fractions, not percentages -- 0.12 rather than 12."
            )
        status = entry.get("status", "supplied")
        if status not in {"supplied", "recovered"}:
            raise LagError(
                f"{p}: profile {name!r} has status {status!r}; expected "
                "'supplied' (the client gave us these) or 'recovered' "
                "(we inferred them and they are unconfirmed)."
            )
        out[name] = LagProfile(
            name=name,
            months=tuple(vals),
            status=status,
            source=entry.get("source", ""),
            note=(entry.get("note") or "").strip(),
            heldout_error_pct=entry.get("heldout_error_pct"),
        )
    return out


def apply_lag(
    monthly: pd.Series,
    profile: LagProfile,
    *,
    multiplier: float = 1.0,
    multiplier_until: str | pd.Timestamp | None = None,
) -> pd.Series:
    """Convolve a monthly drop series with a redemption profile.

    ``multiplier`` converts the driver into a coupon count -- 1.0 when the
    source already is one, and the coupons-per-shipment factor when it is not.
    ``multiplier_until`` is the last month the multiplier applies to: from the
    month after it the source is assumed to already be a coupon count. That is
    the 2026 cutover, expressed as data so it is a diff to the registry rather
    than a branch in the code.

    The result is indexed on the same months as the input. A month whose
    profile reaches back past the start of the input is computed from what is
    there, so it is understated -- :func:`warmup_shortfall` is what notices.
    """
    s = pd.Series(monthly).copy()
    s.index = pd.to_datetime(s.index)
    s = s.sort_index()
    vals = pd.to_numeric(s, errors="coerce").fillna(0.0)

    if multiplier_until is not None:
        cut = pd.Timestamp(multiplier_until)
        scaled = vals.where(vals.index > cut, vals * float(multiplier))
    else:
        scaled = vals * float(multiplier)

    k = np.asarray(profile.months, dtype="float64")
    idx = list(scaled.index)
    pos = {t: i for i, t in enumerate(idx)}
    out = np.zeros(len(idx), dtype="float64")
    arr = scaled.to_numpy(dtype="float64")
    for i, t in enumerate(idx):
        acc = 0.0
        for j, w in enumerate(k):
            if w == 0.0:
                continue
            src = pos.get(t - pd.DateOffset(months=j))
            if src is not None:
                acc += w * arr[src]
        out[i] = acc
    res = pd.Series(out, index=scaled.index, name=s.name)
    res.attrs["profile"] = profile.name
    res.attrs["multiplier"] = float(multiplier)
    return res


def warmup_shortfall(
    monthly: pd.Series, profile: LagProfile, window_start: str | pd.Timestamp
) -> dict:
    """How much of the profile has no drop history behind it at the window start.

    Returns the number of months of history available before ``window_start``,
    how many the profile needs, and the share of the profile's weight that
    falls off the start of the data for the first month of the window. That
    share is, to a first approximation, the proportion by which that month's
    redemptions are understated.
    """
    s = pd.Series(monthly)
    s.index = pd.to_datetime(s.index)
    start = pd.Timestamp(window_start).normalize().replace(day=1)
    have = s.index[s.index < start]
    n_before = int(len(have))
    need = profile.length - 1
    k = np.asarray(profile.months, dtype="float64")
    uncovered = float(k[n_before + 1 :].sum()) if n_before + 1 <= len(k) else 0.0
    total = float(k.sum()) or 1.0
    return {
        "months_of_history_before_window": n_before,
        "months_the_profile_needs": need,
        "profile_weight_without_history": round(uncovered, 6),
        "first_month_understated_pct": round(100.0 * uncovered / total, 3),
        "earliest_drop": str(have.min().date()) if n_before else None,
        "window_start": str(start.date()),
        "profile": profile.name,
    }
