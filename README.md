# Kalima - Quranic Research MCP Server

MCP server for Quranic text analysis, morphological research, and falsification-based linguistic exploration.

## Setup

```bash
pip install -e .
```

### Configuration

Add to `.mcp.json` or your MCP client config:

```json
{
  "mcpServers": {
    "kalima": {
      "command": "python",
      "args": ["-X", "utf8", "-m", "src.server"]
    }
  }
}
```

## Tools (28)

### Quran (4)
- `get_verse` - Get a specific verse (Arabic text only)
- `get_surah` - Get an entire surah
- `list_surahs` - List all 114 surahs
- `search_verses` - Full-text search with Arabic normalization

### Linguistic Analysis (5)
- `search_by_linguistic_features` - Search by morphology (POS, aspect, mood, verb form, root, etc.)
- `compare_roots` - Find verses where two roots co-occur
- `create_pattern_interpretation` - Create linguistic pattern entries with scope
- `create_surah_theme` - Create thematic interpretations for surahs
- `add_verse_evidence` - Link verses as evidence to entries with verification status

### Research (13)
- `search_entries` - Search entries by keyword, phase, category, or scope
- `get_entry` - Get a single entry by ID
- `save_entry` - Save a research entry (with deduplication and evidence verses)
- `save_bulk_entries` - Save multiple entries at once
- `update_entry` - Update entry content, phase, or scope
- `get_entry_evidence` - Get verse evidence for an entry
- `get_entry_dependencies` - Get entry dependency tree
- `get_entry_stats` - Database statistics with confidence distribution and health metrics
- `get_verse_entries` - Get all entries referencing a verse
- `get_verse_with_context` - Morphology-aware verse context with related entries per word
- `find_related_entries` - Discover structural connections between entries
- `add_entry_dependency` - Create typed relationships between entries
- `delete_entry` / `delete_multiple_entries` - Cleanup tools

### Workflow (6)
- `start_verification` - Start systematic verse-by-verse verification
- `continue_verification` - Get next verse in active verification
- `submit_verification` - Submit verification and advance
- `get_verification_stats` - View progress and statistics
- `check_phase_transition` - Auto-transition entry phases based on evidence

## Database

SQLite database (`data/kalima.db`) opened directly with WAL mode. Contains:

- 6,236 verses (complete Quran)
- 114 surahs
- 77,429 tokens with 128,219 morphological segments
- Unified `ref_features` table: 6,744 linguistic features (4,833 lemmas, 1,643 roots, 45 POS tags, 140 dependency relations, 83 morphological features)
- 848+ research entries with typed dependencies and verse-scoped evidence

## Project Structure

```
Kalima/
├── src/                    # Python package
│   ├── server.py           # FastMCP server entry point
│   ├── db.py               # SQLite connection manager (WAL mode)
│   ├── tools/
│   │   ├── quran.py        # Verse retrieval and search
│   │   ├── linguistic.py   # Morphological search, evidence
│   │   ├── research.py     # Entries CRUD, evidence, dependencies
│   │   ├── workflow.py     # Verification state machine
│   │   └── context.py      # Morphology-aware verse context
│   └── utils/
│       ├── arabic.py       # Arabic text normalization
│       ├── features.py     # Feature type mappings (segments <> ref_features)
│       └── short_id.py     # Sequential ID generation
├── data/                   # SQLite database (gitignored)
├── scripts/                # Migration scripts
├── pyproject.toml          # Python package config
└── requirements.txt
```

## Research Methodology

See [CLAUDE.md](CLAUDE.md) for the full falsification-based research approach and AI agent instructions.
