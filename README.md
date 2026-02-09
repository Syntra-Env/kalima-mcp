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

## Tools (36)

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

### Research (15)
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

### Graph Analysis (6) — NEW
- `analyze_coherence` - Composite coherence score (0.0–1.0) for research knowledge base
- `find_contradictions` - Detect explicit and implicit contradictions
- `compute_centrality` - Rank claims by importance (degree, betweenness, pagerank, eigenvector)
- `find_clusters` - Community detection (Louvain, label propagation, greedy modularity)
- `suggest_validation_order` - Topological sort for optimal validation ordering
- `detect_circular_dependencies` - Find circular reasoning in claim dependencies

## Database

SQLite database (`data/database/kalima.db`) opened directly with WAL mode. Contains:

- 6,236 verses (complete Quran)
- 114 surahs
- 77,429 tokens with 128,219 morphological segments
- 733 research claims across 17 patterns

## Project Structure

```
Kalima/
├── src/kalima/             # Python source
│   ├── server.py           # FastMCP server entry point
│   ├── db.py               # SQLite connection manager (WAL mode)
│   ├── tools/
│   │   ├── quran.py        # Verse retrieval and search
│   │   ├── linguistic.py   # Morphological search and pattern creation
│   │   ├── research.py     # Claims CRUD, evidence, dependencies
│   │   ├── workflow.py     # Verification session state machine
│   │   ├── context.py      # Morphology-aware verse context
│   │   └── graph.py        # NetworkX graph analysis
│   └── utils/
│       ├── arabic.py       # Arabic text normalization
│       └── short_id.py     # Sequential ID generation
├── data/database/          # SQLite database (gitignored)
├── pyproject.toml          # Python package config
└── requirements.txt
```

## Research Methodology

See [METHODOLOGY.md](METHODOLOGY.md) for the full falsification-based research approach and [CLAUDE.md](CLAUDE.md) for AI agent instructions.
