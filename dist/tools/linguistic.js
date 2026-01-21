import { getDatabase } from '../db.js';
import { generatePatternId, generateClaimId, generateEvidenceId } from '../utils/shortId.js';
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
// Map user-friendly names to database codes
function normalizeLinguisticFeature(key, value) {
    const mappings = {
        pos: {
            'verb': 'V',
            'noun': 'N',
            'adjective': 'ADJ',
            'pronoun': 'PRON',
            'preposition': 'P',
            'particle': 'T'
        },
        aspect: {
            'imperfective': 'IMPF',
            'present': 'IMPF',
            'perfective': 'PERF',
            'past': 'PERF',
            'imperative': 'IMPV'
        },
        mood: {
            'jussive': 'MOOD:JUS',
            'subjunctive': 'MOOD:SUBJ'
        }
    };
    // Normalize to lowercase for lookup
    const lowerValue = value.toLowerCase();
    // Return mapped value if mapping exists, otherwise return original value unchanged
    return mappings[key]?.[lowerValue] || value;
}
/**
 * Search verses by linguistic features (POS, verb form, mood, aspect, etc.)
 *
 * Examples:
 * - Find present tense verbs: { pos: "VERB", aspect: "imperfective" }
 * - Find imperatives: { pos: "VERB", mood: "imperative" }
 * - Find specific root: { root: "ق-و-ل" }
 */
export async function searchByLinguisticFeatures(options) {
    const db = await getDatabase();
    const { limit = 50, surah, ...linguisticFeatures } = options;
    // Build WHERE clause dynamically
    let whereConditions = [];
    let params = [];
    for (const [key, value] of Object.entries(linguisticFeatures)) {
        if (value !== undefined && value !== null) {
            // Normalize user-friendly names to database codes
            const normalizedValue = normalizeLinguisticFeature(key, String(value));
            whereConditions.push(`s.${key} = ?`);
            params.push(normalizedValue);
        }
    }
    if (surah !== undefined) {
        whereConditions.push('t.verse_surah = ?');
        params.push(surah);
    }
    if (whereConditions.length === 0) {
        throw new Error('At least one linguistic feature must be specified');
    }
    const whereClause = whereConditions.join(' AND ');
    // Query segments matching linguistic features
    const query = `
    SELECT DISTINCT
      t.verse_surah AS surah_number,
      t.verse_ayah AS ayah_number,
      vt.text
    FROM segments s
    JOIN tokens t ON s.token_id = t.id
    JOIN verse_texts vt ON t.verse_surah = vt.surah_number AND t.verse_ayah = vt.ayah_number
    WHERE ${whereClause}
    ORDER BY t.verse_surah ASC, t.verse_ayah ASC
    LIMIT ?
  `;
    params.push(limit);
    const result = db.exec(query, params);
    if (!result.length || !result[0].values.length) {
        return [];
    }
    const verses = rowsToObjects(result[0].columns, result[0].values);
    // For each verse, fetch all segments and tokens
    const versesWithLinguistics = [];
    for (const verse of verses) {
        // Get all tokens for this verse
        const tokensResult = db.exec('SELECT * FROM tokens WHERE verse_surah = ? AND verse_ayah = ? ORDER BY token_index ASC', [verse.surah_number, verse.ayah_number]);
        const tokens = tokensResult.length && tokensResult[0].values.length
            ? rowsToObjects(tokensResult[0].columns, tokensResult[0].values)
            : [];
        // Get all segments for this verse
        const segmentsResult = db.exec(`SELECT s.* FROM segments s
       JOIN tokens t ON s.token_id = t.id
       WHERE t.verse_surah = ? AND t.verse_ayah = ?
       ORDER BY t.token_index ASC`, [verse.surah_number, verse.ayah_number]);
        const segments = segmentsResult.length && segmentsResult[0].values.length
            ? rowsToObjects(segmentsResult[0].columns, segmentsResult[0].values)
            : [];
        versesWithLinguistics.push({
            ...verse,
            tokens,
            segments
        });
    }
    return versesWithLinguistics;
}
/**
 * Create a linguistic pattern with interpretation
 *
 * Example: "Present tense verbs in the Quran indicate ongoing or future actions"
 */
