# Tauri E2E (WebDriver)

This directory contains end-to-end tests that drive the **native Tauri app** via WebDriver (not Playwright-in-a-browser).

## Prereqs (Windows)

1. Install `tauri-driver`:
   - `cargo install tauri-driver --locked`
2. Install Microsoft Edge WebDriver (`msedgedriver.exe`) and ensure it’s on `PATH`.
   - If you prefer keeping tools in-repo, place it at `tools/webdriver/msedgedriver.exe` (ignored by git), or set `MSEDGEDRIVER_PATH`.

## Run

- `npm run test:e2e`

Notes:
- The Tauri app starts the embedded API server on `127.0.0.1:8080` during startup (`desktop/src-tauri/src/lib.rs`), so you don’t need to run the backend separately.

