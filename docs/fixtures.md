# Fixtures

Use deterministic fixtures to keep tests fast and reproducible.

- **Database/index**: place small fixture DB at `data/database/kalima.db` and search index at `data/search-index/`. These are ignored in VCS; provide instructions to generate them for tests.
- **API JSON**: when adding contract tests, keep fixture responses under `tests/fixtures/api/` (e.g., `verse_1_1.json`, `morph_1_1.json`, `dep_1_1.json`).
- **UI E2E**: point Playwright to the fixture backend (or packaged app) and avoid mocks so commands exercise real data.

Document how fixtures are produced and their expected shape so they can be regenerated consistently.
