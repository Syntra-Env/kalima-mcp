import { Database as SqlJsDatabase } from 'sql.js';
/**
 * Generate an ID for claims
 * Format: claim_123
 */
export declare function generateClaimId(db: SqlJsDatabase): string;
/**
 * Generate an ID for workflow sessions
 * Format: session_123
 */
export declare function generateSessionId(db: SqlJsDatabase): string;
/**
 * Generate an ID for patterns
 * Format: pattern_123
 */
export declare function generatePatternId(db: SqlJsDatabase): string;
/**
 * Generate an ID for evidence
 * Format: evidence_123
 */
export declare function generateEvidenceId(db: SqlJsDatabase): string;
/**
 * Check if a string looks like a short ID (vs UUID)
 */
export declare function isShortId(id: string): boolean;
/**
 * Extract the prefix from a short ID
 */
export declare function getShortIdPrefix(id: string): string | null;
//# sourceMappingURL=shortId.d.ts.map