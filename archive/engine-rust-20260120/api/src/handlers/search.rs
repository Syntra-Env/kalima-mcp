use axum::{extract::{Path, State}, http::StatusCode, Json};
use common::{QuerySpec, SearchBackend, SegmentView, StorageBackend};
use std::collections::HashMap;

use crate::{AppState, map_err};

pub async fn search_handler(
    State(state): State<AppState>,
    Json(spec): Json<QuerySpec>,
) -> Result<Json<Vec<SegmentView>>, (StatusCode, String)> {
    let hits = state.search.search(&spec).await.map_err(map_err)?;
    let docs = state
        .storage
        .hydrate_segments(&hits)
        .await
        .map_err(map_err)?;
    Ok(Json(docs))
}

pub async fn search_root(
    State(state): State<AppState>,
    Path(root): Path<String>,
) -> Result<Json<Vec<SegmentView>>, (StatusCode, String)> {
    let hits = state
        .search
        .search_with_filters("", vec![("root".into(), vec![root])], 50)
        .await
        .map_err(map_err)?;
    let docs = state
        .storage
        .hydrate_segments(&hits)
        .await
        .map_err(map_err)?;
    Ok(Json(docs))
}

pub async fn search_roots_query(
    State(state): State<AppState>,
    axum::extract::Query(params): axum::extract::Query<HashMap<String, String>>,
) -> Result<Json<Vec<SegmentView>>, (StatusCode, String)> {
    let root = params.get("root").cloned().unwrap_or_default();
    search_root(State(state), Path(root)).await
}

pub async fn search_pos(
    State(state): State<AppState>,
    Path(pos): Path<String>,
) -> Result<Json<Vec<SegmentView>>, (StatusCode, String)> {
    let hits = state
        .search
        .search_with_filters("", vec![("pos".into(), vec![pos])], 50)
        .await
        .map_err(map_err)?;
    let docs = state
        .storage
        .hydrate_segments(&hits)
        .await
        .map_err(map_err)?;
    Ok(Json(docs))
}

pub async fn search_pattern(
    State(state): State<AppState>,
    Path(pattern): Path<String>,
) -> Result<Json<Vec<SegmentView>>, (StatusCode, String)> {
    let hits = state
        .search
        .search_with_filters("", vec![("pattern".into(), vec![pattern])], 50)
        .await
        .map_err(map_err)?;
    let docs = state
        .storage
        .hydrate_segments(&hits)
        .await
        .map_err(map_err)?;
    Ok(Json(docs))
}

pub async fn search_verb_form(
    State(state): State<AppState>,
    Path(form): Path<String>,
) -> Result<Json<Vec<SegmentView>>, (StatusCode, String)> {
    let hits = state
        .search
        .search_with_filters("", vec![("verb_form".into(), vec![form])], 50)
        .await
        .map_err(map_err)?;
    let docs = state
        .storage
        .hydrate_segments(&hits)
        .await
        .map_err(map_err)?;
    Ok(Json(docs))
}

pub async fn search_dependency(
    State(state): State<AppState>,
    Path(rel): Path<String>,
) -> Result<Json<Vec<SegmentView>>, (StatusCode, String)> {
    let hits = state
        .search
        .search_with_filters("", vec![("dependency_rel".into(), vec![rel])], 50)
        .await
        .map_err(map_err)?;
    let docs = state
        .storage
        .hydrate_segments(&hits)
        .await
        .map_err(map_err)?;
    Ok(Json(docs))
}

pub async fn search_syntax(
    State(state): State<AppState>,
    axum::extract::Query(params): axum::extract::Query<HashMap<String, String>>,
) -> Result<Json<Vec<SegmentView>>, (StatusCode, String)> {
    let q = params.get("q").cloned().unwrap_or_default();
    let mut filters = Vec::new();
    if let Some(pos) = params.get("pos") {
        filters.push(("pos".into(), vec![pos.clone()]));
    }
    let hits = state.search.search_with_filters(&q, filters, 50).await.map_err(map_err)?;
    let docs = state.storage.hydrate_segments(&hits).await.map_err(map_err)?;
    Ok(Json(docs))
}

pub async fn legacy_search(
    State(state): State<AppState>,
    axum::extract::Query(params): axum::extract::Query<HashMap<String, String>>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let query = params.get("q").cloned().unwrap_or_default();
    let search_type = params.get("type").map(|s| s.as_str()).unwrap_or("text");
    let limit: usize = params.get("limit").and_then(|s| s.parse().ok()).unwrap_or(100);

    let results = match search_type {
        "root" => {
            let hits = state.search.search_with_filters("", vec![("root".into(), vec![query.clone()])], limit).await.map_err(map_err)?;
            state.storage.hydrate_segments(&hits).await.map_err(map_err)?
        },
        _ => {
            // Text search
            let hits = state.search.search_with_filters(&query, vec![], limit).await.map_err(map_err)?;
            state.storage.hydrate_segments(&hits).await.map_err(map_err)?
        }
    };

    Ok(Json(serde_json::json!({
        "results": results,
        "query": query,
        "type": search_type,
        "count": results.len()
    })))
}

pub async fn search_verb_forms_query(
    State(state): State<AppState>,
    axum::extract::Query(params): axum::extract::Query<HashMap<String, String>>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let mut filters = Vec::new();

    // Map query params to filters
    if let Some(form) = params.get("form") {
        filters.push(("verb_form".into(), vec![form.clone()]));
    }
    if let Some(person) = params.get("person") {
        filters.push(("person".into(), vec![person.clone()]));
    }
    if let Some(number) = params.get("number") {
        filters.push(("number".into(), vec![number.clone()]));
    }
    if let Some(gender) = params.get("gender") {
        filters.push(("gender".into(), vec![gender.clone()]));
    }
    if let Some(voice) = params.get("voice") {
        filters.push(("voice".into(), vec![voice.clone()]));
    }
    if let Some(mood) = params.get("mood") {
        filters.push(("mood".into(), vec![mood.clone()]));
    }
    if let Some(tense) = params.get("tense") {
        filters.push(("tense".into(), vec![tense.clone()]));
    }
    if let Some(aspect) = params.get("aspect") {
        filters.push(("aspect".into(), vec![aspect.clone()]));
    }

    let hits = state.search.search_with_filters("", filters, 100).await.map_err(map_err)?;
    let docs = state.storage.hydrate_segments(&hits).await.map_err(map_err)?;

    Ok(Json(serde_json::json!({
        "results": docs,
        "count": docs.len()
    })))
}

pub async fn search_dependency_query(
    State(state): State<AppState>,
    axum::extract::Query(params): axum::extract::Query<HashMap<String, String>>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let relation = params.get("relation").cloned().unwrap_or_default();

    let hits = state
        .search
        .search_with_filters("", vec![("dependency_rel".into(), vec![relation.clone()])], 100)
        .await
        .map_err(map_err)?;
    let docs = state.storage.hydrate_segments(&hits).await.map_err(map_err)?;

    Ok(Json(serde_json::json!({
        "results": docs,
        "count": docs.len()
    })))
}

pub async fn list_roots(
    State(state): State<AppState>,
) -> Result<Json<Vec<String>>, (StatusCode, String)> {
    let roots = state.storage.list_unique_roots().await.map_err(map_err)?;
    Ok(Json(roots))
}
