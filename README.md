# Kalima MCP Server

Model Context Protocol (MCP) server that exposes Kalima's Quranic research databases as AI-callable tools.

## Features

20 tools for interacting with Quranic text and research claims:

### Quran Tools
- `get_verse` - Get a specific verse with Arabic text
- `get_surah` - Get an entire surah with all verses
- `list_surahs` - List all 114 surahs
- `search_verses` - Search for verses containing specific Arabic text

### Linguistic Analysis Tools
- `search_by_linguistic_features` - Search verses by morphological features (POS, aspect, mood, verb form, root, etc.)
- `create_pattern_interpretation` - Store linguistic pattern interpretations with associated claims
- `create_surah_theme` - Create thematic interpretations for entire surahs
- `add_verse_evidence` - Link verses as evidence to claims with verification status

### Workflow Tools
- `start_workflow_session` - Start a systematic verse-by-verse verification workflow
- `get_next_verse` - Get the next verse in an active workflow for verification
- `submit_verification` - Submit verification result and automatically advance to next verse
- `get_workflow_stats` - View progress, statistics, and verification breakdown for a workflow
- `list_workflow_sessions` - List all workflow sessions with status and progress
- `check_phase_transition` - Check and auto-transition claim phases based on evidence

### Research Tools
- `search_claims` - Search research claims by phase/pattern
- `get_claim_evidence` - Get verse evidence for a claim
- `get_claim_dependencies` - Get claim dependency tree
- `list_patterns` - List morphological/syntactic/semantic patterns
- `save_insight` - Save new research insights to database
- `update_claim_phase` - Update claim phase in falsification methodology

## Installation

```bash
npm install
npm run build
```

## Testing

```bash
node test-server.js
```

## Configuration for OpenCode

Add to your OpenCode MCP configuration (typically in `~/.opencode/config.json` or Claude Desktop config):

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

### Claude Desktop Configuration

If using Claude Desktop app on Windows, the config file is typically at:
```
C:\Users\<username>\AppData\Roaming\Claude\claude_desktop_config.json
```

Add the MCP server configuration to this file.

## Usage with OpenCode

Once configured, the AI will have access to all 20 tools and can:
- Query Quranic verses with proper Arabic rendering
- Search verses by linguistic features (POS tags, verb forms, mood, aspect, roots)
- Create and track linguistic pattern interpretations
- Document surah themes and verify them verse-by-verse
- Run systematic verse-by-verse verification workflows
- Track progress and statistics across workflow sessions
- Automatically detect contradictions and transition claim phases
- Search and analyze research claims
- Save insights discovered during conversation
- Track research through falsification methodology phases

### Example Queries

**Quran Tools:**
- "Show me verse 2:255" (Ayat al-Kursi)
- "Get the full text of Surah Al-Fatihah"
- "Search for verses containing the word 'رحمة'"

**Linguistic Analysis:**
- "Find verses with present tense verbs"
- "Show me imperative verbs in the Quran"
- "Search for verses with perfective aspect verbs"
- "Find verses from the root ص-ل-و"
- "Create a pattern interpretation: present tense verbs indicate ongoing actions"
- "Create a surah theme for Al-Fatihah: opening prayer and guidance"
- "Mark verse 1:1 as supporting my theme claim"

**Workflow Tools:**
- "Start a workflow to verify my pattern about present tense verbs"
- "Show me the next verse in my workflow"
- "This verse supports my hypothesis - record it and show me the next one"
- "What are the statistics for my workflow session?"
- "List all my active workflow sessions"
- "Check if my claim should transition to a new phase"

**Research Tools:**
- "List all research claims in the hypothesis phase"
- "What patterns have been identified for present tense verbs?"
- "Save this insight: [your observation] with evidence from verse 12:7"
- "Show me the evidence for claim X"

## Linguistic Features

The database contains full morphological analysis for 128,219 segments. You can search by:

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

The search tool supports user-friendly names (e.g., "verb", "present") which are automatically normalized to database codes.
