#!/usr/bin/env python3
"""factory_notblind.py — THE EDGE FACTORY, Phase 1: THE NOT-BLIND GATE.

Charter §3-Phase-1: *"The harness must pass NOT-BLIND validation before any real hypothesis
touches it (§3.39e): a synthetic tape with a planted edge must be detected; an edge-free
shuffled tape must return null; a known-dumb rule must lose ≈ costs. GATE: all three not-blind
checks pass, mutation-tested."* Plus the fourth check `factory_synthetic.py` carries in its own
contract: a price-position-only rule the scorer is REQUIRED to return null on.

This file points `factory_scorer.py` at `factory_synthetic.py` — an instrument at a tape whose
answer is known before the instrument sees it — and writes what happened to the append-only
registry. It is the whole reason the previous system's Sharpe 13.76 / 0.0%-overfit result could
not be caught: every referee was computed inside the same biased simulator it was certifying.

━━ IT DOES NOT LICENSE ITSELF, AND THAT IS DELIBERATE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Charter §4.4/§4.7: the not-blind gate's licence comes from a **fresh-context external seat,
never self-certification.** So this module writes `survived` or `killed` for the MEASUREMENT and
refuses to write `licensed` under any flag. The last row it prints is what is still owed.

━━ WHY THE NULL BAND IS DERIVED, NOT CHOSEN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A null needs a band, and a band picked by hand is a band picked to pass. The band here is a
fixed fraction of the lift THIS RUN measured on the planted tape (check 1): a tape claimed
edge-free may not carry more than a quarter of the percentile lift a real planted edge produces.
If check 1's lift comes in small, the band tightens and the null checks fail as INSUFFICIENT
POWER — the safe direction. Nothing here can be loosened by re-rolling a seed, which is the
p-hacking move the equivalence form exists to block.

━━ THE DAY COUNT IS A POWER CALCULATION, AND IT IS SET BY THE WIDEST CHECK ━━━━━━━━━━━━━━━━━━
Measured at 8 days / k=20 (2026-08-12), every null check failed as INSUFFICIENT POWER — which is
the design working, and which makes N derivable instead of chosen. Check 1's lift is ≈0.041, so
the band is ≈0.0103. Per-day sd, recovered as halfwidth·√8/1.96 from that run:

    check 4b (price-matched confound)  halfwidth 0.0479  sd 0.0691  ⇒ N ≥ 173   ← BINDING
    check 2  (planted rule, free tape) halfwidth 0.0312  sd 0.0450  ⇒ N ≥  73
    check 3  (dumb rule)               halfwidth 0.0350  sd 0.0505  ⇒ N ≥  92
    check 2b (informationless rule)    halfwidth 0.0582  sd 0.0840  ⇒ N ≥ 255 †

`GATE_DAYS = 250` is 1.45× the binding requirement. **The band is NOT loosened to make a check
pass** — that is the one move this whole file exists to prevent.

† 2b and 3 are power-starved for a second reason worth naming: `rule_random` and `rule_dumb`
fire ~12×/day where `rule_planted_signal` fires ~170×/day, so a band calibrated on a dense rule
starves a sparse one. Densifying an INFORMATIONLESS rule keeps it informationless — more draws
of the same nothing — so the gate runs them at several seeds / several phase offsets. There is a
hard limit on this: as coverage approaches the whole session the candidate set becomes the
placebo pool and the percentile is 0.5 BY CONSTRUCTION, i.e. the check passes vacuously. Both
stay near 12-15% of RTH minutes and the coverage is printed with the result so that degeneracy
is visible rather than assumed away.

Verbs:
  gate [--days N] [--k K] [--seed S] [--no-register]      run all four checks
"""
import argparse
import datetime
import json
import os
import statistics as st
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))
import factory_synthetic as fs                 # noqa: E402  the tapes whose answer is known
import factory_backtest as fb                  # noqa: E402  the walker + the frozen costs
import factory_scorer as sc                    # noqa: E402  the placebo scorer
import factory_registry as reg                 # noqa: E402  the multiplicity denominator

GATE_DAYS = 250                                # see the header — set by the BINDING check, 4b
GATE_K = 20                                    # placebo draws per candidate
GATE_SEED = 20260812

