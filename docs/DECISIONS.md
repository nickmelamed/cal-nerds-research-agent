# Decisions

One entry per decision that someone might later question. Newest last.

## D-001: Drop Relevance AI for the demo (2026-11-20)

Context. The original outline used Relevance AI for a no-code agent demo.

Decision. Demo the finished version of the Colab agent students build,
printing every step.

Why. Relevance AI is another sign-up, its visual builder is a different
mental model from the notebooks, and free-tier limits or UI changes could
break a live demo. A printed trace shows the agent loop that a polished UI
hides.

Consequences. The demo previews the build directly. No no-code tool in the
workshop.

## D-002: Research paper assistant on arXiv and Wikipedia (2026-11-20)

Context. The agent needs to work for every level of the audience and use
free APIs.

Decision. An agent that searches arXiv, reads abstracts, and looks up terms
on Wikipedia, with three tools.

Why. Works from curiosity to a real literature search, pays off the earlier
hallucination demo with real citations, and both APIs are free with no key.
Three tools make the trace interesting because the agent has to choose.

Consequences. arXiv's rate guidance (one request every 3 seconds) shapes
the tool code and tests.

## D-003: Self-contained notebooks built from one source (2026-11-20)

Context. Three notebooks share most of their code.

Decision. Shared code lives in `core/` and `build.py` copies it into each
notebook. Notebooks never install this repo or fetch code at runtime.

Why. A fix lands everywhere at once, and a student who opens a link has
every cell they need. Plain `requests` calls keep tool code readable for the
full-code track.

Consequences. Built notebooks are committed and must be rebuilt after any
change.

## D-004: Paid workshop key, own key optional (2026-11-20)

Superseded by D-008. The Groq Developer plan is not available, so the
workshop key moved to OpenRouter.

Context. Every student creating a Groq account adds setup friction for
beginners. Groq rate limits apply per organization and per model, so a
shared key means a shared limit (250K TPM per model on the Developer plan).

Decision. A paid Developer plan key for the workshop, used by default.
Students may paste their own free key instead. Students split across
gpt-oss-120b and gpt-oss-20b for 500K TPM combined, with runs trimmed to
about 6 to 8k tokens.

Why. Setup becomes just opening Colab. Expected cost is under $10. A spend
limit and revoking the key afterward cap the risk of the key leaking.

Consequences. Depends on gpt-oss-20b passing the bake-off. Students who
want to keep building need their own key after the workshop.

## D-005: Recorded responses keyed by request, tools return dicts (2026-11-21)

Context. OFFLINE mode and the fast tests need real arXiv and Wikipedia
responses, and the citation check in phase 2 needs to read ids and titles
from tool output.

Decision. `fixtures/responses.json` stores raw response bodies keyed by the
request URL plus sorted query parameters, and `fixtures/manifest.json` lists
what to record. Tools return small dicts (`id`, `title`, and so on) on
success and a plain message string on failure. `get_abstract` returns `id`,
`title`, and `abstract`.

Why. The tools run unchanged against the recordings, so offline behavior
matches live behavior. Dicts give the citation check ids and titles without
parsing text.

Consequences. A new query or term needs a new recording through the
refresh-fixtures skill, since a missing key behaves like a failed request.

## D-006: One full agent loop in core, starter keeps a stripped copy (2026-11-21)

Context. The demo and guided notebooks need a step cap and token logging.
The full-code starter must lack error handling, a step cap, and logging,
because those are student tasks.

Decision. `core/agent.py` holds one full loop with `max_steps` and a
`Tracer`. Phase 5 builds the starter from a stripped version of the loop in
`notebooks_src/` instead of a second copy in `core/`.

Why. A fix to the loop reaches the demo and guided notebooks through the
build. The starter keeps its own bare loop.

Consequences. Phase 5 must keep the stripped loop in step with the core
loop by hand. `build.py --check` will not catch drift.

## D-007: Bake-off design and the gpt-oss-20b pass bar (2026-11-21)

Partly superseded by D-008. The live-run plan still holds. The 20b pass bar
was replaced by the provider selection rule in `bakeoff/PASS_BAR.md`.

Context. The bake-off has to decide the second student pool, and the
spec's roughly 20 runs per cell would put real load on arXiv.

