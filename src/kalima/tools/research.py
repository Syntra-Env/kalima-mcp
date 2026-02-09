"""Research tools: entries CRUD, evidence, relationships."""

from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from ..db import get_connection, save_database, invalidate_graph_cache
from ..utils.short_id import generate_entry_id

mcp: FastMCP

VALID_PHASES = {'question', 'hypothesis', 'validation', 'active_verification', 'passive_verification', 'validated', 'rejected'}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _find_duplicate(conn, content: str) -> str | None:
    """Return existing entry ID if identical content exists, else None."""
    row = conn.execute(
        "SELECT id FROM entries WHERE TRIM(content) = TRIM(?)", (content,)
    ).fetchone()
    return row["id"] if row else None


def register(server: FastMCP):
    global mcp
    mcp = server

    # --- Search & Read ---

    @mcp.tool()
    def search_entries(
        query: str | None = None,
        phase: str | None = None,
        category: str | None = None,
        scope_type: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Search research entries by keyword, phase, or category.

        Returns entries matching the specified filters.
        """
        conn = get_connection()
        sql = "SELECT * FROM entries WHERE 1=1"
        params: list = []

        if query:
            sql += " AND lower(content) LIKE ?"
            params.append(f"%{query.lower()}%")
        if phase:
            sql += " AND phase = ?"
            params.append(phase)
        if category:
            sql += " AND category = ?"
            params.append(category)
        if scope_type:
            sql += " AND scope_type = ?"
            params.append(scope_type)

        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    @mcp.tool()
    def get_entry(entry_id: str) -> dict:
        """Get a single entry by its ID."""
        conn = get_connection()
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
        if not row:
            return {"error": f"Entry {entry_id} not found"}
        return dict(row)

    @mcp.tool()
    def get_entry_evidence(entry_id: str) -> list[dict]:
        """Get all evidence (verse references) supporting a specific research entry."""
        conn = get_connection()
        rows = conn.execute(
            """SELECT e.id, e.content, e.phase, e.scope_value,
                      ed.dependency_type, e.created_at
               FROM entry_dependencies ed
               JOIN entries e ON e.id = ed.entry_id
               WHERE ed.depends_on_entry_id = ? AND e.scope_type = 'verse'
               ORDER BY e.created_at DESC""",
            (entry_id,)
        ).fetchall()
        results = []
        for r in rows:
            parts = r['scope_value'].split(':') if r['scope_value'] else ['0', '0']
            results.append({
                "entry_id": r['id'],
                "surah": int(parts[0]),
                "ayah": int(parts[1]) if len(parts) > 1 else 0,
                "verification": r['dependency_type'],
                "notes": r['content'],
                "created_at": r['created_at'],
            })
        return results

    @mcp.tool()
    def get_entry_dependencies(entry_id: str) -> dict:
        """Get the dependency tree for an entry."""
        conn = get_connection()

        entry_row = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
        if not entry_row:
            return {"entry": None, "dependencies": []}

        deps = conn.execute(
            """SELECT
                e.id, e.content, e.phase, e.category, e.created_at, e.updated_at,
                ed.dependency_type as dep_type
            FROM entry_dependencies ed
            JOIN entries e ON e.id = ed.depends_on_entry_id
            WHERE ed.entry_id = ?""",
            (entry_id,)
        ).fetchall()

        dependencies = []
        for dep in deps:
            d = dict(dep)
            dep_type = d.pop('dep_type')
            dependencies.append({"entry": d, "type": dep_type})

        return {"entry": dict(entry_row), "dependencies": dependencies}

    @mcp.tool()
    def get_entry_stats() -> dict:
        """Get database statistics: total entries, breakdown by phase/category, confidence distribution, and health metrics."""
        conn = get_connection()

        total_entries = conn.execute("SELECT count(*) FROM entries").fetchone()[0]

        phase_rows = conn.execute(
            "SELECT phase, count(*) as cnt FROM entries GROUP BY phase ORDER BY cnt DESC"
        ).fetchall()
        by_phase = {r['phase']: r['cnt'] for r in phase_rows}

        total_evidence = conn.execute(
            "SELECT count(*) FROM entries WHERE scope_type = 'verse'"
        ).fetchone()[0]

        cat_rows = conn.execute(
            "SELECT category, count(*) as cnt FROM entries GROUP BY category ORDER BY cnt DESC"
        ).fetchall()
        by_category = {r['category'] or 'uncategorized': r['cnt'] for r in cat_rows}

        range_row = conn.execute(
            "SELECT min(id), max(id) FROM entries WHERE id LIKE 'entry_%'"
        ).fetchone()
        id_range = {"min": range_row[0] or "", "max": range_row[1] or ""}

        # Confidence distribution
        conf_row = conn.execute("""
            SELECT
                SUM(CASE WHEN confidence IS NULL THEN 1 ELSE 0 END) as unscored,
                SUM(CASE WHEN confidence >= 0 AND confidence < 0.1 THEN 1 ELSE 0 END) as very_low,
                SUM(CASE WHEN confidence >= 0.1 AND confidence < 0.3 THEN 1 ELSE 0 END) as low,
                SUM(CASE WHEN confidence >= 0.3 AND confidence < 0.6 THEN 1 ELSE 0 END) as moderate,
                SUM(CASE WHEN confidence >= 0.6 THEN 1 ELSE 0 END) as high,
                AVG(confidence) as avg_confidence
            FROM entries
        """).fetchone()

        confidence_distribution = {
            "unscored": conf_row['unscored'] or 0,
            "very_low": conf_row['very_low'] or 0,
            "low": conf_row['low'] or 0,
            "moderate": conf_row['moderate'] or 0,
            "high": conf_row['high'] or 0,
            "avg_confidence": round(conf_row['avg_confidence'], 4) if conf_row['avg_confidence'] is not None else None,
        }

        # Scope distribution
        scope_rows = conn.execute(
            "SELECT scope_type, count(*) as cnt FROM entries WHERE scope_type IS NOT NULL GROUP BY scope_type ORDER BY cnt DESC"
        ).fetchall()
        by_scope = {r['scope_type']: r['cnt'] for r in scope_rows}

        # Health metrics
        orphan_entries = conn.execute(
            """SELECT count(*) FROM entries e
               WHERE e.id NOT IN (SELECT entry_id FROM entry_dependencies)
                 AND e.id NOT IN (SELECT depends_on_entry_id FROM entry_dependencies)
                 AND e.scope_type IS NULL"""
        ).fetchone()[0]

        # Entries without any verse-scoped children (evidence)
        entries_without_evidence = conn.execute(
            """SELECT count(*) FROM entries
               WHERE scope_type != 'verse' OR scope_type IS NULL
                 AND id NOT IN (
                     SELECT ed.depends_on_entry_id FROM entry_dependencies ed
                     JOIN entries e ON e.id = ed.entry_id
                     WHERE e.scope_type = 'verse'
                 )"""
        ).fetchone()[0]

        entries_without_deps = conn.execute(
            """SELECT count(*) FROM entries
               WHERE id NOT IN (SELECT entry_id FROM entry_dependencies)
                 AND id NOT IN (SELECT depends_on_entry_id FROM entry_dependencies)"""
        ).fetchone()[0]

        stale_questions = conn.execute(
            """SELECT count(*) FROM entries
               WHERE phase = 'question'
                 AND created_at = updated_at
                 AND created_at < datetime('now', '-7 days')"""
        ).fetchone()[0]

        return {
            "total_entries": total_entries,
            "by_phase": by_phase,
            "by_category": by_category,
            "by_scope": by_scope,
            "confidence": confidence_distribution,
            "total_evidence": total_evidence,
            "id_range": id_range,
            "health": {
                "orphan_entries": orphan_entries,
                "entries_without_evidence": entries_without_evidence,
                "entries_without_dependencies": entries_without_deps,
                "stale_questions": stale_questions,
            },
        }

    @mcp.tool()
    def get_verse_entries(surah: int, ayah: int) -> list[dict]:
        """Get all entries that reference a specific verse as evidence."""
        conn = get_connection()
        scope_value = f"{surah}:{ayah}"

        # Verse-scoped entries (direct evidence) + their parent entries
        rows = conn.execute(
            """SELECT e.id as entry_id, e.content as entry_content, e.phase as entry_phase,
                      ed.dependency_type as verification, e.created_at,
                      parent.id as parent_id, parent.content as parent_content
               FROM entries e
               LEFT JOIN entry_dependencies ed ON ed.entry_id = e.id
               LEFT JOIN entries parent ON parent.id = ed.depends_on_entry_id
               WHERE e.scope_type = 'verse' AND e.scope_value = ?
               ORDER BY e.created_at DESC""",
            (scope_value,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Write tools ---

    @mcp.tool()
    def save_entry(
        content: str,
        phase: str = "question",
        evidence_verses: list[dict] | None = None,
        category: str = "uncategorized",
        scope_type: str | None = None,
        scope_value: str | None = None,
    ) -> dict:
        """Save a single research entry or insight discovered during conversation.

        When saving 2+ entries at once, prefer save_bulk_entries instead.
        """
        if phase not in VALID_PHASES:
            return {"success": False, "entry_id": "", "message": f"Invalid phase '{phase}'. Must be one of: {', '.join(sorted(VALID_PHASES))}"}

        conn = get_connection()
        evidence_verses = evidence_verses or []

        try:
            existing_id = _find_duplicate(conn, content)
            if existing_id:
                return {
                    "success": True,
                    "entry_id": existing_id,
                    "message": f"Duplicate detected -- returning existing {existing_id}",
                }

            entry_id = generate_entry_id(conn)
            now = _now()

            conn.execute(
                """INSERT INTO entries (id, content, phase, category, scope_type, scope_value, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (entry_id, content, phase, category, scope_type, scope_value, now, now)
            )

            # Create verse-scoped child entries for evidence
            for ev in evidence_verses:
                ev_entry_id = generate_entry_id(conn)
                ev_scope = f"{ev['surah']}:{ev['ayah']}"
                ev_notes = ev.get('notes') or f"Evidence verse {ev_scope}"
                conn.execute(
                    """INSERT INTO entries (id, content, phase, category, scope_type, scope_value, created_at, updated_at)
                       VALUES (?, ?, ?, ?, 'verse', ?, ?, ?)""",
                    (ev_entry_id, ev_notes, phase, category, ev_scope, now, now)
                )
                conn.execute(
                    """INSERT INTO entry_dependencies (entry_id, depends_on_entry_id, dependency_type, created_at)
                       VALUES (?, ?, 'supports', ?)""",
                    (ev_entry_id, entry_id, now)
                )

            save_database()
            invalidate_graph_cache()

            return {
                "success": True,
                "entry_id": entry_id,
                "message": f"Entry saved successfully with {len(evidence_verses)} evidence verse(s)",
            }
        except Exception as e:
            return {"success": False, "entry_id": "", "message": f"Failed to save entry: {e}"}

    @mcp.tool()
    def save_bulk_entries(entries: list[dict]) -> dict:
        """Save multiple research entries at once in a single operation.

        Much more efficient than calling save_entry repeatedly.
        Does not support evidence_verses -- use add_verse_evidence separately.
        """
        # Validate phases
        for i, entry in enumerate(entries):
            p = entry.get('phase', 'question')
            if p not in VALID_PHASES:
                return {"success": False, "entry_ids": [], "message": f"Invalid phase '{p}' in entry {i}. Must be one of: {', '.join(sorted(VALID_PHASES))}"}

        conn = get_connection()
        try:
            created_ids = []
            deduped_ids = []
            now = _now()

            for entry in entries:
                existing_id = _find_duplicate(conn, entry['content'])
                if existing_id:
                    deduped_ids.append(existing_id)
                    continue

                eid = generate_entry_id(conn)
                conn.execute(
                    """INSERT INTO entries (id, content, phase, category, scope_type, scope_value, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (eid, entry['content'], entry.get('phase', 'question'),
                     entry.get('category', 'uncategorized'),
                     entry.get('scope_type'), entry.get('scope_value'),
                     now, now)
                )
                created_ids.append(eid)

            save_database()
            invalidate_graph_cache()

            all_ids = created_ids + deduped_ids
            msg = f"Saved {len(created_ids)} new entries"
            if created_ids:
                msg += f" ({created_ids[0]} through {created_ids[-1]})"
            if deduped_ids:
                msg += f". Skipped {len(deduped_ids)} duplicate(s): {', '.join(deduped_ids)}"

            return {
                "success": True,
                "entry_ids": all_ids,
                "created": len(created_ids),
                "duplicates_skipped": len(deduped_ids),
                "message": msg,
            }
        except Exception as e:
            return {"success": False, "entry_ids": [], "message": f"Failed to save bulk entries: {e}"}

    @mcp.tool()
    def update_entry(
        entry_id: str,
        content: str | None = None,
        phase: str | None = None,
        scope_type: str | None = None,
        scope_value: str | None = None,
    ) -> dict:
        """Update an existing entry's content or phase."""
        if phase is not None and phase not in VALID_PHASES:
            return {"success": False, "message": f"Invalid phase '{phase}'. Must be one of: {', '.join(sorted(VALID_PHASES))}"}

        conn = get_connection()
        try:
            row = conn.execute("SELECT id FROM entries WHERE id = ?", (entry_id,)).fetchone()
            if not row:
                return {"success": False, "message": f"Entry {entry_id} not found"}

            now = _now()
            updates = ["updated_at = ?"]
            params: list = [now]

            if content is not None:
                updates.append("content = ?")
                params.append(content)
            if phase is not None:
                updates.append("phase = ?")
                params.append(phase)
            if scope_type is not None:
                updates.append("scope_type = ?")
                params.append(scope_type)
            if scope_value is not None:
                updates.append("scope_value = ?")
                params.append(scope_value)

            params.append(entry_id)
            conn.execute(f"UPDATE entries SET {', '.join(updates)} WHERE id = ?", params)
            save_database()
            invalidate_graph_cache()

            return {"success": True, "message": f"Entry {entry_id} updated successfully"}
        except Exception as e:
            return {"success": False, "message": f"Failed to update entry: {e}"}

    @mcp.tool()
    def delete_entry(entry_id: str) -> dict:
        """Safely delete an entry and its associated evidence from the database."""
        conn = get_connection()
        try:
            row = conn.execute("SELECT id FROM entries WHERE id = ?", (entry_id,)).fetchone()
            if not row:
                return {"success": False, "message": f"Entry {entry_id} not found"}

            # Delete verse-scoped child entries first
            child_ids = conn.execute(
                """SELECT ed.entry_id FROM entry_dependencies ed
                   JOIN entries e ON e.id = ed.entry_id
                   WHERE ed.depends_on_entry_id = ? AND e.scope_type = 'verse'""",
                (entry_id,)
            ).fetchall()
            for child in child_ids:
                conn.execute("DELETE FROM entry_dependencies WHERE entry_id = ? OR depends_on_entry_id = ?", (child['entry_id'], child['entry_id']))
                conn.execute("DELETE FROM entries WHERE id = ?", (child['entry_id'],))

            conn.execute(
                "DELETE FROM entry_dependencies WHERE entry_id = ? OR depends_on_entry_id = ?",
                (entry_id, entry_id)
            )
            conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))

            save_database()
            invalidate_graph_cache()

            return {"success": True, "message": f"Entry {entry_id} deleted successfully"}
        except Exception as e:
            return {"success": False, "message": f"Failed to delete entry: {e}"}

    @mcp.tool()
    def delete_multiple_entries(entry_ids: list[str]) -> dict:
        """Delete multiple entries at once."""
        conn = get_connection()
        failed = []
        deleted = 0

        try:
            for eid in entry_ids:
                row = conn.execute("SELECT id FROM entries WHERE id = ?", (eid,)).fetchone()
                if not row:
                    failed.append(eid)
                    continue

                # Delete verse-scoped child entries first
                child_ids = conn.execute(
                    """SELECT ed.entry_id FROM entry_dependencies ed
                       JOIN entries e ON e.id = ed.entry_id
                       WHERE ed.depends_on_entry_id = ? AND e.scope_type = 'verse'""",
                    (eid,)
                ).fetchall()
                for child in child_ids:
                    conn.execute("DELETE FROM entry_dependencies WHERE entry_id = ? OR depends_on_entry_id = ?", (child['entry_id'], child['entry_id']))
                    conn.execute("DELETE FROM entries WHERE id = ?", (child['entry_id'],))

                conn.execute(
                    "DELETE FROM entry_dependencies WHERE entry_id = ? OR depends_on_entry_id = ?",
                    (eid, eid)
                )
                conn.execute("DELETE FROM entries WHERE id = ?", (eid,))
                deleted += 1

            save_database()
            invalidate_graph_cache()

            msg = f"Deleted {deleted} entries."
            if failed:
                msg += f" Failed: {len(failed)}"
            return {"success": True, "deleted": deleted, "failed": failed, "message": msg}
        except Exception as e:
            return {"success": False, "deleted": deleted, "failed": failed, "message": f"Failed during deletion: {e}"}

    @mcp.tool()
    def find_related_entries(entry_id: str, limit: int = 20) -> dict:
        """Find entries structurally related to a given entry through shared verse evidence, shared scope, or same-surah evidence."""
        conn = get_connection()

        entry_row = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
        if not entry_row:
            return {"entry": None, "shared_evidence": [], "shared_scope": [], "same_surah_entries": []}
        entry = dict(entry_row)

        # 1. Entries sharing the same verse scope (both scoped to the same verse)
        #    Also: entries whose verse-scoped children overlap
        shared_map: dict[str, dict] = {}

        if entry['scope_type'] == 'verse':
            # This entry IS a verse-scoped entry; find siblings (other entries scoped to same verse)
            siblings = conn.execute(
                """SELECT e.id, e.content, e.phase, e.category, e.created_at, e.updated_at, e.scope_value
                   FROM entries e
                   WHERE e.scope_type = 'verse' AND e.scope_value = ? AND e.id != ?
                   ORDER BY e.updated_at DESC LIMIT ?""",
                (entry['scope_value'], entry_id, limit)
            ).fetchall()
            for r in siblings:
                r = dict(r)
                parts = r['scope_value'].split(':')
                eid = r['id']
                if eid not in shared_map:
                    shared_map[eid] = {
                        "entry": {k: r[k] for k in ('id', 'content', 'phase', 'category', 'created_at', 'updated_at')},
                        "shared_verses": [{"surah": int(parts[0]), "ayah": int(parts[1]) if len(parts) > 1 else 0}],
                    }
        else:
            # Find other parent entries whose verse-scoped children overlap with this entry's children
            my_verses = conn.execute(
                """SELECT e.scope_value FROM entry_dependencies ed
                   JOIN entries e ON e.id = ed.entry_id
                   WHERE ed.depends_on_entry_id = ? AND e.scope_type = 'verse'""",
                (entry_id,)
            ).fetchall()
            my_verse_set = {r['scope_value'] for r in my_verses}

            if my_verse_set:
                placeholders = ','.join('?' * len(my_verse_set))
                overlap_rows = conn.execute(
                    f"""SELECT DISTINCT ed2.depends_on_entry_id as parent_id, e2.scope_value,
                               p.content, p.phase, p.category, p.created_at, p.updated_at
                        FROM entries e2
                        JOIN entry_dependencies ed2 ON ed2.entry_id = e2.id
                        JOIN entries p ON p.id = ed2.depends_on_entry_id
                        WHERE e2.scope_type = 'verse' AND e2.scope_value IN ({placeholders})
                          AND ed2.depends_on_entry_id != ?
                        ORDER BY p.updated_at DESC LIMIT ?""",
                    list(my_verse_set) + [entry_id, limit]
                ).fetchall()
                for r in overlap_rows:
                    r = dict(r)
                    pid = r['parent_id']
                    parts = r['scope_value'].split(':')
                    if pid not in shared_map:
                        shared_map[pid] = {
                            "entry": {"id": pid, "content": r['content'], "phase": r['phase'],
                                      "category": r['category'], "created_at": r['created_at'], "updated_at": r['updated_at']},
                            "shared_verses": [],
                        }
                    shared_map[pid]["shared_verses"].append(
                        {"surah": int(parts[0]), "ayah": int(parts[1]) if len(parts) > 1 else 0}
                    )

        # 2. Entries sharing the same scope (same scope_type + scope_value)
        shared_scope_rows = conn.execute(
            """SELECT e2.id, e2.content, e2.phase, e2.category, e2.created_at, e2.updated_at,
                      e2.scope_type, e2.scope_value
             FROM entries e1
             JOIN entries e2 ON e1.scope_type = e2.scope_type
               AND e1.scope_value = e2.scope_value
               AND e1.id != e2.id
             WHERE e1.id = ? AND e1.scope_type IS NOT NULL
             ORDER BY e2.updated_at DESC
             LIMIT ?""",
            (entry_id, limit)
        ).fetchall()

        scope_map: dict[str, dict] = {}
        for row in shared_scope_rows:
            r = dict(row)
            eid = r['id']
            if eid not in scope_map:
                scope_map[eid] = {
                    "entry": {k: r[k] for k in ('id', 'content', 'phase', 'category', 'created_at', 'updated_at')},
                    "shared_scope": {"type": r['scope_type'], "value": r['scope_value']},
                }

        # 3. Entries with verse children in the same surah (weaker signal)
        surah_map: dict[str, dict] = {}

        if entry['scope_type'] == 'verse' and entry['scope_value']:
            my_surah = entry['scope_value'].split(':')[0]
            surah_rows = conn.execute(
                """SELECT DISTINCT e.id, e.content, e.phase, e.category, e.created_at, e.updated_at
                   FROM entries e
                   WHERE e.scope_type = 'verse' AND e.scope_value LIKE ? AND e.id != ?
                     AND e.scope_value != ?
                   ORDER BY e.updated_at DESC LIMIT ?""",
                (f"{my_surah}:%", entry_id, entry['scope_value'], limit)
            ).fetchall()
            for r in surah_rows:
                r = dict(r)
                surah_map[r['id']] = {
                    "entry": {k: r[k] for k in ('id', 'content', 'phase', 'category', 'created_at', 'updated_at')},
                    "surah": int(my_surah),
                }

        return {
            "entry": entry,
            "shared_evidence": list(shared_map.values()),
            "shared_scope": list(scope_map.values()),
            "same_surah_entries": list(surah_map.values()),
        }

    @mcp.tool()
    def add_entry_dependency(
        entry_id: str,
        depends_on_entry_id: str,
        dependency_type: str,
    ) -> dict:
        """Create a typed relationship between two entries.

        Types: depends_on, supports, contradicts, refines, related.
        """
        conn = get_connection()
        valid_types = ('depends_on', 'supports', 'contradicts', 'refines', 'related')
        if dependency_type not in valid_types:
            return {"success": False, "message": f"Invalid dependency_type. Must be one of: {', '.join(valid_types)}"}

        if entry_id == depends_on_entry_id:
            return {"success": False, "message": "An entry cannot depend on itself"}

        try:
            if not conn.execute("SELECT id FROM entries WHERE id = ?", (entry_id,)).fetchone():
                return {"success": False, "message": f"Entry {entry_id} not found"}
            if not conn.execute("SELECT id FROM entries WHERE id = ?", (depends_on_entry_id,)).fetchone():
                return {"success": False, "message": f"Entry {depends_on_entry_id} not found"}

            dup = conn.execute(
                "SELECT entry_id FROM entry_dependencies WHERE entry_id = ? AND depends_on_entry_id = ? AND dependency_type = ?",
                (entry_id, depends_on_entry_id, dependency_type)
            ).fetchone()
            if dup:
                return {"success": False, "message": f"Dependency already exists: {entry_id} --{dependency_type}--> {depends_on_entry_id}"}

            now = _now()
            conn.execute(
                "INSERT INTO entry_dependencies (entry_id, depends_on_entry_id, dependency_type, created_at) VALUES (?, ?, ?, ?)",
                (entry_id, depends_on_entry_id, dependency_type, now)
            )
            save_database()
            invalidate_graph_cache()

            return {"success": True, "message": f"Dependency created: {entry_id} --{dependency_type}--> {depends_on_entry_id}"}
        except Exception as e:
            return {"success": False, "message": f"Failed to add dependency: {e}"}
