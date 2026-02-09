"""Research tools: claims CRUD, patterns, evidence, relationships."""

from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from ..db import get_connection, save_database, invalidate_graph_cache
from ..utils.short_id import generate_claim_id, generate_evidence_id

mcp: FastMCP


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def register(server: FastMCP):
    global mcp
    mcp = server

    # --- Search & Read ---

    @mcp.tool()
    def search_claims(
        query: str | None = None,
        phase: str | None = None,
        pattern_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Search research claims by keyword, phase, or pattern.

        Returns claims matching the specified filters.
        """
        conn = get_connection()
        sql = "SELECT * FROM claims WHERE 1=1"
        params: list = []

        if query:
            sql += " AND lower(content) LIKE ?"
            params.append(f"%{query.lower()}%")
        if phase:
            sql += " AND phase = ?"
            params.append(phase)
        if pattern_id:
            sql += " AND pattern_id = ?"
            params.append(pattern_id)

        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    @mcp.tool()
    def get_claim(claim_id: str) -> dict:
        """Get a single claim by its ID."""
        conn = get_connection()
        row = conn.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()
        if not row:
            return {"error": f"Claim {claim_id} not found"}
        return dict(row)

    @mcp.tool()
    def get_claim_evidence(claim_id: str) -> list[dict]:
        """Get all evidence (verse references) supporting a specific research claim."""
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM claim_evidence WHERE claim_id = ? ORDER BY created_at DESC",
            (claim_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    @mcp.tool()
    def get_claim_dependencies(claim_id: str) -> dict:
        """Get the dependency tree for a claim."""
        conn = get_connection()

        claim_row = conn.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()
        if not claim_row:
            return {"claim": None, "dependencies": []}

        deps = conn.execute(
            """SELECT
                c.id, c.content, c.phase, c.pattern_id, c.note_file, c.created_at, c.updated_at,
                cd.dependency_type as dep_type
            FROM claim_dependencies cd
            JOIN claims c ON c.id = cd.depends_on_claim_id
            WHERE cd.claim_id = ?""",
            (claim_id,)
        ).fetchall()

        dependencies = []
        for dep in deps:
            d = dict(dep)
            dep_type = d.pop('dep_type')
            dependencies.append({"claim": d, "type": dep_type})

        return {"claim": dict(claim_row), "dependencies": dependencies}

    @mcp.tool()
    def list_patterns(pattern_type: str | None = None) -> list[dict]:
        """List morphological, syntactic, or semantic patterns identified in the Quran."""
        conn = get_connection()
        sql = "SELECT * FROM patterns WHERE 1=1"
        params: list = []
        if pattern_type:
            sql += " AND pattern_type = ?"
            params.append(pattern_type)
        sql += " ORDER BY created_at DESC"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    @mcp.tool()
    def get_claim_stats() -> dict:
        """Get database statistics: total claims, breakdown by phase, total patterns, total evidence, and claim ID range."""
        conn = get_connection()

        total_claims = conn.execute("SELECT count(*) FROM claims").fetchone()[0]

        phase_rows = conn.execute(
            "SELECT phase, count(*) as cnt FROM claims GROUP BY phase ORDER BY cnt DESC"
        ).fetchall()
        by_phase = {r['phase']: r['cnt'] for r in phase_rows}

        total_patterns = conn.execute("SELECT count(*) FROM patterns").fetchone()[0]
        total_evidence = conn.execute("SELECT count(*) FROM claim_evidence").fetchone()[0]

        range_row = conn.execute(
            "SELECT min(id), max(id) FROM claims WHERE id LIKE 'claim_%'"
        ).fetchone()
        id_range = {"min": range_row[0] or "", "max": range_row[1] or ""}

        return {
            "total_claims": total_claims,
            "by_phase": by_phase,
            "total_patterns": total_patterns,
            "total_evidence": total_evidence,
            "id_range": id_range,
        }

    @mcp.tool()
    def get_verse_claims(surah: int, ayah: int) -> list[dict]:
        """Get all claims that reference a specific verse as evidence."""
        conn = get_connection()
        rows = conn.execute(
            """SELECT
                vc.claim_id,
                c.content as claim_content,
                c.phase as claim_phase,
                vc.evidence_type,
                vc.verification,
                vc.notes,
                vc.created_at
            FROM verse_claims vc
            JOIN claims c ON c.id = vc.claim_id
            WHERE vc.surah = ? AND vc.ayah = ?
            ORDER BY vc.created_at DESC""",
            (surah, ayah)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Write tools ---

    @mcp.tool()
    def save_insight(
        content: str,
        phase: str = "question",
        pattern_id: str | None = None,
        evidence_verses: list[dict] | None = None,
    ) -> dict:
        """Save a single research claim or insight discovered during conversation.

        When saving 2+ claims at once, prefer save_bulk_insights instead.
        """
        conn = get_connection()
        evidence_verses = evidence_verses or []

        try:
            claim_id = generate_claim_id(conn)
            now = _now()

            conn.execute(
                "INSERT INTO claims (id, content, phase, pattern_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (claim_id, content, phase, pattern_id, now, now)
            )

            for ev in evidence_verses:
                ev_id = generate_evidence_id(conn)
                conn.execute(
                    "INSERT INTO claim_evidence (id, claim_id, surah, ayah, notes, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (ev_id, claim_id, ev['surah'], ev['ayah'], ev.get('notes'), now)
                )

            save_database()
            invalidate_graph_cache()

            return {
                "success": True,
                "claim_id": claim_id,
                "message": f"Insight saved successfully with {len(evidence_verses)} evidence verse(s)",
            }
        except Exception as e:
            return {"success": False, "claim_id": "", "message": f"Failed to save insight: {e}"}

    @mcp.tool()
    def save_bulk_insights(claims: list[dict]) -> dict:
        """Save multiple research claims at once in a single operation.

        Much more efficient than calling save_insight repeatedly.
        Does not support evidence_verses — use add_verse_evidence separately.
        """
        conn = get_connection()
        try:
            claim_ids = []
            now = _now()

            for claim in claims:
                cid = generate_claim_id(conn)
                conn.execute(
                    "INSERT INTO claims (id, content, phase, pattern_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (cid, claim['content'], claim.get('phase', 'question'), claim.get('pattern_id'), now, now)
                )
                claim_ids.append(cid)

            save_database()
            invalidate_graph_cache()

            return {
                "success": True,
                "claim_ids": claim_ids,
                "message": f"Saved {len(claim_ids)} claims ({claim_ids[0]} through {claim_ids[-1]})",
            }
        except Exception as e:
            return {"success": False, "claim_ids": [], "message": f"Failed to save bulk insights: {e}"}

    @mcp.tool()
    def update_claim(
        claim_id: str,
        content: str | None = None,
        phase: str | None = None,
        pattern_id: str | None = None,
    ) -> dict:
        """Update an existing claim's content, phase, or pattern_id."""
        conn = get_connection()
        try:
            row = conn.execute("SELECT id FROM claims WHERE id = ?", (claim_id,)).fetchone()
            if not row:
                return {"success": False, "message": f"Claim {claim_id} not found"}

            now = _now()
            updates = ["updated_at = ?"]
            params: list = [now]

            if content is not None:
                updates.append("content = ?")
                params.append(content)
            if phase is not None:
                updates.append("phase = ?")
                params.append(phase)
            if pattern_id is not None:
                updates.append("pattern_id = ?")
                params.append(pattern_id)

            params.append(claim_id)
            conn.execute(f"UPDATE claims SET {', '.join(updates)} WHERE id = ?", params)
            save_database()
            invalidate_graph_cache()

            return {"success": True, "message": f"Claim {claim_id} updated successfully"}
        except Exception as e:
            return {"success": False, "message": f"Failed to update claim: {e}"}

    @mcp.tool()
    def delete_claim(claim_id: str) -> dict:
        """Safely delete a claim and its associated evidence from the database."""
        conn = get_connection()
        try:
            row = conn.execute("SELECT id FROM claims WHERE id = ?", (claim_id,)).fetchone()
            if not row:
                return {"success": False, "message": f"Claim {claim_id} not found"}

            conn.execute("DELETE FROM claim_evidence WHERE claim_id = ?", (claim_id,))
            conn.execute(
                "DELETE FROM claim_dependencies WHERE claim_id = ? OR depends_on_claim_id = ?",
                (claim_id, claim_id)
            )
            conn.execute("DELETE FROM claims WHERE id = ?", (claim_id,))

            save_database()
            invalidate_graph_cache()

            return {"success": True, "message": f"Claim {claim_id} deleted successfully"}
        except Exception as e:
            return {"success": False, "message": f"Failed to delete claim: {e}"}

    @mcp.tool()
    def delete_multiple_claims(claim_ids: list[str]) -> dict:
        """Delete multiple claims at once."""
        conn = get_connection()
        failed = []
        deleted = 0

        try:
            for cid in claim_ids:
                row = conn.execute("SELECT id FROM claims WHERE id = ?", (cid,)).fetchone()
                if not row:
                    failed.append(cid)
                    continue

                conn.execute("DELETE FROM claim_evidence WHERE claim_id = ?", (cid,))
                conn.execute(
                    "DELETE FROM claim_dependencies WHERE claim_id = ? OR depends_on_claim_id = ?",
                    (cid, cid)
                )
                conn.execute("DELETE FROM claims WHERE id = ?", (cid,))
                deleted += 1

            save_database()
            invalidate_graph_cache()

            msg = f"Deleted {deleted} claims."
            if failed:
                msg += f" Failed: {len(failed)}"
            return {"success": True, "deleted": deleted, "failed": failed, "message": msg}
        except Exception as e:
            return {"success": False, "deleted": deleted, "failed": failed, "message": f"Failed during deletion: {e}"}

    @mcp.tool()
    def find_related_claims(claim_id: str, limit: int = 20) -> dict:
        """Find claims structurally related to a given claim through shared verse evidence, shared patterns, or same-surah evidence."""
        conn = get_connection()

        claim_row = conn.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()
        if not claim_row:
            return {"claim": None, "shared_evidence": [], "same_pattern": [], "same_surah_claims": []}
        claim = dict(claim_row)

        # 1. Claims sharing exact verse evidence
        shared_rows = conn.execute(
            """SELECT DISTINCT c.id, c.content, c.phase, c.pattern_id, c.note_file, c.created_at, c.updated_at,
                    vc2.surah, vc2.ayah
             FROM verse_claims vc1
             JOIN verse_claims vc2 ON vc1.surah = vc2.surah AND vc1.ayah = vc2.ayah AND vc1.claim_id != vc2.claim_id
             JOIN claims c ON c.id = vc2.claim_id
             WHERE vc1.claim_id = ?
             ORDER BY c.updated_at DESC
             LIMIT ?""",
            (claim_id, limit)
        ).fetchall()

        shared_map: dict[str, dict] = {}
        for row in shared_rows:
            r = dict(row)
            cid = r['id']
            if cid not in shared_map:
                shared_map[cid] = {
                    "claim": {k: r[k] for k in ('id', 'content', 'phase', 'pattern_id', 'note_file', 'created_at', 'updated_at')},
                    "shared_verses": [],
                }
            shared_map[cid]["shared_verses"].append({"surah": r['surah'], "ayah": r['ayah']})

        # 2. Claims in the same pattern
        same_pattern = []
        if claim.get('pattern_id'):
            pattern_rows = conn.execute(
                "SELECT * FROM claims WHERE pattern_id = ? AND id != ? ORDER BY updated_at DESC LIMIT ?",
                (claim['pattern_id'], claim_id, limit)
            ).fetchall()
            same_pattern = [dict(r) for r in pattern_rows]

        # 3. Claims with evidence in the same surah (weaker signal)
        surah_rows = conn.execute(
            """SELECT DISTINCT c.id, c.content, c.phase, c.pattern_id, c.note_file, c.created_at, c.updated_at,
                    vc2.surah
             FROM verse_claims vc1
             JOIN verse_claims vc2 ON vc1.surah = vc2.surah AND vc1.claim_id != vc2.claim_id
               AND NOT (vc1.ayah = vc2.ayah)
             JOIN claims c ON c.id = vc2.claim_id
             WHERE vc1.claim_id = ?
               AND vc2.claim_id NOT IN (
                 SELECT vc3.claim_id FROM verse_claims vc3
                 JOIN verse_claims vc4 ON vc3.surah = vc4.surah AND vc3.ayah = vc4.ayah AND vc3.claim_id != vc4.claim_id
                 WHERE vc4.claim_id = ?
               )
             ORDER BY c.updated_at DESC
             LIMIT ?""",
            (claim_id, claim_id, limit)
        ).fetchall()

        surah_map: dict[str, dict] = {}
        for row in surah_rows:
            r = dict(row)
            cid = r['id']
            if cid not in surah_map:
                surah_map[cid] = {
                    "claim": {k: r[k] for k in ('id', 'content', 'phase', 'pattern_id', 'note_file', 'created_at', 'updated_at')},
                    "surah": r['surah'],
                }

        return {
            "claim": claim,
            "shared_evidence": list(shared_map.values()),
            "same_pattern": same_pattern,
            "same_surah_claims": list(surah_map.values()),
        }

    @mcp.tool()
    def add_claim_dependency(
        claim_id: str,
        depends_on_claim_id: str,
        dependency_type: str,
    ) -> dict:
        """Create a typed relationship between two claims.

        Types: depends_on, supports, contradicts, refines, related.
        """
        conn = get_connection()
        valid_types = ('depends_on', 'supports', 'contradicts', 'refines', 'related')
        if dependency_type not in valid_types:
            return {"success": False, "message": f"Invalid dependency_type. Must be one of: {', '.join(valid_types)}"}

        if claim_id == depends_on_claim_id:
            return {"success": False, "message": "A claim cannot depend on itself"}

        try:
            if not conn.execute("SELECT id FROM claims WHERE id = ?", (claim_id,)).fetchone():
                return {"success": False, "message": f"Claim {claim_id} not found"}
            if not conn.execute("SELECT id FROM claims WHERE id = ?", (depends_on_claim_id,)).fetchone():
                return {"success": False, "message": f"Claim {depends_on_claim_id} not found"}

            dup = conn.execute(
                "SELECT claim_id FROM claim_dependencies WHERE claim_id = ? AND depends_on_claim_id = ? AND dependency_type = ?",
                (claim_id, depends_on_claim_id, dependency_type)
            ).fetchone()
            if dup:
                return {"success": False, "message": f"Dependency already exists: {claim_id} --{dependency_type}--> {depends_on_claim_id}"}

            now = _now()
            conn.execute(
                "INSERT INTO claim_dependencies (claim_id, depends_on_claim_id, dependency_type, created_at) VALUES (?, ?, ?, ?)",
                (claim_id, depends_on_claim_id, dependency_type, now)
            )
            save_database()
            invalidate_graph_cache()

            return {"success": True, "message": f"Dependency created: {claim_id} --{dependency_type}--> {depends_on_claim_id}"}
        except Exception as e:
            return {"success": False, "message": f"Failed to add dependency: {e}"}

    @mcp.tool()
    def delete_pattern(pattern_id: str) -> dict:
        """Delete a pattern and unlink any claims that reference it."""
        conn = get_connection()
        try:
            row = conn.execute("SELECT id FROM patterns WHERE id = ?", (pattern_id,)).fetchone()
            if not row:
                return {"success": False, "message": f"Pattern {pattern_id} not found"}

            conn.execute("UPDATE claims SET pattern_id = NULL WHERE pattern_id = ?", (pattern_id,))
            conn.execute("DELETE FROM pattern_linguistic_features WHERE pattern_id = ?", (pattern_id,))
            conn.execute("DELETE FROM patterns WHERE id = ?", (pattern_id,))

            save_database()
            invalidate_graph_cache()

            return {"success": True, "message": f"Pattern {pattern_id} deleted. Associated claims preserved with pattern_id set to null."}
        except Exception as e:
            return {"success": False, "message": f"Failed to delete pattern: {e}"}