# Densification factors for the two SPARSE informationless rules (header †). Not tuning: these
# rules carry no information at any density, so the only thing changed is n. Coverage is
# reported; if it ever approaches the placebo pool the check goes vacuous.
RANDOM_SEEDS = 5                               # 5 × 12 = ~60 draws/day ≈ 15% of RTH
DUMB_OFFSETS = (0, 7, 15, 22)                  # 4 × 13 = ~52 draws/day ≈ 13% of RTH

# The trade geometry the gate runs. Fixed, because a gate whose geometry moves is a gate that
# can be tuned into passing. sl=20pt against the generator's 3pt/min sigma is ≈1.2 sd over the
# 30-minute hold, so both barriers are genuinely reachable — a stop nothing ever touches would
# make every arm identical and the gate vacuous.
GEOMETRY = dict(sl_pt=20.0, tp_r=None, max_hold_min=30, sym=fb.SYNTHETIC)

NULL_BAND_FRACTION = 0.25                      # of check 1's measured lift
NULL_BAND_CAP = 0.05                           # never wider than 5 percentile points


def rule_random_dense(bars):
    """`fs.rule_random` at several seeds — the same informationless rule, more draws of it.
    De-duplicated, because the same minute drawn twice is one entry, not two facts."""
    seen = {}
    for s in range(RANDOM_SEEDS):
        for idx, side in fs.rule_random(bars, seed=1000 + s):
            seen.setdefault(idx, side)
    return sorted(seen.items())


def rule_dumb_dense(bars):
    """`fs.rule_dumb` at several phase offsets. The offset was always arbitrary; running all of
    them removes the arbitrariness as well as buying the n."""
    out = []
    for off in DUMB_OFFSETS:
        out += [(i, "long") for i in
                range(fs.LOOKBACK + off, len(bars) - fs.DRIFT_MIN - 1, 30)]
    return sorted(set(out))


def _coverage(rows, corpus):
    """Fraction of available minutes the rule actually occupies — the degeneracy guard."""
    if not corpus:
        return 0.0
    minutes = sum(len(b) for b in corpus.values())
    return len(rows) / minutes if minutes else 0.0


def _fmt(s):
    if s.get("insufficient"):
        return f"n={s['n']} — insufficient"
    return (f"n={s['n']} days={s['n_days']} mean {s['mean_percentile']:.4f} "
            f"CI [{s['ci95'][0]:.4f}, {s['ci95'][1]:.4f}] MDE {s['mde_percentile']:.4f}")


