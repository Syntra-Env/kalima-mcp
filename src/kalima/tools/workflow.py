"""Workflow tools: systematic verse-by-verse verification sessions."""

import json
import math
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from ..db import get_connection, save_database, invalidate_graph_cache
from ..utils.short_id import generate_session_id, generate_evidence_id

mcp: FastMCP


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def register(server: FastMCP):
    global mcp
    mcp = server

    @mcp.tool()
    def start_workflow_session(
        claim_id: str,
        workflow_type: str,
        linguistic_features: dict | None = None,
        surah: int | None = None,
        limit: int = 100,
    ) -> dict:
        """Start a new verification workflow session to systematically verify verses one by one."""
        conn = get_connection()
        sid = generate_session_id(conn)

        try:
            if not conn.execute("SELECT id FROM claims WHERE id = ?", (claim_id,)).fetchone():
                return {"success": False, "session_id": "", "message": f"Claim {claim_id} not found", "total_verses": 0}

            verses = []

            if workflow_type == 'pattern' and linguistic_features:
                # Import here to avoid circular dependency
                from .linguistic import _normalize_feature

                conditions = []
                params: list = []

                for key, val in linguistic_features.items():
                    if val is not None:
                        normalized = _normalize_feature(key, str(val))
                        conditions.append(f"s.{key} = ?")
                        params.append(normalized)

                if not conditions:
                    return {"success": False, "session_id": "", "message": "No linguistic features specified", "total_verses": 0}

                where_clause = " AND ".join(conditions)
                params.append(limit)

                rows = conn.execute(
                    f"""SELECT DISTINCT
                        t.verse_surah AS surah_number,
                        t.verse_ayah AS ayah_number,
                        vt.text
                    FROM segments s
                    JOIN tokens t ON s.token_id = t.id
                    JOIN verse_texts vt ON t.verse_surah = vt.surah_number AND t.verse_ayah = vt.ayah_number
                    WHERE {where_clause}
                    ORDER BY t.verse_surah ASC, t.verse_ayah ASC
                    LIMIT ?""",
                    params
                ).fetchall()
                verses = [dict(r) for r in rows]

            elif workflow_type == 'surah_theme' and surah:
                rows = conn.execute(
                    """SELECT surah_number, ayah_number, text
                       FROM verse_texts
                       WHERE surah_number = ?
                       ORDER BY ayah_number ASC""",
                    (surah,)
                ).fetchall()
                verses = [dict(r) for r in rows]
            else:
                return {
                    "success": False, "session_id": "",
                    "message": "Invalid workflow configuration: must specify either linguistic_features for pattern workflow or surah for surah_theme workflow",
                    "total_verses": 0,
                }

            if not verses:
                return {"success": False, "session_id": "", "message": "No verses found matching criteria", "total_verses": 0}

            verses_json = json.dumps(verses)
            ling_json = json.dumps(linguistic_features) if linguistic_features else None

            conn.execute(
                """INSERT INTO workflow_sessions
                   (session_id, claim_id, workflow_type, created_at, current_index,
                    total_verses, status, linguistic_features, surah, verses_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (sid, claim_id, workflow_type, _now(), 0, len(verses), 'active', ling_json, surah, verses_json)
            )
            save_database()

            first = verses[0] if verses else None
            return {
                "success": True,
                "session_id": sid,
                "message": f"Workflow session started with {len(verses)} verses to verify",
                "total_verses": len(verses),
                "first_verse": {"surah": first['surah_number'], "ayah": first['ayah_number'], "text": first['text']} if first else None,
            }
        except Exception as e:
            return {"success": False, "session_id": "", "message": f"Error starting workflow: {e}", "total_verses": 0}

    @mcp.tool()
    def get_next_verse(session_id: str) -> dict:
        """Get the next verse in an active workflow session for verification.

        Returns ONLY the Arabic verse text, progress, and completion status.
        DO NOT add English translations when presenting verses to the user.
        """
        conn = get_connection()

        try:
            row = conn.execute(
                "SELECT current_index, total_verses, verses_json, status FROM workflow_sessions WHERE session_id = ?",
                (session_id,)
            ).fetchone()

            if not row:
                return {"success": False, "message": "Session not found", "progress": {"current": 0, "total": 0, "percentage": 0}, "completed": False}

            current_index, total_verses, verses_json, status = row['current_index'], row['total_verses'], row['verses_json'], row['status']

            if status == 'completed':
                return {"success": True, "message": "Workflow already completed", "progress": {"current": total_verses, "total": total_verses, "percentage": 100}, "completed": True}

            verses = json.loads(verses_json)

            if current_index >= len(verses):
                conn.execute("UPDATE workflow_sessions SET status = ?, current_index = ? WHERE session_id = ?", ('completed', current_index, session_id))
                save_database()
                return {"success": True, "message": "All verses verified - workflow complete", "progress": {"current": total_verses, "total": total_verses, "percentage": 100}, "completed": True}

            verse = verses[current_index]
            percentage = round((current_index / total_verses) * 100)

            return {
                "success": True,
                "message": f"Verse {current_index + 1} of {total_verses}",
                "verse": {"surah": verse['surah_number'], "ayah": verse['ayah_number'], "text": verse['text']},
                "progress": {"current": current_index + 1, "total": total_verses, "percentage": percentage},
                "completed": False,
            }
        except Exception as e:
            return {"success": False, "message": f"Error getting next verse: {e}", "progress": {"current": 0, "total": 0, "percentage": 0}, "completed": False}

    @mcp.tool()
    def submit_verification(
        session_id: str,
        verification: str,
        notes: str | None = None,
    ) -> dict:
        """Submit verification for the current verse in a workflow and advance to the next verse."""
        conn = get_connection()

        try:
            row = conn.execute(
                "SELECT claim_id, current_index, total_verses, verses_json FROM workflow_sessions WHERE session_id = ?",
                (session_id,)
            ).fetchone()

            if not row:
                return {"success": False, "message": "Session not found", "progress": {"current": 0, "total": 0, "percentage": 0}, "completed": False}

            claim_id, current_index, total_verses, verses_json = row['claim_id'], row['current_index'], row['total_verses'], row['verses_json']
            verses = json.loads(verses_json)
            current_verse = verses[current_index]

            # Save verification as evidence
            eid = generate_evidence_id(conn)
            conn.execute(
                """INSERT INTO verse_evidence
                   (id, claim_id, verse_surah, verse_ayah, verification, notes, verified_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (eid, claim_id, current_verse['surah_number'], current_verse['ayah_number'], verification, notes or '', _now())
            )

            # Advance to next verse
            next_index = current_index + 1
            conn.execute("UPDATE workflow_sessions SET current_index = ? WHERE session_id = ?", (next_index, session_id))
            save_database()
            invalidate_graph_cache()

            if next_index >= len(verses):
                conn.execute("UPDATE workflow_sessions SET status = ? WHERE session_id = ?", ('completed', session_id))
                save_database()
                return {
                    "success": True, "message": "Verification saved. Workflow complete!",
                    "evidence_id": eid,
                    "progress": {"current": total_verses, "total": total_verses, "percentage": 100},
                    "completed": True,
                }

            next_verse = verses[next_index]
            percentage = round((next_index / total_verses) * 100)

            return {
                "success": True,
                "message": f"Verification saved. Moving to verse {next_index + 1} of {total_verses}",
                "evidence_id": eid,
                "next_verse": {"surah": next_verse['surah_number'], "ayah": next_verse['ayah_number'], "text": next_verse['text']},
                "progress": {"current": next_index + 1, "total": total_verses, "percentage": percentage},
                "completed": False,
            }
        except Exception as e:
            return {"success": False, "message": f"Error submitting verification: {e}", "progress": {"current": 0, "total": 0, "percentage": 0}, "completed": False}

    @mcp.tool()
    def get_workflow_stats(session_id: str) -> dict:
        """Get statistics and progress for a workflow session."""
        conn = get_connection()

        try:
            session = conn.execute(
                "SELECT claim_id, current_index, total_verses, status FROM workflow_sessions WHERE session_id = ?",
                (session_id,)
            ).fetchone()

            if not session:
                return {"success": False, "message": "Session not found"}

            claim_id, current_index, total_verses = session['claim_id'], session['current_index'], session['total_verses']

            verification_rows = conn.execute(
                "SELECT verification, COUNT(*) as count FROM verse_evidence WHERE claim_id = ? GROUP BY verification",
                (claim_id,)
            ).fetchall()

            counts = {"supports": 0, "contradicts": 0, "unclear": 0, "total_verified": 0}
            for vr in verification_rows:
                v = vr['verification']
                if v in counts:
                    counts[v] = vr['count']
            counts['total_verified'] = counts['supports'] + counts['contradicts'] + counts['unclear']

            percentage = round((current_index / total_verses) * 100) if total_verses > 0 else 0

            return {
                "success": True,
                "message": "Workflow statistics retrieved",
                "stats": {
                    "total_verses": total_verses,
                    "verified": current_index,
                    "remaining": total_verses - current_index,
                    "percentage_complete": percentage,
                    "verification_counts": counts,
                    "has_contradictions": counts['contradicts'] > 0,
                },
            }
        except Exception as e:
            return {"success": False, "message": f"Error getting workflow stats: {e}"}

    @mcp.tool()
    def list_workflow_sessions(status: str | None = None) -> dict:
        """List all workflow sessions with their status and progress."""
        conn = get_connection()

        try:
            sql = """SELECT session_id, claim_id, workflow_type, created_at,
                            current_index, total_verses, status
                     FROM workflow_sessions"""
            params: list = []

            if status:
                sql += " WHERE status = ?"
                params.append(status)
            sql += " ORDER BY created_at DESC"

            rows = conn.execute(sql, params).fetchall()

            if not rows:
                return {"success": True, "message": "No workflow sessions found", "sessions": []}

            sessions = []
            for r in rows:
                percentage = round((r['current_index'] / r['total_verses']) * 100) if r['total_verses'] > 0 else 0
                sessions.append({
                    "session_id": r['session_id'],
                    "claim_id": r['claim_id'],
                    "workflow_type": r['workflow_type'],
                    "created_at": r['created_at'],
                    "progress": {"current": r['current_index'], "total": r['total_verses'], "percentage": percentage},
                    "status": r['status'],
                })

            return {"success": True, "message": f"Found {len(sessions)} workflow session(s)", "sessions": sessions}
        except Exception as e:
            return {"success": False, "message": f"Error listing workflow sessions: {e}", "sessions": []}

    @mcp.tool()
    def check_phase_transition(session_id: str) -> dict:
        """Check if a claim should transition to a new research phase based on verification results."""
        conn = get_connection()

        try:
            # Get stats via the stats function
            stats_result = get_workflow_stats(session_id)
            if not stats_result.get('success') or 'stats' not in stats_result:
                return {"success": False, "message": "Failed to get workflow statistics"}

            stats = stats_result['stats']

            session = conn.execute("SELECT claim_id FROM workflow_sessions WHERE session_id = ?", (session_id,)).fetchone()
            if not session:
                return {"success": False, "message": "Session not found"}

            claim_id = session['claim_id']
            claim = conn.execute("SELECT phase FROM claims WHERE id = ?", (claim_id,)).fetchone()
            if not claim:
                return {"success": False, "message": "Claim not found"}

            current_phase = claim['phase']
            new_phase = None
            reason = ""

            vc = stats['verification_counts']

            if stats['has_contradictions'] and vc['contradicts'] > 0:
                new_phase = 'rejected'
                reason = f"Found {vc['contradicts']} contradicting verse(s)"
            elif stats['percentage_complete'] == 100 and vc['supports'] >= 3:
                new_phase = 'validated'
                reason = f"Workflow complete with {vc['supports']} supporting verses and no contradictions"
            elif current_phase == 'hypothesis' and vc['supports'] >= 3:
                new_phase = 'validation'
                reason = f"Found {vc['supports']} supporting verses, ready for broader validation"

            if new_phase and new_phase != current_phase:
                conn.execute("UPDATE claims SET phase = ? WHERE id = ?", (new_phase, claim_id))
                save_database()
                invalidate_graph_cache()

                return {
                    "success": True,
                    "message": f"Phase transition: {current_phase} → {new_phase}",
                    "phase_transition": {"from": current_phase, "to": new_phase, "reason": reason},
                }

            return {"success": True, "message": f"No phase transition needed (current: {current_phase})"}
        except Exception as e:
            return {"success": False, "message": f"Error checking phase transition: {e}"}
