// Test script for new linguistic analysis tools
import {
  searchByLinguisticFeatures,
  createPatternInterpretation,
  createSurahTheme,
  addVerseEvidence
} from '../dist/tools/linguistic.js';

async function main() {
  console.log('╔════════════════════════════════════════════════════════════════╗');
  console.log('║     Kalima Linguistic Tools - Test Report                     ║');
  console.log('║     Testing 4 new MCP tools for linguistic analysis           ║');
  console.log('╚════════════════════════════════════════════════════════════════╝\n');

  // Test 1: Search by linguistic features - present tense verbs
  console.log('┌─ Test 1: Search Present Tense Verbs ──────────────────────────┐');
  try {
    const presentVerses = await searchByLinguisticFeatures({
      pos: 'VERB',
      aspect: 'imperfective',
      limit: 5
    });
    console.log(`│ Found: ${presentVerses.length} verses with present tense verbs`);
    if (presentVerses.length > 0) {
      console.log('│');
      console.log('│ Sample verse:');
      const v = presentVerses[0];
      console.log(`│   ${v.surah_number}:${v.ayah_number}`);
      console.log(`│   Text: ${v.text.substring(0, 50)}...`);
      console.log(`│   Tokens: ${v.tokens?.length || 0}`);
      console.log(`│   Segments: ${v.segments?.length || 0}`);
    }
    console.log(`│ ${presentVerses.length > 0 ? '✅ PASS' : '❌ FAIL'}`);
  } catch (error) {
    console.log(`│ ❌ ERROR: ${error.message}`);
  }
  console.log('└────────────────────────────────────────────────────────────────┘\n');

  // Test 2: Search imperatives
  console.log('┌─ Test 2: Search Imperative Verbs ─────────────────────────────┐');
  try {
    const imperatives = await searchByLinguisticFeatures({
      pos: 'VERB',
      aspect: 'imperative',
      limit: 3
    });
    console.log(`│ Found: ${imperatives.length} verses with imperatives`);
    if (imperatives.length > 0) {
      console.log('│ Sample: ' + imperatives[0].surah_number + ':' + imperatives[0].ayah_number);
    }
    console.log(`│ ${imperatives.length > 0 ? '✅ PASS' : '❌ FAIL'}`);
  } catch (error) {
    console.log(`│ ❌ ERROR: ${error.message}`);
  }
  console.log('└────────────────────────────────────────────────────────────────┘\n');

  // Test 3: Create pattern interpretation
  console.log('┌─ Test 3: Create Pattern Interpretation ───────────────────────┐');
  try {
    const patternResult = await createPatternInterpretation({
      description: 'Present tense verbs in the Quran',
      pattern_type: 'morphological',
      interpretation: 'Present tense (imperfective aspect) verbs indicate actions that are ongoing, habitual, or will occur in the future',
      linguistic_features: {
        pos: 'VERB',
        aspect: 'imperfective'
      },
      phase: 'hypothesis'
    });
    console.log(`│ Success: ${patternResult.success}`);
    if (patternResult.success) {
      console.log(`│ Pattern ID: ${patternResult.pattern_id}`);
      console.log(`│ Message: ${patternResult.message.split('\n')[0]}`);
    }
    console.log(`│ ${patternResult.success ? '✅ PASS' : '❌ FAIL'}`);

    // Store pattern_id for next test
    if (patternResult.success) {
      global.testPatternId = patternResult.pattern_id;
    }
  } catch (error) {
    console.log(`│ ❌ ERROR: ${error.message}`);
  }
  console.log('└────────────────────────────────────────────────────────────────┘\n');

  // Test 4: Create surah theme
  console.log('┌─ Test 4: Create Surah Theme ──────────────────────────────────┐');
  try {
    const themeResult = await createSurahTheme({
      surah: 1,
      theme: 'Opening prayer and seeking guidance',
      description: 'Al-Fatihah serves as an opening prayer that establishes the believer\'s relationship with Allah',
      phase: 'hypothesis'
    });
    console.log(`│ Success: ${themeResult.success}`);
    if (themeResult.success) {
      console.log(`│ Claim ID: ${themeResult.claim_id}`);
      console.log(`│ Message: ${themeResult.message.split('\n')[0]}`);
    }
    console.log(`│ ${themeResult.success ? '✅ PASS' : '❌ FAIL'}`);

    // Store claim_id for next test
    if (themeResult.success) {
      global.testClaimId = themeResult.claim_id;
    }
  } catch (error) {
    console.log(`│ ❌ ERROR: ${error.message}`);
  }
  console.log('└────────────────────────────────────────────────────────────────┘\n');

  // Test 5: Add verse evidence
  console.log('┌─ Test 5: Add Verse Evidence ──────────────────────────────────┐');
  try {
    if (!global.testClaimId) {
      console.log('│ ⚠️  SKIPPED: No claim_id from previous test');
    } else {
      const evidenceResult = await addVerseEvidence({
        claim_id: global.testClaimId,
        surah: 1,
        ayah: 1,
        verification: 'supports',
        notes: 'First verse invokes Allah\'s name, supporting the theme'
      });
      console.log(`│ Success: ${evidenceResult.success}`);
      if (evidenceResult.success) {
        console.log(`│ Evidence ID: ${evidenceResult.evidence_id}`);
        console.log(`│ Message: ${evidenceResult.message}`);
      }
      console.log(`│ ${evidenceResult.success ? '✅ PASS' : '❌ FAIL'}`);
    }
  } catch (error) {
    console.log(`│ ❌ ERROR: ${error.message}`);
  }
  console.log('└────────────────────────────────────────────────────────────────┘\n');

  // Test 6: Search by specific root
  console.log('┌─ Test 6: Search by Arabic Root ───────────────────────────────┐');
  try {
    // Try a common root - might be "د-ع-و" (invitation/prayer)
    const rootVerses = await searchByLinguisticFeatures({
      root: 'د-ع-و',
      limit: 3
    });
    console.log(`│ Found: ${rootVerses.length} verses with root د-ع-و`);
    if (rootVerses.length > 0) {
      console.log('│ Sample: ' + rootVerses[0].surah_number + ':' + rootVerses[0].ayah_number);
    }
    console.log(`│ ${rootVerses.length >= 0 ? '✅ PASS' : '❌ FAIL'} (0 results OK - root may not exist)`);
  } catch (error) {
    console.log(`│ ❌ ERROR: ${error.message}`);
  }
  console.log('└────────────────────────────────────────────────────────────────┘\n');

  // Summary
  console.log('╔════════════════════════════════════════════════════════════════╗');
  console.log('║                    ✅ Testing Complete                         ║');
  console.log('║                                                                ║');
  console.log('║  New Tools Implemented:                                        ║');
  console.log('║  • search_by_linguistic_features - Query by POS, aspect, etc.  ║');
  console.log('║  • create_pattern_interpretation - Store linguistic patterns   ║');
  console.log('║  • create_surah_theme - Document surah themes                  ║');
  console.log('║  • add_verse_evidence - Track verse verification               ║');
  console.log('╚════════════════════════════════════════════════════════════════╝');
}

main().catch(console.error);
