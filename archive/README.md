# Archived Components

This directory contains components archived during the migration from Tauri desktop app to OpenCode + MCP integration.

**Archive Date:** January 20, 2026

## What's Archived

### 1. Desktop Tauri App (`desktop-tauri-20260120/`)

**Size:** ~500KB
**Purpose:** Tauri-based desktop application with IPC commands

**Contents:**
- `src-tauri/` - Rust backend with Tauri IPC handlers
- `frontend/` - Previously contained custom UI (already removed before archival)

**Why Archived:**
- Functionality replaced by OpenCode + MCP server
- No frontend code remained (was using custom AI chat UI that was abandoned)
- Tauri backend provided reference implementation for MCP server tools

**How to Restore:**
```bash
cp -r archive/desktop-tauri-20260120/ desktop/
```

### 2. Rust Engine (`engine-rust-20260120/`)

**Size:** ~2,900 lines of code across 4 crates
**Purpose:** Rust backend providing Quranic text queries and research tools

**Crates:**
- `api/` - Axum REST API server (418 lines)
- `store/` - SQLite database layer (347 lines)
- `search/` - Tantivy full-text search (982 lines)
- `common/` - Shared types and utilities (1,153 lines)

**Features:**
- 50+ REST endpoints
- SQLite + Tantivy integration
- < 1s startup, ~50MB memory
- > 1000 req/s throughput

**Why Archived:**
- MCP server provides same functionality without Rust toolchain
- TypeScript + sql.js more accessible for contributions
- Tauri app (only consumer of this engine) was archived

**How to Restore:**
```bash
cp -r archive/engine-rust-20260120/ engine/
```

Then build and run:
```bash
cd engine
cargo build --release
cargo run -p api --release
```

### 3. ML Package (`packages-ml-20260120/`)

**Size:** ~85MB
**Purpose:** Unclear - no visible Python source files

**Contents:**
- `checkpoints/` - Model checkpoints
- `models/` - Model definitions
- `scripts/` - Training/inference scripts
- `src/` - Source code (if any)

**Why Archived:**
- Purpose unclear after codebase review
- Not used by MCP server or active development
- Large size (85MB) with minimal documentation

**Note:** Directory was successfully copied to archive, but original may still exist in working tree due to VS Code file lock. Manually remove `packages/ml/` after closing VS Code if present.

### 4. Build Scripts

**Files:**
- `run-desktop.bat` - Launch Tauri desktop app
- `rebuild-desktop.bat` - Rebuild Tauri app

**Why Archived:**
- Specific to Tauri desktop app
- No longer needed with OpenCode integration

## Active System (Not Archived)

### MCP Server (`packages/mcp-server/`)

**Replaces:** Tauri app + Rust engine
**Tech Stack:** TypeScript + sql.js
**Tools:** 10 MCP tools for Quran + research
**Size:** 829 lines of code

**Dependencies:**
- `data/database/kalima.db` (31MB SQLite database)
- Node.js + npm
- Global OpenCode config at `~/.config/opencode/opencode.json`

### Database (`data/database/kalima.db`)

**Size:** 31MB
**Contents:**
- 6,236 Quranic verses with Arabic text
- 236 research claims
- Morphological patterns
- Semantic field mappings

**Shared:** Both archived Rust engine and active MCP server use the same database format.

## Restoring Archived Components

### Full Restoration

To fully restore the Tauri desktop app:

```bash
# 1. Restore directories
cp -r archive/desktop-tauri-20260120/ desktop/
cp -r archive/engine-rust-20260120/ engine/
cp archive/run-desktop.bat .
cp archive/rebuild-desktop.bat .

# 2. Install Rust toolchain (if not present)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
cargo install tauri-cli --locked

# 3. Build and run
cd desktop/src-tauri
cargo tauri dev
```

### Partial Restoration

To use the Rust engine as a standalone API server:

```bash
# 1. Restore engine only
cp -r archive/engine-rust-20260120/ engine/

# 2. Build and run
cd engine
cargo run -p api --release

# Server starts on http://localhost:8080
```

## Why MCP + OpenCode?

### Advantages Over Tauri

1. **No Build Toolchain:** MCP server is pure TypeScript, no Rust compilation needed
2. **Natural Language Interface:** Use OpenCode's AI to query in plain English
3. **Easier Contributions:** Lower barrier to entry (TypeScript vs Rust)
4. **Integrated Workflow:** Research directly in OpenCode alongside coding
5. **Smaller Footprint:** 829 lines vs 2,900 lines of code

### What Was Lost

1. **Native Desktop App:** Tauri provided standalone executable
2. **REST API:** 50+ endpoints for programmatic access
3. **Tantivy Search:** Full-text search engine (MCP uses SQLite FTS)
4. **UI Layers:** Complex multi-layer canvas architecture
5. **Offline Mode:** Tauri app worked without internet

### What Was Gained

1. **AI Integration:** Query database using natural language
2. **Simpler Maintenance:** Smaller codebase, fewer dependencies
3. **Faster Iteration:** No compilation step for changes
4. **Better Documentation:** OpenCode handles UI/UX
5. **Cross-Platform:** Works wherever OpenCode runs

## Rolling Back

If you need to roll back to the Tauri app:

```bash
# 1. Restore from archive
cp -r archive/desktop-tauri-20260120/ desktop/
cp -r archive/engine-rust-20260120/ engine/
cp archive/*.bat .

# 2. Remove MCP server from OpenCode config
# Edit ~/.config/opencode/opencode.json and remove "kalima" entry

# 3. Build and run Tauri
cd desktop/src-tauri
cargo tauri dev
```

## Archive Maintenance

**Keep Archives If:**
- You might need the Rust reference implementation
- You want to compare performance vs MCP server
- You're considering contributing Rust code upstream

**Delete Archives If:**
- MCP server is stable and meets all needs (recommend waiting 2-3 months)
- Disk space is constrained
- You're confident you won't need Tauri app

**Space Saved:** ~88MB (85MB ML + 3MB Tauri/engine)

## Questions?

See:
- [Root README.md](../README.md) - OpenCode setup
- [packages/mcp-server/README.md](../packages/mcp-server/README.md) - MCP server details
- [QURAN_RESEARCH_INTEGRATION.md](../QURAN_RESEARCH_INTEGRATION.md) - Research workflow

---

*Archived: 2026-01-20*
*Reason: Migration to OpenCode + MCP*
