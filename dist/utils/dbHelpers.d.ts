/**
 * Transform sql.js result rows into typed objects
 */
export declare function rowsToObjects<T>(columns: string[], values: any[][]): T[];
/**
 * Normalize Arabic text for search by:
 * 1. Removing diacritics (harakat)
 * 2. Normalizing alef forms: أ إ آ ٱ → ا
 * 3. Normalizing yaa forms: ى → ي
 */
export declare function normalizeArabic(text: string): string;
/**
 * Create a standard MCP tool response with compact JSON
 */
export declare function jsonResponse(data: unknown): {
    content: Array<{
        type: string;
        text: string;
    }>;
};
/**
 * Create an MCP error response
 */
export declare function errorResponse(message: string): {
    content: Array<{
        type: string;
        text: string;
    }>;
    isError: true;
};
//# sourceMappingURL=dbHelpers.d.ts.map