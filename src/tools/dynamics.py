"""HUFD Field Dynamics: Phase-Lock, Drift Energy, Emphasis Detection.

Implements the dynamic components of the HUFD Action Functional:
  S_HUFD = Tr(R²) + α·L_semantic + β·E_d + γ·Φ⁻¹

Where:
  Tr(R²)      = curvature energy (structural tension)
  L_semantic   = Lyapunov deviation from archetypal baseline
  E_d          = drift energy (positional/temporal significance)
  Φ            = phase-lock index (coherence between successive states)

These four terms decompose into emphasis types for Quranic interpretation:
  - High Tr(R²)     → root-level meaning is active
  - High L_semantic  → unusual usage → morpheme/form emphasis
  - High E_d         → position in sentence matters
  - Low Φ            → boundary (speaker change, time shift, topic break)
"""

import math
import sqlite3
import numpy as np
from mcp.server.fastmcp import FastMCP
from ..db import get_connection
from ..utils.hufd_math import (
    get_h_matrix, calculate_curvature_tensor,
    get_discrete_curvature, get_field_tension,
    features_to_h_components
)
from ..utils.units import compose_verse_text, compose_word_text


def _get_verse_h_sequence(conn: sqlite3.Connection, surah: int, ayah: int) -> list[dict]:
    """Get all words in a verse with their su(2) field connections.

    Returns list of {id, word_index, text, h_matrix, features} dicts.
    """
    rows = conn.execute("""
        SELECT wi.id, wi.word_index, wi.normalized_text, wi.word_type_id,
               mt.root_id, mt.lemma_id, mt.pos_id, mt.verb_form_id,
               mt.voice_id, mt.mood_id, mt.aspect_id,
               mt.person_id, mt.number_id, mt.gender_id, mt.case_value_id
        FROM word_instances wi
        JOIN word_type_morphemes wtm ON wi.word_type_id = wtm.word_type_id
        JOIN morpheme_types mt ON wtm.morpheme_type_id = mt.id
        WHERE wi.verse_surah = ? AND wi.verse_ayah = ?
        ORDER BY wi.word_index, wtm.position
    """, (surah, ayah)).fetchall()

    # Group by word_index, take first morpheme for field computation
    words = {}
    for r in rows:
        idx = r['word_index']
        if idx in words:
            continue

        h_mat = get_h_matrix(features_to_h_components(conn, dict(r)))

        words[idx] = {
            'id': r['id'],
            'word_index': idx,
            'text': r['normalized_text'],
            'h_matrix': h_mat,
            'features': {
                'root_id': r['root_id'],
                'lemma_id': r['lemma_id'],
                'pos_id': r['pos_id'],
                'verb_form_id': r['verb_form_id'],
            }
        }

    return [words[k] for k in sorted(words.keys())]


# ── Phase-Lock Index Φ ──────────────────────────────────────────────

def _compute_phase_lock(h_a: np.ndarray, h_b: np.ndarray) -> float:
    """Phase-Lock Index Φ = |⟨ψ_a, ψ_b⟩| normalized.

    Φ → 1: full coherence (same speaker, same topic, continuation)
    Φ → 0: decoherence (boundary, speaker change, time shift)

    Uses the Hilbert-Schmidt inner product on su(2) matrices:
      Φ = |Tr(H_a† · H_b)| / sqrt(Tr(H_a† · H_a) · Tr(H_b† · H_b))
    """
    inner = np.trace(h_a.conj().T @ h_b)
    norm_a = np.trace(h_a.conj().T @ h_a)
    norm_b = np.trace(h_b.conj().T @ h_b)

    denom = np.sqrt(np.abs(norm_a) * np.abs(norm_b))
    if denom < 1e-12:
        return 0.0

    return float(np.clip(np.abs(inner) / denom, 0.0, 1.0))


def _verse_aggregate_h(conn: sqlite3.Connection, surah: int, ayah: int) -> np.ndarray:
    """Aggregate H matrix for a verse (path-ordered product of word connections)."""
    from scipy.linalg import expm
    words = _get_verse_h_sequence(conn, surah, ayah)
    if not words:
        return np.zeros((2, 2), dtype=complex)

    result = np.eye(2, dtype=complex)
    for w in words:
        result = result @ expm(w['h_matrix'])
    return result


# ── Drift Energy E_d ────────────────────────────────────────────────

def _compute_drift_energy(h_prev: np.ndarray, h_curr: np.ndarray) -> float:
    """Drift Energy E_d = ‖∇_t ψ‖² = ‖H_curr - H_prev‖²_F.

    High E_d at a position = that position is semantically loaded.
    Measures how much the field changes between consecutive states.
    """
    diff = h_curr - h_prev
    return float(np.real(np.trace(diff.conj().T @ diff)))


# ── Semantic Lyapunov L_semantic ────────────────────────────────────

