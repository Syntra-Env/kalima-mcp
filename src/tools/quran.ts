import { getDatabase, Verse, Surah } from '../db.js';

// Helper to transform sql.js results to typed objects
function rowsToObjects<T>(columns: string[], values: any[][]): T[] {
  return values.map(row => {
    const obj: any = {};
    columns.forEach((col, idx) => {
      obj[col] = row[idx];
    });
    return obj as T;
  });
}

export async function getVerse(surah: number, ayah: number): Promise<Verse | null> {
  const db = await getDatabase();

  const result = db.exec(
    `SELECT v.surah_number, v.ayah_number, vt.text
     FROM verses v
     JOIN verse_texts vt ON v.surah_number = vt.surah_number AND v.ayah_number = vt.ayah_number
     WHERE v.surah_number = ? AND v.ayah_number = ?`,
    [surah, ayah]
  );

  if (!result.length || !result[0].values.length) {
    return null;
  }

  const verses = rowsToObjects<Verse>(result[0].columns, result[0].values);
  return verses[0];
}

export async function getSurah(surah: number): Promise<{ surah: Surah; verses: Verse[] } | null> {
  const db = await getDatabase();

  // Get surah info
  const surahResult = db.exec(
    'SELECT number, name FROM surahs WHERE number = ?',
    [surah]
  );

  if (!surahResult.length || !surahResult[0].values.length) {
    return null;
  }

  const surahs = rowsToObjects<Surah>(surahResult[0].columns, surahResult[0].values);
  const surahInfo = surahs[0];

  // Get all verses in the surah
  const versesResult = db.exec(
    `SELECT v.surah_number, v.ayah_number, vt.text
     FROM verses v
     JOIN verse_texts vt ON v.surah_number = vt.surah_number AND v.ayah_number = vt.ayah_number
     WHERE v.surah_number = ?
     ORDER BY v.ayah_number ASC`,
    [surah]
  );

  const verses = versesResult.length && versesResult[0].values.length
    ? rowsToObjects<Verse>(versesResult[0].columns, versesResult[0].values)
    : [];

  return {
    surah: surahInfo,
    verses
  };
}

export async function listSurahs(): Promise<Surah[]> {
  const db = await getDatabase();

  const result = db.exec(
    'SELECT number, name FROM surahs ORDER BY number ASC'
  );

  if (!result.length || !result[0].values.length) {
    return [];
  }

  return rowsToObjects<Surah>(result[0].columns, result[0].values);
}

// Normalize Arabic text for search by:
// 1. Removing diacritics (harakat): َ ً ُ ٌ ِ ٍ ّ ْ
// 2. Normalizing alef forms: أ إ آ ٱ → ا
// 3. Normalizing yaa forms: ى → ي
function normalizeArabic(text: string): string {
  return text
    // Remove Arabic diacritics
    .replace(/[\u064B-\u065F\u0670]/g, '')
    // Normalize alef forms to basic alef
    .replace(/[أإآٱ]/g, 'ا')
    // Normalize yaa forms
    .replace(/ى/g, 'ي')
    .trim();
}

export async function searchVerses(query: string, limit: number = 20): Promise<Verse[]> {
  const db = await getDatabase();

  // Normalize the search query
  const normalizedQuery = normalizeArabic(query);

  // Since SQLite doesn't have built-in Arabic normalization,
  // we need to fetch all verses and filter in JavaScript
  const result = db.exec(
    `SELECT v.surah_number, v.ayah_number, vt.text
     FROM verses v
     JOIN verse_texts vt ON v.surah_number = vt.surah_number AND v.ayah_number = vt.ayah_number
     ORDER BY v.surah_number ASC, v.ayah_number ASC`
  );

  if (!result.length || !result[0].values.length) {
    return [];
  }

  const allVerses = rowsToObjects<Verse>(result[0].columns, result[0].values);

  // Filter verses by normalized text
  const matchedVerses = allVerses.filter(verse =>
    normalizeArabic(verse.text).includes(normalizedQuery)
  );

  // Return limited results
  return matchedVerses.slice(0, limit);
}
