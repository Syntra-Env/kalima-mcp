use std::collections::HashMap;
use std::sync::Mutex;

use serde_json::Value;

use super::types::{SurahSummary, Verse};
use super::ARABIC_SURAH_NAMES;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Mode {
    Read,
    Write,
}

#[derive(Debug, Clone)]
pub(crate) struct AppState {
    pub(super) current_verse: Option<Verse>,
    pub(super) base_url: String,
    pub(super) surahs: Vec<SurahSummary>,
    pub(super) interpretations: HashMap<String, Vec<(String, String)>>, // (id, text)
    pub(super) mode: Mode,
    pub(super) editing: Option<(i64, i64, usize)>, // surah, ayah, index (0-based)
    pub(super) client: reqwest::blocking::Client,
}

#[derive(Debug, Clone)]
pub(crate) struct CommandResponse {
    pub(super) output: super::types::CommandOutput,
    pub(super) prefill: Option<String>,
}

impl AppState {
    pub(crate) fn new() -> Self {
        Self {
            current_verse: None,
            base_url: "http://127.0.0.1:8080".to_string(),
            surahs: Vec::new(),
            interpretations: HashMap::new(),
            mode: Mode::Read,
            editing: None,
            client: reqwest::blocking::Client::builder()
                .build()
                .expect("reqwest client"),
        }
    }

    #[cfg(test)]
    pub(super) fn new_with_base_url(base: &str) -> Self {
        Self {
            current_verse: None,
            base_url: base.to_string(),
            surahs: Vec::new(),
            interpretations: HashMap::new(),
            mode: Mode::Read,
            editing: None,
            client: reqwest::blocking::Client::builder()
                .build()
                .expect("reqwest client"),
        }
    }

    pub(crate) fn prompt(&self) -> String {
        if let Some((s, a, _)) = self.editing {
            return format!("kalima editing ({}:{}) >", s, a);
        }
        if let Some(v) = &self.current_verse {
            format!("kalima ({}:{}) >", v.surah.number, v.ayah)
        } else {
            "kalima >".to_string()
        }
    }
}

pub(crate) fn surah_name_or_fallback(number: i64, name: &str) -> String {
    let trimmed = name.trim();
    if !trimmed.is_empty() {
        return trimmed.to_string();
    }
    if (1..=114).contains(&number) {
        return ARABIC_SURAH_NAMES[(number - 1) as usize].to_string();
    }
    format!("Surah {}", number)
}

lazy_static::lazy_static! {
    pub(crate) static ref APP_STATE: Mutex<AppState> = Mutex::new(AppState::new());
    pub(crate) static ref FALLBACK_MORPH: Mutex<Option<HashMap<(i64, i64), Vec<Value>>>> = Mutex::new(None);
    pub(crate) static ref FALLBACK_MASAQ: Mutex<Option<HashMap<(i64, i64), Vec<Value>>>> = Mutex::new(None);
}
