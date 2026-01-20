# Known Issues and Solutions

## ✅ FIXED: Database Path Issue
**Issue**: `save_insight` was saving to wrong path (`packages/data/` instead of root `data/`)
**Status**: Fixed by correcting path resolution in research.ts (4 levels up instead of 3)

## ✅ FIXED: Surah Names (2026-01-20)
**Issue**: `list_surahs` was returning surahs with empty `name` field
**Cause**: The `surahs` table had empty/NULL name column
**Solution**: Populated all 114 surah names using fix-database.js script
**Status**: All surahs now have proper transliterated names (Al-Fatihah, Al-Baqarah, etc.)

## ✅ FIXED: Arabic Verse Search (2026-01-20)
**Issue**: `search_verses` was returning empty results for Arabic queries like "الله"
**Root Cause**: Arabic text in database uses diacritics and alternative Unicode forms:
- Alef with hamza below (U+0671 ٱ) vs regular alef (U+0627 ا)
- Text includes diacritical marks (fatha, kasra, shadda, etc.)
**Solution**: Implemented Arabic text normalization in quran.ts:
- Strips diacritics from both search query and verse text
- Normalizes alef forms (أ إ آ ٱ → ا)
- Normalizes yaa forms (ى → ي)
**Status**: Search now works for both simple queries ("الله") and queries with diacritics ("ٱللَّهِ")

## Remaining Data Issues

### 1. get_claim_evidence Returns Empty
**Symptom**: Evidence queries return no results
**Cause**: The `claim_evidence` table is likely empty (no evidence records created yet)
**Impact**: Medium - evidence linking works but no data populated
**Solution**: Research claims were migrated from JSON but evidence links weren't created

**Query to check**:
```sql
SELECT COUNT(*) FROM claim_evidence;
```

**Fix**: Need migration script to:
1. Parse notes/evidence from existing claims
2. Create claim_evidence records
3. Link verses to claims

## Working Functions (All 10 MCP Tools)

✅ **list_surahs** - Returns all 114 surahs with names
✅ **get_verse** - Retrieves verses with Arabic text correctly
✅ **get_surah** - Gets complete chapters with all verses
✅ **search_verses** - Full-text search with Arabic normalization
✅ **search_claims** - Finds research claims by phase/pattern
✅ **save_insight** - Saves new claims to database
✅ **update_claim_phase** - Updates claim research phases
✅ **get_claim_evidence** - Gets evidence links (returns empty until migration)
✅ **list_patterns** - Returns morphological/semantic patterns
✅ **get_pattern_occurrences** - Gets verses using specific patterns

## Recommendations

### Short-term (Essential) ✅ COMPLETED
1. ✅ Fix save_insight database path (DONE)
2. ✅ Populate surah names (DONE - 2026-01-20)
3. ✅ Fix search_verses Arabic normalization (DONE - 2026-01-20)

### Medium-term (Important)
1. Create evidence migration script from existing claim notes
2. Optimize search_verses for large result sets (consider FTS5 for performance)
3. Add root-based and morphological pattern search

### Long-term (Enhancement)
1. Implement FTS5 for faster Arabic text search
2. Add more advanced search capabilities (root-based, POS patterns)
3. Create comprehensive database seeding/migration scripts
