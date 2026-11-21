# Bake-off definitions and selection rule

## Definitions

A run is one call to `run_agent` on one question through one provider, always
with gpt-oss-120b. A provider is an OpenRouter upstream provider pinned with
provider routing, `openrouter:auto` for OpenRouter's own choice, or
`groq-free` for the baseline on a student's free Groq key.

Tool-call success is the share of tool calls that named a real tool with
valid JSON arguments the tool accepted. A run with no tool calls counts as
one failed call.

Multi-tool use is the share of runs on questions marked
`needs_multiple_tools` that used at least two different tools.

Citation pass means the answer has no unverified citation and at least one
verified citation, as reported by `check_citations`.

An error run is one that raised, or ended at the step cap without an answer.

## Selection rule for the pinned OpenRouter provider

A provider is eligible when all of these hold:

- tool-call success of at least 95%
- mean tokens per run of 8,000 or fewer
- at most 1 in 10 runs ending as an error run
- citation pass rate within 10 points of the best OpenRouter provider
  measured

Among eligible OpenRouter providers the pinned one has the highest citation
pass rate, with lower mean latency breaking ties. The next one is the
fallback. `groq-free` is reported for comparison and is never pinned.

Price per run is TBD until OpenRouter pricing for the pinned provider is
confirmed. It does not decide eligibility.
