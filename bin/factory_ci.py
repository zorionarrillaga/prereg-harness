#!/usr/bin/env python3
"""factory_ci.py — the interval form for candidates that HOLD ACROSS DAYS, and the coverage
harness that decides whether the incumbent form needs replacing.

━━ THE PROBLEM, STATED BEFORE IT IS MEASURED ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The charter's registered interval is `harness_ruler.cluster_bootstrap_ci` — resample DAYS with
replacement, because the decisions inside one day share the same open, trend and news. That is
correct for every candidate the factory has judged so far, because all of them CLOSE THE DAY
THEY OPEN.

C4 does not. It holds 2-5 trading days across 8 instruments, and the dependence it creates is
NOT the one day-clustering removes:

  · WITHIN an instrument there is no overlap at all — C4 §3 forbids re-entry while open.
  · ACROSS instruments there is. US500 entered Monday (held to Wednesday) and US100 entered
    Tuesday (held to Thursday) share Tuesday and Wednesday's tape, and four of C4's eight
    instruments are correlated equity indices, so those shared days are shared SHOCKS.

Day-clustering puts same-day entries in one cluster and therefore handles the first-order case.
It cannot see the second: two trades entered on DIFFERENT days land in DIFFERENT clusters and
are resampled as if independent, while in truth they overlap on correlated tape.

★ AND THE ERROR RUNS TOWARD A FALSE ALIVE. Unmodelled positive dependence makes the resampled
spread too small, so the interval is too NARROW, so "CI excludes 0" fires more often than 5% of
the time under the null. Every other item in the C4 audit pushes toward failing the candidate;
this one pushes toward passing it, which is why it is measured rather than argued about.

━━ WHAT THIS MODULE REFUSES TO DO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
It does not decide that C4 will be judged with the new form. The interval form is part of how a
candidate is judged; changing it needs a registry row, and it must be registered BEFORE any C4
number exists or the choice is unfalsifiable. This module supplies the evidence for that row.

Verbs:
  record      the full evidence table for the C4 interval decision, in one file
  coverage    simulate C4's dependence and measure BOTH forms' true coverage vs the nominal 95%
  selftest    the estimators' invariants, and the positive control that proves the harness works
"""
import argparse
import json
import math
import os
import random
import statistics as st
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))
import harness_ruler as ca                     # noqa: E402  THE interval — one ruler, imported

BOOT_REPS = 2000
NOMINAL = 0.95

# ━━ THE RECOMMENDED BLOCK, AND WHAT IT DOES NOT DO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MEASURED (`coverage`, 300 realisations/hold, rho=0.6, 600-day book, true mean 0):
#
#   hold  day-clustered FP    block=H FP   block=2H FP        (nominal is 0.050)
#      1        0.057           0.057          —              ← positive control, at nominal
#      2        0.087           0.060          —
#      3        0.130           0.090        0.070
#      5        0.163           0.080        0.070
#
# ⇒ At H=5 the INCUMBENT's real false-positive rate is 16.3% against a stated 5% — 3.3x. That is
#   the false-ALIVE the C4 audit predicted, and it is larger than predicted.
#
# ★ AND THE FIX IS PARTIAL. At block=2H the rate is 0.053 (H=2), 0.070 (H=3), 0.070 (H=5).
#   Coverage PLATEAUS there: 3H and 4H buy nothing measurable.
#
# ⚠ WHAT THE RESIDUAL IS, HONESTLY. An earlier draft of this comment said the leftover ~1.5pp
#   was "leftover dependence, not finite-sample error". THAT WAS OVERSTATED AND IS RETRACTED.
#   The Monte-Carlo SE on each coverage figure is ~1.3pp at 300 trials, and the estimator's own
#   no-dependence baseline (rho=0, hold=1) came out 0.953 at 600 days and 0.937 at 1200 on one
#   seed and 0.945/0.950 on another — i.e. the baseline itself bounces across ~1.5pp. So the
#   residual at 2H is NOT resolved at this precision: it is somewhere between zero and ~2pp, and
#   separating it from Monte-Carlo noise would need several thousand trials, which has not been
#   run. The defensible claim is the one the numbers carry:
#
#     block=2H removes the LARGE, unambiguous inflation (16.3% -> 7.0% at H=5) and leaves a
#     residual too small to resolve here. It is not proven to restore the nominal 5%.
#
#   A C4 verdict turning on a CI boundary should be read with that stated.
BLOCK_MULTIPLE = 2


def recommended_block(hold_days):
    """Block length for a candidate holding `hold_days`. See BLOCK_MULTIPLE's measurement."""
    return max(1, int(BLOCK_MULTIPLE * hold_days))


# ── the estimators ──────────────────────────────────────────────────────────────────────────

