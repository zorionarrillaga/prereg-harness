#!/usr/bin/env python3
"""factory_slope_test.py — THE ACCEPTANCE CRITERION for any placebo arm. Run it BEFORE designing.

Charter H32: the gauge ships with the mechanism. This is the gauge, and it exists because the
mechanism it judges was designed without it and died.

━━ WHY THIS EXISTS — the 2026-08-12 TERMINAL ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The Phase-1 report proposed repairing the price-matched arm by walking each placebo at the
CANDIDATE's entry price. It reasoned that "price then differs by zero by construction". An
external seat measured it: on an EDGE-FREE tape the proposed arm reads **0.6023** for a momentum
rule and **0.4238** for a price-extreme rule — a rule-to-rule spread of 0.179, **worse than not
matching at all** (0.164), with the sign flipped. A whole session was about to be spent building
it. `architecture/REFUTATION_2026-08-12_phase1_diagnosis_R1.md`, FOLD 1.

**The defect is a SLOPE, not a LEVEL.** Judge an arm with ONE rule and you sample its residual at
one point — which is exactly how a catastrophically biased arm read as "+0.0077, nearly fine". Two
structurally different rules make the disagreement visible in about two minutes.

━━ ⚠ THE EXPLANATION WAS WRONG. THE CRITERION IS NOT (2026-08-12, later the same day) ━━━━━━━━
This header used to say *"an arm's residual bias is a function of the candidate rule's entry-price
percentile (epp)"*. **That is refuted (F038):** two structurally different rules at the SAME epp
differ by **+0.10 to +0.15** in every bin, on three tapes and within each side separately — six to
nine times the aggregate bias and ~15× `tol`. epp was a convenient one-dimensional label for a
difference that is not one-dimensional. What the rule SELECTS ON matters beyond where it enters.

And the epp numbers themselves were contaminated until today (F036): `entry_price_percentile` used
a **symmetric** ±60min window while being named `lookback_min`, so it was ~half composed of the
trade's own future. The honest positions are ≈0.16 / ≈0.95 / ≈0.51, not the 0.33 / 0.72 / 0.50 this
file printed for a day. Fixed + mutation-pinned in `factory_scorer.selftest`.

**WHAT SURVIVES — and it is the part that matters:** the criterion's OPERATIONAL form is
untouched. *"Judge an arm with two structurally different rules and REJECT if their nulls
disagree"* needs no claim about epp being the cause, and the epp figures are labels this module
prints, never inputs to a verdict. The 400-day rejections (F030 synthetic, F031 real bars) stand.
**Do not read the word "slope" below as a causal claim** — it is the name of a disagreement whose
mechanism is unknown.

━━ THE CRITERION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
An arm QUALIFIES only if, on an **edge-free** tape, its null CI contains 0.5 for **BOTH**:
  · `rule_planted_signal`  — buys local maxima, epp ≈ 0.16 (unfavourable entry)
  · `rule_price_extreme`   — buys local minima, epp ≈ 0.95 (favourable entry)
`rule_dumb` (epp ≈ 0.51) is reported as a NEUTRAL CONTROL, never as a pass condition: it sits at
the zero-crossing of the slope and is structurally blind to this defect. The Phase-1 gate's own
checks 2b and 3 both use epp≈0.51 rules, which is why "5/7" was never five independent
validations (R1 FOLD 7).

━━ ★ THE FORM IS EQUIVALENCE, AND IT DID NOT USE TO BE (repaired 2026-08-12) ━━━━━━━━━━━━━━━━━
This file shipped judging with `lo <= 0.5 <= hi` — the SPAN form that `factory_scorer.null_verdict`
explicitly bans in its own docstring, written by the same author on the same day. A D030 external
seat measured the consequence: **the criterion REJECTED THE INCUMBENT `price` arm** at 160 days on
its own seed (0.5086 [0.5004, 0.5171]) and at 1 of 4 seeds at 40 days. A criterion that cannot
pass the arm it exists to judge repairs against cannot adjudicate anything, and it killed a whole
proposal's worth of work in both directions before it was caught.
`architecture/REFUTATION_2026-08-12_uniform_arm_R1.md` FOLD 4.

So: a probe passes only if its **whole CI lies inside 0.5 ± tol**, and too little data fails as
**INSUFFICIENT POWER** rather than passing on width. The old `MAX_HALFWIDTH = 0.030` guard is
DELETED, not weakened — it was larger than the registered arm's own rule-to-rule spread (0.018)
and 3.7× the gate's null band, while its docstring claimed to discriminate exactly those.

━━ ★ AND THE CRITERION HAD NO POSITIVE CONTROL AT ALL (F132, built 2026-08-13) ━━━━━━━━━━━━━━
Everything above judges an arm on an EDGE-FREE tape. **An arm that is blind to everything passes
that perfectly** — and `factory_synthetic.py:224` had already written the sentence: *"a scorer
that returns null on both is not passing, it is DEAD, and would report null for a real edge
too."* The planted tape was being built one function below (`derive_tol`) and scored on the
REGISTERED arm only, so the arm actually under test never met a known effect.

★ IT IS PASSABLE, AND THAT IS MEASURED, NOT ASSERTED. The one property whose absence has already
broken this criterion once (FOLD 4: a criterion that cannot pass the arm it exists to judge
adjudicates nothing) — with every gate live (absorption, shift, null control) `uniform` at 400
days reads **SENSITIVE**, shift +0.0768 [+0.0685, +0.0851] against a ±0.0086 band with a CLEAN
null control. At 20 days the same arm is INDETERMINATE. Nothing is bought by width anywhere: the
gate abstains on thin data and resolves on thick, which is the whole difference between a
validator and a rubber stamp.
    python3 bin/factory_slope_test.py poscontrol --arm uniform --days 400 --seeds 1

⇒ **THE ASYMMETRY THAT KEEPS THE RECORD INTACT: a REJECT never needed sensitivity evidence.** An
arm biased on an edge-free tape is disqualified whatever its power, so F030, F031 and F131 are
untouched by this repair. Only a PASS was unearned, and only a PASS now has to buy one:
`QUALIFIES` requires `positive_control` to return SENSITIVE. Skipping it prints **UNVALIDATED**,
which is the verdict this module used to print as QUALIFIES.

⚠ **THE RATIFIED ABSORPTION BAR DID NOT SURVIVE ITS OWN MEASUREMENT, AND IS SCOPED, NOT
WEAKENED.** F134 ratified "the placebo pool must gain < 20% of what the candidate side gains".
Implemented and run, it rejects **every arm including the incumbent**: the planted effect is a
15-minute PERSISTENT drift, so any same-day placebo entering during those minutes captures part
of it whether or not a rule selected it. That puts a floor under the pool family which belongs to
the TAPE, not to the arm — measured by `uniform`, the most rule-blind pool draw there is, at
`POOL_ABSORPTION_FLOOR`, **above the bar**. A bar below its own floor convicts by arithmetic, and
this module has already been through one criterion that could not pass the arm it exists to judge
(FOLD 4 below). So absorption BINDS on rule-selected arms — where its evidence came from, and
where there is no floor because the placebo re-runs the rule — and is REPORTED for pool arms.

★ AND THE SCOPED BAR IS LOAD-BEARING, not a courtesy. I first wrote that the surrogate "fails on
shift alone" and that was WRONG when measured: at 20 days its shift is −0.0289 with CI
[−0.0803, +0.0225], which STRADDLES the band ⇒ INDETERMINATE, not a conviction. Absorption at
121.6% is the only thing that convicts it at that size. Deleting the bar as unpassable would have
lost the one worked example the whole repair was built around.

★ AND THE POSITIVE CONTROL NEEDED A NULL CONTROL — the same defect, one level up (D030 seat).
This module exists because a null test had no positive control; the positive control then shipped
with no NULL control, i.e. nobody had asked what the SHIFT statistic reads when the true answer
is zero. On `rule_dumb` — epp≈0.51, no selection relationship to the planted signal, so the true
shift IS zero — the seat measured `time` at **−0.0159 [−0.0198, −0.0120], 128% of the entire
detection bar**, and `uniform` at −0.0087; only the registered arm came back clean (+0.0005).

⇒ THE LEVEL→SHIFT REPAIR MOVED THE CONFOUND RATHER THAN REMOVING IT. `planted − 0.5` counted
STANDING bias as eyesight; `planted − edge_free` counts CHANGE IN bias as eyesight. So an arm's
own null control must be CLEAN — the neutral rule's shift CI inside ±tol — before any verdict is
read from it, and a dirty one yields INDETERMINATE. Refusal, not correction: subtracting a noisy
neutral estimate would invent a point estimate and add its variance to the bar.

⚠ THIS RETRACTED A CLAIM I HAD ALREADY WRITTEN HERE. For an hour this header said the biased
`time` arm was "SENSITIVE (+0.0525), proving bias and blindness are different failures". With its
own null control measured, `time` is **INDETERMINATE**: the +0.0525 is not certifiable, because
the instrument reading it is not zero where it must be. Bias and blindness may well be different
failures — but this module could not have told you, and said so anyway.

★ AND THEN THE OFFSET ITSELF TURNED OUT TO DECAY (F138, measured at the operating size). At 400
days on 4800 `rule_dumb` rows: `uniform` +0.0005 [−0.0046, +0.0056] CLEAN, `time` −0.0020
[−0.0075, +0.0035] CLEAN, `price` +0.0010 [−0.0067, +0.0087] — against tol 0.0086. The `time`
offset fell ~8× while days grew 20×, which is a SMALL-SAMPLE effect in the percentile machinery,
not a permanent property of the arm. So the gate RESOLVES rather than blocking forever — exactly
what the three-way form exists to allow and what the two-way first cut would have denied. Note
`price` misses CLEAN by 0.0001 with a half-width (0.0077) already INSIDE the band: that is a
point estimate grazing a boundary, not missing power. Do not quote the 20-day figures as an
arm's standing bias; that over-reading is what F122 was filed for.

━━ WHERE `tol` COMES FROM, AND WHY IT IS NOT A KNOB ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Derived, never chosen: the gate's own rule (`factory_notblind.NULL_BAND_FRACTION` / `_CAP`,
IMPORTED so the two can never drift) applied to a lift measured on a PLANTED tape — "a null must
sit within 25% of a genuine effect". Two properties are deliberate:
  · it is derived from the **REGISTERED** arm's lift and then applied UNCHANGED to every arm in
    the run. A candidate cannot buy itself a wider band by having a bigger lift — and `uniform`'s
    raw lift IS bigger than the incumbent's, so this is not hypothetical.
  · a criterion pass therefore means the arm satisfies **the gate's own null form**, not a
    house standard invented next door to it.

⚠ AND IT IS A GAUSSIAN-WALK TAPE. Passing here does not mean calibrated on real microstructure.

Verbs:
  run [--arm NAME] [--days N] [--seed S] [--k K]     judge one arm (default: the registered one)
  compare [--days N]                                 judge every arm in factory_scorer.ARMS
"""
import argparse
import os
import statistics as st
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))
import factory_synthetic as fs                 # noqa: E402
import factory_backtest as fb                  # noqa: E402
import factory_scorer as sc                    # noqa: E402
import factory_notblind as nb                  # noqa: E402  the null band's CONSTANTS, imported
#                                              so the criterion and the gate cannot drift apart.
#                                              (nb does not import this module — no cycle.)

