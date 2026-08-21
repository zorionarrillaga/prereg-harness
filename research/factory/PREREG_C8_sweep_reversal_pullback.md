---
id: PREREG-C8-SWEEP-REVERSAL-PULLBACK
type: prereg
created: 2026-08-13
status: frozen
title: "C8 — one elaborated candidate: a liquidity-sweep reversal with a pullback limit entry and two declared exit architectures, frozen before any outcome exists"
related: [F001, F050, F051, F096, F115, F118, F122, F125, F152, F155, F156, F157, F160, F161,
  F171, F177, F179, F182, F183, L021, L024, L025, L026, D048, D055, C5, C6, C7]
---

# PREREG — C8, THE DEPTH CANDIDATE

> **Frozen BEFORE any outcome is evaluated.** The geometry pre-screen has run and its numbers are
> in §6; geometry evaluates no outcome and is numerically identical for the rule and for all three
> controls, so it leaks nothing into the quantity §8 reads. **No expectancy, hit rate, margin or R
> exists for this candidate in this document.**

## 1. THE QUESTION, AND WHY IT IS ONE CANDIDATE AND NOT A GRID

C7 screened 14 sign-based side features on expectancy through a reachable bracket, against three
controls, at every cell of a nine-cell grid, and **zero arms cleared anywhere** (F177). F182 then
measured *why*, in the form that actually matters: the momentum trio **does** carry real train-era
conditional timing — it goes short precisely on days when being short pays **+0.43…+0.53R** against
an unconditional **+0.1356R**. What it cannot do is beat a **drift-aligned control**: margin over
always-short is **+0.064R at SE 0.053**.

> ★ **AND THAT IS WHY MORE POWER IS NOT THE ANSWER.** Resolving +0.064R needs SE ≈ 0.023 ⇒
> n ≈ 3,900 days, the whole 2012-2026 corpus, which spans the cost-regime break. **And it would not
> matter: +0.064R is BELOW the +0.15R MUE.** A perfectly-resolved version of that effect is still
> not tradeable. ⇒ The bottleneck is neither measurement precision nor another axis of breadth: the
> effect size available to a **one-line feature** is roughly 2× too small.
>
> ⚠ **What that conclusion EXCLUDES:** it rules out the reading that a *different* one-line feature
> — one C7 did not enumerate — could clear the MUE. C7 tested seven, all drawn from where price sits
> relative to its own recent path; F182 measured them as **5.04 effective independent arms**, so the
> grid sampled far less of that space than 14 suggests. **"One-line features are 2× too small" is an
> inference from a correlated sample of them, not a proof about the class.** The alternative it rules
> out is cheap to run and is named in §2 as the first thing to try if C8 dies.

> **Does a SIDE drawn from a structural event at a liquidity location — rather than from the sign
> of a scalar — carry enough directional information to beat always-long, always-short and
> alternating, through a bracket the candidate itself defines?**

**The unit is ONE elaborated candidate.** Every form that has ever passed anywhere in our source
ledger (`CATALOGUE_2026-08-13_structure_sweep.md`) is elaborate; every one-line feature we have
built has died. C8 is the synthesis §6 of that catalogue authorises: **Form G** (liquidity-sweep
reversal — the only form in the sweep whose geometry is asymmetric *by construction*), gated by
**Form H**'s clock window, entered by **Form E**'s refusal-to-chase pullback.

⚠ **THE STRONGEST COUNTER, stated so the next session can overrule this rather than inherit it:**
an elaborated candidate has **more free parameters**, and this repo's entire discipline exists
because free parameters manufacture results (L025). A grid of one-line features is *auditable*; a
setup/trigger/entry/exit structure is much easier to fit. **The answer here is mechanical, not
rhetorical: all four free parameters are swept in full (81 configurations), the judged one is the
POSITIONAL median of each, fixed in code before this document was written, and the argmax is
printed only so that it is visible it was not used.**

⚠ **THE SECOND COUNTER, and it is the one I believe:** C7's kill was *not* "nothing separates."
A drift-aligned control is a brutal bar, and a reversal rule in a **rising** era must beat
always-long while systematically taking short trades on roughly half its days. C8 is more likely to
die against K1 than against the tape.

## 2. ⛔ SCOPE — WHAT THIS SCREEN CAN AND CANNOT DO