def gate(days=GATE_DAYS, k=GATE_K, seed=GATE_SEED, register=True):
    checks, ok = [], True

    def record(num, name, passed, detail):
        nonlocal ok
        ok = ok and passed
        checks.append({"check": num, "name": name, "pass": passed, "detail": detail})
        print(f"  {'✓' if passed else '✗'} [{num}] {name}\n      {detail}")

    print(f"═══ NOT-BLIND GATE — {days} days/tape, k={k}, seed {seed}, "
          f"sl {GEOMETRY['sl_pt']:g}pt / hold {GEOMETRY['max_hold_min']}m ═══")
    free = fs.make_corpus(days, seed, 0.0)
    planted = fs.make_corpus(days, seed, fs.DEFAULT_EFFECT_PT)
    band = dict(band="none")                   # percentile is cost-invariant; check 3 uses costs

    # ── CHECK 1 — a planted edge MUST be detected ───────────────────────────────────────────
    print("\n── 1. a synthetic tape with a planted edge is DETECTED ──")
    rows1, rej1 = fb.backtest(planted, fs.rule_planted_signal, **GEOMETRY, **band)
    s1 = sc.score(rows1, planted, k=k, seed=seed)
    reg_arm = s1["arms"][sc.ARM_REGISTERED]
    det, why = sc.detect_verdict(reg_arm)
    record(1, f"planted edge detected on the registered ({sc.ARM_REGISTERED}) arm", det,
           f"{_fmt(reg_arm)} · {why}")
    lift = reg_arm["mean_percentile"] - 0.5 if not reg_arm.get("insufficient") else 0.0
    tol = min(NULL_BAND_CAP, NULL_BAND_FRACTION * lift) if lift > 0 else NULL_BAND_CAP
    print(f"      → measured lift {lift:+.4f} ⇒ null band ±{tol:.4f} "
          f"({NULL_BAND_FRACTION:.0%} of it, capped at {NULL_BAND_CAP})")
    print(f"      · time-matched arm {s1['arms']['time']['mean_percentile']:.4f} at entry-price "
          f"pct {s1['entry_price_percentile']['mean']:.3f} "
          f"(confound_risk={s1['entry_price_percentile']['confound_risk']}) — this rule buys "
          f"local maxima, so the unmatched arm BURIES its real edge")

    # ── CHECK 2 — an edge-free tape MUST return null ────────────────────────────────────────
    print("\n── 2. an edge-free tape returns NULL (equivalence, not 'the CI spans 0.5') ──")
    rows2, _ = fb.backtest(free, fs.rule_planted_signal, **GEOMETRY, **band)
    s2 = sc.score(rows2, free, k=k, seed=seed)
    n2 = s2["arms"][sc.ARM_REGISTERED]
    passed, why = sc.null_verdict(n2, tol)
    record(2, "the SAME rule on the edge-free tape is null", passed, f"{_fmt(n2)} · {why}")
    # …and a rule carrying NO information must be null even where an edge EXISTS. Without this
    # row, a scorer that merely detects "this tape drifts" would pass check 1 and check 2 both.
    rows2b, _ = fb.backtest(planted, rule_random_dense, **GEOMETRY, **band)
    s2b = sc.score(rows2b, planted, k=k, seed=seed)
    n2b = s2b["arms"][sc.ARM_REGISTERED]
    passed_b, why_b = sc.null_verdict(n2b, tol)
    cov2b = _coverage(rows2b, planted)
    record("2b", "an INFORMATIONLESS rule is null even on the tape that HAS the edge",
           passed_b and cov2b < 0.5,
           f"{_fmt(n2b)} · {why_b} · coverage {cov2b:.1%} of minutes"
           f"{' — ⚠ DEGENERATE, the candidate set IS the placebo pool' if cov2b >= 0.5 else ''}")

    # ── CHECK 3 — a known-dumb rule loses ≈ costs ───────────────────────────────────────────
    print("\n── 3. a known-dumb rule loses ≈ costs ──")
    rows3g, _ = fb.backtest(free, rule_dumb_dense, **GEOMETRY, band="none")
    rows3c, _ = fb.backtest(free, rule_dumb_dense, **GEOMETRY, band="central")
    s3 = sc.score(rows3g, free, k=k, seed=seed, arms=(sc.ARM_REGISTERED,))
    n3 = s3["arms"][sc.ARM_REGISTERED]
    passed3, why3 = sc.null_verdict(n3, tol)
    cov3 = _coverage(rows3g, free)
    record(3, "the dumb rule finds no edge (its selection is null)",
           passed3 and cov3 < 0.5,
           f"{_fmt(n3)} · {why3} · coverage {cov3:.1%} of minutes"
           f"{' — ⚠ DEGENERATE' if cov3 >= 0.5 else ''}")
    cost_r = fb.cost_in_r(GEOMETRY["sl_pt"], "central", sym=GEOMETRY["sym"])
    gross = st.mean([r["r_gross"] for r in rows3g])
    net = st.mean([r["r_net"] for r in rows3c])
    # THE MECHANICAL HALF: the entire gap between gross and net must be the cost, to floating
    # precision. This is what catches "costs silently not applied" — the defect that would make
    # every Phase-2 survivor's economics fiction while every percentile stayed correct.
    record("3b", "…and its whole loss vs gross IS the cost, exactly",
           abs((gross - net) - cost_r) < 1e-9,
           f"gross {gross:+.4f}R − net {net:+.4f}R = {gross - net:+.6f}R "
           f"vs frozen cost {cost_r:+.6f}R ({fb.costs('central', sym=fb.SYNTHETIC):.2f}pt at a "
           f"{GEOMETRY['sl_pt']:g}pt stop)")

    # ── CHECK 4 — the confound rule, BOTH values ────────────────────────────────────────────
    print("\n── 4. the price-position-only rule: above chance unmatched, NULL matched ──")
    rows4, _ = fb.backtest(free, fs.rule_price_extreme, **GEOMETRY, **band)
    s4 = sc.score(rows4, free, k=k, seed=seed)
    t4, p4 = s4["arms"]["time"], s4["arms"]["price"]
    det4, why4 = sc.detect_verdict(t4)
    record("4a", "scores ABOVE chance against a TIME-matched placebo (the trap is live)",
           det4, f"{_fmt(t4)} · {why4} · entry-price pct "
                 f"{s4['entry_price_percentile']['mean']:.3f}")
    null4, why4b = sc.null_verdict(p4, tol)
    record("4b", "and returns NULL once the placebo is PRICE-matched", null4,
           f"{_fmt(p4)} · {why4b}")
    print("      ⚠ BOTH VALUES OR IT CERTIFIES NOTHING: a scorer null on both is not passing,"
          "\n        it is dead, and would report null for a real edge too.")

    mde = max([c for c in (reg_arm.get("mde_percentile"), n2.get("mde_percentile"),
                           n2b.get("mde_percentile"), n3.get("mde_percentile"),
                           p4.get("mde_percentile")) if c is not None])
    print(f"\n  {'PASS' if ok else 'FAIL'} — {sum(1 for c in checks if c['pass'])}/{len(checks)}"
          f" checks · worst achieved MDE {mde:.4f} percentile points")
    print("  ⚠ BOUND: this proves the harness is not blind ON A GAUSSIAN-WALK TAPE. It does not"
          "\n    prove calibration on real microstructure — that is the vendor corpus (Phase 2)"
          "\n    and the shadow phase (Phase 3).")

    result = {"days": days, "k": k, "seed": seed, "geometry": GEOMETRY,
              "null_band": tol, "measured_lift": lift, "worst_mde": mde,
              "checks": checks, "passed": ok,
              "rejections_check1": rej1,
              "dropout_registered_arm": reg_arm.get("dropout"),
              "cost_band_check3": "central", "cost_r_check3": cost_r}
    if register:
        _register(result)
    # ⚠ UNCONDITIONAL, and it did not used to be. This disclaimer lived inside `_register` until
    # the mutation suite caught it: a `--no-register` run — which is what every test, every
    # rehearsal and every quick check uses — printed its verdict with NO statement that the
    # verdict licenses nothing. The disclaimer is a property of THE GATE, not of the registry
    # write, and attaching it to the write meant the quieter path was the less honest one.
    wrote = "survived" if ok else "killed"
    print(f"\n  ⛔ NOT LICENSED BY THIS RUN. This gate reports `{wrote}`, which is a MEASUREMENT."
          "\n     Charter §4.4/§4.7 requires a fresh-context external seat to license the"
          "\n     harness; self-certification is exactly what this file exists to prevent."
          "\n     That seat has not run.")
    return ok, result


