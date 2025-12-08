use axum::{extract::State, http::StatusCode, Json};
use common::{EngineError, SegmentView, StorageBackend};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

use crate::{AppState, map_err};

pub async fn health() -> &'static str {
    "ok"
}

pub async fn segment_handler(
    State(state): State<AppState>,
    axum::extract::Path(id): axum::extract::Path<String>,
) -> Result<Json<SegmentView>, (StatusCode, String)> {
    match state.storage.get_segment(&id).await.map_err(map_err)? {
        Some(doc) => Ok(Json(doc)),
        None => Err(map_err(EngineError::NotFound)),
    }
}

pub async fn search_library(
    axum::extract::Query(params): axum::extract::Query<HashMap<String, String>>,
) -> Result<Json<Vec<serde_json::Value>>, (StatusCode, String)> {
    let q = params.get("q").cloned().unwrap_or_default().to_lowercase();
    let notes_dir = PathBuf::from("notes");
    let mut results = Vec::new();
    if notes_dir.exists() {
        for entry in fs::read_dir(notes_dir).map_err(|e| map_err(EngineError::Storage(e.to_string())))? {
            let entry = entry.map_err(|e| map_err(EngineError::Storage(e.to_string())))?;
            let path = entry.path();
            if path.is_file() {
                if let Ok(content) = fs::read_to_string(&path) {
                    if content.to_lowercase().contains(&q) {
                        results.push(serde_json::json!({
                            "path": path.to_string_lossy(),
                            "snippet": &content[..content.len().min(200)]
                        }));
                    }
                }
            }
        }
    }
    Ok(Json(results))
}

pub async fn list_notes() -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let notes_dir = PathBuf::from("notes");
    let mut notes = Vec::new();
    if notes_dir.exists() {
        for entry in fs::read_dir(notes_dir).map_err(|e| map_err(EngineError::Storage(e.to_string())))? {
            let entry = entry.map_err(|e| map_err(EngineError::Storage(e.to_string())))?;
            let path = entry.path();
            if path.is_file() {
                let name = path.file_name().unwrap_or_default().to_string_lossy().into_owned();
                notes.push(serde_json::json!({ "path": path.to_string_lossy(), "title": name }));
            }
        }
    }
    Ok(Json(serde_json::json!({ "notes": notes })))
}

pub async fn get_note_content(
    axum::extract::Query(q): axum::extract::Query<HashMap<String, String>>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let path = q.get("path").cloned().unwrap_or_default();
    let content = fs::read_to_string(&path).unwrap_or_default();
    Ok(Json(serde_json::json!({ "content": content })))
}
