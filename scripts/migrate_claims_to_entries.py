"""Migration script: Rename claims → entries, add categories, clean up data."""

import re
import sqlite3
import sys

DB_PATH = r"c:\Codex\Kalima\data\database\kalima.db"

# Category mapping: content prefix → category
CATEGORY_MAP = [
    # Exact prefix matches (order matters — first match wins)
    (re.compile(r"^Fine Arts Essay(?:\s*\(expanded\))?:\s*", re.IGNORECASE), "essay"),
    (re.compile(r"^Root:\s*", re.IGNORECASE), "root_analysis"),
    (re.compile(r"^NCU (?:Framework|Compatibility|Concept):\s*", re.IGNORECASE), "ncu"),
    (re.compile(r"^Historical Context:\s*", re.IGNORECASE), "historical"),
    (re.compile(r"^Kalima Design:\s*", re.IGNORECASE), "design"),
    (re.compile(r"^Channeling session:\s*", re.IGNORECASE), "session"),
    (re.compile(r"^Personal history:\s*", re.IGNORECASE), "personal"),
    (re.compile(r"^QUESTION:\s*", re.IGNORECASE), "question"),
    (re.compile(r"^Universal Translator Project:\s*", re.IGNORECASE), "design"),
    (re.compile(r"^(?:HYPOTHESIS|SEMANTIC CLAIM|MORPHOLOGICAL INSIGHT|EPISTEMIC BLOCKING CLAIM|LINGUISTIC WARNING|ERA TRANSITION INSIGHT|STYLISTIC CLAIM[^:]*|COMPREHENSIVE GRAMMATICAL ANALYSIS|CRITICAL DEFINITION|FINAL DEFINITION|CORRECTED INTERPRETATION|Taxonomy clarification|Cross-surah connection|Connection to|Falsification-Based Validation|Hierarchy of human terms):\s*", re.IGNORECASE), "quranic_research"),
    # "Claim N:" pattern
    (re.compile(r"^Claim\s+\d+:\s*", re.IGNORECASE), "quranic_research"),
    # Surah theme entries
    (re.compile(r"^Surah \d+\s*\("), "quranic_research"),
    # THE COMING RASOOL, ANGELS' SITUATION, RESPONSIBILITY, etc.
    (re.compile(r"^(?:THE COMING|ANGELS'|RESPONSIBILITY)\s", re.IGNORECASE), "quranic_research"),
]


