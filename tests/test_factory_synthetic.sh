#!/usr/bin/env bash
# test_factory_synthetic.sh — invariants of the KNOWN-NULL device (bin/factory_synthetic.py).
#
# ★ EVERY ASSERTION HERE IS A MUTATION PROOF, NOT A GREEN RUN.
# The module's own `verify` already prints ✓ for each property. That is worth nothing on its
# own: a check never observed to FAIL certifies nothing. This file breaks each property on
# purpose and requires the matching check to go red. If a mutation leaves `verify` green, the
# check is decorative and the mutation is the bug report.
#
# The regression pin is §2. The first version of the generator let planted drift STACK: each
# planted move re-fired the signal that planted it, so a declared +6.0pt effect measured
# +89.34pt with the signal firing on ~350 of 390 minutes. `verify` passed anyway, because the
# assertion was `CI lower bound > 0` — true of a runaway trend as surely as of a 6-point edge.
# The check now requires the DECLARED size to sit inside the measured CI, and §2 below proves
# that form can fail where the old one could not.
#
# Run: bash tests/test_factory_synthetic.sh
set -uo pipefail
cd "$(dirname "$0")/.."
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf '  ✓ %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  ✗ %s\n     wanted: %s\n     got:    %s\n' "$1" "$2" "$3"; }
chk() { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1" "$2" "$3"; fi; }

# The module's own power calculation sets 60; the gate is run at its real sample size here,
# because a mutation test at a sample size nobody uses certifies a configuration nobody runs.
DAYS=60

echo "── 1. the unmutated device passes, and fast enough to be run every time ─────────"
OUT=$(python3 bin/factory_synthetic.py verify --days "$DAYS" 2>&1); RC=$?
chk "verify exits 0 on the real generator" "0" "$RC"
chk "it reports PASS" "yes" "$(echo "$OUT" | grep -q 'PASS —' && echo yes || echo no)"
chk "it states its own bound rather than claiming validation" "yes" \
    "$(echo "$OUT" | grep -qi 'BOUND' && echo yes || echo no)"

# Each mutation runs in a throwaway tree so nothing can leak into the real module.
#
# ⚠ The first version copied only the four modules it thought were needed. Every mutant then
# died on `ModuleNotFoundError: autonomy_gauges` — and since the assertion was "the mutant exits
# non-zero", ALL SIX mutation checks passed while proving nothing at all. A test that cannot
# tell "the mutation was caught" from "the mutant could not start" is the flattering-defect
# shape this whole file exists to catch, and it was in the file catching it. Caught by asserting
# WHICH check failed, not merely that something did — the exit code alone was the vacuous half.
#
# Now: a symlink farm of the real bin/ with only the mutant swapped in, plus a guard that the
# mutant actually RAN. ROOT resolves to the temp dir, so the module's own sys.path insert picks
# up the farm.
# ⚠ Link EVERY entry, not just bin/*.py — the import chain reaches every sibling module in bin/ (the scorer →
# the walker → harness_ruler), and a partial farm reproduced
# the same startup failure one layer deeper. Symlinking directories too makes the farm complete
# without copying the tree.
mutate() {  # $1 = sed expression
  local d f base; d=$(mktemp -d); mkdir -p "$d/bin"
  for f in bin/*; do
    base=$(basename "$f")
    [ "$base" = "factory_synthetic.py" ] && continue
    [ "$base" = "__pycache__" ] && continue
    ln -s "$PWD/$f" "$d/bin/$base"
  done
  sed "$1" bin/factory_synthetic.py > "$d/bin/factory_synthetic.py"
  ( cd "$d" && python3 bin/factory_synthetic.py verify --days "$DAYS" 2>&1 )
  local rc=$?; rm -rf "$d"; return $rc
}

# A mutant that never reached its checks proves nothing — assert it got there.
ran() { echo "$1" | grep -q 'the edge-free tape is edge-free' && echo yes || echo no; }

echo "── 2. ★ THE STACKING PIN — a wrong effect SIZE must fail, not just a wrong sign ──"
# Restore the original stacking bug: plant unconditionally, so drift compounds into a trend.
MUT=$(mutate 's/if effect_pt and not pending:/if effect_pt:/'); RC=$?
chk "stacked drift is REJECTED (the +89pt-vs-+6pt tape)" "1" "$RC"
chk "  …and the mutant actually RAN (not a startup failure)" "yes" "$(ran "$MUT")"
chk "  …and it fails on the size check specifically" "yes" \
    "$(echo "$MUT" | grep -q '✗ planted episodes deliver the DECLARED size' && echo yes || echo no)"
# The OLD assertion form, on that same broken tape, would have waved it through:
OLDFORM=$(python3 - <<'PY'
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), "bin"))
import factory_synthetic as fs, harness_ruler as ca
# rebuild the stacking bug in-process
src_make = fs.make_tape
def stacking(date_str, seed, effect_pt=0.0, truth=None):   # truth arg: make_corpus passes it
    import random, statistics as st
    rng = random.Random(seed); stamps = fs._session_minutes(date_str)
    px = fs.START_PX; bars, closes, pending = [], [], []
    for i, ts in enumerate(stamps):
        drift = sum(d for _, d in pending)
        step = rng.gauss(drift, fs.SIGMA_PT); target = px + step; path = [px]
        for k in range(1, fs.TICKS_PER_MIN + 1):
            frac = k / fs.TICKS_PER_MIN
            path.append(px + (target - px) * frac +
                        (0.0 if k == fs.TICKS_PER_MIN else rng.gauss(0, fs.SIGMA_PT * 0.35)))
        bars.append(fs._bar_from_path(ts, path)); px = path[-1]; closes.append(px)
        pending = [(n - 1, d) for n, d in pending if n - 1 > 0]
        if effect_pt:
            s = fs._signal(closes, i)
            if s: pending.append((fs.DRIFT_MIN, s * effect_pt / fs.DRIFT_MIN))
    return bars
fs.make_tape = stacking
corpus = fs.make_corpus(12, 20260811, fs.DEFAULT_EFFECT_PT)
moves = []
for d, bars in corpus.items():
    closes = [b["close"] for b in bars]
    for i, side in fs.rule_planted_signal(bars):
        j = min(i + fs.DRIFT_MIN, len(closes) - 1)
        mv = closes[j] - closes[i]
        moves.append((d, mv if side == "long" else -mv))
ci = ca.cluster_bootstrap_ci(moves, weight="day")
old_form_passes = ci[0] > 0
new_form_passes = ci[0] <= fs.DEFAULT_EFFECT_PT <= ci[1] and ci[0] > 0
print(f"{'yes' if old_form_passes else 'no'} {'yes' if new_form_passes else 'no'}")
PY
)
chk "  …the OLD 'CI > 0' form would have PASSED that tape (why the pin exists)" "yes" \
    "$(echo "$OLDFORM" | awk '{print $1}')"
chk "  …the NEW form rejects it" "no" "$(echo "$OLDFORM" | awk '{print $2}')"

echo "── 3. the edge-free tape must be able to stop being edge-free ──────────────────"
MUT=$(mutate 's/step = rng.gauss(drift, SIGMA_PT)/step = rng.gauss(drift + 0.5, SIGMA_PT)/'); RC=$?
chk "a drifting 'null' tape is REJECTED" "1" "$RC"
chk "  …and the mutant actually RAN (not a startup failure)" "yes" "$(ran "$MUT")"
chk "  …on the drift check" "yes" \
    "$(echo "$MUT" | grep -q '✗ per-minute drift is inside the null band' && echo yes || echo no)"

echo "── 4. structural integrity checks must be able to fail ─────────────────────────"
# ⚠ The first mutation here set FLOOR_RANGE_PT=0.0 — which produces NO flat bars at all, since
# a 12-tick random path is essentially never flat. The mutant failed on an unrelated check and
# the FLAT assertion never fired: a mutation that does not cause the defect proves nothing about
# the check that is supposed to catch it. This one collapses high and low onto the close.
MUT=$(mutate 's/"high": round(hi, 2), "low": round(lo, 2),/"high": round(c, 2), "low": round(c, 2),/'); RC=$?
chk "flat bars are REJECTED once the floor is removed" "1" "$RC"
chk "  …and the mutant actually RAN (not a startup failure)" "yes" "$(ran "$MUT")"
chk "  …on the FLAT-bar check" "yes" \
    "$(echo "$MUT" | grep -q '✗ no FLAT bars' && echo yes || echo no)"

echo "── 5. determinism must be able to fail ─────────────────────────────────────────"
MUT=$(mutate 's/rng = random.Random(seed)$/rng = random.Random()/'); RC=$?
chk "an unseeded generator is REJECTED" "1" "$RC"
chk "  …and the mutant actually RAN (not a startup failure)" "yes" "$(ran "$MUT")"
chk "  …on the determinism check" "yes" \
    "$(echo "$MUT" | grep -q '✗ same seed ⇒ byte-identical corpus' && echo yes || echo no)"

echo "── 6. the CONFOUND rule is the point — it must really be confounded ────────────"
# rule_price_extreme must select extreme entry prices on a tape with NO edge. If it stops
# doing that, not-blind check 4 (price-matched placebo returns null) proves nothing, because
# the rule it points at no longer carries the confound it is supposed to carry.
# ⚠ The first mutation set the long branch to `if False:`, leaving the SHORT branch still
# selecting local maxima — the confound survived, the check still passed, and the mutant exited
# non-zero for an unrelated reason. Firing on every bar regardless of price position is the
# mutation that actually removes the confound.
MUT=$(mutate 's/if c <= min(window):/if True:/'); RC=$?
chk "a de-fanged confound rule is REJECTED" "1" "$RC"
chk "  …and the mutant actually RAN (not a startup failure)" "yes" "$(ran "$MUT")"
chk "  …on the entry-price-position check" "yes" \
    "$(echo "$MUT" | grep -q '✗ entry-price position is extreme' && echo yes || echo no)"

echo "── 7. the no-look-ahead boundary is real ───────────────────────────────────────"
LOOK=$(python3 - <<'PY'
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), "bin"))
import factory_synthetic as fs
bars = fs.make_tape("2026-01-05", 1, 0.0)
closes = [b["close"] for b in bars]
i = 100
base = fs._signal(closes, i)
# mutate every bar AFTER i; a signal that reads the future would change
future = closes[:i + 1] + [c + 500.0 for c in closes[i + 1:]]
same = fs._signal(future, i) == base
# and it must genuinely depend on the PAST, else "unchanged" is vacuous
past = [c - 500.0 for c in closes[:i]] + closes[i:]
moved = fs._signal(past, i) != base
print(f"{'yes' if same else 'no'} {'yes' if moved else 'no'}")
PY
)
chk "the signal ignores every bar after its own minute" "yes" "$(echo "$LOOK" | awk '{print $1}')"
chk "  …and does depend on the bars before it (so the above is not vacuous)" "yes" \
    "$(echo "$LOOK" | awk '{print $2}')"

echo "── 8. synthetic rows can never be mistaken for tape ────────────────────────────"
# ★ THE ROW SCHEMA IS DECLARED HERE, NOT READ OFF A LIVE TAPE. The private tree compared these
# rows against a recorded session directory; that corpus does not ship, and a comparison against
# an EMPTY corpus would pass vacuously — "no key disagreed" because no key was read. So the
# contract is written down: one walker consumes both tapes, therefore both carry exactly these
# keys. If a real loader in your tree emits a different set, this is the assertion to change,
# and changing it is the moment to re-check every caller.
TAG=$(python3 - <<'PY'
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), "bin"))
import factory_synthetic as fs
CANONICAL = {"time", "open", "high", "low", "close", "volume", "src"}
bars = fs.make_tape("2026-01-05", 1, 0.0)
tagged = all(b.get("src") == "SYNTHETIC" for b in bars)
schema = all(set(b) == CANONICAL for b in bars)
print(f"{'yes' if tagged else 'no'} {'yes' if schema else 'no'}")
PY
)
chk "every row is tagged src=SYNTHETIC" "yes" "$(echo "$TAG" | awk '{print $1}')"
chk "every row carries exactly the canonical bar schema (one walker consumes both)" "yes" \
    "$(echo "$TAG" | awk '{print $2}')"

echo
echo "══ $PASS passed, $FAIL failed ══"
[ "$FAIL" -eq 0 ]
