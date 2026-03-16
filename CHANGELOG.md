# Changelog

All notable changes to the Kalima project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 82 roots from Quranic Arabic Corpus alignment (root audit)
- CHANGELOG.md for tracking data and code changes

### Removed
- 8 invalid roots (0 occurrences): أيي, ثري, حبنك, قني, لحي, _, ذو, انم

### Notes
- Root count: 1,643 → 1,721
- 95% parity with Quranic Arabic Corpus (1,721 vs 1,672 normalized)
- 49 methodological differences remain (thal vs dal root assignment)
- The 49 differences are valid: Kalima uses ذ (thal) as first radical where Corpus uses different letter assignments

---

## [0.1.0] - 2026-03-16

### MCP Server
- Fix MCP connection issues
- Add KALIMA_DB_PATH environment variable
- Add get_content_address and find_by_content_address tools
- Add get_resonance_map and compare_interpretations tools
- Verify all core tools working

### Database Cleanup
- Delete duplicate/test entries from database
- Clean up 43 duplicate claims
- Reduce database from ~110 to ~64 substantive entries
- Drop dead tables: entries, root_cooccurrence, root_lattice
- Update src/db.py to remove legacy initialization

### Audit
- Audit HUFD/UOR math implementation vs source frameworks
- Identify missing subsystems, incorrect math, and gaps
- Refactor math layer to separate Physics, Orchestration, and Substrate

### UOR & HUFD Integration
- Resonance Search tool
- Linguistic Curvature Metric
- Holonomic Deduplication
- Root Manifold Migration (SHA-256 addresses for 1,643 roots)
- UOR Ring Substrate (Z/(2^256)Z arithmetic and dihedral symmetry)

### P0 — Math Foundation
- Replace Arbitrary Feature Scaling with Information-Geometric Metrics
- Populate missing feature frequencies
- Fix get_field_tension() → Tr(H†H) field strength norm
- Add get_pairwise_curvature()
- Implement Full Curvature Tensor
- Phase-Lock Index Φ via Hilbert-Schmidt inner product
- Drift Energy E_d = ‖H_curr - H_prev‖²_F
- Semantic Lyapunov L_semantic = ‖H - H*‖²
- HUFD Action decomposition into emphasis profile

### P1 — Abjadic Gauge Field
- Root Lattice Structure
- Root network tool with shared radical + co-occurrence connections
- Root Resonance via path-ordered holonomy
- Diacritic Gauge Analysis
- Morphological Pattern (Wazn) Fibers
- Root Co-occurrence Metric & Geodesic Distances

### P2 — Interpretation Support
- analyze_verse_emphasis
- detect_boundaries
- compute_passage_drift
- Traditional interpretation table
- verify_root_concordance
- Bilingual Transcription Pipeline
- Meeting Insight Docking

### P3 — UOR Integration
- Ring Substrate Implementation
- Dihedral Group Operations
- Fiber Decomposition (Z/2Z fibration)
- Constraint Resolution Pipeline
- Topological Pipeline (Betti numbers)
- UOR Index Theorem
- Partition Classification
- Spectral Convergence
- Monodromy Classification (FlatType vs TwistedType)

### P4 — Bug Fixes & Infrastructure
- High-resolution Lexical Coupling
- Unified on holonomic_entries table
- Fix resolve_address() holonomic_entries lookup
- Fix resolve_address() verse resolution
- Add numerical stability comment to arccos
- Migrate context.py, workflow.py, gauge.py to holonomic_entries
- Add indexes on holonomic_entries
- Add surprisal caching
- 7-verse analysis benchmark: 85ms
- Repository cleanup
- Math Refactor: Moved core math to src/math/
- Syntax Repair: Fixed SyntaxError across tool files

### Visualization
- 3D Manifold Visualizer
- 2D Field Topology Map

### Surah 15 Research
- Meta-narrative: knowledge concealment & respite period
- Verification through 15:31
- Document linguistic claims (mubin, rubama, ya'rujoon, zalla, sama', samawaat, lawaqih, fasqaynakumuh)
- Biblical stories as misdirection
- Iblis = cognitive bias, Jinn = rushed interpretation

### Session Insights
- Era transition: blocking lifted, appointed time arrived
- Responsibility in new era: become bashar, not insan
- Angels' situation and speaking
- The coming rasool question

### Research
- Add verse evidence to new entries
- Verify root concordance
- Explore بُرُوج semantic field

### Sahih International Loading
- Download Sahih International translation
- Bulk-load into traditional_interpretations table
- Cache as data/sahih_international.json

### Math Framework Redesign
- Created src/math/ module (pure math, no DB/MCP imports)
- RootVector dataclass with morphological profile
- distributional_weight vs instance_anomaly
- concordance_distance via Jensen-Shannon divergence

### Bashar/Melek Verification
- Resonance Benchmark: BASHAR κ=3.0337, MELEK κ=1.5736
- Semantic Bridge Test: Distance 0.4743
- Verse Emphasis Audit on 15:28 and 12:31

### Surah 15 Research (March 2026)
- Iblis Argument (15:33) analysis
- Inthira Logic (15:36-38) confirmed
- NCU Perspective Trace

### Architectural Hardening
- Full Corpus Fingerprinting (1,643 roots)
- Manifold Visualization with distributional_weight

### Transcriber
- Fix Arabic transliteration: Switch to language="en" for phonetic rendering

---

## [0.0.1] - 2025-08-15

### Architecture Migration
- Complete transition to Rust backend (engine directory)
- Add Tauri desktop wrapper for native app experience
- Switch to Tauri interface to overcome CLI Arabic text rendering issues

### Database & Data
- Reorganize repository structure for clarity
- Add QuranResearch integration
- Add MASAQ dataset for morphological analysis
- Normalize MASAQ segment forms to avoid prefix/stem overreach
- Add morphology fallback from Quranic Arabic Corpus
- Strip extra bismillah from plain quran text to match tokenization

### API & Performance
- Fix N+1 query problem in get_surah endpoint
- Add shared lib and tests
- Split Tauri commands into modules
- Ensure full verse coverage with morphology fallback

### UI Features
- Add annotations, chat mode, hotbar, and modes modules
- Improve scroll position, layers, and search layout
- Add navigation annotation layers
- Implement word substitution annotations
- Display full morphology features in inspect
- Add legend command and color roles via font

### Testing
- Add frontend test harness
- Add e2e and unit tests for new UI features
- Verify all MCP tools integration
- Fix and verify OpenCode configuration

---

## [0.0.0] - 2024-12-XX (Initial Release)

### Added
- Initial Kalima project structure
- Database schema with features, morpheme_types, word_instances
- MCP server with verse search and research tools
- Quranic corpus morphology data
- Basic verse inspection and search
