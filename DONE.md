# DONE.md — Completed Tasks

## Audit (2026-03-10)
- [x] Audit HUFD/UOR math implementation vs source frameworks (Harlow docs + uor.foundation.jsonld)
- [x] Identify missing subsystems, incorrect math, and gaps in Quranic interpretation support

## UOR & HUFD
- [x] **Resonance Search:** Tool to find verses/entries sharing identical holonomic addresses at morpheme level but differing in features
- [x] **Linguistic Curvature Metric:** Tool to calculate curvature of a research entry relative to Quranic composition chain
- [x] **Holonomic Deduplication:** Identify and merge research entries with identical content addresses

## MCP Server
- [x] Fix MCP connection issues
- [x] Add KALIMA_DB_PATH environment variable to opencode.json
- [x] Add get_content_address and find_by_content_address tools
- [x] Add get_resonance_map and compare_interpretations tools
- [x] Verify all core tools working:
  - [x] kalima_get_verse
  - [x] kalima_search_verses
  - [x] kalima_search_entries
  - [x] kalima_get_entry_stats
  - [x] kalima_list_surahs
  - [x] kalima_get_verse_with_context
  - [x] kalima_get_feature_context
  - [x] kalima_search_by_linguistic_features

## Database Cleanup (2026-03-10)
- [x] Delete duplicate/test entries from database
- [x] Clean up 43 duplicate claims
- [x] Reduce database from ~110 to ~64 substantive entries

## Surah 15 Research (2026-03-10)
- [x] Establish meta-narrative: knowledge concealment & respite period
- [x] Verification completed through 15:31 (Bashar creation & Iblis refusal)
- [x] Document linguistic claims:
  - [x] mubin = clarifying (not "clear")
  - [x] rubama = hapax legomenon
  - [x] ya'rujoon = limping (not "ascending")
  - [x] zalla = remain in state (not "darkness")
  - [x] sama' (singular) = Torah layer
  - [x] samawaat (plural) = Quran layers
  - [x] lawaqih = pollination (root ل-ق-ح)
  - [x] fasqaynakumuh = 6-part harmonized word
- [x] Save new insights:
  - [x] Biblical stories as misdirection (not just bridge)
  - [x] Iblis = cognitive bias, Jinn = rushed interpretation
  - [x] Supplications shape reality
  - [x] Correct supplication address: رَبِّ not اللَّهُمَّ
  - [x] Bani Israel speech pattern: question-as-declaration

## Session Insights (2026-03-10)
- [x] Era transition: blocking lifted, appointed time arrived
- [x] Responsibility in new era: become bashar, not insan
- [x] Angels' situation and speaking to them
- [x] The coming rasool question
- [x] Open questions saved:
  - [x] Why was knowledge blocked?
  - [x] 1 vs 7 layers - literal or indicative?

## Research
- [x] Add verse evidence to new entries
- [x] Verify root س-ك-ر concordance across Quran
- [x] Verify root س-h-r concordance across Quran
- [x] Explore بُرُوج semantic field

## P0 — Math Foundation (2026-03-10)
- [x] **P0.1**: Replace arbitrary feature scaling with surprisal-based information-geometric metrics
- [x] Populate missing feature frequencies (POS, morph, dep_rel, surah types) from actual usage
- [x] `features_to_h_components()` in hufd_math.py using log-inverse-frequency
- [x] **P0.2**: Fix `get_field_tension()` → Tr(H†H) field strength norm
- [x] Add `get_pairwise_curvature()` for proper Tr(R_μν R^μν) between connection pairs
- [x] **P0.3**: Phase-Lock Index Φ via Hilbert-Schmidt inner product on su(2)
- [x] MCP tool: `measure_phase_lock(surah, ayah_a, ayah_b)`
- [x] Validated: 15:28→29 Φ=0.007 (hard boundary), 15:32→33 Φ=0.10 (speaker change)
- [x] **P0.4**: Drift Energy E_d = ‖H_curr - H_prev‖²_F
- [x] MCP tool: `compute_passage_drift(surah, start, end)`
- [x] **P0.5**: Semantic Lyapunov L_semantic = ‖H - H*‖² (deviation from root baseline)
- [x] **P0.6**: HUFD Action decomposition into emphasis profile (root/morpheme/position/boundary)
- [x] MCP tool: `analyze_verse_emphasis(surah, ayah)`

## P1 — Abjadic Gauge Field (2026-03-10)
- [x] **P1.1**: Root network tool with shared radical + co-occurrence connections
- [x] MCP tool: `get_root_network(root_feature_id)`
- [x] **P1.2**: Root resonance via path-ordered holonomy across all instances
- [x] MCP tool: `compute_root_resonance(root_feature_id)`
- [x] Validated: كتب κ=2.35 (context-dep), ربب κ=1.06 (moderate)

## P2 — Interpretation Support (2026-03-10)
- [x] **P2.1**: `analyze_verse_emphasis` — per-word emphasis decomposition
- [x] **P2.2**: `detect_boundaries` — inter-verse and intra-verse boundary detection
- [x] **P2.3**: `compute_passage_drift` — drift energy across passages
- [x] **P2.4**: Traditional interpretation table + `add_traditional_interpretation` + `compare_with_traditional`
- [x] **P2.5**: `verify_root_concordance` — deviation-sorted falsification-first concordance

## P4 — Bug Fixes & Infrastructure (2026-03-10)
- [x] Fix `resolve_address()` holonomic_entries lookup (now tries both tables)
- [x] Fix `resolve_address()` verse resolution (was querying non-existent `verses` table)
- [x] Add numerical stability comment to arccos clipping
- [x] Migrate context.py, workflow.py, gauge.py from empty `entries` table to `holonomic_entries` (842 rows)
- [x] Add indexes on holonomic_entries (anchor_type+ids, last_activity, category)
- [x] Add surprisal caching in dynamics.py and gauge.py for performance
- [x] 7-verse analysis benchmark: 85ms (12ms/verse with cache)

## P1 — Abjadic Gauge Field (continued)
- [x] **P1.3**: `analyze_diacritic_gauge(root_feature_id)` — diacritic gauge orbit analysis
- [x] Shows lemma-grouped gauge orbits (same root, different diacritical realizations)
- [x] كتب example: 50 forms across 6 lemmas

## System State (2026-03-10)
- 24 MCP tools registered across 8 modules
- 842 research entries in holonomic_entries table
- Feature frequencies populated for all feature types
- Surprisal caching for sub-15ms verse analysis
