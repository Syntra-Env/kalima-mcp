# Fixtures

Place deterministic test assets here.

- Preferred: small DB at `data/database/kalima.db` and index at `data/search-index/` that cover a few verses (e.g., 1:1). Keep these out of VCS if large; document how to regenerate.
- API response fixtures (optional): JSON snapshots under `fixtures/api/` if you want to run API contract tests offline.

Environment:
- Contract tests default to `http://127.0.0.1:8080`; override with `KALIMA_BASE_URL`.
