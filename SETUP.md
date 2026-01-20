# Kalima MCP Server Setup with OpenCode

## Prerequisites

1. OpenCode Desktop App installed
2. Kalima MCP server built (see main README.md)

## Adding Kalima MCP Server to OpenCode

Run this command to add the Kalima MCP server:

```bash
opencode mcp add
```

When prompted, provide:

- **Name**: `kalima`
- **Command**: `node`
- **Args**: `C:/Codex/Kalima/packages/mcp-server/dist/index.js`
- **Environment Variables** (optional):
  - `KALIMA_DB_PATH=C:/Codex/Kalima/data/database/kalima.db`

## Verify Installation

Check that Kalima is listed:

```bash
opencode mcp list
```

You should see `kalima` in the list of MCP servers with status information.

## Test the Integration

1. Start OpenCode Desktop App:
   ```bash
   opencode
   ```

2. Try these test queries:
   - "Show me verse 2:255" (should display Ayat al-Kursi in Arabic)
   - "List the first 5 surahs"
   - "Search for claims in the hypothesis phase"
   - "What is the Bismillah verse?"

3. Verify Arabic text renders correctly in the OpenCode desktop app

## Available Tools

Once configured, the AI has access to 10 tools:

### Quran Tools
- `get_verse` - Fetch specific verse with Arabic text
- `get_surah` - Fetch entire surah with all verses
- `list_surahs` - List all 114 surahs
- `search_verses` - Search verses by Arabic text

### Research Tools
- `search_claims` - Query research claims by phase/pattern
- `get_claim_evidence` - Get verse evidence for a claim
- `get_claim_dependencies` - Get claim dependency tree
- `list_patterns` - List morphological/syntactic patterns
- `save_insight` - Save new insights to database
- `update_claim_phase` - Update claim research phase

## Troubleshooting

### MCP Server Not Starting

Check server logs:
```bash
opencode mcp debug kalima
```

### Test Server Standalone

```bash
cd C:/Codex/Kalima/packages/mcp-server
node test-server.js
```

Should output:
```
✓ Verse query works
✓ List surahs works
✓ Search claims works
All tests passed! MCP server is ready.
```

### Arabic Text Not Rendering

The OpenCode desktop app should support Arabic text rendering. If you see boxes or garbled text:
1. Check that proper Arabic fonts are installed (Scheherazade New, Amiri, etc.)
2. Try the web interface: `opencode web`

### Wrong Database Path

If the database can't be found, set the environment variable when adding the server or update the MCP configuration file directly.

## Manual Configuration (Alternative)

If the interactive `opencode mcp add` doesn't work, you can manually edit the OpenCode MCP configuration file.

The configuration file is typically located at:
- `~/.opencode/mcp-servers.json` or
- `~/.config/opencode/mcp-servers.json`

Add this entry:

```json
{
  "kalima": {
    "command": "node",
    "args": ["C:/Codex/Kalima/packages/mcp-server/dist/index.js"],
    "env": {
      "KALIMA_DB_PATH": "C:/Codex/Kalima/data/database/kalima.db"
    }
  }
}
```

## Next Steps

Once configured and tested:
1. Use OpenCode Desktop App as your primary interface for Quranic research
2. All manual terminal commands are now replaced with AI conversations
3. The AI will automatically call appropriate tools based on your questions
4. Insights from conversations can be saved directly to the database with `save_insight`
