# prereg-harness

**Validate the validator against data with no edge in it, before believing any positive.**

This is a falsification harness for quantitative research: a set of instruments that decide
whether a measured result is real, built on the premise that the measuring apparatus is the
thing most likely to be wrong. It ships a device that manufactures tape whose answer is known
before any scorer sees it, a scorer that is pointed at that tape first, a bar walker with no
look-ahead available to it, an append-only hash-chained registry that freezes a specification
before an outcome exists, and a stopping rule that is a JSON file the gauge reads rather than a
resolution anybody has to remember.

The ordering is the whole idea. A referee computed inside the simulator it is certifying will
pass. A predecessor system produced a Sharpe of 13.76 at a probability-of-overfit of 0.0%, and
every standard referee cleared it, because every referee was computed inside the simulator whose
output it was grading — the number was a property of the apparatus, not of the market. The
instruments here invert that order: the scorer is calibrated against a known null and a known
plant before it is allowed an opinion about a market, and every one of them is written so its
failure mode points at "cannot conclude" rather than at "confirmed".

Nothing in this repository connects to a broker, places an order, or reads an account.

---

## What it decides, and what it refuses to conclude

| Instrument | Decides | Refuses |
|---|---|---|
| `factory_synthetic.py` | whether a tape is edge-free, and whether a planted edge is present at the size declared | to call a Gaussian-walk result "validated" — it prints its own model bound beside every verdict |
| `factory_scorer.py` | whether a rule's entries beat matched placebo entries, at a stated interval | to score a percentile with a naive interval, and to let a time-matched arm stand alone |
| `factory_backtest.py` | what one trade was actually worth, floor and ceiling, net of frozen costs | to price an instrument the cost model was never fitted on — it raises rather than guesses |
| `factory_notblind.py` | whether the scorer detects a plant and returns null on an absence | to self-certify: it writes `survived` or `killed` for the measurement and cannot write `licensed` under any flag |
| `factory_registry.py` | what was registered, when, and against which frozen spec | a kill or null verdict with no `--mde` — "no edge found" must be "no edge above X found" |
| `factory_findings.py` | what is currently believed, and what replaced what | a `measured` finding with no reproduction command, and a supersession that does not name and flip its target |
| `factory_slope_test.py` | whether a scoring arm discriminates across several rules, not one | to convict an arm on thin data — it returns INDETERMINATE and names the band it failed against |
| `factory_ci.py` | the interval form, and whether that form achieves its nominal coverage | to report coverage it has not simulated |
| `edge_factory_gauge.py` | whether the programme is inside its pre-committed budget | to read a threshold from code — every number comes from `research/factory/budget.json` |

---

## The instruments

### 1. A known-null tape, and a known-planted one

`factory_synthetic.py` manufactures two corpora from the same generator and the same seed,
differing only in whether a drift is planted. The edge-free tape has i.i.d. zero-mean minute
returns — no drift, no autocorrelation, no exploitable structure of any kind, rather than none of
the kinds someone thought to test for. The planted tape is
that same tape plus a drift keyed to a signal computable from bars at or before the signal minute,
so the plant is real and the look-ahead is not. Both are deterministic in seed, which makes a
failing check reproducible from the seed alone.

Twelve checks in its `verify` verb measure both values rather than asserting them, and the last
line of output is the bound rather than a claim:

