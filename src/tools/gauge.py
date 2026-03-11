"""Abjadic Gauge Field: Root Resonance, Root Networks, Interpretation Comparison.

Implements the abjadic gauge field from HUFD theory:
  B_abjad = Σ_{ijk} r_{ijk} |C_i C_j C_k⟩

Where consonantal roots form the gauge-invariant topology and
vowel diacritics act as local gauge transformations U(θ).

Key tools:
  - Root resonance: holonomic closure test across all Quranic instances
  - Root network: connectivity graph of related roots
  - Root concordance verification: test a proposed meaning against all instances
  - Traditional interpretation comparison: gauge distance between readings
"""

import math
import sqlite3
import numpy as np
from mcp.server.fastmcp import FastMCP
from ..db import get_connection
from ..utils.hufd_math import get_h_matrix, get_discrete_curvature
from ..utils.units import compose_word_text, compose_verse_text


def _get_root_instances(conn: sqlite3.Connection, root_id: int, limit: int = 500) -> list[dict]:
    """Get all morpheme instances of a root across the Quran, with their features."""
    rows = conn.execute("""
        SELECT wi.id as instance_id, wi.verse_surah, wi.verse_ayah, wi.word_index,
               wi.normalized_text, wi.word_type_id,
               mt.id as morpheme_id, mt.pos_id, mt.verb_form_id, mt.voice_id,
               mt.mood_id, mt.aspect_id, mt.person_id, mt.number_id,
               mt.gender_id, mt.case_value_id, mt.lemma_id
        FROM word_instances wi
        JOIN word_type_morphemes wtm ON wi.word_type_id = wtm.word_type_id
        JOIN morpheme_types mt ON wtm.morpheme_type_id = mt.id
        WHERE mt.root_id = ?
        ORDER BY wi.verse_surah, wi.verse_ayah, wi.word_index
        LIMIT ?
    """, (root_id, limit)).fetchall()
    return [dict(r) for r in rows]


_surprisal_cache: dict[int, float] = {}

def _surprisal(conn: sqlite3.Connection, feature_id) -> float:
    """Information content of a feature value (cached)."""
    if not feature_id:
        return 0.0
    if feature_id in _surprisal_cache:
        return _surprisal_cache[feature_id]
    row = conn.execute(
        "SELECT frequency FROM features WHERE id = ?", (feature_id,)
    ).fetchone()
    if not row or not row['frequency'] or row['frequency'] <= 0:
        _surprisal_cache[feature_id] = 0.0
        return 0.0
    val = math.log(max(128000 / row['frequency'], 1.0))
    _surprisal_cache[feature_id] = val
    return val


def _instance_to_h_components(conn: sqlite3.Connection, inst: dict) -> list[float]:
    """Map a root instance's features to su(2) components."""
    x = _surprisal(conn, inst.get('verb_form_id')) + _surprisal(conn, inst.get('aspect_id'))
    y = _surprisal(conn, inst.get('person_id')) + _surprisal(conn, inst.get('gender_id'))
    z = _surprisal(conn, inst.get('pos_id')) + _surprisal(conn, inst.get('case_value_id'))

    vec = np.array([x, y, z])
    norm = np.linalg.norm(vec)
    return (vec / norm).tolist() if norm > 0 else [0.0, 0.0, 0.0]


