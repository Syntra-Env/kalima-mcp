# Kalima Project Instructions

## Non-Negotiable Rules

1. **NEVER use traditional tafsir, translations, or external interpretations.** When presenting Quranic verses, show ONLY the Arabic text. If no interpretation exists in the Kalima database, say so explicitly — do not fill the gap with traditional or scholarly interpretations.

2. **NEVER translate Quranic Arabic into English.** Do not provide English renderings of verses. The user works directly with the Arabic text and derives meaning through the methodology below.

3. **Only present interpretations that exist in the Kalima database** (entries, patterns, evidence). If asked about a verse with no database entries, state that no verified interpretation exists yet rather than defaulting to conventional readings.

4. **Define Quranic terms using only the Quran itself.** External sources (hadith, biblical parallels, pre-Islamic poetry, traditional dictionaries, Lane's Lexicon) must not override internal Quranic consistency. Words are defined by their usage across ALL Quranic instances.

5. **Treat traditional interpretations as potentially wrong by default.** 1,400 years of scholarship relied on appeals to authority. If your response matches a traditional reading, flag it — this may indicate an unexamined assumption rather than correctness.

## Research Methodology

### Falsification-Based Validation
- Claims gain credibility through **survived falsification attempts**, not accumulation of confirming instances
- A single clear contradiction can invalidate a hypothesis
- Research phases: question → hypothesis → validation → verified / rejected
- Every claim requires Quranic textual evidence

### Concordance Verification
- Before claiming to understand a term, ALL instances in the Quran must be checked
- A word must maintain consistent meaning across all instances
- Use `search_by_linguistic_features` with root parameters to find all occurrences

### Self-Correction
- Previous claims can and should be overturned when evidence warrants it
- Intellectual honesty is a structural feature of this project

## Key Frameworks

### Organic Quranic Methodology
- The Quran is its own dictionary — terms illuminate each other through recursive definition
- Pay attention to prepositions (min vs fi, bi vs li), orthographic features, grammatical anomalies
- Recognize priming from biblical/traditional narratives as a cognitive bias to actively resist

### NCU (Nafs-Centric Universe)
- Each individual exists in a bespoke reality orchestrated by malaikah
- Quranic narratives should be traced from ONE character's perspective as the nafs in that NCU
- Other characters may be apparitions, malaikah orchestrations, or connections to other NCUs

## MCP Server

This project is an MCP (Model Context Protocol) server built with Python/FastMCP. The database is at `data/kalima.db` (or path in `KALIMA_DB_PATH` env var).

### Database schema

#### Compositional Quranic text (read-only reference)
- `word_instances` — Every word occurrence in the Quran (77,429 rows). Columns: `id`, `verse_surah`, `verse_ayah`, `word_index`, `word_type_id` (FK → word_types), `normalized_text`, `global_index`
- `word_types` — Unique word forms / "DNA" (28,725 rows). Columns: `id`. Text is reconstructed from atoms via `compose_word_text()`
- `word_type_morphemes` — Maps word types to their morpheme components. Columns: `word_type_id`, `morpheme_type_id` (FK → morpheme_types), `position`
- `morpheme_types` — Unique morpheme forms (25,705 rows). Feature columns are integer FKs to `features`: `root_id`, `lemma_id`, `pos_id`, `verb_form_id`, `voice_id`, `mood_id`, `aspect_id`, `person_id`, `number_id`, `gender_id`, `case_value_id`. Also: `id`, `uthmani_text`
- `morpheme_atoms` — Character-level decomposition of morphemes. Columns: `morpheme_type_id`, `position`, `base_letter`, `diacritics`. Words are reconstructed by joining atoms in order
- `features` — Unified linguistic reference table (31,118 rows). Columns: `id`, `feature_type`, `category`, `lookup_key`, `label_ar`, `label_en`, `frequency`. FK target for all morpheme feature columns
- `gold_standard` — Reference verse texts for validation (6,236 rows)
- Surah names are stored as a Python constant in `src/utils/surahs.py` (not in a database table)

**Text reconstruction chain**: word_instances → word_types → word_type_morphemes → morpheme_types → morpheme_atoms. Verse text = space-joined words, each word = concatenated `base_letter + diacritics` of its atoms in order.

#### Research entries
- `entries` — All research data. Columns:
  - `id` (TEXT PK, entry_N format), `content` (TEXT), `phase`, `category`, `confidence` (REAL)
  - **Unified anchoring**: `anchor_type` (root/lemma/morpheme/word_type/word_instance/surah/pos/segment_type), `anchor_ids` (single ID, comma-separated IDs, or surah:ayah pattern)
  - `verification` (supports/contradicts/unclear), `notes`
  - **Verification workflow**: `verse_queue` (JSON array), `verse_current_index` (INTEGER)
  - `last_activity` (ISO timestamp)
- **No `entry_locations` or `feature_id`** — replaced by unified anchoring. Relationships between entries are discovered structurally through shared features and overlapping verse locations.

Entry categories: `quranic_research`, `ncu`, `methodology`, `historical`, `design`, `essay`, `personal`, `session`

Entry anchoring types:
- **Feature-anchored**: `anchor_type` is root/lemma/pos/etc, `anchor_ids` points to feature IDs
- **Word-anchored**: `anchor_type` is word_type or word_instance, `anchor_ids` points to type IDs or surah:ayah patterns
- **Cross-cutting**: No anchors — surah themes, multi-feature patterns, etc.

### Install
```
pip install -e .
```

### Key directories
- `src/` — Python package (importable as `src`)
- `src/tools/` — Tool implementations (quran, research, linguistic, workflow, context)
- `src/utils/` — Shared helpers (arabic, short_id, features, units, surahs)
- `src/db.py` — SQLite connection manager (WAL mode, native sqlite3)
- `src/server.py` — FastMCP server entry point
