# UTCP Manual for Kalima

## Overview

This document provides a UTCP (Universal Tool Calling Protocol) manifest for Kalima's research tools. UTCP allows AI agents to directly call Kalima's MCP tools without needing additional infrastructure.

## What is UTCP?

UTCP is a lightweight standard that enables AI agents to discover and call tools using their native protocols. Unlike other approaches:
- **No wrapper servers needed** - agents call your existing API directly
- **No additional infrastructure** - just a JSON manifest describing your tools
- **Protocol agnostic** - works with HTTP, CLI, gRPC, MCP, and more

Key principle: *"If a human can call your API, an AI agent should be able to call it too - with the same security and no additional infrastructure."*

## Current Architecture

Kalima uses Model Context Protocol (MCP) for tool calling:

```
Claude/AI Agent → MCP Server (stdio) → Tool Functions → Database
```

The MCP server is defined in [src/index.ts](src/index.ts) and exposes 22 tools for Quranic research.

## UTCP Integration

UTCP doesn't replace MCP - it provides an **alternative way to describe** the same tools. The MCP server can continue running, and UTCP just adds a JSON manifest that describes how to call those tools.

```
Claude/AI Agent → UTCP Manifest → MCP Protocol → Tool Functions → Database
```

## UTCP Manifest Structure

The manifest follows this structure:

```json
{
  "utcp": "1.0",
  "name": "Kalima",
  "description": "Quranic research tools using falsification methodology",
  "version": "1.0.0",
  "tools": [
    {
      "name": "get_verse",
      "description": "Retrieve a specific verse from the Quran",
      "call_template": {
        "protocol": "mcp",
        "tool_name": "get_verse",
        "parameters": {
          "surah": "{surah}",
          "ayah": "{ayah}"
        }
      },
      "parameters": {
        "surah": {
          "type": "integer",
          "description": "The surah (chapter) number (1-114)",
          "required": true,
          "minimum": 1,
          "maximum": 114
        },
        "ayah": {
          "type": "integer",
          "description": "The ayah (verse) number within the surah",
          "required": true,
          "minimum": 1
        }
      }
    }
  ]
}
```

## Implementation Options

### Option 1: MCP Protocol Reference (Current)

Keep the MCP server as-is and create a UTCP manifest that references MCP tools:

**Pros:**
- No code changes needed
- MCP server continues to work
- UTCP just adds discoverability
- Zero migration risk

**Cons:**
- Still requires MCP server running
- Agents need MCP protocol support
- Can't call tools from non-MCP clients

### Option 2: Direct Function Calls (CLI)

Expose tools as direct TypeScript function calls via CLI:

```json
{
  "call_template": {
    "protocol": "cli",
    "command": "node dist/cli.js get_verse --surah {surah} --ayah {ayah}",
    "format": "json"
  }
}
```

**Pros:**
- No MCP server needed
- Any system that can run commands can use it
- Simple and direct

**Cons:**
- Requires building CLI wrapper
- Less efficient than in-process calls
- Need to handle JSON parsing

### Option 3: HTTP REST API (Future)

Create a lightweight HTTP wrapper around existing functions:

```json
{
  "call_template": {
    "protocol": "http",
    "method": "GET",
    "url": "http://localhost:3000/api/quran/verse/{surah}/{ayah}",
    "headers": {
      "Content-Type": "application/json"
    }
  }
}
```

**Pros:**
- Standard protocol, works everywhere
- Can be called from any HTTP client
- Easy to secure with standard auth

**Cons:**
- Requires building HTTP server
- Additional infrastructure
- More complex deployment

## Recommended Approach

**Start with Option 1** (MCP reference), then optionally add Option 2 (CLI) for broader compatibility:

1. Create `utcp.json` manifest referencing MCP tools
2. Update documentation to explain UTCP usage
3. No code changes needed
4. (Optional) Add CLI wrapper for non-MCP clients

This gives immediate UTCP support with zero risk and zero code changes.

## Tool Categories

### Quran Data Tools (4 tools)
- `get_verse` - Get a specific verse with Arabic text
- `get_surah` - Get an entire surah with all verses
- `list_surahs` - List all 114 surahs
- `search_verses` - Search for verses by Arabic text

### Research Tools (7 tools)
- `search_claims` - Search/filter research claims
- `get_claim_evidence` - Get evidence for a claim
- `get_claim_dependencies` - Get claim dependency tree
- `save_insight` - Create a new claim/insight
- `delete_claim` - Delete a single claim
- `delete_multiple_claims` - Delete multiple claims
- `update_claim_phase` - Update research phase

### Linguistic Tools (5 tools)
- `search_by_linguistic_features` - Search by POS, aspect, mood, root
- `list_patterns` - List linguistic patterns
- `create_pattern_interpretation` - Create pattern with interpretation
- `create_surah_theme` - Create thematic interpretation
- `add_verse_evidence` - Add verse evidence with verification

### Workflow Tools (6 tools)
- `start_workflow_session` - Start verse-by-verse verification
- `get_next_verse` - Get next verse in workflow
- `submit_verification` - Submit verification and advance
- `get_workflow_stats` - Get session statistics
- `list_workflow_sessions` - List all sessions
- `check_phase_transition` - Check if claim should transition phases

## Next Steps

1. Create `utcp.json` manifest file
2. Generate full UTCP definitions for all 22 tools
3. Update [AGENTS.md](AGENTS.md) with UTCP usage instructions
4. Test with UTCP-compatible clients
5. (Optional) Create CLI wrapper for broader compatibility

## References

- [UTCP Specification](https://github.com/universal-tool-calling-protocol/utcp-specification)
- [UTCP Documentation](https://www.utcp.io/)
- [Kalima MCP Server](src/index.ts)
- [Agent Instructions](AGENTS.md)
