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