Decision. The runner uses live arXiv and Wikipedia, starting with a pilot
of 3 runs per model and question, then about 10 per cell. The pass bar for
gpt-oss-20b is written in `bakeoff/PASS_BAR.md` before any run: tool-call
success of at least 95%, citation pass within 10 points of gpt-oss-120b,
mean tokens at most 8,000, and at most 1 in 10 runs ending early or in error.

Why. Fixtures would fail any query the model invents, which skews tool
success. Fewer live runs keep the 3 second arXiv spacing from turning the run
into an all-day job. The bar is fixed before any run.

Consequences. Confidence intervals are wide at 10 runs per cell. If a model
lands near the bar, run more before deciding. The guided questions in
`bakeoff/questions.py` are placeholders until phase 6 picks the exercises.

## D-008: Workshop key on OpenRouter instead of Groq (2026-11-21)

Context. Groq has paused new Developer plan upgrades, so a paid shared
Groq key isn't available. Free Groq keys allow 8K tokens per minute, which
is about one agent run.

Decision. The default workshop key is a paid OpenRouter key for
gpt-oss-120b, pinned to the most reliable provider from the bake-off.
Students can still use their own free Groq key. Notebooks use the `openai`
package with a base URL so either provider works. The split between
gpt-oss-120b and gpt-oss-20b is dropped, and D-007's pass bar for 20b no
longer applies.

Why. OpenRouter doesn't rate limit paid models itself, supports per-key
credit limits, and serves the same model. Students need no key of
their own.

Consequences. Tool calling quality depends on the upstream provider, so the
bake-off now compares providers. Upstream providers can still throttle.

## D-009: Six step cap, forced final answer, and quote rule (2026-11-23)

Context. With 8 steps and tools always on, 22 of the 45 pilot runs on the
three OpenRouter routes that served requests ended at the step cap without
an answer (`results/bakeoff-2026-11-21.csv`). All 15 google-vertex runs
failed with a routing error.
Searching again and again for papers that are not on arXiv, or for dates
that arXiv cannot filter on, caused most of them. After the prompt and
question changes, 15 of 120 runs still capped (`results/bakeoff-main.csv`).

Decision. The last model call of a run has tools turned off and a note
asking for an answer. The cap is 6 steps. The bake-off prompt limits
searches and tells the model that search cannot filter by date. The
citation check ignores quoted phrases that read as examples, not titles,
and reads Unicode hyphens inside old-style arXiv ids.

A quoted phrase now counts as unverified only if it starts in uppercase,
does not end in a period, and has no arrows or math symbols. This removes
false alarms on quoted example text, and it also means a made-up title
written in lowercase or ending in a period is not flagged. Arxiv ids are
checked as before, so a made-up id is still caught.

Why. With the 8 step cap and the forced answer, mean tokens were 8,195 per
run (`results/bakeoff-final-loop.csv`), over the 8,000 bar. Prompt tokens
are most of the total because each step resends the history. With the 6 step
cap the mean was 6,233 and the 90th percentile 7,505, with all 40 runs
answered and cited papers verified (`results/bakeoff-six-steps.csv`).

Consequences. 27 of those 40 runs used the forced last step, so most runs
are five tool steps and an answer. Half of the `guided_biology` runs used
search only and never read an abstract, so their answers lean on titles and
the model's own knowledge. The citation check confirms a cited paper was
retrieved, not that a claim about it is right. This is 10 runs per question
on one routing setting, so the margins are wide.

## D-010: Marker comments pull core code into notebooks (2026-11-23)

Context. Notebooks must be self-contained, so `core/` code has to be copied
into cells at build time.

Decision. A source cell holding `# @core <module>` gets that module's code in
its place, and `# @offline-data` gets the recorded responses from
`fixtures/responses.json`. `build.py` removes `from core` imports and the
`tools.` prefix, and fails if any reference to `core` is left. A cell that
starts with `# @title` becomes a collapsed Colab form cell. `--check` compares
cell types, sources, and metadata and ignores outputs.

`OFFLINE` is set in its own cell after the tools cell, because the tools cell
sets a default. Ruff skips `notebooks/` and `notebooks_src/`. The notebooks
are generated from `core/`, which ruff already checks, and the sources use
names that exist only after the build.

Consequences. `OFFLINE = True` replaces only the arXiv and Wikipedia calls.
The model still needs a key and a network. Saved responses cover only the
recorded queries, so most questions get a "could not be reached" message.
`MODEL` lives in `core/client.py` so the smoke test can use it before the
agent cell runs.