def day_cluster_ci(pairs, reps=BOOT_REPS, seed=7):
    """The INCUMBENT, delegated to `harness_ruler.cluster_bootstrap_ci` rather than reimplemented.

    One ruler. A local copy would be a second interval, and this project has already paid for
    what two rulers cost (C2 v1's pooled number was VOID because it measured a ruler change).
    """
    return ca.cluster_bootstrap_ci(pairs, weight="decision", reps=reps, seed=seed)


def block_bootstrap_ci(pairs, block_days, reps=BOOT_REPS, seed=7):
    """MOVING-BLOCK bootstrap on the DAY axis: resample contiguous runs of `block_days` days.

    Day-clustering is the special case `block_days = 1`. Widening the block to span the hold
    keeps two trades that overlap in time inside the SAME resampling unit, so the dependence
    they actually have survives the resample instead of being assumed away.

    `pairs` is [(day, value)] with `day` an orderable key (ISO date or day index). Blocks are cut
    from the sorted, DISTINCT day axis — not from the trade list — because the dependence lives
    in the calendar, not in how many trades happened to fire.

    ⚠ Blocks are drawn with replacement and wrap circularly, so every day has equal probability
    of appearing. A non-circular version under-weights the first and last `block_days-1` days,
    which on a 12-year corpus is negligible and on a short one is not; the circular form has no
    such edge and costs nothing.

    Returns None when the day axis cannot support at least two blocks — resampling one block
    forever returns a zero-width interval, which would read as certainty. Same refusal the
    incumbent makes for a one-day bootstrap.
    """
    if block_days < 1:
        raise ValueError(f"block_days must be >= 1, got {block_days}")
    byday = {}
    for d, v in pairs:
        byday.setdefault(d, []).append(v)
    days = sorted(byday)
    D = len(days)
    if D < 2 or D < 2 * block_days:
        return None
    n_blocks = math.ceil(D / block_days)
    # Per-day (sum, count) precomputed once: a resampled mean is Σsum/Σcount, so the inner loop
    # is arithmetic instead of list concatenation. Identical estimator, ~2 orders faster — the
    # list form made a 4-hold coverage sweep infeasible, and an unaffordable measurement is one
    # that does not get made.
    dsum = [sum(byday[d]) for d in days]
    dcnt = [len(byday[d]) for d in days]
    rng = random.Random(seed)
    stats = []
    for _ in range(reps):
        tot = cnt = 0.0
        for _b in range(n_blocks):
            s = rng.randrange(D)
            for k in range(block_days):
                j = (s + k) % D
                tot += dsum[j]
                cnt += dcnt[j]
        if cnt:
            stats.append(tot / cnt)
    if len(stats) < 2:
        return None
    stats.sort()
    return [stats[int(0.025 * len(stats))], stats[min(len(stats) - 1, int(0.975 * len(stats)))]]


# ── the simulation: C4's dependence, and nothing else ───────────────────────────────────────

def simulate(rng, n_days=600, n_inst=8, hold=3, rate_per_day=0.134, rho=0.6):
    """One synthetic realisation of a TRUE NULL book shaped like C4. Returns [(day, R)].

    · `rho` — a single common factor across instruments: z = sqrt(rho)*f + sqrt(1-rho)*e. Four
      of C4's eight are equity indices and three are USD crosses, so a positive common factor is
      the realistic case, and §4 of the prereg says so before measuring it.
    · Per instrument, entries fire at `rate_per_day` and NEVER while a position is open — C4 §3.
      So all overlap in this book is CROSS-instrument, which is exactly the claim under test.
    · R for a trade = the sum of that instrument's daily shocks over its hold, scaled by
      sqrt(hold) so every hold length has unit variance and the comparison across H is fair.
    · ★ THE TRUE MEAN IS EXACTLY 0 BY CONSTRUCTION. There is no edge to find, so a 95% interval
      that excludes 0 more than 5% of the time is measuring its own error.
    """
    f = [rng.gauss(0, 1) for _ in range(n_days)]
    a, b = math.sqrt(rho), math.sqrt(1.0 - rho)
    z = [[a * f[d] + b * rng.gauss(0, 1) for d in range(n_days)] for _ in range(n_inst)]
    out = []
    for m in range(n_inst):
        d = 0
        while d < n_days - hold:
            if rng.random() < rate_per_day:
                r = sum(z[m][d:d + hold]) / math.sqrt(hold)
                out.append((d, r))
                d += hold                      # no re-entry while open (C4 §3)
            else:
                d += 1
    return out


