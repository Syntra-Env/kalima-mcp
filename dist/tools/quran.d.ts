import { Verse, Surah } from '../db.js';
export declare function getVerse(surah: number, ayah: number): Promise<Verse | null>;
export declare function getSurah(surah: number): Promise<{
    surah: Surah;
    verses: Verse[];
} | null>;
export declare function listSurahs(): Promise<Surah[]>;
export declare function searchVerses(query: string, limit?: number): Promise<Verse[]>;
//# sourceMappingURL=quran.d.ts.map