GEOMETRY = dict(sl_pt=20.0, tp_r=None, max_hold_min=30, band="none",
                sym=fb.SYNTHETIC)
DEFAULT_DAYS = 40                              # R1 measured the criterion at this size (~2 min)
DEFAULT_K = 20
DEFAULT_SEED = 20260812

# The two poles of the epp slope, plus the neutral control that must NOT be a pass condition.
PROBES = [
    ("rule_planted_signal", fs.rule_planted_signal, "low epp ≈0.16 — buys local MAXIMA", True),
    ("rule_price_extreme", fs.rule_price_extreme, "high epp ≈0.95 — buys local MINIMA", True),
    ("rule_dumb", fs.rule_dumb, "epp ≈0.51 — NEUTRAL CONTROL, not a pass condition", False),
]

_TOL_CACHE = {}
_PC_CACHE = {}

# ★ THE RULER'S OWN DEFECT — `tol` IS ITSELF STILL A LEVEL (F142, 2026-08-13) ━━━━━━━━━━━━━━━━
# `_planted_reference` computes `lift = registered_planted_percentile − 0.5`. That is VERBATIM the
# arithmetic this module condemns two functions below (`positive_control`, "⚠ AND IT IS A SHIFT,
# NOT A LEVEL — the first draft got that wrong and the error flattered"), left standing in the
# ruler that BOTH the null test and the new detection bar are measured against. F030 has already
# CONVICTED the registered arm of the very bias a level folds in, so the circularity runs in the
# flattering direction: THE MORE BIASED THE REFERENCE ARM, THE WIDER THE BAND THAT EXCUSES BIAS.
#
# The repair is one subtraction: `lift = registered_planted_pct − registered_FREE_pct`, the same
# shift form `positive_control` already uses for the arm under test.
#
# ⛔ THE DEFAULT IS DELIBERATELY UNCHANGED, AND THAT IS NOT TIMIDITY. `tol` is an ACCEPTANCE
#    CRITERION — it decides REJECTED vs INDETERMINATE vs QUALIFIES — so switching it is a D030 T3
#    that the ratifying authority signs off, not a correctness patch an author may take. What ships here is the
#    ability to MEASURE BOTH RULERS side by side (`tolcompare`), which is what the proposal needs
#    and what nobody could produce while the level was hardcoded.
#
# ⚠ AND THE REPAIR IS NOT FREE IN THE DIRECTION EVERYONE ASSUMES (F140). `judge` evaluates
#    `outside → REJECTED` BEFORE `underpowered → INDETERMINATE` (see the ladder in `judge`), so a
#    NARROWER band also arms the power gate. Shrinking `tol` can therefore turn a REJECTED into an
#    INDETERMINATE.
#
# ⛔ BUT THE COMFORTING HALF OF THAT SENTENCE WAS FALSE AND IS WITHDRAWN (D030 seat, 2026-08-13).
#    It used to read: "it cannot reverse a wrong call — F030's rejections were achieved DESPITE a
#    too-forgiving band, so they are conservative." **THAT HOLDS ONLY FOR `outside`-DRIVEN
#    REJECTS.** The verdict is NON-MONOTONE in `tol`; mapped on the real 400d price-arm CIs:
#        tol ≥0.0020 → REJECTED(outside) · ≥0.0051 → INDETERMINATE
#        tol ≥0.0075 → REJECTED(else)    · ≥0.0149 → QUALIFIES
#    The shipped band (0.0086) sits in the **else** window, and that window opens only at 0.0075 —
#    i.e. only once the band is wide enough to call a half-width-0.0075 probe "powered". So that
#    conviction was **BOUGHT BY THE INFLATION, not earned despite it**, and withdrawing it returns
#    a manufactured result rather than losing a real one. This is the same mechanism
#    `tests/test_factory_harness.sh` already pins as buying "a confident FALSE REJECTION of the
#    very arm the gate is registered on". Read F144/F147, not just F140.
TOL_LIFT_MODES = ("level", "shift")

# ★★★★★ THE RULER IS `shift` — TRADER-RATIFIED 2026-08-13 15:47 ET ("switch").
#   lift = registered_planted_pct − registered_FREE_pct.  The `level` form (planted − 0.5) is
#   RETAINED as an explicit argument ONLY to reproduce pre-switch rows; it is no longer a default
#   anyone can reach by accident.
#
#   THE DECIDING ARGUMENT, recorded because it was NOT in the author's original case for holding:
#   holding did not preserve knowledge, it preserved a KNOWN-MANUFACTURED CONVICTION. F030 read
#   "all three arms REJECTED at 400 days"; F147 showed the `price` third sits in the `else` window
#   that opens only once the band is wide enough to call a half-width-0.0075 probe "powered".
#
#   ⚠ ACCEPTED CONSEQUENCES, named BEFORE the ruling: F030's headline is amended to
#   two REJECTED + `price` INDETERMINATE; the `time` arm's positive control drops SENSITIVE →
#   INDETERMINATE (F138's 400d neutral CI [−0.0075, +0.0035] is not contained in ±0.0061, so what
#   is withdrawn is interval RESOLUTION — "answered by more days", not a finding about the arm);
#   and at the repaired band `price` lands in the ambiguous middle window instead of convicting.
#   A truer result, not a cleaner one.
#
# ⛔ IT IS A CONSTANT, NOT AN ENV VAR, AND THAT IS THE SECOND HALF OF THE RULING. This used to be
#    `os.environ.get("FACTORY_TOL_LIFT", "level")` — an environment variable silently steering an
#    ACCEPTANCE CRITERION, invisible in every log and every findings row. That is the same defect
#    class as the unregistered 30-week argparse default found in `factory_prescreen.py` the same
#    morning (F141): a magic value from nowhere deciding a kill. Do not reintroduce an env hook.
TOL_LIFT_MODE = "shift"

