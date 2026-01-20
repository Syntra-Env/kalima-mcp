# Kalima - Quranic Research MCP Server

AI-powered Model Context Protocol (MCP) server for Quranic text analysis, morphological research, and linguistic exploration. Integrates seamlessly with OpenCode and Claude Desktop.

## Features

20 specialized tools for Quranic research and linguistic analysis:

### Quran Tools (4)
- `get_verse` - Get specific verse with Arabic text
- `get_surah` - Get entire surah with all verses
- `list_surahs` - List all 114 surahs with transliterated names
- `search_verses` - Full-text search with Arabic normalization

### Linguistic Analysis (4)
- `search_by_linguistic_features` - Search by morphology (POS, aspect, mood, verb form, root)
- `create_pattern_interpretation` - Store linguistic pattern interpretations
- `create_surah_theme` - Create thematic interpretations for surahs
- `add_verse_evidence` - Link verses as evidence to claims

### Workflow Tools (6)
- `start_workflow_session` - Start systematic verse-by-verse verification
- `get_next_verse` - Get next verse in active workflow
- `submit_verification` - Submit verification and advance automatically
- `get_workflow_stats` - View progress and statistics
- `list_workflow_sessions` - List all workflow sessions
- `check_phase_transition` - Auto-transition claim phases based on evidence

### Research Tools (6)
- `search_claims` - Search research claims by phase/pattern
- `get_claim_evidence` - Get verse evidence for claims
- `get_claim_dependencies` - Get claim dependency tree
- `list_patterns` - List morphological/syntactic/semantic patterns
- `save_insight` - Save new research insights
- `update_claim_phase` - Update claim phase (question → hypothesis → verification → theory → law)

## Quick Start

### Installation

```bash
# Install dependencies
npm install

# Build TypeScript
npm run build

# Test the server
npm test
```

### Configuration for OpenCode

Add to your OpenCode config (`~/.config/opencode/opencode.json`):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "kalima": {
      "type": "local",
      "command": [
        "node",
        "C:/Codex/Kalima/dist/index.js"
      ],
      "env": {
        "KALIMA_DB_PATH": "C:/Codex/Kalima/data/database/kalima.db"
      }
    }
  }
}
```

### Configuration for Claude Desktop

For Claude Desktop on Windows (`C:\Users\<username>\AppData\Roaming\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "kalima": {
      "command": "node",
      "args": ["C:/Codex/Kalima/dist/index.js"],
      "env": {
        "KALIMA_DB_PATH": "C:/Codex/Kalima/data/database/kalima.db"
      }
    }
  }
}
```

## Usage Examples

### Basic Queries
- "Show me verse 2:255" (Ayat al-Kursi)
- "Get the full text of Surah Al-Fatihah"
- "Search for verses containing 'رحمة' (mercy)"
- "List all surahs"

### Linguistic Analysis
- "Find verses with present tense verbs"
- "Show me imperative verbs in the Quran"
- "Search for verses with perfective aspect"
- "Find verses from the root ص-ل-و"
- "Create a pattern interpretation: present tense indicates ongoing actions"

### Workflow & Verification
- "Start a workflow to verify my hypothesis about present tense verbs"
- "Show me the next verse in my workflow"
- "This verse supports my hypothesis - record it and continue"
- "What are my workflow statistics?"
- "Check if my claim should transition to a new phase"

### Research Management
- "List all research claims in hypothesis phase"
- "What patterns exist for present tense verbs?"
- "Save this insight: [observation] with evidence from verse 12:7"
- "Show me the dependency tree for this claim"

## Database

The SQLite database (`data/database/kalima.db`) contains:

- **6,236 verses** with Arabic text (complete Quran)
- **114 surahs** with transliterated names
- **77,429 tokens** (full tokenization)
- **128,219 morphological segments** with detailed linguistic features
- **236 research claims** (migrated from QuranResearch)
- Patterns, interpretations, evidence links, and workflow data

### Linguistic Features

Search and analyze by:

- **pos** - Part of speech: `VERB`, `NOUN`, `ADJ`, `PRON`, `P` (preposition), `T` (particle)
- **aspect** - Verb aspect: `imperfective` (present), `perfective` (past), `imperative`
- **mood** - Verb mood: `jussive`, `subjunctive`
- **verb_form** - Arabic verb forms (I-X)
- **root** - Arabic trilateral/quadrilateral roots
- **person** - Grammatical person: `1st`, `2nd`, `3rd`
- **gender** - `masculine`, `feminine`
- **number** - `singular`, `dual`, `plural`
- **case** - Noun case: `nominative`, `accusative`, `genitive`
- **state** - Noun state: `definite`, `indefinite`, `construct`
- **voice** - Verb voice: `active`, `passive`

The search tool accepts user-friendly names (e.g., "verb", "present") and automatically normalizes them to database codes.

## Architecture

- **TypeScript + sql.js** - No Rust toolchain required
- **MCP Protocol** - Standard AI tool integration
- **SQLite Database** - Portable, fast, reliable
- **20 specialized tools** - Comprehensive Quranic research API

## Development

```bash
# Build
npm run build

# Test
npm test

# Run specific test
KALIMA_DB_PATH=data/database/kalima.db node tests/test-server.js
```

### Project Structure

```
Kalima/
├── src/                    # TypeScript source
│   ├── index.ts           # MCP server entry point
│   ├── db.ts              # Database connection
│   └── tools/             # MCP tool implementations
├── dist/                  # Compiled JavaScript
├── data/database/         # SQLite database (gitignored)
├── tests/                 # Test files
├── notes/                 # Personal research notes
├── archive/               # Archived Tauri/Rust implementation
└── package.json           # Dependencies and scripts
```

## Archived Components

The previous Tauri desktop app and Rust backend are archived in `archive/` for reference. See `archive/README.md` for details on the migration to MCP and restoration instructions.

## Research Methodology

Kalima implements a systematic falsification methodology for Quranic research:

1. **Question** - Initial observation or curiosity
2. **Hypothesis** - Testable claim about linguistic patterns
3. **Validation** - Preliminary evidence gathering
4. **Active Verification** - Systematic verse-by-verse testing
5. **Passive Verification** - Ongoing monitoring for counter-examples
6. **Theory** - Well-supported pattern with consistent evidence
7. **Law** - Universal pattern with no exceptions

Claims automatically transition between phases based on evidence ratios and verification progress.

## Contributing

Kalima is designed for:
- Quranic researchers
- Arabic linguists
- Computational linguistics researchers
- Anyone studying Quranic morphology and patterns

All research insights can be saved directly through the MCP tools and become part of the shared knowledge base.

## License

[Add your license here]

## Acknowledgments

- Quranic Corpus for morphological data
- MASAQ dataset
- Noor dataset
- QuranResearch integration
- OpenCode and Model Context Protocol teams
