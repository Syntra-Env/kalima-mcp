# Kalima (كلمة)
### The Holonomic Manifold: HUFD Dynamics + UOR Identity

**Kalima** is a high-resolution Quranic research environment designed for the "Physics of Information" era. It is powered by two complementary frameworks: **Holonomic Unified Field Dynamics (HUFD)** and the **Universal Object Reference (UOR)** foundation.

Kalima treats the Quranic text as a **Holonomic Manifold** where meaning is governed by geometric laws. By mapping linguistic features to a gauge field and securing every entity with immutable content addresses, Kalima provides an objective geometric witness to the text's structure, protecting the researcher from projection and bias.

---

## 💎 The Dual Engines

### 1. HUFD (Holonomic Unified Field Dynamics)
**The Physics of Information Flow.**
HUFD models the text as an **su(2) gauge field**. It measures the "tension" and "curvature" of the linguistic sequence to identify semantic shifts and narrative boundaries.
- **Curvature ($R_{\mu\nu}$)**: Identifies where the meaning of a word "rotates" or evolves across different contexts.
- **Holonomy ($\oint H_\mu$)**: Tests for "Semantic Constants"—roots whose meaning remains invariant across the entire corpus.
- **Phase-Lock ($\Phi$)**: Measures the coupling between verses to detect speaker changes and temporal shifts.

### 2. UOR (Universal Object Reference)
**The Math of Information Identity.**
UOR provides the immutable substrate for the manifold. Every entity (Atom, Morpheme, Word, Verse) is assigned a unique content address derived from its internal structure.
- **Content Addressing**: Enables a strictly bottom-up composition.
- **Z/(2^256)Z Ring Arithmetic**: The foundational mathematical space where information identity is calculated.
- **Dihedral Symmetry**: Analyzes the "Dihedral Atoms" of information to find fundamental inversions and equivalences.

---

## ⚛️ Atomic Composition & Hierarchical Structure

In Kalima, the Quran is not viewed as a flat string of text, but as a hierarchical composition of **Information Atoms**.

1.  **Atoms (P1)**: The irreducible building blocks (Base Letters + Diacritics). Every single character in the Quranic text is an atom with a unique UOR identity.
2.  **Morphemes (P2)**: Compositions of Atoms. This level carries the primary linguistic features (Root, Lemma, POS, Gender, Number, Case, etc.).
3.  **Words (P3)**: Compositions of Morphemes (e.g., Prefix + Stem + Suffix).
4.  **Verses (P4)**: Compositions of Words in a specific sequence.
5.  **Surahs (P5)**: Compositions of Verses.
6.  **Corpus (P6)**: The complete Holonomic Manifold (6,236 Verses / ~77,000 Words).

This bottom-up architecture ensures that any change or insight at the atomic or morphemic level propagates mathematically through the entire manifold.

---

## 🏗️ Architecture & Data Layer

The project follows a strict **Math -> Bridge -> Tool** decoupling, supported by a dedicated data substrate.

### 📊 The Data Layer (`data/`)
- **`data/kalima.db`**: The primary SQLite substrate (Primary Manifold & Research Store).
- **Concurrency**: Operates in **WAL (Write-Ahead Logging)** mode to allow simultaneous transcription, math processing, and MCP querying.
- **Ingestion Sources**: Meeting transcripts, personal notes, and contemplations are processed into this layer to create a methodologically sound reference dataset.

### 1. The Math Layer (`src/math/`)
- **`gauge.py`**: Pure HUFD (su(2) Lie Algebra, Curvature, Holonomy).
- **`uor.py`**: Pure UOR (Ring Substrate, Dihedral generators, Fiber decomposition).
- **`root_space.py`**: Distributional Fingerprints (JS-Divergence, Centrality).
- **`verse_dynamics.py`**: Sequence analysis (Energy, Drift, Phase-Lock).

### 2. The Bridge (`src/math/bridge.py`)
The translator mapping Quranic features (Surprisal/Anomaly) to physical gauge components.

### 3. The Tool Layer (`src/tools/`)
The researcher's interface via the Model Context Protocol (MCP).

---

## 🛠️ MCP Tool Set (Exposed to LLM)