def _register(result):
    """Append the run to the append-only registry. The spec whose sha256 is frozen is THIS FILE:
    the gate's specification and its implementation are the same artifact, so there is no gap
    between what was registered and what ran."""
    name = f"notblind-{datetime.datetime.now().astimezone().strftime('%Y%m%dT%H%M%S')}"
    reg.cmd_register(types.SimpleNamespace(
        file=os.path.abspath(__file__), kind="harness-gate", name=name,
        payload=json.dumps({"days": result["days"], "k": result["k"], "seed": result["seed"],
                            "geometry": result["geometry"],
                            "null_band": result["null_band"],
                            "checks": [c["check"] for c in result["checks"]]})))
    reg.cmd_verdict(types.SimpleNamespace(
        name=name, stage="harness",
        outcome="survived" if result["passed"] else "killed",
        mde=result["worst_mde"],
        payload=json.dumps({"passed": result["passed"],
                            "failed_checks": [c["check"] for c in result["checks"]
                                              if not c["pass"]],
                            "measured_lift": result["measured_lift"],
                            "cost_r": result["cost_r_check3"]})))
    # ★ NOT `licensed` — the outcome above can only ever be `survived` or `killed`. Charter
    # §4.4/§4.7: the licence is a fresh-context external seat's to give, and a module that
    # certified itself would be the 13.76-Sharpe failure again in miniature — the referee
    # computed inside the thing it referees. The disclaimer that says so is printed by `gate()`,
    # unconditionally, because a run that skips registration must not also skip the caveat.
    #
    # ⚠ The disclaimer here USED TO HARDCODE "survived" and it lied on the first real run: the
    # gate came back 5/7 FAIL, this function correctly wrote `killed`, and the summary under it
    # announced `survived`. Never restate an outcome from memory of the happy path.


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gate")
    g.add_argument("--days", type=int, default=GATE_DAYS)
    g.add_argument("--k", type=int, default=GATE_K)
    g.add_argument("--seed", type=int, default=GATE_SEED)
    g.add_argument("--no-register", action="store_true")
    g.add_argument("--json")
    a = ap.parse_args()
    ok, result = gate(a.days, a.k, a.seed, register=not a.no_register)
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(result, fh, indent=1, default=str)
        print(f"  wrote {a.json}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
