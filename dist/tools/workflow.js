// Workflow system for systematic verse-by-verse verification
import { getDatabase, saveDatabase } from '../db.js';
import { searchByLinguisticFeatures } from './linguistic.js';
import { generateSessionId, generateEvidenceId } from '../utils/shortId.js';
/**
 * Start a new verification workflow session
 * Creates a session to systematically verify verses one by one
 */
export async function startWorkflowSession(options) {
    const db = await getDatabase();
    const session_id = generateSessionId(db);
    try {
        // Verify claim exists
        const claimCheck = db.exec('SELECT id FROM claims WHERE id = ?', [options.claim_id]);
        if (claimCheck.length === 0 || claimCheck[0].values.length === 0) {
            return {
                success: false,
                session_id: '',
                message: `Claim ${options.claim_id} not found`,
                total_verses: 0
            };
        }
        let verses = [];
        // Get verses based on workflow type
        if (options.workflow_type === 'pattern' && options.linguistic_features) {
            verses = await searchByLinguisticFeatures({
                ...options.linguistic_features,
                limit: options.limit || 100
            });
        }
        else if (options.workflow_type === 'surah_theme' && options.surah) {
            // Get all verses in the surah
            const result = db.exec(`SELECT surah_number, ayah_number, text
         FROM verse_texts
         WHERE surah_number = ?
         ORDER BY ayah_number ASC`, [options.surah]);
            if (result.length > 0) {
                verses = result[0].values.map(row => ({
                    surah_number: row[0],
                    ayah_number: row[1],
                    text: row[2]
                }));
            }
        }
        else {
            return {
                success: false,
                session_id: '',
                message: 'Invalid workflow configuration: must specify either linguistic_features for pattern workflow or surah for surah_theme workflow',
                total_verses: 0
            };
        }
        if (verses.length === 0) {
            return {
                success: false,
                session_id: '',
                message: 'No verses found matching criteria',
                total_verses: 0
            };
        }
        // Store session
        const versesJson = JSON.stringify(verses);
        const linguisticFeaturesJson = options.linguistic_features
            ? JSON.stringify(options.linguistic_features)
            : null;
        db.exec(`INSERT INTO workflow_sessions
       (session_id, claim_id, workflow_type, created_at, current_index,
        total_verses, status, linguistic_features, surah, verses_json)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`, [
            session_id,
            options.claim_id,
            options.workflow_type,
            new Date().toISOString(),
            0,
            verses.length,
            'active',
            linguisticFeaturesJson,
            options.surah || null,
            versesJson
        ]);
        saveDatabase(db);
        return {
            success: true,
            session_id,
            message: `Workflow session started with ${verses.length} verses to verify`,
            total_verses: verses.length,
            first_verse: verses[0] ? {
                surah: verses[0].surah_number,
                ayah: verses[0].ayah_number,
                text: verses[0].text
            } : undefined
        };
    }
    catch (error) {
        return {
            success: false,
            session_id: '',
            message: `Error starting workflow: ${error.message}`,
            total_verses: 0
        };
    }
}
/**
 * Get the next verse in the workflow session for verification
 */
export async function getNextVerseInWorkflow(session_id) {
    const db = await getDatabase();
    try {
        // Get session
        const result = db.exec('SELECT current_index, total_verses, verses_json, status FROM workflow_sessions WHERE session_id = ?', [session_id]);
        if (result.length === 0 || result[0].values.length === 0) {
            return {
                success: false,
                message: 'Session not found',
                progress: { current: 0, total: 0, percentage: 0 },
                completed: false
            };
        }
        const [currentIndex, totalVerses, versesJson, status] = result[0].values[0];
        if (status === 'completed') {
            return {
                success: true,
                message: 'Workflow already completed',
                progress: {
                    current: totalVerses,
                    total: totalVerses,
                    percentage: 100
                },
                completed: true
            };
        }
        const verses = JSON.parse(versesJson);
        const nextIndex = currentIndex;
        if (nextIndex >= verses.length) {
            // Mark session as completed
            db.exec('UPDATE workflow_sessions SET status = ?, current_index = ? WHERE session_id = ?', ['completed', nextIndex, session_id]);
            saveDatabase(db);
            return {
                success: true,
                message: 'All verses verified - workflow complete',
                progress: {
                    current: totalVerses,
                    total: totalVerses,
                    percentage: 100
                },
                completed: true
            };
        }
        const verse = verses[nextIndex];
        const percentage = Math.round((nextIndex / totalVerses) * 100);
        return {
            success: true,
            message: `Verse ${nextIndex + 1} of ${totalVerses}`,
            verse: {
                surah: verse.surah_number,
                ayah: verse.ayah_number,
                text: verse.text
            },
            progress: {
                current: nextIndex + 1,
                total: totalVerses,
                percentage
            },
            completed: false
        };
    }
    catch (error) {
        return {
            success: false,
            message: `Error getting next verse: ${error.message}`,
            progress: { current: 0, total: 0, percentage: 0 },
            completed: false
        };
    }
}
/**
 * Submit verification for current verse and advance to next
 */