export async function createPatternInterpretation(data) {
    const db = await getDatabase();
    const { description, pattern_type, interpretation, linguistic_features, scope = 'all_verses', phase = 'hypothesis' } = data;
    try {
        const pattern_id = generatePatternId(db);
        const now = new Date().toISOString();
        // Insert the pattern
        db.run('INSERT INTO patterns (id, description, pattern_type, scope, phase, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)', [pattern_id, description, pattern_type, scope, phase, now, now]);
        // Create a linked claim with the interpretation
        const claim_id = generateClaimId(db);
        const claim_content = `${description}\n\nInterpretation: ${interpretation}${linguistic_features ? `\n\nLinguistic features: ${JSON.stringify(linguistic_features)}` : ''}`;
        db.run('INSERT INTO claims (id, content, phase, pattern_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)', [claim_id, claim_content, phase, pattern_id, now, now]);
        // Persist changes to disk
        saveDatabase(db);
        return {
            success: true,
            pattern_id,
            claim_id,
            message: `Pattern created successfully with ID: ${pattern_id}\nLinked claim: ${claim_id}`
        };
    }
    catch (error) {
        return {
            success: false,
            pattern_id: '',
            claim_id: '',
            message: `Failed to create pattern: ${error}`
        };
    }
}
/**
 * Create a surah-level thematic interpretation
 *
 * Example: "Surah Al-Baqarah's theme is guidance for believers"
 */
export async function createSurahTheme(data) {
    const db = await getDatabase();
    const { surah, theme, description, phase = 'hypothesis' } = data;
    try {
        // Get surah name
        const surahResult = db.exec('SELECT name FROM surahs WHERE number = ?', [surah]);
        const surahName = surahResult.length && surahResult[0].values.length
            ? surahResult[0].values[0][0]
            : `Surah ${surah}`;
        const claim_id = generateClaimId(db);
        const now = new Date().toISOString();
        const claim_content = `Surah ${surah} (${surahName}) - Theme: ${theme}${description ? `\n\nDescription: ${description}` : ''}`;
        // Insert the claim
        db.run('INSERT INTO claims (id, content, phase, pattern_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)', [claim_id, claim_content, phase, null, now, now]);
        // Persist changes to disk
        saveDatabase(db);
        return {
            success: true,
            claim_id,
            message: `Surah theme created successfully for ${surahName}\nClaim ID: ${claim_id}\nPhase: ${phase}`
        };
    }
    catch (error) {
        return {
            success: false,
            claim_id: '',
            message: `Failed to create surah theme: ${error}`
        };
    }
}
/**
 * Add a verse as evidence for a claim with verification status
 *
 * Example: Mark verse 2:7 as supporting the present tense verb pattern
 */
export async function addVerseEvidence(data) {
    const db = await getDatabase();
    const { claim_id, surah, ayah, verification, notes } = data;
    try {
        // Check if claim exists
        const claimCheck = db.exec('SELECT id FROM claims WHERE id = ?', [claim_id]);
        if (!claimCheck.length || !claimCheck[0].values.length) {
            return {
                success: false,
                evidence_id: '',
                message: `Claim ${claim_id} not found`
            };
        }
        // Check if verse exists
        const verseCheck = db.exec('SELECT * FROM verse_texts WHERE surah_number = ? AND ayah_number = ?', [surah, ayah]);
        if (!verseCheck.length || !verseCheck[0].values.length) {
            return {
                success: false,
                evidence_id: '',
                message: `Verse ${surah}:${ayah} not found`
            };
        }
        const evidence_id = generateEvidenceId(db);
        const now = new Date().toISOString();
        // Create notes with verification status
        const evidenceNotes = `[${verification.toUpperCase()}] ${notes || ''}`.trim();
        // Insert evidence
        db.run('INSERT INTO claim_evidence (id, claim_id, surah, ayah, notes, created_at) VALUES (?, ?, ?, ?, ?, ?)', [evidence_id, claim_id, surah, ayah, evidenceNotes, now]);
        // Persist changes to disk
        saveDatabase(db);
        return {
            success: true,
            evidence_id,
            message: `Evidence added: Verse ${surah}:${ayah} ${verification} claim ${claim_id}`
        };
    }
    catch (error) {
        return {
            success: false,
            evidence_id: '',
            message: `Failed to add evidence: ${error}`
        };
    }
}
//# sourceMappingURL=linguistic.js.map