"""Workflow tools: entry-centric verification with inline state."""

import json
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from ..db import get_connection, save_database, invalidate_graph_cache
from ..utils.short_id import generate_entry_id
from ..utils.features import TERM_TYPE_TO_FEATURE

mcp: FastMCP


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compute_confidence(conn, entry_id: str) -> float | None:
    """Compute and store confidence score for an entry using inline columns.

    confidence = coverage * support_ratio
    where coverage = verified_count / total_relevant
    and support_ratio = supports / verified_count
    """
    row = conn.execute(
        "SELECT verse_total, verse_verified, verse_supports FROM entries WHERE id = ?",
        (entry_id,)
    ).fetchone()

    if not row or not row['verse_total'] or row['verse_total'] == 0:
        return None
    if not row['verse_verified'] or row['verse_verified'] == 0:
        return None

    coverage = row['verse_verified'] / row['verse_total']
    support_ratio = row['verse_supports'] / row['verse_verified']
    confidence = round(coverage * support_ratio, 4)

    conn.execute("UPDATE entries SET confidence = ? WHERE id = ?", (confidence, entry_id))
    return confidence


def compute_verse_universe(conn, scope_type: str, scope_value: str, limit: int = 500) -> list[dict]:
    """Compute the set of verses an entry's scope covers.

    Returns list of {surah, ayah} dicts.
    """
    if scope_type in ('root', 'lemma'):
        from .linguistic import _resolve_feature_id
        fk_id = _resolve_feature_id(conn, scope_type, scope_value)
        if fk_id is None:
            return []
        fk_col = f"{scope_type}_id"
        rows = conn.execute(
            f"""SELECT DISTINCT t.verse_surah AS surah, t.verse_ayah AS ayah
                FROM segments s
                JOIN tokens t ON s.token_id = t.id
                WHERE s.{fk_col} = ?
                ORDER BY t.verse_surah, t.verse_ayah
                LIMIT ?""",
            (fk_id, limit)
        ).fetchall()
        return [{"surah": r["surah"], "ayah": r["ayah"]} for r in rows]

    elif scope_type == 'pattern':
        from .linguistic import _normalize_feature, _resolve_feature_id

        features = json.loads(scope_value) if isinstance(scope_value, str) else scope_value
        conditions = []
        params: list = []

        for key, val in features.items():
            if val is not None:
                normalized = _normalize_feature(key, str(val))
                fk_id = _resolve_feature_id(conn, key, normalized)
                if fk_id is None:
                    return []
                conditions.append(f"s.{key}_id = ?")
                params.append(fk_id)

        if not conditions:
            return []

        where_clause = " AND ".join(conditions)
        params.append(limit)

        rows = conn.execute(
            f"""SELECT DISTINCT t.verse_surah AS surah, t.verse_ayah AS ayah
                FROM segments s
                JOIN tokens t ON s.token_id = t.id
                WHERE {where_clause}
                ORDER BY t.verse_surah, t.verse_ayah
                LIMIT ?""",
            params
        ).fetchall()
        return [{"surah": r["surah"], "ayah": r["ayah"]} for r in rows]

    elif scope_type == 'surah':
        surah_num = int(scope_value)
        rows = conn.execute(
            "SELECT surah_number AS surah, ayah_number AS ayah FROM verse_texts WHERE surah_number = ? ORDER BY ayah_number",
            (surah_num,)
        ).fetchall()
        return [{"surah": r["surah"], "ayah": r["ayah"]} for r in rows]

    elif scope_type == 'verse_range':
        # scope_value format: "surah:start-end" e.g. "2:1-10"
        parts = scope_value.split(":")
        surah_num = int(parts[0])
        ayah_range = parts[1].split("-")
        start_ayah = int(ayah_range[0])
        end_ayah = int(ayah_range[1])

        rows = conn.execute(
            "SELECT surah_number AS surah, ayah_number AS ayah FROM verse_texts WHERE surah_number = ? AND ayah_number BETWEEN ? AND ? ORDER BY ayah_number",
            (surah_num, start_ayah, end_ayah)
        ).fetchall()
        return [{"surah": r["surah"], "ayah": r["ayah"]} for r in rows]

    else:
        # character, stylistic, etc. — manual verification only
        return []


