use axum::{extract::{Path, State}, http::StatusCode, Json};
use common::EngineError;
use std::collections::HashMap;

use crate::{AppState, map_err};

#[derive(serde::Serialize)]
pub struct SurahResponse {
    pub surah: SurahInfo,
    pub verses: Vec<VerseResponse>,
}

#[derive(serde::Serialize)]
pub struct SurahInfo {
    pub number: i64,
    pub name: String,
}

#[derive(serde::Serialize)]
pub struct VerseResponse {
    pub ayah: i64,
    pub text: String,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    pub tokens: Vec<serde_json::Value>,
}

pub async fn get_verse(
    State(state): State<AppState>,
    Path((surah, ayah)): Path<(i64, i64)>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let verse_data = state.storage.get_verse(surah, ayah).await.map_err(map_err)?;

    if let Some(verse) = verse_data {
        Ok(Json(verse))
    } else {
        Err(map_err(EngineError::NotFound))
    }
}

pub async fn get_verse_by_index(
    State(state): State<AppState>,
    Path(index): Path<i64>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let verse_data = state.storage.get_verse_by_index(index).await.map_err(map_err)?;

    if let Some(verse) = verse_data {
        Ok(Json(verse))
    } else {
        Err(map_err(EngineError::NotFound))
    }
}

pub async fn list_verses(
    State(state): State<AppState>,
    axum::extract::Query(params): axum::extract::Query<HashMap<String, String>>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let start: i64 = params.get("start").and_then(|s| s.parse().ok()).unwrap_or(0);
    let limit: i64 = params.get("limit").and_then(|s| s.parse().ok()).unwrap_or(50);

    let verses = state.storage.list_verses(start, limit).await.map_err(map_err)?;
    let total = state.storage.count_verses().await.map_err(map_err)?;

    Ok(Json(serde_json::json!({
        "verses": verses,
        "total": total,
        "start": start,
        "limit": limit
    })))
}

pub async fn get_surah(
    State(state): State<AppState>,
    Path(number): Path<i64>,
) -> Result<Json<SurahResponse>, (StatusCode, String)> {
    let verses = state.storage.get_surah_verses(number).await.map_err(map_err)?;

    if verses.is_empty() {
        return Err(map_err(EngineError::NotFound));
    }

    // Extract surah info from first verse
    let surah_info = SurahInfo {
        number,
        name: verses.first()
            .and_then(|v| v.get("surah_name"))
            .and_then(|n| n.as_str())
            .unwrap_or("Unknown")
            .to_string(),
    };

    // Populate tokens from segments for each verse
    let mut verse_responses: Vec<VerseResponse> = Vec::new();
    for v in verses {
        let ayah = v.get("ayah").and_then(|a| a.as_i64()).unwrap_or(0);
        let text = v.get("text").and_then(|t| t.as_str()).unwrap_or("").to_string();

        // Fetch tokens/segments for this verse
        let segments = state.storage.get_verse_segments(number, ayah).await.map_err(map_err)?;

        // Group segments by token_index
        let mut tokens_map: HashMap<usize, Vec<serde_json::Value>> = HashMap::new();
        for seg in segments {
            let token_idx = seg.get("token_index").and_then(|v| v.as_u64()).unwrap_or(0) as usize;
            tokens_map.entry(token_idx).or_insert_with(Vec::new).push(seg);
        }

        // Convert to sorted token array
        let mut token_indices: Vec<_> = tokens_map.keys().copied().collect();
        token_indices.sort();
        let tokens: Vec<serde_json::Value> = token_indices
            .into_iter()
            .map(|idx| serde_json::json!({
                "index": idx,
                "segments": tokens_map.get(&idx).cloned().unwrap_or_default()
            }))
            .collect();

        verse_responses.push(VerseResponse {
            ayah,
            text,
            tokens,
        });
    }

    Ok(Json(SurahResponse {
        surah: surah_info,
        verses: verse_responses,
    }))
}

pub async fn list_surahs(
    State(state): State<AppState>,
) -> Result<Json<Vec<store::SurahSummary>>, (StatusCode, String)> {
    let surahs = state.storage.list_surahs().await.map_err(map_err)?;
    Ok(Json(surahs))
}
