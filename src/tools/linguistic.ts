import { getDatabase, Verse, Pattern } from '../db.js';
import { randomUUID } from 'crypto';
import { writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Helper to transform sql.js results to typed objects
function rowsToObjects<T>(columns: string[], values: any[][]): T[] {
  return values.map(row => {
    const obj: any = {};
    columns.forEach((col, idx) => {
      obj[col] = row[idx];
    });
    return obj as T;
  });
}

// Helper to persist database changes to disk
function saveDatabase(db: any): void {
  const dbPath = process.env.KALIMA_DB_PATH || join(__dirname, '../../../../data/database/kalima.db');
  const data = db.export();
  const buffer = Buffer.from(data);
  writeFileSync(dbPath, buffer);
}

// Map user-friendly names to database codes
function normalizeLinguisticFeature(key: string, value: string): string {
  const mappings: Record<string, Record<string, string>> = {
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

// Segment interface based on database schema
interface Segment {
  id: string;
  token_id: string;
  type: string;
  form: string;
  root: string | null;
  lemma: string | null;
  pattern: string | null;
  pos: string | null;
  verb_form: string | null;
  voice: string | null;
  mood: string | null;
  aspect: string | null;
  person: string | null;
  number: string | null;
  gender: string | null;
  case_value: string | null;
  dependency_rel: string | null;
  role: string | null;
  derived_noun_type: string | null;
  state: string | null;
}

// Token interface
interface Token {
  id: string;
  verse_surah: number;
  verse_ayah: number;
  token_index: number;
  text: string;
}

// Verse with linguistic features
export interface VerseWithLinguistics extends Verse {
  segments: Segment[];
  tokens: Token[];
}

/**
 * Search verses by linguistic features (POS, verb form, mood, aspect, etc.)
 *
 * Examples:
 * - Find present tense verbs: { pos: "VERB", aspect: "imperfective" }
 * - Find imperatives: { pos: "VERB", mood: "imperative" }
 * - Find specific root: { root: "ق-و-ل" }
 */
export async function searchByLinguisticFeatures(options: {
  pos?: string;              // Part of speech: VERB, NOUN, ADJ, PRON, etc.
  aspect?: string;            // imperfective (present), perfective (past)
  mood?: string;              // indicative, subjunctive, imperative, jussive
  verb_form?: string;         // Verb conjugation form
  voice?: string;             // active, passive
  person?: string;            // 1st, 2nd, 3rd
  number?: string;            // singular, dual, plural
  gender?: string;            // masculine, feminine
  root?: string;              // Arabic root (e.g., "ق-و-ل")
  lemma?: string;             // Base form
  case_value?: string;        // nominative, accusative, genitive
  dependency_rel?: string;    // Syntactic dependency relation
  role?: string;              // Grammatical role
  surah?: number;             // Limit to specific surah
  limit?: number;             // Max results (default: 50)
}): Promise<VerseWithLinguistics[]> {
  const db = await getDatabase();
  const { limit = 50, surah, ...linguisticFeatures } = options;

  // Build WHERE clause dynamically
  let whereConditions: string[] = [];
  let params: any[] = [];

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

  const verses = rowsToObjects<Verse>(result[0].columns, result[0].values);

  // For each verse, fetch all segments and tokens
  const versesWithLinguistics: VerseWithLinguistics[] = [];

  for (const verse of verses) {
    // Get all tokens for this verse
    const tokensResult = db.exec(
      'SELECT * FROM tokens WHERE verse_surah = ? AND verse_ayah = ? ORDER BY token_index ASC',
      [verse.surah_number, verse.ayah_number]
    );

    const tokens = tokensResult.length && tokensResult[0].values.length
      ? rowsToObjects<Token>(tokensResult[0].columns, tokensResult[0].values)
      : [];

    // Get all segments for this verse
    const segmentsResult = db.exec(
      `SELECT s.* FROM segments s
       JOIN tokens t ON s.token_id = t.id
       WHERE t.verse_surah = ? AND t.verse_ayah = ?
       ORDER BY t.token_index ASC`,
      [verse.surah_number, verse.ayah_number]
    );

    const segments = segmentsResult.length && segmentsResult[0].values.length
      ? rowsToObjects<Segment>(segmentsResult[0].columns, segmentsResult[0].values)
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
export async function createPatternInterpretation(data: {
  description: string;
  pattern_type: 'morphological' | 'syntactic' | 'semantic';
  interpretation: string;
  linguistic_features?: object;
  scope?: string;
  phase?: 'question' | 'hypothesis' | 'validation' | 'verification';
}): Promise<{ success: boolean; pattern_id: string; claim_id: string; message: string }> {
  const db = await getDatabase();
  const {
    description,
    pattern_type,
    interpretation,
    linguistic_features,
    scope = 'all_verses',
    phase = 'hypothesis'
  } = data;

  try {
    const pattern_id = `pattern-${randomUUID()}`;
    const now = new Date().toISOString();

    // Insert the pattern
    db.run(
      'INSERT INTO patterns (id, description, pattern_type, scope, phase, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
      [pattern_id, description, pattern_type, scope, phase, now, now]
    );

    // Create a linked claim with the interpretation
    const claim_id = `claim-${randomUUID()}`;
    const claim_content = `${description}\n\nInterpretation: ${interpretation}${
      linguistic_features ? `\n\nLinguistic features: ${JSON.stringify(linguistic_features)}` : ''
    }`;

    db.run(
      'INSERT INTO claims (id, content, phase, pattern_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
      [claim_id, claim_content, phase, pattern_id, now, now]
    );

    // Persist changes to disk
    saveDatabase(db);

    return {
      success: true,
      pattern_id,
      claim_id,
      message: `Pattern created successfully with ID: ${pattern_id}\nLinked claim: ${claim_id}`
    };

  } catch (error) {
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
export async function createSurahTheme(data: {
  surah: number;
  theme: string;
  description?: string;
  phase?: 'question' | 'hypothesis' | 'validation' | 'verification';
}): Promise<{ success: boolean; claim_id: string; message: string }> {
  const db = await getDatabase();
  const { surah, theme, description, phase = 'hypothesis' } = data;

  try {
    // Get surah name
    const surahResult = db.exec('SELECT name FROM surahs WHERE number = ?', [surah]);
    const surahName = surahResult.length && surahResult[0].values.length
      ? surahResult[0].values[0][0]
      : `Surah ${surah}`;

    const claim_id = `claim-${randomUUID()}`;
    const now = new Date().toISOString();

    const claim_content = `Surah ${surah} (${surahName}) - Theme: ${theme}${
      description ? `\n\nDescription: ${description}` : ''
    }`;

    // Insert the claim
    db.run(
      'INSERT INTO claims (id, content, phase, pattern_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
      [claim_id, claim_content, phase, null, now, now]
    );

    // Persist changes to disk
    saveDatabase(db);

    return {
      success: true,
      claim_id,
      message: `Surah theme created successfully for ${surahName}\nClaim ID: ${claim_id}\nPhase: ${phase}`
    };

  } catch (error) {
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
export async function addVerseEvidence(data: {
  claim_id: string;
  surah: number;
  ayah: number;
  verification: 'supports' | 'contradicts' | 'unclear';
  notes?: string;
}): Promise<{ success: boolean; evidence_id: string; message: string }> {
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
    const verseCheck = db.exec(
      'SELECT * FROM verse_texts WHERE surah_number = ? AND ayah_number = ?',
      [surah, ayah]
    );
    if (!verseCheck.length || !verseCheck[0].values.length) {
      return {
        success: false,
        evidence_id: '',
        message: `Verse ${surah}:${ayah} not found`
      };
    }

    const evidence_id = `evidence-${randomUUID()}`;
    const now = new Date().toISOString();

    // Create notes with verification status
    const evidenceNotes = `[${verification.toUpperCase()}] ${notes || ''}`.trim();

    // Insert evidence
    db.run(
      'INSERT INTO claim_evidence (id, claim_id, surah, ayah, notes, created_at) VALUES (?, ?, ?, ?, ?, ?)',
      [evidence_id, claim_id, surah, ayah, evidenceNotes, now]
    );

    // Persist changes to disk
    saveDatabase(db);

    return {
      success: true,
      evidence_id,
      message: `Evidence added: Verse ${surah}:${ayah} ${verification} claim ${claim_id}`
    };

  } catch (error) {
    return {
      success: false,
      evidence_id: '',
      message: `Failed to add evidence: ${error}`
    };
  }
}
