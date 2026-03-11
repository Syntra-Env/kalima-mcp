# TODO.md
```
Move completed tasks to DONE.md
Next number: 98
```

## Math Framework Redesign
93. Still TODO for `root_space.py`: add co-occurrence fingerprint (which roots appear in the same verses) to the root vector. Currently only has morphological profile.
94. Fix cross-verse awareness: curvature of a word should know how that root behaves across ALL its Quranic instances, not just locally. The Lyapunov functional already tries this (deviation from root baseline) — extend it to use the full distributional vector.
95. Refactor tools layer: `src/tools/` becomes thin wrappers — query DB, pass clean data to `src/math/`, return results. No math in tools.
96. Make `src/math/` independently importable — anyone can `from src.math import root_space` without needing MCP server or database.
97. Validate against known results: phase-lock 15:28→29 boundary, root resonance كتب, verse emphasis 15:28. New math must reproduce these or explain why they change.

## DB Schema Cleanup
90. Drop dead tables from DB and `db.py`: `entries` (0 rows, replaced by `holonomic_entries`), `root_cooccurrence` (0 rows), `root_lattice` (0 rows)

## Cleanup
82. Remove `add_traditional_interpretation` tool — Sahih International is fully loaded (6,236 verses) and static. Traditional translations don't change; only our living research entries evolve.

## compare_with_traditional improvements
85. The current tool shows the HUFD emphasis profile + both readings side by side. This works. But auto-scoring entries against the verse ("root coverage") fails because entries use English/transliteration while roots are Arabic labels. Two options:
   - **Option A — Anchor-based scoring**: If an entry is anchored (via `anchor_type='root'`) to a root ID that's mathematically active in the verse, that's a direct structural match. No text matching needed.
   - **Option B — Just show the math**: Show the fingerprint (active roots ranked by curvature energy, emphasis profile, hot words) and let the researcher judge which reading respects it. Don't try to auto-score.
86. Decide which option to pursue

## NCU
87. NCU Perspective Tracer (P2.6) — trace a Quranic narrative from one nafs's perspective

## Ongoing Research
88. Continue Surah 15 verification from verse 15:32
89. Analyze Iblis argument for refusal (15:33)
