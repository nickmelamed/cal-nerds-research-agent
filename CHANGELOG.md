# Changelog

## Unreleased

- Add `search_arxiv`, `get_abstract`, and `lookup_wikipedia` in `core/tools.py`.
- Add the client wrapper in `core/client.py` with 429 retry and a
  remaining-tokens header reader.
- Move the workshop key to OpenRouter, with a student's own Groq key as the
  optional provider, and add the OpenRouter credit helper.
- Add the provider bake-off scripts and the committed results.
- Cap runs at 6 steps, turn tools off on the last step, and retry an empty
  reply once.
- Read Unicode hyphens in arXiv ids and ignore quoted examples in the
  citation check.
- Add the full-code starter notebook with four student tasks and test cells
  for tasks 2 and 3.
- Add recorded fixtures, fast tests, and slow live tests.
