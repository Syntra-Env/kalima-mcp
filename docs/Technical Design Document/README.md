# Syntra

*Towards Free Agency for All.*

Syntra explores how to make personal AI agency universally accessible — lightweight agents that run on edge devices, protect users from psychological manipulation, and provide proactive guidance without being intrusive.

## Core Ideas

- **Edge-first agents** — fast, local models that run on consumer hardware without cloud dependency.
- **Manipulation defense** — agents that identify and shield users from dark patterns, deceptive design, and persuasion techniques.
- **Proactive but respectful** — useful guidance that surfaces at the right time without becoming noise.
- **Python-based Logic** — The core engine (`humOS`) is implemented in Python and runs directly in the browser via Pyodide.

## Project Structure

- `humos.py`: The core Universal Information Geometry Library.
- `cell-src.js`: Source for the interactive code execution environment (Python REPL).
- `cell.js`: Bundled and minified execution engine.
- `*.html`: TDD documentation and interactive playgrounds.

## Interactive Demos

The documentation includes interactive Python cells where you can run `humOS` code directly.
- **PRISM**: Content addressing and similarity.
- **Field Math**: Manifold operations and clustering.
- **Graph Analysis**: Articulation points, pathologies, and health metrics.
- **HUFD**: Holonomic Unified Field Dynamics and coherence tracking.

## Local Development

To run the site locally:

```bash
python -m http.server 8080
```

Then visit `http://localhost:8080`.

Hosted on GitHub Pages from `master`. The `.nojekyll` file ensures Python and other assets are served correctly.
