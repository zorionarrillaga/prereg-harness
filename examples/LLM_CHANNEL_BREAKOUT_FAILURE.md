# A generated strategy that ran correctly and could barely trade

This is a real failure from an earlier LLM-to-strategy pipeline. The model proposed a multi-day
Donchian breakout with an ATR filter. Its response passed JSON-schema validation, an AST allow-list,
class loading, and a runtime check over 100 synthetic bars. It then compiled and reached the
backtest without raising an exception.

The first evaluation produced zero trades.

## Bug 1: the comparison included the current bar

The generated rule had the following shape:

```python
highs.append(current_bar.high)
max_high = max(highs)

if current_bar.close > max_high + buffer:
    enter_long()
```

For an ordinary OHLC bar:

```text
close <= current high <= maximum high including the current bar
```

Therefore `close > max_high + buffer` is unreachable for every non-negative buffer. The strategy
should have compared the close with the channel formed from prior bars:

```python
prior_high = max(highs[:-1])
if current_bar.close > prior_high + buffer:
    enter_long()
```

The short side had the symmetric error.

## Bug 2: the buffer used the complete channel width

After the first repair, the rule still produced zero trades. The generated buffer was:

```python
buffer = (prior_high - prior_low) * width_multiplier
# width_multiplier was sampled from 1.0 to 3.0
```

The long trigger therefore required the close to exceed the channel high by one to three complete
channel ranges. That was syntactically valid and theoretically possible, but inconsistent with the
stated aim of filtering small breaks. The repaired interpretation used ATR units:

```python
buffer = average_true_range * width_multiplier
```

## What the original validator proved

It established that the response had the expected fields, used permitted syntax, defined the
required class, executed without an exception, and returned correctly shaped intents when it
returned anything. Those are useful checks. They did not establish reachability or correspondence
between prose and code.

## Checks added to the research discipline

For every generated rule:

1. Construct a minimal path that must trigger each entry and exit branch.
2. Assert reachability before looking at market outcomes.
3. Print trigger counts before profitability statistics.
4. Treat zero or implausibly low frequency as a specification failure first.
5. Compare code with a plain-language truth table or a small reference implementation.
6. Keep the proposer outside the evaluator and prevent it from changing gates after seeing results.

The lesson is broader than channel breakouts: a model can generate code that runs and still encode
a different, degenerate, or impossible strategy. Runtime success is only the beginning of
verification.