def _compute_lyapunov(conn: sqlite3.Connection, h_matrix: np.ndarray,
                      root_id: int | None) -> float:
    """Semantic Lyapunov L_semantic = ‖H - H*‖² where H* is the archetypal baseline.

    H* = average field state for all instances of this root across the Quran.
    High L_semantic = unusual usage (morpheme emphasis over root).
    Low L_semantic = typical usage (root carries the meaning).
    """
    if not root_id:
        return 0.0

    # Get all instances of this root to compute the baseline H*
    rows = conn.execute("""
        SELECT mt.pos_id, mt.verb_form_id, mt.voice_id, mt.mood_id,
               mt.aspect_id, mt.person_id, mt.number_id, mt.gender_id,
               mt.case_value_id
        FROM morpheme_types mt
        WHERE mt.root_id = ?
    """, (root_id,)).fetchall()

    if not rows:
        return 0.0

    # Compute average H* (archetypal baseline for this root)
    h_star = np.zeros((2, 2), dtype=complex)
    count = 0
    for r in rows:
        comps = features_to_h_components(conn, dict(r))
        h_star += get_h_matrix(comps)
        count += 1

    if count > 0:
        h_star /= count

    # L_semantic = ‖H - H*‖²_F
    diff = h_matrix - h_star
    return float(np.real(np.trace(diff.conj().T @ diff)))


# ── HUFD Action Decomposition ──────────────────────────────────────

def _compute_action_components(conn: sqlite3.Connection, words: list[dict]) -> dict:
    """Compute the four HUFD action components for a sequence of words.

    Returns per-word decomposition + aggregate emphasis profile.
    """
    if not words:
        return {"words": [], "emphasis": {}}

    per_word = []
    total_curvature = 0.0
    total_lyapunov = 0.0
    total_drift = 0.0
    total_phase = 0.0

    for i, w in enumerate(words):
        h = w['h_matrix']

        # Tr(R²): curvature energy
        curvature = get_field_tension(h)

        # L_semantic: deviation from root baseline
        lyapunov = _compute_lyapunov(conn, h, w['features'].get('root_id'))

        # E_d: drift from previous word
        if i > 0:
            drift = _compute_drift_energy(words[i-1]['h_matrix'], h)
        else:
            drift = 0.0

        # Φ: phase-lock with next word
        if i < len(words) - 1:
            phase = _compute_phase_lock(h, words[i+1]['h_matrix'])
        else:
            phase = 1.0

        per_word.append({
            'word_index': w['word_index'],
            'text': w['text'],
            'curvature': round(curvature, 4),
            'lyapunov': round(lyapunov, 4),
            'drift': round(drift, 4),
            'phase_lock': round(phase, 4),
        })

        total_curvature += curvature
        total_lyapunov += lyapunov
        total_drift += drift
        total_phase += phase

    n = len(words)
    total = total_curvature + total_lyapunov + total_drift + max(0.001, 1.0 - total_phase / n)

    if total < 1e-12:
        emphasis = {'root': 0.25, 'morpheme': 0.25, 'position': 0.25, 'boundary': 0.25}
    else:
        emphasis = {
            'root': round(total_curvature / total, 3),
            'morpheme': round(total_lyapunov / total, 3),
            'position': round(total_drift / total, 3),
            'boundary': round(max(0.001, 1.0 - total_phase / n) / total, 3),
        }

    return {"words": per_word, "emphasis": emphasis}


# ── MCP Tool Registration ──────────────────────────────────────────

