#!/usr/bin/env python3
"""factory_surrogate_arm.py — the RULE-SELECTED placebo. The one untried family (F129).

━━ WHY EVERY EXISTING ARM FAILS, STATED AS ONE SENTENCE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`uniform`, `time` and `price` are all POOL arms: they hold the tape fixed and choose a different
ENTRY MINUTE to compare against. So the candidate's entry was chosen BY THE RULE and the placebo's
entry was chosen BY THE POOL — the two sides differ in **how the entry was selected** as well as
in when it happened. That is the project's own law, already published on the case-study page:

    "a control group that differs from the treatment in more than one way
     measures the difference you did not intend."

All three arms are REJECTED at 400 days, fully powered, on synthetic AND US500 AND US100 (F030,
F031), and four repairs aimed at the pool have been measured and killed (R1 FOLD 1 TERMINAL,
PRICE_BAND tuning FORBIDDEN, epp-parameterised F038, past/future exchangeability F034).

━━ WHAT THIS ARM DOES DIFFERENTLY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
It holds the SELECTION MECHANISM fixed and varies the TAPE. For each placebo draw it builds a
surrogate day, **re-runs the candidate's own rule on it**, and walks an entry the rule chose there.
Both sides are now rule-selected; they differ only in which tape realisation they met.

There is no pool, no price band, no time window — so none of the four dead repairs reaches it, and
neither does the free parameter (`PRICE_BAND`) whose monotone null started this whole contract.

━━ THE SURROGATE, AND WHAT IT PRESERVES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A **circular rotation of the day's close-to-close increments**, re-integrated from the real open.
Rotation is used rather than a shuffle because it preserves the increment autocorrelation almost
entirely — a shuffled day would be an i.i.d. tape, which is a strictly easier null and would
flatter the arm.

Each bar keeps its OWN intrabar shape: `high - close` and `low - close` are carried across and
re-applied to the new close, so a surrogate bar can never be internally inconsistent (a high below
its close would silently change every stop-hit test in `walk_trade`).

⚠ WHAT THE ROTATION EXCLUDES, named because a derived constraint that is not named is the L026
defect: re-integrating increments makes the LEVEL path a construction, so session-scale trend and
the true location of the day's high/low are only partly preserved. Any rule conditioning on the
absolute level, or on where price sits within the day's realised range, is therefore under-tested
by this arm — the same bound `PREREG_realtape_null` §7.2 carries for its block bootstrap. The
alternative it rules out is a level-preserving surrogate (e.g. block-permuting whole sessions),
which preserves level but destroys the within-day increment structure the rules actually read.

⚠ AND: qualifying here is NECESSARY, NEVER SUFFICIENT (`factory_slope_test`'s own standing
caveat). This module ships no verdict of its own — it is judged by the acceptance criterion, on
two structurally different rules, exactly like every arm before it.

━━ ⚠ THIS MODULE SHIPPED WITH ZERO EXECUTABLE ASSERTIONS (repaired 2026-08-13, F132) ━━━━━━━━
Everything above was a claim in prose: nothing would have caught an edit to the rotation, to the
intrabar carry, or to the offset draw. `selftest` below now measures each of them — including the
one with teeth: **offset 0 reproduces the real day EXACTLY**, which is why `day_pool` draws from
`randrange(1, …)`. A mutation to that lower bound puts verbatim copies of the candidate's own tape
into its placebo pool, and every percentile would drift toward 0.5 for the most flattering possible
reason. Run: `python3 bin/factory_surrogate_arm.py selftest`.

⚠ AND NOTE WHAT THE SELFTEST CANNOT SAY: these are INTERNAL invariants — that the surrogate is the
tape this module claims to build. Whether that tape is a valid PLACEBO is a separate question,
answered by `factory_slope_test`, and for this arm the answer is NO (F131/F133: the rotation is a
bijection on cyclic index, both probes read only differences of closes, so 94.9% of outcomes came
back bit-identical to the trade they were relabelled from — 1286/1286 after the range-direction
fix). A green selftest here does not resurrect the arm.
"""
import random


def surrogate_day(bars, offset):
    """One rotated day. Increments rotated by `offset`, re-integrated from the real first close.

    Intrabar shape (high-close, low-close) travels WITH its bar, so bar internals stay consistent.
    `time` is untouched — the clock is real, only the path is surrogate.
    """
    n = len(bars)
    if n < 3:
        return None
    closes = [float(b["close"]) for b in bars]
    incs = [closes[i + 1] - closes[i] for i in range(n - 1)]
    m = len(incs)
    off = offset % m
    rot = incs[off:] + incs[:off]

    out = [dict(bars[0])]
    px = closes[0]
    for i, d in enumerate(rot):
        src = bars[i + 1]
        c0 = float(src["close"])
        px += d
        b = dict(src)
        b["close"] = px
        # carry each bar's own excursions so the walker's stop tests stay meaningful
        if "high" in src:
            b["high"] = px + (float(src["high"]) - c0)
        if "low" in src:
            b["low"] = px + (float(src["low"]) - c0)
        out.append(b)
    return out