def coverage(trials=400, hold=3, block_days=None, seed=20260812, reps=600, **kw):
    """Fraction of realisations whose 95% interval CONTAINS the true mean of 0.

    Nominal is 0.95. BELOW nominal ⇒ the interval is too narrow ⇒ the ALIVE test fires on noise
    more often than its stated 5%. Reported as the false-positive rate the judging rule would
    really run at, because that — not the coverage number — is the quantity a verdict rests on.
    """
    block_days = hold if block_days is None else block_days
    rng = random.Random(seed)
    hit_day = hit_blk = n = 0
    w_day, w_blk = [], []
    for t in range(trials):
        pairs = simulate(rng, hold=hold, **kw)
        if len(pairs) < 20:
            continue
        # The incumbent is evaluated as block_days=1, which the selftest pins as identical to
        # `harness_ruler.cluster_bootstrap_ci` on the same seed. Using the fast path here is what
        # makes a 4-hold sweep affordable; the equivalence is asserted, not assumed.
        cd = block_bootstrap_ci(pairs, 1, reps=reps, seed=seed + t)
        cb = block_bootstrap_ci(pairs, block_days, reps=reps, seed=seed + t)
        if cd is None or cb is None:
            continue
        n += 1
        hit_day += int(cd[0] <= 0.0 <= cd[1])
        hit_blk += int(cb[0] <= 0.0 <= cb[1])
        w_day.append(cd[1] - cd[0])
        w_blk.append(cb[1] - cb[0])
    if not n:
        raise SystemExit("no usable trials")
    return {
        "trials": n, "hold_days": hold, "block_days": block_days, "boot_reps": reps,
        "nominal_coverage": NOMINAL,
        "day_cluster": {"coverage": round(hit_day / n, 4),
                        "false_positive_rate": round(1 - hit_day / n, 4),
                        "mean_ci_width": round(st.mean(w_day), 5)},
        "block": {"coverage": round(hit_blk / n, 4),
                  "false_positive_rate": round(1 - hit_blk / n, 4),
                  "mean_ci_width": round(st.mean(w_blk), 5)},
        "width_ratio_block_over_day": round(st.mean(w_blk) / st.mean(w_day), 4),
    }


# ── selftest ────────────────────────────────────────────────────────────────────────────────