# ★ THE POSITIVE CONTROL'S BAR (F132/F134, ratified 2026-08-13) ━━━━━━━━━━━━━━━━━━━━━━━
# DECLARED, not derived — and labelled as such so nobody later quotes it as a measurement. It is
# the blind D030 seat's reversal condition, adopted verbatim when the T3 was granted.
# ⚠ NO MEASURED CASE SITS ANYWHERE NEAR IT: the surrogate arm absorbed 103% (97% after its
# "fix"), the pool arms are far below. So this digit has never yet been the deciding one, and if
# a future arm lands close to it that is the moment to go and derive it properly — NOT to nudge
# it. Tuning a bar against the arm it is judging is the `PRICE_BAND` prohibition wearing a hat.
ABSORPTION_MAX = 0.20

# ★ AND THE FLOOR UNDER IT, MEASURED — the reason the bar above is SCOPED to rule-selected arms.
# `uniform` draws any minute of the day: no time window, no price band, no rule. It is the most
# rule-blind placebo the pool family can build, so its absorption is that family's floor — and the
# floor belongs to the TAPE, not to the arm.
#
# THE MECHANISM, MEASURED RATHER THAN ARGUED (2026-08-13, 20 days × 3 seeds): the planted tape
# carries a live drift over **85.6% of its own minutes**. The no-stacking rule spaces the drifts,
# but they still tile nearly the whole session, so a rule-blind draw lands inside a live drift ~6
# times in 7. Absorption then comes out at
# ⚠ THE FIRST NUMBER HERE WAS 87.4% AND IT WAS NOT A MEASUREMENT (D030 seat, SERIOUS-4a): it is
# the naive product n_drifts × DRIFT_MIN / minutes, which double-counts drift running past the
# session close. True coverage over 1364 drifts / 23400 minutes is 85.56%. The conclusion is
# unchanged; a figure quoted as measured has to actually be measured.
#   uniform 29.3% (range 4.1%) · price 52.4% (2.7%) · time 62.7% (0.9%) · surrogate 114.8% (41.5%)
# — the floor is 29.1%, ABOVE the 20% bar. Note the ordering is uniform < price < time: the price
# band REMOVES in-drift minutes once price has travelled beyond it, so matching on price absorbs
# LESS than matching on time alone. (I predicted the opposite before measuring; recorded because
# a prediction that failed is the only evidence the number was not fitted.)
#
# ⚠ SCOPE: this is a SYNTHETIC-tape measurement. A real-tape bootstrap plants its effect into a
# different bar population and its floor is not this number — re-measure before quoting it there.
# And it is a RECORDED MEASUREMENT used to scope a bar, never a bar itself: nothing is tested
# against it, and no verdict moves if it changes.
POOL_ABSORPTION_FLOOR = 0.29

DEFAULT_SWEEP_SEEDS = 5           # bar (2) is a statement about seed-to-seed RANGE — one seed
#                                   cannot make it (L025: sweep it, report the median)


def _planted_reference(days, seed, k, corpus_fn=None, verbose=True, lift_mode=None):
    """The planted tape, its candidate rows, and the REGISTERED arm's lift on it — built once.

    This used to live inside `derive_tol`, which threw all of it away and kept a single float.
    That is exactly how F132 happened: the planted corpus was already being constructed on line
    122 and scored on the price arm only, so the arm actually under test never met a known effect.
    Everything the positive control needs was already here.

    `lift_mode` picks WHAT THE LIFT IS MEASURED FROM — see the block above `TOL_LIFT_MODE`:
      · `level` (default, unchanged, ratified-by-inertia) — `planted_pct − 0.5`. Folds the
        registered arm's STANDING BIAS into the band, and F030 convicted that arm of having one.
      · `shift` (the proposed repair, PROPOSE-only until ratified) — `planted_pct − free_pct`,
        the same form `positive_control` already uses. Costs one extra free-tape walk of the
        registered arm per (days, seed, k).
    """
    corpus_fn = corpus_fn or fs.make_corpus
    lift_mode = lift_mode or TOL_LIFT_MODE
    if lift_mode not in TOL_LIFT_MODES:
        raise ValueError(f"lift_mode must be one of {TOL_LIFT_MODES}, got {lift_mode!r}")
    # ⚠ `lift_mode` IS PART OF THE KEY, for the reason the seat demonstrated live one function
    # down: a cache key that omits a discriminating field returns the FIRST caller's object to the
    # second, and here that object carries `tol` — i.e. it would launder one ruler as the other.
    key = (days, seed, k, getattr(corpus_fn, "tape_id", "synthetic"), lift_mode)
    if key in _TOL_CACHE:
        return _TOL_CACHE[key]
    planted = corpus_fn(days, seed, fs.DEFAULT_EFFECT_PT)
    rows, _ = fb.backtest(planted, fs.rule_planted_signal, **GEOMETRY)
    reg = sc.score(rows, planted, k=k, seed=seed, arms=(sc.ARM_REGISTERED,))["arms"][sc.ARM_REGISTERED]
    pct_planted = None if reg.get("insufficient") else reg["mean_percentile"]

    # THE BASELINE THE LIFT IS TAKEN FROM. 0.5 is an ASSUMPTION about an unbiased arm; the free
    # tape is a MEASUREMENT of this arm. That is the whole difference.
    reg_free, rows_free = None, None
    baseline = 0.5
    if lift_mode == "shift":
        free = corpus_fn(days, seed, 0.0)
        rows_free, _ = fb.backtest(free, fs.rule_planted_signal, **GEOMETRY)
        reg_free = sc.score(rows_free, free, k=k, seed=seed,
                            arms=(sc.ARM_REGISTERED,))["arms"][sc.ARM_REGISTERED]
        baseline = None if reg_free.get("insufficient") else reg_free["mean_percentile"]

    lift = 0.0 if (pct_planted is None or baseline is None) else pct_planted - baseline
    tol = min(nb.NULL_BAND_CAP, nb.NULL_BAND_FRACTION * lift) if lift > 0 else nb.NULL_BAND_CAP
    if verbose:
        src = ("0.5 (ASSUMED unbiased)" if lift_mode == "level"
               else f"{baseline:.4f} (MEASURED on the edge-free tape)" if baseline is not None
               else "unmeasurable")
        # ⚠ THE SUBSTRING "null band: planted-tape lift" IS A HARNESS ANCHOR
        # (tests/test_factory_harness.sh §10, "the null band is DERIVED … not declared"). The
        # first draft of this change wrote "null band [level]: planted-tape lift" and BROKE it —
        # F137's rot exactly, a legitimate edit shearing a string anchor. The mode is therefore
        # inserted AFTER the anchor, never inside it. Do not reflow this line.
        print(f"  null band: planted-tape lift [{lift_mode}] on the registered "
              f"('{sc.ARM_REGISTERED}') arm {lift:+.4f} "
              f"= {pct_planted if pct_planted is None else f'{pct_planted:.4f}'} − {src} "
              f"⇒ tol ±{tol:.4f} "
              f"({nb.NULL_BAND_FRACTION:.0%} of it, capped at {nb.NULL_BAND_CAP})")
        if lift <= 0:
            print("    ⚠ NON-POSITIVE LIFT — the band fell back to the CAP. The registered arm "
                  "failed to detect a\n      planted effect, so this run cannot judge anything; "
                  "treat every verdict below as void.")
    ref = {"corpus": planted, "rows": rows, "lift": lift, "tol": tol,
           "ci": reg.get("ci95"), "summary": reg, "lift_mode": lift_mode,
           "pct_planted": pct_planted, "baseline": baseline,
           "free_rows_registered": rows_free, "summary_free": reg_free}
    _TOL_CACHE[key] = ref
    return ref


def derive_tol(days, seed, k, verbose=True, corpus_fn=None, lift_mode=None):
    """The null band, measured — never chosen. Same rule as the gate, same constants, and taken
    from the REGISTERED arm so no candidate can widen its own bar.

    ⚠ This costs one extra planted-tape run per (days, seed, k). That is the price of a band that
    is derived rather than declared, and it is the whole reason the old MAX_HALFWIDTH could sit at
    0.030 — 3.7× this band — without anyone noticing it discriminated nothing.

    `corpus_fn(days, seed, effect_pt)` defaults to the synthetic tape. `factory_realtape` passes a
    vendor-bar bootstrap instead — and the band is RE-DERIVED on whatever tape is passed, never
    inherited across tapes: a tolerance measured on one tape and applied to another is the
    borrowed-constant failure this project has already been bitten by.
    """
    return _planted_reference(days, seed, k, corpus_fn, verbose, lift_mode)["tol"]


