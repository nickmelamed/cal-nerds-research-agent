# cal-nerds-research-agent

Notebooks for the Build an Agent segment of Cal NERDS AI 101, a workshop for
about 60 students ranging from community college to postdocs, most with
little AI experience. Students build a research paper assistant that searches
arXiv, reads abstracts, looks up terms on Wikipedia, and answers with
citations it actually retrieved. There are three Colab notebooks. The demo is
the finished agent Nick runs live. The guided track has students edit only
prompts and tool descriptions. The full-code starter has students write a
tool, error handling, a step cap, and logging. Good means every notebook runs
top to bottom in a fresh Colab runtime, a beginner can read every visible
cell, and the agent's citations check out.

The full design is in docs/SPEC.md and the workshop context is in
docs/workshop-context.md. Read the relevant section before changing anything
it covers. Status is in PROGRESS.md. Decisions and their reasons are in
docs/DECISIONS.md.

## Non-negotiable rules

1. Shared code lives in `core/` and reaches notebooks only through
   `build.py`. Never hand-edit `notebooks/*.ipynb`. Edit `core/` or
   `notebooks_src/` and rebuild.
2. Every built notebook is self-contained. No installing this repo and no
   fetching code from GitHub at runtime. The only pip install in a notebook
   is `openai`.
3. Tools call the arXiv and Wikipedia APIs with `requests` and `xml.etree`.
   Do not add the `arxiv` or `wikipedia` packages.
4. Never write, print, or commit an API key. `OPENROUTER_API_KEY` is the
   workshop key and `GROQ_API_KEY` is a student's own key. Code reads them
   from the environment locally and from Colab Secrets in notebooks. If
   `GROQ_API_KEY` is set the setup cell uses Groq, otherwise it uses
   OpenRouter, and if neither works it falls back to `getpass`. Nick adds
   the workshop key to student copies by hand.
5. Every arXiv request, including in tests and the bake-off, waits at least
   3 seconds after the previous one. Never load-test arXiv, OpenRouter, or Groq
   from a script.
6. Keep an agent run near 6 to 8k tokens. The reasons are cost, latency, and
   the 8K tokens per minute of a free Groq key. Do not raise result counts or text lengths without
   bake-off numbers in `results/` to back it.
7. The citation check runs after every agent answer in all three notebooks,
   and counts a citation as verified only if a tool returned it in that run.
8. The full-code starter deliberately lacks error handling for tool failures,
   a step cap, and token logging, because those are student tasks. Do not add
   them there. It does answer a bad tool name or invalid JSON, so a Run all
   does not crash on the first slip. The 429 retry lives in the setup cell's
   client wrapper in every notebook.
9. Numbers in docs (pass rates, tokens per run, latency, cost) come from
   files in `results/`. Write TBD until they exist.
10. Never weaken a test, lint rule, or check to make it pass.
11. Ask before changing anything in `.claude/protected-paths`, dependencies,
    CI, or hooks.

## Commands

```bash
make setup        # venv and dev dependencies
make build        # assemble notebooks/ from core/ and notebooks_src/
make test         # fast tests with fixtures, no network
make test-live    # live arXiv and Wikipedia tests, slow, rate-limited
make bakeoff      # model comparison, spends OpenRouter and Groq credits, Nick runs it
make agent-check  # what the Stop hook runs
make ci           # exactly what CI runs
```

## Where things live

- `core/`: tools, schemas, client wrapper, agent loop, tracer, citation check.
- `notebooks_src/`: jupytext percent-format sources for demo, guided, and
  full-code notebooks.
- `build.py`: assembles core cells into each notebook. `--check` fails if
  `notebooks/` is out of date.
- `notebooks/`: built notebooks, committed so Open in Colab links work.
- `fixtures/`: cached real API responses for OFFLINE mode and tests.
- `bakeoff/` and `results/`: model comparison scripts and their outputs.
- `tests/`: fast tests use fixtures. Live tests are marked `slow`.
- `.claude/rules/`: path-scoped rules for Python, notebooks, tests, writing.

## How to work here

- Plan before multi-file changes. Write the plan down and wait for approval
  when the task spans several modules or touches the spec.
- A task is done when the Stop hook's checks pass and you have shown the
  output. Show evidence (commands and results), not claims.
- Colab behavior (Secrets, form cells, Open in Colab links, preinstalled
  packages) can't be verified locally. Say so and add the item to the Colab
  checklist in PROGRESS.md instead of claiming it works.
- Commit in small atomic Conventional Commits (`type(scope): subject`). Code
  and its tests go in the same commit. Never use `--no-verify`.
- You may branch and commit locally. Ask before pushing, opening or merging
  pull requests, tagging, or changing dependencies.
- If you repeat a multi-step procedure, or I give you the same instructions
  twice, propose a skill for it in `.claude/skills/` and wait for approval.
- When compacting, keep the list of modified files, the current plan, and
  any failing checks.
