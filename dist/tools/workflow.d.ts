interface VerificationResult {
    supports: number;
    contradicts: number;
    unclear: number;
    total_verified: number;
}
/**
 * Start a new verification workflow session
 * Creates a session to systematically verify verses one by one
 */
export declare function startWorkflowSession(options: {
    claim_id: string;
    workflow_type: 'pattern' | 'surah_theme';
    linguistic_features?: any;
    surah?: number;
    limit?: number;
}): Promise<{
    success: boolean;
    session_id: string;
    message: string;
    total_verses: number;
    first_verse?: {
        surah: number;
        ayah: number;
        text: string;
    };
}>;
/**
 * Get the next verse in the workflow session for verification
 */
export declare function getNextVerseInWorkflow(session_id: string): Promise<{
    success: boolean;
    message: string;
    verse?: {
        surah: number;
        ayah: number;
        text: string;
    };
    progress: {
        current: number;
        total: number;
        percentage: number;
    };
    completed: boolean;
}>;
/**
 * Submit verification for current verse and advance to next
 */
export declare function submitVerification(options: {
    session_id: string;
    verification: 'supports' | 'contradicts' | 'unclear';
    notes?: string;
}): Promise<{
    success: boolean;
    message: string;
    evidence_id?: string;
    next_verse?: {
        surah: number;
        ayah: number;
        text: string;
    };
    progress: {
        current: number;
        total: number;
        percentage: number;
    };
    completed: boolean;
}>;
/**
 * Get workflow statistics and progress
 */
export declare function getWorkflowStats(session_id: string): Promise<{
    success: boolean;
    message: string;
    stats?: {
        total_verses: number;
        verified: number;
        remaining: number;
        percentage_complete: number;
        verification_counts: VerificationResult;
        has_contradictions: boolean;
    };
}>;
/**
 * List all workflow sessions
 */
export declare function listWorkflowSessions(options?: {
    status?: 'active' | 'completed' | 'paused';
}): Promise<{
    success: boolean;
    message: string;
    sessions: Array<{
        session_id: string;
        claim_id: string;
        workflow_type: string;
        created_at: string;
        progress: {
            current: number;
            total: number;
            percentage: number;
        };
        status: string;
    }>;
}>;
/**
 * Auto-transition claim phase based on verification results
 * If contradictions found: move to 'rejected'
 * If sufficient supporting evidence: move to 'validated'
 */
export declare function checkAndTransitionPhase(session_id: string): Promise<{
    success: boolean;
    message: string;
    phase_transition?: {
        from: string;
        to: string;
        reason: string;
    };
}>;
export {};
//# sourceMappingURL=workflow.d.ts.map