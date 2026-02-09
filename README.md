# Kalima - Quranic Research MCP Server

MCP server for Quranic text analysis, morphological research, graph analysis, and falsification-based linguistic exploration.

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
      "args": ["-X", "utf8", "-m", "kalima.server"],
      "env": {
        "PYTHONPATH": "src"
      }
    }
  }
}
```

## Tools (34)

### Quran (4)
- `get_verse` - Get a specific verse (Arabic text only)
- `get_surah` - Get an entire surah
- `list_surahs` - List all 114 surahs
- `search_verses` - Full-text search with Arabic normalization

### Linguistic Analysis (6)
- `search_by_linguistic_features` - Search by morphology (POS, aspect, mood, verb form, root, etc.) with ref table enrichment
- `compare_roots` - Find verses where two roots co-occur
- `create_pattern_interpretation` - Create linguistic pattern entries with linked terms
- `create_surah_theme` - Create thematic interpretations for surahs
- `add_verse_evidence` - Link verses as evidence to entries with verification status
- `link_entry_terms` - Link Arabic roots, lemmas, or linguistic features to entries

### Research (11)
- `search_entries` - Search entries by keyword, phase, or category
- `get_entry` - Get a single entry by ID
- `save_entry` - Save a research entry (with deduplication and category)
- `save_bulk_entries` - Save multiple entries at once (with deduplication)
- `update_entry` - Update entry content or phase
- `get_entry_evidence` - Get verse evidence for an entry
- `get_entry_dependencies` - Get entry dependency tree
- `get_entry_stats` - Database statistics with confidence distribution and health metrics
- `get_verse_entries` - Get all entries referencing a verse
- `get_verse_with_context` - Morphology-aware verse context with related entries per word
- `find_related_entries` - Discover structural connections between entries
- `add_entry_dependency` - Create typed relationships between entries
- `delete_entry` / `delete_multiple_entries` - Cleanup tools

### Workflow (6)
- `start_workflow_session` - Start systematic verse-by-verse verification
- `get_next_verse` - Get next verse in active workflow
- `submit_verification` - Submit verification and advance
- `get_workflow_stats` - View progress and statistics
- `list_workflow_sessions` - List all sessions
- `check_phase_transition` - Auto-transition entry phases based on evidence

### Graph Analysis (6)
- `analyze_coherence` - Composite coherence score (0.0-1.0) for research knowledge base
- `find_contradictions` - Detect explicit and implicit contradictions
- `compute_centrality` - Rank entries by importance (degree, betweenness, pagerank, eigenvector)
- `find_clusters` - Community detection (Louvain, label propagation, greedy modularity)
- `suggest_validation_order` - Topological sort for optimal validation ordering
- `detect_circular_dependencies` - Find circular reasoning in entry dependencies

## Database

SQLite database (`data/database/kalima.db`) opened directly with WAL mode. Contains:

- 6,236 verses (complete Quran)
- 114 surahs
- 77,429 tokens with 128,219 morphological segments
- Unified `ref_features` table: 6,744 linguistic features (4,833 lemmas, 1,643 roots, 45 POS tags, 140 dependency relations, 83 morphological features)
- 725 research entries across 11 categories, linked to features via entry_terms FK

## Project Structure

```
Kalima/
├── src/kalima/             # Python source
│   ├── server.py           # FastMCP server entry point
│   ├── db.py               # SQLite connection manager (WAL mode)
│   ├── tools/
│   │   ├── quran.py        # Verse retrieval and search
│   │   ├── linguistic.py   # Morphological search, evidence, term linking
│   │   ├── research.py     # Entries CRUD, evidence, dependencies
│   │   ├── workflow.py     # Verification session state machine
│   │   ├── context.py      # Morphology-aware verse context
│   │   └── graph.py        # NetworkX graph analysis
│   └── utils/
│       ├── arabic.py       # Arabic text normalization
│       ├── features.py     # Feature type mappings (segments ↔ ref_features)
│       └── short_id.py     # Sequential ID generation
├── data/database/          # SQLite database (gitignored)
├── scripts/                # One-off import/migration scripts
├── BOOKMARKS.md            # Curated research links
├── pyproject.toml          # Python package config
└── requirements.txt
```

## Research Methodology

See [METHODOLOGY.md](METHODOLOGY.md) for the full falsification-based research approach and [CLAUDE.md](CLAUDE.md) for AI agent instructions.
