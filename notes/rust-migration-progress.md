# Kalima Rust Migration - Progress Report

## ✅ Completed Work

### 1. Core API Endpoints Implemented
- `/api/roots` - List all unique roots from the corpus
- `/api/surahs` - List all surahs with metadata (number, name, ayah_count)
- `/api/surah/:number` - Get all verses for a specific surah
- `/api/morph_patterns` - Placeholder (returns empty array)
- `/api/syntax_patterns` - Placeholder (returns empty array)

### 2. Storage Backend Enhancements
Added three new methods to `SqliteStorage`:

- `list_unique_roots()` - Queries distinct roots from segments table
- `list_surahs()` - Returns surah summaries with ayah counts
- `get_surah_verses(number)` - Fetches all verses for a surah with text

### 3. Data Structures
- Created `SurahSummary` struct in `kalima-store`
- Created `SurahResponse`, `SurahInfo`, `VerseResponse` structs in `kalima-api`
- Properly exported and imported across modules

## 🔧 Next Steps

### Immediate Priorities

1. **Install Rust Toolchain**
   ```powershell
   # Download and run rustup-init.exe from https://rustup.rs/
   # Or use winget:
   winget install Rustlang.Rustup
   ```

2. **Build and Test**
   ```bash
   cd engine
   cargo build --release
   cargo test
   ```

3. **Run Ingestion**
   ```bash
   # Ingest the corpus JSONL into SQLite + Tantivy
   cargo run --bin kalima-ingest -- ../datasets/corpus/quran.jsonl
   ```

4. **Start the Server**
   ```bash
   cargo run --release --bin kalima-api
   # Server will run on http://localhost:8080
   ```

### Missing Implementations

#### Critical for Frontend Compatibility

1. **Verse Fetch Endpoints**
   - `/api/verse/:surah/:ayah` - Get specific verse with tokens
   - `/api/verse/index/:index` - Get verse by absolute index
   - `/api/verses` - Paginated verse list

2. **Enhanced Search Endpoints**
   - `/api/search?q=...&type=text|root` - Legacy search compatibility
   - Improve pattern/syntax search beyond heuristics

3. **Morphology Endpoints**
   - `/api/morphology/:surah/:ayah` - MASAQ morphological data
   - `/api/morphology/parsed/:surah/:ayah` - Parsed features with verb forms
   - `/api/morphology/features` - Available morphological features

4. **Dependency/Treebank Endpoints**
   - `/api/dependency/:surah/:ayah` - Dependency tree for verse
   - `/api/dependency/relations` - Available dependency relations

5. **User Data Endpoints**
   - `/api/hypotheses/:verse_ref` - Structure hypotheses
   - `/api/pronouns/:verse_ref` - Pronoun references
   - `/api/translations/:verse_ref` - Verse translations
   - `/api/patterns` - Pattern definitions

#### Nice to Have

1. **Populate Pattern Lists**
   - Analyze corpus to generate morphological patterns
   - Analyze corpus to generate syntactic patterns
   - Cache results for performance

2. **External Connections**
   - Implement external link semantics
   - Return actual external connections instead of empty array

3. **Comprehensive Testing**
   - Add golden tests for all endpoints
   - Test SegmentView shape consistency
   - Test search result formats

4. **Packaging & Deployment**
   - Create release build script
   - Bundle static assets
   - Auto-trigger ingestion on first run
   - Docker containerization

## 📁 Project Structure

```
engine/
├── kalima-api/          # Axum web server
│   └── src/main.rs      # ✅ Updated with new endpoints
├── kalima-core/         # Core traits and types
├── kalima-index/        # Tantivy search backend
├── kalima-store/        # SQLite storage backend
│   └── src/lib.rs       # ✅ Added list methods
└── tests/               # Integration tests
```

## 🎯 Current Status

**Backend**: ~60% complete
- Core search and storage working
- Annotations and connections working
- List endpoints implemented
- Missing: verse fetch, morphology, dependency, user data

**Frontend Compatibility**: ~40%
- Basic search routes working
- Root/POS/pattern search working
- Missing: verse navigation, detailed morphology, user annotations

## 🚀 Quick Start (Once Rust is Installed)

```bash
# 1. Build the project
cd engine
cargo build --release

# 2. Ingest the corpus
cargo run --bin kalima-ingest -- ../datasets/corpus/quran.jsonl

# 3. Run the server
cargo run --release --bin kalima-api

# 4. Test an endpoint
curl http://localhost:8080/api/surahs
curl http://localhost:8080/api/roots
```

## 📝 Notes

- The Python backend (`app.py`) is still fully functional and can be used as reference
- Static assets are served from `../static` by the Rust server
- Database file: `kalima.db` (SQLite)
- Search index: `kalima-index/` (Tantivy)
- All endpoints return JSON
- CORS is not configured yet (add if needed for frontend development)

---

**Last Updated**: 2025-11-23
**Status**: Ready for Rust installation and compilation
