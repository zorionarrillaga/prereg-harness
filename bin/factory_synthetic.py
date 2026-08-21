#!/usr/bin/env python3
"""factory_synthetic.py — THE EDGE FACTORY, Phase 1: the KNOWN-NULL device.

Charter §3-Phase-1: *"The harness must pass NOT-BLIND validation before any real hypothesis
touches it (§3.39e): a synthetic tape with a planted edge must be detected; an edge-free shuffled
tape must return null; a known-dumb rule must lose ≈ costs."*

All three checks need a tape whose answer is known BEFORE the scorer sees it. That tape is this
module. Nothing here scores anything — it only manufactures ground truth.

━━ WHY A KNOWN-NULL COMES FIRST, IN THIS PROJECT SPECIFICALLY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The predecessor system's flagship result was Sharpe 13.76 with probability-of-overfitting 0.0%.
Every standard referee passed, and it lost money live: the referees were computed INSIDE the same
biased simulator they were certifying. What finally worked was inverting the order — validate the
validator against data with no edge in it, and only then believe a positive.

The 2026-08-11 evening repeated the lesson at small scale. The registered fork test returned a
0.725 survivor with its CI clear of chance, on the first attempt. It was withdrawn hours later:
the whole ordering was reproduced by entry-price position alone. **A scorer that had been run
against a price-position-only rule on an edge-free tape would have refused that result before it
was ever registered.** That check is `rule_price_extreme` below, and it is why this module ships
rules as well as tapes.

━━ WHAT THIS GUARANTEES, AND WHAT IT CANNOT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GUARANTEED, by construction and re-measured by `--verify`:
  · `edge_free` has i.i.d. zero-mean minute returns — no drift, no autocorrelation, no
    exploitable structure of ANY kind, not merely none of the kinds we thought to test for.
  · `planted` is that same tape plus a causal drift keyed to a signal computable from bars at or
    before the signal minute. No look-ahead: the signal never reads a bar it precedes.
  · Both are deterministic in `seed`, so a failing check is reproducible from its seed alone.
  · Every bar satisfies low ≤ min(open, close) ≤ max(open, close) ≤ high, and no bar is FLAT
    (Phase 0 found high==low bars are vendor padding; a stop "touched" on one never happened).

NOT GUARANTEED — say it before someone quotes this as more than it is:
  · A tape that passes here is edge-free *in this generator's model*. It is a Gaussian random
    walk, not a market. It can prove a scorer finds a planted effect and refuses a null one; it
    cannot prove the scorer is calibrated on real microstructure. That is what the vendor corpus
    and the shadow phase are for.
  · Passing all checks bounds the false-positive rate; it does not drive it to zero. State the
    achieved bound with the verdict, never "the harness is validated" bare.

━━ THE SRC TAG IS LOUD ON PURPOSE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Every row carries `src="SYNTHETIC"`. Rows are schema-identical to the vendor loader's rows so the
same walker consumes both — which is the point, and also the hazard: a synthetic tape that leaked
into a real verdict would be undetectable in a number and obvious in a row. Grep for the tag.

Verbs:
  emit    --kind edge_free|planted --days N [--seed S] [--out FILE]   write a tape
  verify  [--days N] [--seed S]                                       measure both values
"""
import argparse
import collections
import datetime
import json
import math
import os
import random
import statistics as st
import sys
import zoneinfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))
import harness_ruler as ca                     # noqa: E402  THE interval — one ruler, imported

ET = zoneinfo.ZoneInfo("America/New_York")       # real tz — never a fixed offset (DST)
RTH_OPEN, RTH_CLOSE = datetime.time(9, 30), datetime.time(16, 0)
RTH_MINUTES = 390                                # 09:30 → 16:00

# ── the generator's parameters, named because each one is a claim about the tape ──
START_PX = 20_000.0        # arbitrary level; every statistic below is in points, not percent
SIGMA_PT = 3.0             # per-minute stdev in points — near US100's realised 1m vol
TICKS_PER_MIN = 12         # within-minute path resolution; sets how wick extremes form
FLOOR_RANGE_PT = 0.1       # minimum high−low, so no bar is ever FLAT (see header)

