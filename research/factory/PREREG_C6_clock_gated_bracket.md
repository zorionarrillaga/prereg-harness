---
id: PREREG-C6-CLOCK-GATED-BRACKET
type: prereg
created: 2026-08-13
status: frozen
title: "C6 clock-gated bracket — the first candidate built to F115's k=1 target and F118's payoff prescription, frozen before any outcome exists"
related: [F115, F117, F118, F125, F122, F096, F104, F108, L025, L026, D048, D053, D055]
---

# PREREG — C6, THE CLOCK-GATED BRACKET

> **Frozen BEFORE any outcome is evaluated.** Charter R2 FOLD-4: exact specs pre-registered in a
> commit and counted in the multiplicity registry. **The geometry pre-screen has run and its
> numbers are in §6 — that is the required order of work, and geometry
> evaluates no outcome so it leaks nothing. No expectancy, hit rate, or R exists for this rule.**

## 1. THE QUESTION

Every dead candidate so far was **selective by design**, which made its own holdout test a
formality with a pre-known answer (F050's shape, restated by F115). C6 asks the opposite question:

> **Does a rule that fires on the CLOCK — once per day, every day, with an explicit stop and an
> explicit target — carry an edge our judge can see?**

It is the first candidate built to F115's measured design target (**k=1, ~5 signals/week over the
whole holdout era, 2.07× the MUE at 80% power**) rather than to a selectivity intuition, and the
first built to F118's prescription (**an explicit stop and target, screened on expectancy at a
declared R:R, never a hit rate**).

## 2. ⛔ SCOPE — WHAT THIS SCREEN CAN AND CANNOT DO

- **One instrument, one vendor.** USATECHIDXUSD (US100), Dukascopy BID CFD 1-minute candles.
  **This is not a free choice: `factory_backtest.cost_in_r` refuses every other instrument**,
  because `cost_model.json` was measured on US100.cash only and points are not portable across
  instruments. ⇒ The candidate is therefore single-instrument and must clear the ≥2 signals/week
  floor on its own legs, which **excludes** the portfolio-wide reading D055 ratified — the weaker
  reading is available to C6 and C6 declines it. *(What declining it gives up: a multi-instrument
  version of this same rule would very likely clear both bars more easily, and we will not learn
  whether the effect is instrument-specific. That is the cost of the only honestly-costed path.)*
- **It cannot close the session-structure family.** F051 binds: DEAD means *not detectable at this
  power in this budget*.
- **It is not a test of Gao et al. (2018).** The side signal is theirs; the frame, instrument,
  clock, bracket and era are ours. A kill here is not a refutation of the paper, and a survival
  here is not a confirmation of it.
- **It does not test the entry-price mechanism** (limit-into-pullback), which the structure sweep
  named as the component with the most direct claim on our measured 25.6s latency (F125 §4.5).
  ⇒ C6 enters at market on a clock bar, so it **forgoes** the whole refuse-to-chase family; that
  family is untested by this prereg and may not be reported as dead by it.

## 3. THE SPEC — frozen here, no addition after registration

| | |
|---|---|
| **Instrument** | `USATECHIDXUSD` (US100), RTH 09:30–16:00 ET, vendor 1-minute candles |
| **Eligibility** | Every RTH day whose tape carries at least one bar before the clock and one after it. **No price condition, no filter.** Measured: 648 of 673 day-files in the holdout era, 0 rejected by any rule of ours |
| **Side** | `r1 = close(10:00 ET) − close(prior RTH final bar)`. **LONG** if `r1 > 0`, **SHORT** otherwise. Gao/Han/Li/Zhou, *Market Intraday Momentum*, JFE 2018 — first-half-hour return predicts the last-half-hour return (catalogue Form D) |
| **Entry** | At the **close of the 1-minute bar at the clock**, at market. Clock ∈ **{14:30, 15:00, 15:30} ET** (swept) |
| **Stop** | `S = k × (RTH high − RTH low, 09:30 → clock)`, k ∈ **{0.15, 0.25, 0.35}** (swept). **Relative, never points** — US100 runs 2,400→24,000 across the corpus and a point-declared stop is a different rule at each end |
| **Target** | `T = rr × S`, rr ∈ **{1.5, 2.0, 3.0}** (swept) |
| **Exit** | First of: stop · target · **hard flat at 15:58 ET**. Form F's double time-stop; also our own bell discipline |
| **Cost** | `cost_model.json`, charged **both** bands: central 1.20pt and adverse p90 26.71pt |

