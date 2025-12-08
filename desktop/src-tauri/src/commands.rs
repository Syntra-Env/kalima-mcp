use anyhow::{anyhow, Result};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::{
    collections::{HashMap, HashSet},
    fs,
    sync::Mutex,
};

#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)]
struct SurahSummary {
    number: i64,
    name: String,
    #[serde(default, rename = "ayah_count")]
    ayah_count: Option<i64>,
}

#[derive(Debug, Clone, Deserialize)]
struct SurahInfo {
    number: i64,
    #[serde(default)]
    name: String,
}

#[derive(Debug, Clone, Deserialize)]
struct SurahData {
    surah: SurahInfo,
    verses: Vec<VerseSummary>,
}

#[derive(Debug, Clone, Deserialize)]
struct VerseSummary {
    ayah: i64,
    #[serde(default)]
    text: String,
}

#[derive(Debug, Clone, Deserialize)]
struct Segment {
    #[serde(default)]
    root: Option<String>,
    #[serde(default)]
    pos: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
struct Token {
    text: Option<String>,
    #[serde(default)]
    form: Option<String>,
    #[serde(default)]
    segments: Vec<Segment>,
}

#[derive(Debug, Clone, Deserialize)]
struct Verse {
    surah: SurahInfo,
    ayah: i64,
    #[serde(default)]
    text: String,
    #[serde(default)]
    tokens: Vec<Token>,
}

#[derive(Debug, Clone, Serialize)]
pub struct VerseOutput {
    surah: i64,
    ayah: i64,
    text: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    tokens: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    legend: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct AnalysisToken {
    text: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pos: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    form: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    lemma: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    features: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    role: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    case_: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    gender: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    number: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    definiteness: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    determiner: Option<bool>,
}

#[derive(Debug, Clone, Serialize)]
pub struct AnalysisOutput {
    #[serde(skip_serializing_if = "Option::is_none")]
    header: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    verse_ref: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    text: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    tokens: Option<Vec<AnalysisToken>>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(tag = "output_type", rename_all = "lowercase")]
pub enum CommandOutput {
    Verse(VerseOutput),
    Analysis(AnalysisOutput),
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
}

#[derive(Debug, Clone)]
pub struct AppState {
    current_verse: Option<Verse>,
    base_url: String,
    surahs: Vec<SurahSummary>,
    client: reqwest::blocking::Client,
}

impl AppState {
    fn new() -> Self {
        Self {
            current_verse: None,
            base_url: "http://127.0.0.1:8080".to_string(),
            surahs: Vec::new(),
            client: reqwest::blocking::Client::builder()
                .build()
                .expect("reqwest client"),
        }
    }

    #[cfg(test)]
    fn new_with_base_url(base: &str) -> Self {
        Self {
            current_verse: None,
            base_url: base.to_string(),
            surahs: Vec::new(),
            client: reqwest::blocking::Client::builder()
                .build()
                .expect("reqwest client"),
        }
    }

