# Kalima (كلمة)

A high-resolution Quranic research environment powered by **Holonomic Unified Field Dynamics (HUFD)** and **Universal Object Reference (UOR)**.

Kalima treats the Quranic text as a **Holonomic Manifold** where meaning is governed by geometric laws. Every entity is secured with immutable content addresses, providing an objective geometric witness to the text's structure.

---

## Overview

| Layer | Purpose |
|-------|---------|
| **HUFD** | Models text as an su(2) gauge field. Measures curvature, holonomy, and phase-lock to detect semantic shifts. |
| **UOR** | Assigns SHA-256 content addresses to every entity (Atom → Morpheme → Word → Verse). |

### Core Capabilities

- **Semantic Curvature**: Identify where word meanings rotate across contexts
- **Holonomic Testing**: Verify if a root maintains invariant meaning across the corpus
- **Phase-Lock Analysis**: Detect speaker changes and temporal shifts between verses
- **Content Addressing**: Bottom-up composition with cryptographic identity guarantees

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from src.db import init_db; init_db()"

# Start MCP server
python -m src.mcp
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP Tool Layer                          │
│  (Research Interface for LLMs)                            │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Bridge Layer                          │
│  src/math/bridge.py — Feature → Gauge Mapping             │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                       Math Layer                           │
│  gauge.py    │  uor.py    │  root_space.py  │  verse_... │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                            │
│  kalima.db (SQLite + WAL mode)                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Mathematical Foundations

### HUFD: The Physics of Information Flow

- **Curvature** ($R_{\mu\nu}$): Measures semantic rotation of words across contexts
- **Holonomy** ($\oint H_\mu$): Tests for semantic constants—roots with invariant meaning
- **Phase-Lock** ($\Phi$): Coupling metric between verses for boundary detection

### UOR: The Math of Identity

- **Content Addressing**: SHA-256 addresses derived from internal structure
- **Ring Substrate**: $\mathbb{Z}/(2^{256})\mathbb{Z}$ arithmetic
- **Dihedral Symmetry**: Analyzing fundamental inversions

---

## MCP Tools

### Physics & Dynamics
| Tool | Description |
|------|-------------|
| `analyze_verse_emphasis` | Feature dimensions carrying meaning |
| `detect_boundaries` | Speaker/temporal shifts in passage |
| `measure_phase_lock` | Coupling between verses |
| `compute_passage_drift` | Energy across sequence |
| `measure_manifold_curvature` | Local field tension |
| `get_surah_topology` | Topological map of Surah |

### Resonance & Comparison
| Tool | Description |
|------|-------------|
| `compute_root_resonance` | Universal (Flat) vs Contextual (Twisted) |
| `verify_root_concordance` | Rank instances by tension |
| `compare_with_traditional` | vs classical tafsir |
| `root_distance` | Geodesic distance between roots |

### Identity & Navigation
| Tool | Description |
|------|-------------|
| `resolve_address` | Universal Key for any entity |
| `get_composition` | Bottom-up decomposition |
| `decompose_fibers` | Binary fiber explosion |
| `locate_identity` | Find all manifestations |

---

## Research Workflow

1. **Dock** — Anchor insights to immutable UOR addresses
2. **Analyze** — Test mathematical validity via HUFD
3. **Verify** — Run claim against entire corpus
4. **Refine** — Discover twisted meanings requiring deeper analysis

---

## Data Sources

- **Quran Text**: Tanzil Project (Uthmani)
- **Morphology**: Quranic Arabic Corpus + MASAQ
- **Translations**: Sahih International

---

## References

- HUFD Framework — Harlow/Charlton (2026)
- UOR Foundation — SHA-256 Content Addressing
- Information Geometry — Fisher Information Metrics
- Marvelous Quran — Organic Methodology

---

## License

MIT License — See LICENSE file

---

## Documentation

The full documentation with properly rendered mathematics is available in the `docs/` folder:

### Research Reports
- [Kalima Mathematical Framework](docs/Kalima%20Mathematical%20Framework.html)
- [Limits of the Mathematics](docs/Limits%20of%20the%20Mathematics.html)

### User Interface Design
- [Search-Write Juxtaposition](docs/search-write-juxtaposition.html)
- [Text Substitution Design Pattern](docs/text-substitution-design-pattern.html)
- [Interpretation Verification](docs/interpretation-verification.html)

### Technical Design Documents
- [Technical Design Document Index](docs/Technical%20Design%20Document/index.html)
- [Syntra Core Context and Goals](docs/Technical%20Design%20Document/syntra-core-context-and-goals.html)
- [Syntra Technical Implementation](docs/Technical%20Design%20Document/syntra-technical-implementation.html)
- [Syntra Ecosystem Overview](docs/Technical%20Design%20Document/syntra-ecosystem-overview.html)
