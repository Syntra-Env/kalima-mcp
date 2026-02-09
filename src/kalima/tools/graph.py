"""Graph analysis tools: coherence, contradictions, centrality, clusters, rendering.

Uses NetworkX to build a graph from entries, evidence, and dependencies.
Graph is lazily built on first call and cached; invalidated on writes.
"""

from pathlib import Path

import networkx as nx
from mcp.server.fastmcp import FastMCP

from ..db import get_connection, set_graph_invalidation_callback

mcp: FastMCP

# Cached graph
_graph: nx.DiGraph | None = None
_render_stale: bool = True  # True when graph data changed since last render


def _invalidate_cache():
    global _graph, _render_stale
    _graph = None
    _render_stale = True


def _build_graph() -> nx.DiGraph:
    """Build a directed graph from entries, evidence, and dependencies."""
    global _graph
    if _graph is not None:
        return _graph

    conn = get_connection()
    G = nx.DiGraph()

    # Add entry nodes
    entries = conn.execute("SELECT id, content, phase FROM entries").fetchall()
    for e in entries:
        G.add_node(e['id'], type='entry', content=e['content'], phase=e['phase'])

    # Add verse nodes from verse-scoped entries, linked to their parents
    verse_entries = conn.execute(
        """SELECT e.id, e.content, e.scope_value,
                  ed.depends_on_entry_id as parent_id, ed.dependency_type
           FROM entries e
           LEFT JOIN entry_dependencies ed ON ed.entry_id = e.id
           WHERE e.scope_type = 'verse' AND e.scope_value IS NOT NULL"""
    ).fetchall()
    for ve in verse_entries:
        parts = ve['scope_value'].split(':')
        if len(parts) == 2:
            surah, ayah = int(parts[0]), int(parts[1])
            verse_id = f"v:{surah}:{ayah}"
            if not G.has_node(verse_id):
                G.add_node(verse_id, type='verse', surah=surah, ayah=ayah)
            # Edge from parent entry to verse node
            if ve['parent_id'] and G.has_node(ve['parent_id']):
                dep_type = ve['dependency_type'] or 'related'
                if dep_type in ('supports', 'contradicts'):
                    G.add_edge(ve['parent_id'], verse_id, relation='verification',
                               verification=dep_type, notes=ve['content'])
                else:
                    G.add_edge(ve['parent_id'], verse_id, relation='evidence', notes=ve['content'])

    # Add dependency edges between entries
    deps = conn.execute("SELECT entry_id, depends_on_entry_id, dependency_type FROM entry_dependencies").fetchall()
    for d in deps:
        G.add_edge(d['entry_id'], d['depends_on_entry_id'], relation=d['dependency_type'])

    # Add scope-based edges: connect entries sharing the same scope
    scope_rows = conn.execute(
        """SELECT e1.id as e1, e2.id as e2, e1.scope_type, e1.scope_value
           FROM entries e1
           JOIN entries e2 ON e1.scope_type = e2.scope_type
             AND e1.scope_value = e2.scope_value
             AND e1.id < e2.id
           WHERE e1.scope_type IS NOT NULL"""
    ).fetchall()
    for s in scope_rows:
        G.add_edge(s['e1'], s['e2'], relation='shared_scope', scope_type=s['scope_type'], scope_value=s['scope_value'])

    _graph = G
    return G