**Controls, with the IDENTICAL bracket** (F117's controls are what made its kill credible):
**K1** always LONG · **K2** always SHORT · **K3** alternating by day index. The signal must beat
the best control by more than the achieved MDE, or it has found drift and geometry, not signal.

## 4. THE GRID, DECLARED IN FULL

**3 clocks × 3 stop multiples × 3 payoff ratios = 27 cells**, plus **3 controls × 27 = 81**.
**Total 108 cells.** All of them are run; none is dropped after the fact.

L025 binds: a pre-registered free parameter is still a free parameter. All three swept parameters
were chosen by us, so **the primary is the MEDIAN cell of the 27, never the argmax**. The argmax is
reported alongside it, labelled as not used.

## 5. THE METRIC AND THE PRIMARY

**Mean net R per trade** (expectancy), day-clustered bootstrap, 2000 resamples, days drawn whole.
**Never a hit rate** — F118: a hit rate quoted without its R:R is not a number, and the breakeven
accuracy this rule must beat is 46.0% at 1.5:1 and 28.8% at 3:1, not 57.5%.

**Primary statistic:** the median cell's mean net R, on the **train era 2012-01-01 → 2023-12-31**.
The holdout (2024-01-01 → 2026-08-11) is **not touched by this prereg** and is not touched at all
until the operator starts the Phase-2 clock (D055: on-demand, `phase2_start` is null).

⚠ **THE TRAIN ERA OVERCHARGES COST AND THE SCREEN MUST CARRY IT.** `costs()` is a constant 1.20pt
measured in 2026 at ~24,000 (≈0.5bp); the train era's median US100 price is **6,556**, where the
same constant is ≈1.8bp — a **3.4× relative overcharge, in the killing direction**. So expectancy
is computed **twice**: once at the frozen point cost, once at a price-proportional cost
(0.5bp × price at entry). ⇒ A train kill counts **only if it holds under both**, which **excludes**
the cheap reading that a train death is automatically a death — an overcharged screen manufactures
false deaths, and that is the F115 laundering shape moved from power into cost.

## 6. THE PRE-SCREEN, ALREADY RUN — geometry only, no outcome

`python3 bin/factory_prescreen.py --c6` (era 2024-01-01…2026-08-11, the era whose price level the
cost model was measured at). Full grid: `research/factory/prescreen_c6.json`.

| gate | result | verdict |
|---|---|---|
| **RATE** | 648 signals / 648 day-files = **5.00/week** | clears the ≥2/wk floor — **but see the warning below** |
| **COST, central** | median cell E[cost_r] = **0.0206R = 14% of the MUE** (grid 10–24%) | clears the 33% gate |
| **COST, adverse p90** | median cell **0.4588R = 306% of the MUE** | **FAILS** |
| **POWER** | n = 648, σ_R = √rr (derived), MDE = **+0.285R / +0.306R / +0.341R** at 1.5/2/3:1 | clears the 0.60 gate; 1.9–2.3× the MUE, matching F115's 2.07× |

⚠ **THE RATE GATE IS UNINFORMATIVE HERE AND MUST NOT BE QUOTED AS A PASS.** It exists to catch a
price-triggered rule whose author quoted a *cap* as a *rate* (F050, which killed C1 and C3). A
clock rule fires by construction, so it **cannot** fail this gate. 5.00/week is a restatement of
the spec, not evidence about the market. ⇒ The gate that actually has teeth for this family is
POWER, and it **excludes** nothing here — which is precisely why the branch table below must be
the thing that kills, rather than the pre-screen.

⚠⚠ **COST-VIABLE ON THE CENTRAL BAND ONLY.** The adverse p90 (26.71pt, n=42 discretionary fills,
F127/F128) is 3.1× the MUE against this stop. `cost_model.json` says of its own central figure
that it is *"a MEDIAN-based CONVENTION, not a measurement"*. The honest statement is that C6 is a
pass at 1.20pt and a fail at 26.71pt, and that the adverse figure bounds **our current
discretionary execution**, not execution in principle — this rule fires at a minute known in
advance, the one shape a resting order can be staged for. That is an argument for **re-measuring
the tail on staged orders**, never for quoting only the friendlier band.

## 7. THE BRANCH TABLE — pre-committed, so the result cannot be re-interpreted after it lands

1. **Median cell's expectancy CI upper bound < 0 under BOTH cost treatments** ⇒ C6 is DEAD on
   train, published as *"nothing above X"*, no holdout spent, and **no fourth parameter is invented
   to rescue it**. This **excludes** the repair move that killed the C-series' credibility before:
   adding a filter after seeing the grid.
2. **Median cell does not beat the best of K1/K2/K3 by more than the achieved MDE** ⇒ DEAD. The
   answer is then *drift and geometry*, and the screen says so out loud rather than reporting the
   best feature (F117's own §7 scenario, fired as written).
3. **The grid is flat and only isolated cells win** (per-cell sd small relative to the spread of
   cell means) ⇒ DEAD as noise-over-cells. The flatness check is run and reported either way.
4. **Median cell clears +0.15R net AND beats every control by more than the MDE, under both cost
   treatments** ⇒ C6 is **holdout-eligible**. A verdict row is registered and **the operator is told**.
   ⇒ This **excludes** any path where the harness starts the Phase-2 clock: D055 makes it on-demand and
   his alone, and eligibility spends no budget.
5. **Clears on central cost but not on the adverse band** ⇒ **NOT holdout-eligible**, and the owed
   work is a re-measurement of the execution tail on *staged* orders, not a re-run of the rule.

## 8. WHAT WOULD MAKE THIS SCREEN ITSELF WRONG

- **σ_R = √rr is an upper bound under a two-point payoff.** A gap *through* the stop, or a target
  that slips, puts realised outcomes outside {−1, +rr} and raises σ above it — the MDE would then
  be optimistic. It is checked after the fact against the realised dispersion, and the check is
  reported whichever way it lands.
- **The side signal spans the overnight gap**, and F096 lists gap statistics as a KILLED family.
  `r1` is *prior close → 10:00*, i.e. gap **plus** the first 30 RTH minutes; F117's S2 was the gap
  alone and reached 50.90%. The adjacency is declared here **in advance**: if the signal wins, that
  adjacency must be argued explicitly before any spec is written, exactly as C5's prereg required.
- **The vendor is not our broker.** Basis −2.45pt, level reconstruction error 1.52/3.56/2.52pt
  (GL-42). Against a 64pt median stop that is ~2–6% of R, which is smaller than the cost band gap
  but is not zero.
- **No latency test.** F125 records that one bar of delay inverted Mesfin's London-B control
  (T +5.15 → −3.56). C6 enters at a clock bar close and our loop floor is ~110s, so the entry is
  physically ~2 bars late unless the order is staged in advance. **A latency ladder (entry delayed
  0/1/2/5 minutes) is run as part of the screen and reported**, because a rule that dies at
  +2 minutes is not operable by us regardless of its expectancy at 0.
- **Multiplicity.** This is registry row 40 and the denominator rises with it. 108 cells collapse
  to ONE primary by the median rule, which is what keeps the denominator at one candidate.