def selftest():
    ok = True

    def check(name, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  {'✓' if passed else '✗'} {name}{': ' + detail if detail else ''}")

    print("── block_days=1 IS day-clustering (the incumbent is the special case) ──")
    rng = random.Random(1)
    pairs = [(d, rng.gauss(0, 1)) for d in range(80) for _ in range(3)]
    a = day_cluster_ci(pairs, reps=4000, seed=99)
    b = block_bootstrap_ci(pairs, 1, reps=4000, seed=99)
    check("the two agree to within resampling noise at block_days=1",
          abs(a[0] - b[0]) < 0.02 and abs(a[1] - b[1]) < 0.02,
          f"day {a[0]:+.4f},{a[1]:+.4f} vs block1 {b[0]:+.4f},{b[1]:+.4f}")

    print("── both refuse rather than returning a zero-width interval ──")
    check("one day ⇒ None", day_cluster_ci([("d", 1.0)]) is None and
          block_bootstrap_ci([("d", 1.0)], 1) is None)
    check("a block longer than half the day axis ⇒ None",
          block_bootstrap_ci([(d, 1.0) for d in range(5)], 3) is None)

    print("── ★ THE POSITIVE CONTROL: with NO overlap, day-clustering is already correct ──")
    # hold=1 means every trade opens and closes inside its own day, which is the regime the
    # incumbent was registered for. If day-clustering under-covers HERE, the harness is broken
    # and every number it produces about overlap is worthless. This must come out at ~0.95.
    c1 = coverage(trials=200, hold=1, block_days=1, n_days=400, seed=5, reps=600)
    check("hold=1: day-clustered coverage is at nominal",
          c1["day_cluster"]["coverage"] >= 0.90,
          f"{c1['day_cluster']['coverage']:.3f} vs nominal 0.95")

    print("── ★ THE DISCRIMINATION: overlap really does break day-clustering ──")
    # The whole claim in one assertion, and it is FAILABLE: if C4-shaped overlap did not damage
    # the incumbent, these two numbers would sit on top of each other and this check would go
    # red. It is the check the positive control above exists to make believable.
    c5 = coverage(trials=150, hold=5, block_days=recommended_block(5), reps=400, seed=11)
    d_fp = c5["day_cluster"]["false_positive_rate"]
    b_fp = c5["block"]["false_positive_rate"]
    check("at hold=5 the day-clustered interval fires on noise far more than the block one",
          d_fp > b_fp + 0.04,
          f"day-cluster FP {d_fp:.3f} vs block FP {b_fp:.3f} (nominal 0.050)")
    check("…and the block interval is WIDER, which is the mechanism, not a coincidence",
          c5["width_ratio_block_over_day"] > 1.05,
          f"width x{c5['width_ratio_block_over_day']:.3f}")

    print("── the recommended block scales with the hold ──")
    check("block = 2 x hold, floored at 1",
          (recommended_block(3), recommended_block(5), recommended_block(0)) == (6, 10, 1))

    print("── the estimator is deterministic under a fixed seed ──")
    check("same seed ⇒ same interval",
          block_bootstrap_ci(pairs, 3, seed=4) == block_bootstrap_ci(pairs, 3, seed=4))
    check("different seed ⇒ different interval (it really is resampling)",
          block_bootstrap_ci(pairs, 3, seed=4) != block_bootstrap_ci(pairs, 3, seed=5))

    print()
    print(f"  {'PASS' if ok else 'FAIL'} — interval invariants")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    rc = sub.add_parser("record")
    rc.add_argument("--trials", type=int, default=300)
    rc.add_argument("--reps", type=int, default=600)
    rc.add_argument("--rho", type=float, default=0.6)
    rc.add_argument("--json")
    c = sub.add_parser("coverage")
    c.add_argument("--trials", type=int, default=400)
    c.add_argument("--reps", type=int, default=600)
    c.add_argument("--holds", default="1,2,3,5")
    c.add_argument("--rho", type=float, default=0.6)
    c.add_argument("--json")
    a = ap.parse_args()

    if a.cmd == "selftest":
        return 0 if selftest() else 1

    if a.cmd == "record":
        # The whole evidence table for the C4 interval decision, produced by ONE command so the
        # published numbers cannot drift from the ones a reader can regenerate.
        rec = {"rho": a.rho, "trials": a.trials, "boot_reps": a.reps,
               "nominal_coverage": NOMINAL, "block_multiple": BLOCK_MULTIPLE,
               "baseline_no_dependence": [], "by_hold": []}
        for nd in (600, 1200):
            b = coverage(trials=a.trials, hold=1, block_days=1, reps=a.reps, rho=0.0,
                         n_days=nd, seed=31)
            rec["baseline_no_dependence"].append(
                {"n_days": nd, "coverage": b["block"]["coverage"],
                 "false_positive_rate": b["block"]["false_positive_rate"]})
            print(f"  baseline rho=0 hold=1 n_days={nd}: coverage "
                  f"{b['block']['coverage']:.3f} (FP {b['block']['false_positive_rate']:.3f})")
        for h in (1, 2, 3, 5):
            row = {"hold": h, "arms": []}
            for L in sorted({1, h, recommended_block(h)}):
                r = coverage(trials=a.trials, hold=h, block_days=L, reps=a.reps, rho=a.rho)
                row["arms"].append({
                    "block_days": L,
                    "day_cluster_fp": r["day_cluster"]["false_positive_rate"],
                    "block_fp": r["block"]["false_positive_rate"],
                    "block_coverage": r["block"]["coverage"],
                    "width_ratio": r["width_ratio_block_over_day"]})
                print(f"  hold={h} block={L}: day-cluster FP "
                      f"{r['day_cluster']['false_positive_rate']:.3f} · block FP "
                      f"{r['block']['false_positive_rate']:.3f}")
            rec["by_hold"].append(row)
        out = a.json or os.path.join(ROOT, "research", "factory", "ci_coverage_c4.json")
        json.dump(rec, open(out, "w"), indent=2)
        print(f"wrote {out}")
        return 0

    rows = []
    print(f"\nCI COVERAGE under C4's dependence · common factor rho={a.rho} · "
          f"{a.trials} realisations per hold · TRUE MEAN = 0")
    print(f"  {'hold':>5} {'blk':>4} {'day-cluster':>12} {'FP rate':>8} | "
          f"{'block':>8} {'FP rate':>8} | {'width x':>8}")
    for h in (int(x) for x in a.holds.split(",")):
        r = coverage(trials=a.trials, hold=h, rho=a.rho, reps=a.reps)
        rows.append(r)
        flag = "  ← nominal" if h == 1 else ""
        print(f"  {h:>5} {r['block_days']:>4} {r['day_cluster']['coverage']:>12.3f} "
              f"{r['day_cluster']['false_positive_rate']:>8.3f} | "
              f"{r['block']['coverage']:>8.3f} {r['block']['false_positive_rate']:>8.3f} | "
              f"{r['width_ratio_block_over_day']:>8.3f}{flag}")
    print(f"\n  nominal coverage {NOMINAL} ⇒ a stated 5% false-positive rate.")
    print("  ⓘ simulation of C4's dependence, not a measurement of real tape.")
    if a.json:
        json.dump({"rho": a.rho, "trials": a.trials, "rows": rows}, open(a.json, "w"), indent=2)
        print(f"  wrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
