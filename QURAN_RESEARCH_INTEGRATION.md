# QuranResearch → Kalima Integration

This document describes the integration of QuranResearch notes into the Kalima database.

## Overview

Previously, research findings were stored in two separate systems:
- **Kalima**: SQLite database with Quranic text + morphology
- **QuranResearch**: JSON database with 236 research notes/claims

This integration unifies them into a single SQLite database.

## What Was Added

### Database Schema

Four new tables in Kalima's SQLite:

1. **`patterns`** - Morphological/syntactic patterns (not verse-specific)
   - Example: "Present tense verbs indicate present/future"

2. **`claims`** - Research findings and hypotheses
   - Can optionally link to a pattern
   - Tracks verification phase (question → hypothesis → validation → verification)

3. **`claim_evidence`** - Links claims to supporting verses
   - Many-to-many relationship

4. **`claim_dependencies`** - Claims that build on other claims
   - Directed graph structure

### API Endpoints

New REST endpoints in Kalima API:

- `GET /api/claims?phase={phase}` - List claims, optionally filtered by phase
- `GET /api/claims/{id}/evidence` - Get verse evidence for a claim
- `GET /api/claims/{id}/dependencies` - Get dependency tree (uses recursive SQL)
- `GET /api/research/patterns?pattern_type={type}` - List patterns

## Migration Guide

### Prerequisites

1. Kalima database exists at `data/database/kalima.db`
2. QuranResearch database exists at `../QuranResearch/quran_research_database.json`
3. Python 3.9+ installed

### Steps

1. **Restart Kalima to create new tables**:
   ```bash
   cd apps/desktop/src-tauri
   cargo tauri dev
   ```
   The schema migration runs automatically on startup.

2. **Run the migration script**:
   ```bash
   cd Kalima
   python scripts/migrate_quran_research.py
   ```

   This will:
   - Read 236 notes from QuranResearch JSON
   - Insert as claims into Kalima SQLite
   - Create evidence links for verse references
   - Create dependency links between claims
   - Identify patterns (notes with no references but `pattern_query`)

3. **Verify the migration**:
   ```bash
   python scripts/test_claims_api.py
   ```

   Make sure the Kalima server is running first (`npm run dev`).

4. **Archive the old JSON**:
   ```bash
   mv ../QuranResearch/quran_research_database.json ../QuranResearch/quran_research_database.json.backup
   ```

## Usage Examples

### Query claims by phase

```bash
# Get all claims still in question phase
curl http://localhost:3000/api/claims?phase=question

# Get validated claims
curl http://localhost:3000/api/claims?phase=active_verification
```

### Get evidence for a claim

```bash
curl http://localhost:3000/api/claims/claim_1/evidence
```

Returns:
```json
[
  {
    "id": "...",
    "claim_id": "claim_1",
    "surah": 51,
    "ayah": 7,
    "notes": "Supporting evidence from verse",
    "created_at": "2026-01-20T..."
  }
]
```

### Get dependency tree

```bash
curl http://localhost:3000/api/claims/claim_1/dependencies
```

Returns:
```json
{
  "claim": {
    "id": "claim_1",
    "content": "NCU framework...",
    "phase": "question"
  },
  "dependencies": [
    {
      "id": "claim_2",
      "content": "Mulk concept...",
      "phase": "question"
    }
  ]
}
```

The dependency query uses a recursive CTE, so it returns the entire dependency chain, not just direct dependencies.

### List patterns

```bash
# All patterns
curl http://localhost:3000/api/research/patterns

# Just morphological patterns
curl http://localhost:3000/api/research/patterns?pattern_type=morphological
```

## Database Statistics

After migration, you should have:

| Table | Count | Description |
|-------|-------|-------------|
| claims | 236 | Research findings from QuranResearch |
| patterns | ~20-30 | Morphological patterns (notes with no references) |
| claim_evidence | varies | Verse citations supporting claims |
| claim_dependencies | varies | Claims building on other claims |

Check with:
```bash
sqlite3 data/database/kalima.db "SELECT COUNT(*) FROM claims"
```

## Architecture Benefits

### Before
- Two separate databases
- Manual cross-referencing
- No computational queries
- JSON doesn't scale

### After
- Single SQLite database
- SQL queries for complex relationships
- Recursive CTEs for dependency graphs
- Scales to 10,000+ claims easily

## Next Steps

1. **UI Integration**: Add claims browser to desktop app
2. **Visualization**: Dependency graph viewer
3. **Consistency Checks**: Script to flag contradictory claims
4. **Report Generation**: "All claims about root X"
5. **Provenance Tracking**: Add `discovered_from` field

## Troubleshooting

### Migration fails with "table already exists"

This means the schema migration already ran. Safe to ignore.

### API returns empty arrays

Make sure:
1. Migration script ran successfully
2. Kalima server restarted after schema changes
3. Correct API endpoint (check server logs)

### Cannot connect to API

Ensure Kalima is running:
```bash
cd apps/desktop/src-tauri
cargo tauri dev
```

Server should start on `http://localhost:3000`.

## Rollback

If something goes wrong:

1. Restore the backup:
   ```bash
   mv ../QuranResearch/quran_research_database.json.backup ../QuranResearch/quran_research_database.json
   ```

2. Delete Kalima's database and start fresh:
   ```bash
   rm data/database/kalima.db
   # Run tauri dev to regenerate
   ```

3. Re-ingest the Quran corpus:
   ```bash
   cargo run -p api --release --bin ingest -- \
     --db data/database/kalima.db \
     --index data/search-index \
     --input datasets/combined.jsonl
   ```

---

*Last updated: 2026-01-20*