# ── the planted edge ──
LOOKBACK = 20              # the signal's window, in minutes
DRIFT_MIN = 15             # how long the planted drift runs after a signal
DEFAULT_EFFECT_PT = 6.0    # total planted move over DRIFT_MIN minutes

# ★ THE GATE'S SAMPLE SIZE IS A POWER CALCULATION, NOT A TASTE.
# Derived from the MEASURED per-day sd of each null statistic (2.054pt for the signal arm,
# 0.128pt/min for drift, both over 600 independent-seed days) and the requirement that the CI
# halfwidth come in at ≤ half the tolerance band — so a genuinely null centre still has room to
# wander without tripping the gate. That lands at N ≥ 29 and N ≥ 25 respectively; 60 is double
# the binding one. Setting this from "what makes today's seed pass" would be the same p-hacking
# the equivalence form exists to prevent, so it is set from the sd and left alone.
DEFAULT_VERIFY_DAYS = 60


def _session_minutes(date_str):
    """Epoch seconds for every RTH minute of `date_str`, resolved through the real ET zone."""
    d = datetime.date.fromisoformat(date_str)
    open_dt = datetime.datetime.combine(d, RTH_OPEN, tzinfo=ET)
    return [int((open_dt + datetime.timedelta(minutes=i)).timestamp())
            for i in range(RTH_MINUTES)]


def _bar_from_path(ts, path):
    """OHLC from a within-minute price path, with the coherence invariant enforced, not assumed."""
    o, c = path[0], path[-1]
    hi, lo = max(path), min(path)
    if hi - lo < FLOOR_RANGE_PT:                 # never emit a FLAT bar
        mid = (hi + lo) / 2.0
        hi, lo = mid + FLOOR_RANGE_PT / 2, mid - FLOOR_RANGE_PT / 2
        hi, lo = max(hi, o, c), min(lo, o, c)
    return {"time": ts, "open": round(o, 2), "high": round(hi, 2), "low": round(lo, 2),
            "close": round(c, 2), "src": "SYNTHETIC", "volume": 0}


def _signal(closes, i):
    """+1 / −1 / 0 from bars at or before `i`. THE no-look-ahead boundary — closes[i] is the last
    bar the signal may read, because the drift it triggers starts at i+1."""
    if i < LOOKBACK:
        return 0
    window = closes[i - LOOKBACK:i + 1]
    mean = sum(window) / len(window)
    sd = st.pstdev(window)
    if sd <= 0:
        return 0
    z = (closes[i] - mean) / sd
    return 1 if z > 1.0 else (-1 if z < -1.0 else 0)


def make_tape(date_str, seed, effect_pt=0.0, truth=None):
    """One session. `effect_pt` 0.0 ⇒ edge_free; > 0 ⇒ that much planted drift per signal.

    The drift is applied to the RETURN STREAM as it is generated, so the planted edge is causal:
    a signal at minute i moves minutes i+1 … i+DRIFT_MIN and nothing before them.

    `truth`, if a list is passed, is filled with (bar_index, side) for the minutes where drift was
    ACTUALLY PLANTED. That is the tape's ground truth and it is NOT the same set as
    `rule_planted_signal(bars)`: the rule fires on every signal, including ones occurring while a
    drift is already running, which receive no new drift under the no-stacking rule. Those diluted
    firings drag the rule's average below the planted size — measured +4.7 to +5.1pt against a
    planted +6.0. Scoring the DECLARED effect against the RULE's mean therefore passed or failed on
    sample size alone (CI reached 6.0 at 20 days, missed it at 12). The tape's claim about itself
    is checked against `truth`; what the rule can recover from it is a separate, weaker claim.
    """
    rng = random.Random(seed)
    stamps = _session_minutes(date_str)
    px = START_PX
    bars, closes = [], []
    pending = []                                  # [(minutes_left, per_min_drift), ...]
    for i, ts in enumerate(stamps):
        drift = sum(d for _, d in pending)
        step = rng.gauss(drift, SIGMA_PT)
        # within-minute path: a Brownian bridge from prev close to this close, so wicks are real
        target = px + step
        path = [px]
        for k in range(1, TICKS_PER_MIN + 1):
            frac = k / TICKS_PER_MIN
            bridge = px + (target - px) * frac
            noise = 0.0 if k == TICKS_PER_MIN else rng.gauss(0, SIGMA_PT * 0.35)
            path.append(bridge + noise)
        bars.append(_bar_from_path(ts, path))
        px = path[-1]
        closes.append(px)
        pending = [(n - 1, d) for n, d in pending if n - 1 > 0]
        # ⚠ NO STACKING — a drift may only be planted while none is running. The first version
        # appended unconditionally, and the planted move fed back into its own trigger: drift
        # pushed the close away from its mean, which re-fired the z-score signal, which planted
        # more drift. Measured +89.34pt against a declared +6.0pt, with the signal firing on
        # ~350 of 390 minutes. That tape is a runaway trend, and a scorer "detecting" it would
        # have proved nothing — a blind one finds a 90-point move too, and every MDE calibrated
        # against it would be fiction. Caught by check 2 printing the realised effect next to
        # the declared one; the check itself passed, because `> 0` was too weak to fail.
        if effect_pt and not pending:
            s = _signal(closes, i)
            if s:
                pending.append((DRIFT_MIN, s * effect_pt / DRIFT_MIN))
                if truth is not None:
                    truth.append((i, "long" if s > 0 else "short"))
    return bars


