// Generate human-friendly short IDs
// Format: prefix_number (e.g., "claim_123", "session_456")
/**
 * Get the next available short ID number for a given type
 */
function getNextShortIdNumber(db, type) {
    const tableName = type === 'claim' ? 'claims' :
        type === 'session' ? 'workflow_sessions' :
            type === 'pattern' ? 'patterns' : 'verse_evidence';
    const columnName = type === 'session' ? 'session_id' : 'id';
    try {
        // Get the maximum existing number for this type
        const result = db.exec(`SELECT ${columnName} FROM ${tableName} WHERE ${columnName} LIKE '${type}_%'`);
        if (result.length === 0 || result[0].values.length === 0) {
            return 1; // Start from 1
        }
        let maxNumber = 0;
        for (const row of result[0].values) {
            const shortId = row[0];
            const match = shortId.match(/^[a-z]+_(\d+)$/);
            if (match) {
                const num = parseInt(match[1], 10);
                if (num > maxNumber) {
                    maxNumber = num;
                }
            }
        }
        return maxNumber + 1;
    }
    catch (e) {
        // Table or column doesn't exist yet, start from 1
        return 1;
    }
}
/**
 * Generate an ID for claims
 * Format: claim_123
 */
export function generateClaimId(db) {
    const num = getNextShortIdNumber(db, 'claim');
    return `claim_${num}`;
}
/**
 * Generate an ID for workflow sessions
 * Format: session_123
 */
export function generateSessionId(db) {
    const num = getNextShortIdNumber(db, 'session');
    return `session_${num}`;
}
/**
 * Generate an ID for patterns
 * Format: pattern_123
 */
export function generatePatternId(db) {
    const num = getNextShortIdNumber(db, 'pattern');
    return `pattern_${num}`;
}
/**
 * Generate an ID for evidence
 * Format: evidence_123
 */
export function generateEvidenceId(db) {
    const num = getNextShortIdNumber(db, 'evidence');
    return `evidence_${num}`;
}
/**
 * Check if a string looks like a short ID (vs UUID)
 */
export function isShortId(id) {
    return /^(claim|session|pattern|evidence)_\d+$/.test(id);
}
/**
 * Extract the prefix from a short ID
 */
export function getShortIdPrefix(id) {
    const match = id.match(/^(claim|session|pattern|evidence)_/);
    return match ? match[1] : null;
}
//# sourceMappingURL=shortId.js.map