use axum::{extract::{Path, State}, http::StatusCode, Json};
use common::StorageBackend;
use std::collections::HashMap;

use crate::{AppState, map_err};

pub async fn search_morphology(
    State(state): State<AppState>,
    axum::extract::Query(params): axum::extract::Query<HashMap<String, String>>,
) -> Result<Json<Vec<common::SegmentView>>, (StatusCode, String)> {
    let q = params.get("q").cloned().unwrap_or_default();
    // If query contains "pattern:" or "root:" prefix, map to filters
    let mut filters = Vec::new();
    if let Some(rest) = q.strip_prefix("pattern:") {
        filters.push(("pattern".into(), vec![rest.trim().to_string()]));
    }
    if let Some(rest) = q.strip_prefix("root:") {
        filters.push(("root".into(), vec![rest.trim().to_string()]));
    }
    let hits = state
        .search
        .search_with_filters(&q, filters, 50)
        .await
        .map_err(map_err)?;
    let docs = state.storage.hydrate_segments(&hits).await.map_err(map_err)?;
    Ok(Json(docs))
}

pub async fn get_morphology(
    State(state): State<AppState>,
    Path((surah, ayah)): Path<(i64, i64)>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    // Return segments for this verse as morphology data
    let segments = state.storage.get_verse_segments(surah, ayah).await.map_err(map_err)?;

    Ok(Json(serde_json::json!({
        "surah": surah,
        "ayah": ayah,
        "morphology": segments
    })))
}

pub async fn get_parsed_morphology(
    State(state): State<AppState>,
    Path((surah, ayah)): Path<(i64, i64)>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let segments = state.storage.get_verse_segments(surah, ayah).await.map_err(map_err)?;

    // Group segments by token
    let mut tokens_map: HashMap<usize, Vec<serde_json::Value>> = HashMap::new();
    for seg in segments {
        let token_idx = seg.get("token_index").and_then(|v| v.as_u64()).unwrap_or(0) as usize;
        tokens_map.entry(token_idx).or_insert_with(Vec::new).push(seg);
    }

    let mut tokens = Vec::new();
    for (idx, segs) in tokens_map.into_iter() {
        tokens.push(serde_json::json!({
            "id": idx,
            "segments": segs
        }));
    }

    Ok(Json(serde_json::json!({
        "surah": surah,
        "ayah": ayah,
        "tokens": tokens
    })))
}

pub async fn get_dependency(
    State(state): State<AppState>,
    Path((surah, ayah)): Path<(i64, i64)>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    // Return dependency data for verse (placeholder - would need treebank data)
    let segments = state.storage.get_verse_segments(surah, ayah).await.map_err(map_err)?;

    let dependency_tree: Vec<serde_json::Value> = segments.into_iter()
        .filter_map(|seg| {
            seg.get("dependency_rel").and_then(|rel| {
                if !rel.is_null() {
                    Some(serde_json::json!({
                        "rel_label": rel,
                        "word": seg.get("text").cloned().unwrap_or(serde_json::Value::Null),
                        "pos": seg.get("pos").cloned().unwrap_or(serde_json::Value::Null)
                    }))
                } else {
                    None
                }
            })
        })
        .collect();

    Ok(Json(serde_json::json!({
        "surah": surah,
        "ayah": ayah,
        "dependency_tree": dependency_tree
    })))
}

pub async fn list_morph_patterns(
    State(state): State<AppState>,
) -> Result<Json<Vec<serde_json::Value>>, (StatusCode, String)> {
    // Query unique patterns from storage
    let patterns = state.storage.list_unique_patterns().await.map_err(map_err)?;
    let pattern_list: Vec<serde_json::Value> = patterns
        .into_iter()
        .map(|p| serde_json::json!({ "pattern": p }))
        .collect();
    Ok(Json(pattern_list))
}

pub async fn list_syntax_patterns(
    State(state): State<AppState>,
) -> Result<Json<Vec<serde_json::Value>>, (StatusCode, String)> {
    // Query unique POS tags from storage
    let pos_tags = state.storage.list_unique_pos().await.map_err(map_err)?;
    let syntax_patterns: Vec<serde_json::Value> = pos_tags
        .into_iter()
        .map(|pos| serde_json::json!({ "pos": pos }))
        .collect();
    Ok(Json(syntax_patterns))
}
