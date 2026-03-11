# DONE.md — Completed Tasks

## MCP Server
1. Fix MCP connection issues
2. Add KALIMA_DB_PATH environment variable to opencode.json
3. Add get_content_address and find_by_content_address tools
4. Add get_resonance_map and compare_interpretations tools
5. Verify all core tools working: kalima_get_verse, kalima_search_verses, kalima_search_entries, kalima_get_entry_stats, kalima_list_surahs, kalima_get_verse_with_context, kalima_get_feature_context, kalima_search_by_linguistic_features

## Database Cleanup (2026-03-11)
6. Delete duplicate/test entries from database
7. Clean up 43 duplicate claims
8. Reduce database from ~110 to ~64 substantive entries
9. Drop dead tables: `entries`, `root_cooccurrence`, `root_lattice`
10. Update `src/db.py` to remove legacy initialization for dead tables and simplify schema setup.

## Audit (2026-03-11)
11. Audit HUFD/UOR math implementation vs source frameworks (Harlow docs + uor.foundation.jsonld)
12. Identify missing subsystems, incorrect math, and gaps in Quranic interpretation support
13. Refactor math layer to strictly separate Physics (Math), Orchestration (Tools), and Substrate (Data).

## UOR & HUFD Integration (2026-03-11)
14. **Resonance Search:** Tool to find verses/entries sharing identical holonomic addresses at morpheme level but differing in features
15. **Linguistic Curvature Metric:** Tool to calculate curvature of a research entry relative to Quranic composition chain
16. **Holonomic Deduplication:** Identify and merge research entries with identical content addresses
17. **Root Manifold Migration**: Generated SHA-256 UOR addresses for all 1,643 roots and populated `content_addresses`.
18. **UOR Ring Substrate**: Moved Z/(2^256)Z arithmetic and dihedral symmetry to `src/math/uor.py`.

## P0 — Math Foundation (2026-03-11)
19. Replace Arbitrary Feature Scaling with Information-Geometric Metrics
20. Populate missing feature frequencies (POS, morph, dep_rel, surah types) from actual usage
21. `features_to_h_components()` in `src/math/bridge.py` using log-inverse-frequency (surprisal)
22. Fix `get_field_tension()` → Tr(H†H) field strength norm in `src/math/gauge.py`
23. Add `get_pairwise_curvature()` for proper Tr(R_μν R^μν) between connection pairs
24. Implement Full Curvature Tensor (with background term) in `src/math/gauge.py`
25. Phase-Lock Index Φ via Hilbert-Schmidt inner product on su(2)
26. MCP tool: `measure_phase_lock(surah, ayah_a, ayah_b)`
27. Validated: 15:28→29 Φ=0.007 (hard boundary), 15:32→33 Φ=0.10 (speaker change)
28. Drift Energy E_d = ‖H_curr - H_prev‖²_F in `src/math/verse_dynamics.py`
29. MCP tool: `compute_passage_drift(surah, start, end)`
30. Semantic Lyapunov L_semantic = ‖H - H*‖² (deviation from root baseline) in `src/math/gauge.py`
31. HUFD Action decomposition into emphasis profile (root/morpheme/position/boundary)
32. MCP tool: `analyze_verse_emphasis(surah, ayah)`

## P1 — Abjadic Gauge Field (2026-03-11)
33. Root Lattice Structure (persistent tables & network tool)
34. Root network tool with shared radical + co-occurrence connections
35. MCP tool: `get_root_network(root_feature_id)`
36. Root Resonance (Holonomic Closure Test) via path-ordered holonomy in `src/math/gauge.py`
37. MCP tool: `compute_root_resonance(root_feature_id)`
38. Validated: كتب κ=2.35 (context-dep), ربب κ=1.06 (moderate)
39. Diacritic Gauge Analysis — lemma-grouped gauge orbits
40. كتب example: 50 forms across 6 lemmas
41. Morphological Pattern (Wazn) Fibers (`get_pattern_fiber` tool)
42. Root Co-occurrence Metric & Geodesic Distances
43. **Co-occurrence Fingerprints**: Integrated shared-verse counts into `RootVector` and `src/math/bridge.py`.

## P2 — Interpretation Support (2026-03-11)
44. `analyze_verse_emphasis` — per-word emphasis decomposition
45. `detect_boundaries` — inter-verse and intra-verse boundary detection
46. `compute_passage_drift` — drift energy across passages
47. Traditional interpretation table + `add_traditional_interpretation` + `compare_with_traditional`
48. `verify_root_concordance` — deviation-sorted falsification-first concordance
49. **Bilingual Transcription Pipeline**: Implemented `scripts/transcribe_meeting.py` using `yt-dlp` and `openai-whisper`.
50. **Meeting Insight Docking**: Successfully docked 5 claims from Dr. Hany Mehelba's session (Bashar/Melek/Monodromy/Safaka) to the manifold via `scripts/dock_meeting_insights.py`.

