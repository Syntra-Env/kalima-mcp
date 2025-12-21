use axum::{extract::State, http::StatusCode, Json};
use serde::{Deserialize, Serialize};
use sqlx::{QueryBuilder, Row, Sqlite};
use std::collections::{HashMap, HashSet};

use crate::{AppState, map_err};

#[derive(Debug, Deserialize)]
pub struct ConcordanceRequest {
    pub query: String,  // "#1 r:ajl c:Nom #2 g:M"
}

#[derive(Debug, Serialize)]
pub struct ConcordanceResult {
    pub verses: Vec<String>,     // ["2:255", "3:42"]
    pub verse_counts: Vec<VerseCount>,
    pub total: usize,
    pub matches: Vec<MatchContext>,
}

#[derive(Debug, Serialize)]
pub struct VerseCount {
    pub verse_ref: String, // "2:255"
    pub count: usize,
}

#[derive(Debug, Serialize)]
pub struct MatchContext {
    pub surah: i64,
    pub ayah: i64,
    pub text: String,
    pub tokens: Vec<TokenDisplay>,
    pub matched_indices: Vec<usize>,
}

#[derive(Debug, Serialize)]
pub struct TokenDisplay {
    pub index: usize,
    pub text: String,
    pub matched: bool,
}

pub async fn concordance_search(
    State(state): State<AppState>,
    Json(req): Json<ConcordanceRequest>,
) -> Result<Json<ConcordanceResult>, (StatusCode, String)> {
    // Parse the query
    let query = common::concordance::ConcordanceQuery::parse(&req.query)
        .map_err(|e| (StatusCode::BAD_REQUEST, format!("Invalid query: {}", e)))?;

    if !query.is_valid() {
        return Err((
            StatusCode::BAD_REQUEST,
            "Query must have at least one constraint per anchor".to_string(),
        ));
    }

    let result = execute_sequential_search(&state, &query).await?;
    Ok(Json(result))
}

const MAX_MATCHES_RETURNED: usize = 100;
const CONTEXT_TOKENS: usize = 6;

