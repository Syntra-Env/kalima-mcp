use axum::{extract::{Path, State}, http::StatusCode, Json};
use common::{Annotation, EngineError};
use store::ConnectionRecord;
use std::collections::HashMap;
use uuid::Uuid;

use crate::{AppState, map_err};

// Annotations

#[derive(serde::Deserialize)]
pub struct AnnotationRequest {
    #[serde(default)]
    pub id: Option<String>,
    pub target_id: String,
    pub layer: String,
    pub payload: serde_json::Value,
}

pub async fn create_annotation(
    State(state): State<AppState>,
    Json(req): Json<AnnotationRequest>,
) -> Result<Json<Annotation>, (StatusCode, String)> {
    let id = req.id.unwrap_or_else(|| Uuid::new_v4().to_string());
    let ann = Annotation {
        id: id.clone(),
        target_id: req.target_id,
        layer: req.layer,
        payload: req.payload,
    };
    state.storage.upsert_annotation(&ann).await.map_err(map_err)?;
    Ok(Json(ann))
}

pub async fn list_annotations(
    State(state): State<AppState>,
    axum::extract::Query(params): axum::extract::Query<HashMap<String, String>>,
) -> Result<Json<Vec<Annotation>>, (StatusCode, String)> {
    let target = params.get("target_id").map(|s| s.as_str());
    let anns = state
        .storage
        .list_annotations(target)
        .await
        .map_err(map_err)?;
    Ok(Json(anns))
}

