# Migration Tracker – Legacy (Python/JS) → Rust Engine

Goal: move all current features to the Rust engine while keeping the existing Python/JS UI usable until replaced. This follows the time‑proofing plan: stable data/API, replaceable UI/clients.

## Stable contracts
- Data: UTF-8 text; JSON/JSONL corpus layers; SQLite schema (later Postgres); optional Parquet for analytics.
- API (minimal, permanent):
  - `POST /search` (QuerySpec)
  - `GET /segment/{id}` (SegmentView)
  - `CRUD /annotations` (to add)
- Engine abstractions: `StorageBackend` (SQLite now), `SearchBackend` (Tantivy now), both behind traits.

## Current Rust engine state (baseline)
- `kalima-core`: models/traits (`QuerySpec`, `SegmentView`, `StorageBackend`, `SearchBackend`).
- `kalima-store`: SQLite storage, `segments` table storing `SegmentView` JSON (id/verse_ref/token_index/text/payload).
- `kalima-index`: Tantivy index for text + morph fields (roots, lemmas, pos, verb_form, gender, number, case, pattern, voice, mood, tense, aspect).
- `kalima-api`: Axum HTTP service with `/health`, `/search`, `/segment/{id}`, dev seed doc.
- Schemas: `schemas/query_spec.schema.json`, `schemas/segment_view.schema.json`.

## Legacy feature inventory (to migrate)
- Backend (Python/Flask in `app.py`):
  - Corpus loading from JSONL (Quran), tags, morphology, notes, pronouns, surah summaries.
  - Search endpoints: roots, morphology, syntax, pattern search, verb forms, dependency, notes.
  - Hypotheses/annotations CRUD (check actual endpoints).
  - Connections internal/external between tokens.
- Frontend (static/index.html, js/app.js, js/canvas.js, js/layers.js, css):
  - Word/morpheme/letter selection, details panel with morphological chips.
  - Root explorer, pattern search, morphological/syntax builders.
  - Notes/library search, hypotheses, navigation map, font scaling, settings.
  - Rendering layers (word/morpheme/letter), connection overlays.

## Migration steps
1) Data/model parity
   - Define SQLite schema for verses/tokens/segments/annotations/connections (normalize beyond JSON payload).
   - Import corpus JSONL → SQLite; store morph/syntax/dependency layers; keep JSONL as canonical export.
   - Add annotation/connections tables.
2) API parity
   - Implement `/annotations` CRUD.
   - Add search endpoints covering: root, morph, syntax, pattern, verb forms, dependency, notes/library.
   - Add `/connections` for internal/external links.
   - Ensure SegmentView includes all morphological/dependency fields currently used by UI chips.
3) Search/indexing
   - Extend Tantivy schema to index fields needed by above searches; consider specialized endpoints vs. generic QuerySpec filters.
   - Add ingestion/indexer that syncs SQLite → Tantivy.
4) Frontend bridge
   - Point legacy JS fetches to Rust API equivalents (keep Python backend as fallback until parity).
   - If endpoints aren’t ready, add a lightweight proxy or feature flags to choose backend per route.
5) Tests/goldens
   - Golden queries (JSON) → expected verse refs/ids.
   - SegmentView shape tests vs. schema.
   - Annotation CRUD expected state.
   - Connection CRUD expected state.
   - Basic UI smoke: can load surah list, click word, get SegmentView data.

## Immediate TODOs
- [ ] Design normalized SQLite schema (verses/tokens/segments/annotations/connections) and migrations.
- [ ] Define annotation and connection API routes in Axum.
- [ ] Add ingestion pipeline from existing corpus JSONL to SQLite + Tantivy.
- [ ] Map legacy endpoints in `app.py` to new Rust endpoints (root/morph/syntax/pattern/verb_forms/dependency/notes).
- [ ] Wire legacy frontend fetch URLs to Rust API (behind flag/config) once endpoints are ready.
- [ ] Add golden tests for search and SegmentView against sample corpus slices.

## Notes
- Keep legacy UI and Python backend available during migration; don’t delete until Rust API reaches parity.
- Keep data formats language-agnostic: JSONL exports, SQLite schema, documented JSON schemas.***
