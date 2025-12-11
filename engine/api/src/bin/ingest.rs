use common::{SearchBackend, Segment, SegmentView};
use search::TantivyIndex;
use store::SqliteStorage;
use serde::Deserialize;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::sync::Arc;
use structopt::StructOpt;
use sqlx::{query, Executor};

#[derive(StructOpt)]
struct Args {
    /// Path to JSONL corpus (each line a verse with tokens/segments)
    #[structopt(long, parse(from_os_str))]
    input: PathBuf,
    /// SQLite database path
    #[structopt(long, default_value = "kalima.db")]
    db: String,
    /// Tantivy index directory
    #[structopt(long, default_value = "kalima-index")]
    index: String,
    /// Skip creating the search index (useful for debugging permissions)
    #[structopt(long)]
    skip_index: bool,
}

#[derive(Deserialize)]
struct CorpusVerse {
    surah: SurahMeta,
    ayah: i64,
    #[serde(default)]
    text: Option<String>,
    tokens: Option<Vec<CorpusToken>>,
}

#[derive(Deserialize)]
struct SurahMeta {
    number: i64,
    #[allow(dead_code)]
    name: Option<String>,
}

#[derive(Deserialize)]
struct CorpusToken {
    #[serde(default)]
    id: Option<serde_json::Value>,  // Can be string or integer
    form: String,
    segments: Option<Vec<CorpusSegment>>,
}

#[derive(Deserialize)]
struct CorpusSegment {
    id: Option<String>,
    #[serde(rename = "type")]
    ty: Option<String>,
    form: Option<String>,
    root: Option<String>,
    lemma: Option<String>,
    pattern: Option<String>,
    pos: Option<String>,
    verb_form: Option<String>,
    voice: Option<String>,
    mood: Option<String>,
    aspect: Option<String>,
    person: Option<String>,
    number: Option<String>,
    gender: Option<String>,
    case: Option<String>,
    dependency_rel: Option<String>,
    role: Option<String>,
    derived_noun_type: Option<String>,
    state: Option<String>,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args = Args::from_args();
    let storage = Arc::new(SqliteStorage::connect(&args.db).await?);

    // Speed up bulk ingest: relaxed fsync and WAL journaling are fine for one-shot loads.
    let pragmas = vec![
        "PRAGMA journal_mode=WAL;",
        "PRAGMA synchronous=OFF;",
        "PRAGMA temp_store=MEMORY;",
        "PRAGMA cache_size=-200000;", // ~200MB cache
    ];
    for p in pragmas {
        let _ = storage.pool().execute(p).await;
    }
    
    let index = if !args.skip_index {
        Some(Arc::new(TantivyIndex::open_or_create(&args.index)?))
    } else {
        None
    };

    let file = File::open(&args.input)?;
    let reader = BufReader::new(file);

    let mut verse_count: usize = 0;
    let mut token_count: usize = 0;
    let mut segment_count: usize = 0;
    const LOG_EVERY: usize = 1000;

    for line in reader.lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let verse: CorpusVerse = serde_json::from_str(&line)?;
        verse_count += 1;
        if let Some(tokens) = verse.tokens {
            // Build a canonical verse text: prefer provided text, else join token forms.
            let joined_tokens = tokens
                .iter()
                .map(|t| t.form.as_str())
                .collect::<Vec<_>>()
                .join(" ");
            let verse_text = verse
                .text
                .clone()
                .filter(|t| !t.is_empty())
                .unwrap_or_else(|| joined_tokens.clone());

            for (i, tok) in tokens.into_iter().enumerate() {
                token_count += 1;
                let segs = tok
                    .segments
                    .unwrap_or_default()
                    .into_iter()
                    .enumerate()
                    .map(|(idx, s)| Segment {
                        id: s
                            .id
                            .unwrap_or_else(|| format!("seg-{}-{}-{}-{}", verse.surah.number, verse.ayah, i, idx)),
                        r#type: s.ty.unwrap_or_default(),
                        form: s.form.unwrap_or_else(|| tok.form.clone()),
                        root: s.root,
                        lemma: s.lemma,
                        pattern: s.pattern,
                        pos: s.pos,
                        verb_form: s.verb_form,
                        voice: s.voice,
                        mood: s.mood,
                        aspect: s.aspect,
                        person: s.person,
                        number: s.number,
                        gender: s.gender,
                        case_: s.case,
                        dependency_rel: s.dependency_rel,
                        role: s.role,
                        derived_noun_type: s.derived_noun_type,
                        state: s.state,
                    })
                    .collect::<Vec<_>>();
                segment_count += segs.len();

                let token_id = tok
                    .id
                    .map(|v| v.to_string().trim_matches('"').to_string())
                    .unwrap_or_else(|| format!("{}:{}:{}", verse.surah.number, verse.ayah, i));
                let doc = SegmentView {
                    id: token_id.clone(),
                    verse_ref: format!("{}:{}", verse.surah.number, verse.ayah),
                    token_index: i,
                    text: tok.form.clone(),
                    segments: segs,
                    annotations: vec![],
                };
                storage.upsert_segment(&doc).await?;
                if let Some(idx) = &index {
                    idx.index_document(&doc).await?;
                }
            }

            // Override verse text to the clean Quran text once per verse.
            query(
                r#"
                INSERT INTO verse_texts (surah_number, ayah_number, text)
                VALUES (?1, ?2, ?3)
                ON CONFLICT(surah_number, ayah_number) DO UPDATE SET text=excluded.text;
                "#,
            )
            .bind(verse.surah.number)
            .bind(verse.ayah)
            .bind(&verse_text)
            .execute(storage.pool())
            .await?;
        }

        if verse_count % LOG_EVERY == 0 {
            println!(
                "Ingested {} verses ({} tokens, {} segments)...",
                verse_count, token_count, segment_count
            );
        }
    }

    if let Some(idx) = &index {
        println!("Committing index...");
        idx.commit()?;
    }

    Ok(())
}
