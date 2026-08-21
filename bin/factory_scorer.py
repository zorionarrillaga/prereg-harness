#!/usr/bin/env python3
"""factory_scorer.py — THE EDGE FACTORY, Phase 1: the placebo scorer, generalized.

Charter §3-Phase-1: *"a permutation/placebo scorer (the `harness_ruler.py` method generalized:
candidate entries vs random-minute entries matched on day/side/stop)."*

`harness_ruler.py` answers one question about one corpus: did the OPERATOR's chosen minutes beat
random minutes on our own session tapes. This module answers the same question about ANY
mechanical rule on ANY tape — vendor, synthetic, or ours — and it inherits every repair that
module took on 2026-08-11, because those repairs were not local bugs, they were the method:

  · **Paired per candidate, never pooled by day.** Every placebo inherits ITS OWN candidate's
    stop width. Pooling ranks a narrow-stop entry against wide-stop draws, and R is normalised
    by the stop, so a wider stop mechanically stops out less at the same price move.
  · **The percentile, not the mean.** With a stop and no take-profit every arm is heavy-tailed
    and the median R is −1.0 in all of them. A mean over that is noise with a decimal point.
  · **Day-clustered bootstrap as the registered interval.** Decisions inside a day share the
    open, the trend and the news; treating them as independent understates SE — anti-conservative
    in a design whose entire purpose is not fooling itself.
  · **Every dropout is counted.** An uncounted dropout reselects the arm. The differential
    dropout that made `harness_ruler`'s two arms into two differently-selected subsets was 16% vs
    40%, and it was invisible because nothing printed it.
  · **Forms that disagree are both shown.** Standing project rule (GL-56/57/58).

━━ THE PRICE-MATCHED ARM IS THE REGISTERED ONE FOR MECHANICAL RULES ━━━━━━━━━━━━━━━━━━━━━━━━━
Under this ruler the outcome is monotone in entry price: a long entered below its neighbours has
a nearer stop AND a longer run to the exit, so it dominates higher-entry longs in both branches,
with or without predictive structure. Any rule that enters at a local price extreme in its own
direction harvests arithmetic, and a time-matched percentile scores that as skill.

That is not a hypothetical. On 2026-08-11 the Phase-0a fork test returned a 0.725 survivor whose
CI cleared chance on the first attempt; its entry-price percentile was 0.857, correlation +0.85,
and price-matched it collapsed to 0.529. The whole ordering was entry-price arithmetic.

★ AND THE CONFOUND RUNS BOTH WAYS — measured here 2026-08-12, and NOT in the 08-11 record,
which documented only the manufacturing direction. `factory_synthetic.rule_planted_signal` is a
momentum rule: z > +1 means it buys a local price MAXIMUM, entry-price percentile **0.326**. On
an EDGE-FREE tape it therefore scores **0.3977, CI [0.3770, 0.4198]** on the time-matched arm —
a confident departure BELOW chance produced entirely by arithmetic — and **0.4988** once price
is matched. On the PLANTED tape the same rule reads 0.4722 time-matched (the price penalty
eating a real +6pt edge) against 0.5394 price-matched.

The consequence is not cosmetic: an unmatched arm can BURY a genuine edge as easily as it can
invent one, so a null on the time-matched arm is not evidence of no edge. **The registered
verdict is the price-matched arm, in both directions.**

So `ARM_REGISTERED = "price"`. The time-matched arm is retained and reported — a rule that is
null on BOTH arms is dead, and only the pair distinguishes "no edge" from "a scorer that cannot
see anything", which is check 4 of the not-blind gate.

━━ WHAT THE PERCENTILE IS AND IS NOT INVARIANT TO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Costs shift a candidate and its placebos by the SAME amount (they share sl_pt), so the
percentile is invariant to the cost band. This is a feature — selection quality should not be a
function of the spread — and a trap: **a percentile clearing 0.5 says a rule picks better
moments, NOT that it makes money.** Economic worth is the MUE test on net R, which is a
different statistic and lives with the verdict, never inside this number.

Verbs:
  selftest      positive / negative / anti controls on the known-null device
"""
import argparse
import collections
import json
import os
import random
import statistics as st
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))
import harness_ruler as ca                     # noqa: E402  THE interval — one ruler, imported
import factory_backtest as fb                  # noqa: E402  the one walker

