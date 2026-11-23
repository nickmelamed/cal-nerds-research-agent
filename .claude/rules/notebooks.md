---
paths:
  - "notebooks_src/**"
  - "notebooks/**"
---

# Notebooks

- Students read these, many for the first time in Python. Visible cells are
  short and do one thing. Plain names, no clever comprehensions, decorators,
  or classes unless the cell is teaching them.
- Markdown cells use plain language. Say what to do and what to notice.
  Explain a term the first time it appears.
- Code students don't need to read goes in Colab form cells with `# @title`
  and collapsed code. `build.py` sets the cell metadata.
- In the guided notebook students edit only text: the system prompt, the
  question, and the cell holding the tool descriptions. Keep those cells
  separate from the code.
- `fullcode.py` keeps its own minimal loop and `search_arxiv` on purpose.
  Do not pull in `core/` versions that would hand students the answers.
- Every notebook starts with the shared setup cell and must run with Run all
  in a fresh runtime. With `OFFLINE = True` the arXiv and Wikipedia calls use
  saved responses, but the model call still needs a key and a connection to
  OpenRouter or Groq.
- After any change, run `make build` and confirm `python build.py --check`
  is clean.
