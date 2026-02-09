import { getDatabase, saveDatabase } from '../db.js';
import { generateClaimId, generateEvidenceId } from '../utils/shortId.js';
import { rowsToObjects } from '../utils/dbHelpers.js';
export async function searchClaims(options) {
    const db = await getDatabase();
    const { phase, pattern_id, query: searchQuery, limit = 50 } = options;
    let sql = 'SELECT * FROM claims WHERE 1=1';
    const params = [];
    if (searchQuery) {
        sql += ' AND lower(content) LIKE ?';
        params.push(`%${searchQuery.toLowerCase()}%`);
    }
    if (phase) {
        sql += ' AND phase = ?';
        params.push(phase);
    }
    if (pattern_id) {
        sql += ' AND pattern_id = ?';
        params.push(pattern_id);
    }
    sql += ' ORDER BY updated_at DESC LIMIT ?';
    params.push(limit);
    const result = db.exec(sql, params);
    if (!result.length || !result[0].values.length) {
        return [];
    }
    return rowsToObjects(result[0].columns, result[0].values);
}
export async function getClaimStats() {
    const db = await getDatabase();
    const totalResult = db.exec('SELECT count(*) FROM claims');
    const total_claims = totalResult[0]?.values[0]?.[0] ?? 0;
    const phaseResult = db.exec('SELECT phase, count(*) FROM claims GROUP BY phase ORDER BY count(*) DESC');
    const by_phase = {};
    if (phaseResult.length > 0) {
        for (const row of phaseResult[0].values) {
            by_phase[row[0]] = row[1];
        }
    }
    const patternResult = db.exec('SELECT count(*) FROM patterns');
    const total_patterns = patternResult[0]?.values[0]?.[0] ?? 0;
    const evidenceResult = db.exec('SELECT count(*) FROM claim_evidence');
    const total_evidence = evidenceResult[0]?.values[0]?.[0] ?? 0;
    const rangeResult = db.exec("SELECT min(id), max(id) FROM claims WHERE id LIKE 'claim_%'");
    const id_range = {
        min: rangeResult[0]?.values[0]?.[0] ?? '',
        max: rangeResult[0]?.values[0]?.[1] ?? ''
    };
    return { total_claims, by_phase, total_patterns, total_evidence, id_range };
}
export async function saveBulkInsights(data) {
    const db = await getDatabase();
    const { claims } = data;
    try {
        const claim_ids = [];
        const now = new Date().toISOString();
        for (const claim of claims) {
            const claim_id = generateClaimId(db);
            db.run('INSERT INTO claims (id, content, phase, pattern_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)', [claim_id, claim.content, claim.phase || 'question', claim.pattern_id || null, now, now]);
            claim_ids.push(claim_id);
        }
        saveDatabase(db);
        return {
            success: true,
            claim_ids,
            message: `Saved ${claim_ids.length} claims (${claim_ids[0]} through ${claim_ids[claim_ids.length - 1]})`
        };
    }
    catch (error) {
        return {
            success: false,
            claim_ids: [],
            message: `Failed to save bulk insights: ${error}`
        };
    }
}
export async function updateClaim(data) {
    const db = await getDatabase();
    const { claim_id, content, phase, pattern_id } = data;
    try {
        const checkResult = db.exec('SELECT id FROM claims WHERE id = ?', [claim_id]);
        if (!checkResult.length || !checkResult[0].values.length) {
            return { success: false, message: `Claim ${claim_id} not found` };
        }
        const now = new Date().toISOString();
        const updates = ['updated_at = ?'];
        const params = [now];
        if (content !== undefined) {
            updates.push('content = ?');
            params.push(content);
        }
        if (phase !== undefined) {
            updates.push('phase = ?');
            params.push(phase);
        }
        if (pattern_id !== undefined) {
            updates.push('pattern_id = ?');
            params.push(pattern_id);
        }
        params.push(claim_id);
        db.run(`UPDATE claims SET ${updates.join(', ')} WHERE id = ?`, params);
        saveDatabase(db);
        return { success: true, message: `Claim ${claim_id} updated successfully` };
    }
    catch (error) {
        return { success: false, message: `Failed to update claim: ${error}` };
    }
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
        const claim_id = generateClaimId(db);
        const now = new Date().toISOString();
        // Insert the claim
        db.run('INSERT INTO claims (id, content, phase, pattern_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)', [claim_id, content, phase, pattern_id || null, now, now]);
        // Insert evidence verses
        for (const evidence of evidence_verses) {
            const evidence_id = generateEvidenceId(db);
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
export async function getClaim(claim_id) {
    const db = await getDatabase();
    const result = db.exec('SELECT * FROM claims WHERE id = ?', [claim_id]);
    if (!result.length || !result[0].values.length)
        return null;
    return rowsToObjects(result[0].columns, result[0].values)[0];
}
export async function deleteClaim(claim_id) {
    const db = await getDatabase();
    try {
        // Check if claim exists first
        const checkResult = db.exec('SELECT id FROM claims WHERE id = ?', [claim_id]);
        if (!checkResult.length || !checkResult[0].values.length) {
            return { success: false, message: `Claim ${claim_id} not found` };
        }
        // Delete associated evidence first (foreign key constraint)
        db.run('DELETE FROM claim_evidence WHERE claim_id = ?', [claim_id]);
        // Delete associated dependencies
        db.run('DELETE FROM claim_dependencies WHERE claim_id = ? OR depends_on_claim_id = ?', [claim_id, claim_id]);
        // Delete the claim
        db.run('DELETE FROM claims WHERE id = ?', [claim_id]);
        // Persist changes to disk
        saveDatabase(db);
        return { success: true, message: `Claim ${claim_id} deleted successfully` };
    }
    catch (error) {
        return { success: false, message: `Failed to delete claim: ${error}` };
    }
}
export async function deleteMultipleClaims(claim_ids) {
    const db = await getDatabase();
    const failed = [];
    let deleted = 0;
    try {
        for (const claim_id of claim_ids) {
            // Check if claim exists
            const checkResult = db.exec('SELECT id FROM claims WHERE id = ?', [claim_id]);
            if (!checkResult.length || !checkResult[0].values.length) {
                failed.push(claim_id);
                continue;
            }
            // Delete associated evidence first
            db.run('DELETE FROM claim_evidence WHERE claim_id = ?', [claim_id]);
            // Delete associated dependencies
            db.run('DELETE FROM claim_dependencies WHERE claim_id = ? OR depends_on_claim_id = ?', [claim_id, claim_id]);
            // Delete the claim
            db.run('DELETE FROM claims WHERE id = ?', [claim_id]);
            deleted++;
        }
        // Persist changes to disk
        saveDatabase(db);
        return {
            success: true,
            deleted,
            failed,
            message: `Deleted ${deleted} claims. ${failed.length > 0 ? `Failed: ${failed.length}` : ''}`
        };
    }
    catch (error) {
        return { success: false, deleted, failed, message: `Failed during deletion: ${error}` };
    }
}
export async function getVerseClaims(surah, ayah) {
    const db = await getDatabase();
    const result = db.exec(`SELECT
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
    ORDER BY vc.created_at DESC`, [surah, ayah]);
    if (!result.length || !result[0].values.length) {
        return [];
    }
    return rowsToObjects(result[0].columns, result[0].values);
}
export async function findRelatedClaims(claim_id, limit = 20) {
    const db = await getDatabase();
    // Get the source claim
    const claimResult = db.exec('SELECT * FROM claims WHERE id = ?', [claim_id]);
    if (!claimResult.length || !claimResult[0].values.length) {
        return { claim: null, shared_evidence: [], same_pattern: [], same_surah_claims: [] };
    }
    const claim = rowsToObjects(claimResult[0].columns, claimResult[0].values)[0];
    // 1. Claims sharing exact verse evidence (via verse_claims view which unions claim_evidence + verse_evidence)
    const sharedResult = db.exec(`SELECT DISTINCT c.id, c.content, c.phase, c.pattern_id, c.note_file, c.created_at, c.updated_at,
            vc2.surah, vc2.ayah
     FROM verse_claims vc1
     JOIN verse_claims vc2 ON vc1.surah = vc2.surah AND vc1.ayah = vc2.ayah AND vc1.claim_id != vc2.claim_id
     JOIN claims c ON c.id = vc2.claim_id
     WHERE vc1.claim_id = ?
     ORDER BY c.updated_at DESC
     LIMIT ?`, [claim_id, limit]);
    const sharedMap = new Map();
    if (sharedResult.length && sharedResult[0].values.length) {
        for (const row of sharedResult[0].values) {
            const cols = sharedResult[0].columns;
            const id = row[cols.indexOf('id')];
            const surah = row[cols.indexOf('surah')];
            const ayah = row[cols.indexOf('ayah')];
            if (!sharedMap.has(id)) {
                sharedMap.set(id, {
                    claim: {
                        id,
                        content: row[cols.indexOf('content')],
                        phase: row[cols.indexOf('phase')],
                        pattern_id: row[cols.indexOf('pattern_id')],
                        note_file: row[cols.indexOf('note_file')],
                        created_at: row[cols.indexOf('created_at')],
                        updated_at: row[cols.indexOf('updated_at')],
                    },
                    shared_verses: []
                });
            }
            sharedMap.get(id).shared_verses.push({ surah, ayah });
        }
    }
    // 2. Claims in the same pattern
    let same_pattern = [];
    if (claim.pattern_id) {
        const patternResult = db.exec('SELECT * FROM claims WHERE pattern_id = ? AND id != ? ORDER BY updated_at DESC LIMIT ?', [claim.pattern_id, claim_id, limit]);
        if (patternResult.length && patternResult[0].values.length) {
            same_pattern = rowsToObjects(patternResult[0].columns, patternResult[0].values);
        }
    }
    // 3. Claims with evidence in the same surah (weaker signal)
    const surahResult = db.exec(`SELECT DISTINCT c.id, c.content, c.phase, c.pattern_id, c.note_file, c.created_at, c.updated_at,
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
     LIMIT ?`, [claim_id, claim_id, limit]);
    const surahMap = new Map();
    if (surahResult.length && surahResult[0].values.length) {
        for (const row of surahResult[0].values) {
            const cols = surahResult[0].columns;
            const id = row[cols.indexOf('id')];
            if (!surahMap.has(id)) {
                surahMap.set(id, {
                    claim: {
                        id,
                        content: row[cols.indexOf('content')],
                        phase: row[cols.indexOf('phase')],
                        pattern_id: row[cols.indexOf('pattern_id')],
                        note_file: row[cols.indexOf('note_file')],
                        created_at: row[cols.indexOf('created_at')],
                        updated_at: row[cols.indexOf('updated_at')],
                    },
                    surah: row[cols.indexOf('surah')]
                });
            }
        }
    }
    return {
        claim,
        shared_evidence: Array.from(sharedMap.values()),
        same_pattern,
        same_surah_claims: Array.from(surahMap.values())
    };
}
export async function addClaimDependency(data) {
    const db = await getDatabase();
    const { claim_id, depends_on_claim_id, dependency_type } = data;
    const validTypes = ['depends_on', 'supports', 'contradicts', 'refines', 'related'];
    if (!validTypes.includes(dependency_type)) {
        return { success: false, message: `Invalid dependency_type. Must be one of: ${validTypes.join(', ')}` };
    }
    if (claim_id === depends_on_claim_id) {
        return { success: false, message: 'A claim cannot depend on itself' };
    }
    try {
        // Validate both claims exist
        const check1 = db.exec('SELECT id FROM claims WHERE id = ?', [claim_id]);
        if (!check1.length || !check1[0].values.length) {
            return { success: false, message: `Claim ${claim_id} not found` };
        }
        const check2 = db.exec('SELECT id FROM claims WHERE id = ?', [depends_on_claim_id]);
        if (!check2.length || !check2[0].values.length) {
            return { success: false, message: `Claim ${depends_on_claim_id} not found` };
        }
        // Check for duplicate
        const dupCheck = db.exec('SELECT claim_id FROM claim_dependencies WHERE claim_id = ? AND depends_on_claim_id = ? AND dependency_type = ?', [claim_id, depends_on_claim_id, dependency_type]);
        if (dupCheck.length && dupCheck[0].values.length) {
            return { success: false, message: `Dependency already exists: ${claim_id} --${dependency_type}--> ${depends_on_claim_id}` };
        }
        const now = new Date().toISOString();
        db.run('INSERT INTO claim_dependencies (claim_id, depends_on_claim_id, dependency_type, created_at) VALUES (?, ?, ?, ?)', [claim_id, depends_on_claim_id, dependency_type, now]);
        saveDatabase(db);
        return { success: true, message: `Dependency created: ${claim_id} --${dependency_type}--> ${depends_on_claim_id}` };
    }
    catch (error) {
        return { success: false, message: `Failed to add dependency: ${error}` };
    }
}
export async function deletePattern(pattern_id) {
    const db = await getDatabase();
    try {
        const checkResult = db.exec('SELECT id FROM patterns WHERE id = ?', [pattern_id]);
        if (!checkResult.length || !checkResult[0].values.length) {
            return { success: false, message: `Pattern ${pattern_id} not found` };
        }
        // Unlink claims (set pattern_id to null, don't delete claims)
        db.run('UPDATE claims SET pattern_id = NULL WHERE pattern_id = ?', [pattern_id]);
        // Delete linguistic features
        db.run('DELETE FROM pattern_linguistic_features WHERE pattern_id = ?', [pattern_id]);
        // Delete the pattern
        db.run('DELETE FROM patterns WHERE id = ?', [pattern_id]);
        saveDatabase(db);
        return { success: true, message: `Pattern ${pattern_id} deleted. Associated claims preserved with pattern_id set to null.` };
    }
    catch (error) {
        return { success: false, message: `Failed to delete pattern: ${error}` };
    }
}
//# sourceMappingURL=research.js.map