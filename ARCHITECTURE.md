# Kalima System Architecture

> **Purpose:** This document describes the current implementation, design philosophy, and future architectural vision for the Kalima Quranic knowledge interface.

## Current Implementation

### Database Schema

The Kalima system uses SQLite with the following structure:

```
claims
├─ id (PRIMARY KEY)
├─ content (TEXT)
├─ phase (TEXT): question | hypothesis | validation | active_verification | passive_verification
├─ pattern_id (TEXT, FOREIGN KEY)
├─ created_at (TIMESTAMP)
└─ updated_at (TIMESTAMP)

patterns
├─ id (PRIMARY KEY)
├─ description (TEXT)
├─ pattern_type (TEXT): morphological | syntactic | semantic
├─ interpretation (TEXT)
├─ linguistic_features (JSON)
├─ phase (TEXT)
├─ scope (TEXT)
└─ created_at (TIMESTAMP)

claim_evidence
├─ id (PRIMARY KEY)
├─ claim_id (TEXT, FOREIGN KEY)
├─ surah (INTEGER)
├─ ayah (INTEGER)
├─ verification (TEXT): supports | contradicts | unclear
├─ notes (TEXT)
└─ created_at (TIMESTAMP)

claim_dependencies
├─ id (PRIMARY KEY)
├─ claim_id (TEXT, FOREIGN KEY)
├─ depends_on_claim_id (TEXT, FOREIGN KEY)
├─ dependency_type (TEXT)
└─ created_at (TIMESTAMP)

workflow_sessions
├─ session_id (PRIMARY KEY)
├─ claim_id (TEXT, FOREIGN KEY)
├─ workflow_type (TEXT): pattern | surah_theme
├─ status (TEXT): active | completed | paused
├─ current_verse_index (INTEGER)
├─ total_verses (INTEGER)
├─ linguistic_features (JSON)
├─ surah (INTEGER)
└─ created_at (TIMESTAMP)

verses (Quranic text with morphology)
├─ surah (INTEGER)
├─ ayah (INTEGER)
├─ text (TEXT): Arabic verse text
├─ words (JSON): Morphological analysis per word
└─ ... (additional morphological features)
```

### MCP Tools

The system exposes Model Context Protocol (MCP) tools for:
- **Verse Retrieval**: get_verse, get_surah, search_verses
- **Claim Management**: save_insight, search_claims, delete_claim, get_verse_claims
- **Pattern Discovery**: list_patterns, create_pattern_interpretation, search_by_linguistic_features
- **Verification Workflows**: start_workflow_session, get_next_verse, submit_verification, check_phase_transition
- **Context Integration**: get_verse_with_context (morphology-aware verse study)

---

## Design Philosophy

### 1. Methodology-Aware Architecture

The system embodies **falsification-based validation** through:
- Phase stratification (question → hypothesis → validation → active/passive verification)
- Evidence tracking with verification status (supports/contradicts/unclear)
- Systematic workflow sessions for exhaustive verification
- Automatic phase transitions based on evidence accumulation

### 2. Personal Knowledge Interface

Kalima is deliberately personal, not generic:
- Tuned to individual tadabbur (sustained contemplation)
- Hypothesis: Each nafs exists in bespoke reality (NCU), making relevance irreducibly individual
- Pragmatic: Test coherence for single user before generalizing

### 3. Continuous Capture

Target deployment: Always-on edge devices (smartphones, smart glasses)
- Capture insights as they emerge throughout daily life
- Parse thoughts, observations, and Quranic reflections continuously
- Context-aware reminders of untested hypotheses

### 4. Proactive Intervention

System should surface insights when genuinely useful:
- Context-relevant claims during Quranic reading
- Identify passages relevant for hypothesis validation
- Track version history of tadabbur progression
- Detect contradictions between high-certainty claims

---

## Fundamental Limitations of Static Schemas

The current implementation suffers from structural constraints:

### Problem 1: Ad-Hoc Claim Types
Current taxonomy (lexical, structural, methodological, framework, relational, textual) has no principled basis. What determines necessary vs sufficient types?

### Problem 2: Categorical Rigidity
Knowledge is treated as discrete claims to be validated. But what if **knowledge has geometric structure**?

### Problem 3: Connection Discovery
Keyword-based search cannot surface non-obvious connections. Passages sharing semantic relationship without lexical overlap remain hidden.