```
── 1. the edge-free tape is edge-free (the null must be a real null) ──
  ✓ per-minute drift is inside the null band: mean -0.0006pt/min, CI [-0.0400, +0.0374] ⊂ ±0.1pt/min (achieved bound, day-clustered)
  ✓ lag-1 autocorrelation ≈ 0: mean +0.0064 over 60 days (|x| < 0.05)
── 2. the planted tape actually contains the edge it claims ──
  ✓ planted episodes deliver the DECLARED size (declared value inside the CI): n=1364 mean +6.08pt over 15m, CI [+5.47, +6.69] ⊇ planted +6.0pt
  ✓ the rule RECOVERS a positive effect (weaker claim — dilution is expected): n=12987 mean +4.91pt, CI [+4.09, +5.46] vs planted +6.0pt (diluted, as expected)
  ✓ ★ the SAME signal on the edge-free tape returns null: mean +0.4675pt, CI [-0.2040, +0.9875] ⊂ ±1.5pt (achieved bound, day-clustered)
── 3. the confound rule really is confounded (else check 4 proves nothing) ──
  ✓ entry-price position is extreme, on a tape with NO edge: n=4268 mean favourable-position 0.968 (chance 0.5)
── 4. structural integrity every vendor bar must also satisfy ──
  ✓ OHLC coherence: 46800/46800 bars coherent
  ✓ no FLAT bars: 0 flat of 46800 (vendor padding shape)
  ✓ RTH grid is exactly 390 one-minute bars: 390 bars, contiguous
  ✓ first bar is 09:30 ET (DST resolved per date, not a fixed offset): 09:30:00
── 5. determinism (a failing check must be reproducible from its seed) ──
  ✓ same seed ⇒ byte-identical corpus: re-generated
  ✓ different seed ⇒ different corpus: seed binds

  PASS — 60 days/kind, seed 20260811
  ⚠ BOUND, stated with the verdict per the header: this proves the generator is a known null
    IN ITS OWN MODEL (Gaussian walk). It does not prove any scorer is calibrated on real
    microstructure — that is the vendor corpus and the shadow phase, not this file.
```

Reproduce: `python3 bin/factory_synthetic.py verify`

### 2. A placebo scorer that is matched on price, not only on time

`factory_scorer.py` ranks each candidate entry against placebo entries drawn from the same day,
side and stop width, and reports the percentile rather than the mean — with a stop and no target,
every arm is heavy-tailed and the median outcome is −1R in all of them, so a mean over that is
noise with a decimal point. The interval is a day-clustered bootstrap, because decisions inside a
day share the open, the trend and the news.

The registered arm matches on entry price, and the reason is arithmetic rather than taste. Under
a stop-and-target ruler the outcome is monotone in entry price: a long entered below its
neighbours has a nearer stop and a longer run, so it dominates higher-entry longs with or without
predictive structure. A time-matched percentile scores that as skill. The harness carries a rule
that reads only entry-price position, and the scorer is required to return null on it — that is
check 4 of the gate below.

The confound is bidirectional, which is the part usually left out: an unmatched arm can bury a
genuine edge as easily as it can invent one, so a null on the time-matched arm is not evidence of
absence. Both arms are always reported, and forms that disagree are shown together.

### 3. A walker with no look-ahead available to it

`factory_backtest.py` walks one trade bar by bar through `harness_ruler.walk_bounds`. Three
conventions in that function do most of the work, and all three cost the result rather than
flatter it:

- The walk starts at the first bar **strictly after** the entry minute. The entry bar's range had
  already partly elapsed when the fill happened; crediting its extremes hands the ruler excursion
  that was never available.
- Within a bar the **stop resolves first**. A bar containing both barriers is a loss. Inside a
  one-minute bar we cannot know which extreme came first, so the flattering order is refused.
- The favourable excursion of the **terminating** bar is never credited, for the same reason.

Costs are frozen in `research/factory/cost_model.json` and applied per trade in R, scaled by the
stop. The model raises rather than guesses for any instrument it was not fitted on. The gate
asserts the cost application as an exact identity, not a tolerance — a tolerance is where a
half-applied cost hides.

### 4. The gate that points one at the other

`factory_notblind.py` is the demonstration. It runs seven checks that point the scorer at tape
whose answer is already known: the plant must be detected, the edge-free tape must return null,
an informationless rule must return null even on the tape that has the edge, a known-dumb rule
must lose exactly the cost, and the price-position-only rule must score above chance unmatched
and null once matched.

**The null form is equivalence, not "does the CI span 0.5".** That difference is the whole
distinction between a validator and a rubber stamp. The span form is satisfied by a wide
interval, so it gets *easier* to pass with less data — a rubber stamp rewards you for running a
small sample. The equivalence form requires the entire interval to lie inside a band, and the
band is a fixed fraction of the lift the same run measured on the planted tape. So it gets
*harder* with less data, and nothing in it can be loosened by re-rolling a seed.

