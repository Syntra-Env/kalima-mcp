# ADR 006: Tauri E2E Testing via WebDriver (`tauri-driver` + WebdriverIO)

## Status
Accepted

## Date
2025-12-14

## Context
Playwright browser tests can validate the web UI, but they do not exercise the native Tauri runtime:
- the injected Tauri JS bridge (`window.__TAURI__`, `invoke`)
- the native WebView environment
- desktop startup behavior (including the embedded API server startup)

We need an E2E runner that drives the actual packaged/dev Tauri app.

## Decision
Use Tauri’s WebDriver approach for native E2E tests:
- `tauri-driver` as the WebDriver intermediary for Tauri
- a standard WebDriver client (WebdriverIO) to write and run the tests

## Rationale
- Tests the real desktop app behavior end-to-end.
- Uses standard WebDriver tooling and concepts.
- Aligns with Tauri’s documented guidance for native UI testing.

## Consequences
- The test runner requires `tauri-driver` and a native WebDriver binary (Windows: `msedgedriver.exe`).
- CI for native E2E will need additional setup on supported platforms.
- Browser-only Playwright UI tests are no longer considered sufficient as “desktop E2E”.

## Alternatives Considered
- Keep Playwright-only E2E: rejected because it does not test the Tauri bridge/runtime.
- Custom harness around Tauri internals: rejected as higher maintenance and less standard.

