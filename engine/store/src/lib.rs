//! StorageBackend implementation using SQLite.
//! Normalized schema for surahs/verses/tokens/segments/annotations/connections,
//! plus JSON payloads for SegmentView as a denormalized view.

use async_trait::async_trait;
use common::{parse_verse_ref, EngineError, EngineResult, SearchHit, Segment, SegmentView, StorageBackend};
use sqlx::{sqlite::SqlitePoolOptions, Pool, Row, Sqlite};

pub struct SqliteStorage {
    pool: Pool<Sqlite>,
}

#[derive(Clone, serde::Serialize, serde::Deserialize)]
pub struct SurahSummary {
    pub number: i64,
    pub name: String,
    pub ayah_count: i64,
}

impl SqliteStorage {
    pub fn pool(&self) -> &Pool<Sqlite> {
        &self.pool
    }
    pub async fn connect(path: &str) -> EngineResult<Self> {
        let uri = if path.starts_with("sqlite:") {
            path.to_string()
        } else {
            let p = std::path::Path::new(path);
            let abs = if p.is_absolute() {
                p.to_path_buf()
            } else {
                std::env::current_dir()
                    .unwrap_or_else(|_| std::path::PathBuf::from("."))
                    .join(p)
            };
            let mut s = abs
                .to_string_lossy()
                .replace('\\', "/");
            // Strip Windows UNC prefix if present
            if s.starts_with("//?/") {
                s = s[4..].to_string();
            }
            // Ensure no leading slash before drive letter on Windows
            if s.len() > 1 && s.chars().nth(1) == Some(':') && s.starts_with('/') {
                s = s[1..].to_string();
            }
            format!("sqlite:///{}?mode=rwc", s)
        };

        let pool = SqlitePoolOptions::new()
            .max_connections(5)
            .connect(&uri)
            .await
            .map_err(|e| EngineError::Storage(e.to_string()))?;

        // Run embedded migration (idempotent)
        sqlx::query(MIGRATION_INIT)
            .execute(&pool)
            .await
            .map_err(|e| EngineError::Storage(e.to_string()))?;

        Ok(Self { pool })
    }