def run_migration():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")

    print("Starting migration: claims -> entries")

    # --- Drop views first (they reference old table names and block ALTER/DROP) ---
    print("  Dropping old views...")
    conn.execute("DROP VIEW IF EXISTS verse_claims")

    # --- 1a. Rename tables ---
    print("  Renaming tables...")
    conn.execute("ALTER TABLE claims RENAME TO entries")
    conn.execute("ALTER TABLE claim_evidence RENAME TO entry_evidence")
    conn.execute("ALTER TABLE claim_dependencies RENAME TO entry_dependencies")

    # --- 1b. Add category column ---
    print("  Adding category column...")
    conn.execute("ALTER TABLE entries ADD COLUMN category TEXT DEFAULT 'uncategorized'")

    # --- 1c. Drop note_file column (recreate table without it) ---
    print("  Dropping note_file column...")
    conn.execute("""
        CREATE TABLE entries_new (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            phase TEXT DEFAULT 'question',
            pattern_id TEXT,
            category TEXT DEFAULT 'uncategorized',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(pattern_id) REFERENCES patterns(id)
        )
    """)
    conn.execute("""
        INSERT INTO entries_new (id, content, phase, pattern_id, category, created_at, updated_at)
        SELECT id, content, phase, pattern_id, category, created_at, updated_at FROM entries
    """)
    conn.execute("DROP TABLE entries")
    conn.execute("ALTER TABLE entries_new RENAME TO entries")

    # --- 1d. Migrate IDs (claim_N → entry_N) ---
    print("  Migrating IDs...")
    conn.execute("UPDATE entries SET id = REPLACE(id, 'claim_', 'entry_')")
    conn.execute("UPDATE entry_evidence SET claim_id = REPLACE(claim_id, 'claim_', 'entry_')")
    conn.execute("UPDATE entry_dependencies SET claim_id = REPLACE(claim_id, 'claim_', 'entry_')")
    conn.execute("UPDATE entry_dependencies SET depends_on_claim_id = REPLACE(depends_on_claim_id, 'claim_', 'entry_')")
    conn.execute("UPDATE verse_evidence SET claim_id = REPLACE(claim_id, 'claim_', 'entry_')")
    conn.execute("UPDATE workflow_sessions SET claim_id = REPLACE(claim_id, 'claim_', 'entry_')")

    # --- 1d (cont). Rename FK columns via create-copy-drop-rename ---
    print("  Renaming FK columns...")

    # entry_evidence: claim_id → entry_id
    conn.execute("""
        CREATE TABLE entry_evidence_new (
            id TEXT PRIMARY KEY,
            entry_id TEXT NOT NULL,
            surah INTEGER,
            ayah INTEGER,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(entry_id) REFERENCES entries(id)
        )
    """)
    conn.execute("INSERT INTO entry_evidence_new SELECT id, claim_id, surah, ayah, notes, created_at FROM entry_evidence")
    conn.execute("DROP TABLE entry_evidence")
    conn.execute("ALTER TABLE entry_evidence_new RENAME TO entry_evidence")

    # entry_dependencies: claim_id → entry_id, depends_on_claim_id → depends_on_entry_id
    conn.execute("""
        CREATE TABLE entry_dependencies_new (
            entry_id TEXT NOT NULL,
            depends_on_entry_id TEXT NOT NULL,
            dependency_type TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (entry_id, depends_on_entry_id, dependency_type)
        )
    """)
    conn.execute("INSERT INTO entry_dependencies_new SELECT claim_id, depends_on_claim_id, dependency_type, created_at FROM entry_dependencies")
    conn.execute("DROP TABLE entry_dependencies")
    conn.execute("ALTER TABLE entry_dependencies_new RENAME TO entry_dependencies")

    # verse_evidence: claim_id → entry_id
    conn.execute("""
        CREATE TABLE verse_evidence_new (
            id TEXT PRIMARY KEY,
            entry_id TEXT NOT NULL,
            verse_surah INTEGER NOT NULL,
            verse_ayah INTEGER NOT NULL,
            verification TEXT NOT NULL,
            notes TEXT,
            verified_at TEXT NOT NULL,
            FOREIGN KEY (entry_id) REFERENCES entries(id)
        )
    """)
    conn.execute("INSERT INTO verse_evidence_new SELECT id, claim_id, verse_surah, verse_ayah, verification, notes, verified_at FROM verse_evidence")
    conn.execute("DROP TABLE verse_evidence")
    conn.execute("ALTER TABLE verse_evidence_new RENAME TO verse_evidence")

    # workflow_sessions: claim_id → entry_id
    conn.execute("""
        CREATE TABLE workflow_sessions_new (
            session_id TEXT PRIMARY KEY,
            entry_id TEXT NOT NULL,
            workflow_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            current_index INTEGER NOT NULL,
            total_verses INTEGER NOT NULL,
            status TEXT NOT NULL,
            linguistic_features TEXT,
            surah INTEGER,
            verses_json TEXT NOT NULL,
            FOREIGN KEY (entry_id) REFERENCES entries(id)
        )
    """)
    conn.execute("INSERT INTO workflow_sessions_new SELECT session_id, claim_id, workflow_type, created_at, current_index, total_verses, status, linguistic_features, surah, verses_json FROM workflow_sessions")
    conn.execute("DROP TABLE workflow_sessions")
    conn.execute("ALTER TABLE workflow_sessions_new RENAME TO workflow_sessions")

    # --- 1e. Recreate view ---
    print("  Recreating view...")
    conn.execute("DROP VIEW IF EXISTS verse_claims")
    conn.execute("""
        CREATE VIEW verse_entries AS
        SELECT surah, ayah, entry_id, 'entry_evidence' as evidence_type, notes, NULL as verification, created_at
        FROM entry_evidence
        UNION ALL
        SELECT verse_surah as surah, verse_ayah as ayah, entry_id, 'verse_evidence' as evidence_type, notes, verification, verified_at as created_at
        FROM verse_evidence
    """)

    # --- 1f/1g. Auto-categorize and strip prefixes ---
    print("  Categorizing entries and stripping prefixes...")
    rows = conn.execute("SELECT id, content FROM entries").fetchall()
    categorized = 0
    for row in rows:
        eid, content = row["id"], row["content"]
        category = "uncategorized"
        new_content = content

        for pattern, cat in CATEGORY_MAP:
            m = pattern.match(content)
            if m:
                category = cat
                new_content = content[m.end():].strip()
                break

        if category != "uncategorized" or new_content != content:
            conn.execute(
                "UPDATE entries SET category = ?, content = ? WHERE id = ?",
                (category, new_content, eid)
            )
            categorized += 1
        else:
            conn.execute("UPDATE entries SET category = 'uncategorized' WHERE id = ?", (eid,))

    print(f"    Categorized {categorized} entries with specific categories")

    # --- 1h. Delete test entry ---
    print("  Deleting test entry...")
    conn.execute("DELETE FROM entry_evidence WHERE entry_id = 'entry_273'")
    conn.execute("DELETE FROM entry_dependencies WHERE entry_id = 'entry_273' OR depends_on_entry_id = 'entry_273'")
    conn.execute("DELETE FROM entries WHERE id = 'entry_273'")

    # --- 1i. Recreate indexes ---
    print("  Creating indexes...")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_phase ON entries(phase)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_pattern ON entries(pattern_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_category ON entries(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entry_evidence_entry ON entry_evidence(entry_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entry_evidence_verse ON entry_evidence(surah, ayah)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entry_deps_from ON entry_dependencies(entry_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entry_deps_to ON entry_dependencies(depends_on_entry_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_verse_evidence_entry ON verse_evidence(entry_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_verse_evidence_verse ON verse_evidence(verse_surah, verse_ayah)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_workflow_sessions_entry ON workflow_sessions(entry_id)")

    # --- Commit and verify ---
    conn.commit()

    # Verification
    print("\n--- Verification ---")
    total = conn.execute("SELECT count(*) FROM entries").fetchone()[0]
    print(f"  Total entries: {total}")

    sample = conn.execute("SELECT id FROM entries LIMIT 3").fetchall()
    print(f"  Sample IDs: {[r['id'] for r in sample]}")

    cats = conn.execute("SELECT category, count(*) as cnt FROM entries GROUP BY category ORDER BY cnt DESC").fetchall()
    for r in cats:
        print(f"    {r['category']}: {r['cnt']}")

    # Check FK integrity
    orphan_ev = conn.execute("SELECT count(*) FROM entry_evidence WHERE entry_id NOT IN (SELECT id FROM entries)").fetchone()[0]
    orphan_deps = conn.execute("SELECT count(*) FROM entry_dependencies WHERE entry_id NOT IN (SELECT id FROM entries)").fetchone()[0]
    orphan_ve = conn.execute("SELECT count(*) FROM verse_evidence WHERE entry_id NOT IN (SELECT id FROM entries)").fetchone()[0]
    orphan_ws = conn.execute("SELECT count(*) FROM workflow_sessions WHERE entry_id NOT IN (SELECT id FROM entries)").fetchone()[0]
    print(f"  Orphan entry_evidence: {orphan_ev}")
    print(f"  Orphan entry_dependencies: {orphan_deps}")
    print(f"  Orphan verse_evidence: {orphan_ve}")
    print(f"  Orphan workflow_sessions: {orphan_ws}")

    conn.execute("VACUUM")
    conn.close()
    print("\nMigration complete!")


if __name__ == "__main__":
    run_migration()