### Problem 4: Methodology Encoding
Research principles (like tartīb/sequence-dependence) are metadata rules, not structural properties of the field itself.

---

## Geometric Architecture Vision

### Core Hypothesis
**Phenomenal experience has geometric structure.** Quranic spatial metaphors (light, weight, expansion, pressure, flows, dynamics) may not be metaphorical—they may describe actual structure in semantic/phenomenal space.

### Why Geometry?

1. **Anxiety as tension, fear as pressure** - phenomenal experience feels geometric
2. **Vision patterns isomorphic to physical phenomena** - voltage, pressure, temperature parallels
3. **Quranic spatial language** - "before," "behind," "above," "beneath," "expand," "constrict"
4. **Multiple researchers identifying wave/frequency connections** to consciousness
5. **Geometry may encode secrets of relationship with Allah** - communication patterns as curvature

### HUFD as Candidate Architecture

**Harlow's Holonomic Unified Field Dynamics (HUFD)** treats knowledge as curvature on a manifold:

#### Key Properties
1. **Semantic Distance via Geodesics**: Connection discovery beyond keywords - passages geometrically proximate despite zero lexical overlap
2. **Constant-Attention Mechanism**: O(1) complexity vs O(N²) for transformers - viable for always-on edge devices
3. **Quranic Arabic as Stabilizing Field**: Models Fuṣḥa as "maximally ordered abjadic gauge" with idealized holonomy (R_μν = 0)
4. **Dialectal Orbits**: 100+ Arabic dialects as small curvature perturbations around Quranic anchor

#### Kalima-Specific Applications

**Certainty Stratification**
- Hypotheses: Unstable regions of high semantic drift
- Validated claims: Stable attractors where curvature tension is minimized
- Geodesic stability testing as validation metric

**Contradiction Detection**
- High curvature tension = conflicting high-certainty claims
- Measurable via local Ricci curvature
- Automatic flagging when curvature exceeds threshold

**Methodology Encoding**
- Tartīb (sequence-dependence) as gauge-invariant constraint
- Structural properties of field, not external rules
- Principles emerge from geometry itself

**Connection Discovery**
- Light/guidance passages geometrically proximate
- Semantic distance measured on manifold
- Non-obvious connections surfaced automatically

### Alternative Geometric Approaches

HUFD is one of potentially many geometric architectures:

1. **Hyperbolic Embeddings** (Poincaré, Lorentz)
   - Natural hierarchical structure
   - Proven for WordNet-style taxonomies
   - May suit Quranic conceptual hierarchies

2. **Graph Neural Networks**
   - Explicit relational structure
   - Message passing between concept nodes
   - Combines symbolic and geometric

3. **Geometric Deep Learning**
   - Operates on manifolds, graphs, meshes
   - Gauge equivariance for symmetry preservation
   - General framework for non-Euclidean data

4. **Hybrid Symbolic-Geometric**
   - Symbolic layer for discrete logic
   - Geometric layer for semantic distance
   - Best of both paradigms?

---

## Open Architectural Questions

### 1. HUFD vs Alternatives
Is HUFD the right architecture, or do hyperbolic embeddings / graph neural networks / hybrid approaches outperform?

### 2. Gauge Constraints
Can HUFD encode Quranic methodological principles (tartīb, intra-Quranic definition) as gauge-invariant constraints? Or must they be imposed externally?

### 3. Validation Emergence
Do validation stages (question → hypothesis → validation) emerge naturally from geodesic stability? Or must they be explicitly programmed?

### 4. Holonomy Claim
Is R_μν(ℋ_Qur) = 0 empirically defensible? Does it generalize beyond grammatical structure to semantic content?

### 5. Phenomenal Geometry
Does HUFD's geometric framework accurately describe phenomenal dynamics beyond linguistic structure? Can we test whether Quranic spatial metaphors correlate with actual phenomenal geometry?

### 6. Interpretability Trade-offs
Geometric architectures sacrifice interpretability for connection discovery. How do we maintain debuggability and user trust?

### 7. Edge Deployment Feasibility
Can geometric models run continuously on smartphones/smart glasses? What are quantization/optimization requirements?

---

## Implementation Strategy

### Phase 1: Maintain Static Schema (Current)
- Continue using SQLite for rapid prototyping
- Accumulate research claims and validation data
- Test MCP tool ergonomics
- Establish workflow patterns