SEED = 20260812                                # the placebo must be reproducible
K_DEFAULT = 40                                 # placebo draws per candidate
MIN_POOL = 10                                  # below this a percentile is not a percentile
WINDOW_MIN = 60                                # ±minutes for the time-matched arm
PRICE_BAND = 0.25                              # ±PRICE_BAND × sl_pt around the candidate's entry
ARMS = ("uniform", "time", "price")

# ★ THE RULE-SELECTED ARM IS DELIBERATELY *NOT* IN `ARMS`, and this is the second design that
# tried. Appending it there looked safe for RNG streams (uniform=0/time=1/price=2 keep their
# indices) — but `ARMS` is also the "every arm a caller can loop over" list, and `score()` /
# `selftest()` iterate it WITHOUT a rule to hand. The append made the pinned selftest raise
# instantly. That is the tuple doing its job: membership of `ARMS` is a promise that an arm is
# rule-agnostic, and this arm is not. It gets its own registry and its own RNG stream offset,
# far from any index `ARMS` will ever produce.
ARMS_RULE_SELECTED = ("surrogate",)
SURROGATE_STREAM = 100                         # cannot collide with any ARMS.index()
ARM_REGISTERED = "price"                       # see the module header — mechanical rules

# ★ WHEN IS AN ENTRY PRICE EXTREME ENOUGH TO CARRY THE RESULT? Derived from the 08-11 fork test,
# the only place this has been measured end to end, NOT chosen for taste. Three rules, their
# entry-price percentile and what price-matching did to their score:
#     0.857 (dev 0.357) → 0.725 collapsed to 0.529   ← material
#     0.361 (dev 0.139) → 0.388 lifted   to 0.484    ← material, the OTHER direction
#     0.590 (dev 0.090) → 0.580 moved    to 0.553    ← not material
# The band sits just above the largest deviation that did not matter. Symmetric, because the
# confound is bidirectional (module header): it buries edges as readily as it invents them.
CONFOUND_DEV = 0.15

# 80% power at α=0.05, two-sided: z(0.975) + z(0.80). The MDE is not decoration — charter §4.2
# REFUSES a null verdict that does not ship one, so "no edge found" can never harden into
# "there is no edge".
Z_MDE = 1.959964 + 0.841621


def _pool_idxs(bars, arm, row, rng):
    """Candidate minutes this row may be compared against, per arm.

    The candidate's OWN minute is deliberately left in. It contributes a draw identical to the
    candidate, which mid-ranks to exactly 0.5 and is therefore neutral; removing it would mean
    the candidate is compared only to minutes it was NOT, quietly stacking the pool against it.
    """
    n = len(bars)
    if arm == "uniform":
        return list(range(n))
    base = row["entry_ts"]
    win = [i for i in range(n) if abs(bars[i]["time"] - base) <= WINDOW_MIN * 60]
    if arm == "time":
        return win
    band = PRICE_BAND * row["sl_pt"]
    return [i for i in win if abs(float(bars[i]["close"]) - row["entry"]) <= band]


