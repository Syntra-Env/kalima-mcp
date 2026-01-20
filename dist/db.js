import initSqlJs from 'sql.js';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { readFileSync } from 'fs';
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
// Database connection
let SQL = null;
let db = null;
export async function getDatabase() {
    if (!db) {
        if (!SQL) {
            SQL = await initSqlJs();
        }
        const dbPath = process.env.KALIMA_DB_PATH || join(__dirname, '../../../data/database/kalima.db');
        const buffer = readFileSync(dbPath);
        db = new SQL.Database(buffer);
    }
    return db;
}
export function closeDatabase() {
    if (db) {
        db.close();
        db = null;
    }
}
//# sourceMappingURL=db.js.map