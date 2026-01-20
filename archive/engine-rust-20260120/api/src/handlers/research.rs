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
