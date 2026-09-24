# Sanitized Nexus LLM pipeline extract

These are actual artifacts from the earlier Nexus/FORGE3 strategy-generation pipeline. They are
included to substantiate the worked failure case and make the useful provenance mechanism
inspectable.

## Files

- [`MD_ChannelBreakout_V1.py`](MD_ChannelBreakout_V1.py) is the final human-patched strategy
  source. Its header preserves the original LLM defects: the channel included the current bar,
  and the breakout buffer multiplied the complete channel range. Both made entries effectively
  unreachable.
- [`MD_ChannelBreakout_V1.manifest.json`](MD_ChannelBreakout_V1.manifest.json) is the proposal
  manifest carried by the old registry.
- [`spec_v3.py`](spec_v3.py) is the provenance schema used by the evaluator. It binds each result
  to strategy, execution, fill, exit and risk-model identifiers and hashes, records simulation
  parity status and source lineage, and carries the number of trials that produced the spec.

The strategy module is a historical component, not a standalone trading program. The original
compiler injected `_BaseStrategy` and `Intent`; those execution-system dependencies are
deliberately absent here. The file is useful as inspectable generated code and as a semantic
failure case.

The old proposer executed model-generated Python after an AST allow-list and a short synthetic
runtime check. That executor is not included because an AST allow-list is not a secure sandbox,
and its runtime probe was precisely what failed to catch the two semantic defects documented
here. For a new implementation, use a constrained declarative strategy format or isolate model
code in a separate process or container without credentials, network access or private data.

None of these files establishes an edge or live profitability.
