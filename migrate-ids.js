// Migration script to convert UUID-based IDs to sequential IDs
import initSqlJs from 'sql.js';
import { readFileSync, writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function migrateIds() {
  console.log('Starting ID migration...\n');

  // Load the database
  const SQL = await initSqlJs();
  const dbPath = process.env.KALIMA_DB_PATH || join(__dirname, 'data/database/kalima.db');
  const buffer = readFileSync(dbPath);
  const db = new SQL.Database(buffer);

  // Create a mapping of old UUID IDs to new sequential IDs
  const idMappings = {
    claims: new Map(),
    patterns: new Map(),
    sessions: new Map(),
    evidence: new Map()
  };

  try {
    // 1. Migrate claims
    console.log('Migrating claims...');
    const claimsResult = db.exec('SELECT id FROM claims ORDER BY created_at ASC');
    if (claimsResult.length > 0 && claimsResult[0].values.length > 0) {
      let claimCounter = 1;
      for (const row of claimsResult[0].values) {
        const oldId = row[0];
        const newId = `claim_${claimCounter}`;
        idMappings.claims.set(oldId, newId);
        claimCounter++;
      }
      console.log(`  Mapped ${idMappings.claims.size} claims`);
    }

    // 2. Migrate patterns
    console.log('Migrating patterns...');
    const patternsResult = db.exec('SELECT id FROM patterns ORDER BY created_at ASC');
    if (patternsResult.length > 0 && patternsResult[0].values.length > 0) {
      let patternCounter = 1;
      for (const row of patternsResult[0].values) {
        const oldId = row[0];
        const newId = `pattern_${patternCounter}`;
        idMappings.patterns.set(oldId, newId);
        patternCounter++;
      }
      console.log(`  Mapped ${idMappings.patterns.size} patterns`);
    }

    // 3. Migrate workflow sessions
    console.log('Migrating workflow sessions...');
    const sessionsResult = db.exec('SELECT session_id FROM workflow_sessions ORDER BY created_at ASC');
    if (sessionsResult.length > 0 && sessionsResult[0].values.length > 0) {
      let sessionCounter = 1;
      for (const row of sessionsResult[0].values) {
        const oldId = row[0];
        const newId = `session_${sessionCounter}`;
        idMappings.sessions.set(oldId, newId);
        sessionCounter++;
      }
      console.log(`  Mapped ${idMappings.sessions.size} sessions`);
    }

    // 4. Migrate evidence (both claim_evidence and verse_evidence)
    console.log('Migrating evidence...');
    const evidenceResult = db.exec('SELECT id FROM claim_evidence ORDER BY created_at ASC');
    if (evidenceResult.length > 0 && evidenceResult[0].values.length > 0) {
      let evidenceCounter = 1;
      for (const row of evidenceResult[0].values) {
        const oldId = row[0];
        const newId = `evidence_${evidenceCounter}`;
        idMappings.evidence.set(oldId, newId);
        evidenceCounter++;
      }
      console.log(`  Mapped ${idMappings.evidence.size} claim evidence records`);
    }

    // Check for verse_evidence table
    const verseEvidenceExists = db.exec("SELECT name FROM sqlite_master WHERE type='table' AND name='verse_evidence'");
    if (verseEvidenceExists.length > 0) {
      const verseEvidenceResult = db.exec('SELECT id FROM verse_evidence ORDER BY verified_at ASC');
      if (verseEvidenceResult.length > 0 && verseEvidenceResult[0].values.length > 0) {
        let evidenceCounter = idMappings.evidence.size + 1;
        for (const row of verseEvidenceResult[0].values) {
          const oldId = row[0];
          const newId = `evidence_${evidenceCounter}`;
          idMappings.evidence.set(oldId, newId);
          evidenceCounter++;
        }
        console.log(`  Mapped ${verseEvidenceResult[0].values.length} verse evidence records`);
      }
    }

    // Now apply the mappings
    console.log('\nApplying ID updates...\n');

    // Update claims table
    console.log('Updating claims table...');
    for (const [oldId, newId] of idMappings.claims) {
      db.run('UPDATE claims SET id = ? WHERE id = ?', [newId, oldId]);
    }
    console.log(`  Updated ${idMappings.claims.size} claims`);

    // Update patterns table
    console.log('Updating patterns table...');
    for (const [oldId, newId] of idMappings.patterns) {
      db.run('UPDATE patterns SET id = ? WHERE id = ?', [newId, oldId]);
    }
    console.log(`  Updated ${idMappings.patterns.size} patterns`);

    // Update workflow_sessions table
    console.log('Updating workflow_sessions table...');
    for (const [oldId, newId] of idMappings.sessions) {
      db.run('UPDATE workflow_sessions SET session_id = ? WHERE session_id = ?', [newId, oldId]);
    }
    console.log(`  Updated ${idMappings.sessions.size} sessions`);

    // Update claim_evidence table
    console.log('Updating claim_evidence table...');
    for (const [oldId, newId] of idMappings.evidence) {
      db.run('UPDATE claim_evidence SET id = ? WHERE id = ?', [newId, oldId]);
    }
    // Update foreign key references in claim_evidence
    for (const [oldId, newId] of idMappings.claims) {
      db.run('UPDATE claim_evidence SET claim_id = ? WHERE claim_id = ?', [newId, oldId]);
    }
    console.log(`  Updated claim_evidence records`);

    // Update verse_evidence table if it exists
    if (verseEvidenceExists.length > 0) {
      console.log('Updating verse_evidence table...');
      for (const [oldId, newId] of idMappings.evidence) {
        db.run('UPDATE verse_evidence SET id = ? WHERE id = ?', [newId, oldId]);
      }
      // Update foreign key references in verse_evidence
      for (const [oldId, newId] of idMappings.claims) {
        db.run('UPDATE verse_evidence SET claim_id = ? WHERE claim_id = ?', [newId, oldId]);
      }
      console.log(`  Updated verse_evidence records`);
    }

    // Update pattern_id foreign keys in claims table
    console.log('Updating pattern_id foreign keys in claims...');
    for (const [oldId, newId] of idMappings.patterns) {
      db.run('UPDATE claims SET pattern_id = ? WHERE pattern_id = ?', [newId, oldId]);
    }

    // Update claim_id foreign keys in workflow_sessions table
    console.log('Updating claim_id foreign keys in workflow_sessions...');
    for (const [oldId, newId] of idMappings.claims) {
      db.run('UPDATE workflow_sessions SET claim_id = ? WHERE claim_id = ?', [newId, oldId]);
    }

    // Update claim_dependencies table if it exists
    const depsExists = db.exec("SELECT name FROM sqlite_master WHERE type='table' AND name='claim_dependencies'");
    if (depsExists.length > 0) {
      console.log('Updating claim_dependencies table...');
      for (const [oldId, newId] of idMappings.claims) {
        db.run('UPDATE claim_dependencies SET claim_id = ? WHERE claim_id = ?', [newId, oldId]);
        db.run('UPDATE claim_dependencies SET depends_on_claim_id = ? WHERE depends_on_claim_id = ?', [newId, oldId]);
      }
      console.log(`  Updated claim_dependencies records`);
    }

    // Save the database
    console.log('\nSaving database...');
    const data = db.export();
    const outputBuffer = Buffer.from(data);
    writeFileSync(dbPath, outputBuffer);
    console.log('Database saved successfully!');

    console.log('\n✅ Migration completed!');
    console.log(`\nSummary:`);
    console.log(`  - Claims: ${idMappings.claims.size} migrated`);
    console.log(`  - Patterns: ${idMappings.patterns.size} migrated`);
    console.log(`  - Sessions: ${idMappings.sessions.size} migrated`);
    console.log(`  - Evidence: ${idMappings.evidence.size} migrated`);

  } catch (error) {
    console.error('❌ Migration failed:', error);
    process.exit(1);
  } finally {
    db.close();
  }
}

migrateIds().catch(console.error);