pub async fn delete_annotation(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<StatusCode, (StatusCode, String)> {
    state
        .storage
        .delete_annotation(&id)
        .await
        .map_err(map_err)?;
    Ok(StatusCode::NO_CONTENT)
}

pub async fn get_annotations(
    State(_state): State<AppState>,
    Path((_surah, _ayah)): Path<(i64, i64)>,
) -> Result<Json<Vec<serde_json::Value>>, (StatusCode, String)> {
    // Annotations are handled via the general annotation endpoints
    // This endpoint exists for frontend compatibility
    Ok(Json(vec![]))
}

pub async fn create_annotation_verse(
    State(state): State<AppState>,
    Path((surah, ayah)): Path<(i64, i64)>,
    Json(annotation): Json<serde_json::Value>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    // Convert to annotation format and create
    let target_id = format!("{}:{}", surah, ayah);
    let layer = annotation.get("layer")
        .and_then(|v| v.as_str())
        .unwrap_or("default")
        .to_string();

    let ann = Annotation {
        id: annotation.get("id")
            .and_then(|v| v.as_str())
            .map(|s| s.to_string())
            .unwrap_or_else(|| Uuid::new_v4().to_string()),
        target_id,
        layer,
        payload: annotation.get("payload").cloned().unwrap_or(annotation.clone()),
    };

    state.storage.upsert_annotation(&ann).await.map_err(map_err)?;

    Ok(Json(serde_json::json!({ "success": true })))
}

// Connections

#[derive(serde::Deserialize)]
pub struct ConnectionRequest {
    #[serde(default)]
    pub id: Option<String>,
    pub from_token: String,
    pub to_token: String,
    pub layer: String,
    #[serde(default)]
    pub meta: serde_json::Value,
}

pub async fn create_connection(
    State(state): State<AppState>,
    Json(req): Json<ConnectionRequest>,
) -> Result<Json<ConnectionRecord>, (StatusCode, String)> {
    let id = req.id.unwrap_or_else(|| Uuid::new_v4().to_string());
    let conn = ConnectionRecord {
        id: id.clone(),
        from_token: req.from_token,
        to_token: req.to_token,
        layer: req.layer,
        meta: req.meta,
    };
    state
        .storage
        .upsert_connection(&conn)
        .await
        .map_err(map_err)?;
    Ok(Json(conn))
}

#[derive(serde::Deserialize)]
pub struct VerseQuery {
    pub verse: String,
}

pub async fn list_connections(
    State(state): State<AppState>,
    axum::extract::Query(q): axum::extract::Query<VerseQuery>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let (surah, ayah) = q
        .verse
        .split_once(':')
        .ok_or_else(|| map_err(EngineError::Invalid("Invalid verse param".into())))?;
    let surah_num: i64 = surah
        .parse()
        .map_err(|_| map_err(EngineError::Invalid("Invalid surah".into())))?;
    let ayah_num: i64 = ayah
        .parse()
        .map_err(|_| map_err(EngineError::Invalid("Invalid ayah".into())))?;

    let conns = state
        .storage
        .list_connections_for_verse(surah_num, ayah_num)
        .await
        .map_err(map_err)?;
    Ok(Json(serde_json::json!({
        "internal": conns,
        "external": []
    })))
}

pub async fn delete_connection(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<StatusCode, (StatusCode, String)> {
    state
        .storage
        .delete_connection(&id)
        .await
        .map_err(map_err)?;
    Ok(StatusCode::NO_CONTENT)
}

pub async fn get_connections(
    State(state): State<AppState>,
    Path(verse_ref): Path<String>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let (surah, ayah) = verse_ref
        .split_once(':')
        .ok_or_else(|| map_err(EngineError::Invalid("Invalid verse reference".into())))?;
    let surah_num: i64 = surah
        .parse()
        .map_err(|_| map_err(EngineError::Invalid("Invalid surah".into())))?;
    let ayah_num: i64 = ayah
        .parse()
        .map_err(|_| map_err(EngineError::Invalid("Invalid ayah".into())))?;

    let conns = state
        .storage
        .list_connections_for_verse(surah_num, ayah_num)
        .await
        .map_err(map_err)?;

    Ok(Json(serde_json::json!({
        "internal": conns,
        "external": []
    })))
}

pub async fn save_connections(
    State(state): State<AppState>,
    Path(_verse_ref): Path<String>,
    Json(data): Json<serde_json::Value>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    // Extract connections from the payload
    let empty_vec = vec![];
    let internal = data.get("internal").and_then(|v| v.as_array()).unwrap_or(&empty_vec);

    for conn in internal {
        let conn_id = conn.get("id")
            .and_then(|v| v.as_str())
            .unwrap_or_else(|| "");
        let from_token = conn.get("from_token")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let to_token = conn.get("to_token")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let layer = conn.get("layer")
            .and_then(|v| v.as_str())
            .unwrap_or("default")
            .to_string();
        let meta = conn.get("meta").cloned().unwrap_or(serde_json::json!({}));

        let connection_record = ConnectionRecord {
            id: if conn_id.is_empty() {
                Uuid::new_v4().to_string()
            } else {
                conn_id.to_string()
            },
            from_token,
            to_token,
            layer,
            meta,
        };

        state.storage.upsert_connection(&connection_record).await.map_err(map_err)?;
    }

    Ok(Json(serde_json::json!({ "success": true })))
}

// Pronouns

pub async fn get_pronouns(
    State(state): State<AppState>,
    Path(verse_ref): Path<String>,
) -> Result<Json<Vec<serde_json::Value>>, (StatusCode, String)> {
    let pronouns = state
        .storage
        .get_verse_metadata(&verse_ref, "pronouns")
        .await
        .map_err(map_err)?;
    Ok(Json(pronouns))
}

pub async fn create_pronoun(
    State(state): State<AppState>,
    Path(verse_ref): Path<String>,
    Json(data): Json<serde_json::Value>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let mut pronouns = state
        .storage
        .get_verse_metadata(&verse_ref, "pronouns")
        .await
        .map_err(map_err)?;

    // Add ID if not present
    let mut new_entry = data;
    if !new_entry.get("id").is_some() {
        let id = format!("pr-{}", chrono::Utc::now().timestamp());
        new_entry["id"] = serde_json::json!(id);
    }

    // Add timestamps
    let now = chrono::Utc::now().to_rfc3339();
    new_entry["created_at"] = serde_json::json!(now.clone());
    new_entry["updated_at"] = serde_json::json!(now);

    pronouns.push(new_entry.clone());

    state
        .storage
        .set_verse_metadata(&verse_ref, "pronouns", &serde_json::json!(pronouns))
        .await
        .map_err(map_err)?;

    Ok(Json(serde_json::json!({
        "success": true,
        "reference": new_entry
    })))
}

pub async fn update_pronoun(
    State(state): State<AppState>,
    Path((verse_ref, ref_id)): Path<(String, String)>,
    Json(updates): Json<serde_json::Value>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let mut pronouns = state
        .storage
        .get_verse_metadata(&verse_ref, "pronouns")
        .await
        .map_err(map_err)?;

    let mut found = false;
    for pronoun in &mut pronouns {
        if pronoun.get("id").and_then(|v| v.as_str()) == Some(&ref_id) {
            // Update fields
            if let Some(obj) = pronoun.as_object_mut() {
                if let Some(upd_obj) = updates.as_object() {
                    for (k, v) in upd_obj {
                        if k != "id" {
                            obj.insert(k.clone(), v.clone());
                        }
                    }
                }
                obj.insert("updated_at".to_string(), serde_json::json!(chrono::Utc::now().to_rfc3339()));
            }
            found = true;
            break;
        }
    }

    if !found {
        return Err(map_err(EngineError::NotFound));
    }

    state
        .storage
        .set_verse_metadata(&verse_ref, "pronouns", &serde_json::json!(pronouns))
        .await
        .map_err(map_err)?;

    Ok(Json(serde_json::json!({ "success": true })))
}

pub async fn delete_pronoun(
    State(state): State<AppState>,
    Path((verse_ref, ref_id)): Path<(String, String)>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let mut pronouns = state
        .storage
        .get_verse_metadata(&verse_ref, "pronouns")
        .await
        .map_err(map_err)?;

    let before_len = pronouns.len();
    pronouns.retain(|p| p.get("id").and_then(|v| v.as_str()) != Some(&ref_id));

    if pronouns.len() == before_len {
        return Err(map_err(EngineError::NotFound));
    }

    state
        .storage
        .set_verse_metadata(&verse_ref, "pronouns", &serde_json::json!(pronouns))
        .await
        .map_err(map_err)?;

    Ok(Json(serde_json::json!({ "success": true })))
}

// Hypotheses

pub async fn get_hypotheses(
    State(state): State<AppState>,
    Path(verse_ref): Path<String>,
) -> Result<Json<Vec<serde_json::Value>>, (StatusCode, String)> {
    let hypotheses = state
        .storage
        .get_verse_metadata(&verse_ref, "hypotheses")
        .await
        .map_err(map_err)?;
    Ok(Json(hypotheses))
}

pub async fn create_hypothesis(
    State(state): State<AppState>,
    Path(verse_ref): Path<String>,
    Json(data): Json<serde_json::Value>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let mut hypotheses = state
        .storage
        .get_verse_metadata(&verse_ref, "hypotheses")
        .await
        .map_err(map_err)?;

    let mut new_entry = data;
    if !new_entry.get("id").is_some() {
        let id = format!("hyp-{}", chrono::Utc::now().timestamp());
        new_entry["id"] = serde_json::json!(id);
    }

    let now = chrono::Utc::now().to_rfc3339();
    new_entry["created_at"] = serde_json::json!(now.clone());
    new_entry["updated_at"] = serde_json::json!(now);

    hypotheses.push(new_entry.clone());

    state
        .storage
        .set_verse_metadata(&verse_ref, "hypotheses", &serde_json::json!(hypotheses))
        .await
        .map_err(map_err)?;

    Ok(Json(serde_json::json!({
        "success": true,
        "hypothesis": new_entry
    })))
}

pub async fn update_hypothesis(
    State(state): State<AppState>,
    Path((verse_ref, hyp_id)): Path<(String, String)>,
    Json(updates): Json<serde_json::Value>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let mut hypotheses = state
        .storage
        .get_verse_metadata(&verse_ref, "hypotheses")
        .await
        .map_err(map_err)?;

    let mut found = false;
    for hypothesis in &mut hypotheses {
        if hypothesis.get("id").and_then(|v| v.as_str()) == Some(&hyp_id) {
            if let Some(obj) = hypothesis.as_object_mut() {
                if let Some(upd_obj) = updates.as_object() {
                    for (k, v) in upd_obj {
                        if k != "id" {
                            obj.insert(k.clone(), v.clone());
                        }
                    }
                }
                obj.insert("updated_at".to_string(), serde_json::json!(chrono::Utc::now().to_rfc3339()));
            }
            found = true;
            break;
        }
    }

    if !found {
        return Err(map_err(EngineError::NotFound));
    }

    state
        .storage
        .set_verse_metadata(&verse_ref, "hypotheses", &serde_json::json!(hypotheses))
        .await
        .map_err(map_err)?;

    Ok(Json(serde_json::json!({ "success": true })))
}

pub async fn delete_hypothesis(
    State(state): State<AppState>,
    Path((verse_ref, hyp_id)): Path<(String, String)>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let mut hypotheses = state
        .storage
        .get_verse_metadata(&verse_ref, "hypotheses")
        .await
        .map_err(map_err)?;

    let before_len = hypotheses.len();
    hypotheses.retain(|h| h.get("id").and_then(|v| v.as_str()) != Some(&hyp_id));

    if hypotheses.len() == before_len {
        return Err(map_err(EngineError::NotFound));
    }

    state
        .storage
        .set_verse_metadata(&verse_ref, "hypotheses", &serde_json::json!(hypotheses))
        .await
        .map_err(map_err)?;

    Ok(Json(serde_json::json!({ "success": true })))
}

// Translations

pub async fn get_translations(
    State(state): State<AppState>,
    Path(verse_ref): Path<String>,
) -> Result<Json<Vec<serde_json::Value>>, (StatusCode, String)> {
    let translations = state
        .storage
        .get_verse_metadata(&verse_ref, "translations")
        .await
        .map_err(map_err)?;
    Ok(Json(translations))
}

pub async fn create_translation(
    State(state): State<AppState>,
    Path(verse_ref): Path<String>,
    Json(data): Json<serde_json::Value>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let mut translations = state
        .storage
        .get_verse_metadata(&verse_ref, "translations")
        .await
        .map_err(map_err)?;

    let mut new_entry = data;
    if !new_entry.get("id").is_some() {
        let id = format!("tr-{}", chrono::Utc::now().timestamp());
        new_entry["id"] = serde_json::json!(id);
    }

    let now = chrono::Utc::now().to_rfc3339();
    new_entry["created_at"] = serde_json::json!(now);

    translations.push(new_entry.clone());

    state
        .storage
        .set_verse_metadata(&verse_ref, "translations", &serde_json::json!(translations))
        .await
        .map_err(map_err)?;

    Ok(Json(serde_json::json!({
        "success": true,
        "translation": new_entry
    })))
}

pub async fn update_translations(
    State(state): State<AppState>,
    Path(verse_ref): Path<String>,
    Json(data): Json<Vec<serde_json::Value>>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    state
        .storage
        .set_verse_metadata(&verse_ref, "translations", &serde_json::json!(data))
        .await
        .map_err(map_err)?;

    Ok(Json(serde_json::json!({ "success": true })))
}

// Patterns

pub async fn get_patterns(
    State(state): State<AppState>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let patterns = state
        .storage
        .get_research_data("patterns")
        .await
        .map_err(map_err)?
        .unwrap_or(serde_json::json!({}));
    Ok(Json(patterns))
}

pub async fn create_pattern(
    State(state): State<AppState>,
    Json(mut pattern): Json<serde_json::Value>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let mut patterns = state
        .storage
        .get_research_data("patterns")
        .await
        .map_err(map_err)?
        .unwrap_or(serde_json::json!({}));

    let patterns_obj = patterns.as_object_mut().ok_or_else(|| {
        map_err(EngineError::Invalid("Patterns data is not an object".into()))
    })?;

    let pattern_id = pattern.get("id")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
        .unwrap_or_else(|| format!("pattern-{}", patterns_obj.len() + 1));

    pattern["id"] = serde_json::json!(pattern_id.clone());
    patterns_obj.insert(pattern_id.clone(), pattern);

    state
        .storage
        .set_research_data("patterns", &patterns)
        .await
        .map_err(map_err)?;

    Ok(Json(serde_json::json!({
        "success": true,
        "id": pattern_id
    })))
}

pub async fn get_pattern(
    State(state): State<AppState>,
    Path(pattern_id): Path<String>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let patterns = state
        .storage
        .get_research_data("patterns")
        .await
        .map_err(map_err)?
        .unwrap_or(serde_json::json!({}));

    let pattern = patterns.get(&pattern_id)
        .ok_or_else(|| map_err(EngineError::NotFound))?;

    Ok(Json(pattern.clone()))
}

pub async fn delete_pattern(
    State(state): State<AppState>,
    Path(pattern_id): Path<String>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let mut patterns = state
        .storage
        .get_research_data("patterns")
        .await
        .map_err(map_err)?
        .unwrap_or(serde_json::json!({}));

    let patterns_obj = patterns.as_object_mut().ok_or_else(|| {
        map_err(EngineError::Invalid("Patterns data is not an object".into()))
    })?;

    if patterns_obj.remove(&pattern_id).is_none() {
        return Err(map_err(EngineError::NotFound));
    }

    state
        .storage
        .set_research_data("patterns", &patterns)
        .await
        .map_err(map_err)?;

    Ok(Json(serde_json::json!({ "success": true })))
}

// Tags

pub async fn get_tags(
    State(state): State<AppState>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let tags = state
        .storage
        .get_research_data("tags")
        .await
        .map_err(map_err)?
        .unwrap_or(serde_json::json!({}));
    Ok(Json(tags))
}

pub async fn get_tag(
    State(state): State<AppState>,
    Path(tag_name): Path<String>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let tags = state
        .storage
        .get_research_data("tags")
        .await
        .map_err(map_err)?
        .unwrap_or(serde_json::json!({}));

    let tag = tags.get("tags")
        .and_then(|t| t.get(&tag_name))
        .ok_or_else(|| map_err(EngineError::NotFound))?;

    Ok(Json(tag.clone()))
}

pub async fn update_tag(
    State(state): State<AppState>,
    Path(tag_name): Path<String>,
    Json(tag_data): Json<serde_json::Value>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let mut tags = state
        .storage
        .get_research_data("tags")
        .await
        .map_err(map_err)?
        .unwrap_or(serde_json::json!({}));

    if !tags.get("tags").is_some() {
        tags["tags"] = serde_json::json!({});
    }

    if let Some(tags_obj) = tags.get_mut("tags").and_then(|t| t.as_object_mut()) {
        tags_obj.insert(tag_name, tag_data);
    }

    state
        .storage
        .set_research_data("tags", &tags)
        .await
        .map_err(map_err)?;

    Ok(Json(serde_json::json!({ "success": true })))
}

// Claims (QuranResearch integration)

#[derive(serde::Deserialize)]
pub struct ClaimQuery {
    pub phase: Option<String>,
    pub pattern_id: Option<String>,
}

#[derive(serde::Serialize)]
pub struct Claim {
    pub id: String,
    pub content: String,
    pub phase: String,
    pub pattern_id: Option<String>,
    pub note_file: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

pub async fn list_claims(
    State(state): State<AppState>,
    axum::extract::Query(query): axum::extract::Query<ClaimQuery>,
) -> Result<Json<Vec<Claim>>, (StatusCode, String)> {
    let mut sql = "SELECT id, content, phase, pattern_id, note_file, created_at, updated_at FROM claims WHERE 1=1".to_string();

    if let Some(phase) = &query.phase {
        sql.push_str(&format!(" AND phase = '{}'", phase));
    }
    if let Some(pattern_id) = &query.pattern_id {
        sql.push_str(&format!(" AND pattern_id = '{}'", pattern_id));
    }
    sql.push_str(" ORDER BY updated_at DESC");

    let rows = sqlx::query(&sql)
        .fetch_all(state.storage.pool())
        .await
        .map_err(|e| map_err(common::EngineError::Storage(e.to_string())))?;

    let claims: Vec<Claim> = rows
        .into_iter()
        .map(|row| Claim {
            id: row.try_get("id").unwrap_or_default(),
            content: row.try_get("content").unwrap_or_default(),
            phase: row.try_get("phase").unwrap_or_default(),
            pattern_id: row.try_get("pattern_id").ok(),
            note_file: row.try_get("note_file").ok(),
            created_at: row.try_get("created_at").unwrap_or_default(),
            updated_at: row.try_get("updated_at").unwrap_or_default(),
        })
        .collect();

    Ok(Json(claims))
}

#[derive(serde::Serialize)]
pub struct ClaimEvidence {
    pub id: String,
    pub claim_id: String,
    pub surah: Option<i64>,
    pub ayah: Option<i64>,
    pub notes: Option<String>,
    pub created_at: String,
}

pub async fn get_claim_evidence(
    State(state): State<AppState>,
    Path(claim_id): Path<String>,
) -> Result<Json<Vec<ClaimEvidence>>, (StatusCode, String)> {
    let rows = sqlx::query(
        "SELECT id, claim_id, surah, ayah, notes, created_at FROM claim_evidence WHERE claim_id = ? ORDER BY surah, ayah"
    )
    .bind(&claim_id)
    .fetch_all(state.storage.pool())
    .await
    .map_err(|e| map_err(common::EngineError::Storage(e.to_string())))?;

    let evidence: Vec<ClaimEvidence> = rows
        .into_iter()
        .map(|row| ClaimEvidence {
            id: row.try_get("id").unwrap_or_default(),
            claim_id: row.try_get("claim_id").unwrap_or_default(),
            surah: row.try_get("surah").ok(),
            ayah: row.try_get("ayah").ok(),
            notes: row.try_get("notes").ok(),
            created_at: row.try_get("created_at").unwrap_or_default(),
        })
        .collect();

    Ok(Json(evidence))
}

#[derive(serde::Serialize)]
pub struct DependencyTree {
    pub claim: Claim,
    pub dependencies: Vec<Claim>,
}

pub async fn get_claim_dependencies(
    State(state): State<AppState>,
    Path(claim_id): Path<String>,
) -> Result<Json<DependencyTree>, (StatusCode, String)> {
    // Get the main claim
    let claim_row = sqlx::query(
        "SELECT id, content, phase, pattern_id, note_file, created_at, updated_at FROM claims WHERE id = ?"
    )
    .bind(&claim_id)
    .fetch_one(state.storage.pool())
    .await
    .map_err(|e| map_err(common::EngineError::Storage(e.to_string())))?;

    let claim = Claim {
        id: claim_row.try_get("id").unwrap_or_default(),
        content: claim_row.try_get("content").unwrap_or_default(),
        phase: claim_row.try_get("phase").unwrap_or_default(),
        pattern_id: claim_row.try_get("pattern_id").ok(),
        note_file: claim_row.try_get("note_file").ok(),
        created_at: claim_row.try_get("created_at").unwrap_or_default(),
        updated_at: claim_row.try_get("updated_at").unwrap_or_default(),
    };

    // Recursive CTE to get all dependencies
    let dep_rows = sqlx::query(
        r#"
        WITH RECURSIVE deps(claim_id, depth) AS (
            VALUES(?1, 0)
            UNION
            SELECT depends_on_claim_id, depth+1
            FROM claim_dependencies, deps
            WHERE claim_dependencies.claim_id = deps.claim_id
        )
        SELECT c.id, c.content, c.phase, c.pattern_id, c.note_file, c.created_at, c.updated_at
        FROM claims c
        WHERE c.id IN (SELECT claim_id FROM deps WHERE depth > 0)
        ORDER BY c.updated_at DESC
        "#
    )
    .bind(&claim_id)
    .fetch_all(state.storage.pool())
    .await
    .map_err(|e| map_err(common::EngineError::Storage(e.to_string())))?;

    let dependencies: Vec<Claim> = dep_rows
        .into_iter()
        .map(|row| Claim {
            id: row.try_get("id").unwrap_or_default(),
            content: row.try_get("content").unwrap_or_default(),
            phase: row.try_get("phase").unwrap_or_default(),
            pattern_id: row.try_get("pattern_id").ok(),
            note_file: row.try_get("note_file").ok(),
            created_at: row.try_get("created_at").unwrap_or_default(),
            updated_at: row.try_get("updated_at").unwrap_or_default(),
        })
        .collect();

    Ok(Json(DependencyTree {
        claim,
        dependencies,
    }))
}

#[derive(serde::Serialize)]
pub struct Pattern {
    pub id: String,
    pub description: String,
    pub pattern_type: String,
    pub scope: Option<String>,
    pub phase: String,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(serde::Deserialize)]
pub struct PatternQuery {
    pub pattern_type: Option<String>,
    pub phase: Option<String>,
}

pub async fn list_patterns(
    State(state): State<AppState>,
    axum::extract::Query(query): axum::extract::Query<PatternQuery>,
) -> Result<Json<Vec<Pattern>>, (StatusCode, String)> {
    let mut sql = "SELECT id, description, pattern_type, scope, phase, created_at, updated_at FROM patterns WHERE 1=1".to_string();

    if let Some(ptype) = &query.pattern_type {
        sql.push_str(&format!(" AND pattern_type = '{}'", ptype));
    }
    if let Some(phase) = &query.phase {
        sql.push_str(&format!(" AND phase = '{}'", phase));
    }
    sql.push_str(" ORDER BY updated_at DESC");

    let rows = sqlx::query(&sql)
        .fetch_all(state.storage.pool())
        .await
        .map_err(|e| map_err(common::EngineError::Storage(e.to_string())))?;

    let patterns: Vec<Pattern> = rows
        .into_iter()
        .map(|row| Pattern {
            id: row.try_get("id").unwrap_or_default(),
            description: row.try_get("description").unwrap_or_default(),
            pattern_type: row.try_get("pattern_type").unwrap_or_default(),
            scope: row.try_get("scope").ok(),
            phase: row.try_get("phase").unwrap_or_default(),
            created_at: row.try_get("created_at").unwrap_or_default(),
            updated_at: row.try_get("updated_at").unwrap_or_default(),
        })
        .collect();

    Ok(Json(patterns))
}

// Stats

pub async fn get_stats(
    State(state): State<AppState>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let total_verses = state.storage.count_verses().await.map_err(map_err)?;
    let verses_with_tokens = state.storage.count_verses_with_tokens().await.map_err(map_err)?;
    let total_annotations = state.storage.count_annotations().await.map_err(map_err)?;

    let tags = state
        .storage
        .get_research_data("tags")
        .await
        .map_err(map_err)?
        .unwrap_or(serde_json::json!({}));
    let total_tags = tags.get("tags")
        .and_then(|t| t.as_object())
        .map(|o| o.len())
        .unwrap_or(0);

    Ok(Json(serde_json::json!({
        "total_verses": total_verses,
        "verses_with_tokens": verses_with_tokens,
        "total_annotations": total_annotations,
        "total_hypothesis_tags": total_tags
    })))
}
