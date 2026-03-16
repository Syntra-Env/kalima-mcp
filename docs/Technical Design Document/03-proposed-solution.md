---
title: UOR v3.5.0 (The Prime Framework)
prev_title: Goals
prev_url: 02-goals.html
next_title: Alternatives
next_url: 04-alternatives.html
---

Syntra aligns with **UOR v3.5.0**, implementing the **Prime Framework** for universal number representation. This ensures **Observer Invariance** and **Geometric Consistency** by encoding all information through complete prime factorization.

## Universal Coordinate Projection

Content is projected onto the triadic UOR manifold using prime-factorized Universal Numbers. Similarity is measured via **Geometric Congruence** across prime spectra.

```python
c1 = uor.triality.project_coordinate("Hello world")
c2 = uor.triality.project_coordinate("Goodbye world")

# Coordinates are now stored as {prime: exponent} factorizations
print("Coord 1 (Extension):", c1['extension'])
print("Coord 2 (Extension):", c2['extension'])
print()
resonance = uor.triality.compute_resonance(c1, c2)
print(f"Universal Resonance Fidelity: {resonance:.4f}")
```

## Holonomic Field — Prime Congruence

The **Holonomic Field** utilizes prime factorization to compute observer-invariant congruence. **Semantic Tension** measures local curvature within the prime-factorized semantic lattice.

```python
dataset_raw = [
  "artificial intelligence", "machine learning",
  "deep neural network", "cooking recipe"
]
manifold_points = [{ 'label': s, 'coordinate': uor.triality.project_coordinate(s) } for s in dataset_raw]

query = uor.triality.project_coordinate("neural network training")
neighbors = uor.field.manifold_proximity(query, manifold_points, 3)

print("Manifold Proximity (Prime-Aware):")
for n in neighbors:
    print(f"  {n['item']['label']} -> {n['score']:.3f}")
```

## Gauge Stability & Topology

The topology module assesses **Gauge Stability** by measuring resonance fidelity across edges, ensuring mathematical consistency across the manifold.

```python
topology = uor.topology.build_topology(
  [
    { 'id': "n1", 'label': "Source A" },
    { 'id': "n2", 'label': "Target B" }
  ],
  [
    { 'from': "n1", 'to': "n2", 'relation': "functor" }
  ]
)

stability = uor.topology.assess_gauge_stability(topology)
print(f"Topology Gauge Stability: {stability['resonance_fidelity']:.4f}")
```
