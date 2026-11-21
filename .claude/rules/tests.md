---
paths:
  - "tests/**"
  - "**/test_*.py"
  - "**/*_test.py"
---

# Tests

- Tests are the oracle for the code, so never weaken one to make it pass. Do
  not delete assertions, loosen tolerances, or add skip or xfail markers
  without the owner's approval. The Stop hook checks this against the base
  branch.
- When fixing a bug, first write a test that fails because of it.
- Fast tests use recorded responses in `fixtures/` and never touch the
  network. Fixtures are real responses recorded with the refresh-fixtures
  skill, never written by hand.
- Live tests hit arXiv and Wikipedia, are marked `@pytest.mark.slow`, and go
  through the tools so the 3 second delay applies. Keep them few.
- The citation check gets cases with known answers. A cited paper the run
  retrieved, one it didn't, a made-up ID, and an answer with no citations.
- The model providers (OpenRouter and Groq) are mocked in fast tests. Never
  call them from the test suite.
- Coverage is a floor, not the goal. Do not write hollow tests to raise a
  number.
