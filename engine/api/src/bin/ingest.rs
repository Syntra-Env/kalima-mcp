use common::{SearchBackend, Segment, SegmentView};
use search::TantivyIndex;
use store::SqliteStorage;
use serde::Deserialize;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::sync::Arc;
use structopt::StructOpt;

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
    tense: Option<String>,
    aspect: Option<String>,
    person: Option<String>,
    number: Option<String>,
    gender: Option<String>,
    case: Option<String>,
    dependency_rel: Option<String>,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args = Args::from_args();
    let storage = Arc::new(SqliteStorage::connect(&args.db).await?);
    
    let index = if !args.skip_index {
        Some(Arc::new(TantivyIndex::open_or_create(&args.index)?))
    } else {
        None
    };

    let file = File::open(&args.input)?;
    let reader = BufReader::new(file);

    for line in reader.lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let verse: CorpusVerse = serde_json::from_str(&line)?;
        if let Some(tokens) = verse.tokens {
            for (i, tok) in tokens.into_iter().enumerate() {
                let segs = tok
                    .segments
                    .unwrap_or_default()
                    .into_iter()
                    .enumerate()
                    .map(|(idx, s)| Segment {
                        id: s.id.unwrap_or_else(|| format!("seg-{}-{}-{}", verse.surah.number, verse.ayah, idx)),
                        r#type: s.ty.unwrap_or_default(),
                        form: s.form.unwrap_or_else(|| tok.form.clone()),
                        root: s.root,
                        lemma: s.lemma,
                        pattern: s.pattern,
                        pos: s.pos,
                        verb_form: s.verb_form,
                        voice: s.voice,
                        mood: s.mood,
                        tense: s.tense,
                        aspect: s.aspect,
                        person: s.person,
                        number: s.number,
                        gender: s.gender,
                        case_: s.case,
                        dependency_rel: s.dependency_rel,
                    })
                    .collect::<Vec<_>>();

                let token_id = tok
                    .id
                    .map(|v| v.to_string().trim_matches('"').to_string())
                    .unwrap_or_else(|| format!("{}:{}:{}", verse.surah.number, verse.ayah, i));
                let doc = SegmentView {
                    id: token_id.clone(),
                    verse_ref: format!("{}:{}", verse.surah.number, verse.ayah),
                    token_index: i,
                    text: verse.text.clone().unwrap_or_else(|| tok.form.clone()),
                    segments: segs,
                    annotations: vec![],
                };
                storage.upsert_segment(&doc).await?;
                if let Some(idx) = &index {
                    idx.index_document(&doc).await?;
                }
            }
        }
    }

    if let Some(idx) = &index {
        println!("Committing index...");
        idx.commit()?;
    }

    Ok(())
}
