#!/usr/bin/env python3
"""
Database Graph Visualization - Surah 1 Full Detail
"""

import sqlite3
import networkx as nx
from pyvis.network import Network
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "scholar.db"

def get_surah1_full_graph():
    """Generate a complete graph of Surah 1 with all details."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    G = nx.DiGraph()
    
    colors = {
        'surah': '#FF6B6B',
        'verse': '#4ECDC4', 
        'word_instance': '#45B7D1',
        'word_type': '#96CEB4',
        'morpheme_type': '#FFEAA7',
        'root': '#DDA0DD',
        'feature': '#98D8C8',
        'lemma': '#87CEEB',
        'pos': '#F0E68C',
    }
    
    # ===== SURAH NODE =====
    print("Adding Surah 1...")
    G.add_node("surah_1", label="Al-Fatiha\n(ٱلْفَاتِحَة)", 
              color=colors['surah'], group='surah', size=50, title="Surah 1: Al-Fatiha (The Opening)")
    
    # ===== VERSE NODES =====
    print("Adding verses...")
    verses = conn.execute("""
        SELECT surah, ayah, text FROM gold_standard 
        WHERE surah = 1
        ORDER BY ayah
    """).fetchall()
    
    for v in verses:
        verse_node = f"verse_1_{v['ayah']}"
        short_text = v['text'][:50] + "..." if len(v['text']) > 50 else v['text']
        G.add_node(verse_node, 
                  label=f"Verse {v['ayah']}\n{v['text'][:25]}...",
                  color=colors['verse'], group='verse', size=25,
                  title=f"Verse 1:{v['ayah']}\n\n{v['text']}")
        G.add_edge("surah_1", verse_node, width=3)
    
    # ===== WORD INSTANCES =====
    print("Adding word instances...")
    words = conn.execute("""
        SELECT wi.id, wi.verse_surah, wi.verse_ayah, wi.word_index, 
               wt.id as word_type_id, normalized_text
        FROM word_instances wi
        JOIN word_types wt ON wi.word_type_id = wt.id
        WHERE wi.verse_surah = 1
        ORDER BY wi.verse_ayah, wi.word_index
    """).fetchall()
    
    print(f"  Found {len(words)} words")
    
    word_type_ids = {}
    for w in words:
        word_node = f"word_{w['id']}"
        label = w['normalized_text'] if w['normalized_text'] else f"w{w['word_index']}"
        G.add_node(word_node, 
                  label=label,
                  color=colors['word_instance'], group='word_instance', size=12,
                  title=f"Word: {label}\nPosition: {w['verse_ayah']}:{w['word_index']}")
        
        verse_node = f"verse_1_{w['verse_ayah']}"
        G.add_edge(verse_node, word_node, width=1.5)
        
        # Track word type
        if w['word_type_id'] not in word_type_ids:
            word_type_ids[w['word_type_id']] = []
        word_type_ids[w['word_type_id']].append(w['id'])
    
    # ===== WORD TYPES =====
    print("Adding word types...")
    for wt_id in word_type_ids:
        wt_node = f"word_type_{wt_id}"
        G.add_node(wt_node, 
                  label=f"WT:{wt_id}",
                  color=colors['word_type'], group='word_type', size=15,
                  title=f"Word Type ID: {wt_id}\nInstances: {len(word_type_ids[wt_id])}")
        
        # Connect all instances to this word type
        for wid in word_type_ids[wt_id]:
            word_node = f"word_{wid}"
            G.add_edge(wt_node, word_node, width=0.5)
    
    # ===== MORPHEME TYPES =====
    print("Adding morpheme types...")
    wt_ids = list(word_type_ids.keys())
    if wt_ids:
        placeholders = ','.join('?' * len(wt_ids))
        morphemes = conn.execute(f"""
            SELECT wm.word_type_id, wm.position, mt.id, mt.uthmani_text, mt.root_id,
                   mt.lemma_id, mt.pos_id
            FROM word_type_morphemes wm
            JOIN morpheme_types mt ON wm.morpheme_type_id = mt.id
            WHERE wm.word_type_id IN ({placeholders})
        """, wt_ids).fetchall()
        
        morpheme_type_ids = set()
        for m in morphemes:
            if m['id'] not in morpheme_type_ids:
                morpheme_type_ids.add(m['id'])
                mt_node = f"morpheme_type_{m['id']}"
                label = m['uthmani_text'] if m['uthmani_text'] else f"M:{m['id']}"
                G.add_node(mt_node, 
                          label=label,
                          color=colors['morpheme_type'], group='morpheme_type', size=12,
                          title=f"Morpheme Type: {m['uthmani_text']}\nID: {m['id']}\nRoot ID: {m['root_id']}\nLemma ID: {m['lemma_id']}")
            
            wt_node = f"word_type_{m['word_type_id']}"
            mt_node = f"morpheme_type_{m['id']}"
            G.add_edge(wt_node, mt_node, width=0.5)
    
    # ===== FEATURES (Roots, Lemmas, POS) =====
    print("Adding features (roots, lemmas, POS)...")
    
    # Get all root IDs from morpheme types in this surah
    root_ids = conn.execute("""
        SELECT DISTINCT mt.root_id 
        FROM word_type_morphemes wm
        JOIN morpheme_types mt ON wm.morpheme_type_id = mt.id
        JOIN word_types wt ON wm.word_type_id = wt.id
        JOIN word_instances wi ON wi.word_type_id = wt.id
        WHERE wi.verse_surah = 1 AND mt.root_id IS NOT NULL
    """).fetchall()
    
    roots_added = set()
    for r in root_ids:
        if r['root_id'] and r['root_id'] not in roots_added:
            roots_added.add(r['root_id'])
            root_info = conn.execute("""
                SELECT id, label_en, label_ar, lookup_key 
                FROM features WHERE id = ?
            """, (r['root_id'],)).fetchone()
            
            if root_info:
                root_node = f"root_{root_info['id']}"
                label = root_info['label_en'][:20] if root_info['label_en'] else root_info['lookup_key'][:20]
                G.add_node(root_node,
                          label=f"📖 {label}",
                          color=colors['root'], group='root', size=20,
                          title=f"Root: {root_info['label_en']}\nArabic: {root_info['label_ar']}\nID: {root_info['id']}")
                
                # Link to morpheme types
                mts = conn.execute("""
                    SELECT DISTINCT mt.id FROM morpheme_types mt
                    WHERE mt.root_id = ?
                """, (root_info['id'],)).fetchall()
                
                for mt in mts:
                    mt_node = f"morpheme_type_{mt['id']}"
                    if mt_node in G:
                        G.add_edge(mt_node, root_node, width=1, color='#DDA0DD')
    
    # Lemmas
    lemma_ids = conn.execute("""
        SELECT DISTINCT mt.lemma_id 
        FROM word_type_morphemes wm
        JOIN morpheme_types mt ON wm.morpheme_type_id = mt.id
        JOIN word_types wt ON wm.word_type_id = wt.id
        JOIN word_instances wi ON wi.word_type_id = wt.id
        WHERE wi.verse_surah = 1 AND mt.lemma_id IS NOT NULL
    """).fetchall()
    
    lemmas_added = set()
    for l in lemma_ids:
        if l['lemma_id'] and l['lemma_id'] not in lemmas_added:
            lemmas_added.add(l['lemma_id'])
            lemma_info = conn.execute("""
                SELECT id, label_en, lookup_key 
                FROM features WHERE id = ?
            """, (l['lemma_id'],)).fetchone()
            
            if lemma_info:
                lemma_node = f"lemma_{lemma_info['id']}"
                label = lemma_info['label_en'][:20] if lemma_info['label_en'] else lemma_info['lookup_key'][:20]
                G.add_node(lemma_node,
                          label=f"📝 {label}",
                          color=colors['lemma'], group='lemma', size=15,
                          title=f"Lemma: {lemma_info['label_en']}\nID: {lemma_info['id']}")
                
                # Link to morpheme types
                mts = conn.execute("""
                    SELECT DISTINCT mt.id FROM morpheme_types mt
                    WHERE mt.lemma_id = ?
                """, (lemma_info['id'],)).fetchall()
                
                for mt in mts:
                    mt_node = f"morpheme_type_{mt['id']}"
                    if mt_node in G:
                        G.add_edge(mt_node, lemma_node, width=0.5, color='#87CEEB')
    
    # Parts of Speech
    pos_ids = conn.execute("""
        SELECT DISTINCT mt.pos_id 
        FROM word_type_morphemes wm
        JOIN morpheme_types mt ON wm.morpheme_type_id = mt.id
        JOIN word_types wt ON wm.word_type_id = wt.id
        JOIN word_instances wi ON wi.word_type_id = wt.id
        WHERE wi.verse_surah = 1 AND mt.pos_id IS NOT NULL
    """).fetchall()
    
    pos_added = set()
    for p in pos_ids:
        if p['pos_id'] and p['pos_id'] not in pos_added:
            pos_added.add(p['pos_id'])
            pos_info = conn.execute("""
                SELECT id, label_en, lookup_key 
                FROM features WHERE id = ?
            """, (p['pos_id'],)).fetchone()
            
            if pos_info:
                pos_node = f"pos_{pos_info['id']}"
                label = pos_info['label_en'][:15] if pos_info['label_en'] else pos_info['lookup_key'][:15]
                G.add_node(pos_node,
                          label=f"🏷️ {label}",
                          color=colors['pos'], group='pos', size=15,
                          title=f"POS: {pos_info['label_en']}\nID: {pos_info['id']}")
                
                # Link to morpheme types
                mts = conn.execute("""
                    SELECT DISTINCT mt.id FROM morpheme_types mt
                    WHERE mt.pos_id = ?
                """, (pos_info['id'],)).fetchall()
                
                for mt in mts:
                    mt_node = f"morpheme_type_{mt['id']}"
                    if mt_node in G:
                        G.add_edge(mt_node, pos_node, width=0.5, color='#F0E68C')
    
    # ===== CONTENT ADDRESSES =====
    print("Adding content addresses...")
    ca_count = 0
    for wt_id in word_type_ids:
        cas = conn.execute("""
            SELECT entity_type, entity_id, address 
            FROM content_addresses 
            WHERE entity_type = 'word_type' AND entity_id = ?
        """, (str(wt_id),)).fetchall()
        
        for ca in cas:
            ca_node = f"ca_{ca['entity_type']}_{ca['entity_id']}"
            short_addr = ca['address'][:20] + "..."
            G.add_node(ca_node,
                      label=f"🔗{short_addr[:10]}",
                      color='#F7DC6F', group='content_address', size=8,
                      title=f"Content Address\n{ca['address']}")
            
            wt_node = f"word_type_{wt_id}"
            G.add_edge(wt_node, ca_node, width=0.3, color='#F7DC6F')
            ca_count += 1
    
    print(f"  Added {ca_count} content addresses")
    
    # ===== HOLONOMIC ENTRIES (if any for Surah 1) =====
    print("Adding holonomic entries...")
    holonomic = conn.execute("""
        SELECT address, content, phase, category
        FROM holonomic_entries 
        WHERE anchor_ids LIKE '%1:%' OR content LIKE '%surah 1%' OR content LIKE '%fatiha%'
        LIMIT 50
    """).fetchall()
    
    for h in holonomic:
        h_node = f"holonomic_{h['address'][:20]}"
        G.add_node(h_node,
                  label=f"💡{h['phase'][:8]}",
                  color='#E74C3C', group='holonomic', size=12,
                  title=f"Phase: {h['phase']}\nCategory: {h['category']}\n\n{h['content'][:200]}")
    
    conn.close()
    return G

def visualize_graph(G, output_path):
    """Create interactive HTML visualization."""
    net = Network(height="900px", width="100%", bgcolor="#1a1a2e", font_color="white",
                  directed=True, notebook=False, cdn_resources='remote')
    
    net.from_nx(G)
    
    # Count by group
    groups = {}
    for n in G.nodes():
        g = G.nodes[n].get('group', 'unknown')
        groups[g] = groups.get(g, 0) + 1
    
    net.set_options("""
    {
      "nodes": {
        "borderWidth": 2,
        "borderWidthSelected": 4,
        "font": { "size": 12, "face": "arial" }
      },
      "edges": {
        "color": { "inherit": "both" },
        "smooth": { "type": "continuous" }
      },
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -150,
          "centralGravity": 0.005,
          "springLength": 80,
          "springConstant": 0.05
        },
        "minVelocity": 0.75,
        "solver": "forceAtlas2Based"
      },
      "interaction": {
        "hover": true,
        "navigationButtons": true,
        "keyboard": { "enabled": true },
        "tooltipDelay": 50
      }
    }
    """)
    
    net.save_graph(str(output_path))
    
    html = f"""
    <h1 style="text-align:center; color:#eee; margin:10px;">📖 Surah 1 (Al-Fatiha) - Complete Graph</h1>
    <p style="text-align:center; color:#aaa;">
        <b>Total Nodes:</b> {len(G.nodes())} | <b>Total Edges:</b> {len(G.edges())}<br>
        <b>By Type:</b> {', '.join(f'{k}:{v}' for k,v in sorted(groups.items()))}<br>
        <small>🖱️ Scroll to zoom • Drag to pan • Hover for details • Double-click to focus</small>
    </p>
    <div style="background:#333; padding:10px; margin:10px; border-radius:5px; color:#ccc; font-size:12px;">
        <b>Legend:</b> 
        🔴 Surah | 🔵 Verse | 💧 Word | 🟢 Word Type | 🟡 Morpheme | 🟣 Root | 📝 Lemma | 🏷️ POS | 🔗 Address
    </div>
    """
    
    with open(str(output_path), 'r', encoding='utf-8') as f:
        content = f.read()
    with open(str(output_path), 'w', encoding='utf-8') as f:
        f.write(html + content)
    
    print(f"Graph saved to {output_path}")

def main():
    print("Generating Surah 1 full graph...")
    G = get_surah1_full_graph()
    
    print(f"\n=== GRAPH STATISTICS ===")
    print(f"Nodes: {len(G.nodes())}")
    print(f"Edges: {len(G.edges())}")
    
    groups = {}
    for n in G.nodes():
        g = G.nodes[n].get('group', 'unknown')
        groups[g] = groups.get(g, 0) + 1
    
    print(f"\nBy group:")
    for g, c in sorted(groups.items(), key=lambda x: -x[1]):
        print(f"  {g}: {c}")
    
    output = Path(__file__).parent.parent / "docs" / "surah1_full_graph.html"
    visualize_graph(G, output)

if __name__ == "__main__":
    main()
