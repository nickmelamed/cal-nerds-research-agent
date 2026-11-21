---
name: refresh-fixtures
description: Re-record cached arXiv and Wikipedia responses for tests and OFFLINE mode. Makes live network calls, so only the owner starts this.
disable-model-invocation: true
---

1. List the queries and terms in `fixtures/manifest.json` (the demo
   questions, the guided example questions, and the test cases).
2. Record each response through the real tools so the 3 second delay
   applies. Never write or edit a fixture by hand.
3. Show the diff in `fixtures/` and run `make test` against the new files.
4. Ask before committing, since `fixtures/` is protected.
