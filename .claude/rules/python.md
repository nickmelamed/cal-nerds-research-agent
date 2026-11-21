---
paths:
  - "core/**"
  - "build.py"
  - "bakeoff/**"
---

# Python

- Code in `core/` ends up in notebooks that run on Colab. Use only the
  standard library, `requests`, and `groq` there, and avoid syntax newer
  than the Python version Colab currently ships.
- Type hints on public functions. Docstrings follow writing-style.md.
- Tools return short strings or small JSON-serializable dicts that the model
  reads. On failure they return a message the model can act on ("No papers
  found for that query, try broader terms") instead of raising.
- Tool output is truncated to the token budget in docs/SPEC.md. Keep the
  limits as named constants at the top of the module.
- The arXiv delay lives inside the tool, not in callers, so no code path can
  skip it.
- Bake-off scripts write raw results to `results/` as CSV or JSON. Summaries
  are computed from those files, never typed in.
