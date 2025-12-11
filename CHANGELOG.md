# Changelog

All notable changes to this project will be documented in this file.

## [1.0.1] - 2025-12-10

### Fixed
- **Verse Text Display:** Fixed critical bug where only the first token was displayed instead of the complete verse text
  - Root cause: `upsert_segment` was overwriting verse text with individual token text
  - Solution: Removed incorrect verse_texts insert from upsert_segment, verse text now managed by ingest.rs
- **Duplicate Segments:** Fixed duplicate prefix segments appearing in inspect output
  - Root cause: Demo seed data conflicting with real data for verse 1:1
  - Solution: Disabled seed_demo function since full database is now available
- **Error Handling:** Fixed silent failures in verse text ingestion
  - Changed from `let _ = query(...)` to `.await?` for proper error propagation

### Removed
- **Tense Field:** Completely removed tense field from entire system (use aspect instead for Arabic verbs)
  - Removed from database schema (engine/store/src/lib.rs)
  - Removed from Rust structs (engine/common/src/lib.rs)
  - Removed from API queries and responses (engine/store/src/lib.rs, engine/api/src/bin/ingest.rs)
  - Removed from search index (engine/search/src/lib.rs)
  - Removed from test fixtures (engine/api/tests/golden.rs)
  - Removed from conversion scripts (scripts/convert_datasets.py)

### Added
- **New Morphological Fields:**
  - `derived_noun_type`: Active participle (ACT_PCPL), Passive participle (PASS_PCPL), Verbal noun (VN)
  - `state`: Nominal state (INDEF for indefinite/tanween)
- **Test Coverage:** Added comprehensive Playwright tests for inspect functionality
  - Verifies full verse text display (all tokens)
  - Validates morphological structure (prefixes, stems, roots)
  - Confirms no tense field in output
  - Tests multiple verses for consistency
  - Location: tests/e2e/gui/inspect-verse.spec.ts

### Data
- Re-ingested complete Quranic corpus (6,236 verses) with corrected data
- New fields populated: derived_noun_type (2.8%), state (5.0%)
- Verse text now displays complete text (39 chars for Bismillah vs 6 chars before)

## [1.0.0] - 2025-11-28

### Added
- **Rust Backend:** Complete implementation (2,893 lines, 4 crates)
  - Axum web framework
  - SQLite storage with async queries
  - Tantivy full-text search
  - 50+ RESTful API endpoints
- **Performance:** 10-100x faster search vs Python
- **Deployment:** Docker, systemd, nginx configurations
- **Documentation:** README, CHANGELOG

### Changed
- Port: 5000 (Python) → 8080 (Rust)
- Backend: Python → Rust
- Database: In-memory → SQLite persistence
- Search: Python regex → Tantivy

### Removed
- Python backend (app.py)
- Python tests
- Virtual environment (.venv)
- Migration notes
- Temporary files

### Performance Improvements
- Search latency: ~500ms → ~10-50ms
- Startup time: ~3s → <1s
- Memory usage: ~200MB → ~50MB
- Throughput: ~100 req/s → >1000 req/s

## [0.9.0] - 2025-11-23 (Python Complete)

### Added
- Pattern extraction with F-E-L placeholders
- Clickable syntax roles
- Modular frontend (17 files)

## [0.8.0] - 2025-11-22

### Added
- Initial Rust backend implementation
- Parallel Python/Rust development

## Previous Versions

See git history for details.