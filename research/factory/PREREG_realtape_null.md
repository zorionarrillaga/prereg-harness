# PREREG — the EDGE-FREE REAL-TAPE CONTROL

**Registered 2026-08-12, BEFORE any real-tape null was computed.** Every parameter below is fixed
by this document's sha256 in `research/factory/registry.jsonl`. The prohibition that governs it is
the same one that governs `PRICE_BAND`:

> ⛔ **No parameter here may be changed because the null did not land on 0.5.** Tuning a destructive
> transform until the instrument reads clean is calibrating the instrument on the tape it exists to
> judge. If the null misses, that is the RESULT, and it is reported as the result.

Discharges drain contract `2026-08-12__phase1-validated-on-synthetic-tape-only` (finding F029).
Output artifact: `research/factory/realtape_null.json`.

---

## 1. WHY THIS EXISTS

Every Phase-1 verdict — the not-blind gate, the repaired acceptance criterion, F030's 400-day
conviction of the registered `price` arm — was measured on `bin/factory_synthetic.py`, a
Gaussian-walk tape with no trend, no session structure, no microstructure and no fat tails.
**No arm has ever been judged on the vendor corpus.** Under the project's own diagnosis
truth-harness that is a SINGLE FEED: the author and the D030 external seat agreeing with one
another is not corroboration, because both read the same instrument on the same tape.

The direction of the unknown is **adverse, not neutral** (F029): the R1 seat measured the confound
rule's entry-price percentile at 0.715 inside a ±60min pool against 0.644 whole-day, which implies
the epp residual is *larger* on a trending tape where a local extreme is often a DAY extreme.

## 2. WHAT AN "EDGE-FREE REAL TAPE" HAS TO BE

The synthetic tape's job is *"we know the answer is zero."* The real-tape equivalent needs a
destructive transform that kills any genuine forecasting edge while PRESERVING the microstructure
whose absence is the whole objection. The rules' dependency span sets the scale that must be
destroyed:

| quantity | value | source |
|---|---|---|
| `rule_price_extreme` lookback | 30 min | `factory_synthetic.rule_price_extreme` |
| `rule_planted_signal` lookback (`LOOKBACK`) | 20 min | `factory_synthetic` |
| hold | 30 min | backtest config |
| ⇒ **span to destroy** | **≈60 min** | max(lookback) + hold |

## 3. TRANSFORMS CONSIDERED, AND THE TWO REJECTED — with reasons, in advance

The drain contract named three candidates. Two are rejected here, before measurement, on
mechanism — not on the numbers they would have produced.

**(a) Day-shuffle — REJECTED.** It reorders whole sessions and destroys nothing *inside* a session.
Both probes are intraday rules with a ≤60-minute dependency span, so a day-shuffled tape is,
for their purposes, the untransformed tape. It would have produced a control that cannot fail.

**(b) Cross-instrument label permutation — REJECTED, and this one is subtle.** Computing the rule on
instrument A and entering on B's bars at the same minutes preserves B's tape perfectly and does kill
the signal→outcome link. But the criterion's entire axis is **entry-price percentile**: the probes
are calibrated to sit at epp≈0.33 and epp≈0.72, and the defect being hunted is a SLOPE across that
axis. Entering on B at minutes chosen from A puts the entry at epp≈0.5 by construction, collapsing
the two probes onto one point. It destroys the thing being probed.

**(c) Time-of-day-stratified block bootstrap — ADOPTED.** Below.

## 4. THE TRANSFORM — fixed parameters

Reassemble each session from contiguous blocks of real vendor bars, sampled across days from the
same slot in the session.

| parameter | value | why THIS value (fixed in advance) |
|---|---|---|
| `BLOCK_MIN` | **5** | Short enough that the 30-min lookback spans 6 blocks and the 30-min hold spans 6 more, so any genuine relation at the rules' horizon straddles seams and dies. Long enough that every bar is copied verbatim and 5-minute volatility clustering survives. |
| block sampling | **time-of-day stratified** — a block at session slot *k* is drawn only from slot *k* of other days | The session volatility profile (open ramp, lunch lull, close ramp) is real structure the synthetic tape lacks, and `harness_ruler`'s own header documents time-of-day as **directional**. Destroying it would hand back a different synthetic tape. |
| reassembly | **return space**, re-anchored per block | Concatenating price levels would emit artificial gaps at every seam. Each bar carries its (open, high, low, close) offsets from its block's first open and is re-anchored to the running price, so **bar shape and wick geometry are preserved exactly**. |
| session | **RTH 09:30–16:00 ET**, via `zoneinfo.ZoneInfo("America/New_York")` | Matches the synthetic tape's session. Never a fixed −4 offset (that class defect is already filed: `2026-08-11__hardcoded-et-offset-class-9-scripts`). |
| FLAT bars (`high == low`) | **dropped**, rate recorded | Vendor padding; a stop "touched" on a padded bar never happened (Phase-0 report, ratified for Phase 2). The synthetic tape never emits one (`FLOOR_RANGE_PT`), so keeping them would make the comparison unlike-for-unlike. |
| block eligibility | **complete blocks only** — a slot missing any of its 5 minutes after the FLAT drop contributes nothing | Not a completeness threshold anybody chose: it falls out of `BLOCK_MIN`, and it is what makes every assembled session exactly 390 minutes with no short block to special-case. Dropped blocks are counted and reported. |
| **volatility scale** | **one scalar per instrument = `SIGMA_PT (3.0) / its own realised 1m sd`**, measured on the RAW corpus before any transform | ⚠ **AMENDMENT, registered before any null was computed — see §4a.** |
| `seed` | **20260812** | Same seed as F030, declared before the run. |
| `days` | **400** | Equal to F030 so real and synthetic are compared at equal power, and available on both instruments. |
| primary instrument | **USA500IDXUSD (US500)** | ρ = Ψ/σ ranks it 5.2× above US100 on our own corpus (`factory_instrument_rank.py`); 673 clean days on disk. |
| replication instrument | **USATECHIDXUSD (US100)** | The instrument every prior Phase-1 number was implicitly calibrated against. A second feed for the second feed. |

