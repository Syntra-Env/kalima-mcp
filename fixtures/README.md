# Fixtures

Place deterministic test assets here.

- Preferred: small DB at `data/database/kalima.db` and index at `data/search-index/` that cover a few verses (e.g., 1:1). Keep these out of VCS if large; document how to regenerate.
- API response fixtures (optional): JSON snapshots under `fixtures/api/` if you want to run API contract tests offline.

Environment:
- Desktop contract tests will start a local API server automatically (ephemeral port) unless `KALIMA_BASE_URL` is set.