The module's own header derives the powered configuration: `GATE_DAYS = 250`, set by the widest
check and 1.45× its binding requirement. The command below runs 12 days, which is deliberately
under that — a fast demonstration at a sample size the instrument itself calls too small. Here is
what it does with one:

```
═══ NOT-BLIND GATE — 12 days/tape, k=20, seed 7, sl 20pt / hold 30m ═══

── 1. a synthetic tape with a planted edge is DETECTED ──
  ✓ [1] planted edge detected on the registered (price) arm
      n=2270 days=12 mean 0.5375 CI [0.5195, 0.5579] MDE 0.0275 · mean 0.5375, CI [0.5195, 0.5579] > 0.5 (MDE 0.0275)
      → measured lift +0.0375 ⇒ null band ±0.0094 (25% of it, capped at 0.05)
      · time-matched arm 0.4729 at entry-price pct 0.140 (confound_risk=True) — this rule buys local maxima, so the unmatched arm BURIES its real edge

── 2. an edge-free tape returns NULL (equivalence, not 'the CI spans 0.5') ──
  ✗ [2] the SAME rule on the edge-free tape is null
      n=2204 days=12 mean 0.4978 CI [0.4814, 0.5161] MDE 0.0248 · INSUFFICIENT POWER — CI ±0.0174 is wider than the ±0.0094 band; a null here would be an artifact of low n (MDE 0.0248)
  ✗ [2b] an INFORMATIONLESS rule is null even on the tape that HAS the edge
      n=573 days=12 mean 0.5059 CI [0.4904, 0.5224] MDE 0.0228 · INSUFFICIENT POWER — CI ±0.0160 is wider than the ±0.0094 band; a null here would be an artifact of low n (MDE 0.0228) · coverage 13.3% of minutes

── 3. a known-dumb rule loses ≈ costs ──
  ✗ [3] the dumb rule finds no edge (its selection is null)
      n=530 days=12 mean 0.4916 CI [0.4787, 0.5057] MDE 0.0193 · INSUFFICIENT POWER — CI ±0.0135 is wider than the ±0.0094 band; a null here would be an artifact of low n (MDE 0.0193) · coverage 11.8% of minutes
  ✓ [3b] …and its whole loss vs gross IS the cost, exactly
      gross -0.0484R − net -0.1084R = +0.060000R vs frozen cost +0.060000R (1.20pt at a 20pt stop)

── 4. the price-position-only rule: above chance unmatched, NULL matched ──
  ✓ [4a] scores ABOVE chance against a TIME-matched placebo (the trap is live)
      n=836 days=12 mean 0.6467 CI [0.6106, 0.6874] MDE 0.0548 · mean 0.6467, CI [0.6106, 0.6874] > 0.5 (MDE 0.0548) · entry-price pct 0.944
  ✗ [4b] and returns NULL once the placebo is PRICE-matched
      n=753 days=12 mean 0.5385 CI [0.5037, 0.5710] MDE 0.0481 · INSUFFICIENT POWER — CI ±0.0336 is wider than the ±0.0094 band; a null here would be an artifact of low n (MDE 0.0481)
      ⚠ BOTH VALUES OR IT CERTIFIES NOTHING: a scorer null on both is not passing,
        it is dead, and would report null for a real edge too.

  FAIL — 3/7 checks · worst achieved MDE 0.0481 percentile points
  ⚠ BOUND: this proves the harness is not blind ON A GAUSSIAN-WALK TAPE. It does not
    prove calibration on real microstructure — that is the vendor corpus (Phase 2)
    and the shadow phase (Phase 3).
registry: +row #1 harness-gate 'notblind-20260821T145056' chain=299d167d8bf6
registry: +row #2 verdict 'notblind-20260821T145056' chain=d5bb4476edd9

  ⛔ NOT LICENSED BY THIS RUN. This gate reports `killed`, which is a MEASUREMENT.
     Charter §4.4/§4.7 requires a fresh-context external seat to license the
     harness; self-certification is exactly what this file exists to prevent.
     That seat has not run.
```

