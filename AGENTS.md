# Instructions for AI Agents (Claude)

## Tool Access Options

Kalima tools are available through two protocols:
1. **MCP (Model Context Protocol)** - Primary method for Claude via `mcp__kalima__*` tools
2. **UTCP (Universal Tool Calling Protocol)** - Alternative method via `utcp.json` manifest

Both protocols provide access to the same 22 underlying tools. Use whichever is available in your environment.

## Critical: Use Kalima Tools (MCP or UTCP) First

When working with Kalima research data, **ALWAYS** check for and use the Kalima tools **BEFORE** reaching for Bash/SQL commands.

### Available Kalima MCP Tools

#### Quran Data
- `mcp__kalima__get_verse` - Get a specific verse with Arabic text
- `mcp__kalima__get_surah` - Get an entire surah with all verses
- `mcp__kalima__list_surahs` - List all 114 surahs
- `mcp__kalima__search_verses` - Search for verses by Arabic text

#### Research Claims
- `mcp__kalima__search_claims` - Search/list claims (use this instead of SQL queries)
- `mcp__kalima__get_claim_evidence` - Get evidence for a claim
- `mcp__kalima__get_claim_dependencies` - Get claim dependencies
- `mcp__kalima__save_insight` - Create a new claim/insight
- `mcp__kalima__delete_claim` - Delete a claim (**use this, NOT bash SQL**)
- `mcp__kalima__delete_multiple_claims` - Delete multiple claims at once
- `mcp__kalima__update_claim_phase` - Update research phase of a claim

#### Patterns
- `mcp__kalima__list_patterns` - List linguistic patterns
- `mcp__kalima__create_pattern_interpretation` - Create a new pattern with interpretation
- `mcp__kalima__create_surah_theme` - Create a thematic interpretation for a surah

#### Linguistic Analysis
- `mcp__kalima__search_by_linguistic_features` - Search verses by POS, aspect, mood, root, etc.

#### Workflow/Verification
- `mcp__kalima__start_workflow_session` - Start verse-by-verse verification
- `mcp__kalima__get_next_verse` - Get next verse in workflow
- `mcp__kalima__submit_verification` - Submit verification and advance
- `mcp__kalima__get_workflow_stats` - Get progress statistics
- `mcp__kalima__list_workflow_sessions` - List all sessions (**use this, NOT bash SQL**)
- `mcp__kalima__check_phase_transition` - Check if claim should transition phases
- `mcp__kalima__add_verse_evidence` - Add verse as evidence with verification status

## When to Use Bash vs MCP Tools

### Use MCP Tools for:
- ✅ Listing workflow sessions
- ✅ Getting claim data
- ✅ Deleting claims or sessions
- ✅ Searching verses
- ✅ Adding evidence
- ✅ Any database query or modification related to Kalima research

### Use Bash for:
- ✅ Building the project (`npm run build`)
- ✅ Git operations
- ✅ File system operations (outside of data/)
- ✅ Running tests
- ✅ Installing dependencies

### NEVER Use Bash for:
- ❌ Direct SQL queries on kalima.db
- ❌ Deleting data from database
- ❌ Reading workflow sessions
- ❌ Modifying claims or evidence

## Common Mistakes to Avoid

### ❌ WRONG - Using Bash for database operations:
```javascript
node -e "const db = ...; db.exec('DELETE FROM claims WHERE id = ?', ['claim_123']);"
```

### ✅ CORRECT - Using MCP tool:
```
mcp__kalima__delete_claim with claim_id: "claim_123"
```

### ❌ WRONG - SQL query to list sessions:
```bash
node -e "db.exec('SELECT * FROM workflow_sessions')"
```

### ✅ CORRECT - Using MCP tool:
```
mcp__kalima__list_workflow_sessions
```

## ID Format

All IDs in Kalima use human-friendly sequential format:
- Claims: `claim_1`, `claim_2`, `claim_3`, ...
- Sessions: `session_1`, `session_2`, `session_3`, ...
- Patterns: `pattern_1`, `pattern_2`, `pattern_3`, ...
- Evidence: `evidence_1`, `evidence_2`, `evidence_3`, ...

These replaced the old UUID format (e.g., `claim-a15fb294-1cf9-43a5-95ae-44036a247c03`).

## Research Methodology

This project follows a falsification-based methodology:
1. **Question** - Initial observation or question
2. **Hypothesis** - Testable claim about Quranic interpretation
3. **Validation** - Systematic verse-by-verse verification
4. **Active Verification** - Claim survives initial testing, broader verification
5. **Passive Verification** - Claim is validated, remains open to falsification
6. **Rejected** - Claim was contradicted by evidence

When you find contradictions during verification, that's a **feature not a bug** - the methodology is working correctly by exposing false hypotheses.

## UTCP (Universal Tool Calling Protocol)

Kalima provides a UTCP manifest at `utcp.json` that describes all available tools. UTCP is a lightweight protocol that allows direct tool calling without wrapper servers.

### UTCP Manifest Location
- **File:** [utcp.json](utcp.json)
- **Protocol:** MCP (references existing MCP tools)
- **Tools:** All 22 Kalima tools with full parameter specifications

### Using UTCP
If your environment supports UTCP, you can load the manifest and call tools directly:

```json
{
  "protocol": "mcp",
  "tool_name": "get_verse",
  "parameters": {
    "surah": 2,
    "ayah": 255
  }
}
```

### UTCP Benefits
- **No additional infrastructure** - just a JSON manifest
- **Protocol agnostic** - can reference MCP, HTTP, CLI, or other protocols
- **Standard discovery** - AI agents can find and understand tools automatically
- **Backward compatible** - MCP server continues to work normally

### Documentation
See [MIGRATION_TO_UTCP.md](MIGRATION_TO_UTCP.md) for details on UTCP integration and options for extending beyond MCP.
