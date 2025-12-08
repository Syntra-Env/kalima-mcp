# Testing Strategy

We layer tests to enforce the command laws and guard real behavior:

- **Unit (pure helpers)**: parsing (`parse_verse_ref`, `parse_number`), analysis merge (`build_analysis_tokens`). Property/edge-case coverage, no IO.
- **Contract/API**: call `/api/verse`, `/api/morphology`, `/api/dependency` against a small fixture database/index; assert shape and invariants (surah/ayah ≥ 1, tokens present). See `tests/contract/api_contracts.rs`. Set `KALIMA_BASE_URL` if not using the default.
- **UI end-to-end**: Playwright driving the desktop/web UI against the real backend or packaged app—no mocking—to ensure commands like `see 1:1`, `inspect`, `clear`, zoom, etc. render correctly.
- **Fixtures**: deterministic data under `fixtures/` (or `data/database` for the small test DB) to keep tests fast and reproducible.

Targets:
- Default CI: unit + contract tests on fixtures; UI E2E on a minimal dataset.
- Local full run: `cargo test` in `desktop/src-tauri`, `npx playwright test`, API contract tests.