def register(server: FastMCP):
    global mcp
    mcp = server

    # Register cache invalidation
    set_graph_invalidation_callback(_invalidate_cache)

    @mcp.tool()
    def analyze_coherence() -> dict:
        """Compute a composite coherence score (0.0-1.0) for the research knowledge base.

        Measures how well-connected and internally consistent the entries are.
        Components: connected components ratio, isolated entries ratio, clustering coefficient, graph density.
        """
        G = _build_graph()

        # Work with entry-only subgraph for meaningful metrics
        entry_nodes = [n for n, d in G.nodes(data=True) if d.get('type') == 'entry']
        if not entry_nodes:
            return {"coherence_score": 0.0, "components": {}, "interpretation": "No entries in database"}

        total_entries = len(entry_nodes)

        # Build undirected entry-relationship graph
        CG = nx.Graph()
        CG.add_nodes_from(entry_nodes)

        # Connect entries that share verse evidence
        verse_to_entries: dict[str, list[str]] = {}
        for n, d in G.nodes(data=True):
            if d.get('type') == 'verse':
                connected_entries = [pred for pred in G.predecessors(n) if G.nodes[pred].get('type') == 'entry']
                if len(connected_entries) > 1:
                    verse_to_entries[n] = connected_entries
                    for i, e1 in enumerate(connected_entries):
                        for e2 in connected_entries[i+1:]:
                            CG.add_edge(e1, e2, relation='shared_evidence')

        # Connect entries via direct dependencies
        for u, v, d in G.edges(data=True):
            if d.get('relation') in ('depends_on', 'supports', 'contradicts', 'refines', 'related'):
                if G.nodes.get(u, {}).get('type') == 'entry' and G.nodes.get(v, {}).get('type') == 'entry':
                    CG.add_edge(u, v, relation=d['relation'])

        # Connect entries via shared terms
        for u, v, d in G.edges(data=True):
            if d.get('relation') == 'shared_scope':
                if G.nodes.get(u, {}).get('type') == 'entry' and G.nodes.get(v, {}).get('type') == 'entry':
                    CG.add_edge(u, v, relation='shared_scope')

        # Metrics
        components = list(nx.connected_components(CG))
        num_components = len(components)
        largest_component_size = max(len(c) for c in components) if components else 0

        isolated = len(list(nx.isolates(CG)))
        isolation_ratio = isolated / total_entries if total_entries > 0 else 1.0

        clustering = nx.average_clustering(CG) if CG.number_of_edges() > 0 else 0.0
        density = nx.density(CG)

        # Composite score (weighted)
        connectivity_score = largest_component_size / total_entries if total_entries > 0 else 0.0
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
            interp = "High coherence: entries are well-connected through shared evidence and dependencies"
        elif coherence_score >= 0.4:
            interp = "Moderate coherence: some clusters exist but many entries are isolated"
        else:
            interp = "Low coherence: most entries are disconnected; consider adding evidence links and dependencies"

        return {
            "coherence_score": coherence_score,
            "components": {
                "connectivity_score": round(connectivity_score, 3),
                "non_isolation_score": round(non_isolation_score, 3),
                "clustering_coefficient": round(clustering, 3),
                "density": round(density, 5),
                "num_connected_components": num_components,
                "largest_component_size": largest_component_size,
                "isolated_entries": isolated,
                "total_entries": total_entries,
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
                    "entry_1": {"id": u, "content": u_data.get('content', ''), "phase": u_data.get('phase', '')},
                    "entry_2": {"id": v, "content": v_data.get('content', ''), "phase": v_data.get('phase', '')},
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
                    "entry_id": u,
                    "verification": d.get('verification'),
                })

        for vid, verifs in verse_verifications.items():
            supports = [v for v in verifs if v['verification'] == 'supports']
            contradicts_list = [v for v in verifs if v['verification'] == 'contradicts']

            if supports and contradicts_list:
                verse_node = G.nodes[vid]
                for s in supports:
                    for c in contradicts_list:
                        s_data = G.nodes.get(s['entry_id'], {})
                        c_data = G.nodes.get(c['entry_id'], {})
                        implicit.append({
                            "entry_supports": {"id": s['entry_id'], "content": s_data.get('content', '')},
                            "entry_contradicts": {"id": c['entry_id'], "content": c_data.get('content', '')},
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
        """Compute centrality metrics on entries to find the most important/connected ones.

        Metrics: degree, betweenness, pagerank, eigenvector.
        """
        G = _build_graph()

        # Build entry-only graph
        entry_nodes = [n for n, d in G.nodes(data=True) if d.get('type') == 'entry']
        if not entry_nodes:
            return []

        CG = G.subgraph(entry_nodes + [n for n, d in G.nodes(data=True) if d.get('type') == 'verse']).copy()

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

        # Filter to entry nodes only and sort
        entry_scores = [(n, s) for n, s in scores.items() if G.nodes.get(n, {}).get('type') == 'entry']
        entry_scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for node_id, score in entry_scores[:top_n]:
            data = G.nodes[node_id]
            results.append({
                "entry_id": node_id,
                "content": data.get('content', ''),
                "phase": data.get('phase', ''),
                "score": round(score, 5),
            })

        return results

    @mcp.tool()
    def find_clusters(algorithm: str = "louvain") -> dict:
        """Find clusters (communities) of related entries.

        Algorithms: louvain, label_propagation, greedy_modularity.
        """
        G = _build_graph()

        # Build undirected entry graph
        entry_nodes = [n for n, d in G.nodes(data=True) if d.get('type') == 'entry']
        if not entry_nodes:
            return {"clusters": [], "total_clusters": 0}

        CG = nx.Graph()
        CG.add_nodes_from(entry_nodes)

        # Add edges from shared evidence
        for n, d in G.nodes(data=True):
            if d.get('type') == 'verse':
                connected = [pred for pred in G.predecessors(n) if G.nodes[pred].get('type') == 'entry']
                for i, e1 in enumerate(connected):
                    for e2 in connected[i+1:]:
                        CG.add_edge(e1, e2)

        # Add dependency edges
        for u, v, d in G.edges(data=True):
            if d.get('relation') in ('depends_on', 'supports', 'refines', 'related'):
                if G.nodes.get(u, {}).get('type') == 'entry' and G.nodes.get(v, {}).get('type') == 'entry':
                    CG.add_edge(u, v)

        # Add shared term edges
        for u, v, d in G.edges(data=True):
            if d.get('relation') == 'shared_scope':
                if u in CG and v in CG:
                    CG.add_edge(u, v)

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
            for eid in community:
                data = G.nodes.get(eid, {})
                members.append({
                    "entry_id": eid,
                    "content": data.get('content', ''),
                    "phase": data.get('phase', ''),
                })

            clusters.append({
                "cluster_id": i,
                "size": len(members),
                "members": members,
            })

        return {"clusters": clusters, "total_clusters": len(clusters)}

    @mcp.tool()
    def suggest_validation_order(phase_filter: str | None = None) -> list[dict]:
        """Suggest the order in which entries should be validated.

        Uses topological sort of dependency graph: entries that others depend on
        should be validated first. Centrality used as tiebreaker.
        """
        G = _build_graph()

        # Build dependency-only subgraph
        DG = nx.DiGraph()
        entry_nodes = [n for n, d in G.nodes(data=True) if d.get('type') == 'entry']

        if phase_filter:
            entry_nodes = [n for n in entry_nodes if G.nodes[n].get('phase') == phase_filter]

        DG.add_nodes_from(entry_nodes)

        for u, v, d in G.edges(data=True):
            if d.get('relation') == 'depends_on' and u in DG and v in DG:
                DG.add_edge(u, v)

        # Compute centrality for tiebreaking
        centrality = nx.degree_centrality(G.subgraph(entry_nodes)) if entry_nodes else {}

        # Topological sort (handle cycles gracefully)
        try:
            topo_order = list(nx.topological_sort(DG))
            # Reverse: dependencies first
            topo_order.reverse()
        except nx.NetworkXUnfeasible:
            # Has cycles -- fall back to centrality ordering
            topo_order = sorted(entry_nodes, key=lambda n: centrality.get(n, 0), reverse=True)

        results = []
        for i, node_id in enumerate(topo_order):
            data = G.nodes.get(node_id, {})
            dependents = list(DG.predecessors(node_id))  # entries that depend on this one
            results.append({
                "priority": i + 1,
                "entry_id": node_id,
                "content": data.get('content', ''),
                "phase": data.get('phase', ''),
                "centrality": round(centrality.get(node_id, 0), 5),
                "depended_on_by": len(dependents),
            })

        return results

    @mcp.tool()
    def detect_circular_dependencies() -> dict:
        """Detect circular dependencies (cycles) in the entry dependency graph.

        Flags circular reasoning that should be resolved.
        """
        G = _build_graph()

        # Build dependency-only directed graph
        DG = nx.DiGraph()
        for u, v, d in G.edges(data=True):
            if d.get('relation') == 'depends_on':
                if G.nodes.get(u, {}).get('type') == 'entry' and G.nodes.get(v, {}).get('type') == 'entry':
                    DG.add_edge(u, v)

        cycles = list(nx.simple_cycles(DG))

        cycle_details = []
        for cycle in cycles:
            members = []
            for eid in cycle:
                data = G.nodes.get(eid, {})
                members.append({
                    "entry_id": eid,
                    "content": data.get('content', ''),
                })
            cycle_details.append({
                "length": len(cycle),
                "entries": members,
                "cycle_path": " -> ".join(cycle) + f" -> {cycle[0]}",
            })

        return {
            "has_cycles": len(cycles) > 0,
            "total_cycles": len(cycles),
            "cycles": cycle_details,
        }

    @mcp.tool()
    def render_graph(
        show_isolated: bool = False,
        max_label_length: int = 60,
    ) -> dict:
        """Render the knowledge graph as an interactive HTML file.

        Generates a force-directed graph visualization with color-coded nodes
        (by phase) and edges (by relation type). Opens in any browser.
        Cached: only regenerates when underlying data changes.

        Args:
            show_isolated: Include entries with no connections (default: False)
            max_label_length: Max characters for node labels (default: 60)
        """
        global _render_stale

        # Check if cached HTML is still fresh
        db_dir = Path(__file__).resolve().parent.parent.parent.parent / "data"
        output_path = db_dir / "graph.html"

        if not _render_stale and output_path.exists():
            G = _build_graph()
            nodes_to_include = set()
            if show_isolated:
                nodes_to_include = set(G.nodes())
            else:
                for u, v in G.edges():
                    nodes_to_include.add(u)
                    nodes_to_include.add(v)
            return {
                "success": True,
                "file_path": str(output_path),
                "node_count": len(nodes_to_include),
                "edge_count": sum(1 for u, v in G.edges() if u in nodes_to_include and v in nodes_to_include),
                "message": f"Graph unchanged, serving cached file: {output_path}",
            }

        try:
            from pyvis.network import Network
        except ImportError:
            return {"success": False, "file_path": "", "message": "pyvis not installed. Run: pip install pyvis"}

        G = _build_graph()

        # Phase -> color mapping for entry nodes
        phase_colors = {
            "hypothesis": "#4A90D9",
            "question": "#F5A623",
            "validation": "#7ED321",
            "active_verification": "#50E3C2",
            "passive_verification": "#9B9B9B",
            "validated": "#417505",
            "rejected": "#D0021B",
        }

        # Edge relation -> color mapping
        edge_colors = {
            "evidence": "#AAAAAA",
            "verification": "#4A90D9",
            "depends_on": "#F5A623",
            "supports": "#7ED321",
            "contradicts": "#D0021B",
            "refines": "#9013FE",
            "related": "#50E3C2",
            "shared_scope": "#DDDDDD",
        }

        # Determine which nodes to include
        if show_isolated:
            nodes_to_include = set(G.nodes())
        else:
            nodes_to_include = set()
            for u, v in G.edges():
                nodes_to_include.add(u)
                nodes_to_include.add(v)

        if not nodes_to_include:
            return {"success": False, "file_path": "", "message": "No connected nodes to render"}

        # Build pyvis network
        net = Network(
            height="100vh",
            width="100vw",
            directed=True,
            bgcolor="#1a1a2e",
            font_color="#e0e0e0",
        )
        net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=150, spring_strength=0.01)

        # Add nodes
        for node_id in nodes_to_include:
            data = G.nodes.get(node_id, {})
            node_type = data.get("type", "unknown")

            if node_type == "entry":
                content = data.get("content", "")
                phase = data.get("phase", "question")
                label = content[:max_label_length] + ("..." if len(content) > max_label_length else "")
                # First line only for the visible label
                short_label = node_id
                color = phase_colors.get(phase, "#888888")
                net.add_node(
                    node_id,
                    label=short_label,
                    title=f"<b>{node_id}</b> [{phase}]<br>{label}",
                    color=color,
                    size=15,
                    shape="dot",
                )
            elif node_type == "verse":
                surah = data.get("surah", "?")
                ayah = data.get("ayah", "?")
                net.add_node(
                    node_id,
                    label=f"{surah}:{ayah}",
                    title=f"Verse {surah}:{ayah}",
                    color="#555555",
                    size=8,
                    shape="diamond",
                )

        # Add edges
        for u, v, data in G.edges(data=True):
            if u not in nodes_to_include or v not in nodes_to_include:
                continue
            relation = data.get("relation", "unknown")
            color = edge_colors.get(relation, "#666666")
            width = 1
            dashes = False

            if relation == "evidence":
                dashes = True
                width = 1
            elif relation == "shared_scope":
                dashes = True
                width = 0.5
                color = "#555555"
            elif relation == "verification":
                verification = data.get("verification", "")
                if verification == "supports":
                    color = "#7ED321"
                elif verification == "contradicts":
                    color = "#D0021B"
                else:
                    color = "#F5A623"
                width = 2
            elif relation in ("depends_on", "supports", "contradicts", "refines", "related"):
                width = 2

            title = relation
            if relation == "shared_scope":
                title = f"shared: {data.get('scope_type', '')}={data.get('scope_value', '')}"
            elif relation == "verification":
                title = f"verification: {data.get('verification', '')}"

            net.add_edge(u, v, color=color, width=width, dashes=dashes, title=title)

        # Add legend as HTML overlay
        legend_html = """
        <div style="position:fixed;top:10px;right:10px;background:rgba(0,0,0,0.8);padding:12px 16px;
                    border-radius:8px;font-family:monospace;font-size:12px;color:#e0e0e0;z-index:1000;">
          <div style="margin-bottom:8px;font-weight:bold;font-size:14px;">Kalima Knowledge Graph</div>
          <div style="margin-bottom:4px;"><span style="color:#4A90D9;">&#9679;</span> hypothesis</div>
          <div style="margin-bottom:4px;"><span style="color:#F5A623;">&#9679;</span> question</div>
          <div style="margin-bottom:4px;"><span style="color:#7ED321;">&#9679;</span> validation</div>
          <div style="margin-bottom:4px;"><span style="color:#417505;">&#9679;</span> validated</div>
          <div style="margin-bottom:4px;"><span style="color:#D0021B;">&#9679;</span> rejected</div>
          <div style="margin-bottom:4px;"><span style="color:#555555;">&#9670;</span> verse</div>
          <hr style="border-color:#444;margin:6px 0;">
          <div style="margin-bottom:4px;"><span style="color:#7ED321;">&#8212;</span> supports</div>
          <div style="margin-bottom:4px;"><span style="color:#D0021B;">&#8212;</span> contradicts</div>
          <div style="margin-bottom:4px;"><span style="color:#F5A623;">&#8212;</span> depends_on</div>
          <div style="margin-bottom:4px;"><span style="color:#AAAAAA;">- -</span> evidence</div>
          <div><span style="color:#555555;">&#183;&#183;&#183;</span> shared_scope</div>
        </div>
        """

        # Write to file
        db_dir = Path(__file__).resolve().parent.parent.parent.parent / "data"
        db_dir.mkdir(parents=True, exist_ok=True)
        output_path = db_dir / "graph.html"

        net.write_html(str(output_path))

        # Inject fullscreen CSS and legend into the HTML
        fullscreen_css = "<style>html, body { margin: 0; padding: 0; overflow: hidden; width: 100vw; height: 100vh; }</style>"
        html_content = output_path.read_text(encoding="utf-8")
        html_content = html_content.replace("<head>", "<head>\n" + fullscreen_css)
        html_content = html_content.replace("</body>", legend_html + "\n</body>")
        output_path.write_text(html_content, encoding="utf-8")

        _render_stale = False

        return {
            "success": True,
            "file_path": str(output_path),
            "node_count": len(nodes_to_include),
            "edge_count": sum(1 for u, v in G.edges() if u in nodes_to_include and v in nodes_to_include),
            "message": f"Graph rendered to {output_path}",
        }