def placebo_rank(rows, corpus, arm, k=K_DEFAULT, seed=SEED, sl_key="sl_pt", rule=None,
                 pool_sink=None):
    """Rank each candidate against k placebo entries from its own day, side and stop.

    Returns (pairs, dropout). `pairs` is [(day, percentile)] — the day is carried because the
    interval clusters on it. `dropout` counts, by reason, every candidate that could not be
    ranked; a caller that does not report it is reselecting its own sample.

    ★ `pool_sink` — the POSITIVE CONTROL's window into the placebo side (F132, 2026-08-13).
    A percentile is scale-free, so it cannot answer "did the PLACEBOS also pocket the planted
    effect?" — and an arm that absorbs the effect into its own pool reads null on an edge-free
    tape AND null on a tape carrying a real edge, which is the failure mode that made every
    future QUALIFIES unearned. Pass a list and it is extended with the placebo `r_gross` values
    that were ACTUALLY used to rank (pools rejected for size contribute nothing, exactly as they
    contribute no percentile). Observation only: it draws nothing, consumes no RNG, and changes
    no verdict — measured by `selftest`, which runs the same seed with and without it and
    requires bit-identical pairs. Values are CANDIDATE-WEIGHTED (a day's pool appears once per
    candidate ranked against it), matching the candidate side it is differenced against.
    """
    # ★ ONE RNG STREAM PER ARM. `harness_ruler` shared one stream across arms and adding a third
    # arm silently moved the first one's mean (+0.316 → +0.361), because arm B's draws now came
    # between arm A's. "Seeded and reproducible" was true only until the next arm was added.
    # ── the RULE-SELECTED arm cannot go through `_pool_idxs` at all ────────────────────────────
    # Every other arm answers "which OTHER MINUTE of this same tape?", so it is expressible as a
    # set of indices. This one answers "what would THIS RULE have got on a different tape?", so it
    # needs the rule and builds its own bars. Dispatched here, implemented next door, so the pinned
    # pool-arm code path below is not touched by it. See `factory_surrogate_arm` for the design and
    # for what its surrogate deliberately does NOT preserve.
    if arm == "surrogate":
        if rule is None:
            raise ValueError("the 'surrogate' arm needs the candidate's own rule — it re-runs it "
                             "on each surrogate tape; a caller that cannot supply it cannot use "
                             "this arm (silently falling back to a pool arm would report a "
                             "DIFFERENT arm's null under this arm's name)")
        import factory_surrogate_arm as fsa
        return fsa.rank_all(rows, corpus, rule, fb.walk_trade, k,
                            seed + SURROGATE_STREAM, sl_key, pool_sink=pool_sink)

    rng = random.Random(seed + ARMS.index(arm))
    pairs, dropout = [], collections.Counter()
    for r in rows:
        bars = corpus[r["day"]]
        cand = _pool_idxs(bars, arm, r, rng)
        if len(cand) < MIN_POOL:
            dropout["pool_too_small"] += 1
            continue
        pool = []
        for _ in range(k):
            i = rng.choice(cand)
            p, err = fb.walk_trade(bars, i, r["side"], r[sl_key], r.get("tp_r"),
                                   r.get("max_hold_min"), r.get("cost_band", "central"),
                                   sym=r.get("cost_sym"))
            if err or p["hold_truncated"]:
                continue
            pool.append(p["r_gross"])
        if len(pool) < MIN_POOL:
            dropout["walked_pool_too_small"] += 1
            continue
        below = sum(1 for x in pool if x < r["r_gross"])
        ties = sum(1 for x in pool if x == r["r_gross"])
        pairs.append((r["day"], (below + 0.5 * ties) / len(pool)))
        if pool_sink is not None:
            pool_sink.extend(pool)          # only pools that actually ranked — see the docstring
    return pairs, dict(dropout)


def summarize(pairs, label):
    """The percentile statistic with all three interval forms and its achieved MDE."""
    pcts = [p for _, p in pairs]
    if len(pcts) < 2:
        return {"label": label, "n": len(pcts), "insufficient": True}
    m = st.mean(pcts)
    se_naive = st.pstdev(pcts) / len(pcts) ** 0.5
    naive = [m - 1.96 * se_naive, m + 1.96 * se_naive]
    reg = ca.cluster_bootstrap_ci(pairs, weight="decision")
    dayw = ca.cluster_bootstrap_ci(pairs, weight="day")
    byday = collections.defaultdict(list)
    for d, p in pairs:
        byday[d].append(p)
    ci = reg or naive
    # SE recovered from the registered interval, so the MDE is stamped with the SAME clustering
    # the verdict uses. Reading it off the naive SE would understate the effect we could have
    # seen — the flattering direction, on the number whose whole job is to bound flattery.
    se = (ci[1] - ci[0]) / (2 * 1.959964)
    out = {"label": label, "n": len(pcts), "n_days": len(byday),
           "mean_percentile": m,
           "day_weighted_mean": st.mean([st.mean(v) for v in byday.values()]),
           "ci_form": "day-clustered bootstrap" if reg else "naive (single day — cannot cluster)",
           "ci95": ci, "ci95_clustered": reg, "ci95_day_weighted": dayw, "ci95_naive": naive,
           "se": se, "mde_percentile": Z_MDE * se}
    out["excludes_half"] = ca._excl(ci)
    out["excludes_half_naive"] = ca._excl(naive)
    out["excludes_half_day_weighted"] = ca._excl(dayw)
    verdicts = {out["excludes_half"], out["excludes_half_naive"]}
    if dayw:
        verdicts.add(out["excludes_half_day_weighted"])
    out["forms_disagree"] = len(verdicts) > 1
    return out


