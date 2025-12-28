use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)]
pub(crate) struct SurahSummary {
    pub(crate) number: i64,
    pub(crate) name: String,
    #[serde(default, rename = "ayah_count")]
    pub(crate) ayah_count: Option<i64>,
}

#[derive(Debug, Clone, Deserialize)]
pub(crate) struct SurahInfo {
    pub(crate) number: i64,
    #[serde(default)]
    pub(crate) name: String,
}

#[derive(Debug, Clone, Deserialize)]
pub(crate) struct SurahData {
    pub(crate) surah: SurahInfo,
    pub(crate) verses: Vec<VerseSummary>,
}

#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)]
pub(crate) struct VerseSummary {
    pub(crate) ayah: i64,
    #[serde(default)]
    pub(crate) text: String,
    #[serde(default)]
    pub(crate) tokens: Vec<serde_json::Value>,
}

#[derive(Debug, Clone, Deserialize)]
pub(crate) struct Segment {
    #[serde(default)]
    pub(crate) root: Option<String>,
    #[serde(default)]
    pub(crate) pos: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub(crate) struct Token {
    pub(crate) text: Option<String>,
    #[serde(default)]
    pub(crate) form: Option<String>,
    #[serde(default)]
    pub(crate) segments: Vec<Segment>,
}

#[derive(Debug, Clone, Deserialize)]
pub(crate) struct Verse {
    pub(crate) surah: SurahInfo,
    pub(crate) ayah: i64,
    #[serde(default)]
    pub(crate) text: String,
    #[serde(default)]
    pub(crate) tokens: Vec<Token>,
}

#[derive(Debug, Clone, Serialize)]
pub struct VerseOutput {
    pub(crate) surah: i64,
    pub(crate) ayah: i64,
    pub(crate) text: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) tokens: Option<Vec<serde_json::Value>>,  // Full token data with morphology
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) legend: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct AnalysisToken {
    pub(crate) text: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) pos: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) form: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) lemma: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) features: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) role: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) case_: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) gender: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) number: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) definiteness: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) determiner: Option<bool>,
}

#[derive(Debug, Clone, Serialize)]
pub struct AnalysisOutput {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) header: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) verse_ref: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) text: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) tree: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) tokens: Option<Vec<AnalysisToken>>,
}

#[derive(Debug, Clone, Serialize)]
pub struct ChapterOutput {
    pub(crate) surah: i64,
    pub(crate) name: String,
    pub(crate) verses: Vec<VerseOutput>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(tag = "output_type", rename_all = "lowercase")]
pub enum CommandOutput {
    Verse(VerseOutput),
    Analysis(AnalysisOutput),
    Chapter(ChapterOutput),
    Clear,
    Pager { content: String },
    Error { message: String },
    Warning { message: String },
    Info { message: String },
}

#[derive(Debug, Clone, Serialize)]
pub struct CommandResult {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub output: Option<CommandOutput>,
    pub prompt: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub prefill: Option<String>,
}