These are the specific tools available to the MCP Server for real-time research.

### 🌌 Physics & Dynamics
- `analyze_verse_emphasis`: Analyze which feature dimensions (Root, Anomaly, Position) carry meaning in a verse.
- `detect_boundaries`: Identify speaker changes, temporal shifts, and topic breaks in a passage.
- `measure_phase_lock`: Measure the mathematical coherence (coupling) between two specific verses.
- `compute_passage_drift`: Track morphological "gear shifts" (Energy) across a sequence.
- `measure_manifold_curvature`: HUFD $R_{\mu\nu}$ implementation: Measures local field tension at a word instance.
- `get_surah_topology`: Generates a high-fidelity topological map of a Surah's curvature.
- `compute_topology`: Compute topological Betti numbers for a set of UOR addresses.
- `compute_uor_index`: Apply the Index Theorem to determine manifold completeness.

### 🧪 Resonance & Comparison
- `compute_root_resonance`: Measures if a root is **Universal** (Flat) or **Contextual** (Twisted).
- `verify_root_concordance`: Ranks all instances by **Tension** to find potential falsifiers of a meaning.
- `compare_with_traditional`: Side-by-side comparison of Kalima research vs traditional interpretations.
- `root_distance`: Calculates the **Geodesic Distance** between roots in the manifold.

### 💎 Identity & Navigation
- `resolve_address`: The "Universal Key" to unlock any entity's metadata via its UOR address.
- `get_composition`: Explodes an address into its constituent sub-components (Bottom-Up).
- `decompose_fibers`: Explodes an address into its underlying binary fiber components.
- `classify_uor_partition`: Identifies the ontological partition (Irreducible, Reducible, Unit, Exterior).
- `locate_identity`: Finds all Quranic locations where a specific content address manifests.
- `get_verse_lattice`: Views a verse as a lattice of UOR addresses.
- `get_verse_with_context`: Fetches verse text with full morphological features and related research.
- `get_feature_context`: Finds other instances and entries related to a specific linguistic feature.

### 🖋️ Research & Verification
- `dock_claim_tool`: Anchors a research insight to an immutable UOR address.
- `search_research`: Search for existing claims docked in the manifold.
- `get_entry_details`: Fetch full metadata and verification status for an entry.
- `classify_monodromy`: Detects interpretive "twists" (FlatType vs TwistedType).
- `resolve_research_completeness`: Determines if a research set satisfies the UOR Index Theorem.
- `measure_verification_convergence`: Tracks how close an interpretation is to full corpus verification.
- `start_verification`: Initializes a systematic verification session for a claim.
- `continue_verification`: Advances to the next instance in the verification queue.
- `submit_verification`: Commits a verification result for a specific instance.

---

## 🔄 Research Workflow

The Kalima research workflow is an iterative, non-linear process designed to build a methodologically sound foundation for Quranic understanding.

1.  **Ingest**: Gather raw insights from research meetings, personal transcriptions, and contemplation notes. This feeds the system with high-quality examples of organic methodology.
2.  **Dock**: Anchor these initial insights to immutable **UOR** addresses. This locks the claim to the physical text, not just a subjective reference.
3.  **Analyze**: Use **HUFD** tools (Resonance, Curvature, Phase-Lock) to test the mathematical validity of the claim. Insights often emerge non-linearly while using the tools to explore the manifold.
4.  **Verify**: Systematically run the claim against the entire corpus. A meaning must hold across all instances (surviving falsification) to be considered stable.
5.  **Refine**: Use the results to refine the hypothesis or discover new "twisted" meanings that require deeper gauge analysis.

**Goal**: The ultimate purpose of this ingestion and verification is to create a high-fidelity reference dataset that can be used to test, compare, and eventually train Machine Learning models to understand the organic geometric structure of the Quran.

---

## 📚 Theoretical References
- **HUFD Framework**: Holonomic Unified Field Dynamics (Harlow/Charlton, 2026).
- **UOR Foundation**: Universal Object Reference (Content Addressing via SHA-256).
- **Information Geometry**: Application of Fisher Information Metrics to linguistic features.
- **Marvelous Quran**: Organic Quranic Methodology and Abrahamic Locution