def register(server: FastMCP):

    @server.tool()
    def compute_root_resonance(root_feature_id: int) -> dict:
        """Compute holonomic resonance for a root across all its Quranic instances.

        Tests the holonomic closure condition: ∮H_μ dx^μ = const
        - Low curvature (κ → 0): meaning is conserved (consistent usage)
        - High curvature (κ → π): meaning evolves (context-dependent usage)

        Returns the curvature value, number of instances, and a sample
        of high-curvature locations where meaning may shift.
        """
        conn = get_connection()

        # Get root info
        root_info = conn.execute(
            "SELECT lookup_key, label_ar, frequency FROM features WHERE id = ?",
            (root_feature_id,)
        ).fetchone()
        if not root_info:
            return {"error": "Root not found"}

        instances = _get_root_instances(conn, root_feature_id)
        if not instances:
            return {"error": "No instances found for this root"}

        # Build H matrices for all instances
        h_sequence = []
        instance_data = []
        for inst in instances:
            comps = _instance_to_h_components(conn, inst)
            h_mat = get_h_matrix(comps)
            h_sequence.append(h_mat)
            instance_data.append({
                'loc': f"{inst['verse_surah']}:{inst['verse_ayah']}:{inst['word_index']}",
                'text': inst['normalized_text'],
            })

        # Global holonomy (full path around ALL instances)
        global_kappa = get_discrete_curvature(h_sequence)

        # Local curvatures (sliding window of 5 instances)
        local_curvatures = []
        for i in range(len(h_sequence) - 4):
            window = h_sequence[i:i+5]
            kappa = get_discrete_curvature(window)
            local_curvatures.append({
                'start': instance_data[i]['loc'],
                'end': instance_data[i+4]['loc'],
                'curvature': round(kappa, 4),
            })

        # Find high-curvature regions (meaning shifts)
        hotspots = sorted(local_curvatures, key=lambda x: x['curvature'], reverse=True)[:10]

        # Consistency classification
        if global_kappa < 0.5:
            consistency = "highly_consistent"
        elif global_kappa < 1.5:
            consistency = "moderately_consistent"
        else:
            consistency = "context_dependent"

        return {
            "root": root_info['lookup_key'],
            "root_ar": root_info['label_ar'],
            "total_instances": len(instances),
            "global_curvature": round(global_kappa, 4),
            "consistency": consistency,
            "hotspots": hotspots,
        }

    @server.tool()
    def get_root_network(root_feature_id: int) -> dict:
        """Get the network of roots connected to a given root.

        Roots are connected when they:
        1. Share consonants (e.g., ك-ت-ب and ك-ت-م share ك and ت)
        2. Co-occur in the same verse

        Returns connected roots with connection type and strength.
        """
        conn = get_connection()

        root_info = conn.execute(
            "SELECT lookup_key, label_ar FROM features WHERE id = ?",
            (root_feature_id,)
        ).fetchone()
        if not root_info:
            return {"error": "Root not found"}

        root_key = root_info['lookup_key']
        # Extract consonants from lookup_key (format: "ك-ت-ب")
        consonants = [c.strip() for c in root_key.split('-') if c.strip()]

        # 1. Find roots sharing consonants
        shared_consonant_roots = []
        if consonants:
            # Search for roots containing any of these consonants
            conditions = []
            params = []
            for c in consonants:
                conditions.append("lookup_key LIKE ?")
                params.append(f"%{c}%")

            other_roots = conn.execute(
                f"""SELECT id, lookup_key, label_ar, frequency FROM features
                    WHERE feature_type = 'root' AND id != ? AND ({' OR '.join(conditions)})
                    ORDER BY frequency DESC LIMIT 30""",
                [root_feature_id] + params
            ).fetchall()

            for r in other_roots:
                other_consonants = [c.strip() for c in r['lookup_key'].split('-') if c.strip()]
                shared = set(consonants) & set(other_consonants)
                if shared:
                    shared_consonant_roots.append({
                        'root_id': r['id'],
                        'root': r['lookup_key'],
                        'root_ar': r['label_ar'],
                        'shared_consonants': list(shared),
                        'connection': 'shared_radical',
                        'frequency': r['frequency'],
                    })

        # 2. Find co-occurring roots (same verse)
        cooccurring = conn.execute("""
            SELECT f2.id, f2.lookup_key, f2.label_ar, f2.frequency,
                   COUNT(DISTINCT wi1.verse_surah || ':' || wi1.verse_ayah) as cooccurrence_count
            FROM word_instances wi1
            JOIN word_type_morphemes wtm1 ON wi1.word_type_id = wtm1.word_type_id
            JOIN morpheme_types mt1 ON wtm1.morpheme_type_id = mt1.id
            JOIN word_instances wi2 ON wi1.verse_surah = wi2.verse_surah
                                   AND wi1.verse_ayah = wi2.verse_ayah
                                   AND wi1.id != wi2.id
            JOIN word_type_morphemes wtm2 ON wi2.word_type_id = wtm2.word_type_id
            JOIN morpheme_types mt2 ON wtm2.morpheme_type_id = mt2.id
            JOIN features f2 ON mt2.root_id = f2.id
            WHERE mt1.root_id = ? AND mt2.root_id != ?
            GROUP BY f2.id
            ORDER BY cooccurrence_count DESC
            LIMIT 20
        """, (root_feature_id, root_feature_id)).fetchall()

        cooccurring_roots = [{
            'root_id': r['id'],
            'root': r['lookup_key'],
            'root_ar': r['label_ar'],
            'connection': 'co_occurrence',
            'strength': r['cooccurrence_count'],
            'frequency': r['frequency'],
        } for r in cooccurring]

        return {
            "root": root_key,
            "root_ar": root_info['label_ar'],
            "shared_radical_connections": shared_consonant_roots,
            "co_occurring_roots": cooccurring_roots,
        }

    @server.tool()
    def verify_root_concordance(root_feature_id: int, proposed_meaning: str) -> dict:
        """Verify a proposed meaning for a root against ALL its Quranic instances.

        For each instance, provides:
        - Verse reference and text
        - Local curvature (how much this instance deviates from the pattern)
        - Lyapunov deviation (how unusual this usage is vs the root baseline)

        High-deviation instances are the most important to check —
        they are the potential falsifiers of the proposed meaning.

        Returns instances sorted by deviation (highest first) for efficient
        falsification-based verification.
        """
        conn = get_connection()

        root_info = conn.execute(
            "SELECT lookup_key, label_ar FROM features WHERE id = ?",
            (root_feature_id,)
        ).fetchone()
        if not root_info:
            return {"error": "Root not found"}

        instances = _get_root_instances(conn, root_feature_id)
        if not instances:
            return {"error": "No instances found"}

        # Compute baseline H* (average field state for this root)
        h_star = np.zeros((2, 2), dtype=complex)
        h_matrices = []
        for inst in instances:
            comps = _instance_to_h_components(conn, inst)
            h = get_h_matrix(comps)
            h_matrices.append(h)
            h_star += h
        h_star /= len(instances)

        # Compute deviation for each instance
        instance_results = []
        for i, inst in enumerate(instances):
            h = h_matrices[i]
            diff = h - h_star
            deviation = float(np.real(np.trace(diff.conj().T @ diff)))

            # Get verse text
            verse_text = compose_verse_text(conn, inst['verse_surah'], inst['verse_ayah'])

            # Get lemma for this instance
            lemma = None
            if inst.get('lemma_id'):
                lemma_row = conn.execute(
                    "SELECT lookup_key FROM features WHERE id = ?",
                    (inst['lemma_id'],)
                ).fetchone()
                if lemma_row:
                    lemma = lemma_row['lookup_key']

            instance_results.append({
                'ref': f"{inst['verse_surah']}:{inst['verse_ayah']}",
                'word_index': inst['word_index'],
                'word_text': inst['normalized_text'],
                'lemma': lemma,
                'deviation': round(deviation, 4),
                'verse_text': verse_text[:120] if verse_text else None,
            })

        # Sort by deviation (highest first — most likely to falsify)
        instance_results.sort(key=lambda x: x['deviation'], reverse=True)

        # Compute unique verse count and lemma distribution
        unique_verses = len(set(r['ref'] for r in instance_results))
        lemma_dist = {}
        for r in instance_results:
            if r['lemma']:
                lemma_dist[r['lemma']] = lemma_dist.get(r['lemma'], 0) + 1

        return {
            "root": root_info['lookup_key'],
            "root_ar": root_info['label_ar'],
            "proposed_meaning": proposed_meaning,
            "total_instances": len(instance_results),
            "unique_verses": unique_verses,
            "lemma_distribution": lemma_dist,
            "instances": instance_results,
            "note": "Instances sorted by deviation (highest first). High-deviation instances are the most important to check for falsification.",
        }

    @server.tool()
    def add_traditional_interpretation(surah: int, ayah: int, source: str,
                                       interpretation: str, language: str = "en") -> dict:
        """Add a traditional interpretation for a verse (for comparison purposes).

        Sources might be: 'ibn_kathir', 'tabari', 'zamakhshari', 'sahih_international', etc.
        These are stored as comparison baselines — NOT as authoritative readings.
        """
        conn = get_connection()
        conn.execute(
            """INSERT OR REPLACE INTO traditional_interpretations
               (surah, ayah, source, interpretation, language)
               VALUES (?, ?, ?, ?, ?)""",
            (surah, ayah, source, interpretation, language)
        )
        conn.commit()
        return {"status": "stored", "ref": f"{surah}:{ayah}", "source": source}

    @server.tool()
    def compare_with_traditional(surah: int, ayah: int) -> dict:
        """Compare Kalima research entries with traditional interpretations for a verse.

        Shows:
        1. The verse text (Arabic only)
        2. Any traditional interpretations stored
        3. Kalima research entries anchored to this verse or its features
        4. Feature emphasis analysis (which dimensions carry meaning)

        This allows the researcher to see WHERE interpretations diverge
        and which features drive the divergence.
        """
        conn = get_connection()

        verse_text = compose_verse_text(conn, surah, ayah)
        if not verse_text:
            return {"error": "Verse not found"}

        # Traditional interpretations
        trad_rows = conn.execute(
            "SELECT source, interpretation, language FROM traditional_interpretations WHERE surah = ? AND ayah = ?",
            (surah, ayah)
        ).fetchall()
        traditional = [dict(r) for r in trad_rows]

        # Kalima entries (from both entries and holonomic_entries)
        kalima_entries = []

        # From entries table (anchor_type='word_instance' with surah:ayah pattern)
        entry_rows = conn.execute(
            "SELECT address as id, content, phase, category, confidence, verification FROM holonomic_entries WHERE anchor_type='word_instance' AND anchor_ids LIKE ?",
            (f"{surah}:{ayah}%",)
        ).fetchall()
        for r in entry_rows:
            kalima_entries.append(dict(r))

        # From entries table (anchor_type='surah')
        surah_entries = conn.execute(
            "SELECT address as id, content, phase, category FROM holonomic_entries WHERE anchor_type='surah' AND anchor_ids = ?",
            (str(surah),)
        ).fetchall()
        for r in surah_entries:
            kalima_entries.append(dict(r))

        # Get feature emphasis for this verse
        from src.tools.dynamics import _get_verse_h_sequence, _compute_action_components
        words = _get_verse_h_sequence(conn, surah, ayah)
        action = _compute_action_components(conn, words)

        return {
            "ref": f"{surah}:{ayah}",
            "text": verse_text,
            "traditional_interpretations": traditional,
            "kalima_entries": kalima_entries,
            "emphasis": action["emphasis"],
            "note": "Traditional interpretations shown for comparison only. Kalima methodology requires internal Quranic evidence, not external authority.",
        }

    @server.tool()
    def analyze_diacritic_gauge(root_feature_id: int) -> dict:
        """Analyze the diacritic gauge orbit for a root.

        In HUFD's abjadic gauge field, consonantal roots are gauge-invariant
        (the topology), while diacritics are local gauge transformations U(θ).

        This tool shows:
        1. All diacritic patterns applied to this root's morphemes
        2. Which patterns preserve meaning (gauge-equivalent)
        3. Which patterns alter meaning (gauge-breaking)
        4. The gauge orbit (set of all surface forms from one root)

        Useful for understanding how the same root produces different
        semantic nuances through vowel variation.
        """
        conn = get_connection()

        root_info = conn.execute(
            "SELECT lookup_key, label_ar FROM features WHERE id = ?",
            (root_feature_id,)
        ).fetchone()
        if not root_info:
            return {"error": "Root not found"}

        # Get all morphemes with this root and their atom decomposition
        morphemes = conn.execute("""
            SELECT mt.id as morpheme_id, mt.uthmani_text,
                   mt.pos_id, mt.verb_form_id, mt.lemma_id,
                   f_pos.lookup_key as pos, f_lemma.lookup_key as lemma
            FROM morpheme_types mt
            LEFT JOIN features f_pos ON mt.pos_id = f_pos.id
            LEFT JOIN features f_lemma ON mt.lemma_id = f_lemma.id
            WHERE mt.root_id = ?
        """, (root_feature_id,)).fetchall()

        # Group by lemma to see gauge orbits
        lemma_orbits = {}
        for m in morphemes:
            lemma_key = m['lemma'] or 'unknown'

            # Get atoms (consonants + diacritics)
            atoms = conn.execute("""
                SELECT base_letter, diacritics FROM morpheme_atoms
                WHERE morpheme_type_id = ? ORDER BY position
            """, (m['morpheme_id'],)).fetchall()

            consonants = ''.join(a['base_letter'] for a in atoms if a['base_letter'].strip())
            diacritics_pattern = '|'.join(
                (a['diacritics'] or '-') for a in atoms
            )

            # Count instances
            count = conn.execute("""
                SELECT COUNT(*) FROM word_type_morphemes wtm
                JOIN word_instances wi ON wi.word_type_id = wtm.word_type_id
                WHERE wtm.morpheme_type_id = ?
            """, (m['morpheme_id'],)).fetchone()[0]

            orbit = lemma_orbits.setdefault(lemma_key, {
                'lemma': lemma_key,
                'forms': [],
                'total_instances': 0,
            })
            orbit['forms'].append({
                'text': m['uthmani_text'],
                'pos': m['pos'],
                'consonants': consonants,
                'diacritics': diacritics_pattern,
                'instances': count,
            })
            orbit['total_instances'] += count

        # Sort orbits by instance count
        orbits = sorted(lemma_orbits.values(), key=lambda o: o['total_instances'], reverse=True)

        # Summary: how many distinct surface forms per lemma (gauge orbit size)
        orbit_sizes = [len(o['forms']) for o in orbits]

        return {
            "root": root_info['lookup_key'],
            "root_ar": root_info['label_ar'],
            "total_lemmas": len(orbits),
            "total_forms": sum(orbit_sizes),
            "avg_orbit_size": round(sum(orbit_sizes) / max(len(orbit_sizes), 1), 1),
            "orbits": orbits[:20],
            "note": "Each lemma is a gauge orbit. Forms within the same orbit are gauge-equivalent (same root meaning, different diacritical realization).",
        }

    @server.tool()
    def get_pattern_fiber(root_feature_id: int) -> dict:
        \"\"\"Extract morphological patterns (awzan) for a root.
        
        Models the fiber structure connecting roots to surface forms.
        Each root has a bundle of patterns (Fibers) it participates in.
        Returns unique patterns with their instances.
        \"\"\"
        conn = get_connection()
        
        root_info = conn.execute(
            \"SELECT lookup_key, label_ar FROM features WHERE id = ?\",
            (root_feature_id,)
        ).fetchone()
        if not root_info:
            return {\"error\": \"Root not found\"}
            
        root_key = root_info['lookup_key']
        # Extract the 3 root letters
        r_letters = [c.strip() for c in root_key.split('-') if c.strip()]
        if len(r_letters) != 3:
            return {\"error\": f\"Pattern extraction only supported for 3-letter roots. Found: {root_key}\"}

        # Get all morphemes for this root
        morphemes = conn.execute(\"\"\"
            SELECT id, uthmani_text FROM morpheme_types WHERE root_id = ?
        \"\"\", (root_feature_id,)).fetchall()
        
        patterns = {}
        for m in morphemes:
            # Get atoms
            atoms = conn.execute(\"\"\"
                SELECT base_letter, diacritics FROM morpheme_atoms 
                WHERE morpheme_type_id = ? ORDER BY position
            \"\"\", (m['id'],)).fetchall()
            
            # Map atoms to a skeleton
            # We look for the 3 root letters in order
            skeleton = []
            r_idx = 0
            for a in atoms:
                base = a['base_letter'] or ''
                diac = a['diacritics'] or ''
                
                if r_idx < 3 and base == r_letters[r_idx]:
                    # Replace with F-'-L placeholders
                    placeholder = ['ف', 'ع', 'ل'][r_idx]
                    skeleton.append(placeholder + diac)
                    r_idx += 1
                else:
                    skeleton.append(base + diac)
            
            wazn = ''.join(skeleton)
            entry = patterns.setdefault(wazn, {'pattern': wazn, 'morphemes': [], 'count': 0})
            if m['uthmani_text'] not in entry['morphemes']:
                entry['morphemes'].append(m['uthmani_text'])
            entry['count'] += 1
            
        return {
            "root": root_key,
            "root_ar": root_info['label_ar'],
            "fibers": sorted(patterns.values(), key=lambda x: x['count'], reverse=True)
        }

        @server.tool()
        def root_distance(root_a_id: int, root_b_id: int) -> dict:
        \"\"\"Calculate the geodesic distance between two roots in the manifold.

        Distance is derived from co-occurrence and radical similarity.
        High co-occurrence = Low distance (Strong semantic entanglement).
        \"\"\"
        conn = get_connection()

        # Try to fetch from cache
        row = conn.execute(\"\"\"
            SELECT cooccurrence_count, geodesic_distance FROM root_cooccurrence
            WHERE (root_a_id = ? AND root_b_id = ?) OR (root_a_id = ? AND root_b_id = ?)
        \"\"\", (root_a_id, root_b_id, root_b_id, root_a_id)).fetchone()

        if row:
            return {
                \"root_a\": root_a_id,
                \"root_b\": root_b_id,
                \"cooccurrence\": row['cooccurrence_count'],
                \"distance\": row['geodesic_distance']
            }

        # If not in cache, compute a live estimate (P1.5)
        # 1. Get shared radicals
        row_a = conn.execute(\"SELECT lookup_key FROM features WHERE id = ?\", (root_a_id,)).fetchone()
        row_b = conn.execute(\"SELECT lookup_key FROM features WHERE id = ?\", (root_b_id,)).fetchone()
        if not row_a or not row_b:
            return {\"error\": \"One or both roots not found\"}

        rad_a = set(c.strip() for c in row_a[0].split('-') if c.strip())
        rad_b = set(c.strip() for c in row_b[0].split('-') if c.strip())
        shared = rad_a & rad_b
        radical_similarity = len(shared) / max(len(rad_a), len(rad_b), 1)

        # 2. Get co-occurrence count
        cooc = conn.execute(\"\"\"
            SELECT COUNT(DISTINCT wi1.verse_surah || ':' || wi1.verse_ayah)
            FROM word_instances wi1
            JOIN word_type_morphemes wtm1 ON wi1.word_type_id = wtm1.word_type_id
            JOIN morpheme_types mt1 ON wtm1.morpheme_type_id = mt1.id
            JOIN word_instances wi2 ON wi1.verse_surah = wi2.verse_surah AND wi1.verse_ayah = wi2.verse_ayah
            JOIN word_type_morphemes wtm2 ON wi2.word_type_id = wtm2.word_type_id
            JOIN morpheme_types mt2 ON wtm2.morpheme_type_id = mt2.id
            WHERE mt1.root_id = ? AND mt2.root_id = ?
        \"\"\", (root_a_id, root_b_id)).fetchone()[0]

        # 3. Compute Distance: Inverse of (Radical similarity + normalized co-occurrence)
        # (This is a simplified metric for P1.5 completion)
        normalized_cooc = min(cooc / 10.0, 1.0) # Assume 10+ is very strong
        strength = radical_similarity * 0.5 + normalized_cooc * 0.5
        distance = 1.0 / (strength + 0.01) # Avoid div by zero

        # Cache it
        conn.execute(\"\"\"
            INSERT OR REPLACE INTO root_cooccurrence (root_a_id, root_b_id, cooccurrence_count, geodesic_distance)
            VALUES (?, ?, ?, ?)
        \"\"\", (root_a_id, root_b_id, cooc, distance))
        conn.commit()

        return {
            \"root_a\": row_a[0],
            \"root_b\": row_b[0],
            \"shared_radicals\": list(shared),
            \"cooccurrence\": cooc,
            \"geodesic_distance\": round(distance, 4)
        }

