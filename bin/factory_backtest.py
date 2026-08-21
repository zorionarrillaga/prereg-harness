#!/usr/bin/env python3
"""factory_backtest.py — THE EDGE FACTORY, Phase 1: the no-lookahead bar-walk backtester.

Charter §3-Phase-1: *"One no-lookahead bar-walk backtester (seeded from the gym driver's walker,
which already exists) + the cost model + a permutation/placebo scorer."* This file is the first
two. The third is `factory_scorer.py`; the gate that points one at the other is
`factory_notblind.py`.

━━ IT DOES NOT REIMPLEMENT THE WALKER, AND THAT IS THE WHOLE DESIGN ━━━━━━━━━━━━━━━━━━━━━━━━━
`harness_ruler.walk_bounds` is the project's audited ruler. It already encodes three disciplines
that took live losses to learn — the walk starts STRICTLY AFTER the entry minute (the entry
bar's range had partly elapsed when the fill happened, so crediting its extremes hands the
ruler excursion that was never available); SL resolves before TP inside a bar (pessimistic);
the terminating bar's favourable extreme is not credited (within 1m we cannot know the order).

A copy of that logic here would be a SECOND ruler, and this project has already paid for what
two rulers cost: C2's v1 pooled number was VOID because it measured a ruler change, and the
`ruler_impl:`-vs-`ruler:` key mixup silently broke the only adjudicable contender. So
`walk_trade` below DELEGATES. The one thing the factory needs that `walk_bounds` lacks — a
maximum hold, because a mechanical candidate declares its own time exit — is implemented by
TRUNCATING THE TAPE before delegating, never by forking the walk. An EOD terminator on a
truncated tape IS the time exit, computed by the same code path as every other exit.

━━ TWO PHASE-0 FINDINGS ARE ENFORCED HERE, NOT LEFT TO THE CALLER ━━━━━━━━━━━━━━━━━━━━━━━━━━
1. **FLAT bars are dropped.** `high == low` is vendor padding (Phase 0: 10.6% overall, 3.06%
   inside RTH on US100, and the index/FX split is ~2×). A stop "touched" on a padded bar never
   happened. Dropping them is the charter's instruction; the count is reported, never silent.
2. **The hold window is measured in WALL-CLOCK TIME, not in bars.** This is not pedantry: once
   flat bars are dropped, "30 bars" and "30 minutes" are different windows, and the difference
   is correlated with how quiet the tape was — i.e. with volatility, i.e. with the outcome. A
   bar-counted hold would hand the backtester a quiet-market bias for free.

━━ COSTS COME FROM A FROZEN FILE, ON PURPOSE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`research/factory/cost_model.json` is written by `factory_cost_model.py` and git-tracked. This
module READS it and refuses to run without it. It does not recompute: a cost that recomputes
is a cost that can drift under a result, and the charter's pre-registration discipline means
the number a candidate is judged against must be fixed BEFORE the candidate is judged.

⚠ THE COST IS THE SAME ORDER AS THE EFFECT BEING HUNTED. Central round trip 1.20pt = 0.034R at
a 35pt stop; the p90-adverse band is 26.71pt = 0.763R, which is 5× the ratified 0.15R MUE.
`apply_cost` therefore takes the band explicitly and every caller must say which one it used.

Verbs:
  costs                                     print the frozen cost record
  selftest                                  the walker's own invariants, measured not asserted
"""
import argparse
import datetime
import json
import math
import os
import statistics as st
import sys
import zoneinfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))
import harness_ruler as mcf                    # noqa: E402  THE walker — delegated to, never copied
import factory_data as fd                      # noqa: E402  vendor corpus + instrument specs

FACTORY_DIR = os.environ.get("HARNESS_FACTORY_DIR") or os.path.join(ROOT, "research", "factory")
COST_FILE = os.path.join(FACTORY_DIR, "cost_model.json")

# The two cost bands the charter names. "central" is the median round trip; "adverse" is the
# p90 tail. A verdict must state which it used — see the module header.
COST_BANDS = ("central", "adverse", "none")

# ━━ THE SYMBOL IS REQUIRED, AND THAT IS THE WHOLE POINT OF THIS BLOCK ━━━━━━━━━━━━━━━━━━━━━━━
# `sym` used to default to None, and None meant "the fitted instrument" — so a caller that simply
# FORGOT the argument was charged US100's 1.20pt against whatever instrument it was actually
# screening. That is not a hypothetical: `factory_prescreen.py` takes `sym` as a parameter at six
# entry points and dropped it at seven cost calls; `factory_session_partition.py` takes `--symbol`
# from the CLI and dropped it; `factory_c2.py` screens USA500IDXUSD and dropped it; and
# `backtest()` had no `sym` parameter at all, so the highest-traffic entry point in the module
# could not have passed one. F152 already measured what this class costs once: F117's headline
# band was ~93% cost artifact.
#
# The guard at the leaf was never the problem — it worked. The DEFAULT was the problem. Contract
# `2026-08-13__cost-constant-bypasses-instrument-guard`: *"a guard a call site can decline by
# writing the constant inline is not a guard."* A guard a call site can decline by omitting an
# argument is not a guard either. So there is no default: omit `sym` and you get a loud refusal.
#
# ⚠ NAMED `_SYM_REQUIRED`, NOT `_UNSET`, AND THAT IS NOT STYLE. This module ALREADY binds a
# module-level `_UNSET = object()` further down for `load_vendor(min_norm_range=...)`. A second
# `_UNSET` here REBINDS the name: `costs`/`cost_in_r` are defined ABOVE that line and capture
# the first object as their default, while the `is _UNSET` test in their bodies resolves at CALL
# time to the second — so the check silently never fires. `walk_trade`/`backtest` are defined
# BELOW it and captured the second object, so they worked. Two of four guards passing by accident
# of definition order is exactly the shape that ships. The selftest below caught it.
_SYM_REQUIRED = object()

# A generated tape is not an instrument, and pretending it is would be its own lie. It still has
# to name a cost basis, because it IS charged one — so it names THIS, explicitly, at the call
# site. The difference from the old `sym=None` is not cosmetic: SYNTHETIC has to be TYPED, and it
# is false on any real tape. Rows carry it out in `cost_sym`, so a verdict cannot hide it.
SYNTHETIC = "<synthetic-tape>"


class CostSymbolRequired(TypeError):
    """`sym` was omitted. Deliberately NOT a `CostModelNotFitted` subclass.

    A caller that writes `except CostModelNotFitted` means *"this instrument is not covered"* and
    usually has a fallback. If a forgotten argument raised that type, the fallback would swallow a
    coding defect and re-create the silent-default bug one layer up. This is a TypeError because
    that is what it is: a required argument is missing.
    """