def day_pool(bars, rule, walk, k, rng, geo):
    """The k rule-selected surrogate outcomes for ONE DAY. Built once, reused by every candidate.

    ★ THE POOL IS A PROPERTY OF THE DAY, NOT OF THE CANDIDATE, and that is not merely an
    optimisation. The placebo here is "what would this rule have got on a different realisation of
    this day" — the rule chooses its own entry index AND its own side on the surrogate, so nothing
    about the candidate enters except the trade geometry, which is fixed for a whole run. Building
    it per candidate would have re-drawn the same distribution thousands of times per day and made
    400-day runs unaffordable (the first version did exactly that and had to be killed).

    ⚠ Every candidate on a day is therefore ranked against the SAME pool, which correlates their
    percentiles within the day. That is already the interval's assumption — `summarize` clusters
    the bootstrap ON DAY — so it is handled, not ignored. It would be a real defect under a naive
    i.i.d. interval, and this arm must never be reported with one.
    """
    pool = []
    n = len(bars)
    for _ in range(k):
        sur = surrogate_day(bars, rng.randrange(1, max(2, n - 1)))
        if sur is None:
            continue
        try:
            entries = rule(sur)
        except Exception:
            continue
        if not entries:
            continue                      # the rule fired nowhere on this surrogate
        idx, side = entries[rng.randrange(len(entries))]
        p, err = walk(sur, idx, side, geo["sl_pt"], geo["tp_r"],
                      geo["max_hold_min"], geo["cost_band"], sym=geo.get("sym"))
        if err or p["hold_truncated"]:
            continue
        pool.append(p["r_gross"])
    return pool


def rank_against(row, pool):
    """Mid-rank percentile of the realised outcome within the surrogate pool."""
    below = sum(1 for x in pool if x < row["r_gross"])
    ties = sum(1 for x in pool if x == row["r_gross"])
    return (below + 0.5 * ties) / len(pool)


def rank_all(rows, corpus, rule, walk, k, seed, sl_key="sl_pt", min_pool=10, pool_sink=None):
    """`placebo_rank`'s contract for this arm: -> ([(day, percentile)], dropout counter).

    ⚠ THE GEOMETRY IS TAKEN FROM THE FIRST ROW AND THEN ASSERTED ON EVERY OTHER ROW. The day-level
    pool is only valid if every candidate shares one geometry; a mixed-geometry call would rank
    candidates against a pool walked under someone else's stop, which is precisely the
    "differs in more than one way" defect this arm exists to remove. It raises rather than
    silently averaging over it.
    """
    rng = random.Random(seed)
    pairs, dropout = [], {}
    if not rows:
        return pairs, dropout
    # ⚠ MOVING TARGETS ARE REFUSED OUTRIGHT, not merely compared (D030 seat, 2026-08-13).
    # The guard below originally compared (sl_pt, tp_r, max_hold_min) only. A moving-target row
    # carries `tp_r: None` with `tp_moving: True` (`factory_backtest.py:285`) — which is how EVERY
    # C2 row is built (`factory_c2.py:308`, tp_fn=VWAP-by-time). A homogeneous run of those rows
    # passed the guard with `geo["tp_r"] = None`, so the placebos were walked WITH NO TARGET AT ALL
    # while the candidate exited on its per-bar VWAP: "ranked against a pool walked under someone
    # else's stop", which is precisely what this guard's docstring says it exists to refuse. The
    # day-level pool cannot carry a per-candidate moving target, so the honest answer is refusal.
    if any(r.get("tp_moving") for r in rows):
        raise ValueError("the 'surrogate' arm cannot rank MOVING-TARGET candidates: the placebo "
                         "pool is cached per DAY and cannot carry a per-candidate tp_fn, so the "
                         "placebos would be walked with no target while the candidate exits on "
                         "its own moving one. Refused rather than silently mismatched.")
    geo = {"sl_pt": rows[0][sl_key], "tp_r": rows[0].get("tp_r"),
           "max_hold_min": rows[0].get("max_hold_min"),
           "cost_band": rows[0].get("cost_band", "central"),
           # the surrogate is a reshuffle of the SAME instrument, so it inherits that row's
           # cost basis rather than making a second, independent choice about it
           "sym": rows[0].get("cost_sym")}
    cache = {}
    for r in rows:
        if (r[sl_key], r.get("tp_r"), r.get("max_hold_min")) != \
           (geo["sl_pt"], geo["tp_r"], geo["max_hold_min"]):
            raise ValueError("the 'surrogate' arm caches one placebo pool per DAY, which assumes a "
                             "single trade geometry across the run; this call mixes geometries "
                             f"({geo['sl_pt']}/{geo['max_hold_min']} vs "
                             f"{r[sl_key]}/{r.get('max_hold_min')})")
        day = r["day"]
        if day not in cache:
            cache[day] = day_pool(corpus[day], rule, walk, k, rng, geo)
        pool = cache[day]
        if len(pool) < min_pool:     # below this a percentile is not a percentile
            dropout["surrogate_pool_too_small"] = dropout.get("surrogate_pool_too_small", 0) + 1
            continue
        pairs.append((day, rank_against(r, pool)))
        if pool_sink is not None:
            # candidate-weighted, per `placebo_rank`'s contract: this day's pool is cached and
            # shared, so it lands once per candidate it actually ranked — never once per day.
            pool_sink.extend(pool)
    return pairs, dropout