Reproduce: `python3 bin/factory_notblind.py gate --days 12 --seed 7`

**Read that output as the instrument working.** Three of the seven checks are answerable at
twelve days, and all three answer: the plant is detected on the registered arm, the cost is
priced to six decimals, and the price-position trap fires exactly as designed on the unmatched
arm. On the other four the gate declines to certify an absence at a sample size that cannot
support one, and it prints the achieved MDE beside each refusal — 0.0193 to 0.0481 percentile
points — so a reader can see precisely what this run could and could not have detected.

That refusal is the feature. A tool that returned a clean null here would be reporting "nothing
found" when what it actually had was not enough data to look, and the reader would have no way to
tell those apart. Raise `--days` toward the module's own derived 250 and the same four checks
become answerable.

Then it writes both rows to the registry and refuses to license itself. The licence, in this
design, comes from a fresh-context external reader, never from the module's own opinion of its
own output.

### 5. A registry that freezes the spec, and a stopping rule that is a file

`factory_registry.py` is append-only and hash-chained: every row carries the previous row's hash,
so a silent deletion or rewrite is detectable in-band. Git history is rewritable by its author;
the chain is not. Registration takes a path to a specification file and freezes its sha256, which
is what makes "this was pre-registered" a checkable statement rather than a memory. A kill or
null verdict without `--mde` is refused at the write.

`research/factory/budget.json` holds the stopping rule — the minimum useful edge, the minimum
signal rate, the cap in days and rounds — and `edge_factory_gauge.py` reads those keys and
nothing else. No threshold is hardcoded anywhere in the code, so the gauge cannot drift from the
rule, and changing the rule is a deliberate, dated, reviewable edit to one file.

```
$ python3 bin/edge_factory_gauge.py
═══ EDGE FACTORY — HEADLINE (pace gauge; success = MUE-clearing survivor OR on-schedule dormancy) ═══
  resolved this week: 1 · resolved total: 1 / registered: 3 · registry rows: 5 (THE denominator)
  survivors by stage: none
  Phase-2 clock NOT RUNNING (gate: ON-DEMAND — the operator starts the clock; phase2_start stays null until then) · Phases 0+1 day 10/14
  MUE (ratified): +0.15R/trade net · ≥2 signals/wk (portfolio-wide, per budget.json) · dormancy record: none
```

The row count is the multiplicity denominator. It is printed on the headline because a search
that does not count its own attempts has no p-value.

---

## The tests are mutation proofs

A green test run certifies nothing on its own — a check never observed to fail is a check whose
absence would be invisible. So each property is broken on purpose and the matching check is
asserted to go red **by name**, never by exit code alone. Mutants run in a symlink farm of `bin/`
with exactly one module swapped, and a guard refuses any `sed` that left the file byte-identical:
a dead mutation is a loud failure rather than a silent pass.

```
$ bash tests/test_factory_synthetic.sh
── 1. the unmutated device passes, and fast enough to be run every time ─────────
  ✓ verify exits 0 on the real generator
  ✓ it reports PASS
  ✓ it states its own bound rather than claiming validation
── 2. ★ THE STACKING PIN — a wrong effect SIZE must fail, not just a wrong sign ──
  ✓ stacked drift is REJECTED (the +89pt-vs-+6pt tape)
  ✓   …and the mutant actually RAN (not a startup failure)
  ✓   …and it fails on the size check specifically
  ✓   …the OLD 'CI > 0' form would have PASSED that tape (why the pin exists)
  ✓   …the NEW form rejects it
── 3. the edge-free tape must be able to stop being edge-free ──────────────────
  ✓ a drifting 'null' tape is REJECTED
  ✓   …and the mutant actually RAN (not a startup failure)
  ✓   …on the drift check
── 4. structural integrity checks must be able to fail ─────────────────────────
  ✓ flat bars are REJECTED once the floor is removed
  ✓   …and the mutant actually RAN (not a startup failure)
  ✓   …on the FLAT-bar check
── 5. determinism must be able to fail ─────────────────────────────────────────
  ✓ an unseeded generator is REJECTED
  ✓   …and the mutant actually RAN (not a startup failure)
  ✓   …on the determinism check
── 6. the CONFOUND rule is the point — it must really be confounded ────────────
  ✓ a de-fanged confound rule is REJECTED
  ✓   …and the mutant actually RAN (not a startup failure)
  ✓   …on the entry-price-position check
── 7. the no-look-ahead boundary is real ───────────────────────────────────────
  ✓ the signal ignores every bar after its own minute
  ✓   …and does depend on the bars before it (so the above is not vacuous)
── 8. synthetic rows can never be mistaken for tape ────────────────────────────
  ✓ every row is tagged src=SYNTHETIC
  ✓ every row carries exactly the canonical bar schema (one walker consumes both)

══ 24 passed, 0 failed ══
```

