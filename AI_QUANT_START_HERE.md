# Using this harness with an AI strategy proposer

An AI model can propose hypotheses, rules and code quickly. It should not grade its own work.
This repository supplies an independent falsification path for the second job.

The practical loop is:

1. The model writes a complete strategy specification, including the negative result that would
   change its mind.
2. Freeze that specification before inspecting an outcome.
3. Reject impossible rate, cost and power geometry before running a backtest.
4. Prove that the measurement apparatus detects a planted effect and returns null when no effect
   exists.
5. Run the strategy through the same walker, cost model and interval form used for its controls.
6. Compare its entries with matched placebo entries and simple baselines.
7. Spend validation and holdout data only according to the frozen decision rule.
8. Record the result, including the achieved minimum detectable effect.

This loop can reject a strategy. It cannot establish that future returns or live execution will
match a historical simulation.

## Ten-minute orientation

No third-party Python packages are required.

```bash
# 1. Confirm that the synthetic null really is null and the planted effect has its declared size.
python3 bin/factory_synthetic.py verify

# 2. See whether the scorer can detect an effect and refuse an under-powered conclusion.
python3 bin/factory_notblind.py gate --days 12 --seed 7

# 3. Inspect the invariants of the no-look-ahead walker and placebo scorer.
python3 bin/factory_backtest.py selftest
python3 bin/factory_scorer.py selftest

# 4. Check whether the economic target is plausible before searching for it.
python3 bin/factory_target_arithmetic.py

# 5. Verify the append-only experiment registry.
python3 bin/factory_registry.py verify
python3 bin/factory_registry.py count
```

The twelve-day not-blind demonstration is intentionally small. If it cannot support a conclusion,
it prints `INSUFFICIENT POWER` and the achieved MDE. The powered default is deliberately much
slower:

```bash
python3 bin/factory_notblind.py gate
```

## Give the model a specification job first

Copy [`examples/AI_STRATEGY_SPEC_TEMPLATE.md`](examples/AI_STRATEGY_SPEC_TEMPLATE.md) and ask the
model to complete every field. A useful prompt is:

> Propose one falsifiable trading rule using only information available at the decision time.
> Complete every field in the supplied specification. State the economic mechanism, exact entry
> and exit rules, costs, expected signal frequency, parameter grid, simple baselines, invalidation
> test, and minimum useful effect. Do not report expected profitability and do not alter the
> verification procedure.

Review the proposal as a specification, not as a persuasive explanation. In particular:

- Is every input available at the timestamp where the decision is made?
- Can the trigger actually become true?
- Is every parameter fixed or declared as a complete grid?
- Do stops, targets and costs use compatible units?
- Does the expected signal count give the test enough power?
- Which simple baseline would produce the same exposure?
- What result kills the idea?

Then freeze the file in the registry:

```bash
python3 bin/design_shape_check.py research/factory/PREREG_MY_STRATEGY.md
python3 bin/factory_registry.py register \
  --file research/factory/PREREG_MY_STRATEGY.md \
  --kind prereg \
  --name my-strategy-v1
git add research/factory/PREREG_MY_STRATEGY.md research/factory/registry.jsonl
git commit -m "Preregister my-strategy-v1"
```

The commit is part of the method: it makes later changes visible. Registration alone does not
make an arbitrary parameter defensible, so sweep every declared free parameter and report the
whole grid or its predeclared summary rather than its maximum.

## Keep model code outside the verifier boundary

An AST allow-list or a successful run over synthetic bars is not a secure sandbox, and it does
not prove that the strategy means what its prose says. Prefer a constrained JSON or small rule
DSL that your own adapter interprets. If the model emits executable code, run it in a separate
process or container without credentials, network access or private data.

Before evaluating returns, construct bars that should reach each branch and assert that the
expected intent is emitted. The worked
[`LLM_CHANNEL_BREAKOUT_FAILURE.md`](examples/LLM_CHANNEL_BREAKOUT_FAILURE.md) shows why: the first
generated strategy ran without exceptions yet contained two independent conditions that made its
entries nearly unreachable.

The sanitized [`nexus_llm_extract`](examples/nexus_llm_extract/) contains the actual historical
strategy source, its proposal manifest, and the schema that tied evaluated results to the exact
strategy, execution, fill, exit and risk-model versions. The strategy file is the final
human-patched artifact; its header preserves both original defects and their repairs.

## What to report

For every candidate, retain:

- the frozen strategy and every tried parameter cell;
- exact data eras and an untouched holdout identifier;
- strategy, execution, fill, exit, risk and cost-model versions or hashes;
- number of previous trials;
- trade count, achieved MDE, confidence interval and the predeclared MUE;
- matched-placebo and simple-baseline results;
- every excluded row and the exclusion reason;
- whether the result is simulation-only, paper-confirmed or live-confirmed.

Use precise conclusions: `no effect above X detected at this power`, `survived validation`, or
`failed holdout`. A backtest does not establish deployability, live parity or profitability.