# ★ THE TIME AXIS (2026-08-12). Both probes are rule_dumb — identical, epp≈0.50, no price-position
# selection — differing ONLY in where in the session they fire. So a gap between them is the arm's
# response to WHEN, and cannot be the epp slope wearing a different hat. This exists because the
# `uniform` arm passes the epp criterion while carrying no time window at all, and the walker drops
# placebos whose hold runs past the close: a late pool loses members differentially.
TIME_PROBES = [
    ("rule_early_session", fs.rule_early_session, "first third of the session — epp ≈0.50", True),
    ("rule_late_session", fs.rule_late_session, "last third — the pool that loses members to truncation", True),
]


def positive_control(arm, days=DEFAULT_DAYS, seed=DEFAULT_SEED, k=DEFAULT_K, corpus_fn=None,
                     tol=None, verbose=True, free_corpus=None, free_rows=None, free_pool=None,
                     free_summary=None, lift_mode=None):
    """★ CAN THIS ARM SEE AN EDGE THAT IS ACTUALLY THERE? (F132, built 2026-08-13.)

    The criterion above judges an arm ONLY on an edge-free tape. An arm that is blind to
    everything passes that perfectly — it reads null on a dead tape and null on a live one — and
    the repo already had the sentence for it, in `factory_synthetic.py:224`: *"a scorer that
    returns null on both is not passing, it is DEAD, and would report null for a real edge too."*
    So every REJECT this module ever emitted stands untouched (a biased arm is disqualified
    whatever its power — F030/F031/F131 are unaffected), but every QUALIFIES was unearned. This
    function is the missing half.

    ━━ THE TWO MEASUREMENTS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Switch the planted effect ON and ask what each SIDE pockets:

      · **ABSORPTION** — the placebo pool's mean R gain as a fraction of the candidate side's.
        A percentile cannot answer this: it is scale-free, so an arm whose placebos capture the
        same edge the candidate captured reads a perfectly innocent 0.5. The surrogate arm is the
        worked example — its rotation moves the planted drift in the clock but keeps it on the
        tape, so the placebos re-ran the rule straight into the same effect and absorbed **103%**
        of it (97% after its "fix", F133). BAR: `ABSORPTION_MAX`, declared, see above.

      · **SHIFT** — how far the arm's percentile MOVES when the effect is switched on, measured
        with the same rule and seed on both tapes, against the same ruler the null uses. An arm
        must respond by MORE than the band that would have excused it as null: the whole CI above
        `tol`. Nothing new is invented — `tol` is already `nb.NULL_BAND_FRACTION` (25%) of the
        registered arm's planted lift.

        ⚠ AND IT IS A SHIFT, NOT A LEVEL — the first draft of this function got that wrong and
        the error flattered. It scored `planted_percentile − 0.5`, which for a BIASED arm counts
        its standing bias as eyesight: the incumbent reads 0.5236 on the edge-free tape at 20
        days, so +0.0236 of its "+0.0496 lift" was bias it carries with the effect switched OFF.
        F030 has already convicted every arm here of exactly that bias, so folding it into the
        sensitivity number would have let the worst-biased arm look like the most sensitive one.
        The two tapes share one noise stream (`make_tape` plants drift by shifting the gauss MEAN,
        consuming the same draws), so the two percentiles are positively correlated and combining
        their SEs independently OVERSTATES the interval — conservative, in the direction that
        makes a pass harder rather than easier.

        Three-way, like every other verdict in this module: CI above `tol` ⇒ SENSITIVE, CI below
        ⇒ BLIND, CI straddling ⇒ INDETERMINATE. Too little data is never a pass, and never a
        reject either.

    ⚠ WHAT ONE SEED CANNOT SAY. The ratified bar (2) is *"comparable lift at comparable
    seed-to-seed range"* — and a range is not a single-seed quantity. The surrogate's median lift
    was +0.016 against the registered arm's +0.036, but the disqualifying fact was its **range of
    0.033** against the incumbent's 0.009: it was not reliably positive at all. So this function
    binds only what one seed can carry; the range belongs to `poscontrol --seeds N`, and
    registering an arm requires that sweep. Stated here rather than left implicit, because an
    unstated scope limit is how F122 happened. (The surrogate's absorption range is 41.5% across
    three seeds — 80.2% to 121.6% — so its instability is not confined to the percentile.)

    ⚠ AND IT IS STILL THE SAME GAUSSIAN-WALK TAPE, with a planted effect of a shape we chose.
    SENSITIVE here means "not blind to THIS effect", never "sensitive to whatever is in the
    market".
    """
    corpus_fn = corpus_fn or fs.make_corpus
    # ⚠ `tol` IS PART OF THE KEY (D030 seat, 2026-08-13). It was omitted, and the seat demonstrated
    # the consequence live: two calls differing only in `tol` returned the SAME object, whose
    # `tol` field reported the first call's value. No shipped path passes a differing tol today —
    # but `judge(tol=…)` is exactly what `factory_realtape` uses, so a stale field would have
    # laundered a wrong answer rather than raising.
    # ⚠ `lift_mode` joins `tol` in the key for the same reason `tol` did. Two modes USUALLY produce
    # different tols, which would discriminate on its own — but not always: both fall back to
    # NULL_BAND_CAP on a non-positive lift, and there they collide while `lift_registered` below
    # still differs. Relying on a downstream value to accidentally discriminate the key is the
    # bug, not the collision.
    key = (arm, days, seed, k, tol, getattr(corpus_fn, "tape_id", "synthetic"),
           lift_mode or TOL_LIFT_MODE)
    if key in _PC_CACHE:
        return _PC_CACHE[key]

    ref = _planted_reference(days, seed, k, corpus_fn, verbose=False, lift_mode=lift_mode)
    tol = ref["tol"] if tol is None else tol
    planted, rows_p = ref["corpus"], ref["rows"]

    # The free side. `judge` has already walked exactly this (its first probe IS
    # rule_planted_signal on the edge-free tape) and hands it over rather than paying twice.
    if free_rows is None or free_pool is None or free_summary is None:
        free_corpus = free_corpus if free_corpus is not None else corpus_fn(days, seed, 0.0)
        free_rows, _ = fb.backtest(free_corpus, fs.rule_planted_signal, **GEOMETRY)
        free_pool = []
        free_pairs, _ = sc.placebo_rank(free_rows, free_corpus, arm, k=k, seed=seed,
                                        rule=fs.rule_planted_signal, pool_sink=free_pool)
        free_summary = sc.summarize(free_pairs, arm)

    pool_p = []
    pairs_p, dropout = sc.placebo_rank(rows_p, planted, arm, k=k, seed=seed,
                                       rule=fs.rule_planted_signal, pool_sink=pool_p)
    s = sc.summarize(pairs_p, arm)

    out = {"arm": arm, "days": days, "seed": seed, "k": k, "tol": tol,
           "rule": "rule_planted_signal", "neutral_rule": "rule_dumb",
           "lift_registered": ref["lift"], "ci_registered": ref["ci"], "dropout": dropout,
           "lift_mode": ref["lift_mode"]}

    if (s.get("insufficient") or free_summary.get("insufficient") or len(pool_p) < 2
            or len(free_pool) < 2 or not rows_p or not free_rows):
        out.update({"verdict": "INDETERMINATE", "why": "too few rows or placebos to measure"})
        _PC_CACHE[key] = out
        return out

    cand_gain = st.mean([r["r_gross"] for r in rows_p]) - st.mean([r["r_gross"] for r in free_rows])
    pool_gain = st.mean(pool_p) - st.mean(free_pool)
    shift = s["mean_percentile"] - free_summary["mean_percentile"]
    se = (s["se"] ** 2 + free_summary["se"] ** 2) ** 0.5     # conservative — see the docstring
    slo, shi = shift - 1.959964 * se, shift + 1.959964 * se
    out.update({"cand_gain": cand_gain, "pool_gain": pool_gain,
                "n_pool_planted": len(pool_p), "n_pool_free": len(free_pool),
                "pct_planted": s["mean_percentile"], "pct_free": free_summary["mean_percentile"],
                "shift": shift, "shift_ci": [slo, shi], "n": s["n"],
                "lift_planted": s["mean_percentile"] - 0.5})

    if cand_gain <= 0:
        # The planted effect never reached the candidate side. Nothing downstream is readable —
        # same posture as `derive_tol`'s non-positive-lift fallback: refuse, do not divide.
        out.update({"verdict": "INDETERMINATE", "absorption": None,
                    "why": f"the candidate side GAINED NOTHING from the planted effect "
                           f"({cand_gain:+.4f}R) — this tape cannot test sensitivity"})
        _PC_CACHE[key] = out
        return out

    # ★★ THE NULL CONTROL FOR THE POSITIVE CONTROL (D030 seat, 2026-08-13 — its top finding).
    # This module was built because a null test had no positive control. The positive control
    # then shipped with no NULL control: nobody had asked what the SHIFT statistic reads when the
    # true answer is zero. `rule_dumb` is that question — epp≈0.51, no selection relationship to
    # the planted signal, so its candidates draw the same ambient drift its placebos draw and the
    # true shift is 0. The seat measured it over 10 seeds and it is NOT zero for two of three
    # arms: uniform −0.0087 [−0.0119, −0.0054] and time −0.0159 [−0.0198, −0.0120], the latter
    # 128% OF THE ENTIRE DETECTION BAR, against price's clean +0.0005 [−0.0059, +0.0068].
    #
    # ⇒ THE LEVEL→SHIFT REPAIR MOVED THE CONFOUND, IT DID NOT REMOVE IT. `planted − 0.5` counted
    # STANDING bias as eyesight; `planted − edge_free` counts CHANGE IN bias as eyesight. Today
    # that term is negative for both non-registered arms, so the shipped readings understate and
    # no verdict on record is wrong — but the sign is a property of these arms on this tape, not
    # of the design, and an arm carrying time's magnitude with the opposite sign would collect a
    # full `tol` of free "sensitivity".
    #
    # THE RESPONSE IS REFUSAL, NOT CORRECTION. Subtracting a noisy neutral estimate would invent
    # a corrected point estimate and add its variance to the bar. Instead the arm's own null
    # control must be CLEAN — the neutral shift's whole CI inside ±tol, the same equivalence form
    # and the same ruler used everywhere else in this module — or the run cannot certify anything
    # and says INDETERMINATE. Dirty instrument, no verdict.
    if free_corpus is None:            # a caller that handed rows but not the tape they came from
        free_corpus = corpus_fn(days, seed, 0.0)
    rows_n, _ = fb.backtest(planted, fs.rule_dumb, **GEOMETRY)
    free_n, _ = fb.backtest(free_corpus, fs.rule_dumb, **GEOMETRY)
    pairs_np, _ = sc.placebo_rank(rows_n, planted, arm, k=k, seed=seed, rule=fs.rule_dumb)
    pairs_nf, _ = sc.placebo_rank(free_n, free_corpus, arm, k=k, seed=seed, rule=fs.rule_dumb)
    s_np, s_nf = sc.summarize(pairs_np, arm), sc.summarize(pairs_nf, arm)
    # ★ AND IT IS THREE-WAY TOO — the first cut of this gate was NOT, and it re-committed the
    # module's own oldest error one layer down. It asked only `CI inside ±tol ⇒ clean, else
    # DIRTY`, which convicts an underpowered null control as a biased one. `rule_dumb` fires on
    # ~15× fewer candidates than `rule_planted_signal` (2303 vs 35194 at 200 days), so its
    # interval is far wider at the same day count: measured, the incumbent's neutral control at
    # 200 days is ±0.0089 against a tol of 0.0085 — WIDER THAN THE BAND while its point estimate
    # sits at ≈+0.0005, i.e. as clean as it looks and simply not yet resolved. Under the two-way
    # form that read "DIRTY" and made the positive control UNPASSABLE AT EVERY SIZE TESTED, which
    # is FOLD 4's disease wearing the sensitivity half's clothes.
    #   inside  ⇒ CLEAN · outside ⇒ DIRTY (a real change-in-bias term) · straddling ⇒ UNRESOLVED.
    # Both non-clean states still withhold SENSITIVE — you cannot certify sensitivity on an
    # instrument you have not shown is zeroed — but only DIRTY is a finding about the ARM, and
    # UNRESOLVED is answered by more days rather than by a redesign.
    if s_np.get("insufficient") or s_nf.get("insufficient"):
        neutral_shift, neutral_ci, neutral_state = None, None, None
    else:
        neutral_shift = s_np["mean_percentile"] - s_nf["mean_percentile"]
        nse = (s_np["se"] ** 2 + s_nf["se"] ** 2) ** 0.5
        neutral_ci = [neutral_shift - 1.959964 * nse, neutral_shift + 1.959964 * nse]
        if (-tol) <= neutral_ci[0] and neutral_ci[1] <= tol:
            neutral_state = "CLEAN"
        elif neutral_ci[0] > tol or neutral_ci[1] < -tol:
            neutral_state = "DIRTY"
        else:
            neutral_state = "UNRESOLVED"
    out.update({"neutral_shift": neutral_shift, "neutral_ci": neutral_ci,
                "neutral_state": neutral_state,
                "neutral_clean": (neutral_state == "CLEAN") if neutral_state else None})

    absorption = pool_gain / cand_gain
    # ★ THREE-WAY, the same shape the null verdict was repaired into: a straddling interval is
    # too little data, which is never a pass AND never a reject.
    detects = slo > tol
    refuted = shi < tol
    # ★ ABSORPTION BINDS ON RULE-SELECTED ARMS ONLY — the floor below is measured, not argued.
    absorbs = absorption >= ABSORPTION_MAX
    binding_absorption = arm in sc.ARMS_RULE_SELECTED
    out.update({"absorption": absorption, "detects": detects, "refuted": refuted,
                "absorbs": absorbs, "absorption_binds": binding_absorption})
    if binding_absorption and absorbs:
        out["verdict"] = "BLIND"
    elif neutral_state == "DIRTY":
        # ★ The instrument's own null is not zero for this arm — refuse, do not correct.
        out["verdict"] = "INDETERMINATE"
        out["why"] = (f"THE ARM'S NULL CONTROL IS DIRTY — on the epp-neutral rule, where the true "
                      f"shift is 0, this arm reads {neutral_shift:+.4f} "
                      f"[{neutral_ci[0]:+.4f}, {neutral_ci[1]:+.4f}], entirely outside ±{tol:.4f}. "
                      f"Its shift statistic carries a change-in-bias term of the same order as "
                      f"the bar, so a SENSITIVE here would not be sensitivity.")
    elif neutral_state != "CLEAN":
        out["verdict"] = "INDETERMINATE"
        out["why"] = (f"THE NULL CONTROL IS UNRESOLVED — the epp-neutral rule fires on far fewer "
                      f"candidates, so its interval "
                      f"[{neutral_ci[0]:+.4f}, {neutral_ci[1]:+.4f}] is still wider than the "
                      f"±{tol:.4f} band. Nothing here says the arm is biased; it says this run "
                      f"cannot yet show it is not. Raise --days.")
    elif detects:
        out["verdict"] = "SENSITIVE"
    elif refuted:
        out["verdict"] = "BLIND"
    else:
        out["verdict"] = "INDETERMINATE"
        out["why"] = (f"the shift CI [{slo:+.4f}, {shi:+.4f}] straddles the ±{tol:.4f} band — "
                      f"underpowered, not blind. Raise --days.")

    if verbose:
        print_positive_control(out)
    _PC_CACHE[key] = out
    return out