## 4a. ★ AMENDMENT — the volatility scale (registered 2026-08-12, still BEFORE any null)

Found while implementing, not while measuring: **the original prereg had no unit policy, and the
criterion's geometry is fixed at `sl_pt = 20` / 30-minute hold.** Twenty points means one thing on
US100 near 20,000 and something else entirely on US500 near 5,000 — where a 20pt stop is almost
never touched, so every outcome collapses onto hold-to-close and the arms get judged at a geometry
no candidate rule will ever run at. Leaving it unstated would not have been neutrality; it would
have silently made the primary instrument the weaker test.

**Fixed rule:** each instrument's return stream is multiplied by ONE scalar,
`SIGMA_PT (3.0) / (that instrument's realised 1-minute sd)`, measured on the **raw** corpus before
any transform and before any null. Measured values, recorded here in advance:

| instrument | raw 1m sd | scalar |
|---|---|---|
| USA500IDXUSD | 2.1879 pt | ×1.3712 |
| USATECHIDXUSD | *(measured at run time, recorded in the output JSON)* | — |

A single affine factor changes **units only**: fat tails, volatility clustering, wick-to-body
ratios and the session profile are all scale-invariant and survive exactly. It is called out
because it is the one number in the design that could be mistaken for a knob, and the prohibition
in the banner applies to it in full — it may not be moved because a null missed.

**Why this is an amendment and not an edit:** the registry is append-only and hash-chained, so
this document's amended sha256 is registered as its own row pointing at row #17. The chain, not a
promise, is what proves the parameter was fixed before the measurement.

## 5. HOW `tol` IS DERIVED — unchanged in FORM, re-measured on this tape

`tol` stays `NULL_BAND_FRACTION (0.25) × measured planted-tape lift`, capped at `NULL_BAND_CAP`.
It is **re-derived on the transformed real tape**, by planting `DEFAULT_EFFECT_PT = 6.0` of drift
into the reassembled bars exactly as `make_tape` plants it. It is NOT inherited from the synthetic
run: a band derived on one tape and applied to another is the borrowed-constant failure this
project has already been bitten by.

## 6. ACCEPTANCE — stated before the numbers exist

For each (arm, probe) pair, with residual `r = |centre − 0.5|`:

- **TRANSFERS** iff `r_realtape ≤ r_synthetic` (F030's centres are the synthetic baseline).
- **UNDERSTATEMENT** iff `r_realtape > r_synthetic` — in which case **every synthetic verdict on the
  Phase-1 page, including F030's conviction, is a lower bound**, and the arms are worse than
  measured, not better.
- A probe whose CI halfwidth exceeds `tol` is **INSUFFICIENT POWER** and is neither, exactly as in
  `factory_slope_test.judge`.

**Synthetic baselines this is measured against (F030, 400 days, seed 20260812, tol ±0.0086):**

| arm | `rule_planted_signal` | `rule_price_extreme` | spread |
|---|---|---|---|
| uniform | 0.4740 (r 0.0260) | 0.5354 (r 0.0354) | 0.0614 |
| time | 0.4226 (r 0.0774) | 0.6059 (r 0.1059) | 0.1833 |
| **price** (registered) | 0.5101 (r 0.0101) | 0.4976 (r 0.0024) | 0.0124 |

## 7. WHAT THIS CONTROL CANNOT DO — stated in advance, not after it disappoints

1. **It cannot prove edge-freeness.** A block bootstrap destroys predictability at scales *longer*
   than `BLOCK_MIN`; any edge living entirely inside 5 minutes survives the transform. The claim is
   bounded to exactly this: edge-free **at the probes' horizon**, which is the horizon the probes
   use. An intra-5-minute edge would contaminate, and nothing here would see it.
2. **The price LEVEL path is synthetic even though every bar is real.** Return-space reassembly is
   what buys seamless continuity; the cost is that the multi-hour level trajectory is a construction.
   Trend at the scale of a session is therefore only partially preserved — which is the single most
   important structure F029 says is missing, so this control **under-tests the very objection that
   motivated it**. It is a strict improvement over a Gaussian walk and is not a full answer.
3. **It licenses nothing.** Charter §4.4/§4.7: the licence comes from a fresh-context external seat.
   A transferring null here removes a blocker; it does not certify the harness.

## 8. RUN PLAN

```bash
python3 bin/factory_realtape.py verify                       # transform's own mutation proofs
python3 bin/factory_realtape.py null --instrument USA500IDXUSD --days 400 \
        --json research/factory/realtape_null.json           # primary
python3 bin/factory_realtape.py null --instrument USATECHIDXUSD --days 400 \
        --json research/factory/realtape_null.json --append  # replication
```

Both arms of the comparison are recorded per (instrument, arm, probe) with `source=vendor`, `days`,
and the residual against its synthetic baseline.
