"""Bridge: DB queries → pure math objects.

This is the ONLY file in Scholar that imports from the DB layer to produce 
objects for the Geometer math library. It queries the database and produces 
RootVectors and word_data lists that the pure math functions consume.
"""

import math
import sqlite3
from kalima_math.gauge import get_h_matrix, SIGMAS
from kalima_math.root_space import RootVector, build_root_vector


_surprisal_cache: dict[int, float] = {}

def get_surprisal(conn: sqlite3.Connection, feature_id: int | None) -> float:
    """Information content of a feature value: -log(p)."""
    if feature_id is None: return 0.0
    if feature_id in _surprisal_cache: return _surprisal_cache[feature_id]

    row = conn.execute("SELECT frequency FROM features WHERE id = ?", (feature_id,)).fetchone()
    if not row or not row['frequency'] or row['frequency'] <= 0:
        _surprisal_cache[feature_id] = 0.0
        return 0.0

    # Normalized against total corpus size ~128k morphemes
    val = math.log(max(128000 / row['frequency'], 1.0))
    _surprisal_cache[feature_id] = val
    return val


def _address_to_component(address: str | None) -> float:
    """Project a hex UOR address onto a real scalar [-1, 1].

    This is the coupling constant for the root identity in the field.
    """
    if not address: return 0.0
    seed = int(address[:8], 16)
    return (seed / 0xFFFFFFFF) * 2.0 - 1.0


def features_to_h_components(conn: sqlite3.Connection, feat_row: dict, root_addr: str | None = None) -> list[float]:
    """HUFD Mapping: Maps linguistic features to su(2) gauge components [x, y, z].

    x: Semantic Identity (Root + Lemma Surprisal + UOR Coupling)
    y: Morphological Action (Verb Form + Aspect + Person + Gender + Number)
    z: Syntactic Position (POS + Case + Voice + Mood)
    """
    SCALE = 0.1 # Numerical stability for su(2) exponentials

    # x-component: The 'What' (Identity)
    raw_x = (get_surprisal(conn, feat_row.get('root_id')) +
             get_surprisal(conn, feat_row.get('lemma_id')))

    if root_addr:
        raw_x += _address_to_component(root_addr)

    # y-component: The 'How' (Action/Morphology)
    raw_y = (get_surprisal(conn, feat_row.get('verb_form_id')) +
             get_surprisal(conn, feat_row.get('aspect_id')) +
             get_surprisal(conn, feat_row.get('person_id')) +
             get_surprisal(conn, feat_row.get('gender_id')) +
             get_surprisal(conn, feat_row.get('number_id')))

    # z-component: The 'Where' (Syntax/Function)
    raw_z = (get_surprisal(conn, feat_row.get('pos_id')) +
             get_surprisal(conn, feat_row.get('case_value_id')) +
             get_surprisal(conn, feat_row.get('voice_id')) +
             get_surprisal(conn, feat_row.get('mood_id')))

    # In a full implementation, we'd apply the Information Geometric Metric g_mu_nu here.
    # For now, we use the raw surprisal vector.
    return [raw_x * SCALE, raw_y * SCALE, raw_z * SCALE]


def _feature_lookup_key(conn: sqlite3.Connection, feature_id: int | None) -> str | None:
    """Resolve a feature ID to its lookup_key."""
    if not feature_id:
        return None
    row = conn.execute("SELECT lookup_key FROM features WHERE id = ?", (feature_id,)).fetchone()
    return row["lookup_key"] if row else None


def build_root_vectors_for_verse(conn: sqlite3.Connection, surah: int, ayah: int) -> dict[int, RootVector]:
    """Build RootVectors for all roots that appear in a verse.

    Returns dict mapping root_id → RootVector.
    """
    # Find all root IDs in this verse
    root_ids = conn.execute("""
        SELECT DISTINCT mt.root_id
        FROM word_instances wi
        JOIN word_type_morphemes wtm ON wi.word_type_id = wtm.word_type_id
        JOIN morpheme_types mt ON wtm.morpheme_type_id = mt.id
        WHERE wi.verse_surah = ? AND wi.verse_ayah = ? AND mt.root_id IS NOT NULL
    """, (surah, ayah)).fetchall()

    result = {}
    for row in root_ids:
        rid = row["root_id"]
        if rid not in result:
            rv = build_root_vector_from_db(conn, rid)
            if rv:
                result[rid] = rv
    return result


def build_root_vectors_for_passage(conn: sqlite3.Connection, surah: int,
                                    start_ayah: int, end_ayah: int) -> dict[int, RootVector]:
    """Build RootVectors for all roots in a range of verses."""
    root_ids = conn.execute("""
        SELECT DISTINCT mt.root_id
        FROM word_instances wi
        JOIN word_type_morphemes wtm ON wi.word_type_id = wtm.word_type_id
        JOIN morpheme_types mt ON wtm.morpheme_type_id = mt.id
        WHERE wi.verse_surah = ? AND wi.verse_ayah BETWEEN ? AND ?
              AND mt.root_id IS NOT NULL
    """, (surah, start_ayah, end_ayah)).fetchall()

    result = {}
    for row in root_ids:
        rid = row["root_id"]
        if rid not in result:
            rv = build_root_vector_from_db(conn, rid)
            if rv:
                result[rid] = rv
    return result


