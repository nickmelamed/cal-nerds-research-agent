# Progress

Current phase and what is left. Claude updates this at the end of each
phase. CLAUDE.md stays stable and does not track status.

## Now

- [ ] Phase 1. Core tools (`search_arxiv`, `get_abstract`, `lookup_wikipedia`)
      with fixtures, fast tests, and live tests
- [ ] Phase 1. Client wrapper with 429 handling and rate limit header reader

## Next

- [ ] Phase 2. Agent loop, tracer, citation check
- [ ] Phase 3. Model bake-off (gpt-oss-120b, gpt-oss-20b, qwen3.8-27b),
      including tokens per run and whether cached tokens count toward TPM
- [ ] Phase 4. `build.py` and the demo notebook with OFFLINE mode
- [ ] Phase 5. Full-code starter
- [ ] Phase 6. Guided notebook and exercise 3 wording tests
- [ ] Phase 7. README with Open in Colab links

## Colab checklist (Nick, by hand)

- [ ] Each notebook runs with Run all in a fresh runtime on a fresh Google
      account, once with the workshop key and once with a free key
- [ ] Colab Secrets and the `getpass` fallback both work
- [ ] Form cells render collapsed
- [ ] Open in Colab links open the right notebooks
- [ ] Guided and full-code tracks each fit the 45 minute build block
- [ ] A handful of simultaneous sessions on the workshop key, watching the
      remaining-tokens header

## Workshop logistics (Nick)

- [ ] Dedicated workshop key, spend limit around $50, budget alerts
- [ ] Links in slides, pre-workshop email (own key optional), and wrap-up
      slide (how to get a free key)
- [ ] Revoke the workshop key after the workshop

## Done

## Open questions for the owner