def make_corpus(days, seed, effect_pt=0.0, start="2026-01-05", truth=None):
    """{date: [bar, ...]} over `days` weekdays. Weekdays only — a synthetic Saturday would be a
    tape no integrity check would ever accept from a vendor."""
    d = datetime.date.fromisoformat(start)
    out = {}
    while len(out) < days:
        if d.weekday() < 5:
            day_truth = [] if truth is not None else None
            out[d.isoformat()] = make_tape(d.isoformat(), seed + len(out), effect_pt, day_truth)
            if truth is not None:
                truth[d.isoformat()] = day_truth
        d += datetime.timedelta(days=1)
    return out


# ── THE RULES: what a not-blind check points AT the scorer ──────────────────────────────────
# Each returns [(bar_index, side), ...] using only bars at or before bar_index.

def rule_planted_signal(bars):
    """Fires exactly on the planted signal. A scorer that cannot find THIS is blind."""
    closes = [b["close"] for b in bars]
    out = []
    for i in range(len(bars) - DRIFT_MIN - 1):
        s = _signal(closes, i)
        if s:
            out.append((i + 1, "long" if s > 0 else "short"))
    return out


def rule_random(bars, seed=0):
    """Fires at random minutes. Must return NULL on any tape, planted or not."""
    rng = random.Random(seed)
    idxs = sorted(rng.sample(range(LOOKBACK, len(bars) - DRIFT_MIN - 1), k=12))
    return [(i, "long" if rng.random() < 0.5 else "short") for i in idxs]


def rule_price_extreme(bars, lookback=30):
    """★ THE CONFOUND RULE — the one that already fooled this project once.

    It enters long at a local price MINIMUM and short at a local MAXIMUM. It forecasts nothing:
    the trigger is a pure statement about where the entry price sits among its neighbours. Under
    a fixed stop with no take-profit that is enough to win by arithmetic — a long entered below
    its neighbours has a nearer stop and a longer run to the close.

    CONTRACT, and the reason this is the fourth not-blind check rather than a nice-to-have:
      · against a placebo matched on time only  → this rule MUST score ABOVE chance
      · against a placebo matched on ENTRY PRICE → this rule MUST return null
    Both values, or the check certifies nothing. A scorer that returns null on both is not
    passing — it is dead, and would report null for a real edge too.
    """
    out = []
    for i in range(lookback, len(bars) - DRIFT_MIN - 1):
        window = [b["close"] for b in bars[i - lookback:i + 1]]
        c = bars[i]["close"]
        if c <= min(window):
            out.append((i, "long"))
        elif c >= max(window):
            out.append((i, "short"))
    return out


def rule_dumb(bars):
    """Charter check 3: a known-dumb rule must lose ≈ costs. Buys every 30th minute regardless
    of anything — no signal, no filter, and deliberately no price-position advantage either."""
    return [(i, "long") for i in range(LOOKBACK, len(bars) - DRIFT_MIN - 1, 30)]


