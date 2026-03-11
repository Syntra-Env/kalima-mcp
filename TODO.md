# TODO.md
```
Move completed tasks to DONE.md
Next number: 107
```

## Bashar/Melek Verification (High Priority)
98. **Resonance Benchmark**: Run `compute_root_resonance` for roots `بشر` (106) and `ملك` (1394). Verify the "Broadcaster" (high curvature/anomaly) vs "Governor" (low curvature/consistency) hypothesis.
99. **Semantic Bridge Test**: Use `root_distance` between `بشر` and `سفك`. If the meeting's hypothesis that "Bashar over-discloses" is true, we should see a high concordance score in specific informational contexts.
100. **Verse Emphasis Audit**: Analyze 15:28 and 12:31 using `analyze_verse_emphasis`. Does the math highlight the "Bashar" word as a point of high Anomaly or Drift?

## Surah 15 Ongoing Research
101. Analyze Iblis argument for refusal (15:33). Why "clay from altered black mud"? Map the roots S-L-S-L and H-M-A.
102. Track the "Respite" (Inthira) logic in 15:36-38. Why the "Appointed Time"?
103. NCU Perspective Tracer (P2.6) — trace the narrative of Surah 15 from Iblis's perspective to find the "Cognitive Bias" markers.

## Architectural Hardening
104. **Full Corpus Fingerprinting**: Run a batch script to pre-calculate `RootVector` profiles for all 1,643 roots and cache them. Currently, they are built on-the-fly, which is slow for large passages.
105. **Manifold Visualization Update**: Update the HTML visualizer to use the new `distributional_weight` as the node size for roots, replacing the old raw frequency.

## Cleanup
106. **Traditional Interpretation Scoping**: Decided on **Option B** for `compare_with_traditional`: Show the fingerprint (active roots ranked by curvature energy, emphasis profile, hot words) and let the researcher judge. No auto-scoring. Remove any lingering auto-scoring logic.
