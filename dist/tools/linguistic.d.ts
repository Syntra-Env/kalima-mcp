import { Verse } from '../db.js';
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
interface Token {
    id: string;
    verse_surah: number;
    verse_ayah: number;
    token_index: number;
    text: string;
}
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
export declare function searchByLinguisticFeatures(options: {
    pos?: string;
    aspect?: string;
    mood?: string;
    verb_form?: string;
    voice?: string;
    person?: string;
    number?: string;
    gender?: string;
    root?: string;
    lemma?: string;
    case_value?: string;
    dependency_rel?: string;
    role?: string;
    surah?: number;
    limit?: number;
}): Promise<VerseWithLinguistics[]>;
/**
 * Create a linguistic pattern with interpretation
 *
 * Example: "Present tense verbs in the Quran indicate ongoing or future actions"
 */
export declare function createPatternInterpretation(data: {
    description: string;
    pattern_type: 'morphological' | 'syntactic' | 'semantic';
    interpretation: string;
    linguistic_features?: object;
    scope?: string;
    phase?: 'question' | 'hypothesis' | 'validation' | 'verification';
}): Promise<{
    success: boolean;
    pattern_id: string;
    claim_id: string;
    message: string;
}>;
/**
 * Create a surah-level thematic interpretation
 *
 * Example: "Surah Al-Baqarah's theme is guidance for believers"
 */
export declare function createSurahTheme(data: {
    surah: number;
    theme: string;
    description?: string;
    phase?: 'question' | 'hypothesis' | 'validation' | 'verification';
}): Promise<{
    success: boolean;
    claim_id: string;
    message: string;
}>;
/**
 * Add a verse as evidence for a claim with verification status
 *
 * Example: Mark verse 2:7 as supporting the present tense verb pattern
 */
export declare function addVerseEvidence(data: {
    claim_id: string;
    surah: number;
    ayah: number;
    verification: 'supports' | 'contradicts' | 'unclear';
    notes?: string;
}): Promise<{
    success: boolean;
    evidence_id: string;
    message: string;
}>;
export {};
//# sourceMappingURL=linguistic.d.ts.map