def build_root_vector_from_db(conn: sqlite3.Connection, root_id: int) -> RootVector | None:
    """Build a RootVector for a single root from the database.

    Queries ALL Quranic instances of this root to build its full
    distributional profile.
    """
    # Root info
    root_info = conn.execute(
        "SELECT lookup_key, label_ar FROM features WHERE id = ?", (root_id,)
    ).fetchone()
    if not root_info:
        return None

    # All morpheme types for this root with their features
    morphemes = conn.execute("""
        SELECT mt.id,
               f_pos.lookup_key as pos,
               f_vf.lookup_key as verb_form,
               f_asp.lookup_key as aspect,
               f_per.lookup_key as person,
               f_num.lookup_key as number,
               f_gen.lookup_key as gender,
               f_cas.lookup_key as case_value,
               f_lem.lookup_key as lemma
        FROM morpheme_types mt
        LEFT JOIN features f_pos ON mt.pos_id = f_pos.id
        LEFT JOIN features f_vf ON mt.verb_form_id = f_vf.id
        LEFT JOIN features f_asp ON mt.aspect_id = f_asp.id
        LEFT JOIN features f_per ON mt.person_id = f_per.id
        LEFT JOIN features f_num ON mt.number_id = f_num.id
        LEFT JOIN features f_gen ON mt.gender_id = f_gen.id
        LEFT JOIN features f_cas ON mt.case_value_id = f_cas.id
        LEFT JOIN features f_lem ON mt.lemma_id = f_lem.id
        WHERE mt.root_id = ?
    """, (root_id,)).fetchall()

    morpheme_features = [dict(m) for m in morphemes]

    # All word instance locations for this root
    locations = conn.execute("""
        SELECT wi.verse_surah, wi.verse_ayah
        FROM word_instances wi
        JOIN word_type_morphemes wtm ON wi.word_type_id = wtm.word_type_id
        JOIN morpheme_types mt ON wtm.morpheme_type_id = mt.id
        WHERE mt.root_id = ?
    """, (root_id,)).fetchall()

    instance_locations = [(r["verse_surah"], r["verse_ayah"]) for r in locations]

    # Co-occurrence fingerprint (shared verses with other roots)
    cooccurrences = conn.execute("""
        SELECT mt2.root_id, COUNT(DISTINCT wi1.verse_surah || ':' || wi1.verse_ayah) as count
        FROM word_instances wi1
        JOIN word_type_morphemes wtm1 ON wi1.word_type_id = wtm1.word_type_id
        JOIN morpheme_types mt1 ON wtm1.morpheme_type_id = mt1.id
        JOIN word_instances wi2 ON wi1.verse_surah = wi2.verse_surah
                                AND wi1.verse_ayah = wi2.verse_ayah
        JOIN word_type_morphemes wtm2 ON wi2.word_type_id = wtm2.word_type_id
        JOIN morpheme_types mt2 ON wtm2.morpheme_type_id = mt2.id
        WHERE mt1.root_id = ? AND mt2.root_id != ?
        GROUP BY mt2.root_id
    """, (root_id, root_id)).fetchall()

    cooccurrence_counts = {r["root_id"]: r["count"] for r in cooccurrences}

    return build_root_vector(
        root_id=root_id,
        lookup_key=root_info["lookup_key"],
        label_ar=root_info["label_ar"],
        morpheme_features=morpheme_features,
        instance_locations=instance_locations,
        cooccurrence_counts=cooccurrence_counts,
    )


def get_verse_word_data(conn: sqlite3.Connection, surah: int, ayah: int) -> list[dict]:
    """Get word-level data for a verse in the format analyze_verse() expects.

    Returns list of dicts with keys:
        word_index, text, surah, ayah, root_id, instance_features
    """
    rows = conn.execute("""
        SELECT wi.word_index, wi.normalized_text,
               mt.root_id, mt.pos_id, mt.verb_form_id, mt.aspect_id,
               mt.person_id, mt.number_id, mt.gender_id, mt.case_value_id
        FROM word_instances wi
        JOIN word_type_morphemes wtm ON wi.word_type_id = wtm.word_type_id
        JOIN morpheme_types mt ON wtm.morpheme_type_id = mt.id
        WHERE wi.verse_surah = ? AND wi.verse_ayah = ?
        ORDER BY wi.word_index, wtm.position
    """, (surah, ayah)).fetchall()

    # Group by word_index, take first morpheme (primary morpheme)
    words = {}
    for r in rows:
        idx = r["word_index"]
        if idx in words:
            continue

        # Resolve feature IDs to lookup_keys for instance_features
        instance_features = {}
        for feat_key, feat_col in [
            ("pos", "pos_id"), ("verb_form", "verb_form_id"),
            ("aspect", "aspect_id"), ("person", "person_id"),
            ("number", "number_id"), ("gender", "gender_id"),
            ("case_value", "case_value_id"),
        ]:
            fid = r[feat_col]
            if fid:
                lk = _feature_lookup_key(conn, fid)
                if lk:
                    instance_features[feat_key] = lk

        words[idx] = {
            "word_index": idx,
            "text": r["normalized_text"],
            "surah": surah,
            "ayah": ayah,
            "root_id": r["root_id"],
            "instance_features": instance_features,
        }

    return [words[k] for k in sorted(words.keys())]
