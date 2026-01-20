import initSqlJs, { Database as SqlJsDatabase } from 'sql.js';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { readFileSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Database connection
let SQL: any = null;
let db: SqlJsDatabase | null = null;

export async function getDatabase(): Promise<SqlJsDatabase> {
  if (!db) {
    if (!SQL) {
      SQL = await initSqlJs();
    }

    const dbPath = process.env.KALIMA_DB_PATH || join(__dirname, '../../../data/database/kalima.db');
    const buffer = readFileSync(dbPath);
    db = new SQL.Database(buffer);
  }
  return db as SqlJsDatabase;
}

export function closeDatabase(): void {
  if (db) {
    db.close();
    db = null;
  }
}

// Verse type
export interface Verse {
  surah_number: number;
  ayah_number: number;
  text: string;
}

// Surah type
export interface Surah {
  number: number;
  name: string;
}

// Claim type
export interface Claim {
  id: string;
  content: string;
  phase: string;
  pattern_id: string | null;
  note_file: string | null;
  created_at: string;
  updated_at: string;
}

// Pattern type
export interface Pattern {
  id: string;
  description: string;
  pattern_type: string;
  scope: string | null;
  phase: string;
  created_at: string;
  updated_at: string;
}

// Evidence type
export interface Evidence {
  id: string;
  claim_id: string;
  surah: number;
  ayah: number;
  notes: string | null;
  created_at: string;
}

// Dependency type
export interface Dependency {
  claim_id: string;
  depends_on_claim_id: string;
  dependency_type: string;
  created_at: string;
}
