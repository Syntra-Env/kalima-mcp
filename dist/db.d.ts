import { Database as SqlJsDatabase } from 'sql.js';
export declare function getDatabase(): Promise<SqlJsDatabase>;
export declare function closeDatabase(): void;
export interface Verse {
    surah_number: number;
    ayah_number: number;
    text: string;
}
export interface Surah {
    number: number;
    name: string;
}
export interface Claim {
    id: string;
    content: string;
    phase: string;
    pattern_id: string | null;
    note_file: string | null;
    created_at: string;
    updated_at: string;
}
export interface Pattern {
    id: string;
    description: string;
    pattern_type: string;
    scope: string | null;
    phase: string;
    created_at: string;
    updated_at: string;
}
export interface Evidence {
    id: string;
    claim_id: string;
    surah: number;
    ayah: number;
    notes: string | null;
    created_at: string;
}
export interface Dependency {
    claim_id: string;
    depends_on_claim_id: string;
    dependency_type: string;
    created_at: string;
}
//# sourceMappingURL=db.d.ts.map