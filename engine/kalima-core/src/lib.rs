//! Core models, schemas, and trait contracts for the Kalima engine.

use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use thiserror::Error;
use std::str::FromStr;

// --- Models -----------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryFilter {
    pub field: String,
    pub op: String,
    #[serde(default)]
    pub value: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SortSpec {
    pub field: String,
    #[serde(default = "default_sort_dir")]
    pub direction: SortDirection,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SortDirection {
    Asc,
    Desc,
}

fn default_sort_dir() -> SortDirection {
    SortDirection::Asc
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuerySpec {
    pub query: serde_json::Value,
    #[serde(default)]
    pub filters: Vec<QueryFilter>,
    #[serde(default = "default_limit")]
    pub limit: usize,
    #[serde(default)]
    pub offset: usize,
    #[serde(default)]
    pub sort: Option<SortSpec>,
}

fn default_limit() -> usize {
    50
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Segment {
    pub id: String,
    pub r#type: String,
    pub form: String,
    #[serde(default)]
    pub root: Option<String>,
    #[serde(default)]
    pub lemma: Option<String>,
    #[serde(default)]
    pub pattern: Option<String>,
    #[serde(default)]
    pub pos: Option<String>,
    #[serde(default)]
    pub verb_form: Option<String>,
    #[serde(default)]
    pub voice: Option<String>,
    #[serde(default)]
    pub mood: Option<String>,
    #[serde(default)]
    pub tense: Option<String>,
    #[serde(default)]
    pub aspect: Option<String>,
    #[serde(default)]
    pub person: Option<String>,
    #[serde(default)]
    pub number: Option<String>,
    #[serde(default)]
    pub gender: Option<String>,
    #[serde(default)]
    pub case_: Option<String>,
    #[serde(default)]
    pub dependency_rel: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Annotation {
    pub id: String,
    pub target_id: String,
    pub layer: String,
    pub payload: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SurahInfo {
    pub number: i64,
    #[serde(default)]
    pub name: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerseResponse {
    pub surah: SurahInfo,
    pub ayah: i64,
    #[serde(default)]
    pub text: String,
    #[serde(default)]
    pub tokens: Vec<SegmentView>,
    #[serde(default)]
    pub annotations: Vec<Annotation>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SegmentView {
    pub id: String,
    pub verse_ref: String,
    pub token_index: usize,
    pub text: String,
    pub segments: Vec<Segment>,
    #[serde(default)]
    pub annotations: Vec<Annotation>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchHit {
    pub id: String,
    pub score: f32,
}

// --- Errors -----------------------------------------------------------------

#[derive(Debug, Error)]
pub enum EngineError {
    #[error("not found")]
    NotFound,
    #[error("storage error: {0}")]
    Storage(String),
    #[error("search error: {0}")]
    Search(String),
    #[error("invalid request: {0}")]
    Invalid(String),
    #[error(transparent)]
    Other(#[from] anyhow::Error),
}

pub type EngineResult<T> = Result<T, EngineError>;

pub fn parse_verse_ref(s: &str) -> EngineResult<(i64, i64)> {
    let (a, b) = s
        .split_once(':')
        .ok_or_else(|| EngineError::Invalid(format!("Invalid verse_ref: {}", s)))?;
    let surah = i64::from_str(a)
        .map_err(|_| EngineError::Invalid(format!("Invalid surah number in {}", s)))?;
    let ayah = i64::from_str(b)
        .map_err(|_| EngineError::Invalid(format!("Invalid ayah number in {}", s)))?;
    Ok((surah, ayah))
}

// --- Traits -----------------------------------------------------------------

#[async_trait]
pub trait StorageBackend: Send + Sync {
    async fn get_segment(&self, id: &str) -> EngineResult<Option<SegmentView>>;
    async fn hydrate_segments(&self, ids: &[SearchHit]) -> EngineResult<Vec<SegmentView>>;
}

#[async_trait]
pub trait SearchBackend: Send + Sync {
    async fn search(&self, query: &QuerySpec) -> EngineResult<Vec<SearchHit>>;
    async fn index_document(&self, doc: &SegmentView) -> EngineResult<()>;
}