# ── ★ THE TIME AXIS — rule_dumb split into its own early and late halves (2026-08-12) ────────
# The epp probes above vary the PRICE axis and hold time roughly constant. These two vary the
# TIME axis and hold price EXACTLY constant: both are rule_dumb — no signal, no filter, no
# price-position selection at all — so any gap between them is the arm's response to WHEN the
# candidate sits in the session, and nothing else.
#
# They exist because the `uniform` arm carries no price band (the free parameter that killed the
# registered arm) but also no time window, and `harness_ruler`'s own header documents the time
# axis as directional: the walker DROPS a placebo whose hold runs past the session end
# (`hold_truncated`), so a late-session pool loses its members differentially and the survivors
# skew early. An arm that swapped a price free-parameter for a time-of-day bias would read as a
# repair on the epp criterion alone. Same defect class, different axis — and the criterion that
# missed it once (one probe, one point on a slope) must not miss it again.
#
# Step 10 rather than rule_dumb's 30: a third of a session at step 30 yields ~4 candidates/day.
# Overlapping 30-minute holds correlate, which is exactly what `summarize`'s day-clustered CI
# exists to absorb — the interval's width is driven by DAYS, so buying candidates per day is
# cheap and buying days is what actually narrows it.

def _third(bars):
    lo, hi = LOOKBACK, len(bars) - DRIFT_MIN - 1
    return lo, hi, (hi - lo) // 3


def rule_early_session(bars):
    """rule_dumb restricted to the FIRST third of the walkable session. epp ≈ 0.50 by construction."""
    lo, _, third = _third(bars)
    return [(i, "long") for i in range(lo, lo + third, 10)]


def rule_late_session(bars):
    """rule_dumb restricted to the LAST third. Its placebo pool is the one that loses members to
    truncation, so this is the probe that should move if the arm has a time-of-day slope."""
    _, hi, third = _third(bars)
    return [(i, "long") for i in range(hi - third, hi, 10)]


# ── VERIFY: measure both values rather than assert the docstring ────────────────────────────

def _returns(bars):
    c = [b["close"] for b in bars]
    return [c[i] - c[i - 1] for i in range(1, len(c))]


def _autocorr(xs, lag=1):
    n = len(xs)
    if n <= lag + 1:
        return 0.0
    m = sum(xs) / n
    num = sum((xs[i] - m) * (xs[i - lag] - m) for i in range(lag, n))
    den = sum((x - m) ** 2 for x in xs)
    return num / den if den else 0.0


# ── tolerances for the NULL checks, each stated as a fraction of the planted effect ──
# A null is only meaningful with the sensitivity that produced it, so these are the bands the
# interval must fit INSIDE — not thresholds it must merely straddle. Both are 25% of the planted
# effect: an "edge-free" tape carrying a quarter of the effect we plant is not a null.
TOL_DRIFT_PT_MIN = 0.25 * (DEFAULT_EFFECT_PT / DRIFT_MIN)   # 0.10 pt/min
TOL_SIGNAL_PT = 0.25 * DEFAULT_EFFECT_PT                    # 1.50 pt