def costs(band="central", sym=_SYM_REQUIRED):
    """The frozen round-trip cost in POINTS. Refuses rather than guesses.

    `sym == SYNTHETIC` or `sym ==` the fitted instrument ⇒ the BROKER-EVIDENCE model. Any other
    symbol ⇒ the SECOND-CLASS per-instrument model (see `factory_cost_per_instrument.py`), which
    serves `central` only and refuses `adverse` because no fill tape exists to draw a tail from.
    ⛔ Omitting `sym` raises. There is no default instrument.
    """
    if sym is _SYM_REQUIRED:
        raise CostSymbolRequired(
            "costs()/cost_in_r() require an explicit `sym`. There is no default instrument: this "
            "function returns POINTS, and points measured on one instrument are meaningless on "
            "another (US100's 1.20pt against a EURUSD stop is ~106R — 700x the 0.15R MUE, and the "
            "trade dies of arithmetic rather than of the market, F088). Pass the symbol you are "
            "actually screening; pass factory_backtest.SYNTHETIC only for a generated tape.")
    if band not in COST_BANDS:
        raise ValueError(f"unknown cost band {band!r}; expected one of {COST_BANDS}")
    # ⚠ THE SYMBOL IS VALIDATED BEFORE THE BAND, and the order is load-bearing. The first version
    # of this function returned 0.0 for band="none" BEFORE testing `sym`, which silently un-did the
    # F088 guard on the zero-cost path: `cost_in_r(35, "none", "EURUSD")` refused before the change
    # and returned 0.0 after it, so a gross-only walk on an uncosted instrument became reachable.
    # An external seat caught it. "none" must still mean zero cost — it may never mean zero checks.
    #
    # ⚠ AND `cost_model_instrument_strict()` IS NOW CALLED UNCONDITIONALLY. It used to sit behind
    # `sym is not None and ...`, so the short-circuit meant the old default path never ran the
    # label-drift check at all — the one case that skipped the check was the one every forgetful
    # caller took. Fail-closed on drift now applies to SYNTHETIC too.
    fitted = cost_model_instrument_strict()
    # ⚠ `==`, NOT `is`. SYNTHETIC is a plain str and is not interned, so a `cost_sym` read back
    # out of a persisted row compares equal but not identical — under `is` it fell through to the
    # per-instrument model and raised CostModelNotFitted. The carry-out this module advertises
    # (rows carry the basis in `cost_sym`) was one-way until this line changed. Seat-caught.
    if sym != SYNTHETIC and sym != fitted:
        return _per_instrument_cost(sym, band)
    if band == "none":
        return 0.0
    if not os.path.exists(COST_FILE):
        raise SystemExit(
            f"missing frozen cost model at {COST_FILE}\n"
            f"  regenerate: python3 bin/factory_cost_model.py --json > {COST_FILE}\n"
            f"  (it is git-tracked on purpose — a cost that recomputes can drift under a result)")
    rt = json.load(open(COST_FILE))["round_trip_cost_pt"]
    return float(rt["central"] if band == "central" else rt["adverse_p90"])


PER_INSTRUMENT_FILE = os.path.join(FACTORY_DIR, "cost_model_per_instrument.json")


def per_instrument_provenance(sym):
    """Provenance string for a symbol served by the second-class model, else None.

    Exposed so a verdict can carry the asterisk MECHANICALLY rather than by a human remembering
    which instruments were costed off a vendor book. A caller that scores a non-fitted instrument
    and does not print this is hiding the weaker evidence base, not using it.
    """
    if not os.path.exists(PER_INSTRUMENT_FILE):
        return None
    blk = json.load(open(PER_INSTRUMENT_FILE))["instruments"].get(sym)
    return blk["provenance"] if blk else None


def _per_instrument_cost(sym, band):
    """The second-class charge. Fail-closed on BOTH axes: unknown symbol AND unserved band."""
    if not os.path.exists(PER_INSTRUMENT_FILE):
        raise CostModelNotFitted(
            f"cost model is measured on {cost_model_instrument() or '<unreadable>'} only; refusing "
            f"to cost {sym}. Costs are in POINTS and points are not comparable across instruments "
            f"(US100 1.20pt / a EURUSD stop = ~106R). Measure {sym}'s spread and build the "
            f"second-class model: python3 bin/factory_spread_scaling.py --symbols {sym} "
            f"--from-year 2021 --to-year 2023 && python3 bin/factory_cost_per_instrument.py "
            f"--write — do NOT scale, default, or pass sym=None to silence this.")
    blk = json.load(open(PER_INSTRUMENT_FILE))["instruments"].get(sym)
    if not blk:
        raise CostModelNotFitted(
            f"{sym} has no row in {os.path.basename(PER_INSTRUMENT_FILE)} (needs >=8 non-degenerate "
            f"sampled days). Refusing to cost it. Do NOT scale another instrument's points.")
    if band == "none":
        return 0.0        # zero COST, but only after the symbol proved it is covered at all
    if band not in blk["bands_served"]:
        raise CostModelNotFitted(
            f"{sym} is served at bands {blk['bands_served']} only; band {band!r} is REFUSED. The "
            f"adverse band is a SLIPPAGE tail drawn from n=42 real fills on US100, and {sym} has no "
            f"fill tape — inventing one would be a fabricated number in the position that kills "
            f"candidates. A candidate on {sym} may be screened at central and MAY NOT claim to have "
            f"survived the adverse band.")
    return float(blk["central_pt"])


class CostModelNotFitted(Exception):
    """The frozen cost model does not cover the instrument being walked."""


def cost_model_instrument():
    """The ONE symbol `cost_model.json` was measured on, as a factory_data key."""
    if not os.path.exists(COST_FILE):
        return None
    return _COST_INSTRUMENT_MAP.get(json.load(open(COST_FILE)).get("instrument", ""))


# `cost_model.json` self-declares `regime_bound: "…one instrument"`. This maps its prose
# `instrument` field onto the corpus key so the guard below can compare them mechanically
# rather than by a human remembering which is which.
_COST_INSTRUMENT_MAP = {"US100.cash (broker)": "USATECHIDXUSD"}