def null_verdict(summary, tol, allow_unmatched=False):
    """★ EQUIVALENCE, NOT "does the CI span 0.5".

    ★★ AND IT REFUSES TO CERTIFY A NULL ON AN UNMATCHED ARM. The confound is BIDIRECTIONAL
    (module header): a rule entering at an unfavourable extreme scores 0.3977 on an EDGE-FREE
    tape against 0.4988 price-matched. Momentum, breakout and continuation rules enter at
    unfavourable extremes BY CONSTRUCTION, so an unmatched arm would kill a whole candidate
    family for arithmetic and file it as "no edge found" — a false negative that looks exactly
    like an honest result. The rule "never quote a null from an unmatched arm" was first written
    as a memory line; memory lines rot, so it is enforced HERE, at the only chokepoint every null
    verdict must pass through. `allow_unmatched=True` exists for the exhibit case and has to be
    typed on purpose.

    The span form is satisfied by a WIDE interval — it gets EASIER to pass the less data you
    have, it flakes at the nominal rate on seed luck, and the honest response to a red gate
    becomes "re-run it", which is p-hacking the validator. This form requires the whole
    interval to lie INSIDE 0.5 ± tol, so too little data fails as INSUFFICIENT POWER rather
    than passing as a null. (The same repair `factory_synthetic.py` made to its own checks.)
    """
    arm = summary.get("label")
    if arm in ARMS and arm != ARM_REGISTERED and not allow_unmatched:
        return False, (f"REFUSED — a null on the '{arm}' arm is not a verdict. The entry-price "
                       f"confound is bidirectional and buries real edges as readily as it "
                       f"invents them; the registered arm is '{ARM_REGISTERED}'. Pass "
                       f"allow_unmatched=True only to quote it as an EXHIBIT.")
    if summary.get("insufficient"):
        return False, "n < 2 — nothing to test"
    lo, hi = summary["ci95"]
    half = (hi - lo) / 2
    if half > tol:
        return False, (f"INSUFFICIENT POWER — CI ±{half:.4f} is wider than the ±{tol:.4f} band; "
                       f"a null here would be an artifact of low n (MDE {summary['mde_percentile']:.4f})")
    inside = (0.5 - tol) <= lo and hi <= (0.5 + tol)
    return inside, (f"mean {summary['mean_percentile']:.4f}, CI [{lo:.4f}, {hi:.4f}] "
                    f"{'⊂' if inside else '⊄'} 0.5±{tol:.4f} (MDE {summary['mde_percentile']:.4f})")


def detect_verdict(summary):
    """A detection must clear chance in the RIGHT DIRECTION — an interval sitting entirely
    BELOW 0.5 also 'excludes 0.5' and is the opposite of the claim."""
    if summary.get("insufficient"):
        return False, "n < 2"
    lo, hi = summary["ci95"]
    return lo > 0.5, (f"mean {summary['mean_percentile']:.4f}, CI [{lo:.4f}, {hi:.4f}] "
                      f"{'>' if lo > 0.5 else '⊅'} 0.5 (MDE {summary['mde_percentile']:.4f})")


def score(rows, corpus, k=K_DEFAULT, seed=SEED, arms=ARMS):
    """Every arm, plus the entry-price diagnostic that would have caught the 0.725 survivor."""
    out = {"k": k, "seed": seed, "n_candidates": len(rows), "arms": {}}
    for arm in arms:
        pairs, dropout = placebo_rank(rows, corpus, arm, k, seed)
        s = summarize(pairs, arm)
        s["dropout"] = dropout
        out["arms"][arm] = s
    out["registered_arm"] = ARM_REGISTERED
    out["entry_price_percentile"] = entry_price_percentile(rows, corpus)
    return out


