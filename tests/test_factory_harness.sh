#!/usr/bin/env bash
# test_factory_harness.sh — mutation proofs for the Phase-1 harness.
#   bin/factory_backtest.py  (the no-lookahead walker + the frozen costs)
#   bin/factory_scorer.py    (the placebo scorer: the percentile-vs-placebo method)
#   bin/factory_notblind.py  (the gate that points one at the other)
#
# ★ EVERY ASSERTION HERE IS A MUTATION PROOF, NOT A GREEN RUN.
# Charter §3-Phase-1 GATE: *"all three not-blind checks pass, mutation-tested (the 08-11 session
# found seven flattering defects by running/mutating, zero by reading — assume this harness has
# them too)."* Each module's selftest already prints ✓ per property; that is worth nothing on its
# own, because a check never observed to FAIL certifies nothing. So each property is broken on
# purpose here and the MATCHING check must go red — asserted by name, never by exit code alone.
#
# ⚠ THE EXIT-CODE-ONLY TRAP, inherited verbatim from test_factory_synthetic.sh: a mutant that
# dies on ModuleNotFoundError also exits non-zero, so "the mutant failed" proves nothing. Every
# assertion below names the check it expects to go red, and `ran()` proves the mutant reached its
# checks at all.
#
# ★ THE LOAD-BEARING ONE IS §6. The null verdict uses an EQUIVALENCE form (the whole CI must lie
# inside the band) rather than "does the CI span 0.5". The span form is satisfied by a WIDE
# interval, so it gets EASIER to pass with less data — §6 restores it and requires a deliberately
# under-powered gate run to flip from FAIL to PASS. That is the whole difference between a
# validator and a rubber stamp, and it is the one mutation whose absence would be invisible.
#
# Run: bash tests/test_factory_harness.sh
set -uo pipefail
cd "$(dirname "$0")/.."
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf '  ✓ %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  ✗ %s\n     wanted: %s\n     got:    %s\n' "$1" "$2" "$3"; }
chk() { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1" "$2" "$3"; fi; }

# Scorer selftests are the slow half (~1 min each). Kept at the module's own default sample size:
# a mutation test at a sample size nobody uses certifies a configuration nobody runs.
SC_ARGS="--days 12 --seed 7 --k 30"

# A symlink farm of the real bin/ with ONE module swapped for its mutant. Directories are linked
# too — the import chain reaches every sibling module in bin/ (scorer → walker → harness_ruler)
# and a farm of top-level .py files alone fails at startup one layer deeper.
# $1 = module basename, $2 = sed expression, $3.. = command to run inside the farm
mutate() {
  local target="$1" sedexpr="$2"; shift 2
  local d f base; d=$(mktemp -d); mkdir -p "$d/bin" "$d/research/factory"
  for f in bin/*; do
    base=$(basename "$f")
    [ "$base" = "$target" ] && continue
    [ "$base" = "__pycache__" ] && continue
    ln -s "$PWD/$f" "$d/bin/$base"
  done
  sed "$sedexpr" "bin/$target" > "$d/bin/$target"
  # ★★★ A MUTATION THAT DOES NOT MUTATE IS A GREEN THAT MEANS NOTHING (2026-08-12, F048).
  #   Measured: §10's M1 sed targeted probe labels that commit 2d179cd73 had renamed, so the
  #   "mutant" was byte-identical to the real program. The test then asserted the real program
  #   behaves like the real program and passed — a rubber stamp. Worse, the commit that broke it
  #   is titled "mutation-pinned", and its own message's "38/38 pass" was true and tested nothing.
  #   This is the SAME defect F029 recorded hours earlier, arriving through a different door.
  #   ⇒ every mutation in this file is now checked for having actually changed a byte. Silent
  #   mutation-rot becomes a loud failure, for every current and future mutation, without anyone
  #   having to remember to look. This is the verb; the lesson was the noun.
  if cmp -s "bin/$target" "$d/bin/$target"; then
    echo "✗✗ DEAD MUTATION — sed '$sedexpr' left bin/$target byte-identical."
    echo "   The 'mutant' IS the unmutated program, so whatever this test asserts is vacuous."
    echo "   Fix the sed to match current source; do NOT delete the check."
    rm -rf "$d"; return 97
  fi
  # The frozen cost model is read by path, so the farm needs it or every mutant dies on the
  # refusal instead of on its mutation.
  ln -s "$PWD/research/factory/cost_model.json" "$d/research/factory/cost_model.json"
  ( cd "$d" && "$@" 2>&1 )
  local rc=$?; rm -rf "$d"; return $rc
}

# Did the mutant reach its checks? $1 = output, $2 = a banner only printed once running.
ran() { echo "$1" | grep -q "$2" && echo yes || echo no; }
# Did the named check go RED? Matches the ✗ marker on the line carrying $2.
red() { echo "$1" | grep -F "$2" | grep -q '✗' && echo yes || echo no; }
grn() { echo "$1" | grep -F "$2" | grep -q '✓' && echo yes || echo no; }
# "Caught" = the check did NOT pass — it went red, or the mutant died before printing it.
# ⚠ Weaker than `red` on purpose, and only used where the mutation can legitimately CRASH the
# selftest (a walker with no bars after entry returns None, and the check then dereferences it).
# Always paired with `ran`, or it degenerates into the exit-code-only trap this file warns about.
caught() { [ "$(grn "$1" "$2")" = "no" ] && echo yes || echo no; }

echo "── 1. the unmutated harness passes ─────────────────────────────────────────────"
OUT=$(python3 bin/factory_backtest.py selftest 2>&1); RC=$?
chk "backtest selftest exits 0" "0" "$RC"
chk "…and reports PASS" "yes" "$(echo "$OUT" | grep -q 'PASS —' && echo yes || echo no)"
BT_BANNER="the entry bar is never walked"

OUT=$(python3 bin/factory_scorer.py selftest $SC_ARGS 2>&1); RC=$?
chk "scorer selftest exits 0" "0" "$RC"
chk "…and reports PASS" "yes" "$(echo "$OUT" | grep -q 'PASS —' && echo yes || echo no)"
SC_BANNER="POSITIVE control"

echo "── 2. ★ THE NO-LOOKAHEAD BOUNDARY — the entry bar must never be walked ─────────"
# Start the walk one minute EARLIER, i.e. include the entry bar itself.
MUT=$(mutate factory_backtest.py 's/mcf.walk_bounds(tape, entry_ts,/mcf.walk_bounds(tape, entry_ts - 60,/' \
      python3 bin/factory_backtest.py selftest)
chk "the mutant reached its checks" "yes" "$(ran "$MUT" "$BT_BANNER")"
chk "walking the entry bar is CAUGHT" "yes" \
    "$(red "$MUT" 'a 500pt spike in the ENTRY bar changes nothing')"
# The opposite mutation — never walking the bar AFTER entry — must be caught too, or the check
# is satisfied by a walker that is simply blind rather than careful.
MUT=$(mutate factory_backtest.py 's/b\["time"\] <= horizon/b["time"] <= entry_ts/' \
      python3 bin/factory_backtest.py selftest)
chk "the blind mutant reached its checks" "yes" "$(ran "$MUT" "$BT_BANNER")"
chk "a walker that sees NOTHING after entry is caught too" "yes" \
    "$(caught "$MUT" 'the same spike one bar LATER does terminate at the stop')"

echo "── 3. costs — applied, in the right direction, and exactly ─────────────────────"
# ⚠ ANCHOR ROT, FOUND 2026-08-13 WHILE DOING SOMETHING ELSE. Commit 79b25dc0e (F088, "the cost
# model is US100 POINTS with no symbol") added a `sym` argument to `cost_in_r`, and this sed —
# which spells the call site verbatim — silently stopped matching. The farm's cmp-guard did its
# job and turned it into a LOUD red rather than a rubber stamp, exactly as F048 designed it to.
# ⇒ THE UNCOMFORTABLE PART: this suite has therefore been FAILING since that commit and nobody
# ran it. A mutation harness only protects the runs someone actually performs.
MUT=$(mutate factory_backtest.py 's/"r_net": round(r_gross - cost_in_r(sl_pt, band, sym), 6)/"r_net": round(r_gross, 6)/' \
      python3 bin/factory_backtest.py selftest)
chk "the mutant reached its checks" "yes" "$(ran "$MUT" "$BT_BANNER")"
chk "costs silently NOT applied is caught" "yes" \
    "$(red "$MUT" 'net < gross under every band')"
# ⇒ ANCHOR REPAIRED, not deleted, per the DEAD-MUTATION guard's own instruction: the call site
#   now reads `costs(band, sym=sym)` and the sed spells it that way.
MUT=$(mutate factory_backtest.py 's|return costs(band, sym=sym) / float(sl_pt)|return costs(band, sym=sym)|' \
      python3 bin/factory_backtest.py selftest)
chk "a cost that does not scale with the stop is caught" "yes" \
    "$(red "$MUT" 'cost in R scales as 1/stop')"

echo "── 4. the Phase-0 findings the walker is required to enforce ───────────────────"
MUT=$(mutate factory_backtest.py 's/if drop_flat and b\["high"\] == b\["low"\]:/if False and b["high"] == b["low"]:/' \
      python3 bin/factory_backtest.py selftest)
chk "FLAT (vendor-padded) bars left in the tape is caught" "yes" \
    "$(red "$MUT" '3 planted FLAT bars are dropped and counted')"
# Hold measured in BARS instead of wall-clock time — the quiet-market bias.
MUT=$(mutate factory_backtest.py 's/tape = \[b for b in bars if b\["time"\] <= horizon\]/tape = bars[:entry_idx + 1 + int(max_hold_min)]/' \
      python3 bin/factory_backtest.py selftest)
chk "a bar-counted hold window is caught" "yes" \
    "$(red "$MUT" 'dropping half the bars does not lengthen the hold')"
MUT=$(mutate factory_backtest.py 's/truncated = bars\[-1\]\["time"\] < horizon/truncated = False/' \
      python3 bin/factory_backtest.py selftest)
chk "a truncated hold scored as a real trade is caught" "yes" \
    "$(red "$MUT" "a hold running past the tape's end is flagged")"

echo "── 5. ★ THE PRICE-MATCHED ARM — the confound that produced the 0.725 survivor ──"
# Collapse the price arm into the time arm: no price matching at all.
MUT=$(mutate factory_scorer.py 's/    return \[i for i in win if abs(float(bars\[i\]\["close"\]) - row\["entry"\]) <= band\]/    return win/' \
      python3 bin/factory_scorer.py selftest $SC_ARGS)
chk "the mutant reached its checks" "yes" "$(ran "$MUT" "$SC_BANNER")"
chk "a price arm that does not match price is CAUGHT" "yes" \
    "$(red "$MUT" 'and NOT above chance once price is matched')"
# The entry-price diagnostic must be able to go quiet as well as loud, or it flags everything.
MUT=$(mutate factory_scorer.py 's/^CONFOUND_DEV = 0.15/CONFOUND_DEV = 0.0001/' \
      python3 bin/factory_scorer.py selftest $SC_ARGS)
chk "a confound flag that fires on price-NEUTRAL rules is caught" "yes" \
    "$(red "$MUT" 'the confound rule trips the confound flag')"

echo "── 6. ★★ THE INTERVAL AND THE NULL FORM — the rubber-stamp mutations ───────────"
# 6a. The naive (decision-level) interval instead of the day-clustered one. Decisions inside a
# day share the open, the trend and the news; counting them as independent narrows the CI, and
# the anti-control's price-matched arm then "detects" an edge that is pure arithmetic.
MUT=$(mutate factory_scorer.py 's/    ci = reg or naive/    ci = naive/' \
      python3 bin/factory_scorer.py selftest $SC_ARGS)
chk "the mutant reached its checks" "yes" "$(ran "$MUT" "$SC_BANNER")"
chk "dropping day-clustering manufactures a false positive, and is caught" "yes" \
    "$(red "$MUT" 'and NOT above chance once price is matched')"

# 6b. ★ THE ONE THAT MATTERS. Restore "does the CI span 0.5?" in place of the equivalence form
# and run a deliberately UNDER-POWERED gate. The real form fails it as INSUFFICIENT POWER; the
# span form passes it on a wide interval — a validator that gets easier the less data it has.
UNDER="--days 6 --k 10 --no-register"
REAL=$(python3 bin/factory_notblind.py gate $UNDER 2>&1)
chk "the real gate REFUSES an under-powered run" "yes" \
    "$(echo "$REAL" | grep -q 'INSUFFICIENT POWER' && echo yes || echo no)"
chk "…and fails it rather than certifying" "yes" \
    "$(echo "$REAL" | grep -q 'FAIL —' && echo yes || echo no)"
SPAN='s/^    inside = (0.5 - tol) <= lo and hi <= (0.5 + tol)/    inside = lo <= 0.5 <= hi/;s/^    if half > tol:/    if False:/'
MUT=$(mutate factory_scorer.py "$SPAN" python3 bin/factory_notblind.py gate $UNDER)
chk "the mutant reached its checks" "yes" "$(ran "$MUT" 'a synthetic tape with a planted edge')"
chk "★ the span form passes checks the equivalence form refuses" "yes" \
    "$(grn "$MUT" 'the SAME rule on the edge-free tape is null')"

echo "── 7. the gate cannot license itself ───────────────────────────────────────────"
chk "the gate says so in its own output" "yes" \
    "$(echo "$REAL" | grep -q 'NOT LICENSED BY THIS RUN' && echo yes || echo no)"
chk "no code path writes outcome=licensed" "0" \
    "$(grep -o 'outcome="licensed"' bin/factory_notblind.py | wc -l | tr -d ' ')"
chk "…and the only outcomes it can write are the two measurement verdicts" "yes" \
    "$(grep -q 'outcome="survived" if result\["passed"\] else "killed"' bin/factory_notblind.py \
       && echo yes || echo no)"

echo "── 8. ★ a null on an UNMATCHED arm is REFUSED at the chokepoint ────────────────"
# The rule "never quote a null from an unmatched arm" started life as a memory line. Memory lines
# rot, so it lives in null_verdict() — the one function every null verdict must pass through.
# Removing the refusal must go red, or the enforcement is decorative.
MUT=$(mutate factory_scorer.py 's/    if arm in ARMS and arm != ARM_REGISTERED and not allow_unmatched:/    if False:/' \
      python3 bin/factory_scorer.py selftest $SC_ARGS)
chk "the mutant reached its checks" "yes" "$(ran "$MUT" "$SC_BANNER")"
chk "deleting the unmatched-arm refusal is CAUGHT" "yes" \
    "$(red "$MUT" 'null_verdict REFUSES the time-matched arm')"
# …and the refusal must not be a blanket one, or the registered arm can never return a verdict.
MUT=$(mutate factory_scorer.py 's/    if arm in ARMS and arm != ARM_REGISTERED and not allow_unmatched:/    if True:/' \
      python3 bin/factory_scorer.py selftest $SC_ARGS)
chk "a refusal that also blocks the REGISTERED arm is caught" "yes" \
    "$(red "$MUT" 'the REGISTERED arm is not refused')"

echo "── 9. placebos inherit the CANDIDATE's stop, not a shared one ──────────────────"
# Not a mutation — a direct probe, because the selftest runs a single stop width and a mutation
# there would be invisible. Two rows with different stops must produce placebo pools walked at
# their OWN stop; if the scorer shared one, the wide-stop row's pool would be identical.
# ⇒ ANCHOR REPAIRED: `walk_trade` gained a required `sym` (there is no default instrument, because
#   points measured on one instrument are meaningless on another). The probe passed seven
#   positional arguments and none of them was the symbol, so it died on the refusal rather than on
#   its own assertion — the same rot the section-3 sed carried, arriving through a different door.
PROBE=$(python3 - <<'EOF' 2>&1
import sys; sys.path.insert(0, "bin")
import factory_synthetic as fs, factory_backtest as fb, factory_scorer as sc
corpus = {"2026-01-05": fs.make_tape("2026-01-05", 3, 0.0)}
seen = []
orig = fb.walk_trade
def spy(bars, idx, side, sl_pt, *a, **k):
    seen.append(sl_pt); return orig(bars, idx, side, sl_pt, *a, **k)
fb.walk_trade = spy
rows = []
for sl in (10.0, 40.0):
    r, _ = orig(corpus["2026-01-05"], 100, "long", sl, None, 30, "none", sym=fb.SYNTHETIC)
    r["day"] = "2026-01-05"; rows.append(r)
sc.placebo_rank(rows, corpus, "time", k=5, seed=1)
print("distinct stops walked:", sorted(set(seen)))
EOF
)
chk "both stop widths reach the walker" "yes" \
    "$(echo "$PROBE" | grep -q '10.0, 40.0' && echo yes || echo no)"

echo "── 10. ★ THE SLOPE TEST — the acceptance criterion must DISCRIMINATE ─────────────"
# Built 2026-08-12 after R1 went TERMINAL. Judging an arm with ONE rule samples the epp slope at
# one point, which is how a catastrophically biased arm read as "nearly fine". These proofs are
# the criterion's own not-blind checks: it must PASS the registered arm and REJECT the time arm.
# ★ REWRITTEN 2026-08-12 for the EQUIVALENCE form. The old assertion here was "the registered
# arm QUALIFIES at --days 40" — and pinning it at exactly 40 days is what blinded this suite to
# FOLD 4: under the span form the incumbent REJECTED at 160 days and at 1 of 4 seeds, and no test
# could see it. The honest reading at 40 days is INDETERMINATE for both viable arms, so that is
# what is pinned. A test that demands a PASS from data that cannot support one is the flattering
# shape this file exists to catch.
SL_ARGS="--days 40 --k 20"
OUT=$(python3 bin/factory_slope_test.py run --arm price $SL_ARGS 2>&1)
chk "the registered arm is NOT convicted on thin data" "yes" \
    "$(echo "$OUT" | grep -q '⇒ INDETERMINATE' && echo yes || echo no)"
chk "…and says INSUFFICIENT POWER, naming the band it failed against" "yes" \
    "$(ran "$OUT" 'INSUFFICIENT POWER')"
chk "the null band is DERIVED from a planted-tape lift, not declared" "yes" \
    "$(ran "$OUT" 'null band: planted-tape lift')"
# ★ AND IT MUST NAME WHICH RULER PRODUCED IT (added 2026-08-13 with the `tol` lift_mode work).
# There are now two admissible derivations — `level` (planted−0.5, shipped) and `shift`
# (planted−free, PROPOSED, F142/PROPOSAL_2026-08-13_tol_is_a_level) — and they differ by ~19% at
# the gate's own 250 days. A run that does not say which one it used is unreadable after the fact,
# and a SILENT default flip would move every verdict in the run together. This pins that the label
# is printed AND that the shipped default is still `level`; changing the default must therefore
# break a test rather than pass quietly.
chk "…and NAMES its ruler, with the RATIFIED default `shift`" "yes" \
    "$(ran "$OUT" 'planted-tape lift \[shift\]')"
# ★ THE DEFAULT FLIPPED level -> shift, DELIBERATELY AND ON THE RECORD, and this line
# moved with it — which is the pin doing its job, not the test being bent to fit. The pin exists so
# a SILENT flip breaks a test; a RATIFIED flip is SUPPOSED to require editing this line, and the
# edit is the audit trail. The ruling, and the consequences accepted before it, are dated in the
# originating project log.
chk "…and the ruler's baseline is MEASURED, not the assumed 0.5" "yes" \
    "$(ran "$OUT" 'MEASURED on the edge-free tape')"
OUT=$(python3 bin/factory_slope_test.py run --arm time $SL_ARGS 2>&1)
chk "★ the grossly biased time arm is REJECTED (the criterion still discriminates)" "yes" \
    "$(echo "$OUT" | grep -q '⇒ REJECTED' && echo yes || echo no)"
# M0 — ★ THE THREE-WAY ORDERING, and it pins a bug the author shipped in the first draft of this
# very repair. `null_verdict` answers ONE question, so it may return INSUFFICIENT POWER on any
# wide interval. A criterion that must also say REJECTED cannot inherit that: an interval lying
# ENTIRELY OUTSIDE the band convicts at any width. The draft checked power first and would have
# called the 0.5952 time arm "inconclusive". Restore that ordering and the conviction vanishes.
# ⚠ THE FIRST VERSION OF THIS MUTATION WAS INCOMPLETE and the suite caught it — recorded because
# it is the same error twice in one file: it rewrote the branch CONDITION and left the branch
# BODY saying REJECTED, so the mutant convicted for a different reason and the test read green-ish
# noise. A mutation must produce the DEFECT, not merely a diff. All three edits are needed.
MUT=$(mutate factory_slope_test.py 's/"underpowered": (half > tol) and not outside,/"underpowered": half > tol,/;s/    elif any(r\["outside"\] for r in usable):/    elif any(r["underpowered"] for r in usable):/;s/verdict = "REJECTED"               # a CI clear/verdict = "INDETERMINATE"  # MUTANT: a CI clear/' \
      python3 bin/factory_slope_test.py run --arm time $SL_ARGS)
chk "the mutant reached its checks" "yes" "$(ran "$MUT" 'SLOPE TEST')"
# MEASURED: the mutant reports the 0.4314 / 0.5952 time arm as INDETERMINATE — CIs nowhere near
# the band, called "inconclusive" purely because they are wide. That is the shipped draft bug.
chk "★ checking POWER before non-equivalence loses the conviction entirely" "yes" \
    "$(echo "$MUT" | grep -q '⇒ INDETERMINATE' && echo yes || echo no)"
# M1 — make the NEUTRAL control binding and the epp-extreme probes advisory. The time arm passes
# on rule_dumb alone (epp~0.50 sits at the slope's zero-crossing), so this must stop rejecting it.
# That is exactly the structural blindness R1 FOLD 7 found in gate checks 2b and 3.
# ⚠ THE SED MATCHES ON STRUCTURE, NOT ON THE epp NUMBERS IN THE LABELS (fix 2026-08-12, F048).
#   The previous form pinned "≈0.33"/"≈0.72"/"≈0.50". Commit 2d179cd73 re-labelled those probes to
#   their honest post-F036 positions (0.16/0.95/0.51) and the sed silently stopped matching — a
#   DEAD MUTATION that passed for hours. The numbers are exactly the part that moves when the
#   instrument is corrected, so they are the wrong thing to key on. `MAXIMA", True` and friends
#   carry the pass-condition semantics this mutation is actually about.
MUT=$(mutate factory_slope_test.py 's/MAXIMA", True/MAXIMA", False/;s/MINIMA", True/MINIMA", False/;s/not a pass condition", False/not a pass condition", True/' \
      python3 bin/factory_slope_test.py run --arm time $SL_ARGS)
chk "the mutant reached its checks" "yes" "$(ran "$MUT" 'SLOPE TEST')"
chk "★ judging on the epp-NEUTRAL rule alone stops rejecting the biased arm" "yes" \
    "$(echo "$MUT" | grep -q 'REJECTED' && echo no || echo yes)"
# M2 — ★ RESTORE THE SPAN FORM. This is the defect the 2026-08-12 repair removed, reproduced
# exactly: judge by `lo <= 0.5 <= hi` with no power guard. The registered arm's honest
# INDETERMINATE at 40 days becomes a confident PASS — which is precisely how a whole session's
# readings were taken, and how the criterion came to REJECT the incumbent at other day counts.
# "The span form gets EASIER to pass the less data you have" (factory_scorer.null_verdict).
# ⚠ RUN WITH --no-poscontrol (2026-08-13, F132). The span mutant's null-pass now has to clear a
# POSITIVE CONTROL before it can print QUALIFIES, and at 40 days that control is underpowered —
# so the mutant and the real program would BOTH print INDETERMINATE and this mutation would go
# silently dead, the exact rot the farm's cmp-guard exists to catch but which a semantic collision
# slips past. `--no-poscontrol` isolates the NULL form, which is what M2 is about: it prints
# UNVALIDATED exactly when the null passed, so the discrimination is preserved verbatim.
MUT=$(mutate factory_slope_test.py 's/^        outside = lo > 0.5 + tol or hi < 0.5 - tol/        outside = False/;s/"inside": inside, "outside": outside,/"inside": lo <= 0.5 <= hi, "outside": False,/;s/"underpowered": (half > tol) and not outside,/"underpowered": False,/' \
      python3 bin/factory_slope_test.py run --arm price $SL_ARGS --no-poscontrol)
chk "the mutant reached its checks" "yes" "$(ran "$MUT" 'SLOPE TEST')"
chk "★ the SPAN form buys a confident null-PASS from data the real form calls INDETERMINATE" "yes" \
    "$(echo "$MUT" | grep -q '⇒ UNVALIDATED' && echo yes || echo no)"
REAL_NP=$(python3 bin/factory_slope_test.py run --arm price $SL_ARGS --no-poscontrol 2>&1)
chk "…and the equivalence form abstains on that same data" "yes" \
    "$(echo "$REAL_NP" | grep -q '⇒ INDETERMINATE' && echo yes || echo no)"
# M2b — ★ THE F132 REPAIR, tested on the defect that motivated it. Same span mutant, positive
# control left ON: the unearned pass must NOT survive to the printed verdict.
MUT=$(mutate factory_slope_test.py 's/^        outside = lo > 0.5 + tol or hi < 0.5 - tol/        outside = False/;s/"inside": inside, "outside": outside,/"inside": lo <= 0.5 <= hi, "outside": False,/;s/"underpowered": (half > tol) and not outside,/"underpowered": False,/' \
      python3 bin/factory_slope_test.py run --arm price $SL_ARGS)
chk "the mutant reached its checks" "yes" "$(ran "$MUT" 'SLOPE TEST')"
chk "★ the positive control WITHHOLDS the span form's unearned pass" "yes" \
    "$(echo "$MUT" | grep -q '⇒ QUALIFIES' && echo no || echo yes)"
chk "…and says so by naming the control it ran" "yes" "$(ran "$MUT" 'POSITIVE CONTROL')"
# M3 — loosen the BAND instead of the form, to the old MAX_HALFWIDTH of 0.030 (larger than the
# registered arm's own rule-to-rule spread of 0.018, and 3.7× the gate's null band).
# ⚠ I PREDICTED THIS WOULD MANUFACTURE A PASS. MEASURED, IT DOES THE OPPOSITE — and the opposite
# is more damning. A too-wide band declares adequate power where there is none (±0.0259 no longer
# exceeds ±0.030), and then convicts the INCUMBENT because its CI is not wholly inside the wider
# band. So the loose band does not buy a pass, it buys a confident FALSE REJECTION of the very
# arm the gate is registered on. Same disease as the old §10 note named — "a CONFIDENT VERDICT IN
# EITHER DIRECTION from data that cannot support one" — and this is the other direction.
# ⚠ THE ANCHOR MOVED (2026-08-13, F132). `derive_tol` was refactored into `_planted_reference`,
# which caches a RECORD rather than a bare float, so `_TOL_CACHE[key] = tol` no longer exists and
# this sed became a no-op. The farm's cmp-guard would have caught it loudly — it is doing exactly
# the job F048 built it for — but the honest fix is to anchor on the tol COMPUTATION, which is
# what the mutation is actually about and which does not move when caching is restructured.
MUT=$(mutate factory_slope_test.py 's/^    tol = min(nb.NULL_BAND_CAP.*/    tol = 0.030  # MUTANT: the deleted MAX_HALFWIDTH/' \
      python3 bin/factory_slope_test.py run --arm price $SL_ARGS)
chk "the mutant reached its checks" "yes" "$(ran "$MUT" 'SLOPE TEST')"
chk "★ a 3× loose band CONVICTS the incumbent on data the real band calls INDETERMINATE" "yes" \
    "$(echo "$MUT" | grep -q '⇒ REJECTED' && echo yes || echo no)"
REAL=$(python3 bin/factory_slope_test.py run --arm price $SL_ARGS 2>&1)
chk "…and the derived band abstains on that same data" "yes" \
    "$(echo "$REAL" | grep -q '⇒ INDETERMINATE' && echo yes || echo no)"

echo "── 10b. ★ THE POSITIVE CONTROL — can the arm see an edge that IS there? (F132) ───"
# The criterion above judges on an EDGE-FREE tape only, and an arm blind to everything passes
# that perfectly. These pin the two properties the repair rests on, at 20 days where both are
# measured (`--seeds 1`: the seed-to-seed range is a separate, slower bar).
PC_ARGS="--days 20 --k 20 --seeds 1"
OUT=$(python3 bin/factory_slope_test.py poscontrol --arm surrogate $PC_ARGS 2>&1)
chk "★ the rule-selected surrogate is BLIND — the arm this repair was built around" "yes" \
    "$(echo "$OUT" | grep -q '⇒ BLIND' && echo yes || echo no)"
# ★ AND IT IS THE ABSORPTION BAR THAT CONVICTS IT, NOT THE SHIFT. Measured: the surrogate's shift
# is −0.0289 with CI [−0.0803, +0.0225], which STRADDLES the band ⇒ INDETERMINATE on shift alone.
# The author's first draft of the header claimed "it fails on shift alone"; it does not, and
# scoping the absorption bar away entirely would have lost the only conviction at this size.
MUT=$(mutate factory_slope_test.py 's/    binding_absorption = arm in sc.ARMS_RULE_SELECTED/    binding_absorption = False  # MUTANT/' \
      python3 bin/factory_slope_test.py poscontrol --arm surrogate $PC_ARGS)
chk "the mutant reached its checks" "yes" "$(ran "$MUT" 'POSITIVE CONTROL')"
chk "★ dropping the scoped absorption bar LOSES the surrogate conviction" "yes" \
    "$(echo "$MUT" | grep -q '⇒ BLIND' && echo no || echo yes)"
# ★ THE POSITIVE CONTROL'S OWN NULL CONTROL (D030 seat's top finding, 2026-08-13). The shift
# statistic must read ZERO on the epp-neutral rule, where the true shift IS zero. The `time` arm
# does not: measured −0.0159 [−0.0198, −0.0120] over 10 seeds, 128% of the whole detection bar.
# Its apparent +0.0525 "sensitivity" is therefore not certifiable, and the arm reads INDETERMINATE
# rather than SENSITIVE. ⚠ This test REPLACES one asserting the opposite, which pinned a claim the
# author had written into the header before the null control existed to check it.
# ⚠ AT THIS DAY COUNT THE STATE IS `UNRESOLVED`, NOT `DIRTY`, and the distinction is the point:
# `rule_dumb` fires on ~229 candidates at 20 days against `rule_planted_signal`'s ~3435, so its
# interval is ±0.02-0.03 against a 0.0124 band. Measured here: time −0.0196 [−0.0397, +0.0005],
# uniform −0.0192, price −0.0002 — the same signs and rough magnitudes the seat pooled over 10
# seeds (−0.0159 / −0.0087 / +0.0005), and NONE of them resolvable at 20 days. Both non-clean
# states withhold SENSITIVE; only DIRTY is a finding about the arm.
OUT=$(python3 bin/factory_slope_test.py poscontrol --arm time $PC_ARGS 2>&1)
chk "★ SENSITIVE is withheld while the arm's own NULL CONTROL is not clean" "yes" \
    "$(echo "$OUT" | grep -q '⇒ INDETERMINATE' && echo yes || echo no)"
chk "…and the run names the null control it failed" "yes" "$(ran "$OUT" 'null control')"
# Both non-clean branches must go, or the surviving one still withholds the verdict and the
# mutation reads as a partial no-op.
MUT=$(mutate factory_slope_test.py 's/^    elif neutral_state == "DIRTY":/    elif False:  # MUTANT: no null control/;s/^    elif neutral_state != "CLEAN":/    elif False:  # MUTANT: no null control/' \
      python3 bin/factory_slope_test.py poscontrol --arm time $PC_ARGS)
chk "the mutant reached its checks" "yes" "$(ran "$MUT" 'POSITIVE CONTROL')"
chk "★ deleting the null control certifies a change-in-bias term as SENSITIVITY" "yes" \
    "$(echo "$MUT" | grep -q '⇒ SENSITIVE' && echo yes || echo no)"
# ★ THE THREE-WAY, again — the incumbent at 20 days is UNDERPOWERED, which is not a conviction.
OUT=$(python3 bin/factory_slope_test.py poscontrol --arm price $PC_ARGS 2>&1)
chk "★ the incumbent is INDETERMINATE on thin data, never BLIND" "yes" \
    "$(echo "$OUT" | grep -q '⇒ INDETERMINATE' && echo yes || echo no)"
# ⚠ MUTANT-VS-MUTANT, AND THAT IS DELIBERATE. At 20 days the NULL CONTROL is UNRESOLVED for every
# arm (rule_dumb fires on ~229 candidates), so it short-circuits ahead of the shift three-way and
# a mutation of `refuted` alone never reaches its target — the first version of this check was
# exactly that dead pass. Both runs therefore disable the null-control gate identically, which
# holds it out as a constant, and the ONLY difference between them is the three-way itself.
NULLOFF='s/^    elif neutral_state == "DIRTY":/    elif False:  # held out/;s/^    elif neutral_state != "CLEAN":/    elif False:  # held out/'
MUT=$(mutate factory_slope_test.py "$NULLOFF" \
      python3 bin/factory_slope_test.py poscontrol --arm price $PC_ARGS)
chk "the mutant reached its checks" "yes" "$(ran "$MUT" 'POSITIVE CONTROL')"
chk "★ with the null control held out, a straddling shift is still INDETERMINATE" "yes" \
    "$(echo "$MUT" | grep -q '⇒ INDETERMINATE' && echo yes || echo no)"
MUT=$(mutate factory_slope_test.py "$NULLOFF"';s/^    elif refuted:/    elif True:  # MUTANT: two-way — anything not SENSITIVE is BLIND/' \
      python3 bin/factory_slope_test.py poscontrol --arm price $PC_ARGS)
chk "the mutant reached its checks" "yes" "$(ran "$MUT" 'POSITIVE CONTROL')"
chk "★ collapsing the three-way convicts the incumbent for being underpowered" "yes" \
    "$(echo "$MUT" | grep -q '⇒ BLIND' && echo yes || echo no)"

echo "── 11. ★ THE TIME PROBES — the two properties that make the axis separable ───────"
# Filed as a fault against myself: rule_early_session / rule_late_session shipped into the
# known-null device in the same commit as the verdict they produced, with ZERO coverage
# (REFUTATION_2026-08-12_uniform_arm_R1.md FOLD 11; charter §4 rule 4 requires the not-blind
# proof re-proven after every harness change). These are the two properties the whole time-axis
# argument rests on — if either fails, a "time slope" reading is measuring something else.
# ★ 500 DAYS, NOT 20 (fix 2026-08-12, F048). The neutrality assertion below is a POINT ESTIMATE
#   against hardcoded tolerances with no interval and no power guard — the span-form disease the
#   rest of this suite exists to ban, applied to the suite's own assertion. At 20 days it is
#   noise-dominated and can go green or red on seed luck; measured:
#       days= 20  n=  240/  220  early=0.5452 late=0.4210 gap=0.1242  → NEUTRAL no
#       days=250  n= 3000/ 2750  early=0.5114 late=0.4991 gap=0.0123  → NEUTRAL yes
#       days=500  n= 6000/ 5500  early=0.5095 late=0.5038 gap=0.0057  → NEUTRAL yes
#   ⇒ the red this suite carried was a POWER artifact, not a broken probe.
#   ★ ONLY THE DAY COUNT MOVED. The ±0.05 / ±0.03 tolerances are UNCHANGED, deliberately: they
#   are ratified thresholds, and re-deriving them now — after seeing the measurement they judge —
#   would be calibrating the ruler on the tape it measures, which this project has a standing
#   prohibition against. 500 over 250 because more power makes the assertion HARDER to pass on
#   noise, so a genuine gap still surfaces. Whole check costs ~4s.
PROBE_PY='import sys; sys.path.insert(0,"bin")
import factory_synthetic as fs, factory_backtest as fb, factory_scorer as sc
free = fs.make_corpus(500, 20260812, 0.0)
G = dict(sl_pt=20.0, tp_r=None, max_hold_min=30, band="none", sym=fb.SYNTHETIC)
e,_ = fb.backtest(free, fs.rule_early_session, **G)
l,_ = fb.backtest(free, fs.rule_late_session, **G)
ei = {(r["day"], r["entry_ts"]) for r in e}; li = {(r["day"], r["entry_ts"]) for r in l}
ee = sc.entry_price_percentile(e, free)["mean"]; le = sc.entry_price_percentile(l, free)["mean"]
print("PROBES overlap=%d epp_early=%.3f epp_late=%.3f gap=%.4f" % (len(ei & li), ee, le, abs(ee-le)))
print("DISJOINT", "yes" if not (ei & li) else "no")
print("NEUTRAL", "yes" if abs(ee-0.5) <= 0.05 and abs(le-0.5) <= 0.05 and abs(ee-le) <= 0.03 else "no")'
OUT=$(python3 -c "$PROBE_PY" 2>&1)
chk "the probe check itself ran" "yes" "$(ran "$OUT" 'PROBES overlap')"
chk "★ the two probes partition the session — candidate sets are DISJOINT" "yes" \
    "$(echo "$OUT" | grep '^DISJOINT' | awk '{print $2}')"
chk "★ …and both are epp-NEUTRAL, so a gap is the TIME axis and not the price slope" "yes" \
    "$(echo "$OUT" | grep '^NEUTRAL' | awk '{print $2}')"
# P1 — collapse the partition: make `late` return `early`'s range. The probes stop being a
# contrast at all, and any "time-neutral" reading becomes a tautology.
MUT=$(mutate factory_synthetic.py 's/^    _, hi, third = _third(bars)/    lo, hi, third = _third(bars); hi = lo + third/' \
      python3 -c "$PROBE_PY")
chk "the mutant reached its checks" "yes" "$(ran "$MUT" 'PROBES overlap')"
chk "★ a collapsed partition is CAUGHT (probes would no longer contrast anything)" "no" \
    "$(echo "$MUT" | grep '^DISJOINT' | awk '{print $2}')"
# P2 — give `early` a price-position bias (buy local minima). The time axis would then be
# confounded with the epp axis, which is the exact separation these probes exist to provide.
MUT=$(mutate factory_synthetic.py 's|    return \[(i, "long") for i in range(lo, lo + third, 10)\]|    return [(i, "long") for i in range(lo, lo + third, 10) if bars[i]["close"] <= min(b["close"] for b in bars[max(0, i - 30):i + 1])]|' \
      python3 -c "$PROBE_PY")
chk "the mutant reached its checks" "yes" "$(ran "$MUT" 'PROBES overlap')"
chk "★ an epp-BIASED probe is CAUGHT (the time axis must not smuggle the price slope)" "no" \
    "$(echo "$MUT" | grep '^NEUTRAL' | awk '{print $2}')"

echo
echo "  ${PASS} passed, ${FAIL} failed"
[ "$FAIL" -eq 0 ] || exit 1
