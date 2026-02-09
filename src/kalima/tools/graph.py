"""Graph analysis tools: coherence, contradictions, centrality, clusters.

Uses NetworkX to build a graph from claims, evidence, and dependencies.
Graph is lazily built on first call and cached; invalidated on writes.
"""

import networkx as nx
from mcp.server.fastmcp import FastMCP

from ..db import get_connection, set_graph_invalidation_callback

mcp: FastMCP

# Cached graph
_graph: nx.DiGraph | None = None


def _invalidate_cache():
    global _graph
    _graph = None


def _build_graph() -> nx.DiGraph:
    """Build a directed graph from claims, evidence, and dependencies."""
    global _graph
    if _graph is not None:
        return _graph

    conn = get_connection()
    G = nx.DiGraph()

    # Add claim nodes
    claims = conn.execute("SELECT id, content, phase, pattern_id FROM claims").fetchall()
    for c in claims:
        G.add_node(c['id'], type='claim', content=c['content'], phase=c['phase'], pattern_id=c['pattern_id'])

    # Add verse nodes and evidence edges
    evidence = conn.execute("SELECT claim_id, surah, ayah, notes FROM claim_evidence").fetchall()
    for e in evidence:
        verse_id = f"v:{e['surah']}:{e['ayah']}"
        if not G.has_node(verse_id):
            G.add_node(verse_id, type='verse', surah=e['surah'], ayah=e['ayah'])
        G.add_edge(e['claim_id'], verse_id, relation='evidence', notes=e['notes'])

    # Add verse_evidence edges (from workflow verification)
    ve = conn.execute("SELECT claim_id, verse_surah, verse_ayah, verification, notes FROM verse_evidence").fetchall()
    for v in ve:
        verse_id = f"v:{v['verse_surah']}:{v['verse_ayah']}"
        if not G.has_node(verse_id):
            G.add_node(verse_id, type='verse', surah=v['verse_surah'], ayah=v['verse_ayah'])
        G.add_edge(v['claim_id'], verse_id, relation='verification', verification=v['verification'], notes=v['notes'])

    # Add dependency edges between claims
    deps = conn.execute("SELECT claim_id, depends_on_claim_id, dependency_type FROM claim_dependencies").fetchall()
    for d in deps:
        G.add_edge(d['claim_id'], d['depends_on_claim_id'], relation=d['dependency_type'])

    # Add pattern edges
    patterns = conn.execute("SELECT id FROM patterns").fetchall()
    for p in patterns:
        pid = p['id']
        G.add_node(pid, type='pattern')
        # Link claims to their patterns
        linked = conn.execute("SELECT id FROM claims WHERE pattern_id = ?", (pid,)).fetchall()
        for lc in linked:
            G.add_edge(lc['id'], pid, relation='belongs_to_pattern')

    _graph = G
    return G


