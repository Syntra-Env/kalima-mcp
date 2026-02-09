import { Verse } from '../db.js';
interface RelatedClaim {
    claim_id: string;
    claim_content: string;
    claim_phase: string;
    pattern_id: string | null;
    matched_feature_type: string;
    matched_feature_value: string;
}
interface WordContext {
    token_text: string;
    token_index: number;
    root: string | null;
    lemma: string | null;
    pos: string | null;
    verb_form: string | null;
    aspect: string | null;
    related_claims: RelatedClaim[];
}
export interface VerseWithContext {
    verse: Verse;
    words_with_context: WordContext[];
    direct_verse_claims: Array<{
        claim_id: string;
        claim_content: string;
        claim_phase: string;
        evidence_type: string;
    }>;
}
/**
 * Get a verse with all contextual hypotheses based on linguistic features
 *
 * This retrieves:
 * 1. The verse text
 * 2. For each word: its linguistic features and related claims/patterns
 * 3. Direct claims that reference this verse
 */
export declare function getVerseWithContext(surah: number, ayah: number, options?: {
    include_root_claims?: boolean;
    include_form_claims?: boolean;
    include_pos_claims?: boolean;
}): Promise<VerseWithContext>;
export {};
//# sourceMappingURL=context.d.ts.map