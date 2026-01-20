#!/usr/bin/env python3
"""
Migrate QuranResearch JSON database into Kalima SQLite.

This script reads quran_research_database.json and inserts:
- Notes as Claims
- References as Evidence
- Connections as Dependencies
"""

import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# Paths
KALIMA_ROOT = Path(__file__).parent.parent
QURAN_RESEARCH_ROOT = KALIMA_ROOT.parent / "QuranResearch"
KALIMA_DB = KALIMA_ROOT / "data" / "database" / "kalima.db"
QURAN_RESEARCH_JSON = QURAN_RESEARCH_ROOT / "quran_research_database.json"

# Phase mapping from QuranResearch to Kalima
PHASE_MAP = {
    "question": "question",
    "hypothesis": "hypothesis",
    "validation": "validation",
    "active verification": "active_verification",
    "passive verification": "passive_verification",
}


def load_quran_research_data():
    """Load the QuranResearch JSON database."""
    if not QURAN_RESEARCH_JSON.exists():
        print(f"Error: {QURAN_RESEARCH_JSON} not found")
        sys.exit(1)

    with open(QURAN_RESEARCH_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)


def connect_kalima_db():
    """Connect to Kalima SQLite database."""
    if not KALIMA_DB.exists():
        print(f"Error: {KALIMA_DB} not found")
        print("Make sure Kalima database is initialized first.")
        sys.exit(1)

    return sqlite3.connect(KALIMA_DB)


def migrate_notes_to_claims(conn, data):
    """Migrate QuranResearch notes to Kalima claims."""
    notes = data.get('notes', [])
    print(f"Migrating {len(notes)} notes to claims...")

    cursor = conn.cursor()
    migrated = 0

    for note in notes:
        note_id = note.get('id')
        content = note.get('content', '')
        stage = note.get('stage', 'question')
        pattern_query = note.get('pattern_query')

        # Map phase
        phase = PHASE_MAP.get(stage.lower(), 'question')

        # Generate claim ID
        claim_id = f"claim_{note_id}"

        # Check if pattern_query suggests this should be a pattern
        # Patterns are notes with empty references but have pattern_query
        references = note.get('references', [])
        is_pattern = len(references) == 0 and pattern_query

        if is_pattern:
            # Insert as pattern
            pattern_id = f"pattern_{note_id}"
            cursor.execute("""
                INSERT OR REPLACE INTO patterns
                (id, description, pattern_type, scope, phase, created_at, updated_at)
                VALUES (?, ?, 'morphological', ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (pattern_id, content, pattern_query, phase))

            # Also create a claim that references this pattern
            cursor.execute("""
                INSERT OR REPLACE INTO claims
                (id, content, phase, pattern_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (claim_id, content, phase, pattern_id))
        else:
            # Insert as regular claim
            cursor.execute("""
                INSERT OR REPLACE INTO claims
                (id, content, phase, pattern_id, created_at, updated_at)
                VALUES (?, ?, ?, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (claim_id, content, phase))

        # Insert evidence links (verse references)
        for ref in references:
            start = ref.get('range', {}).get('start', [])
            if len(start) >= 2:
                surah, ayah = start[0], start[1]
                ref_phase = PHASE_MAP.get(ref.get('stage', 'question').lower(), 'question')
                justification = ref.get('justification', '')

                evidence_id = str(uuid4())
                cursor.execute("""
                    INSERT OR REPLACE INTO claim_evidence
                    (id, claim_id, surah, ayah, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (evidence_id, claim_id, surah, ayah, justification))

        # Insert dependencies (connections)
        connections = note.get('connections', [])
        for conn_id in connections:
            target_claim_id = f"claim_{conn_id}"
            cursor.execute("""
                INSERT OR IGNORE INTO claim_dependencies
                (claim_id, depends_on_claim_id, dependency_type, created_at)
                VALUES (?, ?, 'requires', CURRENT_TIMESTAMP)
            """, (claim_id, target_claim_id))

        migrated += 1

    conn.commit()
    print(f"✓ Migrated {migrated} notes to claims")
    return migrated


def verify_migration(conn):
    """Verify the migration succeeded."""
    cursor = conn.cursor()

    # Count claims
    cursor.execute("SELECT COUNT(*) FROM claims")
    claim_count = cursor.fetchone()[0]

    # Count patterns
    cursor.execute("SELECT COUNT(*) FROM patterns")
    pattern_count = cursor.fetchone()[0]

    # Count evidence
    cursor.execute("SELECT COUNT(*) FROM claim_evidence")
    evidence_count = cursor.fetchone()[0]

    # Count dependencies
    cursor.execute("SELECT COUNT(*) FROM claim_dependencies")
    dep_count = cursor.fetchone()[0]

    print("\nMigration Summary:")
    print(f"  Claims: {claim_count}")
    print(f"  Patterns: {pattern_count}")
    print(f"  Evidence links: {evidence_count}")
    print(f"  Dependencies: {dep_count}")


def main():
    import sys
    import io
    # Fix Windows console encoding
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("QuranResearch -> Kalima Migration")
    print("=" * 50)

    # Load data
    print(f"Loading {QURAN_RESEARCH_JSON}...")
    data = load_quran_research_data()

    # Connect to Kalima
    print(f"Connecting to {KALIMA_DB}...")
    conn = connect_kalima_db()

    try:
        # Migrate
        migrate_notes_to_claims(conn, data)

        # Verify
        verify_migration(conn)

        print("\n✓ Migration complete!")
        print("\nNext steps:")
        print("1. Archive the old JSON file:")
        print(f"   mv {QURAN_RESEARCH_JSON} {QURAN_RESEARCH_JSON}.backup")
        print("2. Test the Kalima app to verify data integrity")

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