class CostModelUnresolvable(CostModelNotFitted):
    """The fitted instrument could not be identified — so NOTHING may be costed.

    ⛔ WHY THIS EXISTS AND WHY IT IS FAIL-CLOSED. `cost_model_instrument()` returns None when
    `cost_model.json` is missing or when its `instrument` string drifts by one character out of the
    exact-match map above. Both the routing test in `costs()` and `_refuse_fitted()` in
    `factory_cost_per_instrument.py` key off that ONE lookup — so a None used to make BOTH of them
    fail OPEN together: the fitted instrument stopped being recognised, therefore stopped being
    refused a second-class row, therefore US100 itself could be served off the vendor book. An
    external seat demonstrated it in a temp HARNESS_FACTORY_DIR (label drift → `costs("central",
    sym="USATECHIDXUSD")` → 1.45, the vendor number, in place of 1.20).

    That is precisely the BL-F2 hazard — *lowering modelled cost raises net R exactly as
    effectively as lowering the bar* — reachable by a typo. One string read twice is not defence in
    depth. Unresolvable now RAISES, so the two guards fail closed together instead of open.
    """


def cost_model_instrument_strict():
    """`cost_model_instrument()`, but REFUSES rather than returning None. Use at every gate."""
    fitted = cost_model_instrument()
    if fitted is None:
        raise CostModelUnresolvable(
            f"the fitted instrument is unresolvable: {COST_FILE} is missing, or its 'instrument' "
            f"field is not one of {sorted(_COST_INSTRUMENT_MAP)}. Refusing to cost ANYTHING — when "
            f"the identity of the broker-evidence instrument is unknown, the second-class model "
            f"cannot tell which symbol it is forbidden to shadow.")
    return fitted


def cost_in_r(sl_pt, band="central", sym=_SYM_REQUIRED):
    """Cost expressed in R. R is denominated by the stop, so a wider stop pays proportionally
    less — which is exactly why a candidate cannot buy its way past costs by widening: the stop
    is also what sizes the position.

    ⚠ `costs()` returns POINTS measured on ONE instrument (US100.cash). A "point" is not a
    portable unit: EURUSD's point is ~1e-4 of price where US100's is ~4e-5 of price, so
    dividing US100's 1.20pt by a EURUSD stop charges **106R per trade** — 700× the 0.15R MUE —
    and the trade dies of arithmetic, not of the market. C1/C2/C3 were single-instrument so
    this never bit; C4 is the first multi-instrument candidate and would have been the first
    to eat it, in the PESSIMISTIC direction, producing a fake death that entered the record.

    So: pass `sym` and this REFUSES on an instrument the cost model was not measured on. It
    does not substitute, scale or default — the same fail-closed shape F054 forced on
    `session_vwap`, and for the same reason: a silent fallback degrades a rule under its own
    name. ⛔ 2026-08-14: `sym` is REQUIRED — the old `sym=None` default *was* the substitution
    it warns about, applied to every caller that forgot the argument. Generated tapes pass
    `SYNTHETIC`; real tapes pass their real symbol.

    ⚠ 2026-08-13: the guard no longer refuses OUTRIGHT on a non-fitted instrument — it routes to
    the SECOND-CLASS per-instrument model, which is still fail-closed (unknown symbol → raise,
    unserved band → raise) and still refuses to scale. The refusal moved one layer down; it did
    not weaken. A caller scoring a non-fitted symbol MUST also print
    `per_instrument_provenance(sym)` — that number is a vendor book, not our fills.
    """
    return costs(band, sym=sym) / float(sl_pt)


# ── the corpus ──────────────────────────────────────────────────────────────────────────────

def _tz_and_rth(sym):
    spec = fd.INSTRUMENTS[sym]
    h0, m0 = (int(x) for x in spec["rth"][0].split(":"))
    h1, m1 = (int(x) for x in spec["rth"][1].split(":"))
    return zoneinfo.ZoneInfo(spec["tz"]), datetime.time(h0, m0), datetime.time(h1, m1)


def clean(bars, tz=None, rth=None, drop_flat=True):
    """RTH filter + FLAT-bar removal, with both counts returned rather than swallowed.

    Returns (bars, stats). `stats` is not decoration: a day that loses 30% of its bars to
    padding is a different day from one that loses 2%, and a candidate's verdict must be
    readable against how much tape actually survived to support it.
    """
    stats = {"in": len(bars), "dropped_rth": 0, "dropped_flat": 0}
    out = []
    for b in bars:
        if tz is not None and rth is not None:
            t = datetime.datetime.fromtimestamp(b["time"], tz).time()
            if not (rth[0] <= t < rth[1]):
                stats["dropped_rth"] += 1
                continue
        if drop_flat and b["high"] == b["low"]:
            stats["dropped_flat"] += 1
            continue
        out.append(b)
    stats["out"] = len(out)
    return out, stats


# ── the degenerate-tape guard (F156) — CALIBRATED PER INSTRUMENT, NOT GLOBAL ────────────────
# ⛔ SHIPPED GLOBAL FOR ~90 MINUTES ON 2026-08-13 AND THAT WAS WRONG. An external D030 seat
# measured what a constant calibrated on ONE instrument does to the others through a SHARED
# loader: it deleted 21 USDJPY sessions, 6 EURUSD and 4 GBPUSD — full-length ordinary weekdays,
# not stuck feeds (EURUSD 2014-07-21: 522 bars, 98 distinct closes, an ordinary Monday in the
# record-low-vol summer of 2014). Re-measured here and confirmed.
#
# ★ SO THE CONSTANT IS SCOPED TO THE INSTRUMENTS IT WAS VERIFIED ON, and every other symbol gets
# NO GUARD plus a stat saying so. A loader that silently applies a foreign calibration is worse
# than one that admits it has none: the first deletes real days under a name that sounds safe,
# the second is visible in `loader_stats`. Same fail-closed-on-KNOWLEDGE shape as `cost_in_r`,
# which refuses an instrument it was not measured on rather than substituting one.
# ⚠ Consequence, stated so it is not mistaken for protection: on every symbol outside this map a
# degenerate feed WILL pass. That is the honest state — nobody has measured them.
MIN_NORM_RANGE_BY_SYM = {
    "USATECHIDXUSD": 0.45,   # verified: drops exactly the 4 Feb-2013 days, no genuine session
    "USA500IDXUSD": 0.45,    # verified: same 4 days, same event, no genuine session
}
MIN_NORM_RANGE = 0.45        # the calibrated value; NOT a global default any more