export async function submitVerification(options) {
    const db = await getDatabase();
    try {
        // Get current session state
        const sessionResult = db.exec('SELECT claim_id, current_index, total_verses, verses_json FROM workflow_sessions WHERE session_id = ?', [options.session_id]);
        if (sessionResult.length === 0 || sessionResult[0].values.length === 0) {
            return {
                success: false,
                message: 'Session not found',
                progress: { current: 0, total: 0, percentage: 0 },
                completed: false
            };
        }
        const [claimId, currentIndex, totalVerses, versesJson] = sessionResult[0].values[0];
        const verses = JSON.parse(versesJson);
        const currentVerse = verses[currentIndex];
        // Save verification as evidence
        const evidenceId = generateEvidenceId(db);
        db.exec(`INSERT INTO verse_evidence
       (id, claim_id, verse_surah, verse_ayah, verification, notes, verified_at)
       VALUES (?, ?, ?, ?, ?, ?, ?)`, [
            evidenceId,
            claimId,
            currentVerse.surah_number,
            currentVerse.ayah_number,
            options.verification,
            options.notes || '',
            new Date().toISOString()
        ]);
        // Advance to next verse
        const nextIndex = currentIndex + 1;
        db.exec('UPDATE workflow_sessions SET current_index = ? WHERE session_id = ?', [nextIndex, options.session_id]);
        saveDatabase(db);
        // Check if workflow is complete
        if (nextIndex >= verses.length) {
            db.exec('UPDATE workflow_sessions SET status = ? WHERE session_id = ?', ['completed', options.session_id]);
            saveDatabase(db);
            return {
                success: true,
                message: 'Verification saved. Workflow complete!',
                evidence_id: evidenceId,
                progress: {
                    current: totalVerses,
                    total: totalVerses,
                    percentage: 100
                },
                completed: true
            };
        }
        // Get next verse
        const nextVerse = verses[nextIndex];
        const percentage = Math.round((nextIndex / totalVerses) * 100);
        return {
            success: true,
            message: `Verification saved. Moving to verse ${nextIndex + 1} of ${totalVerses}`,
            evidence_id: evidenceId,
            next_verse: {
                surah: nextVerse.surah_number,
                ayah: nextVerse.ayah_number,
                text: nextVerse.text
            },
            progress: {
                current: nextIndex + 1,
                total: totalVerses,
                percentage
            },
            completed: false
        };
    }
    catch (error) {
        return {
            success: false,
            message: `Error submitting verification: ${error.message}`,
            progress: { current: 0, total: 0, percentage: 0 },
            completed: false
        };
    }
}
/**
 * Get workflow statistics and progress
 */
export async function getWorkflowStats(session_id) {
    const db = await getDatabase();
    try {
        // Get session info
        const sessionResult = db.exec('SELECT claim_id, current_index, total_verses, status FROM workflow_sessions WHERE session_id = ?', [session_id]);
        if (sessionResult.length === 0 || sessionResult[0].values.length === 0) {
            return {
                success: false,
                message: 'Session not found'
            };
        }
        const [claimId, currentIndex, totalVerses, status] = sessionResult[0].values[0];
        // Get verification counts
        const verificationResult = db.exec(`SELECT verification, COUNT(*) as count
       FROM verse_evidence
       WHERE claim_id = ?
       GROUP BY verification`, [claimId]);
        const verificationCounts = {
            supports: 0,
            contradicts: 0,
            unclear: 0,
            total_verified: 0
        };
        if (verificationResult.length > 0) {
            verificationResult[0].values.forEach(row => {
                const [verification, count] = row;
                if (verification === 'supports')
                    verificationCounts.supports = count;
                if (verification === 'contradicts')
                    verificationCounts.contradicts = count;
                if (verification === 'unclear')
                    verificationCounts.unclear = count;
            });
        }
        verificationCounts.total_verified =
            verificationCounts.supports +
                verificationCounts.contradicts +
                verificationCounts.unclear;
        const percentageComplete = Math.round((currentIndex / totalVerses) * 100);
        return {
            success: true,
            message: 'Workflow statistics retrieved',
            stats: {
                total_verses: totalVerses,
                verified: currentIndex,
                remaining: totalVerses - currentIndex,
                percentage_complete: percentageComplete,
                verification_counts: verificationCounts,
                has_contradictions: verificationCounts.contradicts > 0
            }
        };
    }
    catch (error) {
        return {
            success: false,
            message: `Error getting workflow stats: ${error.message}`
        };
    }
}
/**
 * List all workflow sessions
 */