def register(server: FastMCP):

    @server.tool()
    def analyze_verse_emphasis(surah: int, ayah: int) -> dict:
        """Analyze which feature dimensions carry meaning in a verse.

        Uses HUFD action decomposition to determine emphasis:
          - root: structural meaning (curvature energy Tr(R²))
          - morpheme: unusual form/usage (Lyapunov deviation L_semantic)
          - position: word placement matters (drift energy E_d)
          - boundary: verse contains a break point (phase-lock Φ)

        Returns per-word metrics and aggregate emphasis profile.
        """
        conn = get_connection()
        verse_text = compose_verse_text(conn, surah, ayah)
        if not verse_text:
            return {"error": "Verse not found"}

        words = _get_verse_h_sequence(conn, surah, ayah)
        action = _compute_action_components(conn, words)

        return {
            "ref": f"{surah}:{ayah}",
            "text": verse_text,
            "emphasis": action["emphasis"],
            "words": action["words"],
        }

    @server.tool()
    def detect_boundaries(surah: int, start_ayah: int, end_ayah: int) -> dict:
        """Detect speaker changes, temporal shifts, and topic boundaries in a passage.

        Uses Phase-Lock Index Φ between consecutive verses:
          - Φ > 0.7: continuation (same speaker/time/topic)
          - 0.3 < Φ < 0.7: transition zone (gradual shift)
          - Φ < 0.3: boundary (speaker change, time shift, new topic)

        Also detects mid-verse breaks via internal phase-lock drops.
        """
        conn = get_connection()

        boundaries = []
        prev_h = None

        for ayah in range(start_ayah, end_ayah + 1):
            verse_text = compose_verse_text(conn, surah, ayah)
            if not verse_text:
                continue

            curr_h = _verse_aggregate_h(conn, surah, ayah)

            # Inter-verse phase-lock
            if prev_h is not None:
                phi = _compute_phase_lock(prev_h, curr_h)
                if phi < 0.7:
                    if phi < 0.3:
                        btype = "hard_boundary"
                    else:
                        btype = "soft_transition"
                    boundaries.append({
                        "between": f"{surah}:{ayah-1} → {surah}:{ayah}",
                        "phase_lock": round(phi, 4),
                        "type": btype,
                    })

            # Intra-verse phase-lock (detect mid-verse breaks)
            words = _get_verse_h_sequence(conn, surah, ayah)
            for i in range(len(words) - 1):
                word_phi = _compute_phase_lock(
                    words[i]['h_matrix'], words[i+1]['h_matrix']
                )
                if word_phi < 0.3:
                    boundaries.append({
                        "within": f"{surah}:{ayah} word {words[i]['word_index']}→{words[i+1]['word_index']}",
                        "phase_lock": round(word_phi, 4),
                        "type": "intra_verse_break",
                    })

            prev_h = curr_h

        # Build verse chain with phase-lock values
        verse_chain = []
        prev_h = None
        for ayah in range(start_ayah, end_ayah + 1):
            verse_text = compose_verse_text(conn, surah, ayah)
            if not verse_text:
                continue
            curr_h = _verse_aggregate_h(conn, surah, ayah)
            phi_with_prev = _compute_phase_lock(prev_h, curr_h) if prev_h is not None else None
            verse_chain.append({
                "ayah": ayah,
                "text": verse_text[:80] + ("..." if len(verse_text) > 80 else ""),
                "phi_with_previous": round(phi_with_prev, 4) if phi_with_prev is not None else None,
            })
            prev_h = curr_h

        return {
            "surah": surah,
            "range": f"{start_ayah}-{end_ayah}",
            "boundaries": boundaries,
            "verse_chain": verse_chain,
        }

    @server.tool()
    def measure_phase_lock(surah: int, ayah_a: int, ayah_b: int) -> dict:
        """Measure phase coherence between two specific verses.

        Φ = |⟨ψ_a, ψ_b⟩| using Hilbert-Schmidt inner product on su(2).

        Interpretation:
          Φ > 0.7 → same speaker/time/topic (continuation)
          0.3-0.7 → transitional
          Φ < 0.3 → different context (boundary)
        """
        conn = get_connection()

        text_a = compose_verse_text(conn, surah, ayah_a)
        text_b = compose_verse_text(conn, surah, ayah_b)
        if not text_a or not text_b:
            return {"error": "One or both verses not found"}

        h_a = _verse_aggregate_h(conn, surah, ayah_a)
        h_b = _verse_aggregate_h(conn, surah, ayah_b)
        phi = _compute_phase_lock(h_a, h_b)

        if phi > 0.7:
            interpretation = "continuation"
        elif phi > 0.3:
            interpretation = "transition"
        else:
            interpretation = "boundary"

        return {
            "verse_a": f"{surah}:{ayah_a}",
            "verse_b": f"{surah}:{ayah_b}",
            "phase_lock": round(phi, 4),
            "interpretation": interpretation,
        }

    @server.tool()
    def compute_passage_drift(surah: int, start_ayah: int, end_ayah: int) -> dict:
        """Compute drift energy across a passage to find semantically loaded positions.

        E_d = ‖∇_t ψ‖² — how much the field changes between words/verses.
        High drift = that position carries special significance.
        """
        conn = get_connection()

        verse_results = []
        for ayah in range(start_ayah, end_ayah + 1):
            verse_text = compose_verse_text(conn, surah, ayah)
            if not verse_text:
                continue

            words = _get_verse_h_sequence(conn, surah, ayah)
            word_drifts = []
            max_drift = 0.0
            max_drift_word = None

            for i in range(len(words)):
                if i > 0:
                    drift = _compute_drift_energy(words[i-1]['h_matrix'], words[i]['h_matrix'])
                else:
                    drift = 0.0

                word_drifts.append({
                    'word_index': words[i]['word_index'],
                    'text': words[i]['text'],
                    'drift': round(drift, 4),
                })

                if drift > max_drift:
                    max_drift = drift
                    max_drift_word = words[i]['text']

            verse_results.append({
                'ayah': ayah,
                'text': verse_text[:80] + ("..." if len(verse_text) > 80 else ""),
                'peak_drift': round(max_drift, 4),
                'peak_word': max_drift_word,
                'words': word_drifts,
            })

        return {
            "surah": surah,
            "range": f"{start_ayah}-{end_ayah}",
            "verses": verse_results,
        }