def norm_range(bars):
    """A day's range in bp of its own price, divided by sqrt(its own bar count).

    ⛔ IT IS AN EMPIRICAL DISCRIMINATOR, NOT THE RANDOM-WALK ARGUMENT THIS DOCSTRING FIRST GAVE.
    The original justification was: "under a random walk the expected range grows as sqrt(n), so
    range_bp/sqrt(n) is flat in session length." An external D030 seat measured the exponent on
    the corpus and REFUTED it, and re-measurement here confirms: the fitted log-log slope of
    range_bp on n_bars is 1.295 on US100, 1.240 on US500, and 8.483 on EURUSD / 7.635 on USDJPY
    — nowhere near 0.5. The theory was imported, not fitted.
    ⇒ WHAT SURVIVES IS WEAKER AND IS ALL THAT IS CLAIMED: dividing by sqrt(n) REDUCES the
    session-length confound enough to separate the four known stuck days from every genuine
    session ON THE TWO INSTRUMENTS IT WAS VERIFIED ON. It does NOT remove the confound — short
    sessions still score ~2.0-2.6x lower after the correction — which is exactly why this
    constant may not travel, and why `MIN_NORM_RANGE_BY_SYM` scopes it.

    ━━ WHY NOT THE RELATIVE RANGE THE FAULT CONTRACT ASKED FOR ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    F156 proposed a minimum-RELATIVE-range guard and censused the damage at <5bp, finding three
    days (2013-02-26/27/28). Measured before implementing, that instrument is the wrong one and
    its census was an artifact of its own threshold:

      · IT MISSES A FOURTH DAY OF THE SAME EVENT. 2013-02-25 is a FULL 390-bar session with a
        1.892pt range at ~2,727 (6.94bp) — visibly the same stuck feed, sitting just above the
        5bp line. The February-2013 event is four consecutive sessions, not three.
      · ITS THRESHOLD SITS IN NO GAP. Between 5bp and 10bp lie 2014-07-04, 2013-11-28,
        2017-01-16 — genuine HALF SESSIONS (July 4th, Thanksgiving, MLK). A range-only guard
        cannot tell "the feed is stuck" from "the session was short", because a short session
        has a small range for an honest reason. Any threshold that catches all four broken days
        also throws away real tradeable holiday tape.

    ⇒ The confound is SESSION LENGTH, so it is divided out. Under a random walk the expected
    range grows as sqrt(n), so `range_bp / sqrt(n_bars)` is flat in session length and reads as
    "how far did this tape travel, per unit of time it had". A short holiday session scores
    NORMALLY on it; a pinned feed does not.

    MEASURED, US100 corpus: the four February-2013 days score 0.021 / 0.043 / 0.147 / 0.351.
    The next-lowest day in fourteen years is 2014-07-04 at 0.513 — a genuine July-4 half day.
    The corpus median is 5.79, i.e. the dropped days are 16x-280x below a normal day.
    ⚠ THE "[0.40, 0.50] INVARIANCE PLATEAU" CLAIM IS DOWNGRADED, and the seat was right to call
    it out: that interval is nothing more than the open gap between the 4th and 5th ORDER
    STATISTICS of one instrument (0.3513 → 0.5132, a 1.46x gap). Restating an order-statistic
    identity as a robustness result overstates it. It is a real gap and it is why the threshold
    is not delicate ON US100 — and it is FALSE elsewhere: over the same band USDJPY's census runs
    10 → 21 → 35. The gap belongs to the instrument, not to the statistic.

    ⚠ WHAT THIS DOES NOT DO, because the tempting over-reading would be wrong: it is NOT a
    guard against expensive trades. The harm F156 actually measured is cost-in-R = spread/stop
    blowing up on a degenerate stop, and that harm is NOT confined to broken tape — at the
    hour-scale geometry, 2013-11-28 (1.393R), 2014-09-01 (1.291R) and 2014-07-04 (1.255R) are
    genuine sessions costing ~9x the MUE per trade, and this guard passes all three, correctly.
    A cost ceiling is a property of a CANDIDATE'S SPEC (declared, counted, pre-registered), not
    of the corpus loader, and it is where those days must be handled. This EXCLUDES reading a
    clean loader as evidence that a candidate's trades are affordably costed.
    """
    if not bars:
        return 0.0
    px = st.median([b["close"] for b in bars])
    if px <= 0:
        return 0.0
    rng_bp = (max(b["high"] for b in bars) - min(b["low"] for b in bars)) / px * 1e4
    return rng_bp / math.sqrt(len(bars))


_UNSET = object()


def load_vendor(sym, start, end, drop_flat=True, rth_only=True, min_norm_range=_UNSET):
    """{date: [bar, ...]} from the Phase-0 vendor cache. Cache-only — never fetches.

    A backtest that can silently reach the network is a backtest whose corpus is not the one
    that was registered. `factory_data.py pull` is the only thing allowed to fetch.

    `min_norm_range` drops degenerate-feed days (F156). It is COUNTED and the dates are
    RETURNED, never dropped silently — an uncounted exclusion reselects the sample, which is the
    defect `harness_ruler.py` was repaired for. Left unset it resolves PER INSTRUMENT from
    `MIN_NORM_RANGE_BY_SYM` and is **None on any symbol it was not calibrated on**; `stats`
    records which, so "no days dropped" can never be misread as "checked and clean". Pass
    `min_norm_range=None` explicitly to reproduce a row scored before this guard existed.
    """
    if min_norm_range is _UNSET:
        min_norm_range = MIN_NORM_RANGE_BY_SYM.get(sym)
    tz, lo, hi = _tz_and_rth(sym)
    d0, d1 = datetime.date.fromisoformat(start), datetime.date.fromisoformat(end)
    corpus, stats = {}, {"days_seen": 0, "days_used": 0, "dropped_flat": 0, "dropped_rth": 0,
                         "days_absent": 0, "days_not_ok": 0,
                         "dropped_degenerate": 0, "degenerate_days": [],
                         "degenerate_guard": min_norm_range,
                         "degenerate_guard_calibrated": sym in MIN_NORM_RANGE_BY_SYM}
    for d in fd.weekdays(d0, d1):
        p = fd._path(sym, d)
        if not os.path.exists(p):
            stats["days_absent"] += 1
            continue
        stats["days_seen"] += 1
        try:
            blob = json.load(open(p))
        except (json.JSONDecodeError, UnicodeDecodeError):
            stats["days_not_ok"] += 1
            continue
        if blob.get("status") != "ok" or not blob.get("rows"):
            stats["days_not_ok"] += 1
            continue
        bars, s = clean(blob["rows"], tz if rth_only else None,
                        (lo, hi) if rth_only else None, drop_flat)
        if not bars:
            stats["days_not_ok"] += 1
            continue
        # F156 — a pinned feed is not a quiet market. Counted separately from `days_not_ok`
        # because it is a DATA verdict on a day the vendor marked ok, and a reader must be able
        # to see how many days a published number lost to it.
        if min_norm_range is not None and norm_range(bars) < min_norm_range:
            stats["dropped_degenerate"] += 1
            stats["degenerate_days"].append(d.isoformat())
            continue
        for b in bars:
            b.setdefault("src", f"VENDOR:{sym}")
        corpus[d.isoformat()] = bars
        stats["days_used"] += 1
        stats["dropped_flat"] += s["dropped_flat"]
        stats["dropped_rth"] += s["dropped_rth"]
    return corpus, stats


