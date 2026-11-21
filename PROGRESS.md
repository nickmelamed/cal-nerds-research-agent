# Progress

Current phase and what is left. Claude updates this at the end of each
phase. CLAUDE.md stays stable and does not track status.

## Now

- [ ] Phase 3. Model bake-off (gpt-oss-120b, gpt-oss-20b, qwen3.8-27b),
      including tokens per run and whether cached tokens count toward TPM.
      The scripts are built (`bakeoff/run.py`, `bakeoff/summarize.py`).
      Nick runs `python -m bakeoff.run --pilot`, then the full run, then
      `python -m bakeoff.summarize results/bakeoff-<date>.csv`. Prices need
      checking before cost numbers go in docs.

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
- [ ] Usage fields from the real Groq SDK: `prompt_tokens`,
      `completion_tokens`, `prompt_tokens_details.cached_tokens`, and
      `completion_tokens_details.reasoning_tokens`. The tracer reads them with
      defaults of 0, so a missing field reads as 0 cached tokens
- [ ] Cached tokens and TPM: send the same large prompt twice and compare
      `x-ratelimit-remaining-tokens` after each call
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

## Phase 3 handoff notes

Starting point for planning the bake-off in a separate conversation. The
approach below is a proposal, not an agreed plan. Read "Model selection" and
"Groq setup and capacity" in docs/SPEC.md first.

What phase 2 leaves in place.

- `core/agent.py`: `run_agent(client, question, system_prompt, tool_schemas,
  max_steps, tracer, model)` returns an `AgentResult` (`answer`, `steps`,
  `tracer`). `model` is a parameter, so the bake-off can loop over model ids
  without editing core. The default is `MODEL = "openai/gpt-oss-120b"`.
- `core/tracer.py`: `Tracer(verbose=False)` is quiet. `summary()` gives model
  calls, tool calls, total tokens, and seconds. It records `total_tokens`
  only, so prompt, completion, and cached tokens are not split out yet.
- `core/citations.py`: `check_citations(answer, tracer.tool_results)` returns
  verified and unverified lists and a summary line. Pass rate is the share of
  runs with no unverified citation and at least one verified one, which needs
  a definition before the first run.
- `core/schemas.py`: `TOOLS` is what the model sees.
- `bakeoff/` holds only `__init__.py`, and `make bakeoff` runs
  `python -m bakeoff.run`, which does not exist yet. `results/` is empty.

What the spec asks the bake-off to record, per model (gpt-oss-120b,
gpt-oss-20b, qwen/qwen3.8-27b), over about 20 runs of the demo question and
of each guided exercise question.

- Tool call success rate (valid JSON, real tool names).
- Whether it uses more than one tool when it should.
- Citation check pass rate.
- Tokens per run after trimming, against the 6 to 8k target.
- Latency per run.

It also has to settle two things from the spec: whether gpt-oss-20b is
reliable enough to be the second student pool (the top priority), and
whether cached tokens count toward TPM on Groq. Confirm current per-token
prices at the same time.

Constraints that shape the design.

- Rule 5: every arXiv request waits at least 3 seconds after the last one,
  including here. The tool code already enforces it. A full live bake-off is
  roughly 3 models times 20 runs times several questions times 2 to 4 arXiv
  searches per run, so it takes a long time and puts real load on arXiv.
- Rule 9: every number in docs comes from a file in `results/`. Scripts write
  raw CSV or JSON there and summaries are computed from those files.
- `results/*` and `fixtures/*` are protected paths. Writing results from the
  scripts, and any new fixture recording, needs Nick's approval first.
- The bake-off spends Groq credits and Nick runs it. Never load-test Groq
  from a script, so runs go one after another, with the 429 retry in
  `core/client.py` as the only concurrency handling.

Decisions to make when planning.

- Live tools or fixtures. Live arXiv is slow and rate limited. `OFFLINE` mode
  is fast, but the model chooses its own queries, so any query not in
  `fixtures/manifest.json` returns a failure message and skews tool success.
  Options are live arXiv with fewer runs, recording the exact guided and demo
  questions into fixtures first, or a mix. Recording goes through the
  refresh-fixtures skill, which only Nick starts.
- The guided exercise questions are not chosen yet, so the 20 runs per
  exercise have no question list. Exercise 3 (broken tool descriptions) is
  also phase 6 work and should not be folded in here.
- The recorded "protein structure prediction deep learning" search ranks an
  unrelated paper first. Decide the demo question wording from the bake-off
  numbers, not before.
- Whether the tracer should record prompt, completion, and cached tokens
  separately. The cached-token question needs them, so this is likely a small
  change to `core/tracer.py` and `core/agent.py` with tests.
- Whether gpt-oss models spend tokens on reasoning that counts toward the
  6 to 8k target. Check the response `usage` fields on the real SDK.
- A pass bar for gpt-oss-20b, written down before the runs so the result is
  not argued after the fact.

Suggested shape, to react to rather than follow.

- `bakeoff/questions.py` with the question list, `bakeoff/run.py` that loops
  models and questions, runs `run_agent` with a quiet tracer, and appends one
  raw row per run to `results/` (model, question, steps, tool names used,
  tokens, seconds, verified and unverified counts, any error).
- `bakeoff/summarize.py` that computes the table from the raw rows.
- A short plan for how many runs to do first as a pilot (a handful per model)
  before the full 20, so a broken script does not burn credits.
- Fast tests for the scripts with a mocked client, in `tests/`.

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