def print_positive_control(pc):
    """Separated from the measurement so `judge` can print it UNDER its own header — the verdict
    is computed before the report block, and a positive control that printed itself arrived
    above the section title it belongs to."""
    # ★ THE RULE IS NAMED (D030 seat, MINOR-5). SENSITIVE is a claim about
    # (arm × THIS rule × THIS effect shape), and the founding sentence of this module is that one
    # rule samples an arm's residual at one point. Printing the verdict without the rule invited
    # exactly the over-reading the module exists to prevent — `timeaxis` in particular gates a
    # TIME-axis pass on a control run with an epp rule that is not among its own probes.
    print(f"  ── POSITIVE CONTROL — arm '{pc['arm']}' against a KNOWN planted effect "
          f"({fs.DEFAULT_EFFECT_PT:g}pt over {fs.DRIFT_MIN}m), via rule "
          f"'{pc.get('rule', 'rule_planted_signal')}' ──")
    if pc.get("absorption") is None:
        print(f"     ⇒ {pc['verdict']} — {pc.get('why', 'not measurable')}")
        return
    lo, hi = pc["shift_ci"]
    mark = "✗" if pc["absorbs"] else "✓"
    scope = "" if pc["absorption_binds"] else \
        f"  — REPORTED, not binding: floor ≈{POOL_ABSORPTION_FLOOR:.0%} for pool arms"
    print(f"     candidate side gains {pc['cand_gain']:+.4f}R · placebo pool gains "
          f"{pc['pool_gain']:+.4f}R  ⇒ ABSORPTION {pc['absorption']:+.1%}  "
          f"{mark} (bar < {ABSORPTION_MAX:.0%}){scope}")
    print(f"     percentile {pc['pct_free']:.4f} edge-free → {pc['pct_planted']:.4f} planted  "
          f"⇒ SHIFT {pc['shift']:+.4f} [{lo:+.4f}, {hi:+.4f}]  "
          f"{'✓' if pc['detects'] else ('✗' if pc['refuted'] else '?')} vs the ±{pc['tol']:.4f} band")
    if pc.get("neutral_shift") is None:
        print("     null control (rule_dumb): NOT MEASURABLE — n too small")
    else:
        nlo, nhi = pc["neutral_ci"]
        state = pc["neutral_state"]
        mark = {"CLEAN": "✓ clean", "DIRTY": "✗ DIRTY", "UNRESOLVED": "? UNRESOLVED"}[state]
        tail = {"CLEAN": "",
                "DIRTY": "   ⇒ the shift statistic is not zero where it must be",
                "UNRESOLVED": "   ⇒ wider than the band — not a finding about the arm"}[state]
        print(f"     null control — same statistic on epp-neutral 'rule_dumb', where the true "
              f"shift is 0:\n"
              f"       {pc['neutral_shift']:+.4f} [{nlo:+.4f}, {nhi:+.4f}]  "
              f"{mark} vs ±{pc['tol']:.4f}{tail}")
    print(f"     ⇒ {pc['verdict']}"
          + ("   (ONE SEED — bar (2)'s seed-to-seed range needs `poscontrol --seeds N`)"
             if pc["verdict"] == "SENSITIVE" else
             f"   — {pc.get('why', 'this arm cannot see an edge that IS there; its null means nothing')}"))


