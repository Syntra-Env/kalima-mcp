# Rust Engine Migration – Initial Skeleton

This document sketches the Rust “engine room” layout, JSON schemas, and a minimal Axum service skeleton with SQLite + Tantivy behind traits. It is intentionally lean and replaceable; the API and data contracts are the stable pieces.

## Workspace layout
```
engine/
  Cargo.toml               # workspace members
  kalima-core/             # models, schemas, traits
    src/lib.rs
  kalima-store/            # StorageBackend impl (SQLite first)
    src/lib.rs
  kalima-index/            # SearchBackend impl (Tantivy behind a trait)
    src/lib.rs
  kalima-api/              # HTTP service (Axum) wiring storage + search
    src/main.rs
  schemas/                 # JSON Schemas (source of truth)
    query_spec.schema.json
    segment_view.schema.json
```

## Stable contracts (freeze early)
### QuerySpec (search requests)
- `query`: string or structured object (e.g., `{ "field": "root", "op": "eq", "value": "ktb" }`)
- `filters`: list of field filters (layer, surah, ayah, pos, verb_form, gender, number, case, etc.)
- `limit`/`offset`
- `sort` (field + direction)

### SegmentView (retrieval payload)
- `id`: string
- `verse_ref`: `"{surah}:{ayah}"`
- `token_index`: integer
- `text`: surface form
- `segments`: array of segment objects:
  - `id`, `type` (prefix/stem/suffix/clitic), `form`
  - `root`, `lemma`, `pattern`
  - `pos`, `verb_form`, `voice`, `mood`, `tense`, `aspect`
  - `person`, `number`, `gender`, `case`
  - `dependency_rel`
- `annotations`: array (user/auto annotations)

## JSON Schemas (source of truth)
### `schemas/query_spec.schema.json`
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "QuerySpec",
  "type": "object",
  "properties": {
    "query": { "oneOf": [{ "type": "string" }, { "type": "object" }] },
    "filters": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "field": { "type": "string" },
          "op": { "type": "string", "enum": ["eq", "neq", "in", "match"] },
          "value": {}
        },
        "required": ["field", "op", "value"]
      }
    },
    "limit": { "type": "integer", "minimum": 0, "default": 50 },
    "offset": { "type": "integer", "minimum": 0, "default": 0 },
    "sort": {
      "type": "object",
      "properties": {
        "field": { "type": "string" },
        "direction": { "type": "string", "enum": ["asc", "desc"], "default": "asc" }
      },
      "required": ["field"]
    }
  },
  "required": ["query"],
  "additionalProperties": false
}
```

### `schemas/segment_view.schema.json`
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SegmentView",
  "type": "object",
  "properties": {
    "id": { "type": "string" },
    "verse_ref": { "type": "string" },
    "token_index": { "type": "integer" },
    "text": { "type": "string" },
    "segments": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "type": { "type": "string" },
          "form": { "type": "string" },
          "root": { "type": "string" },
          "lemma": { "type": "string" },
          "pattern": { "type": "string" },
          "pos": { "type": "string" },
          "verb_form": { "type": "string" },
          "voice": { "type": "string" },
          "mood": { "type": "string" },
          "tense": { "type": "string" },
          "aspect": { "type": "string" },
          "person": { "type": "string" },
          "number": { "type": "string" },
          "gender": { "type": "string" },
          "case": { "type": "string" },
          "dependency_rel": { "type": "string" }
        },
        "required": ["id", "type", "form"]
      }
    },
    "annotations": { "type": "array" }
  },
  "required": ["id", "verse_ref", "token_index", "text", "segments"]
}
```

## Traits (kalima-core)
- `StorageBackend`: fetch/save verses, tokens, segments, annotations; iterator for ingestion.
- `SearchBackend`: index documents, search with QuerySpec → hits; hydrate IDs via storage.
- `SchemaVersion`: guard migrations.

## Minimal Axum skeleton (kalima-api/src/main.rs)
```rust
use axum::{routing::get, routing::post, Json, Router};
use kalima_core::{QuerySpec, SegmentView};
use std::sync::Arc;
use tokio::sync::Mutex;

#[derive(Clone)]
struct AppState {
    storage: Arc<dyn kalima_core::StorageBackend + Send + Sync>,
    search: Arc<dyn kalima_core::SearchBackend + Send + Sync>,
}

#[tokio::main]
async fn main() {
    let storage = kalima_store::sqlite::SqliteStorage::connect("kalima.db")
        .await
        .expect("sqlite init");
    let search = kalima_index::tantivy::TantivyIndex::open_or_create("index")
        .expect("tantivy init");

    let state = AppState {
        storage: Arc::new(storage),
        search: Arc::new(search),
    };

    let app = Router::new()
        .route("/health", get(|| async { "ok" }))
        .route("/search", post(search_handler))
        .route("/segment/:id", get(segment_handler))
        .with_state(state);

    let addr = "0.0.0.0:8080".parse().unwrap();
    println!("listening on {addr}");
    axum::Server::bind(&addr)
        .serve(app.into_make_service())
        .await
        .unwrap();
}

async fn search_handler(
    axum::extract::State(state): axum::extract::State<AppState>,
    Json(spec): Json<QuerySpec>,
) -> Json<Vec<SegmentView>> {
    let hits = state.search.search(&spec).await.unwrap_or_default();
    let docs = state.storage.hydrate_segments(&hits).await.unwrap_or_default();
    Json(docs)
}

async fn segment_handler(
    axum::extract::State(state): axum::extract::State<AppState>,
    axum::extract::Path(id): axum::extract::Path<String>,
) -> Option<Json<SegmentView>> {
    state.storage.get_segment(&id).await.ok().flatten().map(Json)
}
```

## Storage & search adapters (sketch)
- `kalima-store`: `SqliteStorage` implements `StorageBackend` (rusqlite/sqlx). Later add `PostgresStorage`.
- `kalima-index`: `TantivyIndex` implements `SearchBackend`. Later add alt engines without touching API.

## Next steps
1) Materialize the workspace dirs/files above; add `Cargo.toml` with `axum`, `tokio`, `serde`, `serde_json`, `async-trait`, `tantivy`, `rusqlite/sqlx`.
2) Implement the traits with real code paths and migrations (schema versioning).
3) Add golden tests: QuerySpec → expected verse refs; SegmentView shape; annotation CRUD.
4) Wire the current frontend to `/search` and `/segment/{id}` to exercise the Rust engine.