# ── the walk ────────────────────────────────────────────────────────────────────────────────

class VolumelessTape(Exception):
    """Raised rather than degrading a VWAP into a TWAP. See session_vwap."""


def session_vwap(bars, upto_idx=None):
    """Running session VWAP over `bars[:upto_idx+1]`. REFUSES a volume-less tape — loudly.

    ━━ WHY THIS RAISES INSTEAD OF FALLING BACK ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Until 2026-08-12 the vendor decoder unpacked the bi5 candle's 6th field into `_v` and threw
    it away, so every cached day carried OHLC only. The first candidate to need volume was a
    VWAP-reversion rule whose ONLY claim to differ from the TWAP rule that already died as
    entry-price arithmetic (F003) is that its target is a real VWAP.

    A `volume or 1.0` fallback — the natural, tidy, one-word defensive default — turns this
    function into a TWAP and silently resurrects the dead candidate under the live one's name.
    It would not error, the backtest would run, and the verdict would be attributed to the wrong
    rule. That is the most expensive shape of bug this project has: a complete, plausible-looking
    result that answers a question nobody asked. So: no default, no fallback, no `.get`. A tape
    that cannot support a VWAP makes the VWAP candidate UNRUNNABLE, and says so.

    ⚠ Vendor BID volume (Dukascopy BID_candles_min_1). Not consolidated exchange volume — see
    factory_data.fetch_day. Legitimate and reproducible; not comparable to a published VWAP.
    """
    seg = bars if upto_idx is None else bars[:upto_idx + 1]
    if not seg:
        raise VolumelessTape("empty segment")
    missing = sum(1 for b in seg if "volume" not in b)
    if missing:
        raise VolumelessTape(
            f"{missing}/{len(seg)} bars carry no 'volume' key — this corpus predates the "
            f"2026-08-12 decoder fix. Re-pull: python3 bin/factory_data.py pull --symbols "
            f"<SYM> --from <start> --to <end>  (resume is schema-aware and will re-fetch them).")
    num = sum(((b["high"] + b["low"] + b["close"]) / 3.0) * b["volume"] for b in seg)
    den = sum(b["volume"] for b in seg)
    if den <= 0:
        raise VolumelessTape(
            f"total volume is {den} across {len(seg)} bars — every bar decoded to zero volume, "
            f"so a VWAP is undefined here. This is a DATA verdict, never a signal.")
    return num / den


def walk_trade(bars, entry_idx, side, sl_pt, tp_r=None, max_hold_min=None, band="central",
               tp_fn=None, sym=_SYM_REQUIRED):
    """ONE trade, no look-ahead. Returns a row dict, or None with a reason.

    Entry is at the CLOSE of `bars[entry_idx]` — the last price a rule reading that bar could
    have acted on. The walk then begins at the first bar strictly after it (`walk_bounds`).

    `max_hold_min` truncates the tape to the hold window BY TIMESTAMP and lets the delegated
    walker terminate at EOD-of-window. Time, not bar count — see the module header.
    """
    if entry_idx < 0 or entry_idx >= len(bars):
        return None, "entry_out_of_range"
    if not sl_pt or sl_pt <= 0:
        return None, "no_sl_pt"
    e = bars[entry_idx]
    entry_px, entry_ts = float(e["close"]), e["time"]
    long = side == "long"
    sl_px = entry_px - sl_pt if long else entry_px + sl_pt
    # `tp_fn` (bar -> price or None) is a MOVING target and takes precedence over the fixed
    # `tp_r` multiple. Registered use: C2, whose target is VWAP(t) recomputed each bar. The
    # walker itself is unmodified in the scalar case — see harness_ruler.walk_bounds and the
    # differential proof in tests/test_walk_bounds_moving_tp.py.
    tp_px = None
    if tp_fn is not None:
        tp_px = tp_fn
    elif tp_r is not None:
        tp_px = entry_px + tp_r * sl_pt if long else entry_px - tp_r * sl_pt

    tape = bars
    if max_hold_min is not None:
        horizon = entry_ts + int(max_hold_min) * 60
        tape = [b for b in bars if b["time"] <= horizon]
        # ⚠ A candidate whose hold window runs past the tape's end is NOT a candidate that held
        # to the bell — it is a candidate we cannot score. Reported as truncated so the scorer
        # can refuse it, rather than silently scoring a shorter trade than the rule declared.
        truncated = bars[-1]["time"] < horizon
    else:
        truncated = False

    info, err = mcf.walk_bounds(tape, entry_ts, entry_px, sl_px, sl_pt, side, tp_px, None)
    if err:
        return None, err
    r_gross = info["r_static"]
    return {"entry_idx": entry_idx, "side": side, "entry": entry_px, "entry_ts": entry_ts,
            "sl_pt": float(sl_pt), "tp_r": None if tp_fn is not None else tp_r,
            "tp_moving": tp_fn is not None, "max_hold_min": max_hold_min,
            "r_gross": r_gross,
            "r_net": round(r_gross - cost_in_r(sl_pt, band, sym), 6),
            "cost_r": round(cost_in_r(sl_pt, band, sym), 6), "cost_band": band,
            "cost_sym": sym,
            "terminator": info["terminator"], "bars_walked": info["bars_walked"],
            # ADDITIVE 2026-08-12: surfaced from walk_bounds, which already returns it. C2's
            # "no stacking — flat before the next signal" needs the REAL exit time; assuming
            # every trade runs its full declared hold would understate the firing rate, and
            # rate is the load-bearing quantity in the certify window (PREREG-C2 §4).
            "exit_ts": info["exit_ts"],
            "r_mfe": info["r_mfe"], "r_mae": info["r_mae"],
            "hold_truncated": truncated}, None


