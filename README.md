# Kalima - Quranic Research MCP Server

MCP server for Quranic text analysis, morphological research, and falsification-based linguistic exploration.

## Setup

```bash
npm install
npm run build
```

### Configuration

Add to `.mcp.json` or your MCP client config:

```json
{
  "mcpServers": {
    "kalima": {
      "command": "node",
      "args": ["dist/index.js"],
      "env": {
        "KALIMA_DB_PATH": "data/database/kalima.db"
      }
    }
  }
}
```

## Tools (26)

### Quran (4)
- `get_verse` - Get a specific verse (Arabic text only)
- `get_surah` - Get an entire surah
- `list_surahs` - List all 114 surahs
- `search_verses` - Full-text search with Arabic normalization

### Linguistic Analysis (4)
- `search_by_linguistic_features` - Search by morphology (POS, aspect, mood, verb form, root, etc.)
- `create_pattern_interpretation` - Document linguistic pattern observations
- `create_surah_theme` - Create thematic interpretations for surahs
- `add_verse_evidence` - Link verses as evidence to claims with verification status

### Research (12)
- `search_claims` - Search claims by keyword, phase, or pattern
- `get_claim` - Get a single claim by ID
- `save_insight` - Save a research claim
- `save_bulk_insights` - Save multiple claims at once
- `update_claim` - Update claim content, phase, or pattern link
- `get_claim_evidence` - Get verse evidence for a claim
- `get_claim_dependencies` - Get claim dependency tree
- `get_claim_stats` - Database statistics overview
- `get_verse_claims` - Get all claims referencing a verse
- `get_verse_with_context` - Morphology-aware verse context with related claims per word
- `find_related_claims` - Discover structural connections between claims
- `add_claim_dependency` - Create typed relationships between claims
- `list_patterns` - List morphological/syntactic/semantic patterns
- `delete_claim` / `delete_multiple_claims` / `delete_pattern` - Cleanup tools

### Workflow (6)
- `start_workflow_session` - Start systematic verse-by-verse verification
- `get_next_verse` - Get next verse in active workflow
- `submit_verification` - Submit verification and advance
- `get_workflow_stats` - View progress and statistics
- `list_workflow_sessions` - List all sessions
- `check_phase_transition` - Auto-transition claim phases based on evidence

## Database

SQLite database (`data/database/kalima.db`) contains:

- 6,236 verses (complete Quran)
- 114 surahs
- 77,429 tokens with 128,219 morphological segments
- 733 research claims across 17 patterns

## Project Structure

```
Kalima/
├── src/                    # TypeScript source
│   ├── index.ts            # MCP server entry point + tool definitions
│   ├── db.ts               # Database connection and schema
│   ├── tools/              # Tool implementations
│   │   ├── quran.ts
│   │   ├── linguistic.ts
│   │   ├── research.ts
│   │   ├── workflow.ts
│   │   └── context.ts
│   └── utils/
│       ├── dbHelpers.ts
│       └── shortId.ts
├── dist/                   # Compiled JavaScript
├── datasets/               # Reference corpus data
├── data/database/          # SQLite database (gitignored)
└── package.json
```

## Research Methodology

See [METHODOLOGY.md](METHODOLOGY.md) for the full falsification-based research approach and [CLAUDE.md](CLAUDE.md) for AI agent instructions.