### Phase 2: Comparative Evaluation (Future)
1. **Baseline Comparison**: Static schema vs keyword search
2. **Geometric Prototypes**: Implement HUFD, hyperbolic embeddings, GNN
3. **Hybrid Approaches**: Combine symbolic + geometric
4. **Metrics**: Connection discovery quality, validation prediction accuracy, user satisfaction

### Phase 3: Phenom

enal Testing (Future)
1. **Spatial Metaphor Correlation**: Do Quranic geometric terms map to actual phenomenal experience?
2. **Dayz Prediction**: Can geometric model predict when insights emerge in twilight consciousness?
3. **Angelic Guidance**: Does proper methodology create measurable geometric signatures in understanding?

### Phase 4: Edge Deployment (Future)
1. **Model Quantization**: Reduce to INT8/INT4 for mobile inference
2. **Smart Glasses Integration**: AR overlay for context-aware Quranic study
3. **Continuous Awareness**: Real-time insight capture and verification suggestions
4. **Offline-First**: No cloud dependency for privacy and latency

---

## Current Gaps and Enhancement Opportunities

### Gap 1: Concordance Verification
**Missing**: Automated exhaustive verification across all word instances
**Needed**: Tool to find all occurrences of root/pattern and batch-verify claim

### Gap 2: Coherence Checking
**Missing**: System-wide coherence validation
**Needed**: Detect when new claim contradicts existing high-certainty claim

### Gap 3: Distant Reference Detection
**Missing**: Automatic identification of non-adjacent verse references
**Needed**: Pattern recognition for structural features beyond linear sequence

### Gap 4: Morphology Integration
**Missing**: Seamless connection between linguistic features and claims
**Needed**: Query "claims about Form III verbs" and get relevant hypotheses

### Gap 5: Phenomenological Evidence
**Missing**: Category for experiential validation (dayz, dreams, spiritual experience)
**Needed**: Track when insights emerge and correlate with methodology adherence

### Gap 6: Temporal Tracking
**Missing**: Version history showing evolution of understanding over time
**Needed**: See how interpretation of a verse changed as research progressed

---

## Architectural Principles

### 1. Evidence Over Authority
Claims validated by Quranic text, not scholarly consensus. System should make evidence transparent and falsification easy.

### 2. Uncertainty Quantification
Every claim has phase (certainty level). System should never present hypothesis as validated fact.

### 3. Methodology Transparency
Why was a claim validated? What verses were checked? What counter-evidence was considered? Full audit trail.

### 4. Self-Correction
Previous claims can be overturned. System should make this easy, not shameful. Intellectual honesty as structural feature.

### 5. Connection Discovery
Most valuable insights come from non-obvious connections. Architecture must surface these.

### 6. Personal Tuning
Not generic encyclopedia - personal tadabbur assistant. Learns your patterns, suggests relevant passages.

### 7. Privacy First
Knowledge base deeply personal. No cloud dependency. All processing on-device.

---

## Future Directions

### Short-Term (Static Schema)
1. Implement concordance verification workflows
2. Add contradiction detection across claims
3. Improve morphology search with claim integration
4. Build temporal tracking for claim evolution

### Medium-Term (Hybrid Architecture)
1. Prototype geometric embeddings for connection discovery
2. Test hyperbolic space for Quranic concept hierarchies
3. Implement symbolic+geometric hybrid
4. Compare against static schema baseline

### Long-Term (Full Geometric System)
1. Deploy HUFD or winning architecture
2. Edge device optimization (smart glasses target)
3. Phenomenal geometry validation studies
4. Multi-user (post-validation of personal approach)

### Research Questions
1. Can geometric architecture predict which verses validate a claim?
2. Do validation phases emerge from geodesic stability?
3. Is Quranic spatial language describing actual semantic geometry?
4. Can we measure "closeness to truth" as curvature minimization?

---

## Related Documentation
- [METHODOLOGY.md](METHODOLOGY.md) - Research frameworks and validation approach
- [Kalima - Quranic Knowledge Interface.md](Kalima%20-%20Quranic%20Knowledge%20Interface.md) - Original vision paper
- [NCU Framework and Interpretation.md](NCU%20Framework%20and%20Interpretation.md) - Theoretical foundation

---

*Last Updated: 2026-02-08*
*Architecture actively evolving as research progresses*
