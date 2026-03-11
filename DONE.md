# DONE.md — Completed Tasks

## MCP Server
1. Fix MCP connection issues
2. Add KALIMA_DB_PATH environment variable to opencode.json
3. Add get_content_address and find_by_content_address tools
4. Add get_resonance_map and compare_interpretations tools
5. Verify all core tools working: kalima_get_verse, kalima_search_verses, kalima_search_entries, kalima_get_entry_stats, kalima_list_surahs, kalima_get_verse_with_context, kalima_get_feature_context, kalima_search_by_linguistic_features

## Database Cleanup (2026-03-10)
6. Delete duplicate/test entries from database
7. Clean up 43 duplicate claims
8. Reduce database from ~110 to ~64 substantive entries

## Audit (2026-03-10)
9. Audit HUFD/UOR math implementation vs source frameworks (Harlow docs + uor.foundation.jsonld)
10. Identify missing subsystems, incorrect math, and gaps in Quranic interpretation support

## UOR & HUFD
11. **Resonance Search:** Tool to find verses/entries sharing identical holonomic addresses at morpheme level but differing in features
12. **Linguistic Curvature Metric:** Tool to calculate curvature of a research entry relative to Quranic composition chain
13. **Holonomic Deduplication:** Identify and merge research entries with identical content addresses

## P0 — Math Foundation (2026-03-10)
14. Replace Arbitrary Feature Scaling with Information-Geometric Metrics
15. Populate missing feature frequencies (POS, morph, dep_rel, surah types) from actual usage
16. `features_to_h_components()` in hufd_math.py using log-inverse-frequency
17. Fix `get_field_tension()` → Tr(H†H) field strength norm
18. Add `get_pairwise_curvature()` for proper Tr(R_μν R^μν) between connection pairs
19. Implement Full Curvature Tensor (with background term)
20. Phase-Lock Index Φ via Hilbert-Schmidt inner product on su(2)
21. MCP tool: `measure_phase_lock(surah, ayah_a, ayah_b)`
22. Validated: 15:28→29 Φ=0.007 (hard boundary), 15:32→33 Φ=0.10 (speaker change)
23. Drift Energy E_d = ‖H_curr - H_prev‖²_F
24. MCP tool: `compute_passage_drift(surah, start, end)`
25. Semantic Lyapunov L_semantic = ‖H - H*‖² (deviation from root baseline)
26. HUFD Action decomposition into emphasis profile (root/morpheme/position/boundary)
27. MCP tool: `analyze_verse_emphasis(surah, ayah)`

## P1 — Abjadic Gauge Field (2026-03-10)
28. Root Lattice Structure (persistent tables & network tool)
29. Root network tool with shared radical + co-occurrence connections
30. MCP tool: `get_root_network(root_feature_id)`
31. Root Resonance (Holonomic Closure Test) via path-ordered holonomy
32. MCP tool: `compute_root_resonance(root_feature_id)`
33. Validated: كتب κ=2.35 (context-dep), ربب κ=1.06 (moderate)
34. Diacritic Gauge Analysis — lemma-grouped gauge orbits
35. كتب example: 50 forms across 6 lemmas
36. Morphological Pattern (Wazn) Fibers (`get_pattern_fiber` tool)
37. Root Co-occurrence Metric & Geodesic Distances

## P2 — Interpretation Support (2026-03-10)
38. `analyze_verse_emphasis` — per-word emphasis decomposition
39. `detect_boundaries` — inter-verse and intra-verse boundary detection
40. `compute_passage_drift` — drift energy across passages
41. Traditional interpretation table + `add_traditional_interpretation` + `compare_with_traditional`
42. `verify_root_concordance` — deviation-sorted falsification-first concordance

## P3 — UOR Integration (2026-03-10)
43. Ring Substrate Implementation
44. Dihedral Group Operations
45. Fiber Decomposition (Z/2Z fibration)
46. Constraint Resolution Pipeline (φ-maps)
47. Topological Pipeline (ψ-maps) for Betti numbers
48. UOR Index Theorem Implementation (Completeness Resolution)
49. Partition Classification of Quranic Elements
50. Spectral Convergence for Verification Workflows
51. Monodromy Classification (FlatType vs TwistedType)

