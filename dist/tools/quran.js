import { getDatabase } from '../db.js';
import { rowsToObjects, normalizeArabic } from '../utils/dbHelpers.js';
export async function getVerse(surah, ayah) {
    const db = await getDatabase();
    const result = db.exec(`SELECT v.surah_number, v.ayah_number, vt.text
     FROM verses v
     JOIN verse_texts vt ON v.surah_number = vt.surah_number AND v.ayah_number = vt.ayah_number
     WHERE v.surah_number = ? AND v.ayah_number = ?`, [surah, ayah]);
    if (!result.length || !result[0].values.length) {
        return null;
    }
    const verses = rowsToObjects(result[0].columns, result[0].values);
    return verses[0];
}
export async function getSurah(surah) {
    const db = await getDatabase();
    // Get surah info
    const surahResult = db.exec('SELECT number, name FROM surahs WHERE number = ?', [surah]);
    if (!surahResult.length || !surahResult[0].values.length) {
        return null;
    }
    const surahs = rowsToObjects(surahResult[0].columns, surahResult[0].values);
    const surahInfo = surahs[0];
    // Get all verses in the surah
    const versesResult = db.exec(`SELECT v.surah_number, v.ayah_number, vt.text
     FROM verses v
     JOIN verse_texts vt ON v.surah_number = vt.surah_number AND v.ayah_number = vt.ayah_number
     WHERE v.surah_number = ?
     ORDER BY v.ayah_number ASC`, [surah]);
    const verses = versesResult.length && versesResult[0].values.length
        ? rowsToObjects(versesResult[0].columns, versesResult[0].values)
        : [];
    return {
        surah: surahInfo,
        verses
    };
}
export async function listSurahs() {
    const db = await getDatabase();
    const result = db.exec('SELECT number, name FROM surahs ORDER BY number ASC');
    if (!result.length || !result[0].values.length) {
        return [];
    }
    return rowsToObjects(result[0].columns, result[0].values);
}
export async function searchVerses(query, limit = 20) {
    const db = await getDatabase();
    const normalizedQuery = normalizeArabic(query);
    // Query the pre-normalized column directly in SQL
    const result = db.exec(`SELECT surah_number, ayah_number, text
     FROM verse_texts
     WHERE normalized_text LIKE ?
     ORDER BY surah_number ASC, ayah_number ASC
     LIMIT ?`, [`%${normalizedQuery}%`, limit]);
    if (!result.length || !result[0].values.length) {
        return [];
    }
    return rowsToObjects(result[0].columns, result[0].values);
}
//# sourceMappingURL=quran.js.map