def judge(arm, days=DEFAULT_DAYS, seed=DEFAULT_SEED, k=DEFAULT_K, verbose=True, probes=None,
          tol=None, corpus_fn=None, poscontrol=True, lift_mode=None):
    corpus_fn = corpus_fn or fs.make_corpus
    probes = probes if probes is not None else PROBES
    if tol is None:
        tol = derive_tol(days, seed, k, verbose=verbose, corpus_fn=corpus_fn, lift_mode=lift_mode)
    free = corpus_fn(days, seed, 0.0)
    rows_out, results = [], {}
    pc_free = {}                       # handed to the positive control so the free side is
    #                                    walked ONCE, not twice — its first probe IS that walk
    for name, rule, why, binding in probes:
        rows, _ = fb.backtest(free, rule, **GEOMETRY)
        sink = [] if rule is fs.rule_planted_signal else None
        pairs, dropout = sc.placebo_rank(rows, free, arm, k=k, seed=seed, rule=rule,
                                         pool_sink=sink)
        if sink is not None:
            pc_free = {"free_corpus": free, "free_rows": rows, "free_pool": sink,
                       "free_summary": sc.summarize(pairs, arm)}
        s = sc.summarize(pairs, arm)
        epp = sc.entry_price_percentile(rows, free)
        if s.get("insufficient"):
            results[name] = {"binding": binding, "insufficient": True}
            continue
        lo, hi = s["ci95"]
        half = (hi - lo) / 2
        # ★ THE EQUIVALENCE FORM, via the same chokepoint every gate null passes through.
        # allow_unmatched=True is typed ON PURPOSE and is the documented exhibit path: that
        # refusal exists to stop an unmatched arm's null being quoted as a claim ABOUT THE
        # MARKET (the bidirectional confound buries real edges). Every verdict here is a claim
        # about THE INSTRUMENT, on a synthetic tape whose answer is known, and judging candidate
        # arms is the entire function of this module — refusing them would leave it unable to
        # judge anything except the incumbent.
        inside, note = sc.null_verdict(s, tol, allow_unmatched=True)
        # ★ THREE-WAY, and the first draft of this repair got it WRONG — worth recording because
        # it is the same over-reach in the opposite direction. `null_verdict` answers ONE question
        # ("is this certified null?") so it may return INSUFFICIENT POWER on any wide interval.
        # A criterion that must also say REJECTED cannot inherit that ordering: an interval lying
        # ENTIRELY OUTSIDE the band is a confident non-equivalence no matter how wide it is.
        # Checking power first would have reported the grossly biased `time` arm (0.5952, CI far
        # above the band) as "inconclusive". Equivalence testing has three outcomes, not two.
        outside = lo > 0.5 + tol or hi < 0.5 - tol
        results[name] = {"binding": binding, "mean": s["mean_percentile"], "ci": [lo, hi],
                         "half": half, "epp": epp.get("mean"), "n": s["n"],
                         "inside": inside, "outside": outside,
                         "underpowered": (half > tol) and not outside,
                         "note": note, "dropout": dropout, "why": why}
        rows_out.append(s["mean_percentile"])

    binding_rows = [r for r in results.values() if r.get("binding")]
    usable = [r for r in binding_rows if not r.get("insufficient")]
    if len(usable) < len([p for p in probes if p[3]]):
        verdict = "INDETERMINATE"
    elif any(r["outside"] for r in usable):
        verdict = "REJECTED"               # a CI clear of the band convicts at any width
    elif any(r["underpowered"] for r in usable):
        verdict = "INDETERMINATE"          # too little data — NEVER a pass, and never a reject
    elif all(r["inside"] for r in usable):
        verdict = "QUALIFIES"
    else:
        verdict = "REJECTED"

    # ★ SENSITIVITY GATES ONLY THE PASS (F132, 2026-08-13). The asymmetry is the whole reason the
    # existing record survives this repair: an arm biased on an edge-free tape is disqualified
    # WHATEVER its power, so REJECTED needs no positive control and F030/F031/F131 are untouched.
    # A PASS is the direction that was never earned, so it — and only it — now has to buy one.
    # ★ COMPUTED ALWAYS, GATING ONLY THE PASS (D030 seat, SERIOUS-5). The VERDICT asymmetry is
    # sound — a biased arm is disqualified whatever its power — but running the control only on a
    # would-be pass preserved the DIAGNOSTIC failure that cost the previous session: F131's
    # 400-day REJECT of the surrogate was "uninformative in both directions" and it took an
    # external blind seat to find out why, when the control would have printed
    # "absorption 121.6% ⇒ BLIND" beside it. A reject that also says WHY is the whole point.
    pc = None
    if not poscontrol:
        if verdict == "QUALIFIES":
            verdict = "UNVALIDATED"        # never silently emit the unearned verdict
    else:
        pc = positive_control(arm, days, seed, k, corpus_fn=corpus_fn, tol=tol,
                              verbose=False, lift_mode=lift_mode, **pc_free)
        if verdict == "QUALIFIES":
            if pc["verdict"] == "BLIND":
                verdict = "BLIND"
            elif pc["verdict"] != "SENSITIVE":
                verdict = "INDETERMINATE"
    spread = (max(rows_out) - min(rows_out)) if len(rows_out) > 1 else None

    if verbose:
        axis = "TIME AXIS" if probes is TIME_PROBES else "SLOPE TEST"
        print(f"═══ {axis} — arm '{arm}' · {days} days · k={k} · seed {seed} "
              f"· sl {GEOMETRY['sl_pt']:g}pt / hold {GEOMETRY['max_hold_min']}m ═══")
        for name, rule, why, binding in probes:
            r = results[name]
            tag = "  " if binding else "· "
            if r.get("insufficient"):
                print(f"  {tag}{name:22s} INSUFFICIENT (n<2)")
                continue
            mark = "✗" if r["outside"] else ("?" if r["underpowered"] else ("✓" if r["inside"] else "✗"))
            wide = f"  ⚠ INSUFFICIENT POWER (±{r['half']:.4f} > tol ±{tol:.4f})" \
                if r["underpowered"] else ""
            print(f"  {tag}{mark} {name:22s} epp {r['epp']:.3f}  n={r['n']:6d}  "
                  f"{r['mean']:.4f} [{r['ci'][0]:.4f}, {r['ci'][1]:.4f}] ±{r['half']:.4f}{wide}")
            print(f"       {why}" + ("" if binding else "   (reported only — NOT a pass condition)"))
        if spread is not None:
            print(f"\n  rule-to-rule spread across {len(rows_out)} probe(s): {spread:.4f}")
            print(f"    reference — unmatched arm 0.164 · dead repair 0.179 · "
                  f"registered arm at 40d 0.018")
        if pc is not None:
            print()
            print_positive_control(pc)
        # ★ THE RULER IS STAMPED ON THE VERDICT (ruling of 2026-08-13, second half).
        # Before the switch nothing recorded WHICH ruler produced a verdict, so a pre-switch and a
        # post-switch row were indistinguishable in any log or findings entry. A verdict without
        # its ruler is not a reproducible verdict.
        print(f"\n  ⇒ {verdict}   (equivalence form: whole CI inside 0.5 ± {tol:.4f}"
              f" · ruler '{lift_mode or TOL_LIFT_MODE}')")
        if verdict == "INDETERMINATE":
            print("    (INSUFFICIENT POWER — not a pass and not a reject. Under the OLD span form")
            print("     this same data would have bought a confident verdict. Raise --days.)")
        if verdict == "BLIND":
            print("    (The null is CLEAN and it means NOTHING — the arm cannot see a planted")
            print("     effect either. A scorer null on both tapes is dead, not passing.)")
        if verdict == "UNVALIDATED":
            print("    (The null is clean, but the positive control was SKIPPED. This is the")
            print("     verdict this module used to print as QUALIFIES — F132.)")
        tape = getattr(corpus_fn, "tape_id", None)
        print(f"  ⚠ {tape} tape. Qualifying here is necessary, never sufficient." if tape
              else "  ⚠ Gaussian-walk tape. Qualifying here is necessary, never sufficient.")
    return verdict, results, spread


