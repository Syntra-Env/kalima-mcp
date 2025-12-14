# Runbook (Setup, Test, Troubleshoot)

## Setup
- Prereqs: Rust 1.77+, Tauri CLI, Node (for WebDriver E2E), Python optional.
- Data: place runtime assets in `data/database/kalima.db` and `data/search-index/`. Do not keep DBs in repo root.
- Env: defaults use `http://127.0.0.1:8080` and the `data/` paths; override via env vars if needed.

## Data (one-time)
If you don't already have `data/database/kalima.db` and `data/search-index/`:

- Build the combined corpus: `python scripts/build_combined_jsonl.py` (writes `datasets/combined.jsonl`).
- Ingest: `cd engine && cargo run -p api --release --bin ingest -- --db ../data/database/kalima.db --index ../data/search-index --input ../datasets/combined.jsonl`

## Build/Run
- Desktop dev: `cargo tauri dev` (from `desktop/src-tauri`).
- Desktop release: `cargo tauri build` then copy `desktop/src-tauri/target/release/app.exe` to `Kalima.exe`.
- Run desktop: `./Kalima.exe` (from repo root).

## Testing
- Rust unit/tests (desktop): `cd desktop/src-tauri && cargo test`.
- UI E2E (Tauri): `npm run test:e2e` (requires `tauri-driver`; see `tests/e2e-tauri/README.md`).
- Contract/API (add): `cd desktop/src-tauri && cargo test -q api_contracts` (starts its own API server by default).

## Troubleshooting
- Logs: desktop/backend logs follow Tauri defaults; check console output during dev. Add log level via env if needed.
- Data path issues: verify `data/database/kalima.db` and `data/search-index/` exist; ensure env vars point there.
- Command failures: use `read` and `layer` per `docs/COMMAND_LAWS.md`; use `status` to view base URL and current context.