    pub async fn upsert_segment(&self, doc: &SegmentView) -> EngineResult<()> {
        // Upsert surah and verse metadata
        let (surah_num, ayah_num) = parse_verse_ref(&doc.verse_ref)?;
        sqlx::query(
            r#"INSERT OR IGNORE INTO surahs (number, name) VALUES (?1, ?2)"#,
        )
        .bind(surah_num as i64)
        .bind("") // name unknown in current payload
        .execute(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;

        sqlx::query(
            r#"
            INSERT INTO verses (surah_number, ayah_number)
            VALUES (?1, ?2)
            ON CONFLICT(surah_number, ayah_number) DO NOTHING;
            "#,
        )
        .bind(surah_num as i64)
        .bind(ayah_num as i64)
        .execute(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;

        // Note: verse text is managed by the caller (ingest.rs) to avoid overwriting
        // with token text. The ingest process stores complete verse text separately.

        // Upsert token row
        let token_uid = format!("{}:{}:{}", surah_num, ayah_num, doc.token_index);
        sqlx::query(
            r#"
            INSERT INTO tokens (id, verse_surah, verse_ayah, token_index, text)
            VALUES (?1, ?2, ?3, ?4, ?5)
            ON CONFLICT(id) DO UPDATE SET text=excluded.text;
            "#,
        )
        .bind(&token_uid)
        .bind(surah_num as i64)
        .bind(ayah_num as i64)
        .bind(doc.token_index as i64)
        .bind(&doc.text)
        .execute(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;

        // Upsert segments normalized
        for seg in &doc.segments {
            sqlx::query(
                r#"
                INSERT INTO segments (
                    id, token_id, type, form, root, lemma, pattern, pos, verb_form,
                    voice, mood, aspect, person, number, gender, case_value, dependency_rel, role, derived_noun_type, state
                )
                VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, ?18, ?19, ?20)
                ON CONFLICT(id) DO UPDATE SET
                    token_id=excluded.token_id,
                    type=excluded.type,
                    form=excluded.form,
                    root=excluded.root,
                    lemma=excluded.lemma,
                    pattern=excluded.pattern,
                    pos=excluded.pos,
                    verb_form=excluded.verb_form,
                    voice=excluded.voice,
                    mood=excluded.mood,
                    aspect=excluded.aspect,
                    person=excluded.person,
                    number=excluded.number,
                    gender=excluded.gender,
                    case_value=excluded.case_value,
                    dependency_rel=excluded.dependency_rel,
                    role=excluded.role,
                    derived_noun_type=excluded.derived_noun_type,
                    state=excluded.state;
                "#,
            )
            .bind(&seg.id)
            .bind(&token_uid)
            .bind(&seg.r#type)
            .bind(&seg.form)
            .bind(seg.root.as_ref())
            .bind(seg.lemma.as_ref())
            .bind(seg.pattern.as_ref())
            .bind(seg.pos.as_ref())
            .bind(seg.verb_form.as_ref())
            .bind(seg.voice.as_ref())
            .bind(seg.mood.as_ref())
            .bind(seg.aspect.as_ref())
            .bind(seg.person.as_ref())
            .bind(seg.number.as_ref())
            .bind(seg.gender.as_ref())
            .bind(seg.case_.as_ref())
            .bind(seg.dependency_rel.as_ref())
            .bind(seg.role.as_ref())
            .bind(seg.derived_noun_type.as_ref())
            .bind(seg.state.as_ref())
            .execute(&self.pool)
            .await
            .map_err(|e| EngineError::Storage(e.to_string()))?;
        }

        Ok(())
    }

    pub async fn upsert_annotation(
        &self,
        annotation: &common::Annotation,
    ) -> EngineResult<()> {
        sqlx::query(
            r#"
            INSERT INTO annotations (id, target_id, layer, payload)
            VALUES (?1, ?2, ?3, ?4)
            ON CONFLICT(id) DO UPDATE SET
              target_id=excluded.target_id,
              layer=excluded.layer,
              payload=excluded.payload;
            "#,
        )
        .bind(&annotation.id)
        .bind(&annotation.target_id)
        .bind(&annotation.layer)
        .bind(&annotation.payload)
        .execute(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;
        Ok(())
    }

    pub async fn list_annotations(
        &self,
        target_filter: Option<&str>,
    ) -> EngineResult<Vec<common::Annotation>> {
        let rows = if let Some(target) = target_filter {
            sqlx::query(
                r#"SELECT id, target_id, layer, payload as "payload: serde_json::Value"
                   FROM annotations WHERE target_id = ?1
                   ORDER BY created_at DESC"#,
            )
            .bind(target)
            .fetch_all(&self.pool)
            .await
        } else {
            sqlx::query(
                r#"SELECT id, target_id, layer, payload as "payload: serde_json::Value"
                   FROM annotations
                   ORDER BY created_at DESC"#,
            )
            .fetch_all(&self.pool)
            .await
        }
        .map_err(|e| EngineError::Storage(e.to_string()))?;

        let mut out = Vec::with_capacity(rows.len());
        for row in rows {
            out.push(common::Annotation {
                id: row.try_get::<String, _>(0).map_err(|e| EngineError::Storage(e.to_string()))?,
                target_id: row.try_get::<String, _>(1).map_err(|e| EngineError::Storage(e.to_string()))?,
                layer: row.try_get::<String, _>(2).map_err(|e| EngineError::Storage(e.to_string()))?,
                payload: row.try_get::<serde_json::Value, _>(3).map_err(|e| EngineError::Storage(e.to_string()))?,
            });
        }
        Ok(out)
    }

    pub async fn delete_annotation(&self, id: &str) -> EngineResult<()> {
        sqlx::query(r#"DELETE FROM annotations WHERE id = ?1"#)
            .bind(id)
            .execute(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;
        Ok(())
    }

    pub async fn upsert_connection(
        self: &SqliteStorage,
        conn: &ConnectionRecord,
    ) -> EngineResult<()> {
        sqlx::query(
            r#"
            INSERT INTO connections (id, from_token, to_token, layer, meta)
            VALUES (?1, ?2, ?3, ?4, ?5)
            ON CONFLICT(id) DO UPDATE SET
              from_token=excluded.from_token,
              to_token=excluded.to_token,
              layer=excluded.layer,
              meta=excluded.meta;
            "#,
        )
        .bind(&conn.id)
        .bind(&conn.from_token)
        .bind(&conn.to_token)
        .bind(&conn.layer)
        .bind(&conn.meta)
        .execute(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;
        Ok(())
    }

    pub async fn list_connections_for_verse(
        &self,
        surah: i64,
        ayah: i64,
    ) -> EngineResult<Vec<ConnectionRecord>> {
        let rows = sqlx::query(
            r#"
            SELECT c.id, c.from_token, c.to_token, c.layer, c.meta as "meta: serde_json::Value"
            FROM connections c
            JOIN tokens tf ON c.from_token = tf.id
            WHERE tf.verse_surah = ?1 AND tf.verse_ayah = ?2
            "#,
        )
        .bind(surah)
        .bind(ayah)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;

        Ok(rows
            .into_iter()
            .map(|r| ConnectionRecord {
                id: r.try_get("id").unwrap_or_default(),
                from_token: r.try_get("from_token").unwrap_or_default(),
                to_token: r.try_get("to_token").unwrap_or_default(),
                layer: r.try_get("layer").unwrap_or_default(),
                meta: r.try_get("meta").unwrap_or(serde_json::json!({})),
            })
            .collect())
    }

    pub async fn delete_connection(&self, id: &str) -> EngineResult<()> {
        sqlx::query(r#"DELETE FROM connections WHERE id = ?1"#)
            .bind(id)
            .execute(&self.pool)
            .await
            .map_err(|e| EngineError::Storage(e.to_string()))?;
        Ok(())
    }

    pub async fn list_unique_roots(&self) -> EngineResult<Vec<String>> {
        let rows = sqlx::query(
            r#"SELECT DISTINCT root FROM segments WHERE root IS NOT NULL ORDER BY root"#
        )
        .fetch_all(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;

        Ok(rows
            .into_iter()
            .filter_map(|r| r.try_get::<String, _>(0).ok())
            .collect())
    }

    pub async fn list_unique_patterns(&self) -> EngineResult<Vec<String>> {
        let rows = sqlx::query(
            r#"SELECT DISTINCT pattern FROM segments WHERE pattern IS NOT NULL ORDER BY pattern"#
        )
        .fetch_all(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;

        Ok(rows
            .into_iter()
            .filter_map(|r| r.try_get::<String, _>(0).ok())
            .collect())
    }

    pub async fn list_unique_pos(&self) -> EngineResult<Vec<String>> {
        let rows = sqlx::query(
            r#"SELECT DISTINCT pos FROM segments WHERE pos IS NOT NULL ORDER BY pos"#
        )
        .fetch_all(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;

        Ok(rows
            .into_iter()
            .filter_map(|r| r.try_get::<String, _>(0).ok())
            .collect())
    }

    pub async fn list_surahs(&self) -> EngineResult<Vec<SurahSummary>> {
        let rows = sqlx::query(
            r#"
            SELECT s.number, s.name, COUNT(DISTINCT v.ayah_number) as ayah_count
            FROM surahs s
            LEFT JOIN verses v ON s.number = v.surah_number
            GROUP BY s.number, s.name
            ORDER BY s.number
            "#
        )
        .fetch_all(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;

        Ok(rows
            .into_iter()
            .map(|r| SurahSummary {
                number: r.try_get("number").unwrap_or(0),
                name: r.try_get("name").unwrap_or_default(),
                ayah_count: r.try_get("ayah_count").unwrap_or(0),
            })
            .collect())
    }

    pub async fn get_surah_verses(&self, surah_number: i64) -> EngineResult<Vec<serde_json::Value>> {
        // Get surah name
        let surah_name: String = sqlx::query_scalar(
            r#"SELECT name FROM surahs WHERE number = ?1"#
        )
        .bind(surah_number)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?
        .unwrap_or_else(|| "Unknown".to_string());

        // Get all verses for this surah with their text
        let rows = sqlx::query(
            r#"
            SELECT v.ayah_number, vt.text
            FROM verses v
            LEFT JOIN verse_texts vt ON v.surah_number = vt.surah_number AND v.ayah_number = vt.ayah_number
            WHERE v.surah_number = ?1
            ORDER BY v.ayah_number
            "#
        )
        .bind(surah_number)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;

        Ok(rows
            .into_iter()
            .map(|r| {
                serde_json::json!({
                    "surah_name": surah_name,
                    "ayah": r.try_get::<i64, _>("ayah_number").unwrap_or(0),
                    "text": r.try_get::<Option<String>, _>("text").unwrap_or(None).unwrap_or_default()
                })
            })
            .collect())
    }

    pub async fn get_verse(&self, surah: i64, ayah: i64) -> EngineResult<Option<serde_json::Value>> {
        let text: Option<String> = sqlx::query_scalar(
            r#"SELECT text FROM verse_texts WHERE surah_number = ?1 AND ayah_number = ?2"#
        )
        .bind(surah)
        .bind(ayah)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;

        if text.is_none() {
            return Ok(None);
        }

        let surah_name: String = sqlx::query_scalar(
            r#"SELECT name FROM surahs WHERE number = ?1"#
        )
        .bind(surah)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?
        .unwrap_or_else(|| "Unknown".to_string());

        // Get tokens with their morphological segments
        let rows = sqlx::query(
            r#"
            SELECT t.id as token_id, t.token_index, t.text as token_text,
                   s.id, s.type, s.form, s.root, s.lemma, s.pattern, s.pos,
                   s.verb_form, s.voice, s.mood, s.aspect, s.person,
                   s.number, s.gender, s.case_value, s.dependency_rel
            FROM tokens t
            LEFT JOIN segments s ON s.token_id = t.id
            WHERE t.verse_surah = ?1 AND t.verse_ayah = ?2
            ORDER BY t.token_index, s.id
            "#
        )
        .bind(surah)
        .bind(ayah)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;

        // Group segments by token
        use std::collections::HashMap;
        let mut tokens_map: HashMap<i64, serde_json::Value> = HashMap::new();

        for row in rows {
            let token_index: i64 = row.try_get("token_index").unwrap_or(0);
            let token_text: String = row.try_get("token_text").unwrap_or_default();

            let token = tokens_map.entry(token_index).or_insert_with(|| {
                serde_json::json!({
                    "index": token_index,
                    "text": token_text,
                    "segments": []
                })
            });

            // Add segment if it exists
            if let Ok(seg_id) = row.try_get::<String, _>("id") {
                if !seg_id.is_empty() {
                    let segment = serde_json::json!({
                        "id": seg_id,
                        "type": row.try_get::<String, _>("type").unwrap_or_default(),
                        "form": row.try_get::<String, _>("form").unwrap_or_default(),
                        "root": row.try_get::<Option<String>, _>("root").unwrap_or(None),
                        "lemma": row.try_get::<Option<String>, _>("lemma").unwrap_or(None),
                        "pattern": row.try_get::<Option<String>, _>("pattern").unwrap_or(None),
                        "pos": row.try_get::<Option<String>, _>("pos").unwrap_or(None),
                        "verb_form": row.try_get::<Option<String>, _>("verb_form").unwrap_or(None),
                        "voice": row.try_get::<Option<String>, _>("voice").unwrap_or(None),
                        "mood": row.try_get::<Option<String>, _>("mood").unwrap_or(None),
                        "aspect": row.try_get::<Option<String>, _>("aspect").unwrap_or(None),
                        "person": row.try_get::<Option<String>, _>("person").unwrap_or(None),
                        "number": row.try_get::<Option<String>, _>("number").unwrap_or(None),
                        "gender": row.try_get::<Option<String>, _>("gender").unwrap_or(None),
                        "case": row.try_get::<Option<String>, _>("case_value").unwrap_or(None),
                        "dependency_rel": row.try_get::<Option<String>, _>("dependency_rel").unwrap_or(None),
                    });

                    if let Some(segments) = token.get_mut("segments").and_then(|s| s.as_array_mut()) {
                        segments.push(segment);
                    }
                }
            }
        }

        // Convert to sorted array
        let mut tokens: Vec<_> = tokens_map.into_iter().collect();
        tokens.sort_by_key(|(idx, _)| *idx);
        let tokens_array: Vec<_> = tokens.into_iter().map(|(_, token)| token).collect();

        // Prefer the stored verse text when present; otherwise fall back to the longest token text.
        let verse_text = text
            .clone()
            .filter(|t| !t.is_empty())
            .or_else(|| {
                tokens_array
                    .iter()
                    .filter_map(|t| t.get("text").and_then(|v| v.as_str()))
                    .max_by_key(|s| s.len())
                    .map(|s| s.to_string())
            })
            .unwrap_or_default();

        Ok(Some(serde_json::json!({
            "surah": {
                "number": surah,
                "name": surah_name
            },
            "ayah": ayah,
            "text": verse_text,
            "tokens": tokens_array
        })))
    }

    pub async fn get_verse_by_index(&self, index: i64) -> EngineResult<Option<serde_json::Value>> {
        // Get verse by absolute index (row number)
        let row: Option<(i64, i64)> = sqlx::query_as(
            r#"
            SELECT surah_number, ayah_number 
            FROM verses 
            ORDER BY surah_number, ayah_number 
            LIMIT 1 OFFSET ?1
            "#
        )
        .bind(index)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;

        if let Some((surah, ayah)) = row {
            self.get_verse(surah, ayah).await
        } else {
            Ok(None)
        }
    }

    pub async fn list_verses(&self, start: i64, limit: i64) -> EngineResult<Vec<serde_json::Value>> {
        let rows = sqlx::query(
            r#"
            SELECT v.surah_number, v.ayah_number, vt.text, s.name as surah_name
            FROM verses v
            LEFT JOIN verse_texts vt ON v.surah_number = vt.surah_number AND v.ayah_number = vt.ayah_number
            LEFT JOIN surahs s ON v.surah_number = s.number
            ORDER BY v.surah_number, v.ayah_number
            LIMIT ?1 OFFSET ?2
            "#
        )
        .bind(limit)
        .bind(start)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;

        Ok(rows
            .into_iter()
            .map(|r| {
                serde_json::json!({
                    "surah": {
                        "number": r.try_get::<i64, _>("surah_number").unwrap_or(0),
                        "name": r.try_get::<String, _>("surah_name").unwrap_or_default()
                    },
                    "ayah": r.try_get::<i64, _>("ayah_number").unwrap_or(0),
                    "text": r.try_get::<Option<String>, _>("text").unwrap_or(None).unwrap_or_default(),
                    "tokens": []
                })
            })
            .collect())
    }

    pub async fn count_verses(&self) -> EngineResult<i64> {
        let count: i64 = sqlx::query_scalar(r#"SELECT COUNT(*) FROM verses"#)
            .fetch_one(&self.pool)
            .await
            .map_err(|e| EngineError::Storage(e.to_string()))?;
        Ok(count)
    }

    pub async fn get_verse_segments(&self, surah: i64, ayah: i64) -> EngineResult<Vec<serde_json::Value>> {
        let rows = sqlx::query(
            r#"
            SELECT s.id, s.type, s.form, s.root, s.lemma, s.pattern, s.pos,
                   s.verb_form, s.voice, s.mood, s.aspect, s.person,
                   s.number, s.gender, s.case_value, s.dependency_rel,
                   t.token_index, t.text as token_text
            FROM segments s
            JOIN tokens t ON s.token_id = t.id
            WHERE t.verse_surah = ?1 AND t.verse_ayah = ?2
            ORDER BY t.token_index
            "#
        )
        .bind(surah)
        .bind(ayah)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;

        Ok(rows
            .into_iter()
            .map(|r| {
                serde_json::json!({
                    "id": r.try_get::<String, _>("id").unwrap_or_default(),
                    "type": r.try_get::<String, _>("type").unwrap_or_default(),
                    "form": r.try_get::<String, _>("form").unwrap_or_default(),
                    "root": r.try_get::<Option<String>, _>("root").unwrap_or(None),
                    "lemma": r.try_get::<Option<String>, _>("lemma").unwrap_or(None),
                    "pattern": r.try_get::<Option<String>, _>("pattern").unwrap_or(None),
                    "pos": r.try_get::<Option<String>, _>("pos").unwrap_or(None),
                    "verb_form": r.try_get::<Option<String>, _>("verb_form").unwrap_or(None),
                    "voice": r.try_get::<Option<String>, _>("voice").unwrap_or(None),
                    "mood": r.try_get::<Option<String>, _>("mood").unwrap_or(None),
                    "aspect": r.try_get::<Option<String>, _>("aspect").unwrap_or(None),
                    "person": r.try_get::<Option<String>, _>("person").unwrap_or(None),
                    "number": r.try_get::<Option<String>, _>("number").unwrap_or(None),
                    "gender": r.try_get::<Option<String>, _>("gender").unwrap_or(None),
                    "case": r.try_get::<Option<String>, _>("case_value").unwrap_or(None),
                    "dependency_rel": r.try_get::<Option<String>, _>("dependency_rel").unwrap_or(None),
                    "token_index": r.try_get::<i64, _>("token_index").unwrap_or(0),
                    "word_index": r.try_get::<i64, _>("token_index").unwrap_or(0) + 1,
                    // Prefer the segment form for morphology display; keep token text separately for context.
                    "text": r.try_get::<String, _>("form").unwrap_or_default(),
                    "token_text": r.try_get::<String, _>("token_text").unwrap_or_default()
                })
            })
            .collect())
    }

    // Research data methods
    pub async fn get_verse_metadata(&self, verse_ref: &str, field: &str) -> EngineResult<Vec<serde_json::Value>> {
        let row = sqlx::query(&format!(
            r#"SELECT {} as "data: serde_json::Value" FROM verse_metadata WHERE verse_ref = ?1"#,
            field
        ))
        .bind(verse_ref)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;

        if let Some(row) = row {
            if let Ok(data) = row.try_get::<Option<serde_json::Value>, _>("data") {
                if let Some(arr) = data.and_then(|v| v.as_array().cloned()) {
                    return Ok(arr);
                }
            }
        }
        Ok(vec![])
    }

    pub async fn set_verse_metadata(&self, verse_ref: &str, field: &str, data: &serde_json::Value) -> EngineResult<()> {
        let sql = match field {
            "pronouns" => r#"INSERT INTO verse_metadata (verse_ref, pronouns) VALUES (?1, ?2)
                ON CONFLICT(verse_ref) DO UPDATE SET pronouns=excluded.pronouns"#,
            "hypotheses" => r#"INSERT INTO verse_metadata (verse_ref, hypotheses) VALUES (?1, ?2)
                ON CONFLICT(verse_ref) DO UPDATE SET hypotheses=excluded.hypotheses"#,
            "translations" => r#"INSERT INTO verse_metadata (verse_ref, translations) VALUES (?1, ?2)
                ON CONFLICT(verse_ref) DO UPDATE SET translations=excluded.translations"#,
            _ => return Err(EngineError::Invalid(format!("Unknown metadata field: {}", field))),
        };

        sqlx::query(sql)
            .bind(verse_ref)
            .bind(data)
            .execute(&self.pool)
            .await
            .map_err(|e| EngineError::Storage(e.to_string()))?;
        Ok(())
    }

    pub async fn get_research_data(&self, key: &str) -> EngineResult<Option<serde_json::Value>> {
        let row = sqlx::query(
            r#"SELECT value as "value: serde_json::Value" FROM research_data WHERE key = ?1"#
        )
        .bind(key)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;

        Ok(row.and_then(|r| r.try_get("value").ok()))
    }

    pub async fn set_research_data(&self, key: &str, value: &serde_json::Value) -> EngineResult<()> {
        sqlx::query(
            r#"INSERT INTO research_data (key, value, updated_at) VALUES (?1, ?2, CURRENT_TIMESTAMP)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP"#
        )
        .bind(key)
        .bind(value)
        .execute(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;
        Ok(())
    }

    pub async fn count_annotations(&self) -> EngineResult<i64> {
        let count: i64 = sqlx::query_scalar(r#"SELECT COUNT(*) FROM annotations"#)
            .fetch_one(&self.pool)
            .await
            .map_err(|e| EngineError::Storage(e.to_string()))?;
        Ok(count)
    }

    pub async fn count_verses_with_tokens(&self) -> EngineResult<i64> {
        let count: i64 = sqlx::query_scalar(
            r#"SELECT COUNT(DISTINCT verse_surah || ':' || verse_ayah) FROM tokens"#
        )
        .fetch_one(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;
        Ok(count)
    }

    pub async fn get_all_verse_texts(&self, limit: usize) -> EngineResult<Vec<(String, String)>> {
        let rows = sqlx::query(
            r#"
            SELECT surah_number, ayah_number, text
            FROM verse_texts
            WHERE text IS NOT NULL AND text != ''
            ORDER BY surah_number, ayah_number
            LIMIT ?1
            "#
        )
        .bind(limit as i64)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;

        Ok(rows
            .into_iter()
            .filter_map(|r| {
                let surah: i64 = r.try_get("surah_number").ok()?;
                let ayah: i64 = r.try_get("ayah_number").ok()?;
                let text: String = r.try_get("text").ok()?;
                Some((format!("{}:{}", surah, ayah), text))
            })
            .collect())
    }
}

#[derive(Clone, serde::Serialize, serde::Deserialize)]
pub struct ConnectionRecord {
    pub id: String,
    pub from_token: String,
    pub to_token: String,
    pub layer: String,
    pub meta: serde_json::Value,
}

#[async_trait]
impl StorageBackend for SqliteStorage {
    async fn get_segment(&self, id: &str) -> EngineResult<Option<SegmentView>> {
        // Hydrate from normalized tables
        let token_row = sqlx::query(
            r#"SELECT verse_surah, verse_ayah, token_index, text FROM tokens WHERE id = ?1"#,
        )
        .bind(id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;

        let Some(token) = token_row else { return Ok(None); };
        let surah: i64 = token.try_get("verse_surah").map_err(|e| EngineError::Storage(e.to_string()))?;
        let ayah: i64 = token.try_get("verse_ayah").map_err(|e| EngineError::Storage(e.to_string()))?;
        let token_index: i64 = token.try_get("token_index").map_err(|e| EngineError::Storage(e.to_string()))?;
        let text: String = token.try_get("text").map_err(|e| EngineError::Storage(e.to_string()))?;

        let seg_rows = sqlx::query(
            r#"SELECT id, type, form, root, lemma, pattern, pos, verb_form, voice, mood, aspect, person, number, gender, case_value, dependency_rel, role, derived_noun_type, state
                FROM segments WHERE token_id = ?1"#,
        )
        .bind(id)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| EngineError::Storage(e.to_string()))?;

        let mut segments = Vec::with_capacity(seg_rows.len());
        for r in seg_rows {
            segments.push(Segment {
                id: r.try_get("id").map_err(|e| EngineError::Storage(e.to_string()))?,
                r#type: r.try_get::<String, _>("type").unwrap_or_default(),
                form: r.try_get::<String, _>("form").unwrap_or_default(),
                root: r.try_get::<Option<String>, _>("root").unwrap_or(None),
                lemma: r.try_get::<Option<String>, _>("lemma").unwrap_or(None),
                pattern: r.try_get::<Option<String>, _>("pattern").unwrap_or(None),
                pos: r.try_get::<Option<String>, _>("pos").unwrap_or(None),
                verb_form: r.try_get::<Option<String>, _>("verb_form").unwrap_or(None),
                voice: r.try_get::<Option<String>, _>("voice").unwrap_or(None),
                mood: r.try_get::<Option<String>, _>("mood").unwrap_or(None),
                aspect: r.try_get::<Option<String>, _>("aspect").unwrap_or(None),
                person: r.try_get::<Option<String>, _>("person").unwrap_or(None),
                number: r.try_get::<Option<String>, _>("number").unwrap_or(None),
                gender: r.try_get::<Option<String>, _>("gender").unwrap_or(None),
                case_: r.try_get::<Option<String>, _>("case_value").unwrap_or(None),
                dependency_rel: r.try_get::<Option<String>, _>("dependency_rel").unwrap_or(None),
                role: r.try_get::<Option<String>, _>("role").unwrap_or(None),
                derived_noun_type: r.try_get::<Option<String>, _>("derived_noun_type").unwrap_or(None),
                state: r.try_get::<Option<String>, _>("state").unwrap_or(None),
            });
        }

        let verse_ref = format!("{}:{}", surah, ayah);
        Ok(Some(SegmentView {
            id: id.to_string(),
            verse_ref,
            token_index: token_index as usize,
            text,
            segments,
            annotations: vec![],
        }))
    }

    async fn hydrate_segments(&self, ids: &[SearchHit]) -> EngineResult<Vec<SegmentView>> {
        // Fetch by id list; sqlite doesn't support array binds easily without temp table,
        // so fetch individually for now.
        let mut out = Vec::new();
        for hit in ids {
            if let Some(doc) = self.get_segment(&hit.id).await? {
                out.push(doc);
            }
        }
        Ok(out)
    }
}

// Single-file migration to bootstrap SQLite schema.
const MIGRATION_INIT: &str = r#"
CREATE TABLE IF NOT EXISTS surahs (
    number INTEGER PRIMARY KEY,
    name TEXT
);

CREATE TABLE IF NOT EXISTS verses (
    surah_number INTEGER NOT NULL,
    ayah_number INTEGER NOT NULL,
    PRIMARY KEY (surah_number, ayah_number)
);

CREATE TABLE IF NOT EXISTS verse_texts (
    surah_number INTEGER NOT NULL,
    ayah_number INTEGER NOT NULL,
    text TEXT,
    PRIMARY KEY (surah_number, ayah_number)
);

CREATE TABLE IF NOT EXISTS tokens (
    id TEXT PRIMARY KEY,
    verse_surah INTEGER NOT NULL,
    verse_ayah INTEGER NOT NULL,
    token_index INTEGER NOT NULL,
    text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS segments (
    id TEXT PRIMARY KEY,
    token_id TEXT NOT NULL,
    type TEXT,
    form TEXT,
    root TEXT,
    lemma TEXT,
    pattern TEXT,
    pos TEXT,
    verb_form TEXT,
    voice TEXT,
    mood TEXT,
    aspect TEXT,
    person TEXT,
    number TEXT,
    gender TEXT,
    case_value TEXT,
    dependency_rel TEXT,
    role TEXT,
    derived_noun_type TEXT,
    state TEXT
);

CREATE INDEX IF NOT EXISTS idx_segments_token ON segments(token_id);
CREATE INDEX IF NOT EXISTS idx_segments_root ON segments(root);
CREATE INDEX IF NOT EXISTS idx_segments_lemma ON segments(lemma);
CREATE INDEX IF NOT EXISTS idx_segments_pos ON segments(pos);
CREATE INDEX IF NOT EXISTS idx_segments_pattern ON segments(pattern);

CREATE TABLE IF NOT EXISTS segment_payload (
    id TEXT PRIMARY KEY,
    verse_ref TEXT NOT NULL,
    token_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    payload JSON NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_segment_payload_verse ON segment_payload(verse_ref);
CREATE INDEX IF NOT EXISTS idx_segment_payload_token ON segment_payload(token_index);

CREATE TABLE IF NOT EXISTS annotations (
    id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL,
    layer TEXT,
    payload JSON NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_annotations_target ON annotations(target_id);

CREATE TABLE IF NOT EXISTS connections (
    id TEXT PRIMARY KEY,
    from_token TEXT NOT NULL,
    to_token TEXT NOT NULL,
    layer TEXT,
    meta JSON
);

CREATE INDEX IF NOT EXISTS idx_connections_from ON connections(from_token);
CREATE INDEX IF NOT EXISTS idx_connections_to ON connections(to_token);

CREATE TABLE IF NOT EXISTS verse_metadata (
    verse_ref TEXT PRIMARY KEY,
    pronouns JSON,
    hypotheses JSON,
    translations JSON
);

CREATE TABLE IF NOT EXISTS research_data (
    key TEXT PRIMARY KEY,
    value JSON NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"#;