def sweep_positive_control(arm, days=DEFAULT_DAYS, seed=DEFAULT_SEED, k=DEFAULT_K,
                           n_seeds=DEFAULT_SWEEP_SEEDS, corpus_fn=None, verbose=True):
    """★ BAR (2) IN FULL — the part one seed cannot carry.

    The ratified condition is *"lift comparable to the registered arm's at comparable seed-to-seed
    RANGE"*, and the surrogate arm failed on the range, not the median: +0.016 median against the
    incumbent's +0.036, but a range of **0.033** against the incumbent's **0.009** — so it was not
    reliably positive at all, and a single lucky seed would have shown a healthy number.

    THE RULE, stated so it invents no threshold: **every seed must be SENSITIVE.** An arm that
    goes blind at one seed in five is not an instrument, and this needs no "how much range is too
    much" constant — the detection bar each seed must clear is the same derived one. The median
    and range are REPORTED next to the ratified reference figures so a reader can see how close
    the call was, never so a threshold can be fitted to them (L025: sweep it, report the median).
    """
    seeds = [seed + i for i in range(n_seeds)]
    runs = []
    for s in seeds:
        pc = positive_control(arm, days, s, k, corpus_fn=corpus_fn, verbose=False)
        runs.append(pc)
        if verbose:
            if pc.get("absorption") is None:
                print(f"  seed {s}  {pc['verdict']:13s} — {pc.get('why', '')}")
            else:
                print(f"  seed {s}  {pc['verdict']:13s} shift {pc['shift']:+.4f} "
                      f"[{pc['shift_ci'][0]:+.4f}, {pc['shift_ci'][1]:+.4f}]  "
                      f"absorption {pc['absorption']:+7.1%}"
                      + (f"  · null control {pc['neutral_state']}"
                         if pc.get("neutral_state") else ""))
                # ★ AND WHY, not merely WHAT. The sweep printed a verdict and swallowed the
                # reason, so a run blocked by the NULL CONTROL looked identical to one blocked by
                # a straddling shift — opposite remedies (raise --days vs the arm is contaminated).
                # Caught by the suite asking this output to name the control it failed.
                if pc.get("why"):
                    print(f"            {pc['why']}")

    ok = [r for r in runs if r.get("absorption") is not None]
    out = {"arm": arm, "days": days, "k": k, "seeds": seeds, "runs": runs}
    if not ok:
        out["verdict"] = "INDETERMINATE"
        if verbose:
            print("\n  ⇒ INDETERMINATE — no seed produced a readable measurement")
        return out

    shifts = [r["shift"] for r in ok]
    regs = [r["lift_registered"] for r in ok]
    absorb = [r["absorption"] for r in ok]
    n_sens = sum(1 for r in ok if r["verdict"] == "SENSITIVE")
    out.update({"shift_median": st.median(shifts), "shift_range": max(shifts) - min(shifts),
                "reg_median": st.median(regs), "reg_range": max(regs) - min(regs),
                "absorption_median": st.median(absorb),
                "n_sensitive": n_sens, "n_measured": len(ok)})
    out["verdict"] = ("SENSITIVE" if (len(ok) == len(seeds)
                                      and all(r["verdict"] == "SENSITIVE" for r in ok))
                      else "BLIND" if any(r["verdict"] == "BLIND" for r in ok)
                      else "INDETERMINATE")
    if verbose:
        print(f"\n  ── across {len(seeds)} seed(s) · {days} days · k={k} ──")
        print(f"     candidate '{arm}'  shift median {out['shift_median']:+.4f}  "
              f"range {out['shift_range']:.4f}")
        print(f"     registered '{sc.ARM_REGISTERED}'  planted lift median "
              f"{out['reg_median']:+.4f}  range {out['reg_range']:.4f}  (the ruler, not a rival)")
        print(f"     absorption median {out['absorption_median']:+.1%}  "
              f"(bar < {ABSORPTION_MAX:.0%}"
              + ("" if arm in sc.ARMS_RULE_SELECTED
                 else f"; NOT binding here — pool floor ≈{POOL_ABSORPTION_FLOOR:.0%}") + ")")
        print(f"     ratified reference (F134) — registered ~+0.036 range 0.009 · "
              f"the REJECTED surrogate +0.016 range 0.033, absorption 103%")
        print(f"\n  ⇒ {out['verdict']}   "
              f"({out['n_sensitive']}/{len(seeds)} seed(s) SENSITIVE — every seed must be)")
        print("  ⚠ Sensitivity is NECESSARY, never sufficient. The null still binds separately,")
        print("    and both live on a tape whose effect we chose the shape of.")
    return out