def backtest(corpus, rule, sl_pt, tp_r=None, max_hold_min=None, band="central",
             drop_truncated=True, sym=_SYM_REQUIRED):
    """Run `rule` over every day of `corpus`. `rule(bars) -> [(entry_idx, side), ...]`.

    Every rejection is COUNTED. An uncounted dropout reselects the sample, which is the exact
    defect repaired in `harness_ruler.py` on 2026-08-11 (16% vs 40% differential dropout made two
    arms into two differently-selected subsets, and the contrast between them was reported as
    if it were the contrast between the arms).

    ⛔ 2026-08-14: `sym` ADDED and REQUIRED. This function previously had no `sym` parameter at
    all and called `walk_trade` positionally, dropping it — so the module's highest-traffic entry
    point could not have costed a non-US100 corpus correctly even if its caller wanted to. It was
    structurally incapable of it. `factory_cost_per_instrument.py`'s header named this defect.
    """
    rows, rejected = [], {}
    for day in sorted(corpus):
        bars = corpus[day]
        for idx, side in rule(bars):
            row, err = walk_trade(bars, idx, side, sl_pt, tp_r, max_hold_min, band, sym=sym)
            if err:
                rejected[err] = rejected.get(err, 0) + 1
                continue
            if drop_truncated and row["hold_truncated"]:
                rejected["hold_truncated"] = rejected.get("hold_truncated", 0) + 1
                continue
            row["day"] = day
            rows.append(row)
    return rows, rejected


# ── selftest: the walker's invariants, MEASURED ─────────────────────────────────────────────

