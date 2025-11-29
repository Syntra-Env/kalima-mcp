use axum::{extract::State, http::StatusCode, routing::get, routing::post, Json, Router};
use axum::extract::Path;
use axum::response::{IntoResponse, Response};
use axum::http::{header, Uri};
use common::{Annotation, EngineError, QuerySpec, SearchBackend, SegmentView, StorageBackend};
use search::TantivyIndex;
use store::{ConnectionRecord, SqliteStorage, SurahSummary};
use std::sync::Arc;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};
use uuid::Uuid;
use std::fs;
use std::path::PathBuf;
use std::collections::HashMap;
use rust_embed::RustEmbed;

#[derive(RustEmbed)]
#[folder = "../../desktop/web/"]
struct StaticAssets;

#[derive(Clone)]
struct AppState {
    storage: Arc<SqliteStorage>,
    search: Arc<TantivyIndex>,
}

pub async fn start_server() {
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::new(
            std::env::var("RUST_LOG").unwrap_or_else(|_| "info".into()),
        ))
        .with(tracing_subscriber::fmt::layer())
        .init();

    // Init backends
    let db_path = std::env::var("KALIMA_DB").unwrap_or_else(|_| "data/database/kalima.db".into());
    let index_path = std::env::var("KALIMA_INDEX").unwrap_or_else(|_| "data/search-index".into());

    let storage = Arc::new(
        SqliteStorage::connect(&db_path)
            .await
            .expect("sqlite init"),
    );
    let search = Arc::new(
        TantivyIndex::open_or_create(&index_path)
            .expect("tantivy init"),
    );

    // Seed with a tiny doc so the API has something to return (dev only).
    seed_demo(&storage, &search).await.expect("seed");

    let state = AppState { storage, search };

    let app = Router::new()
        .route("/health", get(health))
        .route("/search", post(search_handler))
        .route("/search/root/:root", get(search_root))
        .route("/search/pos/:pos", get(search_pos))
        .route("/search/pattern/:pattern", get(search_pattern))
        .route("/search/verb_forms/:verb_form", get(search_verb_form))
        .route("/search/dependency/:rel", get(search_dependency))
        // Compatibility stubs for legacy calls
        .route("/api/search/syntax", get(search_syntax))
        .route("/api/search/pattern_word", post(search_pattern_word))
        .route("/api/search/morphology", get(search_morphology))
        .route("/api/search/verb_forms", get(search_verb_forms_query))
        .route("/api/search/dependency", get(search_dependency_query))
        .route("/api/library_search", get(search_library))
        .route("/api/notes", get(list_notes))
        .route("/api/notes/content", get(get_note_content))
        .route("/api/roots", get(list_roots))
        .route("/api/morph_patterns", get(list_morph_patterns))
        .route("/api/syntax_patterns", get(list_syntax_patterns))
        .route("/api/surahs", get(list_surahs))
        .route("/api/surah/:number", get(get_surah))
        .route("/api/search/roots", get(search_roots_query))
        .route("/api/verse/:surah/:ayah", get(get_verse))
        .route("/api/verse/index/:index", get(get_verse_by_index))
        .route("/api/verses", get(list_verses))
        .route("/api/search", get(legacy_search))
        .route("/api/morphology/:surah/:ayah", get(get_morphology))
        .route("/api/morphology/parsed/:surah/:ayah", get(get_parsed_morphology))
        .route("/api/dependency/:surah/:ayah", get(get_dependency))
        .route("/segment/:id", get(segment_handler))
        .route("/annotations", post(create_annotation).get(list_annotations))
        .route("/annotations/:id", axum::routing::delete(delete_annotation))
        .route("/connections", post(create_connection).get(list_connections))
        .route("/connections/:id", axum::routing::delete(delete_connection))
        .route("/api/connections/:verse_ref", get(get_connections).post(save_connections))
        .route("/api/annotations/:surah/:ayah", get(get_annotations).post(create_annotation_verse))
        // Research endpoints
        .route("/api/pronouns/:verse_ref", get(get_pronouns).post(create_pronoun))
        .route("/api/pronouns/:verse_ref/:ref_id", axum::routing::put(update_pronoun).delete(delete_pronoun))
        .route("/api/hypotheses/:verse_ref", get(get_hypotheses).post(create_hypothesis))
        .route("/api/hypotheses/:verse_ref/:hyp_id", axum::routing::put(update_hypothesis).delete(delete_hypothesis))
        .route("/api/translations/:verse_ref", get(get_translations).post(create_translation).put(update_translations))
        .route("/api/patterns", get(get_patterns).post(create_pattern))
        .route("/api/patterns/:pattern_id", get(get_pattern).delete(delete_pattern))
        .route("/api/tags", get(get_tags))
        .route("/api/tags/:tag_name", get(get_tag).put(update_tag))
        .route("/api/stats", get(get_stats))
        .with_state(state)
        .fallback(static_handler);

    let addr = "0.0.0.0:8080";
    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .expect("bind listener");
    tracing::info!("listening on {addr}");
    axum::serve(listener, app).await.expect("serve");
}

