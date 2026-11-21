# Changelog

## Unreleased

- Add `search_arxiv`, `get_abstract`, and `lookup_wikipedia` in `core/tools.py`.
- Add the Groq client wrapper in `core/client.py` with 429 retry and a
  remaining-tokens header reader.
- Add recorded fixtures, fast tests, and slow live tests.
