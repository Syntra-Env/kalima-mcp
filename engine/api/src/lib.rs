mod config;
mod handlers;

pub use config::ServerConfig;

use axum::{http::StatusCode, routing::get, routing::post, Router};
use common::{EngineError, SearchBackend};
use search::TantivyIndex;
use store::SqliteStorage;
use std::sync::Arc;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

#[derive(Clone)]
pub struct AppState {
    pub storage: Arc<SqliteStorage>,
    pub search: Arc<TantivyIndex>,
}

pub async fn start_server() {
    start_server_with_config(ServerConfig::from_env()).await
}

pub async fn start_server_with_config(config: ServerConfig) {
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::new(&config.log_level))
        .with(tracing_subscriber::fmt::layer())
        .init();

    // Validate configuration
    if let Err(e) = config.validate() {
        eprintln!("Configuration validation failed: {}", e);
        eprintln!("Hint: Ensure data directories exist or set KALIMA_DB and KALIMA_INDEX environment variables");
        std::process::exit(1);
    }

    tracing::info!("Starting Kalima API server");
    tracing::info!("Database: {}", config.database_path);
    tracing::info!("Index: {}", config.index_path);
    tracing::info!("Bind address: {}", config.bind_address);

    // Init backends
    let storage = Arc::new(
        SqliteStorage::connect(&config.database_path)
            .await
            .expect("sqlite init"),
    );
    let search = Arc::new(
        TantivyIndex::open_or_create(&config.index_path)
            .expect("tantivy init"),
    );

    // Seed with a tiny doc so the API has something to return (dev only).
    // DISABLED: We now have a full database, so demo seed is not needed and causes duplicates
    // seed_demo(&storage, &search).await.expect("seed");

    let state = AppState { storage, search };

    let app = Router::new()
        // Health check
        .route("/health", get(handlers::util::health))

        // Search endpoints
        .route("/search", post(handlers::search::search_handler))
        .route("/search/root/:root", get(handlers::search::search_root))
        .route("/search/pos/:pos", get(handlers::search::search_pos))
        .route("/search/pattern/:pattern", get(handlers::search::search_pattern))
        .route("/search/verb_forms/:verb_form", get(handlers::search::search_verb_form))
        .route("/search/dependency/:rel", get(handlers::search::search_dependency))

        // Legacy search endpoints for backwards compatibility
        .route("/api/search/syntax", get(handlers::search::search_syntax))
        .route("/api/search/pattern_word", post(handlers::pattern::search_pattern_word))
        .route("/api/search/morphology", get(handlers::morphology::search_morphology))
        .route("/api/search/verb_forms", get(handlers::search::search_verb_forms_query))
        .route("/api/search/dependency", get(handlers::search::search_dependency_query))
        .route("/api/search", get(handlers::search::legacy_search))
        .route("/api/search/roots", get(handlers::search::search_roots_query))

        // Library/notes endpoints
        .route("/api/library_search", get(handlers::util::search_library))
        .route("/api/notes", get(handlers::util::list_notes))
        .route("/api/notes/content", get(handlers::util::get_note_content))

        // Metadata endpoints
        .route("/api/roots", get(handlers::search::list_roots))
        .route("/api/morph_patterns", get(handlers::morphology::list_morph_patterns))
        .route("/api/syntax_patterns", get(handlers::morphology::list_syntax_patterns))

        // Verse endpoints
        .route("/api/surahs", get(handlers::verse::list_surahs))
        .route("/api/surah/:number", get(handlers::verse::get_surah))
        .route("/api/verse/:surah/:ayah", get(handlers::verse::get_verse))
        .route("/api/verse/index/:index", get(handlers::verse::get_verse_by_index))
        .route("/api/verses", get(handlers::verse::list_verses))

        // Morphology endpoints
        .route("/api/morphology/:surah/:ayah", get(handlers::morphology::get_morphology))
        .route("/api/morphology/parsed/:surah/:ayah", get(handlers::morphology::get_parsed_morphology))
        .route("/api/dependency/:surah/:ayah", get(handlers::morphology::get_dependency))

        // Segment endpoints
        .route("/segment/:id", get(handlers::util::segment_handler))

        // Annotation endpoints
        .route("/annotations", post(handlers::research::create_annotation).get(handlers::research::list_annotations))
        .route("/annotations/:id", axum::routing::delete(handlers::research::delete_annotation))
        .route("/api/annotations/:surah/:ayah", get(handlers::research::get_annotations).post(handlers::research::create_annotation_verse))

        // Connection endpoints
        .route("/connections", post(handlers::research::create_connection).get(handlers::research::list_connections))
        .route("/connections/:id", axum::routing::delete(handlers::research::delete_connection))
        .route("/api/connections/:verse_ref", get(handlers::research::get_connections).post(handlers::research::save_connections))

        // Research endpoints
        .route("/api/pronouns/:verse_ref", get(handlers::research::get_pronouns).post(handlers::research::create_pronoun))
        .route("/api/pronouns/:verse_ref/:ref_id", axum::routing::put(handlers::research::update_pronoun).delete(handlers::research::delete_pronoun))
        .route("/api/hypotheses/:verse_ref", get(handlers::research::get_hypotheses).post(handlers::research::create_hypothesis))
        .route("/api/hypotheses/:verse_ref/:hyp_id", axum::routing::put(handlers::research::update_hypothesis).delete(handlers::research::delete_hypothesis))
        .route("/api/translations/:verse_ref", get(handlers::research::get_translations).post(handlers::research::create_translation).put(handlers::research::update_translations))
        .route("/api/patterns", get(handlers::research::get_patterns).post(handlers::research::create_pattern))
        .route("/api/patterns/:pattern_id", get(handlers::research::get_pattern).delete(handlers::research::delete_pattern))
        .route("/api/tags", get(handlers::research::get_tags))
        .route("/api/tags/:tag_name", get(handlers::research::get_tag).put(handlers::research::update_tag))
        .route("/api/stats", get(handlers::research::get_stats))
        .with_state(state);

    let listener = tokio::net::TcpListener::bind(&config.bind_address)
        .await
        .expect("bind listener");
    tracing::info!("Server listening on {}", config.bind_address);
    axum::serve(listener, app).await.expect("serve");
}

async fn seed_demo(storage: &SqliteStorage, search: &TantivyIndex) -> Result<(), (StatusCode, String)> {
    let doc = common::SegmentView {
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
            aspect: None,
            person: None,
            number: None,
            gender: None,
            case_: Some("gen".into()),
            dependency_rel: None,
            role: None,
            derived_noun_type: None,
            state: None,
        }],
        annotations: vec![],
    };
    storage.upsert_segment(&doc).await.map_err(map_err)?;
    let _ = search.index_document(&doc).await.map_err(map_err)?;
    Ok(())
}

/// Maps EngineError to HTTP responses
pub fn map_err(err: EngineError) -> (StatusCode, String) {
    match err {
        EngineError::NotFound => (StatusCode::NOT_FOUND, "Not found".into()),
        EngineError::Invalid(msg) => (StatusCode::BAD_REQUEST, msg),
        EngineError::Storage(msg) | EngineError::Search(msg) => {
            (StatusCode::INTERNAL_SERVER_ERROR, msg)
        }
        EngineError::Other(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()),
    }
}