async fn health() -> &'static str {
    "ok"
}

// Hybrid static file handler: checks folder first, falls back to embedded
async fn static_handler(uri: Uri) -> Response {
    let path = uri.path().trim_start_matches('/');

    // Strip /static/ prefix if present
    let path = path.trim_start_matches("static/");

    // Default to index.html for root
    let path = if path.is_empty() || path == "/" {
        "index.html"
    } else {
        path
    };

    // Strategy 1: Try to serve from external folder (for easy updates)
    let folder_path = PathBuf::from("./desktop/web").join(path);
    if folder_path.exists() && folder_path.is_file() {
        if let Ok(content) = fs::read(&folder_path) {
            let mime_type = mime_guess::from_path(&folder_path)
                .first_or_octet_stream();

            return (
                [(header::CONTENT_TYPE, mime_type.as_ref())],
                content
            ).into_response();
        }
    }

    // Strategy 2: Serve from embedded assets (production fallback)
    match StaticAssets::get(path) {
        Some(content) => {
            let mime_type = mime_guess::from_path(path)
                .first_or_octet_stream();

            (
                [(header::CONTENT_TYPE, mime_type.as_ref())],
                content.data.into_owned()
            ).into_response()
        }
        None => {
            // If path not found, try serving index.html (for SPA routing)
            if path != "index.html" {
                if let Some(content) = StaticAssets::get("index.html") {
                    return (
                        [(header::CONTENT_TYPE, "text/html")],
                        content.data.into_owned()
                    ).into_response();
                }
            }

            (StatusCode::NOT_FOUND, "404 Not Found").into_response()
        }
    }
}

