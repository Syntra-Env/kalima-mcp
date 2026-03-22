#!/usr/bin/env python3
"""
Database Graph Visualization Generator
Creates an interactive HTML graph of the Scholar database entities.
"""

import sqlite3
import networkx as nx
from pyvis.network import Network
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "scholar.db"

def get_db_graph(max_nodes_per_type=100, include_content_addresses=False):
    """Generate a NetworkX graph from the database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    G = nx.DiGraph()
    
    # Define colors for each entity type
    colors = {
        'surah': '#FF6B6B',
        'verse': '#4ECDC4', 
        'word_instance': '#45B7D1',
        'word_type': '#96CEB4',
        'morpheme_type': '#FFEAA7',
        'root': '#DDA0DD',
        'feature': '#98D8C8',
        'content_address': '#F7DC6F',
    }
    
    # Get surah-verse structure (sample: first 3 surahs)
    print("Adding surah/verse nodes...")
    verses = conn.execute("""
        SELECT DISTINCT surah, ayah FROM gold_standard 
        WHERE surah <= 3
        ORDER BY surah, ayah
    """).fetchall()
    
    surah_nodes = set()
    for v in verses:
        surah_node = f"surah_{v['surah']}"
        if surah_node not in surah_nodes:
            G.add_node(surah_node, label=f"Surah {v['surah']}", 
                      color=colors['surah'], group='surah', size=30)
            surah_nodes.add(surah_node)
        verse_node = f"verse_{v['surah']}_{v['ayah']}"
        G.add_node(verse_node, label=f"{v['surah']}:{v['ayah']}", 
                  color=colors['verse'], group='verse', size=15)
        G.add_edge(surah_node, verse_node, width=2)
    
    # Get word instances for sample verses
    print("Adding word instance nodes...")
    words = conn.execute("""
        SELECT wi.id, wi.verse_surah, wi.verse_ayah, wi.word_index, 
               wt.id as word_type_id, normalized_text
        FROM word_instances wi
        JOIN word_types wt ON wi.word_type_id = wt.id
        WHERE wi.verse_surah <= 3
        ORDER BY wi.verse_surah, wi.verse_ayah, wi.word_index
        LIMIT 500
    """).fetchall()
    
    word_type_ids = set()
    for w in words:
        word_node = f"word_{w['id']}"
        label = w['normalized_text'][:20] if w['normalized_text'] else f"word_{w['word_index']}"
        G.add_node(word_node, label=label, 
                  color=colors['word_instance'], group='word_instance', size=8)
        
        verse_node = f"verse_{w['verse_surah']}_{w['verse_ayah']}"
        G.add_edge(verse_node, word_node, width=1)
        
        # Track word types
        if w['word_type_id'] not in word_type_ids:
            word_type_ids.add(w['word_type_id'])
            wt_node = f"word_type_{w['word_type_id']}"
            G.add_node(wt_node, label=f"WT:{w['word_type_id']}", 
                      color=colors['word_type'], group='word_type', size=12)
        G.add_edge(wt_node, word_node, width=0.5)
    
    # Get morpheme types for sample words
    print("Adding morpheme type nodes...")
    wids = [w['id'] for w in words[:100]]
    if wids:
        placeholders = ','.join('?' * len(wids))
        morphemes = conn.execute(f"""
            SELECT wm.word_type_id, wm.position, mt.id, mt.uthmani_text, mt.root_id
            FROM word_type_morphemes wm
            JOIN morpheme_types mt ON wm.morpheme_type_id = mt.id
            WHERE wm.word_type_id IN ({placeholders})
        """, wids).fetchall()
        
        morpheme_type_ids = set()
        for m in morphemes:
            if m['id'] not in morpheme_type_ids:
                morpheme_type_ids.add(m['id'])
                mt_node = f"morpheme_type_{m['id']}"
                label = m['uthmani_text'][:15] if m['uthmani_text'] else f"M:{m['id']}"
                G.add_node(mt_node, label=label,
                          color=colors['morpheme_type'], group='morpheme_type', size=10)
            wt_node = f"word_type_{m['word_type_id']}"
            mt_node = f"morpheme_type_{m['id']}"
            G.add_edge(wt_node, mt_node, width=0.3)
    
    # Get root features
    print("Adding root nodes...")
    roots = conn.execute("""
        SELECT id, label_en, lookup_key 
        FROM features 
        WHERE feature_type = 'root' 
        LIMIT 50
    """).fetchall()
    
    for r in roots:
        root_node = f"root_{r['id']}"
        label = r['label_en'][:20] if r['label_en'] else r['lookup_key'][:20]
        G.add_node(root_node, label=label,
                  color=colors['root'], group='root', size=20)
        
        # Link to morpheme types that have this root
        mt_with_root = conn.execute("""
            SELECT DISTINCT id FROM morpheme_types WHERE root_id = ?
        """, (r['id'],)).fetchall()
        
        for mt in mt_with_root[:3]:  # Limit connections
            mt_node = f"morpheme_type_{mt['id']}"
            if mt_node in G:
                G.add_edge(mt_node, root_node, width=0.5)
    
    # Optional: Include content addresses (can be large)
    if include_content_addresses:
        print("Adding content address nodes...")
        ca_count = conn.execute("SELECT COUNT(*) FROM content_addresses").fetchone()[0]
        print(f"Total content addresses: {ca_count}")
        
        # Sample some content addresses
        cas = conn.execute("""
            SELECT entity_type, entity_id, address 
            FROM content_addresses 
            LIMIT 200
        """).fetchall()
        
        for ca in cas:
            ca_node = f"ca_{ca['entity_type']}_{ca['entity_id'][:20]}"
            short_addr = ca['address'][:16] + "..."
            G.add_node(ca_node, label=short_addr,
                      color=colors['content_address'], group='content_address', size=6)
            
            # Link to entity
            if ca['entity_type'] == 'morpheme_type':
                mt_node = f"morpheme_type_{ca['entity_id']}"
                if mt_node in G:
                    G.add_edge(mt_node, ca_node, width=0.3)
    
    conn.close()
    return G

def visualize_graph(G, output_path=None):
    """Create interactive HTML visualization using pyvis."""
    if output_path is None:
        output_path = Path(__file__).parent.parent / "docs" / "database_graph.html"
    else:
        output_path = Path(output_path)
    
    net = Network(height="800px", width="100%", bgcolor="#222222", font_color="white",
                  directed=True, notebook=False, cdn_resources='remote')
    
    # Copy networkx graph to pyvis
    net.from_nx(G)
    
    # Customize physics for better layout
    net.set_options("""
    {
      "nodes": {
        "borderWidth": 2,
        "borderWidthSelected": 4,
        "font": { "size": 14, "face": "arial" }
      },
      "edges": {
        "color": { "inherit": "both" },
        "smooth": { "type": "continuous" }
      },
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -100,
          "centralGravity": 0.01,
          "springLength": 100,
          "springConstant": 0.08
        },
        "minVelocity": 0.75,
        "solver": "forceAtlas2Based"
      },
      "interaction": {
        "hover": true,
        "navigationButtons": true,
        "keyboard": { "enabled": true },
        "tooltipDelay": 100
      }
    }
    """)
    
    # Add legend/title
    html = f"""
    <h1 style="text-align:center; color:white; margin:10px;">Scholar Database Graph</h1>
    <p style="text-align:center; color:#aaa;">
        Nodes: {len(G.nodes())} | Edges: {len(G.edges())}<br>
        <small>Hover for details • Scroll to zoom • Drag to pan • Double-click to focus</small>
    </p>
    """
    
    net.save_graph(str(output_path))
    
    # Prepend title to HTML
    with open(str(output_path), 'r', encoding='utf-8') as f:
        content = f.read()
    with open(str(output_path), 'w', encoding='utf-8') as f:
        f.write(html + content)
    
    print(f"Graph saved to {output_path}")
    return output_path

def main():
    print("Generating database graph...")
    print("This may take a moment...")
    
    G = get_db_graph(max_nodes_per_type=100, include_content_addresses=True)
    
    print(f"\nGraph Statistics:")
    print(f"  Nodes: {len(G.nodes())}")
    print(f"  Edges: {len(G.edges())}")
    print(f"  Node types: {set(G.nodes[n].get('group', 'unknown') for n in G.nodes())}")
    
    output = visualize_graph(G)
    print(f"\nOpen {output} in a browser to explore the graph.")

if __name__ == "__main__":
    main()
