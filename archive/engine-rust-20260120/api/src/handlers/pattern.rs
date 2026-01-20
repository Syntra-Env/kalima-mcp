use axum::{extract::State, http::StatusCode, Json};
use common::{EngineError, StorageBackend};

use crate::{AppState, map_err};

#[derive(serde::Deserialize)]
pub struct PatternWordRequest {
    #[serde(default)]
    pub word: Option<String>,
    #[serde(default)]
    pub allow_prefix: Option<bool>,
    #[serde(default)]
    pub allow_suffix: Option<bool>,
    #[serde(default)]
    pub segments: Option<serde_json::Value>,
    #[serde(default)]
    pub limit: Option<usize>,
}

/// Convert pattern segments to a regex pattern for Arabic text matching.
///
/// This function builds a regex pattern that matches Arabic text with diacritics.
/// It handles:
/// - Arabic letters: Unicode range U+0621 to U+064A (basic Arabic block)
///   plus extended forms U+0671-U+0673, U+0675 (alef with wasla, hamza variations)
/// - Diacritics: U+064B to U+0652 (tanween, kasra, fatha, damma, sukun, shadda)
///   plus U+0670 (alef superscript), U+0653-U+0655 (variants)
/// - Tatweel: U+0640 (elongation mark, optional matching with *)
///
/// The pattern respects word boundaries based on allow_prefix/allow_suffix flags.
pub fn pattern_segments_to_regex(
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

pub async fn search_pattern_word(
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