async fn search_handler(
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

async fn search_root(
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

async fn search_roots_query(
    State(state): State<AppState>,
    axum::extract::Query(params): axum::extract::Query<HashMap<String, String>>,
) -> Result<Json<Vec<SegmentView>>, (StatusCode, String)> {
    let root = params.get("root").cloned().unwrap_or_default();
    search_root(State(state), Path(root)).await
}

async fn search_pos(
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

async fn search_pattern(
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

async fn search_verb_form(
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

async fn search_dependency(
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

// Legacy-compatible stubs (return empty results for now)
async fn search_syntax(
    State(state): State<AppState>,
    axum::extract::Query(params): axum::extract::Query<std::collections::HashMap<String, String>>,
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

#[derive(serde::Deserialize)]
struct PatternWordRequest {
    #[serde(default)]
    word: Option<String>,
    #[serde(default)]
    allow_prefix: Option<bool>,
    #[serde(default)]
    allow_suffix: Option<bool>,
    #[serde(default)]
    segments: Option<serde_json::Value>,
    #[serde(default)]
    limit: Option<usize>,
}

fn pattern_segments_to_regex(
    segments: &[serde_json::Value],
    allow_prefix: bool,
    allow_suffix: bool,
) -> Option<String> {
    // Arabic letter range (including extended alef/hamza forms)
    const ARABIC_LETTERS: &str = r"[\u{0621}-\u{064A}\u{0671}-\u{0673}\u{0675}]";
    // Diacritic marks
    const DIACRITIC_CLASS: &str = r"[\u{064B}-\u{0652}\u{0670}\u{0653}-\u{0655}]";
    // Tatweel (elongation mark)
    const TATWEEL: &str = r"\u{0640}*";

    let mut parts = Vec::new();

    for seg in segments {
        let letter = seg.get("letter").and_then(|v| v.as_str());
        let any_letter = seg.get("any_letter").and_then(|v| v.as_bool()).unwrap_or(letter.is_none());
        let diacritics = seg.get("diacritics").and_then(|v| v.as_array());
        let any_diacritics = seg.get("any_diacritics").and_then(|v| v.as_bool()).unwrap_or(false);

        // Build letter part
        let letter_part = if any_letter {
            ARABIC_LETTERS.to_string()
        } else if let Some(l) = letter {
            regex::escape(l)
        } else {
            ARABIC_LETTERS.to_string()
        };

        // Build diacritic part
        let diac_part = if any_diacritics {
            format!("{}*", DIACRITIC_CLASS)
        } else if let Some(diacs) = diacritics {
            let specific: String = diacs
                .iter()
                .filter_map(|d| d.as_str())
                .map(|d| regex::escape(d))
                .collect();
            format!("{}{}*", specific, DIACRITIC_CLASS)
        } else {
            format!("{}*", DIACRITIC_CLASS)
        };

        parts.push(format!("{}{}{}", letter_part, diac_part, TATWEEL));
    }

    if parts.is_empty() {
        return None;
    }

    let body = parts.join("");

    // Word boundaries based on allow_prefix/allow_suffix
    let left = if allow_prefix { "" } else { r"(?<!\S)" };
    let right = if allow_suffix { "" } else { r"(?!\S)" };

    Some(format!("{}{}{}", left, body, right))
}

async fn search_pattern_word(
    State(state): State<AppState>,
    Json(body): Json<PatternWordRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let limit = body.limit.unwrap_or(50);

    // If we have segments, do regex-based pattern matching
    if let Some(segments) = body.segments.as_ref().and_then(|v| v.as_array()) {
        if !segments.is_empty() {
            let allow_prefix = body.allow_prefix.unwrap_or(false);
            let allow_suffix = body.allow_suffix.unwrap_or(false);

            let pattern = pattern_segments_to_regex(segments, allow_prefix, allow_suffix)
                .ok_or_else(|| map_err(EngineError::Invalid("Failed to build regex pattern".into())))?;

            let re = regex::Regex::new(&pattern)
                .map_err(|e| map_err(EngineError::Invalid(format!("Invalid regex: {}", e))))?;

            // Fetch verse texts and match against pattern
            let verse_texts = state.storage.get_all_verse_texts(6236).await.map_err(map_err)?;
            let mut results = Vec::new();
            let mut total_count = 0;

            for (verse_ref, text) in verse_texts {
                let matches: Vec<_> = re.find_iter(&text).collect();
                if !matches.is_empty() {
                    total_count += matches.len();
                    if results.len() < limit {
                        // Parse verse_ref to get verse data
                        if let Some((surah_str, ayah_str)) = verse_ref.split_once(':') {
                            if let (Ok(surah), Ok(ayah)) = (surah_str.parse::<i64>(), ayah_str.parse::<i64>()) {
                                if let Ok(Some(verse_data)) = state.storage.get_verse(surah, ayah).await {
                                    results.push(serde_json::json!({
                                        "verse": verse_data,
                                        "match": "Pattern match",
                                        "match_regex": pattern,
                                        "match_count": matches.len()
                                    }));
                                }
                            }
                        }
                    }
                }
            }

            return Ok(Json(serde_json::json!({
                "results": results,
                "total_count": total_count,
                "query": body.segments,
                "type": "pattern_word"
            })));
        }
    }

    // Fallback to simple text search if no segments provided
    let word = body.word.as_deref().unwrap_or("");
    let mut filters = Vec::new();
    if let Some(segments) = body.segments.as_ref().and_then(|v| v.as_array()) {
        for seg in segments {
            if let Some(pat) = seg.get("pattern").and_then(|p| p.as_str()) {
                filters.push(("pattern".into(), vec![pat.to_string()]));
            }
            if let Some(pos) = seg.get("pos").and_then(|p| p.as_str()) {
                filters.push(("pos".into(), vec![pos.to_string()]));
            }
        }
    }
    let hits = state
        .search
        .search_with_filters(word, filters, limit)
        .await
        .map_err(map_err)?;
    let docs = state.storage.hydrate_segments(&hits).await.map_err(map_err)?;

    Ok(Json(serde_json::json!({
        "results": docs,
        "count": docs.len(),
        "query": word,
        "type": "pattern_word"
    })))
}

async fn search_morphology(
    State(state): State<AppState>,
    axum::extract::Query(params): axum::extract::Query<std::collections::HashMap<String, String>>,
) -> Result<Json<Vec<SegmentView>>, (StatusCode, String)> {
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

async fn search_library(
    axum::extract::Query(params): axum::extract::Query<std::collections::HashMap<String, String>>,
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

async fn list_notes() -> Result<Json<serde_json::Value>, (StatusCode, String)> {
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

async fn get_note_content(
    axum::extract::Query(q): axum::extract::Query<std::collections::HashMap<String, String>>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let path = q.get("path").cloned().unwrap_or_default();
    let content = fs::read_to_string(&path).unwrap_or_default();
    Ok(Json(serde_json::json!({ "content": content })))
}

async fn segment_handler(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<SegmentView>, (StatusCode, String)> {
    match state.storage.get_segment(&id).await.map_err(map_err)? {
        Some(doc) => Ok(Json(doc)),
        None => Err(map_err(common::EngineError::NotFound)),
    }
}

async fn seed_demo(storage: &SqliteStorage, search: &TantivyIndex) -> Result<(), (StatusCode, String)> {
    let doc = SegmentView {
        id: "demo-1".into(),
        verse_ref: "1:1".into(),
        token_index: 0,
        text: "بِسْمِ".into(),
        segments: vec![common::Segment {
            id: "seg-1".into(),
            r#type: "prefix".into(),
            form: "بِ".into(),
            root: None,
            lemma: None,
            pattern: None,
            pos: Some("P".into()),
            verb_form: None,
            voice: None,
            mood: None,
            tense: None,
            aspect: None,
            person: None,
            number: None,
            gender: None,
            case_: Some("gen".into()),
            dependency_rel: None,
        }],
        annotations: vec![],
    };
    storage.upsert_segment(&doc).await.map_err(map_err)?;
    let _ = search.index_document(&doc).await.map_err(map_err)?;
    Ok(())
}

// Map EngineError to HTTP responses
fn map_err(err: EngineError) -> (StatusCode, String) {
    match err {
        EngineError::NotFound => (StatusCode::NOT_FOUND, "Not found".into()),
        EngineError::Invalid(msg) => (StatusCode::BAD_REQUEST, msg),
        EngineError::Storage(msg) | EngineError::Search(msg) => {
            (StatusCode::INTERNAL_SERVER_ERROR, msg)
        }
        EngineError::Other(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()),
    }
}

#[derive(serde::Deserialize)]
struct AnnotationRequest {
    #[serde(default)]
    id: Option<String>,
    target_id: String,
    layer: String,
    payload: serde_json::Value,
}

async fn create_annotation(
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

async fn list_annotations(
    State(state): State<AppState>,
    axum::extract::Query(params): axum::extract::Query<std::collections::HashMap<String, String>>,
) -> Result<Json<Vec<Annotation>>, (StatusCode, String)> {
    let target = params.get("target_id").map(|s| s.as_str());
    let anns = state
        .storage
        .list_annotations(target)
        .await
        .map_err(map_err)?;
    Ok(Json(anns))
}

async fn delete_annotation(
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

#[derive(serde::Deserialize)]
struct ConnectionRequest {
    #[serde(default)]
    id: Option<String>,
    from_token: String,
    to_token: String,
    layer: String,
    #[serde(default)]
    meta: serde_json::Value,
}

async fn create_connection(
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
struct VerseQuery {
    verse: String,
}

async fn list_connections(
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

async fn list_roots(
    State(state): State<AppState>,
) -> Result<Json<Vec<String>>, (StatusCode, String)> {
    // Query all unique roots from storage
    let roots = state.storage.list_unique_roots().await.map_err(map_err)?;
    Ok(Json(roots))
}

async fn list_morph_patterns(
    State(_state): State<AppState>,
) -> Result<Json<Vec<serde_json::Value>>, (StatusCode, String)> {
    // For now, return empty array - can be populated from corpus analysis
    Ok(Json(vec![]))
}

async fn list_syntax_patterns(
    State(_state): State<AppState>,
) -> Result<Json<Vec<serde_json::Value>>, (StatusCode, String)> {
    // For now, return empty array - can be populated from corpus analysis
    Ok(Json(vec![]))
}

async fn list_surahs(
    State(state): State<AppState>,
) -> Result<Json<Vec<SurahSummary>>, (StatusCode, String)> {
    let surahs = state.storage.list_surahs().await.map_err(map_err)?;
    Ok(Json(surahs))
}

#[derive(serde::Serialize)]
struct SurahResponse {
    surah: SurahInfo,
    verses: Vec<VerseResponse>,
}

#[derive(serde::Serialize)]
struct SurahInfo {
    number: i64,
    name: String,
}

#[derive(serde::Serialize)]
struct VerseResponse {
    ayah: i64,
    text: String,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    tokens: Vec<serde_json::Value>,
}

async fn get_surah(
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
    
    let verse_responses: Vec<VerseResponse> = verses
        .into_iter()
        .map(|v| VerseResponse {
            ayah: v.get("ayah").and_then(|a| a.as_i64()).unwrap_or(0),
            text: v.get("text").and_then(|t| t.as_str()).unwrap_or("").to_string(),
            tokens: vec![], // TODO: populate from segments
        })
        .collect();
    
    Ok(Json(SurahResponse {
        surah: surah_info,
        verses: verse_responses,
    }))
}

async fn get_verse(
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

async fn get_verse_by_index(
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

async fn list_verses(
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

async fn legacy_search(
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

async fn get_morphology(
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

async fn get_parsed_morphology(
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

async fn get_dependency(
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

async fn delete_connection(
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

// Research endpoint handlers

async fn get_pronouns(
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

async fn create_pronoun(
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

async fn update_pronoun(
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

async fn delete_pronoun(
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

async fn get_hypotheses(
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

async fn create_hypothesis(
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

async fn update_hypothesis(
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

async fn delete_hypothesis(
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

async fn get_translations(
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

async fn create_translation(
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

async fn update_translations(
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

async fn get_patterns(
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

async fn create_pattern(
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

async fn get_pattern(
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

async fn delete_pattern(
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

async fn get_tags(
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

async fn get_tag(
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

async fn update_tag(
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

async fn get_stats(
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

// Additional frontend-compatible endpoints

async fn search_verb_forms_query(
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

async fn search_dependency_query(
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

async fn get_connections(
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

async fn save_connections(
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

async fn get_annotations(
    State(_state): State<AppState>,
    Path((_surah, _ayah)): Path<(i64, i64)>,
) -> Result<Json<Vec<serde_json::Value>>, (StatusCode, String)> {
    // For now, return empty array - annotations are handled differently in the verse endpoint
    // This endpoint exists for frontend compatibility
    Ok(Json(vec![]))
}

async fn create_annotation_verse(
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

    let ann = common::Annotation {
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