    fn prompt(&self) -> String {
        if let Some(v) = &self.current_verse {
            format!("kalima ({}:{}) >", v.surah.number, v.ayah)
        } else {
            "kalima >".to_string()
        }
    }
}

lazy_static::lazy_static! {
    static ref APP_STATE: Mutex<AppState> = Mutex::new(AppState::new());
    static ref FALLBACK_MORPH: Mutex<Option<HashMap<(i64, i64), Vec<Value>>>> = Mutex::new(None);
    static ref FALLBACK_MASAQ: Mutex<Option<HashMap<(i64, i64), Vec<Value>>>> = Mutex::new(None);
}

#[tauri::command]
pub fn execute_command(command: String) -> CommandResult {
    let mut state = APP_STATE.lock().unwrap();

    match handle_command(&mut state, &command) {
        Ok(output) => CommandResult {
            output: Some(output),
            prompt: state.prompt(),
        },
        Err(e) => CommandResult {
            output: Some(CommandOutput::Error {
                message: format!("Error: {}", e),
            }),
            prompt: state.prompt(),
        },
    }
}

fn handle_command(state: &mut AppState, line: &str) -> Result<CommandOutput> {
    let mut parts = line.split_whitespace();
    let cmd = parts.next().ok_or_else(|| anyhow!("empty command"))?;
    let rest = parts.collect::<Vec<_>>().join(" ");

    match cmd {
        "inspect" => {
            if rest.is_empty() {
                inspect_current(state)
            } else if rest.contains(':') {
                let (s, a) = parse_verse_ref(&rest)?;
                let verse = fetch_verse(state, s, a)?;
                state.current_verse = Some(verse.clone());
                inspect_specific(state, &verse)
            } else {
                Err(anyhow!(
                    "usage: inspect [<surah:ayah>] (single command shows all available linguistic data)"
                ))
            }
        }
        "see" => {
            // Shorthand: allow `see <surah:ayah>` without the `verse` keyword
            if !rest.contains(' ') && rest.contains(':') {
                let (s, a) = parse_verse_ref(&rest)?;
                return see_specific_verse(state, s, a);
            }

            let mut args = rest.split_whitespace();
            let subtype = args.next().ok_or_else(|| {
                anyhow!("usage: see <book|chapter|verse|sentence|word|morpheme|letter> [value]")
            })?;
            let tail = args.collect::<Vec<_>>().join(" ");
            match subtype {
                "chapter" => {
                    let num = parse_number(&tail)?;
                    see_chapter(state, num)
                }
                "verse" => {
                    // Allow either a simple ayah number (if a surah is in scope) or a fully-qualified surah:ayah
                    if tail.contains(':') {
                        let (s, a) = parse_verse_ref(&tail)?;
                        see_specific_verse(state, s, a)
                    } else {
                        let num = parse_number(&tail)?;
                        see_verse(state, num)
                    }
                }
                "sentence" => {
                    let num = parse_number(&tail)?;
                    see_sentence(num)
                }
                "word" => {
                    let num = parse_number(&tail)?;
                    see_word(state, num)
                }
                "morpheme" => {
                    let key = tail.trim();
                    if key.is_empty() {
                        Err(anyhow!("usage: see morpheme <morpheme_letter>"))
                    } else {
                        see_morpheme(state, key)
                    }
                }
                "letter" => {
                    let num = parse_number(&tail)?;
                    see_letter(state, num)
                }
                _ => Err(anyhow!("unknown see subcommand: {}", subtype)),
            }
        }
        "clear" => Ok(CommandOutput::Clear),
        "help" => Ok(CommandOutput::Info {
            message: print_help(),
        }),
        "status" => Ok(CommandOutput::Info {
            message: format!(
                "base_url: {} | current_verse: {} | surahs_cached: {}",
                state.base_url,
                state
                    .current_verse
                    .as_ref()
                    .map(|v| format!("{}:{}", v.surah.number, v.ayah))
                    .unwrap_or_else(|| "none".into()),
                state.surahs.len()
            ),
        }),
        "exit" | "quit" => std::process::exit(0),
        _ => Err(anyhow!(
            "unknown command: {}. Type 'help' for available commands.",
            cmd
        )),
    }
}

fn inspect_current(state: &AppState) -> Result<CommandOutput> {
    if let Some(v) = &state.current_verse {
        inspect_specific(state, v)
    } else {
        Err(anyhow!(
            "No verse in focus. Use 'search <surah:ayah>' first."
        ))
    }
}

fn inspect_specific(state: &AppState, verse: &Verse) -> Result<CommandOutput> {
    // Try to pull full morphology and dependency data; fall back to verse tokens.
    let mut morph_segments =
        fetch_morphology(state, verse.surah.number, verse.ayah).unwrap_or_default();
    let dependencies = fetch_dependency(state, verse.surah.number, verse.ayah).unwrap_or_default();

    // If morphology is missing or clearly incomplete, try a local fallback corpus.
    let expected_tokens = verse
        .tokens
        .len()
        .max(verse.text.split_whitespace().count());
    let mut used_fallback = false;
    if morph_segments.len() < expected_tokens {
        let masaq = load_masaq_morphology(verse.surah.number, verse.ayah);
        if !masaq.is_empty() {
            morph_segments = masaq;
            used_fallback = true;
        } else {
            let fallback = load_fallback_morphology(verse.surah.number, verse.ayah);
            if !fallback.is_empty() {
                morph_segments = fallback;
                used_fallback = true;
            }
        }
    }
    let tokens = build_analysis_tokens(verse, &morph_segments, &dependencies, !used_fallback);

    Ok(CommandOutput::Analysis(AnalysisOutput {
        header: Some("=== Full Linguistic Analysis ===".to_string()),
        verse_ref: Some(format!("{}:{}", verse.surah.number, verse.ayah)),
        text: Some(verse.text.clone()),
        tokens: Some(tokens),
    }))
}

fn see_chapter(state: &mut AppState, number: i64) -> Result<CommandOutput> {
    let surah = fetch_surah(state, number)?;

    // Keep context on the first ayah of this surah for follow-up commands.
    if let Some(first) = surah.verses.first() {
        let verse = fetch_verse(state, number, first.ayah)?;
        state.current_verse = Some(verse);
    }

    let mut content = String::new();
    content.push_str(&format!(
        "=== Surah {}: {} ===\n\n",
        surah.surah.number, surah.surah.name
    ));
    for verse in &surah.verses {
        content.push_str(&format!(
            "{}:{}  {}\n",
            surah.surah.number, verse.ayah, verse.text
        ));
    }

    Ok(CommandOutput::Pager { content })
}

fn see_verse(state: &mut AppState, ayah: i64) -> Result<CommandOutput> {
    let surah_num = state
        .current_verse
        .as_ref()
        .map(|v| v.surah.number)
        .ok_or_else(|| {
            anyhow!("No surah in context. Use 'see chapter <N>' or 'see verse <surah:ayah>' first.")
        })?;

    let verse = fetch_verse(state, surah_num, ayah)?;
    state.current_verse = Some(verse.clone());
    Ok(render_verse(&verse))
}

fn see_specific_verse(state: &mut AppState, surah: i64, ayah: i64) -> Result<CommandOutput> {
    let verse = fetch_verse(state, surah, ayah)?;
    state.current_verse = Some(verse.clone());
    Ok(render_verse(&verse))
}

fn see_sentence(number: i64) -> Result<CommandOutput> {
    Ok(CommandOutput::Warning {
        message: format!(
            "Sentence {} view is not available yet (sentences can span multiple ayat).",
            number
        ),
    })
}

fn see_word(state: &AppState, word_num: i64) -> Result<CommandOutput> {
    let verse = state
        .current_verse
        .as_ref()
        .ok_or_else(|| anyhow!("No verse in focus. Use 'search <surah:ayah>' first."))?;

    let idx = (word_num - 1) as usize;
    let token = verse
        .tokens
        .get(idx)
        .ok_or_else(|| anyhow!("Word {} not found in current verse", word_num))?;

    let mut details = Vec::new();
    let token_text = token.text.clone().unwrap_or_default();
    details.push(AnalysisToken {
        text: token_text.clone(),
        root: token.segments.get(0).and_then(|s| s.root.clone()),
        pos: token.segments.get(0).and_then(|s| s.pos.clone()),
        form: token.form.clone(),
        lemma: None,
        features: None,
        role: None,
        case_: None,
        gender: None,
        number: None,
        definiteness: None,
        determiner: None,
    });

    Ok(CommandOutput::Analysis(AnalysisOutput {
        header: Some(format!("=== Word {} ===", word_num)),
        verse_ref: Some(format!("{}:{}", verse.surah.number, verse.ayah)),
        text: Some(token_text),
        tokens: Some(details),
    }))
}

fn see_morpheme(state: &AppState, key: &str) -> Result<CommandOutput> {
    let verse = state
        .current_verse
        .as_ref()
        .ok_or_else(|| anyhow!("No verse in focus. Use 'search <surah:ayah>' first."))?;

    // We do not have distinct morpheme labels; surface what we have so the command still responds.
    let mut lines = Vec::new();
    for (t_idx, token) in verse.tokens.iter().enumerate() {
        for (s_idx, seg) in token.segments.iter().enumerate() {
            let root = seg.root.clone().unwrap_or_else(|| "?".to_string());
            let pos = seg.pos.clone().unwrap_or_else(|| "?".to_string());
            lines.push(format!(
                "Word {} segment {} -> root: {}, pos: {}",
                t_idx + 1,
                s_idx + 1,
                root,
                pos
            ));
        }
    }

    if lines.is_empty() {
        return Ok(CommandOutput::Warning {
            message: "No morpheme data available for the current verse.".to_string(),
        });
    }

    let mut content = String::new();
    content.push_str(&format!(
        "Morpheme view (requested key: {}). Using available segment data:\n\n",
        key
    ));
    content.push_str(&lines.join("\n"));

    Ok(CommandOutput::Pager { content })
}

fn see_letter(_state: &AppState, number: i64) -> Result<CommandOutput> {
    Ok(CommandOutput::Warning {
        message: format!(
            "Letter-level zoom for letter {} is not supported yet.",
            number
        ),
    })
}

fn render_verse(verse: &Verse) -> CommandOutput {
    CommandOutput::Verse(VerseOutput {
        surah: verse.surah.number,
        ayah: verse.ayah,
        text: verse.text.clone(),
        tokens: None,
        legend: None,
    })
}

fn build_analysis_tokens(
    verse: &Verse,
    morphology: &[Value],
    dependencies: &[Value],
    include_text_fallback: bool,
) -> Vec<AnalysisToken> {
    let mut seen_keys: HashSet<String> = HashSet::new();
    let mut tokens: Vec<AnalysisToken> = Vec::new();

    // Prefer morphology when available, but we will append any verse tokens not covered.
    if !morphology.is_empty() {
        for seg in morphology {
            let text = seg
                .get("text")
                .and_then(Value::as_str)
                .unwrap_or("")
                .to_string();
            let pos = seg.get("pos").and_then(Value::as_str).map(|s| s.to_string());
            let dep = seg
                .get("dependency_rel")
                .and_then(Value::as_str)
                .map(|s| s.to_string());
            let root = seg
                .get("root")
                .and_then(Value::as_str)
                .map(|s| s.to_string());
            let form = seg
                .get("form")
                .and_then(Value::as_str)
                .map(|s| s.to_string());
            let seg_type = seg.get("type").and_then(Value::as_str);
            let lemma = seg.get("lemma").and_then(Value::as_str).map(|s| s.to_string());
            let features = seg
                .get("features")
                .and_then(Value::as_str)
                .map(|s| s.to_string());

            let mut label = text.clone();
            if let Some(t) = seg_type {
                label = format!("{} ({})", label, t);
            }
            let pos_label = if let Some(dep_rel) = dep {
                Some(if let Some(p) = &pos {
                    format!("{} | dep: {}", p, dep_rel)
                } else {
                    format!("dep: {}", dep_rel)
                })
            } else {
                pos.clone()
            };

            let key = form
                .as_ref()
                .map(|s| s.to_lowercase())
                .unwrap_or_else(|| text.to_lowercase());
            if !key.is_empty() {
                seen_keys.insert(key.clone());
            }
            if !text.is_empty() {
                seen_keys.insert(text.to_lowercase());
            }

            tokens.push(AnalysisToken {
                text: label,
                root,
                pos: pos_label,
                form: form.or_else(|| pos.clone()),
                lemma,
                features,
                role: seg
                    .get("role")
                    .and_then(Value::as_str)
                    .map(|s| s.to_string()),
                case_: seg.get("case").and_then(Value::as_str).map(|s| s.to_string()),
                gender: seg.get("gender").and_then(Value::as_str).map(|s| s.to_string()),
                number: seg.get("number").and_then(Value::as_str).map(|s| s.to_string()),
                definiteness: seg
                    .get("definiteness")
                    .and_then(Value::as_str)
                    .map(|s| s.to_string()),
                determiner: seg.get("determiner").and_then(Value::as_bool),
            });
        }
    }

    if include_text_fallback {
        // Append any verse tokens not already represented in morphology.
        let verse_tokens: Vec<AnalysisToken> = verse
            .tokens
            .iter()
            .flat_map(|token| {
                let base_text = token
                    .form
                    .clone()
                    .or_else(|| token.text.clone())
                    .unwrap_or_default();
                let key = base_text.to_lowercase();
                if !key.is_empty() && seen_keys.contains(&key) {
                    return Vec::new();
                }

                if token.segments.is_empty() {
                    // If the token text looks like an entire verse (contains whitespace), split into words.
                    if base_text.contains(char::is_whitespace) {
                        let mut word_tokens = Vec::new();
                        for w in base_text.split_whitespace() {
                            let key = w.to_lowercase();
                            if key.is_empty() || seen_keys.contains(&key) {
                                continue;
                            }
                            seen_keys.insert(key);
                            word_tokens.push(AnalysisToken {
                                text: w.to_string(),
                                root: None,
                                pos: None,
                                form: None,
                                lemma: None,
                                features: None,
                                role: None,
                                case_: None,
                                gender: None,
                                number: None,
                                definiteness: None,
                                determiner: None,
                            });
                        }
                        return word_tokens;
                    }

                    return vec![AnalysisToken {
                        text: base_text.clone(),
                        root: None,
                        pos: None,
                        form: token.form.clone(),
                        lemma: None,
                        features: None,
                        role: None,
                        case_: None,
                        gender: None,
                        number: None,
                        definiteness: None,
                        determiner: None,
                    }];
                }

                token
                    .segments
                    .iter()
                    .map(|seg| {
                        let mut label = base_text.clone();
                        if let Some(t) = &seg.pos {
                            label = format!("{} ({})", label, t);
                        }
                        AnalysisToken {
                            text: label,
                            root: seg.root.clone(),
                            pos: seg.pos.clone(),
                            form: token.form.clone(),
                            lemma: None,
                            features: None,
                            role: None,
                            case_: None,
                            gender: None,
                            number: None,
                            definiteness: None,
                            determiner: None,
                        }
                    })
                    .collect::<Vec<_>>()
            })
            .collect();

        tokens.extend(verse_tokens);
    }

    // Final fallback: ensure every whitespace-delimited word in the verse text is present.
    if include_text_fallback {
        for w in verse.text.split_whitespace() {
            let key = w.to_lowercase();
            if !key.is_empty() && !seen_keys.contains(&key) {
                seen_keys.insert(key);
                tokens.push(AnalysisToken {
                    text: w.to_string(),
                    root: None,
                    pos: None,
                    form: None,
                    lemma: None,
                    features: None,
                    role: None,
                    case_: None,
                    gender: None,
                    number: None,
                    definiteness: None,
                    determiner: None,
                });
            }
        }
    }

    if !dependencies.is_empty() {
        for dep in dependencies {
            let rel = dep
                .get("rel_label")
                .and_then(Value::as_str)
                .unwrap_or("dep");
            let word = dep.get("word").and_then(Value::as_str).unwrap_or("");
            let pos = dep
                .get("pos")
                .and_then(Value::as_str)
                .map(|s| s.to_string());
            tokens.push(AnalysisToken {
                text: format!("{} -> {}", rel, word),
                root: None,
                pos,
                form: None,
                lemma: None,
                features: None,
                role: Some(rel.to_string()),
                case_: None,
                gender: None,
                number: None,
                definiteness: None,
                determiner: None,
            });
        }
    }

    tokens
}

fn fetch_surah(state: &AppState, number: i64) -> Result<SurahData> {
    let surah = state
        .client
        .get(format!("{}/api/surah/{}", state.base_url, number))
        .send()?
        .error_for_status()?
        .json::<SurahData>()?;
    Ok(surah)
}

fn fetch_verse(state: &AppState, surah: i64, ayah: i64) -> Result<Verse> {
    let verse = state
        .client
        .get(format!("{}/api/verse/{}/{}", state.base_url, surah, ayah))
        .send()?
        .error_for_status()?
        .json::<Verse>()?;
    validate_verse(&verse)?;
    Ok(verse)
}

fn fetch_morphology(state: &AppState, surah: i64, ayah: i64) -> Result<Vec<Value>> {
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

fn fetch_dependency(state: &AppState, surah: i64, ayah: i64) -> Result<Vec<Value>> {
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

fn load_fallback_morphology(surah: i64, ayah: i64) -> Vec<Value> {
    // Load and cache the corpus once.
    {
        let cache = FALLBACK_MORPH.lock().unwrap();
        if let Some(map) = &*cache {
            if let Some(vals) = map.get(&(surah, ayah)) {
                return vals.clone();
            }
        }
    }

    let path = "datasets/quranic-corpus-morphology-0.4.txt";
    let content = match fs::read_to_string(path) {
        Ok(c) => c,
        Err(_) => return vec![],
    };

    let mut map: HashMap<(i64, i64), Vec<Value>> = HashMap::new();
    for line in content.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let parts: Vec<&str> = line.split('\t').collect();
        if parts.len() < 3 {
            continue;
        }
        // parts[0] like "(1:1:1:1)"
        let ref_str = parts[0].trim_matches('(').trim_matches(')');
        let ref_parts: Vec<&str> = ref_str.split(':').collect();
        if ref_parts.len() < 2 {
            continue;
        }
        let s: i64 = ref_parts.get(0).and_then(|v| v.parse().ok()).unwrap_or(0);
        let a: i64 = ref_parts.get(1).and_then(|v| v.parse().ok()).unwrap_or(0);
        let surface = parts[1].trim();
        let pos = parts[2].trim();
        let tags = parts.get(3).map(|v| v.trim()).unwrap_or("");

        let mut root: Option<String> = None;
        let mut lemma: Option<String> = None;
        let mut seg_type: Option<String> = None;
        let mut case_: Option<String> = None;
        let mut gender: Option<String> = None;
        let mut number: Option<String> = None;
        let mut person: Option<String> = None;
        let mut tense: Option<String> = None;
        let aspect: Option<String> = None;
        let mut mood: Option<String> = None;
        let mut voice: Option<String> = None;
        let mut extra_feats: Vec<String> = Vec::new();
        for t in tags.split('|') {
            if t.starts_with("ROOT:") {
                root = Some(t.trim_start_matches("ROOT:").to_string());
                continue;
            }
            if t.starts_with("LEM:") {
                lemma = Some(t.trim_start_matches("LEM:").to_string());
                continue;
            }
            if seg_type.is_none()
                && (t.eq_ignore_ascii_case("PREFIX") || t.eq_ignore_ascii_case("STEM"))
            {
                seg_type = Some(t.to_string());
                continue;
            }

            let upper = t.to_uppercase();
            match upper.as_str() {
                "GEN" | "ACC" | "NOM" => case_ = Some(upper),
                "DEF" | "INDEF" => extra_feats.push(upper),
                "M" | "F" => gender = Some(upper),
                "SG" | "PL" | "DU" => number = Some(upper),
                "P1" | "P2" | "P3" => person = Some(upper),
                "IMPF" | "PERF" | "IMPV" => tense = Some(upper),
                "SUBJ" | "JUS" | "IND" => mood = Some(upper),
                "ACT" | "PASS" => voice = Some(upper),
                _ => {
                    // Keep anything else we don't explicitly map.
                    extra_feats.push(t.to_string());
                }
            }
        }

        let mut features_parts = Vec::new();
        if let Some(c) = &case_ {
            features_parts.push(format!("case:{}", c));
        }
        if let Some(g) = &gender {
            features_parts.push(format!("gender:{}", g));
        }
        if let Some(n) = &number {
            features_parts.push(format!("number:{}", n));
        }
        if let Some(p) = &person {
            features_parts.push(format!("person:{}", p));
        }
        if let Some(t) = &tense {
            features_parts.push(format!("tense:{}", t));
        }
        if let Some(a) = &aspect {
            features_parts.push(format!("aspect:{}", a));
        }
        if let Some(m) = &mood {
            features_parts.push(format!("mood:{}", m));
        }
        if let Some(v) = &voice {
            features_parts.push(format!("voice:{}", v));
        }
        if !extra_feats.is_empty() {
            features_parts.extend(extra_feats.clone());
        }
        let features_str = if features_parts.is_empty() {
            None
        } else {
            Some(features_parts.join(" | "))
        };

        map.entry((s, a))
            .or_default()
            .push(serde_json::json!({
                "text": surface,
                "pos": pos,
                "root": root,
                "case": case_,
                "gender": gender,
                "number": number,
                "definiteness": if features_parts.iter().any(|f| f.eq_ignore_ascii_case("def") || f.eq_ignore_ascii_case("indef")) {
                    Some(features_parts.iter().find(|f| f.eq_ignore_ascii_case("def") || f.eq_ignore_ascii_case("indef")).unwrap().to_string())
                } else { None::<String> },
                "determiner": None::<bool>,
                "lemma": lemma,
                "features": features_str,
                "form": surface,
                "type": seg_type.unwrap_or_else(|| "stem".into())
            }));
    }

    let result = map.get(&(surah, ayah)).cloned().unwrap_or_default();
    let mut cache = FALLBACK_MORPH.lock().unwrap();
    *cache = Some(map);
    result
}

fn load_masaq_morphology(surah: i64, ayah: i64) -> Vec<Value> {
    {
        let cache = FALLBACK_MASAQ.lock().unwrap();
        if let Some(map) = &*cache {
            if let Some(vals) = map.get(&(surah, ayah)) {
                return vals.clone();
            }
        }
    }

    let path = "datasets/MASAQ.csv";
    let file = match fs::File::open(path) {
        Ok(f) => f,
        Err(_) => return vec![],
    };

    let mut rdr = csv::ReaderBuilder::new()
        .has_headers(true)
        .flexible(true)
        .from_reader(file);

    let mut map: HashMap<(i64, i64), Vec<Value>> = HashMap::new();
    for result in rdr.records() {
        if let Ok(rec) = result {
            let s: i64 = rec.get(1).and_then(|v| v.parse().ok()).unwrap_or(0);
            let a: i64 = rec.get(2).and_then(|v| v.parse().ok()).unwrap_or(0);
            let word = rec.get(5).unwrap_or("").trim();
            let lemma = rec.get(6).unwrap_or("").trim();
            let segmented = rec.get(7).unwrap_or("").trim();
            let morph_tag = rec.get(8).unwrap_or("").trim();
            let morph_type = rec.get(9).unwrap_or("").trim();
            let punctuation = rec.get(10).unwrap_or("").trim();
            let invariable = rec.get(11).unwrap_or("").trim();
            let syntactic_role = rec.get(12).unwrap_or("").trim();
            let possessive = rec.get(13).unwrap_or("").trim();
            let case_mood = rec.get(14).unwrap_or("").trim();
            let case_marker = rec.get(15).unwrap_or("").trim();
            let phrase = rec.get(16).unwrap_or("").trim();
            let phrase_fn = rec.get(17).unwrap_or("").trim();
            let notes = rec.get(18).unwrap_or("").trim();

            let mut features = Vec::new();
            for (label, val) in [
                ("type", morph_type),
                ("punct", punctuation),
                ("invar", invariable),
                ("role", syntactic_role),
                ("poss", possessive),
                ("case", case_mood),
                ("case_marker", case_marker),
                ("phrase", phrase),
                ("phrase_fn", phrase_fn),
                ("notes", notes),
            ] {
                if !val.is_empty() {
                    features.push(format!("{}:{}", label, val));
                }
            }

            let determiner = morph_tag.eq_ignore_ascii_case("DET") || morph_type.eq_ignore_ascii_case("DET");
            let case_field = if !case_mood.is_empty() { Some(case_mood.to_string()) } else { None };

            map.entry((s, a)).or_default().push(serde_json::json!({
                "text": word,
                "lemma": if lemma.is_empty() { None::<String> } else { Some(lemma.to_string()) },
                "pos": if morph_tag.is_empty() { None::<String> } else { Some(morph_tag.to_string()) },
                "form": if segmented.is_empty() { None::<String> } else { Some(segmented.to_string()) },
                "features": if features.is_empty() { None::<String> } else { Some(features.join(" | ")) },
                "type": if morph_type.is_empty() { None::<String> } else { Some(morph_type.to_string()) },
                "role": if syntactic_role.is_empty() { None::<String> } else { Some(syntactic_role.to_string()) },
                "case": case_field,
                "gender": None::<String>,
                "number": None::<String>,
                "definiteness": None::<String>,
                "determiner": Some(determiner),
            }));
        }
    }

    let result = map.get(&(surah, ayah)).cloned().unwrap_or_default();
    let mut cache = FALLBACK_MASAQ.lock().unwrap();
    *cache = Some(map);
    result
}

fn parse_verse_ref(s: &str) -> Result<(i64, i64)> {
    let parts: Vec<_> = s.split(':').collect();
    let surah = parts
        .get(0)
        .ok_or_else(|| anyhow!("missing surah"))?
        .parse()?;
    let ayah = parts
        .get(1)
        .ok_or_else(|| anyhow!("missing ayah"))?
        .parse()?;
    Ok((surah, ayah))
}

fn parse_number(s: &str) -> Result<i64> {
    if let Ok(n) = s.trim().parse::<i64>() {
        return Ok(n);
    }

    let words = [
        ("zero", 0),
        ("one", 1),
        ("two", 2),
        ("three", 3),
        ("four", 4),
        ("five", 5),
        ("six", 6),
        ("seven", 7),
        ("eight", 8),
        ("nine", 9),
        ("ten", 10),
        ("eleven", 11),
        ("twelve", 12),
        ("thirteen", 13),
        ("fourteen", 14),
        ("fifteen", 15),
        ("sixteen", 16),
        ("seventeen", 17),
        ("eighteen", 18),
        ("nineteen", 19),
        ("twenty", 20),
        ("thirty", 30),
        ("forty", 40),
        ("fifty", 50),
        ("sixty", 60),
        ("seventy", 70),
        ("eighty", 80),
        ("ninety", 90),
        ("hundred", 100),
        ("thousand", 1000),
    ];

    let lower = s.trim().to_lowercase();
    let parts: Vec<&str> = lower.split_whitespace().collect();

    if parts.len() == 1 {
        for (word, num) in &words {
            if &lower == word {
                return Ok(*num);
            }
        }
    } else {
        let mut total = 0i64;
        let mut current = 0i64;

        for part in parts {
            let mut found = false;
            for (word, num) in &words {
                if part == *word {
                    if *num >= 100 {
                        current = if current == 0 { 1 } else { current };
                        current *= num;
                    } else {
                        current += num;
                    }
                    found = true;
                    break;
                }
            }
            if !found {
                return Err(anyhow!("unrecognized number word: {}", part));
            }
        }
        total += current;
        return Ok(total);
    }

    Err(anyhow!("invalid number: {}", s))
}

fn print_help() -> String {
    let mut help = String::new();
    help.push_str("=== Kalima CLI Commands ===\n\n");
    help.push_str("Search & Navigate:\n");
    help.push_str("  see chapter <N>           - View a surah\n");
    help.push_str("  see verse <N>             - View an ayah in the current surah\n");
    help.push_str("  see verse <S:A>           - View a specific ayah by surah:ayah\n");
    help.push_str("  see sentence <N>          - View a sentence (may span ayat)\n");
    help.push_str("  see word <N>              - View a specific word in the current verse\n");
    help.push_str("  see morpheme <letter>     - View morpheme details (best-effort)\n");
    help.push_str("  see letter <N>            - View a specific letter (placeholder)\n\n");
    help.push_str("Inspect Linguistic Details:\n");
    help.push_str("  inspect                   - Show full linguistic analysis of current verse\n");
    help.push_str("  inspect <surah:ayah>      - Inspect a specific verse directly\n\n");
    help.push_str("General:\n");
    help.push_str("  clear                     - Clear the interface output\n");
    help.push_str("  status                    - Show current base URL and context state\n");
    help.push_str("  help                      - Show this help\n");
    help.push_str("  exit | quit               - Exit the application\n");
    help
}

fn validate_verse(v: &Verse) -> Result<()> {
    if v.surah.number < 1 {
        anyhow::bail!("invalid surah number {}", v.surah.number);
    }
    if v.ayah < 1 {
        anyhow::bail!("invalid ayah number {}", v.ayah);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn parse_verse_ref_accepts_surah_ayah() {
        assert_eq!(parse_verse_ref("2:5").unwrap(), (2, 5));
    }

    #[test]
    fn parse_number_words_and_digits() {
        assert_eq!(parse_number("12").unwrap(), 12);
        assert_eq!(parse_number("twenty three").unwrap(), 23);
    }

    #[test]
    fn inspect_current_uses_morphology_and_dependencies() {
        let server = httpmock::MockServer::start();

        // Mock morphology and dependency endpoints for 1:1
        let _morph = server.mock(|when, then| {
            when.method(httpmock::Method::GET)
                .path("/api/morphology/1/1");
            then.status(200).json_body(json!({
                "surah": 1,
                "ayah": 1,
                "morphology": [{
                    "text": "بِسْمِ",
                    "pos": "N",
                    "root": "ب س م",
                    "form": "basm",
                    "type": "noun",
                    "dependency_rel": "obj"
                }]
            }));
        });

        let _deps = server.mock(|when, then| {
            when.method(httpmock::Method::GET)
                .path("/api/dependency/1/1");
            then.status(200).json_body(json!({
                "surah": 1,
                "ayah": 1,
                "dependency_tree": [{
                    "rel_label": "subj",
                    "word": "الله",
                    "pos": "N"
                }]
            }));
        });

        let mut state = AppState::new_with_base_url(&server.base_url());
        state.current_verse = Some(Verse {
            surah: SurahInfo { number: 1, name: "Al-Fatiha".into() },
            ayah: 1,
            text: "بِسْمِ ٱللَّهِ".into(),
            tokens: vec![Token {
                text: Some("بِسْمِ".into()),
                form: Some("بِسْمِ".into()),
                segments: vec![],
            }],
        });

        let output = inspect_current(&state).expect("inspect should succeed");
        let analysis = match output {
            CommandOutput::Analysis(a) => a,
            _ => panic!("expected analysis output"),
        };

        assert_eq!(analysis.header.as_deref(), Some("=== Full Linguistic Analysis ==="));
        assert_eq!(analysis.verse_ref.as_deref(), Some("1:1"));
        assert_eq!(analysis.text.as_deref(), Some("بِسْمِ ٱللَّهِ"));

        let tokens = analysis.tokens.unwrap();
        assert!(tokens.iter().any(|t| t.text.contains("بِسْمِ") && t.pos.as_deref() == Some("N | dep: obj")));
        assert!(tokens.iter().any(|t| t.text.contains("subj -> الله") && t.pos.as_deref() == Some("N")));
    }

    #[test]
    fn build_tokens_prefers_morphology_segments() {
        let verse = Verse {
            surah: SurahInfo {
                number: 1,
                name: "Test".into(),
            },
            ayah: 1,
            text: "text".into(),
            tokens: vec![],
        };
        let morph = vec![json!({
            "text": "word",
            "pos": "N",
            "root": "r",
            "form": "f",
            "type": "noun",
            "dependency_rel": "subj"
        })];
        let deps: Vec<Value> = vec![];
        let tokens = build_analysis_tokens(&verse, &morph, &deps, true);
        assert!(tokens.iter().any(|t| t.text == "word (noun)"));
        assert!(tokens.iter().any(|t| t.root.as_deref() == Some("r")));
        assert!(tokens.iter().any(|t| t.pos.as_deref() == Some("N | dep: subj")));
    }

    #[test]
    fn build_tokens_falls_back_to_verse_segments() {
        let verse = Verse {
            surah: SurahInfo {
                number: 1,
                name: "Test".into(),
            },
            ayah: 1,
            text: "text".into(),
            tokens: vec![Token {
                text: Some("base".into()),
                form: Some("form".into()),
                segments: vec![Segment {
                    root: Some("root".into()),
                    pos: Some("POS".into()),
                }],
            }],
        };
        let tokens = build_analysis_tokens(&verse, &[], &[], true);
        assert_eq!(tokens.len(), 2);
        assert!(tokens.iter().any(|t| t.text == "form (POS)" && t.root.as_deref() == Some("root")));
        assert!(tokens.iter().any(|t| t.text == "text"));
    }

    #[test]
    fn build_tokens_includes_dependencies() {
        let verse = Verse {
            surah: SurahInfo {
                number: 1,
                name: "Test".into(),
            },
            ayah: 1,
            text: "text".into(),
            tokens: vec![],
        };
        let morph: Vec<Value> = vec![];
        let deps: Vec<Value> = vec![json!({
            "rel_label": "subj",
            "word": "foo",
            "pos": "N"
        })];
        let tokens = build_analysis_tokens(&verse, &morph, &deps, true);
        assert_eq!(tokens.len(), 2);
        assert!(tokens.iter().any(|t| t.text == "text"));
        assert!(tokens.iter().any(|t| t.text == "subj -> foo" && t.pos.as_deref() == Some("N")));
    }

    #[test]
    fn build_tokens_merges_partial_morphology_with_verse() {
        let verse = Verse {
            surah: SurahInfo {
                number: 1,
                name: "Test".into(),
            },
            ayah: 1,
            text: "text".into(),
            tokens: vec![
                Token {
                    text: Some("first".into()),
                    form: Some("first".into()),
                    segments: vec![],
                },
                Token {
                    text: Some("second".into()),
                    form: Some("second".into()),
                    segments: vec![Segment {
                        root: Some("r2".into()),
                        pos: Some("POS2".into()),
                    }],
                },
            ],
        };
        // Morphology only covers the first token
        let morph = vec![json!({
            "text": "first",
            "pos": "POS1",
            "root": "r1",
            "form": "f1",
            "type": "noun",
        })];
        let deps: Vec<Value> = vec![];
        let tokens = build_analysis_tokens(&verse, &morph, &deps, true);
        assert_eq!(tokens.len(), 3);
        assert!(tokens.iter().any(|t| t.text.contains("first") && t.root.as_deref() == Some("r1")));
        assert!(tokens.iter().any(|t| t.text.contains("second") && t.root.as_deref() == Some("r2")));
        assert!(tokens.iter().any(|t| t.text == "text"));
    }

    #[test]
    fn build_tokens_splits_whole_verse_tokens_into_words() {
        let verse = Verse {
            surah: SurahInfo {
                number: 1,
                name: "Test".into(),
            },
            ayah: 1,
            text: "foo bar baz".into(),
            tokens: vec![Token {
                text: Some("foo bar baz".into()),
                form: Some("foo bar baz".into()),
                segments: vec![],
            }],
        };
        let tokens = build_analysis_tokens(&verse, &[], &[], true);
        assert_eq!(tokens.len(), 3);
        assert!(tokens.iter().any(|t| t.text == "foo"));
        assert!(tokens.iter().any(|t| t.text == "bar"));
        assert!(tokens.iter().any(|t| t.text == "baz"));
    }
}
