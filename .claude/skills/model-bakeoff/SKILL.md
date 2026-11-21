---
name: model-bakeoff
description: Run the OpenRouter provider comparison for gpt-oss-120b, plus a free Groq baseline, and write results to results/. Spends credits, so only the owner starts this.
disable-model-invocation: true
---

Run the model bake-off described in docs/SPEC.md.

1. Confirm `OPENROUTER_API_KEY` is set, and `GROQ_API_KEY` for the baseline,
   without printing either. Confirm the comparison list with the owner. It is
   the OpenRouter providers serving gpt-oss-120b, plus one free Groq run.
2. Estimate token use from the run count and the latest tokens-per-run
   figure, and show it before starting.
3. Run `make bakeoff`. Runs go one at a time with the arXiv delay in place.
4. Write raw per-run results to `results/bakeoff-<date>.csv` with provider,
   model, question, tool call success, tools used, citation check result, prompt
   and completion tokens, cached tokens if reported, and latency.
5. Generate the summary table from that file and show it. Note whether
   cached tokens appear in the usage data.
6. Recommend a pinned provider and one fallback, with the numbers. The owner
   decides and records it in docs/DECISIONS.md.