```
$ bash tests/test_factory_registry.sh
test_factory_registry: 10 passed, 0 failed
```

```
$ bash tests/test_factory_harness.sh
── 1. the unmutated harness passes ─────────────────────────────────────────────
  ✓ backtest selftest exits 0
  ✓ …and reports PASS
  ✓ scorer selftest exits 0
  ✓ …and reports PASS
── 2. ★ THE NO-LOOKAHEAD BOUNDARY — the entry bar must never be walked ─────────
  ✓ the mutant reached its checks
  ✓ walking the entry bar is CAUGHT
  ✓ the blind mutant reached its checks
  ✓ a walker that sees NOTHING after entry is caught too
── 3. costs — applied, in the right direction, and exactly ─────────────────────
  ✓ the mutant reached its checks
  ✓ costs silently NOT applied is caught
  ✓ a cost that does not scale with the stop is caught
── 4. the Phase-0 findings the walker is required to enforce ───────────────────
  ✓ FLAT (vendor-padded) bars left in the tape is caught
  ✓ a bar-counted hold window is caught
  ✓ a truncated hold scored as a real trade is caught
── 5. ★ THE PRICE-MATCHED ARM — the confound that produced the 0.725 survivor ──
  ✓ the mutant reached its checks
  ✓ a price arm that does not match price is CAUGHT
  ✓ a confound flag that fires on price-NEUTRAL rules is caught
── 6. ★★ THE INTERVAL AND THE NULL FORM — the rubber-stamp mutations ───────────
  ✓ the mutant reached its checks
  ✓ dropping day-clustering manufactures a false positive, and is caught
  ✓ the real gate REFUSES an under-powered run
  ✓ …and fails it rather than certifying
  ✓ the mutant reached its checks
  ✓ ★ the span form passes checks the equivalence form refuses
── 7. the gate cannot license itself ───────────────────────────────────────────
  ✓ the gate says so in its own output
  ✓ no code path writes outcome=licensed
  ✓ …and the only outcomes it can write are the two measurement verdicts
── 8. ★ a null on an UNMATCHED arm is REFUSED at the chokepoint ────────────────
  ✓ the mutant reached its checks
  ✓ deleting the unmatched-arm refusal is CAUGHT
  ✓ a refusal that also blocks the REGISTERED arm is caught
── 9. placebos inherit the CANDIDATE's stop, not a shared one ──────────────────
  ✓ both stop widths reach the walker
── 10. ★ THE SLOPE TEST — the acceptance criterion must DISCRIMINATE ─────────────
  ✓ the registered arm is NOT convicted on thin data
  ✓ …and says INSUFFICIENT POWER, naming the band it failed against
  ✓ the null band is DERIVED from a planted-tape lift, not declared
  ✓ …and NAMES its ruler, with the RATIFIED default 
  ✓ …and the ruler's baseline is MEASURED, not the assumed 0.5
  ✓ ★ the grossly biased time arm is REJECTED (the criterion still discriminates)
  ✓ the mutant reached its checks
  ✓ ★ checking POWER before non-equivalence loses the conviction entirely
  ✓ the mutant reached its checks
  ✓ ★ judging on the epp-NEUTRAL rule alone stops rejecting the biased arm
  ✓ the mutant reached its checks
  ✓ ★ the SPAN form buys a confident null-PASS from data the real form calls INDETERMINATE
  ✓ …and the equivalence form abstains on that same data
  ✓ the mutant reached its checks
  ✓ ★ the positive control WITHHOLDS the span form's unearned pass
  ✓ …and says so by naming the control it ran
  ✓ the mutant reached its checks
  ✓ ★ a 3× loose band CONVICTS the incumbent on data the real band calls INDETERMINATE
  ✓ …and the derived band abstains on that same data
── 10b. ★ THE POSITIVE CONTROL — can the arm see an edge that IS there? (F132) ───
  ✓ ★ the rule-selected surrogate is BLIND — the arm this repair was built around
  ✓ the mutant reached its checks
  ✓ ★ dropping the scoped absorption bar LOSES the surrogate conviction
  ✓ ★ SENSITIVE is withheld while the arm's own NULL CONTROL is not clean
  ✓ …and the run names the null control it failed
  ✓ the mutant reached its checks
  ✓ ★ deleting the null control certifies a change-in-bias term as SENSITIVITY
  ✓ ★ the incumbent is INDETERMINATE on thin data, never BLIND
  ✓ the mutant reached its checks
  ✓ ★ with the null control held out, a straddling shift is still INDETERMINATE
  ✓ the mutant reached its checks
  ✓ ★ collapsing the three-way convicts the incumbent for being underpowered
── 11. ★ THE TIME PROBES — the two properties that make the axis separable ───────
  ✓ the probe check itself ran
  ✓ ★ the two probes partition the session — candidate sets are DISJOINT
  ✓ ★ …and both are epp-NEUTRAL, so a gap is the TIME axis and not the price slope
  ✓ the mutant reached its checks
  ✓ ★ a collapsed partition is CAUGHT (probes would no longer contrast anything)
  ✓ the mutant reached its checks
  ✓ ★ an epp-BIASED probe is CAUGHT (the time axis must not smuggle the price slope)

  68 passed, 0 failed
```