- **One instrument, one vendor.** `USATECHIDXUSD` (US100), Dukascopy BID CFD 1-minute candles.
  Not a free choice: `factory_backtest.cost_in_r` refuses every other instrument. ⚠ **The rule
  reaches the ≥2/wk floor on its own legs by a margin of 0.20/wk (§6), so the portfolio-wide
  reading D055 ratified is NOT relied on — and it is NOT available either, since F179's vendor-ASK
  path is an unruled T3.**
- **It cannot prove anything empty.** F051 binds absolutely: DEAD means *not detectable at this
  power in this budget*. At n≈334 the 80%-power MDE is **+0.19R**, i.e. **1.3× the MUE** — better
  than C7's 1.8–2.0×, and still a bar a real +0.10R effect would fail.
- ⛔ **IT DOES NOT TEST A TRAILING STOP, so Form I's falsifiable negative claim is UNTESTED here.**
  `harness_ruler.walk_bounds` accepts a moving *target* but a fixed stop *price*; a moving stop means
  forking the one ruler, and C2's v1 pooled number was VOID because two rulers disagreed. A
  candidate may not modify the instrument that judges it. **Search-map item 5 is therefore only
  HALF addressed** (static bracket vs location target), and the trailing half stays open.
- ⛔ **It does not test partial fills**, so Form I's multi-target/breakeven-ratchet architecture —
  the mechanism that converts a 1:1 shape into an asymmetric one without a higher hit rate — is
  likewise untested. Same reason, same ruler.
- **It tests ONE liquidity level: the prior RTH session's high and low.** ⇒ This **EXCLUDES**
  intraday pools (relative-equal highs/lows, the opening range, the overnight extreme) and any
  multi-level confluence. Those are cheap to add and are deliberately not added: each is a free
  parameter on the *setup*, and the catalogue's own §6 discipline is *synthesise first, register
  once*. **A sweep of a level this screen does not name is untested, not dead.**
- **It tests the SWEEP-FAILURE side only.** ⇒ **EXCLUDES** the continuation reading (acceptance
  beyond the level ⇒ trade *with* the break), which is the same event's opposite interpretation and
  is a separate candidate. C7's lesson — that assuming the informative polarity is what C6 did, and
  it lost — argues for running both. **It is not run here**, because a second polarity doubles the
  multiplicity of a screen whose whole power advantage over C7 is its tiny denominator. Named as
  the first thing to test if C8 dies.
- **Restricting the train era to 2021+ is a real degree of freedom** — inherited from C7 §4,
  unchanged, and it excludes any effect living only in the older, higher-cost tape.

## 3. THE FRAME — F161's, inherited and NOT re-derived, with two declared departures

| | |
|---|---|
| **Instrument** | `USATECHIDXUSD` (US100), RTH 09:30–16:00 ET, vendor 1-minute candles |
| **Era** | **2021-01-01 → 2023-12-31** (train). The holdout 2024-01-01→2026-08-11 is **NOT TOUCHED** |
| **Setup** | prior RTH session high `PDH` / low `PDL`. Parameter-free, mechanical, causal |
| **Trigger** | first bar in `[09:30, T1]` whose running excursion exceeded the level **and** whose CLOSE is back inside it. Side = **against** the sweep. `k = 1` — one trade per day |
| **Entry** | resting **LIMIT** at `close + φ × (swept extreme − close)`, live `M` minutes. **φ = 0 is a MARKET entry at the trigger close** — the no-pullback control slice |
| **Stop** | **STRUCTURAL**: beyond the swept extreme, `+ b × range(trigger − 30min, trigger)` |
| **Exit** | **X1** `T = rr × S`, rr ∈ {1.5, 2.0} · **X2** the opposing pool (`PDL` after a high sweep) · both hard flat at **15:58 ET** |
| **Cost** | `cost_model.json` central **1.20pt in POINTS** (F160), charged through `cost_in_r(…, sym=SYM)` |
| **Eligibility** | scale window ≥10 bars and range > 0 · stop non-degenerate · `1.20 / S ≤ 0.15R` · fill at or before **15:00** |

**The two departures from F161, and both are the point:**
1. **The stop is structural, not `k × a range`.** F161 fixed *where the scale comes from* (the hold
   window's own range, never the day's) because C6 mis-declared its bracket by 3.6×. C8 honours the
   principle by a different route: the stop is pinned to the price the sweep failed at, which is a
   *location on the same tape the hold runs over*, and the buffer that widens it is denominated in
   the 30 minutes immediately before the trigger. ⇒ This **EXCLUDES** the reading that C8's
   geometry inherits C6/C7's measured reachability. It does not. **Reachability is re-measured for
   this frame in §6 and it is the gate that qualifies X2.**
