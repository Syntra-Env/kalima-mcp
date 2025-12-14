use anyhow::Result;
use serde_json::Value;

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

pub(crate) fn fetch_morphology(state: &AppState, surah: i64, ayah: i64) -> Result<Vec<Value>> {
    let res: Value = state
        .client
        .get(format!(
            "{}/api/morphology/{}/{}",
            state.base_url, surah, ayah
        ))
        .send()?
        .error_for_status()?
        .json()?;
    let s = res.get("surah").and_then(Value::as_i64).unwrap_or(0);
    let a = res.get("ayah").and_then(Value::as_i64).unwrap_or(0);
    if s != surah || a != ayah {
        anyhow::bail!(
            "morphology response mismatch: expected {}:{}, got {}:{}",
            surah,
            ayah,
            s,
            a
        );
    }
    Ok(res
        .get("morphology")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default())
}

pub(crate) fn fetch_dependency(state: &AppState, surah: i64, ayah: i64) -> Result<Vec<Value>> {
    let res: Value = state
        .client
        .get(format!(
            "{}/api/dependency/{}/{}",
            state.base_url, surah, ayah
        ))
        .send()?
        .error_for_status()?
        .json()?;
    let s = res.get("surah").and_then(Value::as_i64).unwrap_or(0);
    let a = res.get("ayah").and_then(Value::as_i64).unwrap_or(0);
    if s != surah || a != ayah {
        anyhow::bail!(
            "dependency response mismatch: expected {}:{}, got {}:{}",
            surah,
            ayah,
            s,
            a
        );
    }
    Ok(res
        .get("dependency_tree")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default())
}
