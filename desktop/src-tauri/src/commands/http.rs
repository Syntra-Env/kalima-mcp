use anyhow::Result;

use super::state::surah_name_or_fallback;
use super::state::AppState;
use super::types::{SurahData, SurahSummary, Verse};

pub(crate) fn fetch_surah(state: &AppState, number: i64) -> Result<SurahData> {
    let surah = state
        .client
        .get(format!("{}/api/surah/{}", state.base_url, number))
        .send()?
        .error_for_status()?
        .json::<SurahData>()?;
    Ok(surah)
}

pub(crate) fn fetch_surah_list(state: &AppState) -> Result<Vec<SurahSummary>> {
    let surahs = state
        .client
        .get(format!("{}/api/surahs", state.base_url))
        .send()?
        .error_for_status()?
        .json::<Vec<SurahSummary>>()?;
    Ok(surahs
        .into_iter()
        .map(|mut s| {
            if s.name.trim().is_empty() {
                s.name = surah_name_or_fallback(s.number, &s.name);
            }
            s
        })
        .collect())
}

pub(crate) fn fetch_verse(state: &AppState, surah: i64, ayah: i64) -> Result<Verse> {
    let res = state
        .client
        .get(format!("{}/api/verse/{}/{}", state.base_url, surah, ayah))
        .send()?;

    if res.status() == reqwest::StatusCode::NOT_FOUND {
        anyhow::bail!("Verse does not exist.");
    }

    let verse = res.error_for_status()?.json::<Verse>()?;
    super::validate_verse(&verse)?;
    Ok(verse)
}
