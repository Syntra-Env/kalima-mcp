// Shared database helpers used across tool modules
/**
 * Transform sql.js result rows into typed objects
 */
export function rowsToObjects(columns, values) {
    return values.map(row => {
        const obj = {};
        columns.forEach((col, idx) => {
            obj[col] = row[idx];
        });
        return obj;
    });
}
/**
 * Normalize Arabic text for search by:
 * 1. Removing diacritics (harakat)
 * 2. Normalizing alef forms: أ إ آ ٱ → ا
 * 3. Normalizing yaa forms: ى → ي
 */
export function normalizeArabic(text) {
    return text
        .replace(/[\u064B-\u065F\u0670]/g, '')
        .replace(/[أإآٱ]/g, 'ا')
        .replace(/ى/g, 'ي')
        .trim();
}
/**
 * Create a standard MCP tool response with compact JSON
 */
export function jsonResponse(data) {
    return {
        content: [{ type: 'text', text: JSON.stringify(data) }]
    };
}
/**
 * Create an MCP error response
 */
export function errorResponse(message) {
    return {
        content: [{ type: 'text', text: message }],
        isError: true
    };
}
//# sourceMappingURL=dbHelpers.js.map