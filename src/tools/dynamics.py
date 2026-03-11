"""Verse Dynamics: Emphasis, Boundaries, Drift, and Phase-Lock.

Thin tool layer — queries DB, passes clean data to src/math/, returns results.
All math lives in src/math/verse_dynamics.py and src/math/root_space.py.

Four signals per word:
  - weight:    distributional centrality of the root (structural pillar vs peripheral)
  - anomaly:   how unusual this specific usage is for this root
  - drift:     morphological profile distance from previous word
  - coherence: profile similarity with next word

Aggregate emphasis profile per verse:
  - root:      how much structural root weight drives this verse
  - anomaly:   how much unusual usage drives this verse
  - position:  how much word-order dynamics drive this verse
  - boundary:  how much coherence drop signals a break
"""

from mcp.server.fastmcp import FastMCP
from ..db import get_connection
from ..utils.units import compose_verse_text
from ..math.bridge import (
    build_root_vectors_for_verse,
    build_root_vectors_for_passage,
    get_verse_word_data,
)
from ..math.verse_dynamics import analyze_verse, verse_coherence


def register(server: FastMCP):

    @server.tool()
    def analyze_verse_emphasis(surah: int, ayah: int) -> dict:
        """Analyze which feature dimensions carry meaning in a verse.

        Emphasis dimensions:
          - root: structural meaning (distributional weight of active roots)
          - anomaly: unusual form/usage (instance anomaly vs root baseline)
          - position: word placement matters (morphological drift between words)
          - boundary: verse contains a break point (coherence drop)

        Returns per-word metrics and aggregate emphasis profile.
        """
        conn = get_connection()
        verse_text = compose_verse_text(conn, surah, ayah)
        if not verse_text:
            return {"error": "Verse not found"}

        word_data = get_verse_word_data(conn, surah, ayah)
        root_vectors = build_root_vectors_for_verse(conn, surah, ayah)
        analysis = analyze_verse(word_data, root_vectors)

        words_out = []
        for w in analysis.words:
            words_out.append({
                "word_index": w.word_index,
                "text": w.text,
                "root": w.root_key,
                "weight": w.weight,
                "anomaly": w.anomaly,
                "drift": w.drift,
                "coherence": w.coherence,
                "energy": round(w.energy, 4),
            })

        return {
            "ref": f"{surah}:{ayah}",
            "text": verse_text,
            "emphasis": analysis.emphasis,
            "dominant": analysis.dominant_dimension,
            "hot_words": [{"text": w.text, "root": w.root_key, "energy": round(w.energy, 3)}
                          for w in analysis.hot_words],
            "active_roots": [{"root": r, "weight": round(wt, 3)} for r, wt in analysis.active_roots],
            "words": words_out,
        }

    @server.tool()
    def detect_boundaries(surah: int, start_ayah: int, end_ayah: int) -> dict:
        """Detect speaker changes, temporal shifts, and topic boundaries in a passage.

        Uses verse coherence (instance agreement + root profile drift + topic overlap):
          - coherence > 0.5: continuation (same speaker/time/topic)
          - 0.25 < coherence < 0.5: transition zone
          - coherence < 0.25: boundary (speaker change, time shift, new topic)

        Also detects intra-verse breaks via word-level coherence drops.
        """
        conn = get_connection()
        root_vectors = build_root_vectors_for_passage(conn, surah, start_ayah, end_ayah)

        # Build analyses for all verses
        verse_analyses = {}
        verse_word_data = {}
        for ayah in range(start_ayah, end_ayah + 1):
            vt = compose_verse_text(conn, surah, ayah)
            if not vt:
                continue
            wd = get_verse_word_data(conn, surah, ayah)
            va = analyze_verse(wd, root_vectors)
            verse_analyses[ayah] = va
            verse_word_data[ayah] = wd

        # Detect boundaries
        boundaries = []
        verse_chain = []
        prev_ayah = None

        for ayah in sorted(verse_analyses.keys()):
            va = verse_analyses[ayah]
            vt = compose_verse_text(conn, surah, ayah)

            coh_with_prev = None
            if prev_ayah is not None:
                coh_with_prev = verse_coherence(
                    verse_analyses[prev_ayah], va, root_vectors,
                    verse_word_data[prev_ayah], verse_word_data[ayah],
                )
                if coh_with_prev < 0.5:
                    btype = "hard_boundary" if coh_with_prev < 0.25 else "soft_transition"
                    boundaries.append({
                        "between": f"{surah}:{prev_ayah} → {surah}:{ayah}",
                        "coherence": coh_with_prev,
                        "type": btype,
                    })

            # Intra-verse breaks: find words with coherence < 0.3
            for w in va.words:
                if w.coherence is not None and w.coherence < 0.3 and w.word_index < len(va.words) - 1:
                    boundaries.append({
                        "within": f"{surah}:{ayah} after word {w.word_index} ({w.text})",
                        "coherence": w.coherence,
                        "type": "intra_verse_break",
                    })

            verse_chain.append({
                "ayah": ayah,
                "text": vt[:80] + ("..." if len(vt) > 80 else "") if vt else "",
                "coherence_with_previous": coh_with_prev,
                "emphasis": va.emphasis,
            })
            prev_ayah = ayah

        return {
            "surah": surah,
            "range": f"{start_ayah}-{end_ayah}",
            "boundaries": boundaries,
            "verse_chain": verse_chain,
        }

    @server.tool()
    def measure_phase_lock(surah: int, ayah_a: int, ayah_b: int) -> dict:
        """Measure coherence between two specific verses.

        Combines instance-level feature agreement, root profile similarity,
        and topic overlap into a single coherence score.

        Interpretation:
          > 0.5 → continuation (same speaker/time/topic)
          0.25-0.5 → transitional
          < 0.25 → boundary (different context)
        """
        conn = get_connection()

        text_a = compose_verse_text(conn, surah, ayah_a)
        text_b = compose_verse_text(conn, surah, ayah_b)
        if not text_a or not text_b:
            return {"error": "One or both verses not found"}

        root_vectors = build_root_vectors_for_passage(conn, surah, ayah_a, ayah_b)
        wd_a = get_verse_word_data(conn, surah, ayah_a)
        wd_b = get_verse_word_data(conn, surah, ayah_b)
        va = analyze_verse(wd_a, root_vectors)
        vb = analyze_verse(wd_b, root_vectors)

        coh = verse_coherence(va, vb, root_vectors, wd_a, wd_b)

        if coh > 0.5:
            interpretation = "continuation"
        elif coh > 0.25:
            interpretation = "transition"
        else:
            interpretation = "boundary"

        return {
            "verse_a": f"{surah}:{ayah_a}",
            "verse_b": f"{surah}:{ayah_b}",
            "coherence": coh,
            "interpretation": interpretation,
            "emphasis_a": va.emphasis,
            "emphasis_b": vb.emphasis,
        }

    @server.tool()
    def compute_passage_drift(surah: int, start_ayah: int, end_ayah: int) -> dict:
        """Compute drift energy across a passage to find semantically loaded positions.

        Drift = morphological profile distance between adjacent words.
        High drift = the text shifts semantic/grammatical gears at that point.
        """
        conn = get_connection()
        root_vectors = build_root_vectors_for_passage(conn, surah, start_ayah, end_ayah)

        verse_results = []
        for ayah in range(start_ayah, end_ayah + 1):
            verse_text = compose_verse_text(conn, surah, ayah)
            if not verse_text:
                continue

            word_data = get_verse_word_data(conn, surah, ayah)
            analysis = analyze_verse(word_data, root_vectors)

            word_drifts = []
            max_drift = 0.0
            max_drift_word = None

            for w in analysis.words:
                word_drifts.append({
                    "word_index": w.word_index,
                    "text": w.text,
                    "root": w.root_key,
                    "drift": w.drift,
                    "energy": round(w.energy, 4),
                })
                if w.drift > max_drift:
                    max_drift = w.drift
                    max_drift_word = w.text

            verse_results.append({
                "ayah": ayah,
                "text": verse_text[:80] + ("..." if len(verse_text) > 80 else ""),
                "peak_drift": round(max_drift, 4),
                "peak_word": max_drift_word,
                "words": word_drifts,
            })

        return {
            "surah": surah,
            "range": f"{start_ayah}-{end_ayah}",
            "verses": verse_results,
        }