def register(server: FastMCP):
    global mcp
    mcp = server

    @mcp.tool()
    def start_verification(entry_id: str, limit: int = 500) -> dict:
        """Start a new verification workflow for an entry.

        Computes the verse universe from the entry's scope, stores the queue,
        and returns the first verse. Requires scope_type and scope_value to be set.
        """
        conn = get_connection()

        try:
            entry = conn.execute(
                "SELECT id, scope_type, scope_value, verse_queue, verse_current_index FROM entries WHERE id = ?",
                (entry_id,)
            ).fetchone()

            if not entry:
                return {"success": False, "message": f"Entry {entry_id} not found"}

            if not entry['scope_type'] or not entry['scope_value']:
                return {"success": False, "message": f"Entry {entry_id} has no scope set. Set scope_type and scope_value first."}

            # Compute verse universe
            queue = compute_verse_universe(conn, entry['scope_type'], entry['scope_value'], limit)

            if not queue:
                return {"success": False, "message": f"No verses found for scope {entry['scope_type']}={entry['scope_value']}"}

            now = _now()
            queue_json = json.dumps(queue)

            conn.execute(
                """UPDATE entries SET
                    verse_total = ?,
                    verse_current_index = 0,
                    verse_queue = ?,
                    verification_started_at = ?,
                    verification_updated_at = ?
                   WHERE id = ?""",
                (len(queue), queue_json, now, now, entry_id)
            )
            save_database()

            first = queue[0]
            verse_text = conn.execute(
                "SELECT text FROM verse_texts WHERE surah_number = ? AND ayah_number = ?",
                (first['surah'], first['ayah'])
            ).fetchone()

            return {
                "success": True,
                "message": f"Verification started with {len(queue)} verses",
                "total_verses": len(queue),
                "first_verse": {
                    "surah": first['surah'],
                    "ayah": first['ayah'],
                    "text": verse_text['text'] if verse_text else "",
                },
            }
        except Exception as e:
            return {"success": False, "message": f"Error starting verification: {e}"}

    @mcp.tool()
    def continue_verification(entry_id: str) -> dict:
        """Continue verification for an entry, returning the current verse.

        Returns ONLY the Arabic verse text, progress, and completion status.
        DO NOT add English translations when presenting verses to the user.
        """
        conn = get_connection()

        try:
            entry = conn.execute(
                "SELECT verse_total, verse_current_index, verse_queue FROM entries WHERE id = ?",
                (entry_id,)
            ).fetchone()

            if not entry:
                return {"success": False, "message": f"Entry {entry_id} not found", "progress": {}, "completed": False}

            if not entry['verse_queue']:
                return {"success": False, "message": "No verification queue. Call start_verification first.", "progress": {}, "completed": False}

            queue = json.loads(entry['verse_queue'])
            total = entry['verse_total'] or len(queue)
            current_index = entry['verse_current_index'] or 0

            if current_index >= len(queue):
                return {
                    "success": True,
                    "message": "All verses verified — verification complete",
                    "progress": {"current": total, "total": total, "percentage": 100},
                    "completed": True,
                }

            verse = queue[current_index]
            verse_text = conn.execute(
                "SELECT text FROM verse_texts WHERE surah_number = ? AND ayah_number = ?",
                (verse['surah'], verse['ayah'])
            ).fetchone()

            percentage = round((current_index / total) * 100)

            return {
                "success": True,
                "message": f"Verse {current_index + 1} of {total}",
                "verse": {
                    "surah": verse['surah'],
                    "ayah": verse['ayah'],
                    "text": verse_text['text'] if verse_text else "",
                },
                "progress": {"current": current_index + 1, "total": total, "percentage": percentage},
                "completed": False,
            }
        except Exception as e:
            return {"success": False, "message": f"Error: {e}", "progress": {}, "completed": False}

    @mcp.tool()
    def submit_verification(
        entry_id: str,
        verification: str,
        notes: str | None = None,
    ) -> dict:
        """Submit verification for the current verse and advance to the next."""
        conn = get_connection()

        try:
            entry = conn.execute(
                """SELECT verse_total, verse_current_index, verse_queue,
                          verse_verified, verse_supports, verse_contradicts, verse_unclear
                   FROM entries WHERE id = ?""",
                (entry_id,)
            ).fetchone()

            if not entry:
                return {"success": False, "message": f"Entry {entry_id} not found"}

            if not entry['verse_queue']:
                return {"success": False, "message": "No verification queue."}

            queue = json.loads(entry['verse_queue'])
            current_index = entry['verse_current_index'] or 0

            if current_index >= len(queue):
                return {"success": False, "message": "Verification already complete."}

            current_verse = queue[current_index]
            now = _now()

            # Map verification to dependency type
            dep_type_map = {'supports': 'supports', 'contradicts': 'contradicts', 'unclear': 'related'}
            dep_type = dep_type_map.get(verification, 'related')

            # Save evidence as verse-scoped child entry
            eid = generate_entry_id(conn)
            scope_value = f"{current_verse['surah']}:{current_verse['ayah']}"
            parent_row = conn.execute("SELECT phase, category FROM entries WHERE id = ?", (entry_id,)).fetchone()
            conn.execute(
                """INSERT INTO entries (id, content, phase, category, scope_type, scope_value, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'verse', ?, ?, ?)""",
                (eid, notes or f"Verification: {verification}", parent_row['phase'], parent_row['category'],
                 scope_value, now, now)
            )
            conn.execute(
                """INSERT INTO entry_dependencies (entry_id, depends_on_entry_id, dependency_type, created_at)
                   VALUES (?, ?, ?, ?)""",
                (eid, entry_id, dep_type, now)
            )

            # Update inline counters
            verified = (entry['verse_verified'] or 0) + 1
            supports = (entry['verse_supports'] or 0) + (1 if verification == 'supports' else 0)
            contradicts = (entry['verse_contradicts'] or 0) + (1 if verification == 'contradicts' else 0)
            unclear = (entry['verse_unclear'] or 0) + (1 if verification == 'unclear' else 0)
            next_index = current_index + 1

            conn.execute(
                """UPDATE entries SET
                    verse_current_index = ?,
                    verse_verified = ?,
                    verse_supports = ?,
                    verse_contradicts = ?,
                    verse_unclear = ?,
                    verification_updated_at = ?
                   WHERE id = ?""",
                (next_index, verified, supports, contradicts, unclear, now, entry_id)
            )

            save_database()
            invalidate_graph_cache()

            total = entry['verse_total'] or len(queue)

            # Check if done
            if next_index >= len(queue):
                confidence = _compute_confidence(conn, entry_id)
                save_database()
                return {
                    "success": True,
                    "message": "Verification saved. All verses complete!",
                    "entry_id": eid,
                    "progress": {"current": total, "total": total, "percentage": 100},
                    "completed": True,
                    "confidence": confidence,
                }

            # Return next verse
            next_verse = queue[next_index]
            verse_text = conn.execute(
                "SELECT text FROM verse_texts WHERE surah_number = ? AND ayah_number = ?",
                (next_verse['surah'], next_verse['ayah'])
            ).fetchone()

            percentage = round((next_index / total) * 100)

            return {
                "success": True,
                "message": f"Verification saved. Moving to verse {next_index + 1} of {total}",
                "entry_id": eid,
                "next_verse": {
                    "surah": next_verse['surah'],
                    "ayah": next_verse['ayah'],
                    "text": verse_text['text'] if verse_text else "",
                },
                "progress": {"current": next_index + 1, "total": total, "percentage": percentage},
                "completed": False,
            }
        except Exception as e:
            return {"success": False, "message": f"Error submitting verification: {e}"}

    @mcp.tool()
    def get_verification_stats(entry_id: str) -> dict:
        """Get verification statistics for an entry. Reads inline columns — no aggregation needed."""
        conn = get_connection()

        try:
            entry = conn.execute(
                """SELECT verse_total, verse_verified, verse_supports, verse_contradicts,
                          verse_unclear, verse_current_index, scope_type, scope_value,
                          verification_started_at, verification_updated_at, confidence
                   FROM entries WHERE id = ?""",
                (entry_id,)
            ).fetchone()

            if not entry:
                return {"success": False, "message": f"Entry {entry_id} not found"}

            total = entry['verse_total'] or 0
            verified = entry['verse_verified'] or 0
            current_index = entry['verse_current_index'] or 0
            remaining = max(0, total - current_index) if total else 0
            percentage = round((current_index / total) * 100) if total > 0 else 0

            return {
                "success": True,
                "message": "Verification statistics retrieved",
                "stats": {
                    "scope_type": entry['scope_type'],
                    "scope_value": entry['scope_value'],
                    "total_verses": total,
                    "verified": verified,
                    "remaining": remaining,
                    "percentage_complete": percentage,
                    "verification_counts": {
                        "supports": entry['verse_supports'] or 0,
                        "contradicts": entry['verse_contradicts'] or 0,
                        "unclear": entry['verse_unclear'] or 0,
                        "total_verified": verified,
                    },
                    "has_contradictions": (entry['verse_contradicts'] or 0) > 0,
                    "confidence": entry['confidence'],
                    "started_at": entry['verification_started_at'],
                    "updated_at": entry['verification_updated_at'],
                },
            }
        except Exception as e:
            return {"success": False, "message": f"Error getting stats: {e}"}

    @mcp.tool()
    def check_phase_transition(entry_id: str) -> dict:
        """Check if an entry should transition to a new research phase based on verification results."""
        conn = get_connection()

        try:
            entry = conn.execute(
                """SELECT phase, verse_total, verse_verified, verse_supports,
                          verse_contradicts, verse_unclear, verse_current_index
                   FROM entries WHERE id = ?""",
                (entry_id,)
            ).fetchone()

            if not entry:
                return {"success": False, "message": f"Entry {entry_id} not found"}

            current_phase = entry['phase']
            supports = entry['verse_supports'] or 0
            contradicts = entry['verse_contradicts'] or 0
            total = entry['verse_total'] or 0
            current_index = entry['verse_current_index'] or 0
            percentage = round((current_index / total) * 100) if total > 0 else 0

            new_phase = None
            reason = ""

            if contradicts > 0:
                new_phase = 'rejected'
                reason = f"Found {contradicts} contradicting verse(s)"
            elif percentage == 100 and supports >= 3:
                new_phase = 'validated'
                reason = f"Verification complete with {supports} supporting verses and no contradictions"
            elif current_phase == 'hypothesis' and supports >= 3:
                new_phase = 'validation'
                reason = f"Found {supports} supporting verses, ready for broader validation"

            if new_phase and new_phase != current_phase:
                conn.execute("UPDATE entries SET phase = ? WHERE id = ?", (new_phase, entry_id))
                save_database()
                invalidate_graph_cache()

                confidence = _compute_confidence(conn, entry_id)
                if confidence is not None:
                    save_database()

                return {
                    "success": True,
                    "message": f"Phase transition: {current_phase} -> {new_phase}",
                    "phase_transition": {"from": current_phase, "to": new_phase, "reason": reason},
                    "confidence": confidence,
                }

            # Always recompute confidence when checking
            confidence = _compute_confidence(conn, entry_id)
            if confidence is not None:
                save_database()

            return {"success": True, "message": f"No phase transition needed (current: {current_phase})", "confidence": confidence}
        except Exception as e:
            return {"success": False, "message": f"Error checking phase transition: {e}"}
