# Progress

Current phase and what is left. Claude updates this at the end of each
phase. CLAUDE.md stays stable and does not track status.

## Now

- [ ] Phase 3. Model bake-off (gpt-oss-120b, gpt-oss-20b, qwen3.8-27b),
      including tokens per run and whether cached tokens count toward TPM

## Next

- [ ] Phase 4. `build.py` and the demo notebook with OFFLINE mode
- [ ] Phase 5. Full-code starter
- [ ] Phase 6. Guided notebook and exercise 3 wording tests
- [ ] Phase 7. README with Open in Colab links

## Colab checklist (Nick, by hand)

- [ ] Each notebook runs with Run all in a fresh runtime on a fresh Google
      account, once with the workshop key and once with a free key
- [ ] Colab Secrets and the `getpass` fallback both work (`get_api_key` in
      `core/client.py`)
- [ ] 429 retry message and `remaining_tokens()` against the real Groq SDK
      headers
- [ ] `run_agent` against the real Groq SDK. Check the `tool_use_failed`
      error text and that `usage.total_tokens` is set
- [ ] Form cells render collapsed
- [ ] Open in Colab links open the right notebooks
- [ ] Guided and full-code tracks each fit the 45 minute build block
- [ ] A handful of simultaneous sessions on the workshop key, watching the
      remaining-tokens header

## Workshop logistics (Nick)

- [ ] Dedicated workshop key, spend limit around $50, budget alerts
- [ ] Links in slides, pre-workshop email (own key optional), and wrap-up
      slide (how to get a free key)
- [ ] Revoke the workshop key after the workshop

## Done

- [x] Phase 1. Core tools (`search_arxiv`, `get_abstract`, `lookup_wikipedia`)
      with fixtures, fast tests, and live tests (PR #1)
- [x] Phase 1. Client wrapper with 429 handling and rate limit header reader
      (PR #1)
- [x] Phase 2. Tool schemas, agent loop, tracer, and citation check, with
      mocked-Groq tests (PR #3)

## Phase 2 handoff notes

What phase 1 leaves for phase 2 to build on.

- `core/tools.py`: `search_arxiv` returns a list of dicts (`id`, `title`,
  `authors`, `date`, `link`) or a message string. `get_abstract` returns a
  dict (`id`, `title`, `abstract`) or a message string. `lookup_wikipedia`
  returns a dict (`title`, `summary`, `url`) or a message string. Call
  `reset_cache()` at the start of each agent run.
- Old-style arXiv ids keep their archive prefix (`cond-mat/9812291`), and ids
  are stored without a version suffix. The citation check has to match both
  forms.
- `core/client.py`: use `chat(client, **kwargs)` for every model call so the
  429 retry applies. `remaining_tokens()` reads the headers from the last
  response.
- The citation check must count a citation as verified only if a tool
  returned it in that run, so the tracer needs to keep raw tool results.
  `core/citations.py` is a protected path, so ask before creating it.
- The loop handles Groq `tool_use_failed` errors by feeding the error back to
  the model once, per docs/SPEC.md. Tests mock Groq and never call it.
- The step cap and token logging belong in the demo and guided loop. The
  full-code starter leaves them out on purpose.
- `fixtures/responses.json` only covers the queries in
  `fixtures/manifest.json`. Any new demo or guided question needs a new
  recording through the refresh-fixtures skill, which only Nick starts.
- The recorded arXiv search for "protein structure prediction deep learning"
  ranks an unrelated paper first. Check the demo question wording before
  committing to it, and measure it in the phase 3 bake-off.

## Outstanding from PR 1 review (optional, none applied)

- [ ] `search_arxiv` calls `int(max_results)`, which raises on a non-numeric
      string from the model. Return a message instead.
- [ ] Wikipedia requests are not retried on 429 or 5xx. The spec only asks
      for arXiv retries.
- [ ] `test_wikipedia_summary_is_short` uses a weak `count(". ") < 3`
      assertion. Tighten it.
- [ ] `.claude/gate-commands` still lists the two individual checks. Switch
      it to `make agent-check` once Nick approves, since the file is a
      protected path.
- [ ] `make agent-check` needs `.venv`, so run `make setup` in a fresh clone.

## Open questions for the owner
