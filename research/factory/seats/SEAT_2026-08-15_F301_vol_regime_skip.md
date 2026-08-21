---
id: SEAT_2026-08-15_F301_vol_regime_skip
type: refutation
created: 2026-08-15
status: live
title: "D030 round 1 — F301 (vol-regime skip WORLD-CLAIM). Verdict: REFUTED."
related: [F301, F266, F122, F051, F186, L025, L032, PRESPEC-vol-regime-skip, GOVERNANCE_FACTORY]
---

> **INCLUDED AS AN EXAMPLE OF THE PRACTICE, NOT AS A RUNNABLE ARTIFACT.** The candidate module
> this seat audits (`factory_vol_regime_skip.py`) and the vendor train tape it re-scores are not
> part of this extraction, so the tables below cannot be re-derived from this repository. What
> travels is the shape: a fresh-context adversary, given the claim and the tree and nothing of the
> author's reasoning, whose default verdict is REFUTED and who must be argued out of it by
> evidence. It found that the pre-registered specification said one thing and the deciding line of
> code did another — the stop was sized from the session's own realised range, a number nobody has
> at the open — and that the module's own passing selftest never looked at the stop. Seven of nine
> cells flip sign once the specified stop is used. The claim was withdrawn.
>
> The verbatim transcript is kept rather than a summary of it, because a summary passes through
> the author's memory, and the author is the party the seat exists to check.

# D030 EXTERNAL REFUTATION — F301 (WORLD-CLAIM, `ungraded`)

Round-1 seat. Not a fold-scorer. Spawn framing is the author's; the files and the train tape are the evidence.

Claim as filed:

> Vol-regime skip is NO_INFORMATION on train: rate clears (2.45/wk) but HIGH mean −0.065R does not beat always-long (−0.083R); every HIGH CI upper ≤ +0.014 < +0.15R. Holdout untouched.

I did not run `screen` (it writes artifacts). I did not open any date ≥ 2024-01-01. I ran `selftest`, re-derived the JSON arithmetic, and re-scored the declared object and the implemented object from the train tape through the module.

---

## 1. IS THE PROBLEM REAL?

Yes as a *research question*. This is not machinery for an undemonstrated bug. It is a train-only pre-screen of the rate-first successor F266 demanded after C9 died on rate. The pre-spec mtime is 04:18:21; the runner 04:18:29; the JSON/artifact 04:19:34; the NOTE 04:20:05; F301 `ts` 04:20:21. Same commit (`894c0f55`). Grid, primary (HIGH, median of rate-clearers, never argmax, never LOW), unpaired information test, BL-F1, and the kill table are written in `PRESPEC_vol_regime_skip.md` before those numbers exist on disk.

That does not prove no unpublished scratch run happened in the eight seconds between prespec and module. It is the evidence the repo can give, and it is consistent with spec-then-official-run.

The problem that *this seat* is here for is whether the filed WORLD-CLAIM is about the object the pre-spec named. It is not.

---

## 2. DOES THE MEASUREMENT ACTUALLY SAY WHAT IT CLAIMS?

### 2.1 Selftest — PASS, 10/10, vacuous on the defect that kills the claim

```
python3 bin/factory_vol_regime_skip.py selftest   # exit 0
```

Loader refuses `2024-06-03`. `list_train_days` yields 3059 days, first **2012-01-04**, last **2023-12-29**, zero dates ≥ 2024-01-01. Argparse block does not mention `TRAIN_END` / `HOLDOUT`. Pad through-stop does not fill; a live through-print does. `decisive_block` on a fake 9-cell grid returns 9.

What it does **not** lock:

- A `leak` counter is incremented inside the look-ahead loop and **never asserted**.
- The window check is last-slot-equals-prev (value equality). It would not catch today's `rv` inserted at `window[0]`.
- It never builds a two-day fixture in which today's range ≠ yesterday's range and asks whether the **stop** used yesterday. That is the specified look-ahead. The selftest does not touch it.
- It does not lock median-vs-argmax in `verdict_high` (F299's selftest did; this one does not).
- `decisive_block` is `return list(high_cells)` — an identity. The count check cannot fail unless someone later edits that function.

SELFTEST PASS is not a lock on F301's numbers and is not a lock on the specified trade.

### 2.2 Re-derived load-bearing numbers (JSON, internal)

**(a) All 9 HIGH rates ≥ 2.0.** Range 2.4406–2.4658. All clear. Median-cell rate 2.4586 ≈ 2.46/wk (claim says 2.45). Alternate denominators still clear: n_kept/5 = 2.44; n_cache/5 = 2.28; calendar span of kept days (623 weeks) = 2.24; full 2012-01-01…2023-12-31 (626 weeks) = 2.23.

**(b) The declared primary is the positional median, not the argmax.** Sorted HIGH means `[4] = −0.065204372896046` = `statistics.median` = cell W=20 k=0.35. Least-bad cell is a different row (W=20 k=0.50, −0.0438). L025/L032 `[0]` / argmax on the *published reduction*: **fails**. `verdict_high` takes `means[len//2]` then the first declaration-order cell with that mean. No silent `[0]`.

**(c) "every HIGH CI upper ≤ +0.014" is already false on the published object.** W=20 k=0.25 widest hi = **+0.014314760963904325**. The other eight are ≤ +0.014. Max hi is still 0.0143 ≪ 0.15, so this alone does not move the bar-fail. It is rounding theater in the claim sentence, the NOTE, and the REPORT.

**(d) Holdout dates.** JSON contains exactly two ISO dates: `train_end=2023-12-31` and `holdout_start=2024-01-01`. Artifact text: one date, `2023-12-31`. Scored HIGH dates on the tape: first 2012-02-17, last 2023-12-21, **0** ≥ 2024-01-01. `phase2_start` is still `null`. No vol-regime-skip prereg row exists. Cache *contains* 682 holdout-named files (2024-01-01 … 2026-08-11); `list_train_days` excludes them by string bound and the wrapper raises `HoldoutPeek` on load. Filenames were listed; contents were not read. BL-F1: **fails to breach.**

**(e) `beats_k1` is correctly False on the published numbers.** HIGH −0.065204 > K1 −0.082495, but HIGH CI lo −0.137406 is not > K1's mean. Code: `beats_k1 = sm["mean"] > k1m and lo > k1m`. Reported `false`. Matches.

**(f) Tape reload of the published cell.** `score(tag_regime(build_days(), 20), "HIGH", 0.35)` → n=1397, mean **−0.065204372896046**, widest (−0.13740574551842574, 0.004223560197632284), L=63, rate 2.4586413234776483. Exact match to JSON. This is not a JSON-internal check; it is a reload of the vendor train days. The published numbers *are* what the module computes.

The claim's arithmetic about the **implemented** object holds (with the 0.014 rounding). The implemented object is not the specified object.

---

## 3. THE HOLE — same-day range stop, not the pre-specified prior-day stop

Pre-spec §1, twice:

> stop at `k × prior-day RTH range` (points)
>
> stop `k` | **0.25, 0.35, 0.50** × prior-day RTH range

`score()`:

```python
sl = k * r["range_pt"]
```

`r` is **today's** session row. `range_pt` is today's RTH high−low, known only after 15:58. At the 09:31 open the stop is not a number a trader can place.

The regime tag is causal (`rv[t-1]` vs median of the previous W completed rvs; today's rv is appended *after* the tag; window-last == prev on all 2841 tagged W=20 days). They locked the estimator and left the **stop** on today's range. That is L032 in the form this repo has already paid for: the pre-spec names the look-ahead, the selftest advertises it, the deciding line does the other thing.

This is not a small unit slip. HIGH means yesterday was the loud day. Vol mean-reverts on this tape:

| polarity | median(today range / prior range) | share today < prior |
|---|---:|---:|
| HIGH (primary) | **0.795** | **69.5%** |
| LOW | 1.218 | 33.7% |

So on the declared primary, the leaked stop is systematically *tighter* than the specified stop. That manufactures extra −1R days and inflates cost/sl (94 HIGH k=0.35 days have cost/sl > the entire 0.15R MUE under same-day; 10 under prior-day). Concrete: 2012-03-01, today range 20.48 vs prior 29.80 — same-day stop prints **−1.17R**, prior-day stop prints **+0.88R**. 2013-02-25, today range 1.89 pt after a 20.86 pt yesterday — same-day sl = 0.66 pt against a 1.20 pt cost (**−2.81R**); prior-day **−0.34R**.

I re-scored every HIGH cell with `sl = k × previous kept session's range_pt` (the specified, pre-open quantity). Same walker, same cost, same days, train only.

| W | k | implemented mean (today range) | specified mean (prior range) | specified CI hi |
|---:|---:|---:|---:|---:|
| 10 | 0.25 | −0.1021 | −0.0197 | +0.0688 |
| 10 | 0.35 | −0.0876 | +0.0227 | +0.0936 |
| 10 | 0.50 | −0.0551 | +0.0157 | +0.0734 |
| 20 | 0.25 | −0.0747 | +0.0110 | +0.0991 |
| 20 | 0.35 | **−0.0652** (headline) | +0.0419 | **+0.1110** |
| 20 | 0.50 | −0.0438 | **+0.0182** (specified median) | +0.0721 |
| 40 | 0.25 | −0.0871 | −0.0067 | +0.0767 |
| 40 | 0.35 | −0.0631 | +0.0371 | +0.1069 |
| 40 | 0.50 | −0.0456 | +0.0216 | +0.0755 |

Seven of nine specified HIGH means are **positive**. The L025 median of the specified grid is W=20 k=0.50 at **+0.0182R**, not W=20 k=0.35 at −0.0652R. Max specified CI hi is **+0.111**, not +0.014. K1 at the specified stop is **+0.014R** at k=0.50 (W-min), not −0.083R.

On W=20 k=0.35 HIGH, 226 days stop under today's range and live under yesterday's; only 18 go the other way. Mean(todayR − priorR) = **−0.107R**.

The filed sentence therefore attributes three load-bearing numbers (−0.065R, −0.083R, every CI hi ≤ +0.014) to a skip the pre-spec did not define. A later session inheriting "CI tops out at +0.014, all means negative" will think the specified skip is ~8× further from the bar than it is, and will think the sign is the opposite of what the specified trade prints. That is the F182 failure mode: a wrong explanation of a kill, entering the elimination list.

The verdict *label* NO_INFORMATION is what the specified object would most likely still print — see §5. That is not a defence of F301's numbers. GOVERNANCE_FACTORY §4: a claim enters the list at its measured width. These widths are of the wrong object.

---

## 4. THE FOUR FEATURED ATTACKS (and the rest of the spawn list)

### 4.1 BL-F1

Fails to breach. See §2.2(d). `load_day` in this module wraps `factory_session_partition.load_day` and raises `HoldoutPeek` on any date ≥ 2024-01-01. No CLI override. I did not call the unwrapped loader on a holdout date.

### 4.2 Look-ahead in rv / median

The **tag** is clean. `tag_regime` computes `med = median(rvs[-W:])` *before* appending today; `_window` after the append is the previous W rvs; last slot equals `_prev_rv` on every tagged W=20 day; zero value-collisions of today with prev. HIGH[t] = rv[t−1] > median(rv[t−W], …, rv[t−1]) matches the pre-spec (yesterday is inside the median; that is declared, not a leak).

The **stop** is the look-ahead. It is not in the selftest. It is the hole.

### 4.3 HIGH promoted vs LOW cherrypick

Fails to breach. HIGH is declared primary in the pre-spec before the official numbers. LOW cannot be the headline. Published LOW is entirely negative; several CIs exclude 0 from above (worse than HIGH). Cherry-picking the polarity that *dies* is the opposite of the usual cheat.

Specified (prior-day) LOW is also not a survivor: every LOW cell `beats_k1=False`, every LOW CI hi < +0.15. They did not bury a living opposite polarity. They also did not measure it — the LOW table in the artifact is the leaked stop.

### 4.4 Paired-on-taken-days identically zero — did they actually use unpaired?

Yes. `beats_k1` compares HIGH's subset mean to K1's full-sample mean. `paired_diff` is defined, never called, and **crashes** if you do call it (`summarise` reads `p[4]` on a 2-tuple). I built the intersection myself on W=20 k=0.35: 1397 paired diffs, all identically 0.0, as the pre-spec said they must be (HIGH long on a HIGH day *is* K1 on that day). They did not launder a zero paired test into a result. Unpaired is what ran.

### 4.5 K1 universe (W=min) vs HIGH W=20 manufacturing the +0.017

Does not manufacture it. GOVERNANCE_FACTORY §4 rule 4 ("never compare cells computed on different populations") is violated — K1 is scored on the W=10 universe (n=2851) and the headline HIGH cell is W=20 (n=1397 of 2841). Same-universe K1 W=20 k=0.35 is **−0.083026**, not −0.082495. HIGH − K1_W20 = **+0.01782**; published HIGH − K1_W10 = **+0.01729**. The mismatch *shrinks* the filter's apparent edge by 0.0005R. The +0.017 is the mixture identity: HIGH −0.065 and LOW −0.100 against K1 ≈ (1397·HIGH + 1444·LOW)/2841. Not a sample-size artifact.

On the specified stop the same mismatch is equally small and equally not the hole.

### 4.6 Rate denominator

Fails to flip. Every defensible reading of "per week" on this train still clears 2.0 (see §2.2(a)). TIE days are counted in `n_elig` and not taken; observed TIE count is **0** at W=10/20/40. `weeks = n_elig/5` assumes a 5-day week of eligible sessions; calendar weeks are the stricter reading and still pass.

### 4.7 F051 family overclaim

Fails to close the family. NOTE and F301 body keep F122's vol-regime *family* open and close "this skip, at this power, on this tape." That is the F051-correct scope. "No detectable regime information" is slightly strong given a +0.017 point estimate inside an MDE of 0.071 — F051's own lesson is that failing to clear a bar is not "information is absent" — but they did not file a family kill. Not the refute.

Closing "this one-condition realized-vol skip" as a candidate, when the numbers attached to the close are of a non-specified stop, **is** the refute. The family sentence is fine; the skip-level close is not earned at the filed width.

### 4.8 L025 / L032 `[0]` / argmax

The published reduction is the median of the **leaked** 9. That attack on the reduction fails (see §2.2(b)). L032's actual content is the one that fires: *naming the defect in the pre-spec does not prevent the defect*. They wrote, in bold-adjacent prose, that today's range is not in the estimator and that the selftest must lock it. Then `score()` sized the stop with today's range. The selftest passed. The headline cell of the specified grid is a different (W, k) than the one they published.

---

## 5. DOES THE SPECIFIED OBJECT STILL DIE?

I am not the builder and I am not filing a replacement finding. For the reversal condition it is necessary to say what the specified object did in this seat's recompute, train only, central cost, same walker:

- All 9 HIGH rates still clear 2.0.
- L025 median HIGH cell: W=20 k=0.50, n=1397, **+0.0182R**, CI [−0.0341, +0.0721], MDE 0.053.
- K1 prior-day, same k, W-min: **+0.0138R**. HIGH−K1 = +0.0044 < MDE. CI lo −0.0341 is not above K1. `beats_k1=False`.
- Least-bad HIGH cell (W=20 k=0.35): +0.0419R, CI hi **+0.1110**, delta vs same-universe K1 +0.0293 < its MDE 0.0685. Still `beats_k1=False`.
- Every specified HIGH and LOW CI hi < +0.15. No cell is a TRAIN_SURVIVOR. No cell is FAILS_BAR (that label requires `beats_k1`).
- Label that `verdict_high` would emit on this grid: **NO_INFORMATION**.

So: the *direction* "this skip, specified, does not clear +0.15R and does not beat always-long by more than MDE on train" is what a corrected screen would most likely file. F301 did not file that. It filed −0.065 / −0.083 / ≤+0.014, which are false of the specified skip.

I did not treat this as a reason to let F301 through. A wrong-object kill with a coincidentally similar label is how the next session inherits a false residual (0.136R of "room to the bar" that is actually 0.039R, and a sign that is actually positive).

---

## 6. WHAT IT BREAKS AND WHAT IT HIDES

- **Consumes the elimination list.** F301 is a WORLD-CLAIM. Later sessions will not re-open a skip whose file says "all means negative, CI ≤ +0.014." The specified skip's means are mostly positive and its friendliest CI reaches +0.111.
- **Selftest hides the defect.** PASS + "today's rv is excluded from the window" reads as look-ahead-clean. The stop was never in the test.
- **`paired_diff` is dead and broken.** A reviewer who trusts the comment "compared to K1 on that cell's own taken dates" (module L300–302) will think a paired test ran. It cannot run.
- **Adverse was promised and not run.** Pre-spec §2: "`adverse` reported on the median HIGH cell only." The string `adverse` does not appear in the module. Adverse US100 is 26.71 pt; on the published median sl (~27.5 pt) that is ~−1.37R mean. For a kill at *central* this omission cannot rescue the candidate, so it is not the hole. It is a spec break.
- **`beats_k1` ignores MDE** despite the pre-spec table ("does not beat K1 by more than MDE"). Both definitions give False on both objects. Residual.
- Second walker (`walk_long` / `walk_short`), not `factory_backtest.walk_trade`. Same shape as the overnight harvest unit. Not the hole; named.

---

## WHAT I ATTACKED AND WHAT WOULD HAVE BROKEN A CLEAN CLAIM

Attacked: BL-F1 date leakage; look-ahead in rv/median *and* in the stop; HIGH vs LOW cherrypick; unpaired vs identically-zero paired; K1 W=min vs HIGH W=20 day-set (F059 / GOVERNANCE §4.4); rate denominator; F051 family overclaim; L025/L032 `[0]`/argmax; JSON-vs-tape identity; CI ≤ +0.014 rounding; missing adverse; `beats_k1` vs the MDE table; pre-spec-after-the-fact; `phase2_start` / prereg spend.

It would have broken a *clean* F301 if: any scored date ≥ 2024-01-01; the headline cell was the argmax (W=20 k=0.50 leaked, −0.0438); a HIGH CI hi ≥ 0.15 on the **specified** stop; the specified median HIGH beat K1 by more than MDE with CI lo above K1; today's rv sat in the median window; LOW had been swapped in as the headline after seeing it; the pre-spec post-dated the JSON; the finding closed the F122 family.

The stop basis fired. The rest did not.

---

## VERDICT

**REFUTED**

F301's load-bearing numbers (−0.065R, −0.083R, every HIGH CI upper ≤ +0.014) describe `sl = k × today's RTH range`, which is not known at 09:31 and is not the stop the pre-spec named (`k × prior-day RTH range`). On the specified stop the same tape prints a different primary cell, a positive median mean (+0.018R), and a max HIGH CI hi of +0.111. The selftest that claims to lock look-ahead does not look at the stop. Holdout was not touched; that is the only half of the claim that survives.

**REVERSAL CONDITION.** A train-only re-screen in which `score()` sets the stop from the previous kept session's `range_pt` (a quantity available before 09:31), the selftest has a fixture that fails if today's range is used instead, and the published headline numbers remain HIGH mean −0.065R, K1 −0.083R, every HIGH CI hi ≤ +0.014. Alternatively: F301 is superseded by a new row whose numbers are the specified object's actual width (this seat's recompute: median HIGH ≈ +0.018R at W=20 k=0.50, max HIGH CI hi ≈ +0.111, `beats_k1=False`, every CI hi < +0.15) and whose module implements that stop.

**SALVAGE PATH.** Fix the stop; lock it; re-run `screen`; file a new finding at that width. Do not keep F301's −0.065 / −0.083 / ≤+0.014. The label NO_INFORMATION is the likely restatement, not a reason to preserve the old numbers. None of that is a build I am authoring.

---

## OWED (not the refute)

1. `adverse` on the median HIGH cell, as the pre-spec already required.
2. `paired_diff` is unreachable and would IndexError; delete it or make `summarise` accept a 2-tuple. Do not cite the comment at L300–302 as if a same-date comparison ran.
3. `beats_k1` should implement the pre-spec's MDE clause or the table should be rewritten to match the code. Both currently agree on False; the drift is still a future footgun.
4. Selftest should assert the `leak` counter it bothers to increment, and should lock median-vs-argmax the way the overnight-harvest selftest does.
5. K1 should sit on the same eligible-day universe as the HIGH cell it is compared to (GOVERNANCE §4 rule 4). It did not flip this result.
6. Claim-sentence rounding: even the leaked object has a CI hi of +0.01431, not ≤ +0.014.

Do not spend the holdout. Do not file a prereg row. Do not treat F122 as closed. Do not treat F301's numbers as the specified skip.

**REFUTED**
