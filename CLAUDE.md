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
- Research phases: question → hypothesis → validation → active_verification → passive_verification
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
- `entries` — All research data lives here. Each has:
  - `id` (entry_N), `content`, `phase`, `category`, `confidence`, timestamps
  - `feature_id` (INTEGER, UNIQUE, nullable) — FK to `features`. When set, this entry is the canonical interpretation for that linguistic feature. UNIQUE constraint enforces one interpretation per feature.
  - Inline verification: `verse_total`, `verse_verified`, `verse_supports`, `verse_contradicts`, `verse_unclear`, `verse_current_index`, `verse_queue` (JSON), `verification_started_at`, `verification_updated_at`
- `entry_locations` — Many-to-many mapping of entries to Quranic locations, including verse evidence.
  - `id` (INTEGER PK), `entry_id` (TEXT FK -> entries), `surah` (INTEGER), `ayah_start` (INTEGER, nullable), `ayah_end` (INTEGER, nullable), `word_start` (INTEGER, nullable), `word_end` (INTEGER, nullable), `verification` (TEXT, nullable: supports/contradicts/unclear), `notes` (TEXT, nullable)
  - Whole surah: `(surah=N, rest NULL)`. Single verse: `(surah=N, ayah_start=M)`. Verse range: `(surah=N, ayah_start=M, ayah_end=K)`. Word range: add `word_start`/`word_end`.
  - Verse evidence is stored as locations with `verification` and `notes` set (no separate child entries needed).
- `words` — Quranic words. Each has `id`, `text`, `word_index`, `verse_surah`, `verse_ayah`, `normalized_text`. Verse text is composed by space-joining words ordered by `word_index`. Covering index: `idx_words_verse(verse_surah, verse_ayah, word_index)`
- `features` — Unified linguistic reference table (roots, lemmas, POS, morph features, dependency relations). Each has `feature_type`, `category`, `lookup_key`, `label_ar`, `label_en`, `frequency`. Serves as FK target for normalized `morphemes` columns and `entries.feature_id`
- `morphemes` — Morphological components of Quranic words. `word_id` FK -> `words(id)`. Feature columns are normalized as integer FKs to `features` (e.g. `root_id`, `lemma_id`, `pos_id`, `verb_form_id`, etc.). Non-feature columns: `id` (PK, mor-S-A-W-M format), `word_id`, `form`, `uthmani_form` (full Uthmani orthography including diacritics/tajweed marks — words can be reconstructed by concatenating `uthmani_form` of ordered morphemes)
- Surah names are stored as a Python constant in `src/utils/surahs.py` (not in a database table)
- **No `dependencies` table** — relationships between entries are discovered structurally through shared features (via `feature_id` → morphemes → words → verses) and shared locations (via `entry_locations`). This eliminates manual dependency wiring.

Entry categories: `quranic_research`, `ncu`, `methodology`, `historical`, `design`, `essay`, `personal`, `session`

Entry types:
- **Feature-anchored**: Has `feature_id` — canonical interpretation for a root, lemma, verb form, etc.
- **Location-anchored**: Has rows in `entry_locations` — verse-level evidence with optional `verification` status
- **Cross-cutting**: Neither `feature_id` nor locations — surah themes, multi-feature patterns, etc. Related entries discovered at query time through shared features and overlapping verse locations.

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
