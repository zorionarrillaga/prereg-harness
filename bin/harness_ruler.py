#!/usr/bin/env python3
"""harness_ruler.py — THE RULER. One bar walker, one interval form, nothing else.

Two rulers is the failure mode this module exists to prevent. When a walker lives in the
backtest AND a near-copy lives in the scorer, a verdict can move because the ruler changed
rather than because the tape did, and no test in the suite can see the difference. So the
walk lives here, once, and every caller delegates to it.

Three functions, and they are load-bearing in this order:

  walk_bounds()          the floor and the ceiling of one trade, read off the tape with no
                         policy assumed and no look-ahead available
  cluster_bootstrap_ci() the registered interval: resample DAYS, never decisions
  excludes_half()        the one-line verdict helper the scorer's percentile arm reads

Everything here is pure. No I/O, no globals that a caller can move, no clock. That is what
makes it safe to be the single ruler.
"""
import collections
import random
import statistics as st

# The registered interval: resample DAYS with replacement. Seeded separately from any placebo
# draw so that changing the pool size K does not silently move every CI in the repo.
BOOT_REPS = 3000
BOOT_SEED = 20260811


def walk_bounds(bars, entry_ts, entry_px, sl_px, r_denom, side, tp, exit_ts):
    """FLOOR + CEILING for one trade from the tape. Pure; no policy assumed.

    Returns (info, err). Bars are 1m dicts with keys time/open/high/low/close, minute-deduped,
    sorted ascending.

    Walk starts at the first bar STRICTLY AFTER the entry minute — the entry bar's range had
    already partly elapsed when the fill happened, so crediting its extremes would hand the
    ruler excursion that was never available.

    SL-FIRST within a bar (pessimistic, binding): a bar containing both SL and TP resolves SL.
    The favourable excursion of the TERMINATING bar is NOT credited — within a 1m bar we cannot
    know whether the favourable extreme preceded or followed the stop, so we refuse to assume
    the flattering order. This single choice is worth more than any parameter in the harness:
    the optimistic convention is undetectable by eye and inflates every result it touches.
    """
    if not bars:
        return None, "no_tape"
    if not r_denom:
        return None, "no_sl_pt"
    long = side == "long"
    # ★ THE STOP IS AN EXPLICIT PRICE, NOT A DISTANCE. An earlier version derived it as
    # entry ∓ intended_sl_pt, and one hand-checked fill showed why that is wrong: the fill row
    # carried an intended stop distance of 68.0pt AND an actual submitted stop 35.6pt from the
    # fill. The walk placed the stop 68pt away, never hit it, ran to target and scored +2.34R
    # against a reality that stopped out at −0.52R — and the whole 2.86R difference was being
    # attributed to "management". It was not management. R stays denominated by `r_denom` (the
    # INTENDED stop distance) so every leg remains comparable across candidates regardless of
    # where the stop actually sat.
    sl = sl_px
    if (long and sl >= entry_px) or ((not long) and sl <= entry_px):
        return None, "degenerate"
    # ━━ `tp` MAY BE A CALLABLE: bar -> price or None (a MOVING target) ━━━━━━━━━━━━━━━━━━━━
    # Needed by any candidate whose registered target is recomputed each bar (a VWAP-reversion
    # rule, say). The alternative was a second walker, and this module's whole design is that
    # there is exactly ONE ruler.
    #
    # ⚠ THE SCALAR PATH IS UNCHANGED, and that is the property that matters. A scalar `tp`
    # takes exactly the branches it took before: same degenerate guard, same per-bar compare,
    # same terminator price. Only a callable reaches the new code.
    #
    # A callable skips the entry-time degenerate guard BY DESIGN: a moving target's side is a
    # per-bar property, not an entry-time one, so it is enforced per bar below. The CALLER is
    # responsible for not entering when the target is already through entry.
    tp_is_fn = callable(tp)
    if tp is not None and not tp_is_fn:
        if (long and not (tp > entry_px)) or ((not long) and not (tp < entry_px)):
            return None, "degenerate"

    after = [b for b in bars if b["time"] > entry_ts]
    if not after:
        return None, "no_bars_after_entry"

    def r_of(px):
        return (px - entry_px) / r_denom if long else (entry_px - px) / r_denom

    best = entry_px          # running favorable extreme, EXCLUDING the terminating bar
    worst = entry_px
    term = None              # ("SL"|"TP"|"EOD", price, bar_time)
    srcs = set()
    for b in after:
        srcs.add(b.get("src", "?"))
        sl_hit = (b["low"] <= sl) if long else (b["high"] >= sl)
        # tp_px is the target AS OF THIS BAR. For a scalar it is the same value every bar, so
        # this is the identical comparison the scalar path always made.
        tp_px = tp(b) if tp_is_fn else tp
        tp_hit = (tp_px is not None) and ((b["high"] >= tp_px) if long else (b["low"] <= tp_px))
        if sl_hit:
            term = ("SL", sl, b["time"])
            break
        if tp_hit:
            term = ("TP", tp_px, b["time"])
            break
        fav = b["high"] if long else b["low"]
        adv = b["low"] if long else b["high"]
        if r_of(fav) > r_of(best):
            best = fav
        if r_of(adv) < r_of(worst):
            worst = adv
    if term is None:
        last = after[-1]
        term = ("EOD", float(last["close"]), last["time"])

    # ⚠ COVERAGE. If the real trade closed after our tape ends, the ceiling is truncated and the
    # row must not score. Judged against the LAST BAR WE HAVE, not against the terminator we
    # computed — an EOD terminator on a short tape is exactly the silent-truncation case.
    if exit_ts is not None and after[-1]["time"] + 60 < exit_ts and term[0] == "EOD":
        return None, "hold_uncovered"

    r_static = r_of(term[1])
    # The ceiling cannot be below the floor: when the terminator IS the best available (a clean
    # target hit, or a stop with no favourable excursion at all), ceiling == floor and there is
    # no management headroom to attribute. Those rows are excluded from any capture ratio by
    # construction — dividing by a zero interval is where a capture ratio invents information.
    r_mfe = max(r_of(best), r_static)
    return {
        "r_static": round(r_static, 4),
        "r_mfe": round(r_mfe, 4),
        "r_mae": round(r_of(worst), 4),
        "terminator": term[0],
        # The terminating bar's timestamp. A "no stacking — flat before the next signal" rule
        # needs the real exit time, and the alternative (assume every trade runs the full hold)
        # would understate the firing RATE, which is the load-bearing quantity in any rate gate.
        "exit_ts": term[2],
        "bars_walked": len(after),
        "srcs": sorted(srcs),
    }, None