2. **The entry time is event-driven, not a clock.** ⇒ This **EXCLUDES** direct comparability with
   C6/C7's cells: their `n` is every day by construction, C8's is 44% of days. The controls are
   what restore comparability, and they are the only thing that does.

**The F156 degenerate-feed guard is ON** (`norm_range`, 0.45, calibrated for this symbol).
Measured: it drops **0 days in this era** — a checked fact, and it also means the prior-session
chain `PDH/PDL` is intact (dropping a day would rewire the day after it).

### 3a. The cost ceiling — declared, DERIVED, and NEARLY NON-BINDING

`cost_in_r ≤ MUE`, read from `budget.json`. It removes a parameter rather than adding one, is known
strictly before entry, and applies identically to the rule and to all three controls, so **it
cannot manufacture a signal-vs-control difference**. Measured at the judged config it excludes
**1 of 335 trades**. ⚠ **What it EXCLUDES:** the excluded trades are those whose pullback filled
closest to the swept extreme — i.e. the *best* entries — so the ceiling is systematically removing
the high-R:R tail, and any effect living specifically there is removed from the sample.

## 4. ⚠ THE FOUR SWEPT FREE PARAMETERS — all swept, positional median judges (L025)

| # | parameter | swept values | **judged (positional median)** | what it controls |
|---|---|---|---|---|
| 1 | `T1` window end | 11:30 · **13:00** · 14:30 | **13:00** | how late a sweep may fire |
| 2 | `φ` pullback | 0.00 · **0.33** · 0.66 | **0.33** | **the entry-price mechanism** |
| 3 | `b` stop buffer | 0.00 · **0.25** · 0.50 | **0.25** | how far beyond the extreme the stop sits |
| 4 | `M` limit patience | 15 · **30** · 60 | **30** | how long the limit rests |

**81 configurations × 3 exit readings, all run, none dropped after the fact.** The judged
configuration is written in `bin/factory_c8.py` as the constant `JUDGED` and was fixed before this
document existed.

★ **THE φ AXIS IS THE ENTRY-PRICE TEST, AND NO SEPARATE ARM IS ADDED FOR IT.** φ=0 is a genuine
market-entry-at-the-trigger-close control — C6's and C7's convention exactly — so the φ contrast
across the sweep *is* search-map item 4, measured. ⇒ This **EXCLUDES** reading a good C8 result as
evidence *for* pullback entry without reading the φ=0 slice: if φ=0 does as well, the pullback
bought nothing, and the report must say so.

⚠ **L025's known hole applies here exactly as it applied to C7: a sweep RANGE can be chosen so its
middle is the value the author wanted.** No robustness check inside a range can see outside it. The
mitigation is that all four ranges bracket their natural degenerate endpoints — φ=0 is *no*
pullback, b=0 is *no* buffer — so the middle is not a hand-placed optimum. **The full 81-row grid
is published so a reader can judge the range, not just the middle.**

## 5. ONE COST TREATMENT, AND THE GUARD IS NOT INLINED

Points only (F160; the price-proportional treatment is REFUTED). ★ **Unlike C7, which computed
`COST_PT / sl` inline, every cost in C8 goes through `fb.cost_in_r(sl_pt, "central", sym=SYM)`** —
so F152's fault (*a guard that can be bypassed by inlining is not a guard*) cannot be re-committed
on this candidate's path. ⚠ The adverse p90 band (26.71pt) is **not** a gate; it is a qualifier, and
it is a brutal one here (§6). It bounds **our current discretionary execution** (n=42 fills), and
C8's entry is a **resting limit** — the one order shape that tail was never measured on. That is an
argument for re-measuring the tail on staged orders, **never** for quoting only the friendly band.

## 6. THE PRE-SCREEN, ALREADY RUN — geometry only, no outcome

`python3 bin/factory_c8.py --prescreen` → `research/factory/prescreen_c8.json` (81 rows).

