# Cal NERDS AI 101: Notebook Build Plan

Builds on docs/workshop-context.md, which covers the workshop schedule, the agent, and the two build tracks. Where the two differ, this document wins. Three notebooks for the Build an Agent segment, all in Colab, all built around the research paper assistant.

## Guiding decisions

**One source of truth.** The finished demo notebook is built first and everything else is derived from it. The tool functions, tool schemas, agent loop and trace printer live in one place (`core/`) and a small build script copies them into each notebook. Fixing a bug once fixes it everywhere.

**Every notebook is self-contained.** No `pip install` of our own package and no fetching code from GitHub at runtime. If a student opens the link, every cell they need is in the notebook. Only third-party install is `openai`.

**Plain HTTP for the tools.** arXiv via its Atom API with `requests` and `xml.etree`, Wikipedia via its REST summary endpoint. No `arxiv` or `wikipedia` packages, so the full-code track can read exactly what each tool does.

**OpenRouter workshop key by default, own Groq key optional.** Nick pays for an OpenRouter key used only for the workshop. The setup cell uses a student's own Groq key if `GROQ_API_KEY` is set in Colab Secrets, and otherwise the workshop key. Details under Providers and capacity below.

**Same setup cell in all three.** Key and provider selection as above, then a smoke-test call that prints a clear pass or fail. Keys never get pasted into a cell that gets shared, other than the workshop key, which is revoked after the workshop.

**Citation check in every notebook.** Runs automatically after each agent answer in the demo and guided notebooks. In the full-code starter it runs too, and writing an improved version is a stretch task.

## Providers and capacity

Build for about 60 students.

### Providers

The default is OpenRouter with a paid key Nick controls, set to gpt-oss-120b. The optional provider is Groq with a student's own free key. Both expose the OpenAI-compatible chat completions API, so notebooks use the `openai` package with a base URL setting.

Free Groq limits for gpt-oss-120b are 30 RPM, 1K RPD, 8K TPM and 200K TPD per account. A run can pause on 429s, which is acceptable for a fallback. These are the fallback numbers and come from Groq's docs.

OpenRouter does not enforce rate limits on paid models, but the upstream providers can throttle or go down. Pin gpt-oss-120b to the provider with the most reliable tool calling in the bake-off, with one fallback, using OpenRouter's provider routing settings.

### Keys and setup cell

`OPENROUTER_API_KEY` holds the workshop key. Nick adds it to student copies by hand. `GROQ_API_KEY` is a student's own key. If it is set in Colab Secrets the setup cell uses Groq, otherwise the workshop OpenRouter key. If neither works, it prompts with `getpass`. The smoke test prints which provider and model are in use.

429 handling stays in the client wrapper. It reads `retry-after` when present and backs off otherwise, since the providers send different headers. The remaining-tokens helper is Groq-only. For OpenRouter a helper calls `GET https://openrouter.ai/api/v1/key` so Nick can watch remaining credit.

### Token budget

Keep each run near 6 to 8k tokens. The reasons are cost, latency, and the 8K TPM of a free Groq key. Measured in the bake-off. Cuts: 3 search results instead of 5, abstracts truncated to about 150 words, short tool schemas, Wikipedia summaries cut to 2 or 3 sentences.

### Cost

TBD until the bake-off. Confirm gpt-oss-120b pricing on OpenRouter for the pinned provider. The estimate stays in the low single-digit dollars until real numbers exist.

### Key safety

- Create a dedicated OpenRouter key with a credit limit
- Revoke the key right after the workshop, since it will end up in shared copies of notebooks

### Student messaging

- Pre-workshop email says creating a free Groq key is optional and worth doing for anyone who wants to keep building after the workshop
- Wrap-up slide shows how to get a free key and swap it into the notebooks, since the workshop key stops working afterward

## arXiv and Wikipedia load

Calls come from Google's Colab machines, not the venue wifi, so most students won't share an IP. Some may, and arXiv can be slow at peak times, so the search tool always waits 3 seconds between calls, retries with backoff, and caches results within a session. If arXiv still fails, the tool returns a clear message and the agent can fall back to Wikipedia.

The `OFFLINE` flag ships in all three notebooks with cached results for the provided example questions, so anyone whose arXiv calls keep failing can still finish the exercises.

## Shared core (built first)

| Piece | What it does |
|---|---|
| `search_arxiv(query, max_results=3)` | Returns id, title, authors, date, link. 3 second delay plus retry with backoff on 429/503. Returns a friendly message on zero results instead of an empty list |
| `get_abstract(paper_id)` | Fetches by `id_list`, truncated to about 150 words. Reuses a per-run cache so it doesn't re-hit arXiv for papers the search already returned |
| `lookup_wikipedia(term)` | REST summary endpoint with a proper User-Agent. Falls back to Wikipedia search when the exact title misses. Truncates to 2 or 3 sentences |
| `TOOLS` schemas | Short JSON schemas with descriptions in their own cell so the guided track can edit text without touching code |
| `run_agent(question, system_prompt, tools, max_steps)` | The decide, call tool, read result, repeat loop. Handles Groq's `tool_use_failed` errors by feeding the error back to the model once before giving up. Handles 429s with `retry-after` when present |
| `Tracer` | Prints each step readably. Step number, the model's tool choice and arguments, a truncated result, final answer. Also collects tokens and latency per call |
| `check_citations(answer, trace)` | Pulls every arXiv ID or title out of the final answer and confirms each was actually returned by a tool during this run |

The citation check is the payoff for the hallucination demo earlier in the day. The demo ends with a line like "4 of 4 cited papers were retrieved by the agent in this run."

## Notebook 1. Finished demo (Nick runs live)