## P4 — Bug Fixes & Infrastructure (2026-03-10)
52. High-resolution Lexical Coupling
53. Unified on holonomic_entries table
54. Fix `resolve_address()` holonomic_entries lookup (now tries both tables)
55. Fix `resolve_address()` verse resolution (was querying non-existent `verses` table)
56. Add numerical stability comment to arccos clipping
57. Migrate context.py, workflow.py, gauge.py from empty `entries` table to `holonomic_entries` (842 rows)
58. Add indexes on holonomic_entries (anchor_type+ids, last_activity, category)
59. Add surprisal caching in dynamics.py and gauge.py for performance
60. 7-verse analysis benchmark: 85ms (12ms/verse with cache)
61. Database Indexes & Performance
62. Repository cleanup (pristine research state)

## Visualization
63. 3D Manifold Visualizer
64. 2D Field Topology Map

## Surah 15 Research (2026-03-10)
65. Establish meta-narrative: knowledge concealment & respite period
66. Verification completed through 15:31 (Bashar creation & Iblis refusal)
67. Document linguistic claims: mubin = clarifying (not "clear"), rubama = hapax legomenon, ya'rujoon = limping (not "ascending"), zalla = remain in state (not "darkness"), sama' (singular) = Torah layer, samawaat (plural) = Quran layers, lawaqih = pollination (root ل-ق-ح), fasqaynakumuh = 6-part harmonized word
68. Save new insights: Biblical stories as misdirection (not just bridge), Iblis = cognitive bias, Jinn = rushed interpretation, Supplications shape reality, Correct supplication address: رَبِّ not اللَّهُمَّ, Bani Israel speech pattern: question-as-declaration

## Session Insights (2026-03-10)
69. Era transition: blocking lifted, appointed time arrived
70. Responsibility in new era: become bashar, not insan
71. Angels' situation and speaking to them
72. The coming rasool question
73. Open questions saved: Why was knowledge blocked? 1 vs 7 layers - literal or indicative?

## Research
74. Add verse evidence to new entries
75. Verify root س-ك-ر concordance across Quran
76. Verify root س-h-r concordance across Quran
77. Explore بُرُوج semantic field

## Sahih International Loading (2026-03-11)
78. Download Sahih International translation (6,236 verses) from quran.com API
79. Bulk-load into `traditional_interpretations` table (source='sahih_international')
80. Cached as `data/sahih_international.json` for re-runs without re-downloading
81. Confirmed isolation: table has zero FK/import connections to HUFD/UOR/resonance pipeline
82. Fix the 15:31 duplicate in `traditional_interpretations` table — deleted stray ibn_kathir row (id=1)
83. Remove `holonomize_traditional_interpretation` and `compare_interpretive_tension` from research.py — hash-distance comparison was noise, not a real linguistic metric. Already removed in prior session.

## Math Framework Redesign (2026-03-11)
91. Created `src/math/` module — pure math, no DB/MCP imports. Takes arrays/dicts in, returns results. Independently importable.
92. `src/math/root_space.py` — Root as a distributional vector built from all Quranic instances. RootVector dataclass with morphological profile (POS + verb_form + aspect + person + number + gender + case), surah spread, verse locations, lemma count.
93. Fixed importance vs rarity: two independent signals replace the old surprisal scalar:
    - `distributional_weight` = surah spread * form diversity. ربب=0.874 (pillar), هيت=0.025 (peripheral). Frequent central roots score HIGH.
    - `instance_anomaly` = per-subspace probability of this specific usage. Typical verb form=0.31 (low), rare adjective=0.45 (higher). Measures how unusual THIS instance is, not how rare the root is.
    - `concordance_distance` = Jensen-Shannon divergence between two root profiles. Measures distributional similarity.

## System State (2026-03-10)
- 24 MCP tools registered across 8 modules
- 842 research entries in holonomic_entries table
- Feature frequencies populated for all feature types
- Surprisal caching for sub-15ms verse analysis
