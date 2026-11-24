# Progress

Current phase and what is left. Claude updates this at the end of each
phase. CLAUDE.md stays stable and does not track status.

## Now

Phase 7 is written on branch `phase-7-readme`. The README has the Open in
Colab links and a section on reproducing the notebooks later. The links
resolve only once this is on `main`, so they are still on the Colab checklist.

## Next

- [ ] Colab dry runs and load check from the checklist below

## Colab checklist (Nick, by hand)

- [ ] Demo notebook in a fresh runtime: the `!pip install` cell, the smoke test
      text, OFFLINE mode, and the Open in Colab badge
- [ ] Each notebook runs with Run all in a fresh runtime on a fresh Google
      account, once with the workshop key and once with a free key
- [ ] Colab Secrets and the `getpass` fallback both work (`get_api_key` in
      `core/client.py`)
- [ ] 429 retry message, the OpenRouter credit helper, and the Groq
      remaining-tokens helper against the real OpenAI SDK on both providers
- [ ] Usage fields from the real OpenAI SDK on both providers: `prompt_tokens`,
      `completion_tokens`, `prompt_tokens_details.cached_tokens`, and
      `completion_tokens_details.reasoning_tokens`. Missing fields read as 0
- [ ] `run_agent` against the real OpenAI SDK on both providers. Check the
      `tool_use_failed` error text and that `usage.total_tokens` is set
- [ ] OpenRouter `GET /api/v1/key` returns `data.limit_remaining` for a key
      with a credit limit, and `extra_body` provider routing (`order`,
      `allow_fallbacks`) pins the upstream provider
- [ ] Form cells render collapsed
- [ ] Full-code starter runs with Run all in a fresh runtime, the hint
      `<details>` blocks render, and the task 2 and 3 test cells print
      "Not yet" on the untouched starter, with Wi-Fi off for task 2
- [x] Guided notebook runs with Run all in a fresh runtime, form cells render
      collapsed, and `compare` finishes well inside the exercise 1 time
- [x] Guided notebook with `OFFLINE = True` on the three exercise 2 questions
- [ ] Open in Colab links open the right notebooks
- [ ] Guided and full-code tracks each fit the 45 minute build block
- [ ] A handful of simultaneous sessions on the workshop key, watching the
      remaining OpenRouter credit

## Workshop logistics (Nick)

- [ ] Save a copy of the demo notebook with outputs from a good live run
- [ ] Dedicated OpenRouter workshop key with a credit limit
- [ ] Links in slides, pre-workshop email (own key optional), and wrap-up
      slide (how to get a free key)
- [ ] Revoke the workshop key after the workshop

## Done

- [x] Phase 1. Core tools (`search_arxiv`, `get_abstract`, `lookup_wikipedia`)
      with fixtures, fast tests, and live tests (PR #1)
- [x] Phase 1. Client wrapper with 429 handling and rate limit header reader
      (PR #1). Now covers both OpenRouter and Groq, see D-008
- [x] Phase 2. Tool schemas, agent loop, tracer, and citation check, with
      mocked-Groq tests (PR #3)
- [x] Phase 3. Bake-off (PR #6). Results: `results/bakeoff-six-steps.csv`
      (tokens and citations), `results/bakeoff-groq-baseline.csv` (free Groq
      key), `results/bakeoff-cost-sample.csv` (cost, now in docs/SPEC.md)
- [x] Phase 4. `build.py`, the demo notebook, and OFFLINE mode, see D-010
      (PR #7)
- [x] Phase 5. Full-code starter notebook and its tests, see D-011
- [x] Phase 6. Guided notebook, exercise 3 wording tests in
      `results/bakeoff-ex3*.csv`, see D-012
- [x] Phase 7. README with Open in Colab links and a section on reproducing
      the notebooks after the workshop

## Phase 4 notes from the bake-off

- Use `MAX_STEPS = 6` and the forced last step from `core/agent.py`. Without
  them, runs averaged more than 8k tokens (`results/bakeoff-final-loop.csv`).
- Start from the system prompt in `bakeoff/questions.py`. The search limit
  and the "no years in a query" line are what stopped the search loops.
- The demo candidates are `demo_open` and `backup_weather`. The original
  named-systems question (AlphaFold, RoseTTAFold) never finished in
  `results/bakeoff-diagnose3.csv`, because those papers are not on arXiv.
- The citation check passes an answer whose claims come from the model's own
  knowledge, as long as the cited ids were retrieved. Say so in the demo
  script.

## Phase 5 notes from the bake-off

- The full-code starter keeps its own bare loop. It must not get the forced
  last step, the empty-reply retry, or the `extra_body` argument, since the
  step cap and error handling are student tasks.

## Phase 3 handoff notes

Starting point for planning the bake-off in a separate conversation. The
approach below is a proposal, not an agreed plan. Read "Model selection" and
"Providers and capacity" in docs/SPEC.md first. These handoff notes
predate D-008 and describe the old Groq model comparison.

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