# ── selftest: the surrogate's invariants, MEASURED (F132, 2026-08-13) ───────────────────────

class _RecordingRandom(random.Random):
    """A Random that remembers the ARGUMENTS it was asked for. The offset draw's lower bound is
    a load-bearing constant (0 would emit the real day as a placebo), and a bound is only
    testable if the call that uses it is observable."""

    def __init__(self, seed):
        super().__init__(seed)
        self.randrange_args = []

    def randrange(self, *a, **kw):
        self.randrange_args.append(a)
        return super().randrange(*a, **kw)


def selftest():
    """Every assertion here is one a mutation could break. None of them read a docstring."""
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import factory_synthetic as fs                       # noqa: E402
    import factory_backtest as fb                        # noqa: E402
    ok = True

    def check(name, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  {'✓' if passed else '✗'} {name}{': ' + detail if detail else ''}")

    bars = fs.make_tape("2026-01-05", 1, 0.0)
    closes = [float(b["close"]) for b in bars]
    incs = sorted(closes[i + 1] - closes[i] for i in range(len(closes) - 1))

    print("── offset 0 IS the real day — which is why day_pool draws from 1 ──")
    ident = surrogate_day(bars, 0)
    check("offset 0 reproduces every close bit-identically",
          [float(b["close"]) for b in ident] == closes,
          f"{len(closes)} closes")
    rec = _RecordingRandom(7)
    geo = {"sl_pt": 20.0, "tp_r": None, "max_hold_min": 30, "cost_band": "none",
           "sym": fb.SYNTHETIC}
    day_pool(bars, fs.rule_dumb, fb.walk_trade, 5, rec, geo)
    lows = [a[0] for a in rec.randrange_args if len(a) == 2]
    check("the offset draw's lower bound is ≥1, never 0",
          bool(lows) and all(lo >= 1 for lo in lows),
          f"lower bounds drawn: {sorted(set(lows))}")

    print("── the rotation is a PERMUTATION of the day's increments, not a redraw ──")
    sur = surrogate_day(bars, 137)
    sc_ = [float(b["close"]) for b in sur]
    check("increment multiset is preserved exactly",
          sorted(sc_[i + 1] - sc_[i] for i in range(len(sc_) - 1)) == incs)
    check("re-integration starts from the REAL first close",
          sc_[0] == closes[0], f"{sc_[0]} == {closes[0]}")
    check("the path itself actually moved (offset ≠ 0 is not a no-op)",
          sc_ != closes)
    check("length and clock are untouched",
          len(sur) == len(bars) and all(a["time"] == b["time"] for a, b in zip(sur, bars)))

    print("── intrabar shape travels WITH its bar (walk_trade's stop tests stay meaningful) ──")
    dh = [abs((float(s["high"]) - float(s["close"])) - (float(b["high"]) - float(b["close"])))
          for s, b in zip(sur[1:], bars[1:])]
    dl = [abs((float(s["close"]) - float(s["low"])) - (float(b["close"]) - float(b["low"])))
          for s, b in zip(sur[1:], bars[1:])]
    check("high−close carried on every bar", max(dh) < 1e-9, f"max drift {max(dh):.2e}")
    check("close−low carried on every bar", max(dl) < 1e-9, f"max drift {max(dl):.2e}")
    check("no surrogate bar is internally inconsistent (low ≤ close ≤ high)",
          all(float(b["low"]) <= float(b["close"]) <= float(b["high"]) for b in sur))

    print("── the guards REFUSE rather than silently mismatch ──")
    check("a day shorter than 3 bars returns None", surrogate_day(bars[:2], 1) is None)
    corpus = {"2026-01-05": bars}
    rows, _ = fb.backtest(corpus, fs.rule_dumb, 20.0, None, 30, "none", sym=fb.SYNTHETIC)
    if len(rows) < 2:
        check("enough rows to exercise the guards", False, f"n={len(rows)}")
    else:
        moving = [dict(r) for r in rows]
        moving[0]["tp_moving"] = True
        try:
            rank_all(moving, corpus, fs.rule_dumb, fb.walk_trade, 5, 3)
            check("a MOVING-TARGET row is refused", False, "no raise")
        except ValueError as e:
            check("a MOVING-TARGET row is refused", "moving" in str(e).lower())
        mixed = [dict(r) for r in rows]
        mixed[-1]["sl_pt"] = mixed[-1]["sl_pt"] + 5
        try:
            rank_all(mixed, corpus, fs.rule_dumb, fb.walk_trade, 5, 3)
            check("a MIXED-GEOMETRY run is refused", False, "no raise")
        except ValueError as e:
            check("a MIXED-GEOMETRY run is refused", "geometr" in str(e).lower())

        print("── pool_sink OBSERVES: same seed, same pairs, with it and without ──")
        p_a, _ = rank_all(rows, corpus, fs.rule_dumb, fb.walk_trade, 12, 5)
        sink = []
        p_b, _ = rank_all(rows, corpus, fs.rule_dumb, fb.walk_trade, 12, 5, pool_sink=sink)
        check("pairs are bit-identical with the sink attached", p_a == p_b,
              f"{len(p_a)} pair(s)")
        # ⚠ THIS ASSERTION USED TO BE A MODULUS AND IT WAS VACUOUS (D030 seat, 2026-08-13).
        # It read `len(sink) % len(pairs) == 0`, and with 12 candidates over 1 day a mutant that
        # sank `pool[:1]` gives 12 % 12 == 0 — GREEN while discarding 91.7% of the absorption
        # numerator. The sink's whole job is to make `pool_gain` commensurate with `cand_gain`,
        # so the count has to be checked against the pools that were actually built, recomputed
        # here rather than inferred from a remainder.
        # The recompute must NOT read the sink, or a mutation corrupts both sides equally and
        # cancels. `day_pool` is called with a fresh Random(5) — rank_all's own seed, in its
        # initial state — which reproduces this single-day corpus's pool draw for draw.
        geo_c = {"sl_pt": rows[0]["sl_pt"], "tp_r": rows[0].get("tp_r"),
                 "max_hold_min": rows[0].get("max_hold_min"),
                 "cost_band": rows[0].get("cost_band", "central"),
                 "sym": rows[0].get("cost_sym")}
        pool_c = day_pool(corpus[rows[0]["day"]], fs.rule_dumb, fb.walk_trade, 12,
                          random.Random(5), geo_c)
        want = len(p_b) * len(pool_c)        # one pool per DAY, extended once per ranked candidate
        check("the sink holds EVERY placebo R that ranked — recomputed, not a remainder",
              len(sink) == want and want > 0,
              f"{len(sink)} sunk vs {want} = {len(p_b)} candidate(s) × pool {len(pool_c)}")
        # ★ THE ONE A MUTATION SURVIVED (2026-08-13, caught by the mutation harness before this
        # shipped): every pool above passes the size gate, so "extend BEFORE the check" was
        # indistinguishable from "extend after". Force the gate to reject everything — a pool
        # that buys no percentile must buy no R either, or the absorption denominator silently
        # includes placebos the null never saw.
        sink_rej = []
        p_c, _ = rank_all(rows, corpus, fs.rule_dumb, fb.walk_trade, 12, 5,
                          min_pool=10 ** 6, pool_sink=sink_rej)
        check("a pool too small to RANK contributes nothing to the sink",
              p_c == [] and sink_rej == [],
              f"{len(p_c)} pair(s), {len(sink_rej)} value(s) sunk")

    print("── rank_against is a MID-rank (ties split), not a strict one ──")
    check("all-below → 1.0", rank_against({"r_gross": 9.0}, [0.0, 1.0]) == 1.0)
    check("all-above → 0.0", rank_against({"r_gross": -9.0}, [0.0, 1.0]) == 0.0)
    check("a tie contributes one half", rank_against({"r_gross": 1.0}, [0.0, 1.0]) == 0.75)

    print(f"\n{'✓ SELFTEST PASSED' if ok else '✗ SELFTEST FAILED'}")
    return ok


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) > 1 and _sys.argv[1] == "selftest":
        _sys.exit(0 if selftest() else 1)
    print(__doc__)
    print("verbs:\n  selftest    the surrogate's invariants, measured not asserted")
    _sys.exit(0)
