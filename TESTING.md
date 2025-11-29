# Testing Guide

## Frontend (Playwright)

The desktop web assets under `desktop/web/` can be exercised headlessly with Playwright using mocked API responses.

### Install
```bash
npm install
```

### Run
```bash
# Headless smoke
npm run test:e2e

# Headed for debugging
npm run test:e2e:headed

# Playwright UI mode
npm run test:e2e:ui
```

The config (`playwright.config.ts`) starts a static server on port 4173 via `http-server` and intercepts `/api/**` calls in the tests to serve fixtures (see `tests/e2e/navigation.spec.ts`). No backend is required.

## Backend (Rust)
```bash
cd engine
cargo test
```

## Conventions
- Keep unit/integration tests colocated with their crates (`engine/*/tests`).
- Place cross-cutting UI/E2E flows under `tests/e2e/`.
- Add lightweight API fixtures in tests instead of requiring the SQLite DB or Tantivy index.
