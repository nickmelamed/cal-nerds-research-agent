# Bake-off definitions and pass bar

## Definitions

A run is one call to `run_agent` on one question with one model.

Tool-call success is the share of tool calls in a run that named a real
tool with valid JSON arguments the tool accepted. A run with no tool calls
counts as a failure for this measure.

Multi-tool use is the share of runs on questions marked
`needs_multiple_tools` that used at least two different tools.

Citation pass means the answer has no unverified citation and at least one
verified citation, as reported by `check_citations`.

An error run is one that raised, or ended at the step cap without an answer.

## Pass bar for gpt-oss-20b as the second student pool

All of these, measured over the same questions as gpt-oss-120b:

- tool-call success of at least 95%
- citation pass rate within 10 points of gpt-oss-120b
- mean tokens per run of 8,000 or fewer
- at most 1 in 10 runs ending as an error run

If it fails, qwen/qwen3.8-27b is evaluated against the same bar.
