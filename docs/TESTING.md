# Testing Strategy

We layer tests to enforce the command laws and guard real behavior:

- **Unit (pure helpers)**: parsing (`parse_verse_ref`, `parse_number`), analysis merge (`build_analysis_tokens`). Property/edge-case coverage, no IO.
- **Contract/API**: call `/api/verse`, `/api/morphology`, `/api/dependency` against a small fixture database/index; assert shape and invariants (surah/ayah ≥ 1, tokens present). See `desktop/src-tauri/tests/contract/api_contracts.rs`. Set `KALIMA_BASE_URL` if not using the default.
- **UI end-to-end (Tauri)**: WebDriver driving the native Tauri app (WebView). See `tests/e2e-tauri/README.md` and run `npm run test:e2e`.
- **Fixtures**: deterministic data under `fixtures/` (or `data/database` for the small test DB) to keep tests fast and reproducible.

Targets:
- Default CI: unit + contract tests on fixtures; UI E2E on a minimal dataset.
- Local full run: `cargo test` in `desktop/src-tauri`, `npm run test:e2e`, API contract tests.
