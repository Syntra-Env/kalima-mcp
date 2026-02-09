// Shared database helpers used across tool modules

/**
 * Transform sql.js result rows into typed objects
 */
export function rowsToObjects<T>(columns: string[], values: any[][]): T[] {
  return values.map(row => {
    const obj: any = {};
    columns.forEach((col, idx) => {
      obj[col] = row[idx];
    });
    return obj as T;
  });
}

/**
 * Normalize Arabic text for search by:
 * 1. Removing diacritics (harakat)
 * 2. Normalizing alef forms: أ إ آ ٱ → ا
 * 3. Normalizing yaa forms: ى → ي
 */
export function normalizeArabic(text: string): string {
  return text
    .replace(/[\u064B-\u065F\u0670]/g, '')
    .replace(/[أإآٱ]/g, 'ا')
    .replace(/ى/g, 'ي')
    .trim();
}

/**
 * Create a standard MCP tool response with compact JSON
 */
export function jsonResponse(data: unknown): { content: Array<{ type: string; text: string }> } {
  return {
    content: [{ type: 'text', text: JSON.stringify(data) }]
  };
}

/**
 * Create an MCP error response
 */
export function errorResponse(message: string): { content: Array<{ type: string; text: string }>; isError: true } {
  return {
    content: [{ type: 'text', text: message }],
    isError: true
  };
}