| gate | judged config | grid median | verdict |
|---|---|---|---|
| **RATE** | **2.20/wk** (n=334 of 758 day-files) | 2.01/wk | **clears ≥2/wk — but only just; see below** |
| **COST** | **E[cost_r] 0.0370R = 25% of the MUE** | 0.0370R | clears the 33% gate |
| **POWER** | n=334 ⇒ MDE **+0.188R** (1.5:1) / **+0.217R** (2:1) | — | clears the 0.60 gate; **1.3–1.4× the MUE** |
| | ⚠ **EXCLUDES**: an MDE above the MUE means this screen can only detect an edge **larger than the bar we would trade at**. A true +0.15R effect — exactly a survivor — has well under 80% power here. ⇒ **A DEAD verdict rules out a LARGE effect and says nothing about a marginal one.** The shape this excludes is "C8 is dead" read as "C8 has no edge"; it may only be read as "C8 has no edge this n can see." | | |
| **REACH (X1)** | 1.5:1 on **89.2%**, 2:1 on **79.3%** (union) vs breakevens 41.5% / 34.6% | — | clears |
| **REACH (X2)** | pool median **5.36R**, reached on **18.9%** vs a 16.3% breakeven | — | ⚠ **MARGINAL — 2.6 points** |

★ **UNLIKE C6 AND C7, THE RATE GATE HERE IS INFORMATIVE.** A clock rule fires by construction and
*cannot* fail it (PREREG-C7 §6 said so explicitly). C8 is price-triggered, so 2.20/wk is a measured
property of the tape and not a restatement of the spec.