def verify(days, seed):
    ok = True

    def check(name, passed, detail):
        nonlocal ok
        ok = ok and passed
        print(f"  {'✓' if passed else '✗'} {name}: {detail}")
        return passed

    def _day_ci(pairs):
        """Day-clustered CI, pre-aggregated to one value per day.

        `cluster_bootstrap_ci(..., weight="day")` computes the mean of PER-DAY means, so
        collapsing each day to its own mean first is the same estimand with the same day draws —
        verified numerically: both paths return bit-identical bounds on an 11,826-pair arm. It is
        15× faster (14.9s → 1.0s per call), which is what makes a 60-day gate runnable inside a
        test suite. The statistic is NOT weakened to buy the speed; that would be trading away
        the only thing this file is for.
        """
        byday = collections.defaultdict(list)
        for d, v in pairs:
            byday[d].append(v)
        return ca.cluster_bootstrap_ci([(d, st.mean(vs)) for d, vs in byday.items()],
                                       weight="day")

    def check_null(name, pairs, tol, unit):
        """★ THE FORM MATTERS MORE THAN THE THRESHOLD.

        The first version asked "does the CI span 0?" — which is satisfied by a WIDE interval,
        i.e. it gets EASIER to pass the less data you have. That is backwards for a null: it
        rewards low power, and it flakes at the nominal rate on seed luck, so the honest response
        to a red gate becomes "re-run it" — p-hacking the validator that exists to stop exactly
        that. Measured: the same generator passed at 12 and 20 days and failed at 8 and 30.

        The equivalence form instead requires the whole interval to lie INSIDE ±tol. Too little
        data now fails as INSUFFICIENT POWER rather than passing as a null, which is the
        charter's MDE-stamped verdict discipline applied to the instrument itself.
        """
        lo, hi = _day_ci(pairs)
        mean = sum(v for _, v in pairs) / len(pairs)
        half = (hi - lo) / 2
        if half > tol:
            return check(name, False,
                         f"INSUFFICIENT POWER at {days} days — CI ±{half:.4f}{unit} is wider than"
                         f" the ±{tol:g}{unit} band; a null here would be an artifact of low n")
        return check(name, lo >= -tol and hi <= tol,
                     f"mean {mean:+.4f}{unit}, CI [{lo:+.4f}, {hi:+.4f}] ⊂ ±{tol:g}{unit}"
                     f" (achieved bound, day-clustered)")

    print("── 1. the edge-free tape is edge-free (the null must be a real null) ──")
    free = make_corpus(days, seed, 0.0)
    drift_pairs = [(d, sum(_returns(b)) / len(_returns(b))) for d, b in free.items()]
    check_null("per-minute drift is inside the null band", drift_pairs,
               TOL_DRIFT_PT_MIN, "pt/min")
    acs = [_autocorr(_returns(b)) for b in free.values()]
    check("lag-1 autocorrelation ≈ 0",
          abs(sum(acs) / len(acs)) < 0.05,
          f"mean {sum(acs) / len(acs):+.4f} over {len(acs)} days (|x| < 0.05)")

    print("── 2. the planted tape actually contains the edge it claims ──")
    ptruth = {}
    planted = make_corpus(days, seed, DEFAULT_EFFECT_PT, truth=ptruth)

    def _moves(corpus, picks_for):
        out = []
        for d, bars in corpus.items():
            closes = [b["close"] for b in bars]
            for i, side in picks_for(d, bars):
                j = min(i + DRIFT_MIN, len(closes) - 1)
                mv = closes[j] - closes[i]
                out.append((d, mv if side == "long" else -mv))
        return out

    # ★ 2a — THE TAPE'S OWN CLAIM, scored against GROUND TRUTH (the minutes where drift was
    # actually planted). `mci[0] > 0` was the first form of this check and it passed on a tape
    # whose realised move was 15× the planted one; an effect size that is not the declared one
    # makes every MDE computed against this tape wrong, in the flattering direction. The second
    # form scored the RULE's mean against the declared size and passed or failed on sample size
    # alone — 20 days reached 6.0, 12 days did not. Ground truth removes both failure modes.
    tmoves = _moves(planted, lambda d, b: ptruth[d])
    tci = _day_ci(tmoves)
    tmean = sum(v for _, v in tmoves) / len(tmoves)
    check("planted episodes deliver the DECLARED size (declared value inside the CI)",
          tci[0] <= DEFAULT_EFFECT_PT <= tci[1] and tci[0] > 0,
          f"n={len(tmoves)} mean {tmean:+.2f}pt over {DRIFT_MIN}m, CI [{tci[0]:+.2f}, {tci[1]:+.2f}]"
          f" ⊇ planted {DEFAULT_EFFECT_PT:+.1f}pt")

    # ★ 2b — the WEAKER, separate claim: what a rule can actually recover. Diluted by firings
    # inside a running drift, so it is expected BELOW the planted size — the requirement is only
    # that it is detectably positive. Stated as its own row so the two are never conflated.
    moves = _moves(planted, lambda d, b: rule_planted_signal(b))
    mci = _day_ci(moves)
    mmean = sum(v for _, v in moves) / len(moves)
    check("the rule RECOVERS a positive effect (weaker claim — dilution is expected)",
          mci[0] > 0,
          f"n={len(moves)} mean {mmean:+.2f}pt, CI [{mci[0]:+.2f}, {mci[1]:+.2f}]"
          f" vs planted {DEFAULT_EFFECT_PT:+.1f}pt"
          f" ({'diluted, as expected' if mmean < DEFAULT_EFFECT_PT else 'ABOVE planted — investigate'})")
    fmoves = _moves(free, lambda d, b: rule_planted_signal(b))
    check_null("★ the SAME signal on the edge-free tape returns null", fmoves,
               TOL_SIGNAL_PT, "pt")

    print("── 3. the confound rule really is confounded (else check 4 proves nothing) ──")
    pos = []
    for d, bars in free.items():
        for i, side in rule_price_extreme(bars):
            lo = max(0, i - 30)
            window = [b["close"] for b in bars[lo:i + 1]]
            e = bars[i]["close"]
            better = (sum(1 for x in window if x > e) if side == "long"
                      else sum(1 for x in window if x < e))
            pos.append((d, better / len(window)))
    pmean = sum(v for _, v in pos) / len(pos)
    check("entry-price position is extreme, on a tape with NO edge",
          pmean > 0.9,
          f"n={len(pos)} mean favourable-position {pmean:.3f} (chance 0.5)")

    print("── 4. structural integrity every vendor bar must also satisfy ──")
    allbars = [b for bs in list(free.values()) + list(planted.values()) for b in bs]
    bad = [b for b in allbars
           if not (b["low"] <= min(b["open"], b["close"])
                   and max(b["open"], b["close"]) <= b["high"])]
    check("OHLC coherence", not bad, f"{len(allbars) - len(bad)}/{len(allbars)} bars coherent")
    flat = [b for b in allbars if b["high"] == b["low"]]
    check("no FLAT bars", not flat, f"{len(flat)} flat of {len(allbars)} (vendor padding shape)")
    stamps = [b["time"] for b in free[sorted(free)[0]]]
    check("RTH grid is exactly 390 one-minute bars",
          len(stamps) == RTH_MINUTES and all(stamps[i + 1] - stamps[i] == 60
                                             for i in range(len(stamps) - 1)),
          f"{len(stamps)} bars, contiguous")
    t0 = datetime.datetime.fromtimestamp(stamps[0], ET).time()
    check("first bar is 09:30 ET (DST resolved per date, not a fixed offset)",
          t0 == RTH_OPEN, f"{t0}")

    print("── 5. determinism (a failing check must be reproducible from its seed) ──")
    again = make_corpus(days, seed, 0.0)
    check("same seed ⇒ byte-identical corpus",
          json.dumps(free, sort_keys=True) == json.dumps(again, sort_keys=True), "re-generated")
    other = make_corpus(days, seed + 1, 0.0)
    check("different seed ⇒ different corpus",
          json.dumps(free, sort_keys=True) != json.dumps(other, sort_keys=True), "seed binds")

    print()
    print(f"  {'PASS' if ok else 'FAIL'} — {days} days/kind, seed {seed}")
    if ok:
        print("  ⚠ BOUND, stated with the verdict per the header: this proves the generator is a"
              " known null\n    IN ITS OWN MODEL (Gaussian walk). It does not prove any scorer is"
              " calibrated on real\n    microstructure — that is the vendor corpus and the shadow"
              " phase, not this file.")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("emit")
    e.add_argument("--kind", choices=["edge_free", "planted"], required=True)
    e.add_argument("--days", type=int, default=20)
    e.add_argument("--seed", type=int, default=20260811)
    e.add_argument("--effect-pt", type=float, default=DEFAULT_EFFECT_PT)
    e.add_argument("--out")
    v = sub.add_parser("verify")
    v.add_argument("--days", type=int, default=DEFAULT_VERIFY_DAYS)
    v.add_argument("--seed", type=int, default=20260811)
    a = ap.parse_args()

    if a.cmd == "emit":
        corpus = make_corpus(a.days, a.seed, a.effect_pt if a.kind == "planted" else 0.0)
        blob = json.dumps({"kind": a.kind, "seed": a.seed, "days": a.days,
                           "effect_pt": a.effect_pt if a.kind == "planted" else 0.0,
                           "src": "SYNTHETIC", "corpus": corpus}, sort_keys=True)
        if a.out:
            os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
            with open(a.out, "w") as fh:
                fh.write(blob)
            print(f"wrote {a.out}: {a.kind}, {a.days} days × {RTH_MINUTES} bars, seed {a.seed}")
        else:
            print(blob)
        return 0
    return 0 if verify(a.days, a.seed) else 1


if __name__ == "__main__":
    sys.exit(main())