def entry_price_percentile(rows, corpus, lookback_min=WINDOW_MIN):
    """WHERE the rule enters, independent of what happens next — the confound diagnostic.

    For a long: the fraction of PRIOR closes ABOVE the entry (a low entry ⇒ near 1.0). This reads
    the trigger only; it cannot know the outcome — and as of 2026-08-12 that sentence is TRUE.

    ━━ ⛔ THE DEFECT THIS FUNCTION SHIPPED WITH, 2026-08-11 → 2026-08-12 ━━━━━━━━━━━━━━━━━━━━━━
    The window was `abs(b["time"] - base) <= lookback_min * 60` — **SYMMETRIC** — while the
    parameter was named `lookback_min` and this docstring already claimed it could not know the
    outcome. Half the window was POST-entry, so the statistic was ~half composed of the trade's
    own future: a long that runs up has more closes above its entry, which raises epp AND the
    outcome percentile, mechanically and with no market involved.

    Found by a D030 external seat refuting `PROPOSAL_epp_calibration` (which it killed TERMINAL
    on exactly this), re-verified at source. Measured on the US500 edge-free control, 250 days,
    `rule_dumb` — a rule with NO price selection at all:
        corr(pct, epp_symmetric) = +0.298   ← what this function used to return
        corr(pct, epp_past_only) = +0.044   ← what it returns now
        corr(pct, epp_future)    = +0.376
    Binned residual range collapsed 0.206 → 0.026 with every CI then spanning zero, replicated on
    three tapes. **The "epp slope" that organised the whole 2026-08-12 repair effort was largely
    this defect looking at itself.** Findings F036/F038; fault
    `2026-08-12__entry-price-percentile-is-half-forward-looking`.

    ⚠ **SCOPE — what the defect did NOT do:** epp is a LABEL and a diagnostic. It is not an input
    to any arm verdict (`factory_slope_test.judge` only reports it), so the REJECTED verdicts in
    F030/F031 are untouched. What it contaminated is every printed "epp ≈" figure, the mechanistic
    story, and any design that would USE epp as a covariate.

    ⚠ **`CONFOUND_DEV = 0.15` is now of UNVERIFIED PROVENANCE** — it was derived from the 08-11
    fork-test figures 0.361 / 0.590 / 0.857, which were produced by `fork_test_matched.entry_pct`
    against a ±60min pool and may carry the same contamination. Re-derive before trusting
    `confound_risk`.

    ━━ THE ENTRY BAR IS EXCLUDED, DELIBERATELY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    `base` IS the entry bar's close, so admitting it would compare the entry price against itself
    — a degenerate member that drags every reading toward 0 (this function counts strict `>` and
    has no tie handling). Strictly-prior only.

    Returns `dropped` — rows with too few prior bars to score. A one-sided window has ~half the
    members of the old symmetric one, so this bites roughly twice as often as it used to and an
    uncounted dropout reselects the sample (the 08-11 `harness_ruler` defect).
    """
    vals, dropped = [], 0
    for r in rows:
        bars = corpus[r["day"]]
        base = r["entry_ts"]
        # STRICTLY BEFORE the entry bar. The mutation proof in `selftest` plants a spike in the
        # post-entry bars and fails if this reading moves.
        win = [float(b["close"]) for b in bars if 0 < (base - b["time"]) <= lookback_min * 60]
        if len(win) < MIN_POOL:
            dropped += 1
            continue
        better = (sum(1 for x in win if x > r["entry"]) if r["side"] == "long"
                  else sum(1 for x in win if x < r["entry"]))
        vals.append(better / len(win))
    if not vals:
        return {"n": 0, "dropped": dropped}
    m = st.mean(vals)
    return {"n": len(vals), "dropped": dropped, "mean": m,
            "deviation": abs(m - 0.5), "confound_risk": abs(m - 0.5) >= CONFOUND_DEV,
            "direction": "favourable (inflates the time arm)" if m > 0.5
                         else "unfavourable (deflates the time arm)",
            "note": "0.5 = neutral entry price; the time-matched arm is only trustworthy near it"}


# ── selftest ────────────────────────────────────────────────────────────────────────────────

