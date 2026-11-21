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
