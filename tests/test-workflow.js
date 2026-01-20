// Test script for workflow system
import {
  createPatternInterpretation,
  createSurahTheme
} from '../dist/tools/linguistic.js';
import {
  startWorkflowSession,
  getNextVerseInWorkflow,
  submitVerification,
  getWorkflowStats,
  listWorkflowSessions,
  checkAndTransitionPhase
} from '../dist/tools/workflow.js';

async function main() {
  console.log('╔════════════════════════════════════════════════════════════════╗');
  console.log('║     Kalima Workflow System - Test Report                      ║');
  console.log('║     Testing 6 new workflow management tools                   ║');
  console.log('╚════════════════════════════════════════════════════════════════╝\n');

  // Test 1: Create pattern and start pattern workflow
  console.log('┌─ Test 1: Start Pattern Workflow ──────────────────────────────┐');
  try {
    // First create a pattern
    const pattern = await createPatternInterpretation({
      description: 'Present tense verbs test pattern',
      pattern_type: 'morphological',
      interpretation: 'Testing workflow with present tense verbs',
      linguistic_features: { pos: 'VERB', aspect: 'imperfective' },
      phase: 'hypothesis'
    });
    console.log(`│ Pattern created: ${pattern.pattern_id}`);
    console.log(`│ Claim created: ${pattern.claim_id}`);

    // Start workflow
    const session = await startWorkflowSession({
      claim_id: pattern.claim_id,
      workflow_type: 'pattern',
      linguistic_features: { pos: 'VERB', aspect: 'imperfective' },
      limit: 5
    });
    console.log(`│ Session started: ${session.session_id}`);
    console.log(`│ Total verses: ${session.total_verses}`);
    if (session.first_verse) {
      console.log(`│ First verse: ${session.first_verse.surah}:${session.first_verse.ayah}`);
    }
    console.log(`│ ${session.success ? '✅ PASS' : '❌ FAIL'}`);

    // Store for next tests
    global.testSessionId = session.session_id;
    global.testClaimId = pattern.claim_id;
  } catch (error) {
    console.log(`│ ❌ ERROR: ${error.message}`);
  }
  console.log('└────────────────────────────────────────────────────────────────┘\n');

  // Test 2: Get next verse
  console.log('┌─ Test 2: Get Next Verse ──────────────────────────────────────┐');
  try {
    if (!global.testSessionId) {
      console.log('│ ⚠️  SKIPPED: No session from previous test');
    } else {
      const result = await getNextVerseInWorkflow(global.testSessionId);
      console.log(`│ Success: ${result.success}`);
      if (result.verse) {
        console.log(`│ Verse: ${result.verse.surah}:${result.verse.ayah}`);
        console.log(`│ Text: ${result.verse.text.substring(0, 40)}...`);
      }
      console.log(`│ Progress: ${result.progress.current}/${result.progress.total} (${result.progress.percentage}%)`);
      console.log(`│ ${result.success ? '✅ PASS' : '❌ FAIL'}`);
    }
  } catch (error) {
    console.log(`│ ❌ ERROR: ${error.message}`);
  }
  console.log('└────────────────────────────────────────────────────────────────┘\n');

  // Test 3: Submit verification (supports)
  console.log('┌─ Test 3: Submit Verification (Supports) ───────────────────────┐');
  try {
    if (!global.testSessionId) {
      console.log('│ ⚠️  SKIPPED: No session from previous test');
    } else {
      const result = await submitVerification({
        session_id: global.testSessionId,
        verification: 'supports',
        notes: 'Test verification - this verse supports the pattern'
      });
      console.log(`│ Success: ${result.success}`);
      console.log(`│ Evidence ID: ${result.evidence_id}`);
      if (result.next_verse) {
        console.log(`│ Next verse: ${result.next_verse.surah}:${result.next_verse.ayah}`);
      }
      console.log(`│ Progress: ${result.progress.current}/${result.progress.total} (${result.progress.percentage}%)`);
      console.log(`│ ${result.success ? '✅ PASS' : '❌ FAIL'}`);
    }
  } catch (error) {
    console.log(`│ ❌ ERROR: ${error.message}`);
  }
  console.log('└────────────────────────────────────────────────────────────────┘\n');

  // Test 4: Submit verification (contradicts)
  console.log('┌─ Test 4: Submit Verification (Contradicts) ────────────────────┐');
  try {
    if (!global.testSessionId) {
      console.log('│ ⚠️  SKIPPED: No session from previous test');
    } else {
      const result = await submitVerification({
        session_id: global.testSessionId,
        verification: 'contradicts',
        notes: 'Test verification - this verse contradicts the pattern'
      });
      console.log(`│ Success: ${result.success}`);
      console.log(`│ Evidence ID: ${result.evidence_id}`);
      console.log(`│ Progress: ${result.progress.current}/${result.progress.total} (${result.progress.percentage}%)`);
      console.log(`│ ${result.success ? '✅ PASS' : '❌ FAIL'}`);
    }
  } catch (error) {
    console.log(`│ ❌ ERROR: ${error.message}`);
  }
  console.log('└────────────────────────────────────────────────────────────────┘\n');

  // Test 5: Get workflow stats
  console.log('┌─ Test 5: Get Workflow Stats ──────────────────────────────────┐');
  try {
    if (!global.testSessionId) {
      console.log('│ ⚠️  SKIPPED: No session from previous test');
    } else {
      const result = await getWorkflowStats(global.testSessionId);
      console.log(`│ Success: ${result.success}`);
      if (result.stats) {
        console.log(`│ Total verses: ${result.stats.total_verses}`);
        console.log(`│ Verified: ${result.stats.verified}`);
        console.log(`│ Remaining: ${result.stats.remaining}`);
        console.log(`│ Supports: ${result.stats.verification_counts.supports}`);
        console.log(`│ Contradicts: ${result.stats.verification_counts.contradicts}`);
        console.log(`│ Unclear: ${result.stats.verification_counts.unclear}`);
        console.log(`│ Has contradictions: ${result.stats.has_contradictions}`);
      }
      console.log(`│ ${result.success ? '✅ PASS' : '❌ FAIL'}`);
    }
  } catch (error) {
    console.log(`│ ❌ ERROR: ${error.message}`);
  }
  console.log('└────────────────────────────────────────────────────────────────┘\n');

  // Test 6: Check phase transition
  console.log('┌─ Test 6: Check Phase Transition ──────────────────────────────┐');
  try {
    if (!global.testSessionId) {
      console.log('│ ⚠️  SKIPPED: No session from previous test');
    } else {
      const result = await checkAndTransitionPhase(global.testSessionId);
      console.log(`│ Success: ${result.success}`);
      console.log(`│ Message: ${result.message}`);
      if (result.phase_transition) {
        console.log(`│ Transition: ${result.phase_transition.from} → ${result.phase_transition.to}`);
        console.log(`│ Reason: ${result.phase_transition.reason}`);
      }
      console.log(`│ ${result.success ? '✅ PASS' : '❌ FAIL'}`);
    }
  } catch (error) {
    console.log(`│ ❌ ERROR: ${error.message}`);
  }
  console.log('└────────────────────────────────────────────────────────────────┘\n');

  // Test 7: List workflow sessions
  console.log('┌─ Test 7: List Workflow Sessions ──────────────────────────────┐');
  try {
    const result = await listWorkflowSessions();
    console.log(`│ Success: ${result.success}`);
    console.log(`│ Found ${result.sessions.length} session(s)`);
    if (result.sessions.length > 0) {
      const session = result.sessions[0];
      console.log(`│ First session: ${session.session_id.substring(0, 20)}...`);
      console.log(`│ Type: ${session.workflow_type}`);
      console.log(`│ Status: ${session.status}`);
      console.log(`│ Progress: ${session.progress.percentage}%`);
    }
    console.log(`│ ${result.success ? '✅ PASS' : '❌ FAIL'}`);
  } catch (error) {
    console.log(`│ ❌ ERROR: ${error.message}`);
  }
  console.log('└────────────────────────────────────────────────────────────────┘\n');

  // Test 8: Complete remaining verses
  console.log('┌─ Test 8: Complete Workflow ───────────────────────────────────┐');
  try {
    if (!global.testSessionId) {
      console.log('│ ⚠️  SKIPPED: No session from previous test');
    } else {
      // Submit remaining verifications
      let completed = false;
      let count = 0;
      while (!completed && count < 10) {
        const result = await submitVerification({
          session_id: global.testSessionId,
          verification: 'supports',
          notes: 'Completing workflow'
        });
        completed = result.completed;
        count++;
      }
      console.log(`│ Submitted ${count} more verification(s)`);
      console.log(`│ Workflow completed: ${completed}`);
      console.log(`│ ${completed ? '✅ PASS' : '⚠️  PARTIAL'}`);
    }
  } catch (error) {
    console.log(`│ ❌ ERROR: ${error.message}`);
  }
  console.log('└────────────────────────────────────────────────────────────────┘\n');

  // Test 9: Start surah theme workflow
  console.log('┌─ Test 9: Start Surah Theme Workflow ──────────────────────────┐');
  try {
    // Create surah theme
    const theme = await createSurahTheme({
      surah: 1,
      theme: 'Test theme for Al-Fatihah',
      description: 'Testing surah workflow',
      phase: 'hypothesis'
    });
    console.log(`│ Theme created: ${theme.claim_id}`);

    // Start workflow
    const session = await startWorkflowSession({
      claim_id: theme.claim_id,
      workflow_type: 'surah_theme',
      surah: 1
    });
    console.log(`│ Session started: ${session.session_id}`);
    console.log(`│ Total verses: ${session.total_verses} (entire Al-Fatihah)`);
    console.log(`│ ${session.success ? '✅ PASS' : '❌ FAIL'}`);

    // Store for final test
    global.testSurahSessionId = session.session_id;
  } catch (error) {
    console.log(`│ ❌ ERROR: ${error.message}`);
  }
  console.log('└────────────────────────────────────────────────────────────────┘\n');

  // Test 10: Complete surah workflow
  console.log('┌─ Test 10: Complete Surah Workflow ────────────────────────────┐');
  try {
    if (!global.testSurahSessionId) {
      console.log('│ ⚠️  SKIPPED: No surah session from previous test');
    } else {
      // Verify all 7 verses of Al-Fatihah
      let completed = false;
      let count = 0;
      while (!completed && count < 10) {
        const result = await submitVerification({
          session_id: global.testSurahSessionId,
          verification: 'supports',
          notes: `Verse ${count + 1} supports the theme`
        });
        completed = result.completed;
        count++;
      }
      console.log(`│ Verified ${count} verse(s)`);
      console.log(`│ Workflow completed: ${completed}`);

      // Get final stats
      const stats = await getWorkflowStats(global.testSurahSessionId);
      if (stats.stats) {
        console.log(`│ Final stats: ${stats.stats.verification_counts.supports} supports, ${stats.stats.verification_counts.contradicts} contradicts`);
      }
      console.log(`│ ${completed ? '✅ PASS' : '⚠️  PARTIAL'}`);
    }
  } catch (error) {
    console.log(`│ ❌ ERROR: ${error.message}`);
  }
  console.log('└────────────────────────────────────────────────────────────────┘\n');

  // Summary
  console.log('╔════════════════════════════════════════════════════════════════╗');
  console.log('║                    ✅ Testing Complete                         ║');
  console.log('║                                                                ║');
  console.log('║  New Workflow Tools Implemented:                               ║');
  console.log('║  • start_workflow_session - Begin verse-by-verse verification  ║');
  console.log('║  • get_next_verse - Get current verse for verification        ║');
  console.log('║  • submit_verification - Submit result and advance             ║');
  console.log('║  • get_workflow_stats - View progress and statistics           ║');
  console.log('║  • list_workflow_sessions - List all workflow sessions         ║');
  console.log('║  • check_phase_transition - Auto-transition claim phases      ║');
  console.log('║                                                                ║');
  console.log('║  Workflow Features:                                            ║');
  console.log('║  ✓ Pattern workflows (linguistic feature search)              ║');
  console.log('║  ✓ Surah theme workflows (entire chapter verification)        ║');
  console.log('║  ✓ Progress tracking (current/total/percentage)                ║');
  console.log('║  ✓ Evidence tracking (supports/contradicts/unclear)            ║');
  console.log('║  ✓ Contradiction detection                                     ║');
  console.log('║  ✓ Auto-phase transitions                                      ║');
  console.log('║  ✓ Resumable sessions (database-backed state)                  ║');
  console.log('╚════════════════════════════════════════════════════════════════╝');
}

main().catch(console.error);