def selftest(days=12, seed=7, k=30):
    """Positive / negative / anti controls — the scorer pointed at tapes whose answer is known.

    This is NOT the gate (that is `factory_notblind.py`, which registers its verdict and runs
    at gate power). It is the fast check that the wiring is live, and it deliberately uses too
    few days so that the null rows exercise the INSUFFICIENT-POWER path rather than passing on
    a wide interval.
    """
    import factory_synthetic as fs
    ok = True

    def check(name, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  {'✓' if passed else '✗'} {name}{': ' + detail if detail else ''}")

    free = fs.make_corpus(days, seed, 0.0)
    planted = fs.make_corpus(days, seed, fs.DEFAULT_EFFECT_PT)
    geo = dict(sl_pt=20.0, max_hold_min=30, band="none", sym=fb.SYNTHETIC)

    print("── POSITIVE control: the planted signal on the planted tape ──")
    rows, rej = fb.backtest(planted, fs.rule_planted_signal, **geo)
    s = score(rows, planted, k=k)
    det_p, d_p = detect_verdict(s["arms"]["price"])
    check("detected on the REGISTERED (price-matched) arm", det_p, d_p)
    # ⚠ NOT a pass condition, and the reason is the module header's bidirectional finding: this
    # rule buys local maxima, so the time-matched arm charges it an arithmetic penalty that eats
    # the planted edge. Printed so the gap is visible, never asserted away.
    print(f"    · time-matched arm reads {s['arms']['time']['mean_percentile']:.4f} "
          f"— buried by entry price, not by absence of edge (see NEGATIVE control)")

    print("── NEGATIVE control: the SAME rule on the edge-free tape ──")
    rows0, _ = fb.backtest(free, fs.rule_planted_signal, **geo)
    s0 = score(rows0, free, k=k)
    check("does not detect an edge that is not there",
          not detect_verdict(s0["arms"]["price"])[0],
          f"{s0['arms']['price']['mean_percentile']:.4f} "
          f"CI {[round(x, 4) for x in s0['arms']['price']['ci95']]}")
    # ★ THE BIDIRECTIONAL CONTROL. Same rule, same edge-free tape, both arms — the time arm must
    # be pushed BELOW chance by entry price while the price arm sits at it. Without this row the
    # positive control's relaxation above would just be a threshold quietly lowered.
    t0 = s0["arms"]["time"]
    check("★ the time-matched arm is BIASED BELOW chance on a tape with no edge",
          t0["ci95"][1] < 0.5 and s0["entry_price_percentile"]["mean"] < 0.5,
          f"time {t0['mean_percentile']:.4f} CI [{t0['ci95'][0]:.4f},{t0['ci95'][1]:.4f}] "
          f"at entry-price pct {s0['entry_price_percentile']['mean']:.3f} — "
          f"price arm {s0['arms']['price']['mean_percentile']:.4f}")

    print("── ★ THE ENTRY-PRICE DIAGNOSTIC CANNOT SEE THE FUTURE (F036 mutation proof) ──")
    # The defect this pins shipped for a day and killed a proposal: the window was SYMMETRIC while
    # the parameter was named `lookback_min`. Plant an impossible spike in every bar AFTER each
    # entry. A forward-looking window moves; a strictly-prior one cannot. This assertion fails on
    # the exact mutation `0 < (base - b["time"])` -> `abs(b["time"] - base)`.
    # ⚠ PER-ROW, and the first draft of this proof was WRONG in a way worth recording: it spiked
    # one shared corpus after the day's EARLIEST entry, which also spiked bars sitting BEFORE every
    # later entry — so it moved the honest reading and "failed" a correct implementation. A
    # look-ahead proof has to be built one decision at a time or it plants its own look-behind.
    rows_m, _ = fb.backtest(free, fs.rule_dumb, **geo)
    moved, tested = 0, 0
    for r in rows_m[:40]:
        before = entry_price_percentile([r], free)
        if before.get("n") != 1:
            continue
        spiked = {r["day"]: [dict(b) for b in free[r["day"]]]}
        for b in spiked[r["day"]]:
            if b["time"] > r["entry_ts"]:
                for key in ("open", "high", "low", "close"):
                    b[key] = float(b[key]) + 10_000.0
        after = entry_price_percentile([r], spiked)
        tested += 1
        if abs(before["mean"] - after["mean"]) > 1e-12:
            moved += 1
    check("a +10,000pt spike in every POST-entry bar leaves the reading unchanged",
          tested > 0 and moved == 0,
          f"{tested} decisions, {moved} moved — a symmetric window moves ALL of them")
    check("the entry bar itself is excluded (no degenerate self-comparison)",
          entry_price_percentile(rows_m, free, lookback_min=0)["n"] == 0,
          "a zero-width lookback admits nothing, not the entry bar")

    print("── ANTI control: the confound rule, both values ──")
    rowsx, _ = fb.backtest(free, fs.rule_price_extreme, **geo)
    sx = score(rowsx, free, k=k)
    # The diagnostic is judged by CONTRAST against rules known to be price-neutral, not against a
    # constant: "extreme" depends on the window, and a hardcoded 0.9 borrowed from a 30-bar
    # window silently becomes wrong at ±60 minutes. Neutral rules pin the scale in the same run.
    rows_n, _ = fb.backtest(free, fs.rule_dumb, **geo)
    neutral = entry_price_percentile(rows_n, free)["mean"]
    epp = sx["entry_price_percentile"]
    check("the confound rule trips the confound flag; a price-neutral rule does not",
          epp["confound_risk"] and abs(neutral - 0.5) < CONFOUND_DEV,
          f"price_extreme {epp['mean']:.3f} (dev {epp['deviation']:.3f}) vs neutral {neutral:.3f}")
    check("scores ABOVE chance on the time-matched arm (the trap)",
          detect_verdict(sx["arms"]["time"])[0], detect_verdict(sx["arms"]["time"])[1])
    check("and NOT above chance once price is matched",
          not detect_verdict(sx["arms"]["price"])[0], detect_verdict(sx["arms"]["price"])[1])

    print("── a null on an UNMATCHED arm is refused, not reported ──")
    ref_pass, ref_why = null_verdict(s0["arms"]["time"], 0.05)
    check("null_verdict REFUSES the time-matched arm",
          not ref_pass and ref_why.startswith("REFUSED"), ref_why[:72])
    exh_pass, _ = null_verdict(s0["arms"]["time"], 0.05, allow_unmatched=True)
    check("…and the exhibit escape hatch still works when typed on purpose",
          isinstance(exh_pass, bool), "allow_unmatched=True evaluates the band")
    ok_pass, _ = null_verdict(s0["arms"][ARM_REGISTERED], 0.05)
    check("the REGISTERED arm is not refused", ok_pass, f"arm '{ARM_REGISTERED}' evaluated")

    print("── the MDE is stamped and the equivalence form refuses low power ──")
    passed, why = null_verdict(s0["arms"]["price"], 0.001)
    check("an absurdly tight band fails as INSUFFICIENT POWER, not as a null",
          not passed and "INSUFFICIENT POWER" in why, why[:70])
    check("MDE is positive and finite", 0 < s0["arms"]["price"]["mde_percentile"] < 1,
          f"{s0['arms']['price']['mde_percentile']:.4f}")

    print("── dropouts are counted, never silent ──")
    check("every arm reports a dropout dict",
          all("dropout" in s["arms"][a] for a in ARMS), str(s["arms"]["price"]["dropout"]))
    check("rejections from the walk are counted too", isinstance(rej, dict), str(rej))

    # ★ THE POOL-ARM `pool_sink` — added 2026-08-13 after a D030 seat found it had NO executable
    # assertion anywhere (SERIOUS-3). This is the path that produced `POOL_ABSORPTION_FLOOR`, the
    # number used to scope a ratified bar, and nothing would have caught a mutation to it: the
    # only test lived next door in `factory_surrogate_arm` and covered the OTHER branch, and the
    # slope test's own assertions are on verdicts, which for pool arms absorption does not bind.
    print("── pool_sink OBSERVES the pool arms: no RNG consumed, no pair moved ──")
    for arm in ARMS:
        a_pairs, a_drop = placebo_rank(rows, planted, arm, k=k, seed=seed)
        sink = []
        b_pairs, b_drop = placebo_rank(rows, planted, arm, k=k, seed=seed, pool_sink=sink)
        check(f"'{arm}': pairs bit-identical with the sink attached",
              a_pairs == b_pairs and a_drop == b_drop, f"{len(a_pairs)} pair(s)")
        # Every pool that RANKED contributed exactly the placebos it was ranked against. Pools
        # are re-drawn per candidate here (unlike the day-cached surrogate), and the walker drops
        # truncated holds, so the size is bounded by k rather than equal to it — but it can never
        # be below MIN_POOL, which is the condition under which the candidate was kept at all.
        check(f"'{arm}': sink size is consistent with the pools that ranked",
              len(b_pairs) * MIN_POOL <= len(sink) <= len(b_pairs) * k,
              f"{len(sink)} in [{len(b_pairs) * MIN_POOL}, {len(b_pairs) * k}]")

    print()
    print(f"  {'PASS' if ok else 'FAIL'} — scorer controls ({days} days, k={k}, seed {seed})")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("selftest")
    s.add_argument("--days", type=int, default=12)
    s.add_argument("--seed", type=int, default=7)
    s.add_argument("--k", type=int, default=30)
    s.add_argument("--json", action="store_true")
    a = ap.parse_args()
    ok = selftest(a.days, a.seed, a.k)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