def register(server: FastMCP):
    global mcp
    mcp = server

    # Register cache invalidation
    set_graph_invalidation_callback(_invalidate_cache)

    @mcp.tool()
    def analyze_coherence() -> dict:
        """Compute a composite coherence score (0.0–1.0) for the research knowledge base.

        Measures how well-connected and internally consistent the claims are.
        Components: connected components ratio, isolated claims ratio, clustering coefficient, graph density.
        """
        G = _build_graph()

        # Work with claim-only subgraph for meaningful metrics
        claim_nodes = [n for n, d in G.nodes(data=True) if d.get('type') == 'claim']
        if not claim_nodes:
            return {"coherence_score": 0.0, "components": {}, "interpretation": "No claims in database"}

        total_claims = len(claim_nodes)

        # Build undirected claim-relationship graph
        CG = nx.Graph()
        CG.add_nodes_from(claim_nodes)

        # Connect claims that share verse evidence
        verse_to_claims: dict[str, list[str]] = {}
        for n, d in G.nodes(data=True):
            if d.get('type') == 'verse':
                connected_claims = [pred for pred in G.predecessors(n) if G.nodes[pred].get('type') == 'claim']
                if len(connected_claims) > 1:
                    verse_to_claims[n] = connected_claims
                    for i, c1 in enumerate(connected_claims):
                        for c2 in connected_claims[i+1:]:
                            CG.add_edge(c1, c2, relation='shared_evidence')

        # Connect claims via direct dependencies
        for u, v, d in G.edges(data=True):
            if d.get('relation') in ('depends_on', 'supports', 'contradicts', 'refines', 'related'):
                if G.nodes.get(u, {}).get('type') == 'claim' and G.nodes.get(v, {}).get('type') == 'claim':
                    CG.add_edge(u, v, relation=d['relation'])

        # Connect claims via shared pattern
        for n, d in G.nodes(data=True):
            if d.get('type') == 'pattern':
                pattern_claims = [pred for pred in G.predecessors(n) if G.nodes[pred].get('type') == 'claim']
                for i, c1 in enumerate(pattern_claims):
                    for c2 in pattern_claims[i+1:]:
                        CG.add_edge(c1, c2, relation='same_pattern')

        # Metrics
        components = list(nx.connected_components(CG))
        num_components = len(components)
        largest_component_size = max(len(c) for c in components) if components else 0

        isolated = len(list(nx.isolates(CG)))
        isolation_ratio = isolated / total_claims if total_claims > 0 else 1.0

        clustering = nx.average_clustering(CG) if CG.number_of_edges() > 0 else 0.0
        density = nx.density(CG)

        # Composite score (weighted)
        connectivity_score = largest_component_size / total_claims if total_claims > 0 else 0.0
        non_isolation_score = 1.0 - isolation_ratio
        coherence_score = round(
            0.35 * connectivity_score +
            0.30 * non_isolation_score +
            0.20 * clustering +
            0.15 * min(density * 10, 1.0),  # Scale density up since it's typically very small
            3
        )

        # Interpretation
        if coherence_score >= 0.7:
            interp = "High coherence: claims are well-connected through shared evidence and dependencies"
        elif coherence_score >= 0.4:
            interp = "Moderate coherence: some clusters exist but many claims are isolated"
        else:
            interp = "Low coherence: most claims are disconnected; consider adding evidence links and dependencies"

        return {
            "coherence_score": coherence_score,
            "components": {
                "connectivity_score": round(connectivity_score, 3),
                "non_isolation_score": round(non_isolation_score, 3),
                "clustering_coefficient": round(clustering, 3),
                "density": round(density, 5),
                "num_connected_components": num_components,
                "largest_component_size": largest_component_size,
                "isolated_claims": isolated,
                "total_claims": total_claims,
            },
            "interpretation": interp,
        }

    @mcp.tool()
    def find_contradictions() -> dict:
        """Find contradictions in the research knowledge base.

        Two sources:
        1. Explicit "contradicts" dependency edges
        2. Implicit contradictions: same verse with opposing verification statuses
        """
        G = _build_graph()
        conn = get_connection()

        # 1. Explicit contradictions
        explicit = []
        for u, v, d in G.edges(data=True):
            if d.get('relation') == 'contradicts':
                u_data = G.nodes.get(u, {})
                v_data = G.nodes.get(v, {})
                explicit.append({
                    "claim_1": {"id": u, "content": u_data.get('content', ''), "phase": u_data.get('phase', '')},
                    "claim_2": {"id": v, "content": v_data.get('content', ''), "phase": v_data.get('phase', '')},
                    "type": "explicit",
                })

        # 2. Implicit contradictions (same verse, opposing verifications)
        implicit = []
        verse_verifications: dict[str, list[dict]] = {}

        for u, v, d in G.edges(data=True):
            if d.get('relation') == 'verification' and G.nodes.get(v, {}).get('type') == 'verse':
                vid = v
                if vid not in verse_verifications:
                    verse_verifications[vid] = []
                verse_verifications[vid].append({
                    "claim_id": u,
                    "verification": d.get('verification'),
                })

        for vid, verifs in verse_verifications.items():
            supports = [v for v in verifs if v['verification'] == 'supports']
            contradicts = [v for v in verifs if v['verification'] == 'contradicts']

            if supports and contradicts:
                verse_node = G.nodes[vid]
                for s in supports:
                    for c in contradicts:
                        s_data = G.nodes.get(s['claim_id'], {})
                        c_data = G.nodes.get(c['claim_id'], {})
                        implicit.append({
                            "claim_supports": {"id": s['claim_id'], "content": s_data.get('content', '')},
                            "claim_contradicts": {"id": c['claim_id'], "content": c_data.get('content', '')},
                            "verse": {"surah": verse_node.get('surah'), "ayah": verse_node.get('ayah')},
                            "type": "implicit",
                        })

        return {
            "explicit_contradictions": explicit,
            "implicit_contradictions": implicit,
            "total": len(explicit) + len(implicit),
        }

    @mcp.tool()
    def compute_centrality(metric: str = "degree", top_n: int = 20) -> list[dict]:
        """Compute centrality metrics on claims to find the most important/connected ones.

        Metrics: degree, betweenness, pagerank, eigenvector.
        """
        G = _build_graph()

        # Build claim-only graph
        claim_nodes = [n for n, d in G.nodes(data=True) if d.get('type') == 'claim']
        if not claim_nodes:
            return []

        CG = G.subgraph(claim_nodes + [n for n, d in G.nodes(data=True) if d.get('type') == 'verse']).copy()

        if metric == "degree":
            scores = nx.degree_centrality(CG)
        elif metric == "betweenness":
            scores = nx.betweenness_centrality(CG)
        elif metric == "pagerank":
            scores = nx.pagerank(CG)
        elif metric == "eigenvector":
            try:
                scores = nx.eigenvector_centrality(CG, max_iter=1000)
            except nx.PowerIterationFailedConvergence:
                scores = nx.eigenvector_centrality_numpy(CG)
        else:
            return [{"error": f"Unknown metric: {metric}. Use: degree, betweenness, pagerank, eigenvector"}]

        # Filter to claim nodes only and sort
        claim_scores = [(n, s) for n, s in scores.items() if G.nodes.get(n, {}).get('type') == 'claim']
        claim_scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for node_id, score in claim_scores[:top_n]:
            data = G.nodes[node_id]
            results.append({
                "claim_id": node_id,
                "content": data.get('content', ''),
                "phase": data.get('phase', ''),
                "score": round(score, 5),
            })

        return results

    @mcp.tool()
    def find_clusters(algorithm: str = "louvain") -> dict:
        """Find clusters (communities) of related claims.

        Algorithms: louvain, label_propagation, greedy_modularity.
        """
        G = _build_graph()

        # Build undirected claim graph
        claim_nodes = [n for n, d in G.nodes(data=True) if d.get('type') == 'claim']
        if not claim_nodes:
            return {"clusters": [], "total_clusters": 0}

        CG = nx.Graph()
        CG.add_nodes_from(claim_nodes)

        # Add edges from shared evidence
        for n, d in G.nodes(data=True):
            if d.get('type') == 'verse':
                connected = [pred for pred in G.predecessors(n) if G.nodes[pred].get('type') == 'claim']
                for i, c1 in enumerate(connected):
                    for c2 in connected[i+1:]:
                        CG.add_edge(c1, c2)

        # Add dependency edges
        for u, v, d in G.edges(data=True):
            if d.get('relation') in ('depends_on', 'supports', 'refines', 'related'):
                if G.nodes.get(u, {}).get('type') == 'claim' and G.nodes.get(v, {}).get('type') == 'claim':
                    CG.add_edge(u, v)

        # Add pattern edges
        for n, d in G.nodes(data=True):
            if d.get('type') == 'pattern':
                pattern_claims = [pred for pred in G.predecessors(n) if G.nodes[pred].get('type') == 'claim']
                for i, c1 in enumerate(pattern_claims):
                    for c2 in pattern_claims[i+1:]:
                        CG.add_edge(c1, c2)

        # Run community detection
        if algorithm == "louvain":
            communities = nx.community.louvain_communities(CG)
        elif algorithm == "label_propagation":
            communities = list(nx.community.label_propagation_communities(CG))
        elif algorithm == "greedy_modularity":
            communities = list(nx.community.greedy_modularity_communities(CG))
        else:
            return {"error": f"Unknown algorithm: {algorithm}. Use: louvain, label_propagation, greedy_modularity"}

        clusters = []
        for i, community in enumerate(sorted(communities, key=len, reverse=True)):
            members = []
            patterns_in_cluster = set()
            for cid in community:
                data = G.nodes.get(cid, {})
                members.append({
                    "claim_id": cid,
                    "content": data.get('content', ''),
                    "phase": data.get('phase', ''),
                })
                if data.get('pattern_id'):
                    patterns_in_cluster.add(data['pattern_id'])

            clusters.append({
                "cluster_id": i,
                "size": len(members),
                "members": members,
                "common_patterns": list(patterns_in_cluster),
            })

        return {"clusters": clusters, "total_clusters": len(clusters)}

    @mcp.tool()
    def suggest_validation_order(phase_filter: str | None = None) -> list[dict]:
        """Suggest the order in which claims should be validated.

        Uses topological sort of dependency graph: claims that others depend on
        should be validated first. Centrality used as tiebreaker.
        """
        G = _build_graph()

        # Build dependency-only subgraph
        DG = nx.DiGraph()
        claim_nodes = [n for n, d in G.nodes(data=True) if d.get('type') == 'claim']

        if phase_filter:
            claim_nodes = [n for n in claim_nodes if G.nodes[n].get('phase') == phase_filter]

        DG.add_nodes_from(claim_nodes)

        for u, v, d in G.edges(data=True):
            if d.get('relation') == 'depends_on' and u in DG and v in DG:
                DG.add_edge(u, v)

        # Compute centrality for tiebreaking
        centrality = nx.degree_centrality(G.subgraph(claim_nodes)) if claim_nodes else {}

        # Topological sort (handle cycles gracefully)
        try:
            topo_order = list(nx.topological_sort(DG))
            # Reverse: dependencies first
            topo_order.reverse()
        except nx.NetworkXUnfeasible:
            # Has cycles — fall back to centrality ordering
            topo_order = sorted(claim_nodes, key=lambda n: centrality.get(n, 0), reverse=True)

        results = []
        for i, node_id in enumerate(topo_order):
            data = G.nodes.get(node_id, {})
            dependents = list(DG.predecessors(node_id))  # claims that depend on this one
            results.append({
                "priority": i + 1,
                "claim_id": node_id,
                "content": data.get('content', ''),
                "phase": data.get('phase', ''),
                "centrality": round(centrality.get(node_id, 0), 5),
                "depended_on_by": len(dependents),
            })

        return results

    @mcp.tool()
    def detect_circular_dependencies() -> dict:
        """Detect circular dependencies (cycles) in the claim dependency graph.

        Flags circular reasoning that should be resolved.
        """
        G = _build_graph()

        # Build dependency-only directed graph
        DG = nx.DiGraph()
        for u, v, d in G.edges(data=True):
            if d.get('relation') == 'depends_on':
                if G.nodes.get(u, {}).get('type') == 'claim' and G.nodes.get(v, {}).get('type') == 'claim':
                    DG.add_edge(u, v)

        cycles = list(nx.simple_cycles(DG))

        cycle_details = []
        for cycle in cycles:
            members = []
            for cid in cycle:
                data = G.nodes.get(cid, {})
                members.append({
                    "claim_id": cid,
                    "content": data.get('content', ''),
                })
            cycle_details.append({
                "length": len(cycle),
                "claims": members,
                "cycle_path": " → ".join(cycle) + f" → {cycle[0]}",
            })

        return {
            "has_cycles": len(cycles) > 0,
            "total_cycles": len(cycles),
            "cycles": cycle_details,
        }