export async function listWorkflowSessions(options) {
    const db = await getDatabase();
    try {
        let query = `
      SELECT session_id, claim_id, workflow_type, created_at,
             current_index, total_verses, status
      FROM workflow_sessions
    `;
        const params = [];
        if (options?.status) {
            query += ' WHERE status = ?';
            params.push(options.status);
        }
        query += ' ORDER BY created_at DESC';
        const result = db.exec(query, params);
        if (result.length === 0 || result[0].values.length === 0) {
            return {
                success: true,
                message: 'No workflow sessions found',
                sessions: []
            };
        }
        const sessions = result[0].values.map(row => {
            const [sessionId, claimId, workflowType, createdAt, currentIndex, totalVerses, status] = row;
            const percentage = Math.round((currentIndex / totalVerses) * 100);
            return {
                session_id: sessionId,
                claim_id: claimId,
                workflow_type: workflowType,
                created_at: createdAt,
                progress: {
                    current: currentIndex,
                    total: totalVerses,
                    percentage
                },
                status: status
            };
        });
        return {
            success: true,
            message: `Found ${sessions.length} workflow session(s)`,
            sessions
        };
    }
    catch (error) {
        return {
            success: false,
            message: `Error listing workflow sessions: ${error.message}`,
            sessions: []
        };
    }
}
/**
 * Auto-transition claim phase based on verification results
 * If contradictions found: move to 'rejected'
 * If sufficient supporting evidence: move to 'validated'
 */
export async function checkAndTransitionPhase(session_id) {
    const db = await getDatabase();
    try {
        const statsResult = await getWorkflowStats(session_id);
        if (!statsResult.success || !statsResult.stats) {
            return {
                success: false,
                message: 'Failed to get workflow statistics'
            };
        }
        const stats = statsResult.stats;
        // Get session and claim info
        const sessionResult = db.exec('SELECT claim_id FROM workflow_sessions WHERE session_id = ?', [session_id]);
        if (sessionResult.length === 0 || sessionResult[0].values.length === 0) {
            return {
                success: false,
                message: 'Session not found'
            };
        }
        const claimId = sessionResult[0].values[0][0];
        // Get current phase
        const claimResult = db.exec('SELECT phase FROM claims WHERE id = ?', [claimId]);
        if (claimResult.length === 0 || claimResult[0].values.length === 0) {
            return {
                success: false,
                message: 'Claim not found'
            };
        }
        const currentPhase = claimResult[0].values[0][0];
        // Transition logic
        let newPhase = null;
        let reason = '';
        // If contradictions found, move to rejected
        if (stats.has_contradictions && stats.verification_counts.contradicts > 0) {
            newPhase = 'rejected';
            reason = `Found ${stats.verification_counts.contradicts} contradicting verse(s)`;
        }
        // If workflow complete and no contradictions, validate with sufficient evidence
        else if (stats.percentage_complete === 100 && stats.verification_counts.supports >= 3) {
            newPhase = 'validated';
            reason = `Workflow complete with ${stats.verification_counts.supports} supporting verses and no contradictions`;
        }
        // If still in hypothesis and have some supporting evidence, move to validation
        else if (currentPhase === 'hypothesis' && stats.verification_counts.supports >= 3) {
            newPhase = 'validation';
            reason = `Found ${stats.verification_counts.supports} supporting verses, ready for broader validation`;
        }
        // Apply phase transition
        if (newPhase && newPhase !== currentPhase) {
            db.exec('UPDATE claims SET phase = ? WHERE id = ?', [newPhase, claimId]);
            saveDatabase(db);
            return {
                success: true,
                message: `Phase transition: ${currentPhase} → ${newPhase}`,
                phase_transition: {
                    from: currentPhase,
                    to: newPhase,
                    reason
                }
            };
        }
        return {
            success: true,
            message: `No phase transition needed (current: ${currentPhase})`
        };
    }
    catch (error) {
        return {
            success: false,
            message: `Error checking phase transition: ${error.message}`
        };
    }
}
//# sourceMappingURL=workflow.js.map