# Bake-off results

Raw per-run CSVs from `python -m bakeoff.run`. One row is one agent run on one
question through one provider, always with gpt-oss-120b. Summaries come from
`python -m bakeoff.summarize <file>`. The columns and the selection rule are
in `bakeoff/run.py` and `bakeoff/PASS_BAR.md`.

The files were recorded at different points in the work, so the agent loop
and the columns differ between them. Older files lack some columns, such as
`tool_sequence`, `answer`, `served_by`, and `cost_usd`.

## Files the docs cite

| File | Runs | Setup | Used for |
|---|---|---|---|
| `bakeoff-six-steps.csv` | 40 | `openrouter:auto`, 6 step cap, forced last step | Tokens per run and citation pass rate in D-009 |
| `bakeoff-cost-sample.csv` | 20 | `openrouter:auto`, 6 step cap | Cost per run in docs/SPEC.md |
| `bakeoff-groq-four.csv` | 12 | free Groq key, 6 step cap | Groq fallback check |
| `bakeoff-final-loop.csv` | 40 | `openrouter:auto`, 8 step cap, forced last step | Tokens before the cap was lowered, in D-009 |
| `bakeoff-main.csv` | 120 | two OpenRouter routes, 8 step cap, tools always on | Capped runs after the prompt change, in D-009 |
| `bakeoff-2026-11-21.csv` | 75 | four OpenRouter routes and a free Groq key, 8 step cap | First pilot, in D-009 |

## Diagnostic and small checks

| File | Runs | What it checked |
|---|---|---|
| `bakeoff-diagnose.csv` | 10 | Why runs hit the step cap. First file with `tool_sequence` |
| `bakeoff-diagnose2.csv` | 10 | Effect of the search limit in the prompt |
| `bakeoff-diagnose3.csv` | 15 | The original demo question against two open-ended ones. First file with answers |
| `bakeoff-groq-baseline.csv` | 6 | First clean free Groq key check |
| `bakeoff-cost-check.csv` | 2 | That `cost_usd` fills in |

## Reading the columns

`served_by` lists the upstream providers OpenRouter named for the run's calls.
One run can list several. `cost_usd` is the cost OpenRouter reports and is
blank for Groq. `ended_early` is true when a run raised, hit the step cap, or
returned an empty answer. `citation_pass` is true when the answer has at
least one verified citation and no unverified one.
