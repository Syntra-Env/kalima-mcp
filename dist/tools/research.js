import { getDatabase } from '../db.js';
import { randomUUID } from 'crypto';
import { writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
// Helper to transform sql.js results to typed objects
function rowsToObjects(columns, values) {
    return values.map(row => {
        const obj = {};
        columns.forEach((col, idx) => {
            obj[col] = row[idx];
        });
        return obj;
    });
}
// Helper to persist database changes to disk
function saveDatabase(db) {
    const dbPath = process.env.KALIMA_DB_PATH || join(__dirname, '../../../../data/database/kalima.db');
    const data = db.export();
    const buffer = Buffer.from(data);
    writeFileSync(dbPath, buffer);
}
export async function searchClaims(options) {
    const db = await getDatabase();
    const { phase, pattern_id, limit = 50 } = options;
    let query = 'SELECT * FROM claims WHERE 1=1';
    const params = [];
    if (phase) {
        query += ' AND phase = ?';
        params.push(phase);
    }
    if (pattern_id) {
        query += ' AND pattern_id = ?';
        params.push(pattern_id);
    }
    query += ' ORDER BY updated_at DESC LIMIT ?';
    params.push(limit);
    const result = db.exec(query, params);
    if (!result.length || !result[0].values.length) {
        return [];
    }
    return rowsToObjects(result[0].columns, result[0].values);
}
export async function getClaimEvidence(claim_id) {
    const db = await getDatabase();
    const result = db.exec('SELECT * FROM claim_evidence WHERE claim_id = ? ORDER BY created_at DESC', [claim_id]);
    if (!result.length || !result[0].values.length) {
        return [];
    }
    return rowsToObjects(result[0].columns, result[0].values);
}
export async function getClaimDependencies(claim_id) {
    const db = await getDatabase();
    // Get the main claim
    const claimResult = db.exec('SELECT * FROM claims WHERE id = ?', [claim_id]);
    if (!claimResult.length || !claimResult[0].values.length) {
        return { claim: null, dependencies: [] };
    }
    const claims = rowsToObjects(claimResult[0].columns, claimResult[0].values);
    const claim = claims[0];
    // Get dependencies with joined claim data
    const depsResult = db.exec(`SELECT
      c.id, c.content, c.phase, c.pattern_id, c.note_file, c.created_at, c.updated_at,
      cd.dependency_type as dep_type
    FROM claim_dependencies cd
    JOIN claims c ON c.id = cd.depends_on_claim_id
    WHERE cd.claim_id = ?`, [claim_id]);
    if (!depsResult.length || !depsResult[0].values.length) {
        return { claim, dependencies: [] };
    }
    const rawDeps = rowsToObjects(depsResult[0].columns, depsResult[0].values);
    const dependencies = rawDeps.map(dep => ({
        claim: {
            id: dep.id,
            content: dep.content,
            phase: dep.phase,
            pattern_id: dep.pattern_id,
            note_file: dep.note_file,
            created_at: dep.created_at,
            updated_at: dep.updated_at
        },
        type: dep.dep_type
    }));
    return { claim, dependencies };
}
export async function listPatterns(pattern_type) {
    const db = await getDatabase();
    let query = 'SELECT * FROM patterns WHERE 1=1';
    const params = [];
    if (pattern_type) {
        query += ' AND pattern_type = ?';
        params.push(pattern_type);
    }
    query += ' ORDER BY created_at DESC';
    const result = db.exec(query, params);
    if (!result.length || !result[0].values.length) {
        return [];
    }
    return rowsToObjects(result[0].columns, result[0].values);
}
export async function saveInsight(data) {
    const db = await getDatabase();
    const { content, phase = 'question', pattern_id, evidence_verses = [] } = data;
    try {
        const claim_id = `claim-${randomUUID()}`;
        const now = new Date().toISOString();
        // Insert the claim
        db.run('INSERT INTO claims (id, content, phase, pattern_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)', [claim_id, content, phase, pattern_id || null, now, now]);
        // Insert evidence verses
        for (const evidence of evidence_verses) {
            const evidence_id = `evidence-${randomUUID()}`;
            db.run('INSERT INTO claim_evidence (id, claim_id, surah, ayah, notes, created_at) VALUES (?, ?, ?, ?, ?, ?)', [evidence_id, claim_id, evidence.surah, evidence.ayah, evidence.notes || null, now]);
        }
        // Persist changes to disk
        saveDatabase(db);
        return {
            success: true,
            claim_id,
            message: `Insight saved successfully with ${evidence_verses.length} evidence verse(s)`
        };
    }
    catch (error) {
        return {
            success: false,
            claim_id: '',
            message: `Failed to save insight: ${error}`
        };
    }
}
export async function updateClaimPhase(claim_id, new_phase) {
    const db = await getDatabase();
    try {
        const now = new Date().toISOString();
        // Check if claim exists first
        const checkResult = db.exec('SELECT id FROM claims WHERE id = ?', [claim_id]);
        if (!checkResult.length || !checkResult[0].values.length) {
            return false;
        }
        // Update the claim
        db.run('UPDATE claims SET phase = ?, updated_at = ? WHERE id = ?', [new_phase, now, claim_id]);
        // Persist changes to disk
        saveDatabase(db);
        return true;
    }
    catch (error) {
        return false;
    }
}
//# sourceMappingURL=research.js.map