⛔⛔ **AND THE RATE GATE IS THE FRAGILE ONE. IT PASSES BY 0.20/wk AND ITS PASS DEPENDS ON A SPEC
READING I MADE DURING THE PRE-SCREEN.** The first implementation voided a whole day when the
session's *first* sweep-failure had no definable 30-minute scale window — 178 of 758 days, 23% of
the corpus, discarded for a quantity that is multiplied by zero in a third of the grid. That
conflated k=1 ("at most one trade per day") with eligibility ("a trade needs a definable stop
scale"), and made ineligibility contagious to the rest of the session — the same shape as the
uncounted differential dropout `harness_ruler.py` was repaired for. **Repaired before any outcome
existed: an ineligible trigger is skipped, the day is not.** Effect: **1.44/wk → 2.20/wk.**

> ⚠ **THE CHOICE THAT MADE MY OWN CANDIDATE VIABLE IS THE ONE TO DISTRUST.** §5 of the 08-13
> handoff: *whichever way a claim points, ask which choice makes it easier, and take the other.*
> So the stricter reading is measured and frozen here rather than left to be discovered later:
> **the T0=10:00 variant** — *the window may not open before the scale that denominates its stop
> exists* — gives **1.99/wk, i.e. it FAILS the floor by 0.01.** ⇒ **C8 sits ON the ≥2/wk floor, not
> above it.** Every downstream number carries that. **This EXCLUDES quoting C8's rate as a clean
> pass**, and it means a rate-based kill is available to a later reader who prefers the stricter
> reading — which is a legitimate reading, not a nitpick. **146 of the 334 firing days used a later
> trigger**, and a reader who holds that a 09:33 setup and a 09:43 setup are different events
> should subtract them.

⚠ **THE ADVERSE BAND IS 549% OF THE MUE** (0.8237R/trade). C8's median stop is ~34pt, and 26.71pt
against that is a catastrophic fraction. **C8 is a pass at 1.20pt and a fail at 26.71pt**, exactly
like every candidate before it — and unlike them, its entry is a resting limit at a price we chose,
which is the shape a p90 measured on discretionary market orders least describes. Neither of those
sentences may be dropped when the other is quoted.

⚠ **X2's TARGET IS ESSENTIALLY UNREACHABLE AND THIS IS PRE-DECLARED, NOT DISCOVERED.** The opposing
pool sits a median **5.36R** away and is touched by *either* side on 18.9% of days against a 16.3%
breakeven. ⇒ **X2 is expected to resolve overwhelmingly on the 15:58 time-stop, i.e. it is a
fixed-horizon rule wearing a bracket's costume — the exact F155 defect that killed C6's
declaration.** It is run anyway, because "the practitioner location-target exit is a time-stop in
disguise on this instrument" is a real finding about search-map item 5 and it costs one walk. **It
may NOT be reported as a genuine bracket, whatever it returns.**
⚠ **What pre-declaring X2 unreachable EXCLUDES:** it rules out reading a *positive* X2 result as
evidence for location-targeting. If X2 wins, the honest reading is that the **15:58 time-stop** won,
because that is what 81% of its trades resolve on — and a fixed-horizon exit is C5's dead shape, not
a new one. The alternative shape not tested is a **nearer** location target (today's opposing session
extreme, or the pool's midpoint), which would be reachable; it is a different setup parameter and is
not swept here.

⚠ **PER-SIDE REACHABILITY IS DELIBERATELY ABSENT FROM THIS DOCUMENT.** F183 refuted C7's use of the
OR-over-both-sides oracle as a per-trade ceiling, and the per-side split is the honest statistic —
but C8's side is **determined by the setup**, so a per-side figure is one lookup from the rule's own
MFE ceiling and would leak outcome into a document that must freeze before outcome exists. ⇒ The
union is used here **only** as the mis-declaration check it was always valid for; **the per-side
split is OWED to the screen** and must appear in the verdict artifact.
⚠ **What withholding it EXCLUDES:** it rules out this pre-screen being able to say the bracket is
*genuine*. The union can only detect a bracket that is unreachable by **anyone**; a bracket
reachable only in the direction the rule does **not** take would pass here and be worthless. ⇒ **§6's
X1 reachability row is a floor on the mis-declaration question, not a pass on it**, and a reader who
wants the real answer must read the screen's artifact, not this table.

⚠ **FORM H's NARROW KILL-ZONE IS EXCLUDED ON A MEASUREMENT, NOT ON TASTE.** 10:00–11:00 yields
1.94/wk and 14:00–15:00 yields 1.10/wk **on triggers alone, before any fill or cost attrition** —
both below the floor. ⇒ This **EXCLUDES** the possibility that the effect lives only inside a
narrow hour: if it does, C8 cannot see it, and no result here bears on it.

## 7. THE CONTROLS — identical everything except the side

**K1** always LONG · **K2** always SHORT · **K3** alternating by day index. Each takes the **same
day, the same entry index, the same entry price, the same `sl_pt` and the same target in R** as the
rule, on its own side. ⇒ The comparison isolates **the side and nothing else** — setup, timing,
entry mechanism and geometry are held fixed — which is correct, because the side is the measured
bottleneck. ⚠ **What that EXCLUDES:** the controls cannot tell us whether the *setup* is worth
anything relative to trading at a random minute. A rule whose entire value is "trade at 11:07 on
sweep days" would be invisible to this design. That question needs a different control (a
random-minute placebo on the same days) and is not asked here.

⚠ **THE ALL-THREE BAR IS BRUTAL AND IT IS KEPT.** In a rising era a reversal rule taking shorts on
roughly half its days must still beat always-long. A rule that merely *approximates* drift scores as
a failure — the intended exclusion (F117 §7), inherited unchanged from C7 §8.

## 8. THE METRIC, THE PRIMARY, AND THE MULTIPLICITY CORRECTION

**Mean net R per trade** (expectancy). Never a hit rate — F118 binds. **Day-clustered bootstrap,
2000 resamples, days drawn whole**, one shared index matrix across every series so a paired margin
is resampled on the same draw of days.

**The primary is the PAIRED margin, computed FIRST** (F153: C6 published the unpaired number and
the sign flipped when paired). For every control, `R_rule(d) − R_control(d)` on the same day, same
config, same walk.

**Multiplicity: 3 primary comparisons** — X1@1.5, X1@2.0, X2. Bonferroni two-sided α = 0.05/3 ⇒
**z = 2.394**. ★ This is C8's real advantage over C7 (z = 3.124): **depth buys power by shrinking
the denominator.** Registry rows remain THE factory-wide denominator and this is row #44.
⚠ **What counting only 3 EXCLUDES:** it rules out charging the 81-configuration sweep to the
multiplicity. That is defensible **only** because the judged configuration is positional and was
fixed in code first — the sweep is reported as robustness, never read for a win. ⇒ **If any later
reader promotes a non-judged configuration, this z is void and the correct denominator is 81 × 3.**
The shape excluded is "pick the best config and keep this bar."

⚠ **The three comparisons are NOT independent** — X1@1.5 and X1@2.0 share every entry and differ
only in where the target sits, and X2 shares the entries too. Bonferroni over 3 therefore
over-corrects, which is the safe direction for a kill and the unsafe one for a near-miss. ⇒ **What
that EXCLUDES:** it rules out reading a near-miss as evidence of nothing. An arm whose unadjusted
95% bound clears but whose adjusted bound does not is **unresolved at this multiplicity, not dead**,
and the kill branch must name it rather than absorb it. The realised correlation between the three R
series is reported so a reader can judge the over-correction rather than take this claim on trust.

## 9. THE BRANCH TABLE — pre-committed, fired mechanically, no parameter added to rescue a branch

1. **DEAD.** No exit reading's paired margin clears its adjusted lower bound against all three
   controls ⇒ published as *"a liquidity-sweep reversal with a pullback entry is measured DEAD at
   this power in this budget on US100 2021-2023."* No holdout spent, no Phase-2 clock, **and no
   fifth parameter, second level, or continuation polarity is added to rescue it** — that repair
   move is what cost the C-series its credibility.
2. **AMBIGUOUS-ONE-READING.** Exactly one of the three clears ⇒ **NOT closed and NOT eligible.**
   Named, family stays open, returns only through its own prereg.
3. **ABOVE-CONTROLS-BELOW-MUE.** X1 clears all three controls at **both** ratios but its median net
   R < **+0.15R** ⇒ not holdout-eligible; published as *"nothing above the measured ceiling."*
4. **SURVIVOR.** X1 clears all three controls at **both** ratios **AND** median net R ≥ **+0.15R**
   ⇒ holdout-eligible. A verdict row is registered and **the operator is told.** ⇒ This **EXCLUDES**
   any path where the harness starts the Phase-2 clock: D055 makes it on-demand and the operator's alone.

**X2 alone can never reach branch 3 or 4**, because §6 pre-declares its target unreachable — a
reading whose bracket is mis-declared cannot promote a candidate whatever it returns. It can only
contribute to branch 1 or be reported as branch 2.

**The latency ladder (0/1/2/5 min) is run on any reading that reaches branch 3 or 4** — and, unlike
C6/C7, it is also **run unconditionally on the judged config**, because C8's central structural
claim is that a resting limit is latency-immune and that claim is falsifiable at zero extra cost.
An arm alive only at +0 min is not operable by us (loop floor ~110s).

## 10. WHAT WOULD MAKE THIS SCREEN ITSELF WRONG

- **The rate gate passes by 0.20/wk on a spec reading I chose mid-pre-screen** (§6). This is the
  single largest threat to C8's standing as a test, whichever way the expectancy lands.
- **σ_R = √rr is an upper bound under a two-point payoff**, and X1 reaches its target on 79–89% of
  days (union), so fewer trades land on an interior EOD mark than in C6/C7 and the bound is
  *tighter* here. Realised dispersion is checked against √rr and reported whichever way it lands.
- **The fill bar is credited to the position, and it has to be.** `walk_bounds` starts strictly
  after the entry minute because a close-entry's bar had already elapsed; a **limit fills mid-bar**,
  so the remainder of that bar is genuinely available. The pessimistic half is applied (if the fill
  bar's *adverse* extreme reaches the stop, the trade resolves SL); the favourable half is **not**
  credited, which is `walk_bounds`' own rule. ⚠ If that asymmetry is wrong, it is wrong in the
  direction that *hurts* the candidate, on ~every limit trade.
- **A limit fill assumes our order was there and was filled at our price.** On a CFD with no
  visible book that is an assumption, not a measurement. It is the same class of assumption every
  harvested form in the catalogue makes, and it is the reason the adverse band cannot simply be
  dismissed.
- **The vendor is not our broker.** Basis −2.45pt, level reconstruction error 1.52/3.56/2.52pt.
  Against C8's ~34pt median stop that is **4–10% of R** — and C8's stop is pinned to a *price
  location*, so a level error moves the stop itself, not just the cost. **This matters more for C8
  than it did for C6 or C7**, whose stops were multiples of a range and therefore only mis-scaled.
  ⚠ **What that comparison EXCLUDES:** it rules out the reading that a level error is *only* a
  drawback here. A reconstruction error displaces `PDH`/`PDL` and the sweep extreme **together and in
  the same direction** on the same tape, so the trigger and the stop move as one and much of the
  error cancels inside the rule. The shape excluded is "C8's structural stop is strictly more
  vendor-fragile"; what is actually claimed is narrower — **the residual, non-cancelling part of the
  error lands on the stop rather than only on the cost**, and this screen cannot measure how large
  that residual is without a second feed.
- **One instrument, one vendor, one 730-day era.** The project's own diagnosis truth-harness says a
  single feed is **INDETERMINATE — and that binds a NULL exactly as it binds a survivor.**
- **PREREG clauses rot when nothing enforces them** (PREREG-C6 §7.3/§8 were promised and never
  implemented, disclosed in F157). Every clause here that produces a number is fired by
  `bin/factory_c8_train_screen.py` and lands in the verdict artifact, or it is absent and the
  artifact says which.
