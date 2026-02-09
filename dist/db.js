import initSqlJs from 'sql.js';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { readFileSync, writeFileSync } from 'fs';
import { normalizeArabic } from './utils/dbHelpers.js';
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
// Database connection
let SQL = null;
let db = null;
export async function getDatabase() {
    if (!db) {
        if (!SQL) {
            SQL = await initSqlJs();
        }
        const dbPath = process.env.KALIMA_DB_PATH || join(__dirname, '../../../data/database/kalima.db');
        const buffer = readFileSync(dbPath);
        const newDb = new SQL.Database(buffer);
        // Enable foreign key constraints
        newDb.exec('PRAGMA foreign_keys = ON;');
        // Initialize verse_claims view and indexes
        initializeVerseClaimsView(newDb);
        // Initialize pattern linguistic features table
        initializePatternLinguisticFeatures(newDb);
        // Initialize workflow tables (moved from workflow.ts)
        initializeWorkflowTables(newDb);
        // Initialize normalized search index for Arabic verse search
        initializeSearchIndex(newDb);
        db = newDb;
        return newDb;
    }
    return db;
}
function initializeVerseClaimsView(database) {
    // Create indexes on evidence tables for fast verse lookups
    database.exec(`
    CREATE INDEX IF NOT EXISTS idx_claim_evidence_verse
    ON claim_evidence(surah, ayah);
  `);
    database.exec(`
    CREATE INDEX IF NOT EXISTS idx_verse_evidence_verse
    ON verse_evidence(verse_surah, verse_ayah);
  `);
    // Drop view if it exists (to handle schema updates)
    database.exec(`DROP VIEW IF EXISTS verse_claims;`);
    // Create unified view of all verse-to-claim relationships
    database.exec(`
    CREATE VIEW verse_claims AS
    SELECT
      surah,
      ayah,
      claim_id,
      'claim_evidence' as evidence_type,
      notes,
      NULL as verification,
      created_at
    FROM claim_evidence
    UNION ALL
    SELECT
      verse_surah as surah,
      verse_ayah as ayah,
      claim_id,
      'verse_evidence' as evidence_type,
      notes,
      verification,
      verified_at as created_at
    FROM verse_evidence;
  `);
}
function initializePatternLinguisticFeatures(database) {
    // Create table for linking patterns/claims to linguistic features
    database.exec(`
    CREATE TABLE IF NOT EXISTS pattern_linguistic_features (
      id TEXT PRIMARY KEY,
      pattern_id TEXT,
      feature_type TEXT NOT NULL,
      feature_value TEXT NOT NULL,
      created_at TEXT NOT NULL,
      FOREIGN KEY (pattern_id) REFERENCES patterns(id) ON DELETE CASCADE
    );
  `);
    // Create indexes for fast lookups
    database.exec(`
    CREATE INDEX IF NOT EXISTS idx_pattern_ling_features_pattern
    ON pattern_linguistic_features(pattern_id);
  `);
    database.exec(`
    CREATE INDEX IF NOT EXISTS idx_pattern_ling_features_type_value
    ON pattern_linguistic_features(feature_type, feature_value);
  `);
}
function initializeWorkflowTables(database) {
    database.exec(`
    CREATE TABLE IF NOT EXISTS workflow_sessions (
      session_id TEXT PRIMARY KEY,
      claim_id TEXT NOT NULL,
      workflow_type TEXT NOT NULL,
      created_at TEXT NOT NULL,
      current_index INTEGER NOT NULL,
      total_verses INTEGER NOT NULL,
      status TEXT NOT NULL,
      linguistic_features TEXT,
      surah INTEGER,
      verses_json TEXT NOT NULL,
      FOREIGN KEY (claim_id) REFERENCES claims(id)
    )
  `);
    database.exec(`
    CREATE TABLE IF NOT EXISTS verse_evidence (
      id TEXT PRIMARY KEY,
      claim_id TEXT NOT NULL,
      verse_surah INTEGER NOT NULL,
      verse_ayah INTEGER NOT NULL,
      verification TEXT NOT NULL,
      notes TEXT,
      verified_at TEXT NOT NULL,
      FOREIGN KEY (claim_id) REFERENCES claims(id)
    )
  `);
}
function initializeSearchIndex(database) {
    // Add normalized_text column if it doesn't exist
    try {
        database.exec(`ALTER TABLE verse_texts ADD COLUMN normalized_text TEXT`);
    }
    catch (e) {
        // Column already exists, skip
    }
    // Check if normalized texts need to be populated
    const check = database.exec(`SELECT COUNT(*) FROM verse_texts WHERE normalized_text IS NULL`);
    const nullCount = check[0]?.values[0]?.[0];
    if (nullCount > 0) {
        // Populate normalized texts
        const allTexts = database.exec(`SELECT surah_number, ayah_number, text FROM verse_texts`);
        if (allTexts.length > 0) {
            for (const row of allTexts[0].values) {
                const normalized = normalizeArabic(row[2]);
                database.exec(`UPDATE verse_texts SET normalized_text = ? WHERE surah_number = ? AND ayah_number = ?`, [normalized, row[0], row[1]]);
            }
        }
        // Create index on normalized_text for fast LIKE queries
        database.exec(`CREATE INDEX IF NOT EXISTS idx_verse_texts_normalized ON verse_texts(normalized_text)`);
        // Persist the migration so it only runs once
        const dbPath = process.env.KALIMA_DB_PATH || join(__dirname, '../../../data/database/kalima.db');
        const data = database.export();
        const buffer = Buffer.from(data);
        writeFileSync(dbPath, buffer);
    }
}
/**
 * Save the in-memory database to disk
 * CRITICAL: Must be called after any write operations to persist changes
 */
export function saveDatabase(database) {
    const dbToSave = database || db;
    if (!dbToSave)
        return;
    const dbPath = process.env.KALIMA_DB_PATH || join(__dirname, '../../../data/database/kalima.db');
    const data = dbToSave.export();
    const buffer = Buffer.from(data);
    writeFileSync(dbPath, buffer);
}
export function closeDatabase() {
    if (db) {
        db.close();
        db = null;
    }
}
//# sourceMappingURL=db.js.map