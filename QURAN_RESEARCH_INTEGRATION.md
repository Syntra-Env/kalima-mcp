# QuranResearch → Kalima Integration

This document describes the integration of QuranResearch notes into the Kalima database and how to access them through OpenCode + MCP.

## Overview

Research findings are now unified in a single SQLite database accessible through:
- **OpenCode Desktop** via Model Context Protocol (MCP)
- **Direct SQLite queries** for advanced analysis

The database contains:
- 6,236 Quranic verses with Arabic text and morphology
- 236 research claims from QuranResearch
- Morphological and semantic patterns
- Evidence links between claims and verses

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

### MCP Tools

Kalima provides 10 MCP tools accessible through OpenCode:

**Quranic Text:**
- `list_surahs` - List all 114 surahs
- `get_verse` - Get specific verse with Arabic text
- `get_surah` - Get complete chapter
- `search_verses` - Full-text search in verses

**Research Claims:**
- `search_claims` - Find claims by phase/pattern
- `save_insight` - Save new research insights
- `update_claim_phase` - Update claim research phase
- `get_claim_evidence` - Get verse evidence for claims

**Linguistic Patterns:**
- `list_patterns` - List morphological/semantic patterns
- `get_pattern_occurrences` - Get verses using patterns

## Usage with OpenCode

### Example Queries

Start OpenCode Desktop and ask:

**Quranic Text:**
- "Show me verse 2:255"
- "Get surah Al-Fatihah (surah 1)"
- "Search for verses containing 'الله'"

**Research Claims:**
- "Search for claims about 'heart' in phase hypothesis"
- "Show me all claims in question phase"
- "Get evidence for claim ID claim_42"

**Linguistic Patterns:**
- "List all semantic field patterns"
- "Show me occurrences of pattern 'emphasis'"

### Saving New Insights

You can save research insights directly through OpenCode:

```
"Save this insight: The word 'qalb' (heart) appears in contexts of
transformation and change. Phase: hypothesis. Pattern: semantic_field_transformation"
```

The MCP server will:
1. Generate a unique claim ID
2. Store in the database
3. Link to relevant verses if specified
4. Set the research phase

## Direct Database Access

For advanced queries, you can query SQLite directly:

```bash
# Count claims by phase
sqlite3 data/database/kalima.db "
  SELECT phase, COUNT(*)
  FROM claims
  GROUP BY phase
"

# Find all claims about a specific root
sqlite3 data/database/kalima.db "
  SELECT c.id, c.title, c.content
  FROM claims c
  WHERE c.content LIKE '%root%'
"
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

### Current (MCP + OpenCode)
- Natural language interface via OpenCode
- Direct SQLite access for complex queries
- 10 MCP tools for structured operations
- No build toolchain required (TypeScript + sql.js)
- Scales to 10,000+ claims easily

### Archived (Tauri + Rust)
- See `archive/` directory for reference implementation
- REST API with 50+ endpoints
- Rust backend with Axum + Tantivy
- Required Rust toolchain

## Troubleshooting

### MCP Server not connecting to OpenCode

Check that the MCP server is configured:

```bash
# Verify global config exists
cat ~/.config/opencode/opencode.json

# Should show:
# {
#   "mcp": {
#     "kalima": {
#       "type": "local",
#       "command": ["node", "C:/Codex/Kalima/packages/mcp-server/dist/index.js"]
#     }
#   }
# }
```

If missing, run:
```bash
cd packages/mcp-server
npm run add-to-opencode
```

### Database queries return no results

Check database integrity:
```bash
sqlite3 data/database/kalima.db "SELECT COUNT(*) FROM claims"
sqlite3 data/database/kalima.db "SELECT COUNT(*) FROM verses"
```

Should show:
- 236 claims
- 6,236 verses

### OpenCode can't find verses

Ensure the database file exists:
```bash
ls -lh data/database/kalima.db  # Should be ~31MB
```

## Known Issues

See [packages/mcp-server/KNOWN_ISSUES.md](packages/mcp-server/KNOWN_ISSUES.md) for current known issues including:
- Empty surah names (cosmetic issue)
- Arabic text search normalization
- Empty claim_evidence table (migration pending)

---

*Last updated: 2026-01-20*
