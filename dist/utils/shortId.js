// Generate human-friendly short IDs
// Format: prefix_number (e.g., "claim_123", "session_456")
// In-memory cache for last-issued ID number per type
const idCache = {};
/**
 * Get the next available short ID number for a given type.
 * Uses SQL MAX on first call, then increments from cache.
 */
function getNextShortIdNumber(db, type) {
    if (idCache[type] !== undefined) {
        idCache[type]++;
        return idCache[type];
    }
    const prefix = type + '_';
    const prefixLen = prefix.length;
    let maxNumber = 0;
    if (type === 'evidence') {
        for (const tableName of ['claim_evidence', 'verse_evidence']) {
            try {
                const result = db.exec(`SELECT MAX(CAST(SUBSTR(id, ${prefixLen + 1}) AS INTEGER)) FROM ${tableName} WHERE id LIKE '${prefix}%'`);
                const val = result[0]?.values[0]?.[0];
                if (val && val > maxNumber)
                    maxNumber = val;
            }
            catch (e) {
                // Table doesn't exist yet, skip
            }
        }
    }
    else {
        const tableName = type === 'claim' ? 'claims' :
            type === 'session' ? 'workflow_sessions' : 'patterns';
        const columnName = type === 'session' ? 'session_id' : 'id';
        try {
            const result = db.exec(`SELECT MAX(CAST(SUBSTR(${columnName}, ${prefixLen + 1}) AS INTEGER)) FROM ${tableName} WHERE ${columnName} LIKE '${prefix}%'`);
            const val = result[0]?.values[0]?.[0];
            if (val)
                maxNumber = val;
        }
        catch (e) {
            // Table doesn't exist yet
        }
    }
    idCache[type] = maxNumber + 1;
    return idCache[type];
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