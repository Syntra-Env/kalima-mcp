import { getDatabase, Verse } from '../db.js';
import { rowsToObjects } from '../utils/dbHelpers.js';

interface LinguisticFeature {
  root: string | null;
  lemma: string | null;
  pos: string | null;
  verb_form: string | null;
  aspect: string | null;
  mood: string | null;
}

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
export async function getVerseWithContext(
  surah: number,
  ayah: number,
  options: {
    include_root_claims?: boolean;
    include_form_claims?: boolean;
    include_pos_claims?: boolean;
  } = {}
): Promise<VerseWithContext> {
  const db = await getDatabase();
  const {
    include_root_claims = true,
    include_form_claims = true,
    include_pos_claims = true
  } = options;

  // Get the verse text
  const verseResult = db.exec(
    'SELECT surah_number, ayah_number, text FROM verse_texts WHERE surah_number = ? AND ayah_number = ?',
    [surah, ayah]
  );

  if (!verseResult.length || !verseResult[0].values.length) {
    throw new Error(`Verse ${surah}:${ayah} not found`);
  }

  const verse = rowsToObjects<Verse>(verseResult[0].columns, verseResult[0].values)[0];

  // Get all tokens and their segments for this verse
  const tokensResult = db.exec(
    `SELECT
      t.id as token_id,
      t.text as token_text,
      t.token_index,
      s.root,
      s.lemma,
      s.pos,
      s.verb_form,
      s.aspect,
      s.mood
    FROM tokens t
    LEFT JOIN segments s ON s.token_id = t.id
    WHERE t.verse_surah = ? AND t.verse_ayah = ?
    ORDER BY t.token_index ASC`,
    [surah, ayah]
  );

  const tokenData = tokensResult.length && tokensResult[0].values.length
    ? rowsToObjects<{
        token_id: string;
        token_text: string;
        token_index: number;
        root: string | null;
        lemma: string | null;
        pos: string | null;
        verb_form: string | null;
        aspect: string | null;
        mood: string | null;
      }>(tokensResult[0].columns, tokensResult[0].values)
    : [];

  // For each token, find related claims based on linguistic features
  const wordsWithContext: WordContext[] = [];

  for (const token of tokenData) {
    const relatedClaims: RelatedClaim[] = [];

    // Build feature queries
    const featuresToCheck: Array<{ type: string; value: string | null }> = [];

    if (include_root_claims && token.root) {
      featuresToCheck.push({ type: 'root', value: token.root });
    }
    if (include_form_claims && token.verb_form) {
      featuresToCheck.push({ type: 'verb_form', value: token.verb_form });
    }
    if (include_pos_claims && token.pos) {
      featuresToCheck.push({ type: 'pos', value: token.pos });
    }
    if (token.aspect) {
      featuresToCheck.push({ type: 'aspect', value: token.aspect });
    }

    // Query for claims with matching linguistic features
    for (const feature of featuresToCheck) {
      if (feature.value) {
        const claimsResult = db.exec(
          `SELECT DISTINCT
            c.id as claim_id,
            c.content as claim_content,
            c.phase as claim_phase,
            c.pattern_id,
            plf.feature_type as matched_feature_type,
            plf.feature_value as matched_feature_value
          FROM pattern_linguistic_features plf
          JOIN claims c ON c.pattern_id = plf.pattern_id
          WHERE plf.feature_type = ? AND plf.feature_value = ?`,
          [feature.type, feature.value]
        );

        if (claimsResult.length && claimsResult[0].values.length) {
          const claims = rowsToObjects<RelatedClaim>(
            claimsResult[0].columns,
            claimsResult[0].values
          );
          relatedClaims.push(...claims);
        }
      }
    }

    wordsWithContext.push({
      token_text: token.token_text,
      token_index: token.token_index,
      root: token.root,
      lemma: token.lemma,
      pos: token.pos,
      verb_form: token.verb_form,
      aspect: token.aspect,
      related_claims: relatedClaims
    });
  }

  // Get direct verse claims (claims that explicitly reference this verse)
  const verseClaimsResult = db.exec(
    `SELECT
      vc.claim_id,
      c.content as claim_content,
      c.phase as claim_phase,
      vc.evidence_type
    FROM verse_claims vc
    JOIN claims c ON c.id = vc.claim_id
    WHERE vc.surah = ? AND vc.ayah = ?
    ORDER BY vc.created_at DESC`,
    [surah, ayah]
  );

  const directVerseClaims = verseClaimsResult.length && verseClaimsResult[0].values.length
    ? rowsToObjects<{
        claim_id: string;
        claim_content: string;
        claim_phase: string;
        evidence_type: string;
      }>(verseClaimsResult[0].columns, verseClaimsResult[0].values)
    : [];

  return {
    verse,
    words_with_context: wordsWithContext,
    direct_verse_claims: directVerseClaims
  };
}