## P3 — UOR Integration (2026-03-11)
51. Ring Substrate Implementation
52. Dihedral Group Operations
53. Fiber Decomposition (Z/2Z fibration)
54. Constraint Resolution Pipeline (φ-maps)
55. Topological Pipeline (ψ-maps) for Betti numbers
56. UOR Index Theorem Implementation (Completeness Resolution)
57. Partition Classification of Quranic Elements
58. Spectral Convergence for Verification Workflows
59. Monodromy Classification (FlatType vs TwistedType)

## P4 — Bug Fixes & Infrastructure (2026-03-11)
60. High-resolution Lexical Coupling
61. Unified on holonomic_entries table
62. Fix `resolve_address()` holonomic_entries lookup (now tries both tables)
63. Fix `resolve_address()` verse resolution (was querying non-existent `verses` table)
64. Add numerical stability comment to arccos clipping
65. Migrate context.py, workflow.py, gauge.py from empty `entries` table to `holonomic_entries` (842 rows)
66. Add indexes on holonomic_entries (anchor_type+ids, last_activity, category)
67. Add surprisal caching in dynamics.py and gauge.py for performance
68. 7-verse analysis benchmark: 85ms (12ms/verse with cache)
69. Database Indexes & Performance
70. Repository cleanup (pristine research state)
71. **Math Refactor (Thin Wrappers)**: Moved all core math from `src/tools/` and `src/utils/` to `src/math/` (`gauge.py`, `root_space.py`, `uor.py`, `bridge.py`, `verse_dynamics.py`).
72. **Syntax Repair**: Fixed mass `SyntaxError` (backslash escapes in triple quotes) across all tool files.

## Visualization
73. 3D Manifold Visualizer
74. 2D Field Topology Map

## Surah 15 Research (2026-03-11)
75. Establish meta-narrative: knowledge concealment & respite period
76. Verification completed through 15:31 (Bashar creation & Iblis refusal)
77. Document linguistic claims: mubin = clarifying (not "clear"), rubama = hapax legomenon, ya'rujoon = limping (not "ascending"), zalla = remain in state (not "darkness"), sama' (singular) = Torah layer, samawaat (plural) = Quran layers, lawaqih = pollination (root ل-ق-ح), fasqaynakumuh = 6-part harmonized word
78. Save new insights: Biblical stories as misdirection (not just bridge), Iblis = cognitive bias, Jinn = rushed interpretation, Supplications shape reality, Correct supplication address: رَبِّ not اللَّهُمَّ, Bani Israel speech pattern: question-as-declaration
79. **Docked Transcription Insights**: Integrated `Bashar` (indiscriminate broadcaster) vs `Melek` (disciplined governor) and `Safaka` (over-disclosing) vs `Dima` (secrets of locution).

## Session Insights (2026-03-11)
80. Era transition: blocking lifted, appointed time arrived
81. Responsibility in new era: become bashar, not insan
82. Angels' situation and speaking to them
83. The coming rasool question
84. Open questions saved: Why was knowledge blocked? 1 vs 7 layers - literal or indicative?

## Research
85. Add verse evidence to new entries
86. Verify root س-ك-ر concordance across Quran
87. Verify root س-h-r concordance across Quran
88. Explore بُرُوج semantic field

## Sahih International Loading (2026-03-11)
89. Download Sahih International translation (6,236 verses) from quran.com API
90. Bulk-load into `traditional_interpretations` table (source='sahih_international')
91. Cached as `data/sahih_international.json` for re-runs without re-downloading
92. Confirmed isolation: table has zero FK/import connections to HUFD/UOR/resonance pipeline
93. Fix the 15:31 duplicate in `traditional_interpretations` table — deleted stray ibn_kathir row (id=1)
94. Remove `holonomize_traditional_interpretation` and `compare_interpretive_tension` from research.py — hash-distance comparison was noise, not a real linguistic metric. Already removed in prior session.

## Math Framework Redesign (2026-03-11)
95. Created `src/math/` module — pure math, no DB/MCP imports. Takes arrays/dicts in, returns results. Independently importable.
96. `src/math/root_space.py` — Root as a distributional vector built from all Quranic instances. RootVector dataclass with morphological profile (POS + verb_form + aspect + person + number + gender + case), surah spread, verse locations, lemma count.
97. Fixed importance vs rarity: two independent signals replace the old surprisal scalar:
    - `distributional_weight` = surah spread * form diversity. ربب=0.874 (pillar), هيت=0.025 (peripheral). Frequent central roots score HIGH.
    - `instance_anomaly` = per-subspace probability of this specific usage. Typical verb form=0.31 (low), rare adjective=0.45 (higher). Measures how unusual THIS instance is, not how rare the root is.
    - `concordance_distance` = Jensen-Shannon divergence between two root profiles. Measures distributional similarity.