#[derive(Debug, Clone, Copy)]
enum ConstraintTarget {
    TokenText,
    SegmentColumn(&'static str),
}

fn constraint_target(field: &str) -> Option<ConstraintTarget> {
    let normalized = field.trim().to_ascii_lowercase();
    Some(match normalized.as_str() {
        "text" | "original" => ConstraintTarget::TokenText,
        "root" | "roots" => ConstraintTarget::SegmentColumn("root"),
        "lemma" | "lemmas" => ConstraintTarget::SegmentColumn("lemma"),
        "pattern" => ConstraintTarget::SegmentColumn("pattern"),
        "pos" => ConstraintTarget::SegmentColumn("pos"),
        "verb_form" => ConstraintTarget::SegmentColumn("verb_form"),
        "gender" => ConstraintTarget::SegmentColumn("gender"),
        "number" => ConstraintTarget::SegmentColumn("number"),
        "case" | "case_" => ConstraintTarget::SegmentColumn("case_value"),
        "voice" => ConstraintTarget::SegmentColumn("voice"),
        "mood" => ConstraintTarget::SegmentColumn("mood"),
        "aspect" => ConstraintTarget::SegmentColumn("aspect"),
        "person" => ConstraintTarget::SegmentColumn("person"),
        "dependency" | "dependency_rel" => ConstraintTarget::SegmentColumn("dependency_rel"),
        "role" => ConstraintTarget::SegmentColumn("role"),
        "derived_noun_type" => ConstraintTarget::SegmentColumn("derived_noun_type"),
        "state" => ConstraintTarget::SegmentColumn("state"),
        "segment_type" | "type" => ConstraintTarget::SegmentColumn("type"),
        "segment_form" | "form" => ConstraintTarget::SegmentColumn("form"),
        _ => return None,
    })
}

async fn fetch_anchor_positions(
    state: &AppState,
    constraints: &[common::concordance::FieldConstraint],
) -> Result<Vec<(i64, i64, usize)>, (StatusCode, String)> {
    let mut qb = QueryBuilder::<Sqlite>::new(
        "SELECT t.verse_surah, t.verse_ayah, t.token_index FROM tokens t WHERE ",
    );

    for (i, constraint) in constraints.iter().enumerate() {
        if i > 0 {
            qb.push(" AND ");
        }

        let target = constraint_target(&constraint.field).ok_or_else(|| {
            (
                StatusCode::BAD_REQUEST,
                format!("Unknown constraint field '{}'", constraint.field),
            )
        })?;

        match target {
            ConstraintTarget::TokenText => {
                push_value_predicate(
                    &mut qb,
                    "t.text",
                    &constraint.value,
                    constraint.negated,
                );
            }
            ConstraintTarget::SegmentColumn(col) => {
                if constraint.negated {
                    qb.push("NOT ");
                }
                qb.push("EXISTS (SELECT 1 FROM segments s WHERE s.token_id = t.id AND ");
                push_value_predicate(&mut qb, &format!("s.{}", col), &constraint.value, false);
                qb.push(")");
            }
        }
    }

    qb.push(" ORDER BY t.verse_surah, t.verse_ayah, t.token_index");

    let rows = qb
        .build()
        .fetch_all(state.storage.pool())
        .await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    let mut out = Vec::with_capacity(rows.len());
    for row in rows {
        let surah: i64 = row
            .try_get("verse_surah")
            .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        let ayah: i64 = row
            .try_get("verse_ayah")
            .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        let token_index: i64 = row
            .try_get("token_index")
            .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        if token_index >= 0 {
            out.push((surah, ayah, token_index as usize));
        }
    }
    Ok(out)
}

fn split_any_of(value: &str) -> Vec<String> {
    let mut parts = Vec::new();
    for raw in value.split(|c| c == '|' || c == ',') {
        let trimmed = raw.trim();
        if !trimmed.is_empty() {
            parts.push(trimmed.to_string());
        }
    }
    if parts.is_empty() {
        vec![value.to_string()]
    } else {
        parts
    }
}

fn to_like_pattern(value: &str) -> Option<String> {
    if !value.contains('*') {
        return None;
    }

    let mut out = String::new();
    for ch in value.chars() {
        match ch {
            '*' => out.push('%'),
            '%' | '_' | '\\' => {
                out.push('\\');
                out.push(ch);
            }
            _ => out.push(ch),
        }
    }
    Some(out)
}

fn push_value_predicate(
    qb: &mut QueryBuilder<Sqlite>,
    column: &str,
    value: &str,
    negated: bool,
) {
    let parts = split_any_of(value);

    if parts.len() == 1 {
        let v = &parts[0];
        if let Some(like) = to_like_pattern(v) {
            qb.push(column);
            if negated {
                qb.push(" NOT LIKE ");
            } else {
                qb.push(" LIKE ");
            }
            qb.push_bind(like);
            qb.push(" ESCAPE '\\\\'");
        } else {
            qb.push(column);
            if negated {
                qb.push(" <> ");
            } else {
                qb.push(" = ");
            }
            qb.push_bind(v.clone());
        }
        return;
    }

    if negated {
        qb.push("NOT ");
    }
    qb.push("(");

    for (idx, raw) in parts.into_iter().enumerate() {
        if idx > 0 {
            qb.push(" OR ");
        }

        qb.push(column);
        if let Some(like) = to_like_pattern(&raw) {
            qb.push(" LIKE ");
            qb.push_bind(like);
            qb.push(" ESCAPE '\\\\'");
        } else {
            qb.push(" = ");
            qb.push_bind(raw);
        }
    }

    qb.push(")");
}

async fn fetch_verse_tokens(
    state: &AppState,
    surah: i64,
    ayah: i64,
) -> Result<Vec<(usize, String)>, (StatusCode, String)> {
    let rows = sqlx::query("SELECT token_index, text FROM tokens WHERE verse_surah = ?1 AND verse_ayah = ?2 ORDER BY token_index")
        .bind(surah)
        .bind(ayah)
        .fetch_all(state.storage.pool())
        .await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    let mut out = Vec::with_capacity(rows.len());
    for row in rows {
        let idx: i64 = row
            .try_get("token_index")
            .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        let text: String = row
            .try_get("text")
            .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        if idx >= 0 {
            out.push((idx as usize, text));
        }
    }
    Ok(out)
}

async fn execute_sequential_search(
    state: &AppState,
    query: &common::concordance::ConcordanceQuery,
) -> Result<ConcordanceResult, (StatusCode, String)> {
    let anchors = query.anchors.clone();

    let mut per_anchor: Vec<HashMap<(i64, i64), Vec<usize>>> = Vec::new();
    for anchor in &anchors {
        let positions = fetch_anchor_positions(state, &anchor.constraints).await?;
        let mut by_verse: HashMap<(i64, i64), HashSet<usize>> = HashMap::new();
        for (surah, ayah, token_index) in positions {
            by_verse
                .entry((surah, ayah))
                .or_insert_with(HashSet::new)
                .insert(token_index);
        }

        let mut out_map: HashMap<(i64, i64), Vec<usize>> = HashMap::new();
        for (k, set) in by_verse {
            let mut v: Vec<usize> = set.into_iter().collect();
            v.sort_unstable();
            out_map.insert(k, v);
        }
        per_anchor.push(out_map);
    }

    let Some(first) = per_anchor.first() else {
        return Ok(ConcordanceResult {
            total: 0,
            verses: vec![],
            verse_counts: vec![],
            matches: vec![],
        });
    };

    let mut candidate_verses: HashSet<(i64, i64)> = first.keys().copied().collect();
    for anchor_map in per_anchor.iter().skip(1) {
        candidate_verses.retain(|k| anchor_map.contains_key(k));
    }

    let mut sorted_candidates: Vec<(i64, i64)> = candidate_verses.into_iter().collect();
    sorted_candidates.sort();

    let anchor_count = per_anchor.len();
    let mut total_matches = 0usize;
    let mut matches = Vec::new();
    let mut verse_refs_set: HashSet<String> = HashSet::new();
    let mut verse_counts: HashMap<String, usize> = HashMap::new();

    let mut token_cache: HashMap<(i64, i64), Vec<(usize, String)>> = HashMap::new();
    let mut verse_text_cache: HashMap<(i64, i64), String> = HashMap::new();

    for (surah, ayah) in sorted_candidates {
        let mut anchor_lists: Vec<&Vec<usize>> = Vec::with_capacity(anchor_count);
        for anchor_map in &per_anchor {
            let list = anchor_map
                .get(&(surah, ayah))
                .ok_or_else(|| (StatusCode::INTERNAL_SERVER_ERROR, "Anchor map missing verse".to_string()))?;
            anchor_lists.push(list);
        }

        for &start in anchor_lists[0].iter() {
            let mut matched_indices: Vec<usize> = Vec::with_capacity(anchor_count);
            matched_indices.push(start);

            let mut prev = start;
            let mut ok = true;
            for k in 1..anchor_count {
                let gap = anchors
                    .get(k - 1)
                    .and_then(|a| a.gap_to_next)
                    .unwrap_or(common::concordance::GapRange { min: 0, max: 0 });
                let min_idx = prev.saturating_add(1 + gap.min);
                let max_idx = prev.saturating_add(1 + gap.max);

                let list = anchor_lists[k];
                let found = match list.binary_search(&min_idx) {
                    Ok(pos) => list.get(pos).copied(),
                    Err(pos) => list.get(pos).copied(),
                };

                if let Some(idx) = found {
                    if idx <= max_idx {
                        matched_indices.push(idx);
                        prev = idx;
                    } else {
                        ok = false;
                        break;
                    }
                } else {
                    ok = false;
                    break;
                }
            }

            if !ok {
                continue;
            }

            total_matches += 1;

            if matches.len() >= MAX_MATCHES_RETURNED {
                continue;
            }

            let verse_key = (surah, ayah);
            let tokens = if let Some(t) = token_cache.get(&verse_key) {
                t.clone()
            } else {
                let t = fetch_verse_tokens(state, surah, ayah).await?;
                token_cache.insert(verse_key, t.clone());
                t
            };

            let text = if let Some(t) = verse_text_cache.get(&verse_key) {
                t.clone()
            } else {
                let verse_data = state.storage.get_verse(surah, ayah).await.map_err(map_err)?;
                let t = verse_data
                    .as_ref()
                    .and_then(|v| v.get("text"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string();
                verse_text_cache.insert(verse_key, t.clone());
                t
            };

            let window_start = matched_indices
                .first()
                .copied()
                .unwrap_or(0)
                .saturating_sub(CONTEXT_TOKENS);
            let window_end = (matched_indices.last().copied().unwrap_or(0) + 1 + CONTEXT_TOKENS).min(tokens.len());

            let window_tokens: Vec<TokenDisplay> = tokens
                .iter()
                .filter(|(idx, _)| *idx >= window_start && *idx < window_end)
                .map(|(idx, tok_text)| TokenDisplay {
                    index: *idx,
                    text: tok_text.clone(),
                    matched: matched_indices.contains(idx),
                })
                .collect();

            let verse_ref = format!("{}:{}", surah, ayah);
            verse_refs_set.insert(verse_ref.clone());
            *verse_counts.entry(verse_ref.clone()).or_insert(0) += 1;

            matches.push(MatchContext {
                surah,
                ayah,
                text,
                tokens: window_tokens,
                matched_indices,
            });
        }
    }

    let mut verse_refs: Vec<String> = verse_refs_set.into_iter().collect();
    verse_refs.sort();

    let mut verse_counts_vec: Vec<VerseCount> = verse_counts
        .into_iter()
        .map(|(verse_ref, count)| VerseCount { verse_ref, count })
        .collect();
    verse_counts_vec.sort_by(|a, b| a.verse_ref.cmp(&b.verse_ref));

    Ok(ConcordanceResult {
        total: total_matches,
        verses: verse_refs,
        verse_counts: verse_counts_vec,
        matches,
    })
}
