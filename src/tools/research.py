"""Research tools: entries CRUD, evidence, relationships."""

from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from ..db import get_connection, save_database
from ..utils.short_id import generate_entry_id
from ..utils.units import get_entry_locations, add_entry_location, entries_at_verse

mcp: FastMCP

VALID_PHASES = {'question', 'hypothesis', 'validation', 'active_verification', 'passive_verification', 'validated', 'rejected'}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _find_duplicate(conn, content: str) -> str | None:
    """Return existing entry ID if identical cross-cutting content exists.

    Only matches entries with no locations and no feature_id (cross-cutting).
    Verse-evidence and feature-anchored entries are allowed to share content
    because they're anchored to different locations.
    """
    row = conn.execute(
        """SELECT id FROM entries
           WHERE TRIM(content) = TRIM(?)
             AND feature_id IS NULL
             AND NOT EXISTS (SELECT 1 FROM entry_locations el WHERE el.entry_id = entries.id)""",
        (content,)
    ).fetchone()
    return row["id"] if row else None


def _augment_entry_dict(conn, d: dict) -> dict:
    """Add locations array to entry dict for output."""
    locations = get_entry_locations(conn, d['id'])
    if locations:
        d['locations'] = locations
    return d


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
            if scope_type == 'verse':
                sql += " AND EXISTS (SELECT 1 FROM entry_locations el WHERE el.entry_id = entries.id)"
            elif scope_type in ('root', 'lemma', 'pattern', 'surah'):
                sql += " AND feature_id IS NOT NULL"
            else:
                sql += " AND feature_id IS NULL AND NOT EXISTS (SELECT 1 FROM entry_locations el WHERE el.entry_id = entries.id)"

        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return [_augment_entry_dict(conn, dict(r)) for r in rows]

    @mcp.tool()
    def get_entry(entry_id: str) -> dict:
        """Get a single entry by its ID."""
        conn = get_connection()
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
        if not row:
            return {"error": f"Entry {entry_id} not found"}
        return _augment_entry_dict(conn, dict(row))

    @mcp.tool()
    def get_entry_evidence(entry_id: str) -> list[dict]:
        """Get all evidence (verse references) supporting a specific research entry."""
        conn = get_connection()
        rows = conn.execute(
            """SELECT el.surah, el.ayah_start AS ayah, el.ayah_end,
                      el.word_start, el.word_end,
                      el.verification, el.notes
               FROM entry_locations el
               WHERE el.entry_id = ?
                 AND el.verification IS NOT NULL
               ORDER BY el.surah, el.ayah_start""",
            (entry_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    @mcp.tool()
    def get_entry_dependencies(entry_id: str) -> dict:
        """Get structurally related entries discovered through shared features and locations."""
        conn = get_connection()

        entry_row = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
        if not entry_row:
            return {"entry": None, "related": []}

        entry = dict(entry_row)
        related = []

        # 1. Entries sharing the same feature_id (same root/lemma/etc.)
        if entry.get('feature_id'):
            # Find the feature details
            feat = conn.execute("SELECT feature_type, lookup_key FROM features WHERE id = ?", (entry['feature_id'],)).fetchone()
            if feat:
                # Find other entries whose features are related via morphemes
                # e.g., if this is a root entry, find lemma entries derived from it
                if feat['feature_type'] == 'root':
                    lemma_entries = conn.execute(
                        """SELECT DISTINCT e.id, e.content, e.phase, e.category
                           FROM entries e
                           JOIN features f ON e.feature_id = f.id
                           JOIN morpheme_library ml ON ml.lemma_id = f.id
                           WHERE ml.root_id = ? AND e.id != ?""",
                        (entry['feature_id'], entry_id)
                    ).fetchall()
                    for r in lemma_entries:
                        related.append({"entry": dict(r), "relation": "derived_lemma"})

        # 2. Entries sharing locations
        my_locs = get_entry_locations(conn, entry_id)
        if my_locs:
            for loc in my_locs:
                if loc.get('ayah_start'):
                    loc_eids = entries_at_verse(conn, loc['surah'], loc['ayah_start'])
                    for eid in loc_eids:
                        if eid != entry_id:
                            r = conn.execute(
                                "SELECT id, content, phase, category FROM entries WHERE id = ?", (eid,)
                            ).fetchone()
                            if r:
                                related.append({"entry": dict(r), "relation": "shared_location"})

        return {"entry": _augment_entry_dict(conn, entry), "related": related}

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
            "SELECT count(DISTINCT entry_id) FROM entry_locations"
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

        # Entry type distribution
        feature_count = conn.execute(
            "SELECT count(*) FROM entries WHERE feature_id IS NOT NULL"
        ).fetchone()[0]
        verse_count = total_evidence
        cross_cutting = conn.execute(
            """SELECT count(*) FROM entries
               WHERE feature_id IS NULL
                 AND NOT EXISTS (SELECT 1 FROM entry_locations el WHERE el.entry_id = entries.id)"""
        ).fetchone()[0]

        by_type = {
            "feature_anchored": feature_count,
            "verse_evidence": verse_count,
            "cross_cutting": cross_cutting,
        }

        # Health metrics
        # Unanchored entries: no feature_id AND no locations
        unanchored = conn.execute(
            """SELECT count(*) FROM entries e
               WHERE e.feature_id IS NULL
                 AND NOT EXISTS (SELECT 1 FROM entry_locations el WHERE el.entry_id = e.id)"""
        ).fetchone()[0]

        # Entries without any verse evidence (no locations with verification)
        entries_without_evidence = conn.execute(
            """SELECT count(*) FROM entries e
               WHERE NOT EXISTS (
                   SELECT 1 FROM entry_locations el
                   WHERE el.entry_id = e.id AND el.verification IS NOT NULL
               )"""
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
            "by_type": by_type,
            "confidence": confidence_distribution,
            "total_evidence": total_evidence,
            "id_range": id_range,
            "health": {
                "unanchored_entries": unanchored,
                "entries_without_evidence": entries_without_evidence,
                "stale_questions": stale_questions,
            },
        }

    @mcp.tool()
    def get_verse_entries(surah: int, ayah: int) -> list[dict]:
        """Get all entries that reference a specific verse."""
        conn = get_connection()

        entry_ids = entries_at_verse(conn, surah, ayah)
        if not entry_ids:
            return []

        placeholders = ",".join("?" for _ in entry_ids)
        rows = conn.execute(
            f"""SELECT e.id as entry_id, e.content as entry_content, e.phase as entry_phase,
                      e.created_at, el.verification, el.notes as location_notes
               FROM entries e
               JOIN entry_locations el ON el.entry_id = e.id
               WHERE e.id IN ({placeholders})
                 AND el.surah = ? AND el.ayah_start = ?
               ORDER BY e.created_at DESC""",
            entry_ids + [surah, ayah]
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

            # Resolve feature_id if scope_type is a feature type
            feature_id = None
            if scope_type in ('root', 'lemma') and scope_value:
                from .linguistic import _resolve_feature_id
                feature_id = _resolve_feature_id(conn, scope_type, scope_value)

            conn.execute(
                """INSERT INTO entries (id, content, phase, category, feature_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (entry_id, content, phase, category, feature_id, now, now)
            )

            # Add evidence verses as locations with verification
            for ev in evidence_verses:
                ev_notes = ev.get('notes') or f"Evidence verse {ev['surah']}:{ev['ayah']}"
                conn.execute(
                    """INSERT OR IGNORE INTO entry_locations
                       (entry_id, surah, ayah_start, verification, notes)
                       VALUES (?, ?, ?, 'supports', ?)""",
                    (entry_id, ev['surah'], ev['ayah'], ev_notes)
                )

            save_database()

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

                # Resolve feature_id if scope_type provided
                feature_id = None
                scope_type = entry.get('scope_type')
                scope_value = entry.get('scope_value')
                if scope_type in ('root', 'lemma') and scope_value:
                    from .linguistic import _resolve_feature_id
                    feature_id = _resolve_feature_id(conn, scope_type, scope_value)

                conn.execute(
                    """INSERT INTO entries (id, content, phase, category, feature_id, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (eid, entry['content'], entry.get('phase', 'question'),
                     entry.get('category', 'uncategorized'),
                     feature_id, now, now)
                )
                created_ids.append(eid)

            save_database()

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
            if scope_type is not None and scope_value is not None:
                # Resolve feature_id from scope_type/scope_value
                if scope_type in ('root', 'lemma'):
                    from .linguistic import _resolve_feature_id
                    feature_id = _resolve_feature_id(conn, scope_type, scope_value)
                    if feature_id is not None:
                        updates.append("feature_id = ?")
                        params.append(feature_id)

            params.append(entry_id)
            conn.execute(f"UPDATE entries SET {', '.join(updates)} WHERE id = ?", params)
            save_database()

            return {"success": True, "message": f"Entry {entry_id} updated successfully"}
        except Exception as e:
            return {"success": False, "message": f"Failed to update entry: {e}"}

    @mcp.tool()
    def delete_entry(entry_id: str) -> dict:
        """Safely delete an entry and its associated locations from the database."""
        conn = get_connection()
        try:
            row = conn.execute("SELECT id FROM entries WHERE id = ?", (entry_id,)).fetchone()
            if not row:
                return {"success": False, "message": f"Entry {entry_id} not found"}

            conn.execute("DELETE FROM entry_locations WHERE entry_id = ?", (entry_id,))
            conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))

            save_database()

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

                conn.execute("DELETE FROM entry_locations WHERE entry_id = ?", (eid,))
                conn.execute("DELETE FROM entries WHERE id = ?", (eid,))
                deleted += 1

            save_database()

            msg = f"Deleted {deleted} entries."
            if failed:
                msg += f" Failed: {len(failed)}"
            return {"success": True, "deleted": deleted, "failed": failed, "message": msg}
        except Exception as e:
            return {"success": False, "deleted": deleted, "failed": failed, "message": f"Failed during deletion: {e}"}

    @mcp.tool()
    def find_related_entries(entry_id: str, limit: int = 20) -> dict:
        """Find entries structurally related to a given entry through shared locations, shared features, or same-surah presence."""
        conn = get_connection()

        entry_row = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
        if not entry_row:
            return {"entry": None, "shared_locations": [], "shared_feature": [], "same_surah_entries": []}
        entry = dict(entry_row)

        # Get this entry's locations
        my_locations = get_entry_locations(conn, entry_id)

        # 1. Entries sharing verse locations
        shared_map: dict[str, dict] = {}
        if my_locations:
            for loc in my_locations:
                loc_entry_ids = entries_at_verse(conn, loc['surah'], loc['ayah_start']) if loc.get('ayah_start') else []
                for eid in loc_entry_ids:
                    if eid != entry_id and eid not in shared_map:
                        r = conn.execute(
                            "SELECT id, content, phase, category, created_at, updated_at FROM entries WHERE id = ?",
                            (eid,)
                        ).fetchone()
                        if r:
                            shared_map[eid] = {
                                "entry": dict(r),
                                "shared_verses": [{"surah": loc['surah'], "ayah": loc['ayah_start']}],
                            }
                    elif eid != entry_id and eid in shared_map:
                        shared_map[eid]["shared_verses"].append({"surah": loc['surah'], "ayah": loc['ayah_start']})

        # 2. Entries sharing related features (e.g., same root -> find lemma entries)
        feature_related: dict[str, dict] = {}
        if entry.get('feature_id') is not None:
            feat = conn.execute("SELECT feature_type, lookup_key FROM features WHERE id = ?", (entry['feature_id'],)).fetchone()
            if feat and feat['feature_type'] == 'root':
                # Find entries anchored to lemmas derived from this root
                rows = conn.execute(
                    """SELECT DISTINCT e.id, e.content, e.phase, e.category, e.created_at, e.updated_at,
                              f.lookup_key as feature_value
                       FROM entries e
                       JOIN features f ON e.feature_id = f.id
                       JOIN morpheme_library ml ON ml.lemma_id = f.id
                       WHERE ml.root_id = ? AND e.id != ?
                       ORDER BY e.updated_at DESC LIMIT ?""",
                    (entry['feature_id'], entry_id, limit)
                ).fetchall()
                for r in rows:
                    r = dict(r)
                    feature_related[r['id']] = {
                        "entry": {k: r[k] for k in ('id', 'content', 'phase', 'category', 'created_at', 'updated_at')},
                        "relationship": "derived_lemma",
                        "feature_value": r['feature_value'],
                    }

        # 3. Entries in the same surah
        surah_map: dict[str, dict] = {}
        if my_locations:
            my_surahs = {loc['surah'] for loc in my_locations}
            for s in my_surahs:
                surah_rows = conn.execute(
                    """SELECT DISTINCT e.id, e.content, e.phase, e.category, e.created_at, e.updated_at
                       FROM entries e
                       JOIN entry_locations el ON el.entry_id = e.id
                       WHERE el.surah = ? AND e.id != ?
                       ORDER BY e.updated_at DESC LIMIT ?""",
                    (s, entry_id, limit)
                ).fetchall()
                for r in surah_rows:
                    r = dict(r)
                    surah_map[r['id']] = {
                        "entry": {k: r[k] for k in ('id', 'content', 'phase', 'category', 'created_at', 'updated_at')},
                        "surah": s,
                    }

        return {
            "entry": _augment_entry_dict(conn, entry),
            "shared_locations": list(shared_map.values()),
            "shared_feature": list(feature_related.values()),
            "same_surah_entries": list(surah_map.values()),
        }