def selftest():
    """Every assertion here is one a mutation could break. None of them read a docstring."""
    import factory_synthetic as fs
    ok = True
    skipped = []

    def check(name, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  {'✓' if passed else '✗'} {name}{': ' + detail if detail else ''}")

    # ⊘ NOT RUN IS ITS OWN STATE, AND IT IS LOUDER THAN EITHER VERDICT.
    # A handful of checks below are pinned against the licensed vendor corpus, which does not
    # ship with this repository. Reporting them as PASS would certify nothing; reporting them
    # as FAIL would name a defect that was never observed. Both readings are false, and the
    # false one that gets believed is whichever the reader was already expecting. So an
    # unrunnable check says it did not run, by name, and the summary line carries the count.
    def skip(name, why):
        skipped.append(name)
        print(f"  ⊘ NOT RUN — {name}: {why}")

    bars = fs.make_tape("2026-01-05", 1, 0.0)
    print("── the entry bar is never walked (the no-look-ahead boundary) ──")
    # Enter at bar 100. Plant an impossible spike INSIDE bar 100 itself: if the walker credited
    # the entry bar, this would terminate instantly at the stop.
    spiked = [dict(b) for b in bars]
    spiked[100]["low"] = spiked[100]["close"] - 500
    r_plain, _ = walk_trade(bars, 100, "long", 20.0, max_hold_min=30, band="none", sym=SYNTHETIC)
    r_spike, _ = walk_trade(spiked, 100, "long", 20.0, max_hold_min=30, band="none", sym=SYNTHETIC)
    check("a 500pt spike in the ENTRY bar changes nothing",
          r_plain["r_gross"] == r_spike["r_gross"],
          f"{r_plain['r_gross']} == {r_spike['r_gross']}")
    # …and the very next bar MUST be seen, or the walker is simply blind rather than careful.
    nxt = [dict(b) for b in bars]
    nxt[101]["low"] = nxt[101]["close"] - 500
    r_next, _ = walk_trade(nxt, 100, "long", 20.0, max_hold_min=30, band="none", sym=SYNTHETIC)
    check("the same spike one bar LATER does terminate at the stop",
          r_next["terminator"] == "SL" and r_next["r_gross"] == -1.0,
          f"{r_next['terminator']} {r_next['r_gross']}")

    print("── the hold window is wall-clock, not bar count ──")
    r30, _ = walk_trade(bars, 100, "long", 60.0, max_hold_min=30, band="none", sym=SYNTHETIC)
    thinned = [b for i, b in enumerate(bars) if i <= 100 or i % 2 == 0]
    r30t, _ = walk_trade(thinned, thinned.index(bars[100]), "long", 60.0, max_hold_min=30,
                         band="none", sym=SYNTHETIC)
    check("dropping half the bars does not lengthen the hold",
          r30["bars_walked"] > r30t["bars_walked"],
          f"{r30['bars_walked']} dense vs {r30t['bars_walked']} thinned, same 30 minutes")

    print("── FLAT bars are removed, and the count is reported ──")
    padded = [dict(b) for b in bars]
    for i in (5, 6, 7):
        padded[i]["high"] = padded[i]["low"] = padded[i]["close"]
    kept, stats = clean(padded, drop_flat=True)
    check("3 planted FLAT bars are dropped and counted",
          stats["dropped_flat"] == 3 and len(kept) == len(padded) - 3,
          f"dropped {stats['dropped_flat']}")

    print("── costs are applied, in the direction that hurts ──")
    r_free, _ = walk_trade(bars, 100, "long", 20.0, max_hold_min=30, band="none", sym=SYNTHETIC)
    r_cent, _ = walk_trade(bars, 100, "long", 20.0, max_hold_min=30, band="central", sym=SYNTHETIC)
    r_adv, _ = walk_trade(bars, 100, "long", 20.0, max_hold_min=30, band="adverse", sym=SYNTHETIC)
    check("net < gross under every band, and adverse costs more than central",
          r_free["r_net"] == r_free["r_gross"] and r_cent["r_net"] < r_free["r_net"]
          and r_adv["r_net"] < r_cent["r_net"],
          f"none {r_free['r_net']:+.4f} · central {r_cent['r_net']:+.4f} · adverse {r_adv['r_net']:+.4f}")
    check("cost in R scales as 1/stop",
          abs(cost_in_r(10.0, sym=SYNTHETIC) - 2 * cost_in_r(20.0, sym=SYNTHETIC)) < 1e-12,
          f"{cost_in_r(10.0, sym=SYNTHETIC):.5f} vs 2×{cost_in_r(20.0, sym=SYNTHETIC):.5f}")

    print("── the cost model REFUSES an instrument it was not measured on (F088) ──")
    fitted = cost_model_instrument()
    # POSITIVE CONTROL FIRST: the guard must PASS the one symbol it does cover, or "it raises"
    # is indistinguishable from "it always raises" (F068 — a test that cannot fail).
    _ok = True
    try:
        cost_in_r(20.0, "central", fitted)
    except CostModelNotFitted:
        _ok = False
    check(f"passes the fitted instrument ({fitted})", _ok, "no raise on the covered symbol")
    # ⚠ THE LIST IS DERIVED, NOT HARDCODED, AND THAT MATTERS. It used to name
    # ("EURUSD", "USA500IDXUSD", "XAUUSD") literally and assert that all three refuse — which meant
    # this selftest would FAIL the moment the second-class model covered any of them. Covering
    # US500 is the STATED remediation of the open contract
    # `2026-08-12__factory-cost-model-is-us100-points-only`, so the selftest was a landmine sitting
    # on its own repair path: doing the right thing would have broken the test that guards it.
    # An external seat found it. Now the probe set is whatever is genuinely UNCOVERED today.
    # ⚠ 2026-08-14: THE CANDIDATE LIST WAS ITSELF A LANDMINE, one layer up from the one this
    # comment already describes. It was hardcoded to five symbols and filtered by coverage — so
    # when US500/XAUUSD/EURUSD were fitted second-class rows (the stated remediation of the open
    # cost-model contract), the list emptied and this check passed VACUOUSLY at "0 of 0": an
    # F068 test that cannot fail, reporting success. Derive the candidates from the INSTRUMENT
    # TABLE instead, and REFUSE TO PASS on an empty probe set.
    _covered = set()
    if os.path.exists(PER_INSTRUMENT_FILE):
        _covered = set(json.load(open(PER_INSTRUMENT_FILE))["instruments"])
    _probe = [s for s in fd.INSTRUMENTS if s not in _covered and s != fitted]
    check("there is at least one uncovered instrument left to probe with",
          bool(_probe), f"{len(_covered)} covered of {len(fd.INSTRUMENTS)} known")
    _raised = []
    for other in _probe:
        try:
            cost_in_r(20.0, "central", other)
        except CostModelNotFitted:
            _raised.append(other)
    check(f"refuses every uncovered instrument ({len(_probe)} probed)",
          len(_raised) == len(_probe), f"raised on {_raised} of {_probe}")
    # And the refusal must reach through walk_trade, not just the leaf — the walker is what a
    # candidate actually calls, so a guard that only holds at the leaf is not a guard.
    _uncov = _probe[0] if _probe else None
    try:
        walk_trade(bars, 100, "long", 20.0, max_hold_min=30, sym=_uncov)
        _through = False
    except CostModelNotFitted:
        _through = True
    check("walk_trade propagates the refusal", _through and _uncov is not None,
          f"walk_trade(sym={_uncov!r}) raised")

    print("── `sym` is REQUIRED — there is no default instrument (2026-08-14) ──")
    # The guard at the leaf always worked. What did not was the DEFAULT: `sym=None` meant "the
    # fitted instrument", so forgetting the argument bought US100's points for any tape. Each
    # check below fails if that default is restored anywhere on the chain.
    def _omits(fn, label):
        try:
            fn()
        except CostSymbolRequired:
            return True
        except Exception as e:                      # noqa: BLE001 — any other type is a FAIL
            check(f"{label} raises CostSymbolRequired, not {type(e).__name__}", False, str(e)[:60])
        return False

    check("costs() with no sym refuses",
          _omits(lambda: costs("central"), "costs()"), "raised CostSymbolRequired")
    check("cost_in_r() with no sym refuses",
          _omits(lambda: cost_in_r(20.0), "cost_in_r()"), "raised CostSymbolRequired")
    check("walk_trade() with no sym refuses",
          _omits(lambda: walk_trade(bars, 100, "long", 20.0, max_hold_min=30), "walk_trade()"),
          "raised CostSymbolRequired")
    check("backtest() with no sym refuses",
          _omits(lambda: backtest({"d": bars}, lambda b: [(100, "long")], 20.0,
                                  max_hold_min=30), "backtest()"),
          "raised CostSymbolRequired")
    # ⚠ THE TYPE SEPARATION IS LOAD-BEARING, not tidiness. Callers write `except
    # CostModelNotFitted` to mean "this instrument is not covered" and fall back. If a FORGOTTEN
    # argument raised that type, the fallback would swallow a coding defect and re-create the
    # silent default one layer up — the same bug wearing a handler.
    _leaked = False
    try:
        costs("central")
    except CostModelNotFitted:
        _leaked = True
    except CostSymbolRequired:
        pass
    check("a missing sym is NOT catchable as CostModelNotFitted", not _leaked,
          "CostSymbolRequired does not subclass it")
    # And the no-op proof: naming the fitted instrument explicitly must return bit-identical
    # numbers to the old implicit path, or this refactor moved a published number.
    _identical = all(costs(b, sym=SYNTHETIC) == costs(b, sym=fitted)
                     for b in ("central", "adverse", "none"))
    check("SYNTHETIC and the fitted symbol price identically on every band", _identical,
          f"central {costs('central', sym=fitted)} · adverse {costs('adverse', sym=fitted)}")

    print("── SL-first inside a bar (pessimism is load-bearing) ──")
    both = [dict(b) for b in bars]
    both[101]["low"] = both[100]["close"] - 500
    both[101]["high"] = both[100]["close"] + 500
    r_both, _ = walk_trade(both, 100, "long", 20.0, tp_r=2.0, max_hold_min=30, band="none", sym=SYNTHETIC)
    check("a bar containing BOTH barriers resolves to the stop",
          r_both["terminator"] == "SL", r_both["terminator"])

    print("── the degenerate-feed guard fires on pinned tape and NOT on a short session (F156) ──")
    # POSITIVE CONTROL FIRST, or "it drops the day" is indistinguishable from "it drops
    # everything" (F068 — a test that cannot fail). A normal synthetic day must survive.
    check("a normal full session passes the guard", norm_range(bars) >= MIN_NORM_RANGE,
          f"norm_range {norm_range(bars):.2f} >= {MIN_NORM_RANGE}")
    # ⛔ THE CHECK THAT USED TO SIT HERE WAS CIRCULAR AND AN EXTERNAL SEAT CAUGHT IT. It asserted
    # that a one-third-length SYNTHETIC session still passes, "so session length is divided out"
    # — but `factory_synthetic.make_tape` IS a constant-sigma Gaussian random walk, the exact
    # process under which the sqrt(n) exponent holds by construction. It could not fail, and the
    # one claim that needed testing was the one it pretended to test. On the REAL corpus the
    # exponent is 1.295, not 0.5. Replaced by the real-tape pin below.
    short = bars[:len(bars) // 3]
    check("a one-third-length synthetic session passes (NOTE: synthetic is a random walk, so "
          "this pins nothing about real tape — see the corpus check below)",
          norm_range(short) >= MIN_NORM_RANGE,
          f"norm_range {norm_range(short):.2f} over {len(short)} bars")
    # …and a PINNED tape of the same length must fail. Built by compressing the day's range
    # 200-fold about its own median — the February-2013 signature, not a date list.
    mid = st.median([b["close"] for b in bars])
    pinned = [dict(b, open=mid + (b["open"] - mid) / 200.0, high=mid + (b["high"] - mid) / 200.0,
                   low=mid + (b["low"] - mid) / 200.0, close=mid + (b["close"] - mid) / 200.0)
              for b in bars]
    check("a 200x-compressed (pinned) session of the SAME length fails it",
          norm_range(pinned) < MIN_NORM_RANGE,
          f"norm_range {norm_range(pinned):.4f} < {MIN_NORM_RANGE}")

    # ★ THE REAL-TAPE PIN. The three synthetic checks above bound the constant only to roughly
    # (0.012, 2.49) — a 200x window — because two of them are the same synthetic day scaled. A
    # threshold of 2.0 would pass every one of them while deleting 1,876 of 3,570 USDJPY days.
    # So the constant is pinned HERE, on the corpus, from BOTH sides. A date list is the right
    # thing in a TEST (it asserts behaviour); it would be the wrong thing in the guard (it would
    # be a noun that rots the next time a feed sticks) — which is why the guard has none.
    _STUCK = {"2013-02-25", "2013-02-26", "2013-02-27", "2013-02-28"}
    _corpus_days, _ = load_vendor("USATECHIDXUSD", "2012-01-01", "2026-08-11", rth_only=True)
    _HAVE_CORPUS = bool(_corpus_days)
    _WHY = ("the vendor corpus is not in this checkout (licensed 1m data; run "
            "`python3 bin/factory_data.py pull` against your own entitlement to populate it)")
    for _sym in ("USATECHIDXUSD", "USA500IDXUSD"):
        if not _HAVE_CORPUS:
            skip(f"{_sym}: the calibrated threshold drops EXACTLY the known stuck event", _WHY)
            skip(f"{_sym}: a 2.0 threshold would over-drop, so the constant is pinned from ABOVE",
                 _WHY)
            continue
        _, s_cal = load_vendor(_sym, "2012-01-01", "2026-08-11", rth_only=True)
        check(f"{_sym}: the calibrated threshold drops EXACTLY the known stuck event",
              set(s_cal["degenerate_days"]) == _STUCK,
              f"dropped {sorted(s_cal['degenerate_days'])}")
        _, s_loose = load_vendor(_sym, "2012-01-01", "2026-08-11", rth_only=True,
                                 min_norm_range=2.0)
        check(f"{_sym}: a 2.0 threshold would over-drop, so the constant is pinned from ABOVE",
              s_loose["dropped_degenerate"] > 10 * s_cal["dropped_degenerate"],
              f"{s_loose['dropped_degenerate']} days at 2.0 vs {s_cal['dropped_degenerate']} at "
              f"{MIN_NORM_RANGE}")
    # …and the constant must NOT be applied to an instrument it was never calibrated on.
    _, s_fx = load_vendor("USDJPY", "2012-01-01", "2026-08-11", rth_only=True)
    check("USDJPY (uncalibrated) gets NO guard, and says so rather than implying it is clean",
          s_fx["degenerate_guard"] is None and not s_fx["degenerate_guard_calibrated"]
          and s_fx["dropped_degenerate"] == 0,
          f"guard={s_fx['degenerate_guard']} calibrated={s_fx['degenerate_guard_calibrated']}")
    if _HAVE_CORPUS:
        _, s_fx_forced = load_vendor("USDJPY", "2012-01-01", "2026-08-11", rth_only=True,
                                     min_norm_range=MIN_NORM_RANGE)
        check("…and forcing US100's constant onto USDJPY WOULD delete genuine sessions (why it "
              "is scoped)", s_fx_forced["dropped_degenerate"] >= 10,
              f"{s_fx_forced['dropped_degenerate']} USDJPY days would be dropped")
    else:
        skip("…and forcing US100's constant onto USDJPY WOULD delete genuine sessions (why it "
             "is scoped)", _WHY)

    print("── truncation is detected, not scored as a shorter trade ──")
    r_trunc, _ = walk_trade(bars, len(bars) - 5, "long", 20.0, max_hold_min=60, band="none", sym=SYNTHETIC)
    check("a hold running past the tape's end is flagged", r_trunc["hold_truncated"], "flagged")
    rows, rej = backtest({"d": bars}, lambda b: [(len(b) - 5, "long")], 20.0,
                         max_hold_min=60, band="none", sym=SYNTHETIC)
    check("…and backtest() drops it, counted", not rows and rej.get("hold_truncated") == 1,
          f"{rej}")

    print()
    _tail = (f" · {len(skipped)} corpus-pinned check(s) NOT RUN (no vendor data in this "
             f"checkout — the synthetic invariants above are unaffected)") if skipped else ""
    print(f"  {'PASS' if ok else 'FAIL'} — walker invariants{_tail}")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("costs")
    c.add_argument("--band", choices=COST_BANDS, default="central")
    c.add_argument("--sl-pt", type=float, default=35.0)
    # The ONE place a default symbol is honest: a human is typing `costs` to read the frozen
    # record, and the record's own subject is the fitted instrument. It is still PRINTED below,
    # so the reader is never left guessing which instrument the number belongs to. Library
    # callers get no such default — see the _SYM_REQUIRED block at the top of this module.
    c.add_argument("--sym", default=None,
                   help="instrument to price (default: the fitted broker-evidence instrument)")
    sub.add_parser("selftest")
    a = ap.parse_args()
    if a.cmd == "costs":
        blob = json.load(open(COST_FILE))
        sym = a.sym or cost_model_instrument_strict()
        print(f"frozen: {COST_FILE}")
        print(f"  priced for: {sym}")
        print(f"  round trip {a.band}: {costs(a.band, sym=sym):.2f}pt "
              f"= {cost_in_r(a.sl_pt, a.band, sym=sym):.4f}R at a {a.sl_pt:g}pt stop")
        prov = per_instrument_provenance(sym)
        if prov:
            print(f"  ⚠ SECOND-CLASS basis (vendor book, not our fills): {prov}")
        print(f"  instrument: {blob['instrument']} · bound: {blob['regime_bound']}")
        return 0
    return 0 if selftest() else 1


if __name__ == "__main__":
    sys.exit(main())