1. Setup and smoke test, pinned to gpt-oss-120b
2. Tools, collapsed into Colab form cells with a one-line summary each
3. Agent loop, visible, since this is what the slide diagram describes
4. Run the protein folding question with full trace
5. Citation check
6. Backup question in a second cell in case the first gets a weak answer
7. Optional cell for the chatbot comparison talking points (web search off vs. on)

Extras for robustness
- Keep a copy of the notebook with saved outputs from a good run. If the model provider or arXiv misbehaves live, switch tabs and narrate the saved trace.
- `OFFLINE = False` flag that swaps arXiv and Wikipedia calls for a small cached JSON of real results for the demo questions.
- Run the live demo before students start building, so the shared pool is empty.

This notebook also doubles as the answer key for the full-code track.

## Notebook 2. Guided track

Tool code is pre-written and collapsed. Students only edit text cells and plain-language strings. Each exercise has a "Your turn" cell and a "What to notice" note.

| # | Exercise | Est. min |
|---|---|---|
| 0 | Setup, then run the agent once on a provided question and read the trace together | 5 |
| 1 | System prompt. Run the same question with a plain-language prompt and a technical prompt, side by side via a `compare()` helper | 10 |
| 2 | Your field. Change the question to something in your own major or research area | 10 |
| 3 | Break a tool description. Make one description vague or misleading and watch the agent skip or misuse that tool | 12 |
| 4 | Stretch. Remove a tool entirely, or add a rule to the system prompt like "always define jargon with Wikipedia" | as time allows |
| End | Share-out cell that prints the question, number of steps, tools used, citation check result and the answer | 3 |

Exercise 3 needs testing. A vague description like "Gets information" may not reliably change behavior. A misleading one, such as describing `search_arxiv` as a dictionary lookup, usually does. Ship whichever wording reliably produces visible misbehavior on the chosen models, and offer both as suggestions. The citation check makes the damage visible here too, since a broken search tool tends to produce uncited or unverified answers.

`compare()` runs the two prompts one after the other rather than in parallel, to keep bursts against the shared pool smaller.

## Notebook 3. Full-code starter

Starts with a working loop and only `search_arxiv`. No error handling, no step cap, no logging, so those are real tasks. Tasks are ordered by priority so finishing two still gives a student something to share. The 429 retry lives in the setup cell's client wrapper rather than the loop, so students on the shared key are protected even before they finish task 2.

| # | Task | Checkpoint |
|---|---|---|
| 1 | Write a new tool, either `save_to_reading_list(paper_id, note)` or a date filter on search, plus its schema | Agent uses it unprompted on a suitable question |
| 2 | Error handling for empty results, network failures and bad tool arguments | Provided test cell passes (calls tools with an empty query, a bad ID, a forced timeout) |
| 3 | Cap loop iterations and return a graceful message at the cap | Test cell with `max_steps=1` returns cleanly |
| 4 | Log tokens and latency per call and print a run summary | Summary table prints after a run |
| Stretch | Add `get_abstract` and `lookup_wikipedia` from scratch, or make `check_citations` stricter (match titles as well as IDs) | Matches demo behavior |

Each task gets a collapsed hint cell. Full solutions live in the demo notebook, linked at the top.

## Model selection

The model is gpt-oss-120b. The bake-off compares the OpenRouter providers that serve it, plus one baseline run on a free Groq key. For each, run the demo question and the guided exercises about 10 to 20 times and record

- tool call success rate (valid JSON, real tool names)
- whether it uses more than one tool when it should
- citation check pass rate
- tokens per run after the trimming above, to confirm the 6–8k target
- latency per run
- price per run

The result is one pinned provider and one fallback for OpenRouter's provider routing settings. gpt-oss-20b and qwen3.8-27b are optional extras. Also confirm current gpt-oss-120b pricing for the pinned provider.

## Repo

Public repo at `github.com/nickmelamed/cal-nerds-research-agent`. Named for this agent so future workshop builds can get their own repos.

```
cal-nerds-research-agent/
  core/            tools, schemas, client wrapper, loop, tracer, citation check
  notebooks_src/   jupytext .py sources for each notebook
  build.py         assembles core cells into each notebook
  notebooks/       built .ipynb files with Open in Colab badges
  fixtures/        recorded arXiv/Wikipedia responses for OFFLINE mode and tests
  bakeoff/         model comparison scripts
  results/         bake-off outputs that docs cite
  tests/           fast tests on fixtures, live API tests marked slow
  docs/            this spec, workshop context, decision log
```

The workshop key is never committed. It's added to the student-facing copies of the notebooks just before the workshop (or shared on a slide) and revoked afterward.

Open in Colab links follow the pattern `colab.research.google.com/github/nickmelamed/cal-nerds-research-agent/blob/main/notebooks/<name>.ipynb`. Students use File, Save a copy in Drive.

## Build order

No fixed deadline.

1. Core tools with fast tests on fixtures and a few live tests against arXiv and Wikipedia
2. Provider bake-off for gpt-oss-120b on OpenRouter plus a free Groq baseline, including tokens per run
3. Demo notebook, including the citation check and offline fallback
4. Full-code starter, derived by removing pieces from the demo
5. Guided notebook, then test exercise 3 wordings
6. Dry run of all three in Colab on a fresh Google account, once with the workshop key and once with a fresh free key, timed against the 45 minute build block
7. Load check. A handful of simultaneous Colab sessions on the workshop key, watching remaining OpenRouter credit
8. Workshop key setup. Dedicated OpenRouter key with a credit limit
9. Final links into the slides, the pre-workshop email (own key optional) and the wrap-up slide (how to get a free key)
10. After the workshop, revoke the key
