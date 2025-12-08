# Runbook (Setup, Test, Troubleshoot)

## Setup
- Prereqs: Rust 1.70+, Tauri CLI, Node (for Playwright), Python optional.
- Data: place runtime assets in `data/database/kalima.db` and `data/search-index/`. Do not keep DBs in repo root.
- Env: defaults use `http://127.0.0.1:8080` and the `data/` paths; override via env vars if needed.

## Build/Run
- Desktop dev: `cargo tauri dev` (from `desktop/src-tauri`).
- Desktop release: `cargo tauri build` then copy `desktop/src-tauri/target/release/app.exe` to `Kalima.exe`.
- Run desktop: `./Kalima.exe` (from repo root).

## Testing
- Rust unit/tests (desktop): `cd desktop/src-tauri && cargo test`.
- UI E2E: `npx playwright test` (ensure server/app running against fixtures).
- Contract/API (add): call `/api/verse`, `/api/morphology`, `/api/dependency` against fixtures; assert shapes per `docs/API_CONTRACTS.md`.

## Troubleshooting
- Logs: desktop/backend logs follow Tauri defaults; check console output during dev. Add log level via env if needed.
- Data path issues: verify `data/database/kalima.db` and `data/search-index/` exist; ensure env vars point there.
- Command failures: use `inspect`/`see` per `docs/COMMAND_LAWS.md`; use `status` to view base URL and current context.