The harness suite is the slow one (about 57 minutes on an M-series laptop) because each mutant
re-runs a full scorer selftest at the module's own default sample size — a mutation test at a
sample size nobody uses certifies a configuration nobody runs.

---

## External refutation

`research/factory/seats/` carries a verbatim transcript from a fresh-context adversary given a
claim, the tree, and none of the author's reasoning, whose default verdict is "this does not
hold" and who must be argued out of it by evidence in the repository.

The one included found that a pre-registered specification said the stop was sized from the
**prior** session's range and the deciding line of code sized it from the **current** session's
range — a number nobody has at the open. The module's own selftest passed and had never looked at
the stop. Seven of nine grid cells flip sign once the specified stop is used. The claim was
withdrawn and the transcript kept, verbatim, because a summary of a seat passes through the
author's memory and the author is the party the seat exists to check.

That is what the registry's `licensed` verdict requires and what the not-blind gate refuses to
substitute for itself.

---

## Layout

```
bin/
  harness_ruler.py         the single ruler: one bar walker, one interval form
  factory_synthetic.py     the known-null device — edge-free and planted tape, plus confound rules
  factory_scorer.py        permutation/placebo scorer; paired per candidate, percentile, day-clustered
  factory_backtest.py      no-lookahead walker + frozen cost application
  factory_surrogate_arm.py an alternative null: re-run the rule on surrogate tapes
  factory_notblind.py      the gate that points the scorer at tape with a known answer
  factory_slope_test.py    the acceptance criterion, and its own not-blind checks
  factory_ci.py            interval forms and a coverage harness
  factory_registry.py      append-only hash-chained registry; freezes the spec sha256
  factory_findings.py      append-only findings ledger; three refusals
  factory_data.py          vendor loader: per-instrument divisor and plausibility band, declared then verified
  edge_factory_gauge.py    the stopping rule, machine-read from budget.json
  design_shape_check.py    a spec lint: every derived constraint must name what it excludes
tests/                     mutation proofs for the registry, the synthetic device, and the harness
research/factory/
  budget.json              the stopping rule, in the form the gauge reads
  cost_model.json          the frozen cost model
  registry.jsonl           the hash chain — generated by running this repo
  findings.jsonl           the findings ledger — generated by running this repo
  FINDINGS.md              derived from the ledger; regenerated, never edited
  PREREG_*.md              frozen specifications, registered by sha256
  seats/                   external refutation transcripts
```