def compare_tol_rulers(days=DEFAULT_DAYS, seed=DEFAULT_SEED, k=DEFAULT_K, seeds=1, arms=None,
                       verbose=True, judge_arms=True):
    """★ THE GAUGE THAT SHIPS WITH THE `tol` PROPOSAL (F142) — both rulers, side by side.

    It answers the only three questions the D030 proposal can be judged on, and it answers them
    by RUNNING both, never by arguing:

      1. HOW INFLATED is the level-based band?  `tol_level / tol_shift − 1`, per seed.
      2. WHAT DOES THE REPAIR COST?  Each arm judged under both rulers, verdicts side by side —
         so a REJECTED→INDETERMINATE flip (F140's warning, the direction the intuition gets
         backwards) is VISIBLE rather than discovered afterwards.
      3. WHAT DOES IT DO TO THE POSITIVE CONTROL?  Explicitly ambiguous a priori: a narrower band
         makes DETECTION easier (`slo > tol`) and the NULL CONTROL harder (CLEAN needs the
         neutral CI inside ±tol). the proposal required this measured before it could be adopted,
         not after it.

    ⚠ It reports. It decides nothing and changes no default — `tol` is an acceptance criterion and
    only the ratifying authority may switch it.
    """
    arms = list(arms if arms is not None else sc.ARMS)
    seed_list = [seed + i for i in range(max(1, seeds))]
    rows = []
    for s in seed_list:
        r = {"seed": s}
        for mode in TOL_LIFT_MODES:
            ref = _planted_reference(days, s, k, verbose=False, lift_mode=mode)
            r[mode] = {"tol": ref["tol"], "lift": ref["lift"], "baseline": ref["baseline"],
                       "pct_planted": ref["pct_planted"], "verdicts": {}, "pc": {}}
        if judge_arms:
            for mode in TOL_LIFT_MODES:
                tol = r[mode]["tol"]
                for arm in arms:
                    v, res, _ = judge(arm, days, s, k, verbose=False, tol=tol, lift_mode=mode)
                    # WHY the verdict is what it is — the flip F140 predicts is REJECTED→
                    # INDETERMINATE via the power gate, and only the reason distinguishes it
                    # from an INDETERMINATE that was always going to be one.
                    binding = [x for x in res.values() if x.get("binding")
                               and not x.get("insufficient")]
                    r[mode]["verdicts"][arm] = {
                        "verdict": v,
                        "n_outside": sum(1 for x in binding if x["outside"]),
                        "n_underpowered": sum(1 for x in binding if x["underpowered"]),
                        "max_half": max([x["half"] for x in binding], default=None)}
                    pc = positive_control(arm, days, s, k, tol=tol, verbose=False, lift_mode=mode)
                    # ⛔ THIS READ A KEY THAT IS NEVER WRITTEN (D030 seat, 2026-08-13).
                    # `positive_control` emits `neutral_state` / `neutral_shift` / `neutral_ci`;
                    # there has never been a `null_control` key. So every "null None" printed in
                    # data/logs/factory_tolcompare_*.log was a TYPO WEARING THE COSTUME OF A
                    # MEASUREMENT, and the proposal read it as evidence — it explained the None as
                    # "the control short-circuits before reaching it", which the same log line
                    # refutes: a SENSITIVE verdict is unreachable unless `neutral_state == CLEAN`.
                    # The gauge could not answer the one question §4(d) of the proposal asked it.
                    r[mode]["pc"][arm] = {"verdict": pc["verdict"],
                                          "shift": pc.get("shift"),
                                          "shift_ci": pc.get("shift_ci"),
                                          "neutral_state": pc.get("neutral_state"),
                                          "neutral_ci": pc.get("neutral_ci")}
        rows.append(r)

    if verbose:
        print(f"═══ tol RULER COMPARISON — {days} days · k={k} · {len(seed_list)} seed(s) "
              f"from {seed_list[0]} ═══")
        print("  level = planted_pct − 0.5 (today, SHIPPED)   ·   "
              "shift = planted_pct − free_pct (PROPOSED, F142)")
        for r in rows:
            lv, sh = r["level"], r["shift"]
            infl = (lv["tol"] / sh["tol"] - 1) if sh["tol"] else float("nan")
            print(f"\n  ── seed {r['seed']} ──")
            print(f"     level: lift {lv['lift']:+.4f} (planted {lv['pct_planted']:.4f} − 0.5)"
                  f"          ⇒ tol ±{lv['tol']:.4f}")
            print(f"     shift: lift {sh['lift']:+.4f} (planted {sh['pct_planted']:.4f} − free "
                  f"{sh['baseline']:.4f}) ⇒ tol ±{sh['tol']:.4f}")
            print(f"     ⇒ the shipped band is INFLATED by {infl:+.1%}  "
                  f"(the registered arm's standing bias on the edge-free tape is "
                  f"{sh['baseline'] - 0.5:+.4f})")
            if not judge_arms:
                continue
            print(f"     {'arm':10s} {'level':>28s}   {'shift':>28s}")
            for arm in arms:
                a, b = lv["verdicts"][arm], sh["verdicts"][arm]
                def _tag(x):
                    return (f"{x['verdict']:14s} out{x['n_outside']} pw{x['n_underpowered']}")
                flip = "  ← FLIPPED" if a["verdict"] != b["verdict"] else ""
                print(f"     {arm:10s} {_tag(a):>28s}   {_tag(b):>28s}{flip}")
            print(f"     {'arm':10s} {'positive control':>28s}   {'positive control':>28s}")
            for arm in arms:
                a, b = lv["pc"][arm], sh["pc"][arm]
                flip = "  ← FLIPPED" if a["verdict"] != b["verdict"] else ""
                def _pc(x):
                    ci = x.get("neutral_ci")
                    ci_s = f"[{ci[0]:+.4f},{ci[1]:+.4f}]" if ci else "—"
                    return f"{x['verdict']} / null {x.get('neutral_state') or '—'} {ci_s}"
                print(f"     {arm:10s} {_pc(a):>34s}   {_pc(b):>34s}{flip}")
        print("\n  ⛔ THE VERDICT IS NON-MONOTONE IN tol, SO 'FLIP = INFORMATION LOST' IS FALSE")
        print("    FOR THE else-BRANCH (D030 seat, 2026-08-13). Mapped on the real 400d price CIs:")
        print("      tol ≥0.0020 REJECTED(outside) · ≥0.0051 INDETERMINATE · ≥0.0075 REJECTED(else)")
        print("      · ≥0.0149 QUALIFIES.   The shipped 0.0086 sits in the else window, which is")
        print("    reachable ONLY because a band that wide declares a half-width-0.0075 probe")
        print("    'powered'. That conviction was BOUGHT BY THE INFLATION, not earned despite it —")
        print("    the same 'too-wide band declares adequate power where there is none' mechanism")
        print("    tests/test_factory_harness.sh already pins as manufacturing a FALSE REJECTION.")
        print("  ⚠ 'Information given back, never a verdict overturned' SURVIVES ONLY for")
        print("    outside-driven rejects (uniform/time, out2) — a CI wholly clear of the band")
        print("    convicts at any width, so a narrower band cannot weaken it. For an else-branch")
        print("    reject the opposite holds, and that is the one the price arm carries.")
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--arm", default=sc.ARM_REGISTERED,
                   choices=list(sc.ARMS) + list(sc.ARMS_RULE_SELECTED))
    r.add_argument("--no-poscontrol", dest="poscontrol", action="store_false",
                   help="skip the positive control — a clean null then reads UNVALIDATED, "
                        "never QUALIFIES (F132)")
    # rule-selected arms are judgeable here but are NOT in `sc.ARMS` — see the note on
    # ARMS_RULE_SELECTED in factory_scorer: membership of ARMS promises rule-agnosticism.
    r.add_argument("--days", type=int, default=DEFAULT_DAYS)
    r.add_argument("--seed", type=int, default=DEFAULT_SEED)
    r.add_argument("--k", type=int, default=DEFAULT_K)
    c = sub.add_parser("compare")
    c.add_argument("--days", type=int, default=DEFAULT_DAYS)
    c.add_argument("--seed", type=int, default=DEFAULT_SEED)
    c.add_argument("--k", type=int, default=DEFAULT_K)
    t = sub.add_parser("timeaxis")
    t.add_argument("--days", type=int, default=DEFAULT_DAYS)
    t.add_argument("--seed", type=int, default=DEFAULT_SEED)
    t.add_argument("--k", type=int, default=DEFAULT_K)
    p = sub.add_parser("poscontrol")
    p.add_argument("--arm", default=sc.ARM_REGISTERED,
                   choices=list(sc.ARMS) + list(sc.ARMS_RULE_SELECTED))
    p.add_argument("--days", type=int, default=DEFAULT_DAYS)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--k", type=int, default=DEFAULT_K)
    p.add_argument("--seeds", type=int, default=DEFAULT_SWEEP_SEEDS,
                   help="how many consecutive seeds to sweep; 1 skips the range and is NOT "
                        "the registration bar")
    tc = sub.add_parser("tolcompare", help="both `tol` rulers side by side (F142 proposal gauge)")
    tc.add_argument("--days", type=int, default=DEFAULT_DAYS)
    tc.add_argument("--seed", type=int, default=DEFAULT_SEED)
    tc.add_argument("--k", type=int, default=DEFAULT_K)
    tc.add_argument("--seeds", type=int, default=1)
    tc.add_argument("--bands-only", dest="judge_arms", action="store_false",
                    help="just the two bands — skip re-judging every arm under both (fast)")
    a = ap.parse_args()

    if a.cmd == "tolcompare":
        compare_tol_rulers(a.days, a.seed, a.k, a.seeds, judge_arms=a.judge_arms)
        return 0

    if a.cmd == "run":
        verdict, _, _ = judge(a.arm, a.days, a.seed, a.k, poscontrol=a.poscontrol)
        return 0 if verdict == "QUALIFIES" else 1
    if a.cmd == "poscontrol":
        print(f"═══ POSITIVE CONTROL — arm '{a.arm}' · {a.days} days · k={a.k} · "
              f"{a.seeds} seed(s) from {a.seed} ═══")
        out = sweep_positive_control(a.arm, a.days, a.seed, a.k, a.seeds)
        return 0 if out["verdict"] == "SENSITIVE" else 1
    if a.cmd == "timeaxis":
        out = {}
        tol = derive_tol(a.days, a.seed, a.k)     # ONE ruler for every arm — R1 FOLD 9
        for arm in sc.ARMS:
            v, res, sp = judge(arm, a.days, a.seed, a.k, probes=TIME_PROBES, tol=tol)
            out[arm] = (v, sp, res)
            print()
        print("═══ TIME-AXIS SUMMARY — the epp criterion cannot see this ═══")
        for arm, (v, sp, res) in out.items():
            e = res.get("rule_early_session", {}).get("mean")
            l = res.get("rule_late_session", {}).get("mean")
            gap = f"early−late {e - l:+.4f}" if (e is not None and l is not None) else "gap n/a"
            star = " ← registered" if arm == sc.ARM_REGISTERED else ""
            print(f"  {arm:9s} {v:14s} {gap}{star}")
        print("\n  ⚠ TIME-NEUTRAL here is necessary, never sufficient — it is one more axis")
        print("    checked, not a licence. The epp criterion still binds separately.")
        return 0 if all(v == "QUALIFIES" for v, _, _ in out.values()) else 1
    verdicts = {}
    tol = derive_tol(a.days, a.seed, a.k)         # ONE ruler for every arm — R1 FOLD 9
    for arm in sc.ARMS:
        v, _, sp = judge(arm, a.days, a.seed, a.k, tol=tol)
        verdicts[arm] = (v, sp)
        print()
    print("═══ SUMMARY ═══")
    for arm, (v, sp) in verdicts.items():
        star = " ← registered" if arm == sc.ARM_REGISTERED else ""
        print(f"  {arm:9s} {v:14s} spread {sp:.4f}{star}" if sp is not None
              else f"  {arm:9s} {v}{star}")
    return 0 if verdicts[sc.ARM_REGISTERED][0] == "QUALIFIES" else 1


if __name__ == "__main__":
    sys.exit(main())
