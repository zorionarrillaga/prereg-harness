---
id: REPLACE-ME
status: draft
created: YYYY-MM-DD
generated_by: model-and-version
trial_number: 1
---

# Strategy specification

Freeze this document before inspecting an outcome. If the proposal changes, register a new version
and count it as another trial.

## 1. Falsifiable claim

- **Claim:**
- **Economic or behavioral mechanism:**
- **Evidence references:**
- **Result that would invalidate the claim:**

## 2. Decision boundary

- **Instrument and venue:**
- **Bar or event frequency:**
- **Trading session and timezone:**
- **Decision timestamp:**
- **Inputs available at that timestamp:**
- **Missing-data behavior:**

## 3. Exact rule

- **Eligibility:**
- **Long entry:**
- **Short entry:**
- **Position sizing:**
- **Stop:**
- **Target:**
- **Time exit:**
- **Overlapping-signal behavior:**

State explicitly why each entry condition is reachable. Give at least one constructed bar sequence
that should trigger it and one that should not.

## 4. Execution and costs

- **Order assumption:**
- **Fill model:**
- **Spread, commission, slippage and financing:**
- **Adverse cost sensitivity:**
- **Strategy implementation/version hash:**
- **Execution model/version hash:**
- **Fill model/version hash:**
- **Exit policy/version hash:**
- **Risk model/version hash:**

## 5. Search space

- **Complete parameter grid:**
- **Number of cells:**
- **Primary summary across cells:**
- **Number of earlier related trials:**

The maximum cell is descriptive only unless it was the frozen primary before outcomes existed.

## 6. Cheap prechecks

- **Expected signals per week:**
- **Expected holdout observations:**
- **Estimated dispersion in R:**
- **Achieved or projected MDE:**
- **Minimum useful effect, net of costs:**
- **Reason the planned test has enough power:**

## 7. Controls

- **Do-nothing baseline:**
- **Always-long/always-short or exposure-matched baseline:**
- **Matched-placebo construction:**
- **Known-null negative control:**
- **Planted-edge positive control:**

## 8. Data separation

- **Train era:**
- **Validation era:**
- **One-shot holdout era or immutable identifier:**
- **Permitted train-stage changes:**
- **Validation survival rule:**
- **Holdout survival rule:**
- **What happens after a failed holdout:**

## 9. Reporting contract

Report every tried cell, excluded observation, achieved MDE, net result, confidence interval,
baseline result and placebo result. Label the result as simulation-only until separately confirmed
against paper or live fills.