def cluster_bootstrap_ci(pairs, weight="decision", reps=BOOT_REPS, seed=BOOT_SEED):
    """★ THE REGISTERED INTERVAL: resample DAYS with replacement, not decisions.

    `pairs` is [(day, value)]. A day is one draw of one tape and the decisions inside it share
    everything — the same open, the same trend, the same news. Treating them as independent is
    what produced a ±0.048 interval where the day-clustered form gives ±0.055 and, on one arm,
    a DIFFERENT ANSWER to the only question being asked.

    weight="decision" gives every decision one vote. weight="day" gives every DAY equal weight.
    They are DIFFERENT ESTIMANDS, not two takes on one number, so both are returned and the
    caller must show both when they disagree.

    Returns None when there are too few days to resample — a one-day bootstrap resamples the
    same day forever and returns a zero-width interval, which would read as certainty.
    """
    byday = collections.defaultdict(list)
    for d, v in pairs:
        byday[d].append(v)
    days = sorted(byday)
    if len(days) < 2:
        return None
    rng = random.Random(seed)
    stats = []
    for _ in range(reps):
        samp = [days[rng.randrange(len(days))] for _ in days]
        if weight == "day":
            stats.append(st.mean([st.mean(byday[d]) for d in samp]))
        else:
            stats.append(st.mean([v for d in samp for v in byday[d]]))
    stats.sort()
    return [stats[int(0.025 * reps)], stats[min(reps - 1, int(0.975 * reps))]]


def excludes_half(ci):
    """Does this interval exclude the chance percentile? None (no interval) is never a verdict."""
    return ci is not None and not (ci[0] <= 0.5 <= ci[1])


# Kept under its historical private name so a lifted call site reads identically.
_excl = excludes_half
