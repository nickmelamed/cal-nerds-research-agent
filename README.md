# cal-nerds-research-agent

Notebooks for the Build an Agent segment of Cal NERDS AI 101, a workshop for
students from community college through postdoc, most with little AI
experience. You build a research paper assistant. It searches arXiv, reads
abstracts, looks up terms on Wikipedia, and answers with citations. After
every answer a check confirms that each cited paper was returned by a tool in
that run, so a citation the model made up gets flagged.

## The notebooks

Open one in Colab, then use File, Save a copy in Drive so your edits are
yours. Run the cells from top to bottom.

| Notebook | For | What you do | Open |
|---|---|---|---|
| Demo | Everyone | Watch the finished agent run and read how it works | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/nickmelamed/cal-nerds-research-agent/blob/main/notebooks/demo.ipynb) |
| Guided | No coding experience needed | Change the agent's behavior by editing prompts and tool descriptions | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/nickmelamed/cal-nerds-research-agent/blob/main/notebooks/guided.ipynb) |
| Build it yourself | Some Python | Write a tool, handle tool errors, add a step cap, and log tokens | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/nickmelamed/cal-nerds-research-agent/blob/main/notebooks/fullcode.ipynb) |

## Running a notebook

The notebooks need a key for a language model. During the workshop the
instructor adds a workshop key to your copy. It is revoked afterwards, so it
will not work if you come back later.

To use your own key, create a free account at [Groq](https://console.groq.com),
make an API key, and in Colab open the key icon in the left sidebar. Add a
secret named `GROQ_API_KEY`, paste the key as its value, and turn on notebook
access. The setup cell uses Groq when that secret exists. If no key is found
it asks you to paste one. Never type a key into a cell that you share.

If arXiv is slow or failing, set `OFFLINE = True` in the setup section. The
tools then answer from recorded arXiv and Wikipedia responses for the example
questions, with no network calls for the tools.

## Reproducing this later

Everything you need is in the notebook you saved. It installs one package,
`openai`, and does not install this repo or download code from it. You can
rerun it next month or next year with only a Groq key.

The tools call the arXiv and Wikipedia web APIs directly with `requests` and
`xml.etree`, so each request and response is visible in the code. The arXiv
tool waits 3 seconds between requests, as arXiv asks. The model is not
deterministic, so two runs of the same question can search differently and
cite different papers. The citation check does not vary. It counts a citation
as verified only if a tool returned that paper during the same run.

A run is capped at 6 model calls and costs about 6,200 tokens on average
(`results/bakeoff-six-steps.csv`). On OpenRouter that was about $0.0015 per
run (`results/bakeoff-cost-sample.csv`). A free Groq key allows 8,000 tokens
per minute, so a run can pause briefly and then continue.

To run the code on your own machine:

```bash
make setup     # virtual environment and dependencies
make test      # fast tests on recorded responses, no network
```

Locally, keys come from the environment variables `GROQ_API_KEY` or
`OPENROUTER_API_KEY` instead of Colab secrets.

## For maintainers

The shared code lives in `core/` and `notebooks_src/` holds the notebook
sources. `build.py` assembles them into `notebooks/`, which is committed so
the Colab links work. Do not edit the `.ipynb` files by hand. Change the
sources and rebuild.

```bash
make build        # assemble notebooks/ from core/ and notebooks_src/
make test         # fast tests with fixtures, no network
make test-live    # live arXiv and Wikipedia tests, slow and rate-limited
make bakeoff      # model comparison, spends provider credits
make agent-check  # build check, tests, lint, style check, key scan
make ci           # exactly what CI runs
```

The design is in [docs/SPEC.md](docs/SPEC.md), the reasons behind choices are
in [docs/DECISIONS.md](docs/DECISIONS.md), and current status is in
[PROGRESS.md](PROGRESS.md). Bake-off outputs that the docs cite are in
[results/](results/).
