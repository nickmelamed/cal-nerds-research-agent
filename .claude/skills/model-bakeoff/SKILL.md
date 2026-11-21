---
name: model-bakeoff
description: Run the Groq model comparison and write results to results/. Spends Groq credits, so only the owner starts this.
disable-model-invocation: true
---

Run the model bake-off described in docs/SPEC.md.

1. Confirm `GROQ_API_KEY` is set without printing it, and confirm the model
   list with the owner (default gpt-oss-120b, gpt-oss-20b, qwen3.8-27b).
2. Estimate token use from the run count and the latest tokens-per-run
   figure, and show it before starting.
3. Run `make bakeoff`. Runs go one at a time with the arXiv delay in place.
4. Write raw per-run results to `results/bakeoff-<date>.csv` with model,
   question, tool call success, tools used, citation check result, prompt
   and completion tokens, cached tokens if reported, and latency.
5. Generate the summary table from that file and show it. Note whether
   cached tokens appear in the usage data.
6. Recommend a demo model and a second student pool, with the numbers. The
   owner decides and records it in docs/DECISIONS.md.