`harness_ruler.py` exists because of this extraction. In the originating tree the walker and the
interval lived in two modules belonging to a live execution loop, and importing them pulled in a
closure of **9 files and 4,340 lines** — a bar-source union, a replay engine, exit classifiers,
live gauges — of which this research code called exactly three functions: `walk_bounds`,
`cluster_bootstrap_ci`, and a four-line interval helper. Those 154 lines are lifted into
`harness_ruler.py` and every caller repointed. Measured over the same nine entry points, the
import closure went from **22 modules / 9,902 lines to 13 modules / 5,354 lines** — and all
thirteen are present in this repository, none of them touching a broker. Nothing was stubbed:
what left was a live execution loop that the research code never called.

One ruler, imported everywhere, is a load-bearing constraint rather than tidiness: when a walker
lives in the backtest and a near-copy lives in the scorer, a verdict can move because the ruler
changed rather than because the tape did, and no test in the suite can see the difference.

---

## Running it

Python 3.9+ (`zoneinfo` is the binding requirement). No dependencies outside the standard library.

```bash
python3 bin/factory_synthetic.py verify                    # the known-null device measures both its values
python3 bin/factory_notblind.py gate --days 12 --seed 7    # fast demo (under-powered, and says so)
python3 bin/factory_notblind.py gate                       # the powered configuration, GATE_DAYS = 250 (over an hour)
python3 bin/factory_backtest.py selftest                   # walker invariants
python3 bin/factory_scorer.py selftest                     # positive / negative / anti controls
python3 bin/factory_ci.py selftest                         # interval invariants + the overlap discrimination
python3 bin/factory_slope_test.py run --arm price --days 40 --k 20   # the acceptance criterion
python3 bin/factory_registry.py verify                     # walk and recompute the hash chain
python3 bin/factory_registry.py count                      # the multiplicity denominator
python3 bin/factory_findings.py index                      # regenerate FINDINGS.md from the ledger
python3 bin/edge_factory_gauge.py                          # the stopping rule, read from budget.json
bash tests/test_factory_synthetic.sh                       # mutation proofs
bash tests/test_factory_registry.sh
bash tests/test_factory_harness.sh                         # slow
```

Five checks in `factory_backtest.py selftest` are pinned against a licensed vendor corpus that
does not ship. They report `⊘ NOT RUN` with the reason, and the summary line carries the count —
an unrunnable check must not be reported as passing, and must not be reported as failing either.
`python3 bin/factory_data.py pull --symbols USATECHIDXUSD --from 2012-01-01 --to 2023-12-31`
populates that corpus against your own data entitlement.

---

## What is not in this repository

This is one component of a larger system that runs against a live broker account. The execution
loop, the broker adapter, the account state and the risk fuses are not published and will not be
— they are inseparable from credentials and a funded account. What is here is the part that
stands on its own.

Two consequences worth stating plainly:

- **The registry and the findings ledger here were generated by running this harness in this
  checkout.** The originating project's own ledgers stay private. So every row you can read is a
  real row, produced by the command it names, and the chain verifies from genesis — it is this
  repository's own history rather than an import of someone else's.
- **The reproducible part is the method.** The known-null device, the matched placebo arms, the
  equivalence null form, the frozen cost application, the hash-chained registry and every
  mutation proof run and re-run from a clean clone, on any machine, with no data of mine.
  Measurements whose inputs are a private trade journal or a licensed 1-minute corpus stay where
  their inputs are; the instruments that produced them are here in full.

The instruments outlast the programme they were built for. That programme was paused on a
resource decision, its calendar is still running, and these tools travel independently of it.

Read access to more can be arranged for a serious conversation.

---

## Licence

MIT. See `LICENSE`.
