use anyhow::{anyhow, Result};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::{
    collections::{HashMap, HashSet},
    fs,
    sync::Mutex,
    time::{SystemTime, UNIX_EPOCH},
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

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Mode {
    Read,
    Write,
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
    tree: Option<String>,
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
    #[serde(skip_serializing_if = "Option::is_none")]
    pub prefill: Option<String>,
}

#[derive(Debug, Clone)]
pub struct AppState {
    current_verse: Option<Verse>,
    base_url: String,
    surahs: Vec<SurahSummary>,
    interpretations: HashMap<String, Vec<(String, String)>>, // (id, text)
    mode: Mode,
    editing: Option<(i64, i64, usize)>, // surah, ayah, index (0-based)
    client: reqwest::blocking::Client,
}

#[derive(Debug, Clone)]
struct CommandResponse {
    output: CommandOutput,
    prefill: Option<String>,
}

const ARABIC_SURAH_NAMES: [&str; 114] = [
    "الفاتحة",
    "البقرة",
    "آل عمران",
    "النساء",
    "المائدة",
    "الأنعام",
    "الأعراف",
    "الأنفال",
    "التوبة",
    "يونس",
    "هود",
    "يوسف",
    "الرعد",
    "إبراهيم",
    "الحجر",
    "النحل",
    "الإسراء",
    "الكهف",
    "مريم",
    "طه",
    "الأنبياء",
    "الحج",
    "المؤمنون",
    "النور",
    "الفرقان",
    "الشعراء",
    "النمل",
    "القصص",
    "العنكبوت",
    "الروم",
    "لقمان",
    "السجدة",
    "الأحزاب",
    "سبإ",
    "فاطر",
    "يس",
    "الصافات",
    "ص",
    "الزمر",
    "غافر",
    "فصلت",
    "الشورى",
    "الزخرف",
    "الدخان",
    "الجاثية",
    "الأحقاف",
    "محمد",
    "الفتح",
    "الحجرات",
    "ق",
    "الذاريات",
    "الطور",
    "النجم",
    "القمر",
    "الرحمن",
    "الواقعة",
    "الحديد",
    "المجادلة",
    "الحشر",
    "الممتحنة",
    "الصف",
    "الجمعة",
    "المنافقون",
    "التغابن",
    "الطلاق",
    "التحريم",
    "الملك",
    "القلم",
    "الحاقة",
    "المعارج",
    "نوح",
    "الجن",
    "المزمل",
    "المدثر",
    "القيامة",
    "الإنسان",
    "المرسلات",
    "النبإ",
    "النازعات",
    "عبس",
    "التكوير",
    "الانفطار",
    "المطففين",
    "الانشقاق",
    "البروج",
    "الطارق",
    "الأعلى",
    "الغاشية",
    "الفجر",
    "البلد",
    "الشمس",
    "الليل",
    "الضحى",
    "الشرح",
    "التين",
    "العلق",
    "القدر",
    "البينة",
    "الزلزلة",
    "العاديات",
    "القارعة",
    "التكاثر",
    "العصر",
    "الهمزة",
    "الفيل",
    "قريش",
    "الماعون",
    "الكوثر",
    "الكافرون",
    "النصر",
    "المسد",
    "الإخلاص",
    "الفلق",
    "الناس",
];

impl AppState {
    fn new() -> Self {
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
    fn new_with_base_url(base: &str) -> Self {
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

    fn prompt(&self) -> String {
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

fn surah_name_or_fallback(number: i64, name: &str) -> String {
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
    static ref APP_STATE: Mutex<AppState> = Mutex::new(AppState::new());
    static ref FALLBACK_MORPH: Mutex<Option<HashMap<(i64, i64), Vec<Value>>>> = Mutex::new(None);
    static ref FALLBACK_MASAQ: Mutex<Option<HashMap<(i64, i64), Vec<Value>>>> = Mutex::new(None);
}

#[tauri::command]
pub fn execute_command(command: String) -> CommandResult {
    let mut state = APP_STATE.lock().unwrap();

    match handle_command(&mut state, &command) {
        Ok(resp) => CommandResult {
            output: Some(resp.output),
            prompt: state.prompt(),
            prefill: resp.prefill,
        },
        Err(e) => CommandResult {
            output: Some(CommandOutput::Error {
                message: format!("Error: {}", e),
            }),
            prompt: state.prompt(),
            prefill: None,
        },
    }
}

fn resp(output: CommandOutput) -> Result<CommandResponse> {
    Ok(CommandResponse {
        output,
        prefill: None,
    })
}

fn handle_command(state: &mut AppState, line: &str) -> Result<CommandResponse> {
    // When in editing mode, any non-empty line replaces the targeted interpretation.
    if state.editing.is_some() && !line.trim().is_empty() {
        let (s, a, idx) = state.editing.unwrap();
        let list = state
            .interpretations
            .get(&interp_key(s, a))
            .cloned()
            .unwrap_or_else(Vec::new);
        if idx >= list.len() {
            anyhow::bail!("editing target out of range; try 'write' again.");
        }
        let old_id = &list[idx].0;

        // Delete existing annotation, then save replacement.
        let _ = state
            .client
            .delete(format!("{}/annotations/{}", state.base_url, old_id))
            .send();
        save_interpretation(state, s, a, line.trim())?;
        state.editing = None;

        // Refresh list
        let interp = Some(fetch_interpretations_with_ids(state, s, a)?);
        let verse = fetch_verse(state, s, a)?;
        state.current_verse = Some(verse.clone());
        state.mode = Mode::Write;

        return resp(CommandOutput::Pager {
            content: {
                let mut c = String::from("=== Interpretation (write mode) ===\n\n");
                c.push_str(&render_verse_line(&verse, interp, Mode::Write));
                c
            },
        });
    }

    let mut parts = line.split_whitespace();
    let cmd = parts.next().ok_or_else(|| anyhow!("empty command"))?;
    let rest = parts.collect::<Vec<_>>().join(" ");

    match cmd {
        "inspect" => {
            if rest.is_empty() {
                resp(inspect_current(state)?)
            } else if rest.contains(':') {
                let (s, a) = parse_verse_ref(&rest)?;
                let verse = fetch_verse(state, s, a)?;
                state.current_verse = Some(verse.clone());
                resp(inspect_specific(state, &verse)?)
            } else {
                Err(anyhow!(
                    "usage: inspect [<surah:ayah>] (single command shows all available linguistic data)"
                ))
            }
        }
        "read" => {
            state.mode = Mode::Read;
            let trimmed = rest.trim();

            // No args: show current verse if present.
            if trimmed.is_empty() {
                if let Some(v) = &state.current_verse {
                    return resp(read_specific_verse(state, v.surah.number, v.ayah)?);
                } else {
                    anyhow::bail!("No verse in focus. Use 'read <surah:ayah>' first.");
                }
            }

            // Shorthand: allow `read <surah:ayah>` without the `verse` keyword
            if !trimmed.contains(' ') && trimmed.contains(':') {
                let (s, a) = parse_verse_ref(trimmed)?;
                return resp(read_specific_verse(state, s, a)?);
            }
            // Shorthand: allow `read <ayah>` within current surah
            if !trimmed.contains(' ') && trimmed.chars().all(|c| c.is_ascii_digit()) {
                let num = parse_number(trimmed)?;
                return resp(read_verse(state, num)?);
            }

            let mut args = trimmed.split_whitespace();
            let subtype = args.next().ok_or_else(|| {
                anyhow!("usage: read <book|chapters|chapter|verse|sentence|word|morpheme|letter> [value]")
            })?;
            let tail = args.collect::<Vec<_>>().join(" ");
            match subtype {
                "chapters" => resp(read_chapters(state)?),
                "chapter" => {
                    let num = parse_number(&tail)?;
                    resp(read_chapter(state, num)?)
                }
                "verse" => {
                    // Allow either a simple ayah number (if a surah is in scope) or a fully-qualified surah:ayah
                    if tail.contains(':') {
                        let (s, a) = parse_verse_ref(&tail)?;
                        resp(read_specific_verse(state, s, a)?)
                    } else {
                        let num = parse_number(&tail)?;
                        resp(read_verse(state, num)?)
                    }
                }
                "sentence" => {
                    let num = parse_number(&tail)?;
                    resp(read_sentence(num)?)
                }
                "word" => {
                    let num = parse_number(&tail)?;
                    resp(read_word(state, num)?)
                }
                "morpheme" => {
                    let key = tail.trim();
                    if key.is_empty() {
                        Err(anyhow!("usage: read morpheme <morpheme_letter>"))
                    } else {
                        resp(read_morpheme(state, key)?)
                    }
                }
                "letter" => {
                    let num = parse_number(&tail)?;
                    resp(read_letter(state, num)?)
                }
                _ => Err(anyhow!("unknown read subcommand: {}", subtype)),
            }
        }
        "write" => resp(handle_write(state, &rest)?),
        "edit" => handle_edit(state, &rest),
        "clear" => resp(CommandOutput::Clear),
        "help" => resp(CommandOutput::Info {
            message: print_help(),
        }),
        "status" => resp(CommandOutput::Info {
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
        "legend" => resp(CommandOutput::Info {
            message: "Colors: role subj=green, obj=red, comp=blue, other=gold. POS is blue text. Case is cyan text.".to_string(),
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
    let morph_segments =
        fetch_morphology(state, verse.surah.number, verse.ayah).unwrap_or_default();
    let dependencies = fetch_dependency(state, verse.surah.number, verse.ayah).unwrap_or_default();

    // Validate morphology coverage based on actual indices present.
    if morph_segments.is_empty() {
        anyhow::bail!(
            "No morphology data for {}:{}; check database ingestion.",
            verse.surah.number,
            verse.ayah
        );
    }

    let mut raw_indices: Vec<usize> = Vec::new();
    for seg in &morph_segments {
        if let Some(idx) = seg
            .get("word_index")
            .and_then(Value::as_u64)
            .map(|v| v as usize)
        {
            raw_indices.push(idx);
        } else if let Some(idx) = seg
            .get("token_index")
            .and_then(Value::as_u64)
            .map(|v| v as usize)
        {
            raw_indices.push(idx);
        }
    }
    if raw_indices.is_empty() {
        anyhow::bail!(
            "Morphology for {}:{} has no word indices; check dataset.",
            verse.surah.number,
            verse.ayah
        );
    }
    let min_idx = *raw_indices.iter().min().unwrap_or(&1);
    let normalized: HashSet<usize> = raw_indices
        .iter()
        .map(|i| if min_idx == 0 { i + 1 } else { *i })
        .collect();
    let max_idx = *normalized.iter().max().unwrap_or(&1);
    let expected_tokens = if verse.tokens.is_empty() {
        max_idx
    } else {
        verse.tokens.len().max(max_idx)
    };
    for idx in 1..=expected_tokens {
        if !normalized.contains(&idx) {
            anyhow::bail!(
                "Incomplete morphology for {}:{}; missing word {} of {}.",
                verse.surah.number,
                verse.ayah,
                idx,
                expected_tokens
            );
        }
    }

    let _tokens = build_analysis_tokens(verse, &morph_segments, &dependencies, false);
    let tree = build_tree_display(verse, &morph_segments);

    Ok(CommandOutput::Analysis(AnalysisOutput {
        header: Some("=== Full Linguistic Analysis ===".to_string()),
        verse_ref: Some(format!("{}:{}", verse.surah.number, verse.ayah)),
        text: Some(verse.text.clone()),
        tree: Some(tree),
        tokens: None,
    }))
}

fn render_verse_line(verse: &Verse, interp: Option<Vec<(String, String)>>, mode: Mode) -> String {
    let mut content = format!("{}:{}  {}\n", verse.surah.number, verse.ayah, verse.text);
    if mode == Mode::Write {
        let list = interp.unwrap_or_else(Vec::new);
        if list.is_empty() {
            content.push_str("(no interpretations yet)\n\n");
        } else {
            for (idx, item) in list.iter().enumerate() {
                content.push_str(&format!("{}. {}\n", idx + 1, item.1));
            }
            content.push('\n');
        }
    }
    content
}

fn read_chapter(state: &mut AppState, number: i64) -> Result<CommandOutput> {
    let surah = fetch_surah(state, number)?;
    let surah_name = surah_name_or_fallback(surah.surah.number, &surah.surah.name);

    // Keep context on the first ayah of this surah for follow-up commands.
    if let Some(first) = surah.verses.first() {
        let verse = fetch_verse(state, number, first.ayah)?;
        state.current_verse = Some(verse);
    }

    let mut content = String::new();
    content.push_str(&format!(
        "=== Surah {}: {} ===\n\n",
        surah.surah.number, surah_name
    ));
    for verse in &surah.verses {
        // Some datasets omit verse_texts for certain ayat (e.g., 1:1); fetch full verse as fallback.
        let verse_full = if verse.text.trim().is_empty() {
            fetch_verse(state, surah.surah.number, verse.ayah)?
        } else {
            Verse {
                surah: SurahInfo {
                    number: surah.surah.number,
                    name: surah.surah.name.clone(),
                },
                ayah: verse.ayah,
                text: verse.text.clone(),
                tokens: vec![],
            }
        };
        let interp = match state.mode {
            Mode::Write => Some(fetch_interpretations_with_ids(
                state,
                surah.surah.number,
                verse.ayah,
            )?),
            Mode::Read => None,
        };
        content.push_str(&render_verse_line(&verse_full, interp, state.mode));
    }

    Ok(CommandOutput::Pager { content })
}

fn parse_write_target(state: &AppState, rest: &str) -> Result<((i64, i64), String)> {
    let trimmed = rest.trim();
    if trimmed.is_empty() {
        if let Some(v) = &state.current_verse {
            return Ok(((v.surah.number, v.ayah), String::new()));
        } else {
            anyhow::bail!("No verse in focus. Use 'write <surah:ayah>' to set a target.");
        }
    }

    let mut parts = trimmed.splitn(2, ' ');
    let first = parts.next().unwrap_or_default();
    let remaining = parts.next().unwrap_or("").trim_start().to_string();

    if first.contains(':') {
        let (s, a) = parse_verse_ref(first)?;
        Ok(((s, a), remaining))
    } else {
        let ayah = parse_number(first)?;
        let surah = state
            .current_verse
            .as_ref()
            .map(|v| v.surah.number)
            .ok_or_else(|| anyhow!("No surah in context. Use 'write <surah:ayah>' first."))?;
        Ok(((surah, ayah), remaining))
    }
}

fn handle_write(state: &mut AppState, rest: &str) -> Result<CommandOutput> {
    state.mode = Mode::Write;
    state.editing = None;

    let trimmed = rest.trim();
    if let Some(rem) = trimmed.strip_prefix("chapter") {
        let num = parse_number(rem.trim())?;
        return read_chapter(state, num);
    }

    let ((surah, ayah), note_text) = parse_write_target(state, trimmed)?;
    if !note_text.is_empty() {
        save_interpretation(state, surah, ayah, &note_text)?;
    }

    let verse = fetch_verse(state, surah, ayah)?;
    state.current_verse = Some(verse.clone());
        let interp_ids = fetch_interpretations_with_ids(state, surah, ayah)?;
        let interp = Some(interp_ids.clone());

        let mut content = String::new();
        content.push_str("=== Interpretation (write mode) ===\n\n");
        content.push_str(&render_verse_line(&verse, interp, Mode::Write));

        Ok(CommandOutput::Pager { content })
}

fn handle_edit(state: &mut AppState, rest: &str) -> Result<CommandResponse> {
    if state.mode != Mode::Write {
        anyhow::bail!("edit only works in write mode. Use 'write' first.");
    }
    let (surah_num, ayah_num) = {
        let verse = state
            .current_verse
            .as_ref()
            .ok_or_else(|| anyhow!("No verse in focus. Use 'write <surah:ayah>' first."))?;
        (verse.surah.number, verse.ayah)
    };

    let idx: usize = rest
        .trim()
        .parse()
        .map_err(|_| anyhow!("usage: edit <interpretation_number>"))?;
    let list = fetch_interpretations_with_ids(state, surah_num, ayah_num)?;
    if idx == 0 || idx > list.len() {
        anyhow::bail!("interpretation {} not found ({} total).", idx, list.len());
    }
    let text = list[idx - 1].1.clone();
    state.editing = Some((surah_num, ayah_num, idx - 1));

    Ok(CommandResponse {
        output: CommandOutput::Info {
            message: format!("Editing interpretation {}.", idx),
        },
        prefill: Some(text),
    })
}

fn read_chapters(state: &mut AppState) -> Result<CommandOutput> {
    if state.surahs.is_empty() {
        state.surahs = fetch_surah_list(state)?;
    }

    let mut content = String::from("=== Chapters ===\n\n");
    for s in &state.surahs {
        let name = surah_name_or_fallback(s.number, &s.name);
        content.push_str(&format!("{}. {}\n", s.number, name));
    }

    Ok(CommandOutput::Pager { content })
}

fn read_verse(state: &mut AppState, ayah: i64) -> Result<CommandOutput> {
    let surah_num = state
        .current_verse
        .as_ref()
        .map(|v| v.surah.number)
        .ok_or_else(|| {
            anyhow!("No surah in context. Use 'read chapter <N>' or 'read verse <surah:ayah>' first.")
        })?;

    let verse = fetch_verse(state, surah_num, ayah)?;
    state.current_verse = Some(verse.clone());
    Ok(render_verse(&verse))
}

fn read_specific_verse(state: &mut AppState, surah: i64, ayah: i64) -> Result<CommandOutput> {
    let verse = fetch_verse(state, surah, ayah)?;
    state.current_verse = Some(verse.clone());
    Ok(render_verse(&verse))
}

fn read_sentence(number: i64) -> Result<CommandOutput> {
    Ok(CommandOutput::Warning {
        message: format!(
            "Sentence {} view is not available yet (sentences can span multiple ayat).",
            number
        ),
    })
}

fn read_word(state: &AppState, word_num: i64) -> Result<CommandOutput> {
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
        tree: None,
        tokens: Some(details),
    }))
}

fn read_morpheme(state: &AppState, key: &str) -> Result<CommandOutput> {
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

fn read_letter(_state: &AppState, number: i64) -> Result<CommandOutput> {
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

    consolidate_tokens(tokens)
}

fn consolidate_tokens(tokens: Vec<AnalysisToken>) -> Vec<AnalysisToken> {
    let mut map: HashMap<String, AnalysisToken> = HashMap::new();
    for t in tokens {
        let key = t.text.to_lowercase();
        map.entry(key)
            .and_modify(|existing| {
                if existing.pos.is_none() {
                    existing.pos = t.pos.clone();
                }
                if existing.root.is_none() {
                    existing.root = t.root.clone();
                }
                if existing.lemma.is_none() {
                    existing.lemma = t.lemma.clone();
                }
                if existing.form.is_none() {
                    existing.form = t.form.clone();
                }
                if existing.features.is_none() {
                    existing.features = t.features.clone();
                }
                if existing.role.is_none() {
                    existing.role = t.role.clone();
                }
                if existing.case_.is_none() {
                    existing.case_ = t.case_.clone();
                }
                if existing.gender.is_none() {
                    existing.gender = t.gender.clone();
                }
                if existing.number.is_none() {
                    existing.number = t.number.clone();
                }
                if existing.definiteness.is_none() {
                    existing.definiteness = t.definiteness.clone();
                }
                if existing.determiner.is_none() {
                    existing.determiner = t.determiner;
                }
            })
            .or_insert(t);
    }
    map.into_values().collect()
}

fn pos_long_form(tag: &str) -> String {
    let upper = tag.trim().to_uppercase();
    let long = match upper.as_str() {
        "DET" => "Determiner",
        "PREP" => "Preposition",
        "NOUN" => "Noun",
        "PROP-NOUN" | "PROPN" => "Proper Noun",
        "ADJ" => "Adjective",
        "VERB" | "V" => "Verb",
        "ADV" => "Adverb",
        "PRON" => "Pronoun",
        "CONJ" => "Conjunction",
        "PART" => "Particle",
        "NUM" => "Numeral",
        "INTERJ" => "Interjection",
        _ => {
            let cleaned = upper.replace('_', " ").replace('-', " ");
            let titled = cleaned
                .split_whitespace()
                .map(|w| {
                    let mut chars = w.chars();
                    match chars.next() {
                        Some(first) => format!("{}{}", first.to_uppercase(), chars.as_str().to_lowercase()),
                        None => String::new(),
                    }
                })
                .collect::<Vec<_>>()
                .join(" ");
            return if titled.is_empty() { tag.to_string() } else { titled };
        }
    };
    format!("{} ({})", long, tag)
}

fn interp_key(surah: i64, ayah: i64) -> String {
    format!("{}:{}", surah, ayah)
}

fn extract_annotation_text(payload: &Value) -> Option<String> {
    if let Some(s) = payload.as_str() {
        return Some(s.to_string());
    }
    payload
        .get("text")
        .and_then(Value::as_str)
        .map(|s| s.to_string())
}

fn fetch_interpretations_with_ids(
    state: &mut AppState,
    surah: i64,
    ayah: i64,
) -> Result<Vec<(String, String)>> {
    let key = interp_key(surah, ayah);
    if let Some(cached) = state.interpretations.get(&key) {
        return Ok(cached.clone());
    }

    let url = format!("{}/annotations", state.base_url);
    let resp: Vec<serde_json::Value> = state
        .client
        .get(url)
        .query(&[("target_id", key.as_str())])
        .send()?
        .error_for_status()?
        .json()?;

    let mut out = Vec::new();
    for ann in resp {
        if ann
            .get("layer")
            .and_then(Value::as_str)
            .map(|l| l.eq_ignore_ascii_case("interpretation"))
            .unwrap_or(false)
        {
            if let (Some(id), Some(payload)) = (ann.get("id"), ann.get("payload")) {
                if let Some(text) = extract_annotation_text(payload) {
                    let id_str = if let Some(s) = id.as_str() {
                        s.to_string()
                    } else {
                        id.to_string()
                    };
                    out.push((id_str, text));
                }
            }
        }
    }
    state.interpretations.insert(key, out.clone());
    Ok(out)
}

fn save_interpretation(state: &mut AppState, surah: i64, ayah: i64, text: &str) -> Result<()> {
    let key = interp_key(surah, ayah);
    let ts = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis();
    let id = format!("interp-{}-{}-{}", surah, ayah, ts);
    let body = serde_json::json!({
        "id": id,
        "target_id": key,
        "layer": "interpretation",
        "payload": { "text": text },
    });

    state
        .client
        .post(format!("{}/annotations", state.base_url))
        .json(&body)
        .send()?
        .error_for_status()?;

    state
        .interpretations
        .entry(interp_key(surah, ayah))
        .or_default()
        .push((id, text.to_string()));
    Ok(())
}

fn build_tree_display(verse: &Verse, segments: &[Value]) -> String {
    #[derive(Default)]
    struct Node {
        surface: String,
        segments: Vec<SegmentRender>,
    }

    #[derive(Default, Clone)]
    struct SegmentRender {
        kind: String,
        text: String,
        details: Vec<String>,
    }

    // Anchor to the verse text order to avoid mis-grouping.
    let mut word_surfaces: Vec<String> = verse
        .text
        .split_whitespace()
        .map(|s| s.to_string())
        .collect();
    if word_surfaces.is_empty() && !verse.tokens.is_empty() {
        word_surfaces = verse
            .tokens
            .iter()
            .map(|t| t.form.clone().or_else(|| t.text.clone()).unwrap_or_default())
            .collect();
    }

    let mut nodes: Vec<Node> = word_surfaces
        .iter()
        .map(|w| Node {
            surface: w.clone(),
            ..Default::default()
        })
        .collect();

    // Capture phrase metadata for header, if present.
    let mut phrase_label: Option<String> = None;
    let mut phrase_role: Option<String> = None;

    let mut cursor = 1usize;
    for seg in segments {
        let mut idx = seg
            .get("word_index")
            .and_then(Value::as_u64)
            .map(|v| v as usize)
            .filter(|v| *v >= 1 && *v <= word_surfaces.len())
            .unwrap_or(0);
        let kind = seg
            .get("type")
            .and_then(Value::as_str)
            .unwrap_or("")
            .to_lowercase();
        let text = seg.get("text").and_then(Value::as_str).unwrap_or("");
        let pos = seg.get("pos").and_then(Value::as_str).unwrap_or("");
        let role = seg.get("role").and_then(Value::as_str).unwrap_or("");
        let case_ = seg.get("case").and_then(Value::as_str).unwrap_or("");
        let root = seg.get("root").and_then(Value::as_str).unwrap_or("");
        let features = seg.get("features").and_then(Value::as_str).unwrap_or("");

        // Extract phrase info from feature set.
        if phrase_label.is_none() || phrase_role.is_none() {
            for part in features.split(" | ") {
                if let Some((k, v)) = part.split_once(':') {
                    match k {
                        "phrase" if !v.is_empty() && phrase_label.is_none() => {
                            phrase_label = Some(v.to_string())
                        }
                        "phrase_fn" if !v.is_empty() && phrase_role.is_none() => {
                            phrase_role = Some(v.to_string())
                        }
                        _ => {}
                    }
                }
            }
        }

        if idx == 0 {
            idx = cursor.min(word_surfaces.len()).max(1);
        }
        if idx == 0 || idx > word_surfaces.len() {
            continue;
        }

        let mut parts = Vec::new();
        let mut grammar_state: Option<String> = None;
        let mut inflection: Option<String> = None;
        if !features.is_empty() {
            for part in features.split(" | ") {
                if let Some((k, v)) = part.split_once(':') {
                    match k {
                        "poss" if !v.is_empty() => grammar_state = Some(v.to_string()),
                        "invar" if !v.is_empty() => inflection = Some(v.to_string()),
                        _ => {}
                    }
                }
            }
        }
        if !pos.is_empty() {
            parts.push(format!("POS: {}", pos_long_form(pos)));
        }
        if !role.is_empty() {
            parts.push(format!("Role: {}", role));
        }
        if !case_.is_empty() {
            parts.push(format!("Case: {}", case_));
        }
        if let Some(inf) = inflection.clone() {
            parts.push(format!("Inflection: {}", inf));
        }
        if let Some(gs) = grammar_state.clone() {
            parts.push(format!("Grammar: {}", gs));
        }
        if !root.is_empty() {
            parts.push(format!("Root: {}", root));
        }

        let label = if kind.contains("prefix") { "Prefix" } else { "Stem" };
        let mut segment = SegmentRender {
            kind: label.to_string(),
            text: text.to_string(),
            details: Vec::new(),
        };
        if !parts.is_empty() {
            segment.details.extend(parts);
        }

        if let Some(node) = nodes.get_mut(idx - 1) {
            node.segments.push(segment);
        }

        if kind.contains("stem") && idx >= cursor {
            cursor = (idx + 1).min(word_surfaces.len());
        }
    }

    // Helper to append optional glosses to phrase/role.
    fn with_gloss(value: Option<String>, gloss: Option<&str>) -> Option<String> {
        match (value, gloss) {
            (Some(v), Some(g)) => Some(format!("{} ({})", v, g)),
            (Some(v), None) => Some(v),
            _ => None,
        }
    }

    let phrase_gloss = with_gloss(
        phrase_label.clone(),
        phrase_label
            .as_deref()
            .and_then(|v| if v == "شبه جملة" { Some("Semi-Sentence") } else { None }),
    );
    let role_gloss = with_gloss(
        phrase_role.clone(),
        phrase_role
            .as_deref()
            .and_then(|v| if v == "خبر" { Some("Predicate") } else { None }),
    );

    let mut out = String::new();
    out.push_str("Clause (Sentence)\n");
    let phrase_line = match (phrase_gloss, role_gloss) {
        (Some(p), Some(r)) => format!("└─ Phrase: {} | Role: {}", p, r),
        (Some(p), None) => format!("└─ Phrase: {}", p),
        (None, Some(r)) => format!("└─ Phrase | Role: {}", r),
        _ => "└─ Phrase".to_string(),
    };
    out.push_str(&format!("{}\n", phrase_line));

    let total = nodes.len();
    for (i, node) in nodes.iter().enumerate() {
        let is_last_word = i + 1 == total;
        let word_prefix = if is_last_word { "   └─" } else { "   ├─" };
        out.push_str(&format!("{} Word {}: {}\n", word_prefix, i + 1, node.surface));

        let seg_count = node.segments.len();
        for (j, seg) in node.segments.iter().enumerate() {
            let is_last_seg = j + 1 == seg_count;
            let mid = if is_last_word { "      " } else { "   │   " };
            let connector = if is_last_seg { "└─" } else { "├─" };
            out.push_str(&format!("{}{} {}: {}\n", mid, connector, seg.kind, seg.text));

            if !seg.details.is_empty() {
                let detail_indent = if is_last_seg { format!("{}    ", mid) } else { format!("{}│   ", mid) };
                for detail in &seg.details {
                    out.push_str(&format!("{}{}\n", detail_indent, detail));
                }
            }
        }
    }

    out
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

fn fetch_surah_list(state: &AppState) -> Result<Vec<SurahSummary>> {
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
        let w_idx: usize = ref_parts.get(2).and_then(|v| v.parse().ok()).unwrap_or(0);
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
                "word_index": w_idx,
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
                    let word_idx = rec.get(3).and_then(|v| v.parse().ok()).unwrap_or(0usize);
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
            let base_text = if !segmented.is_empty() { segmented } else { word };

            // Normalize forms/text: use segmented text; strip definite article or leading alif for stems.
            let (norm_text, norm_form) = if morph_type.eq_ignore_ascii_case("Prefix") {
                let t = if !base_text.is_empty() { base_text } else { word };
                (t.to_string(), Some(t.to_string()))
            } else {
                let mut t = if !base_text.is_empty() { base_text.to_string() } else { word.to_string() };
                if determiner && t.starts_with("ال") {
                    t = t.trim_start_matches("ال").to_string();
                } else if t.starts_with('ا') {
                    t = t.trim_start_matches('ا').to_string();
                }
                (t.clone(), Some(t))
            };

            map.entry((s, a)).or_default().push(serde_json::json!({
                "text": norm_text,
                "lemma": if lemma.is_empty() { None::<String> } else { Some(lemma.to_string()) },
                "pos": if morph_tag.is_empty() { None::<String> } else { Some(morph_tag.to_string()) },
                "form": norm_form,
                "word_index": word_idx,
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
    help.push_str("Read (navigate):\n");
    help.push_str("  read chapters             - List all surahs with their Arabic names\n");
    help.push_str("  read chapter <N>          - View a surah\n");
    help.push_str("  read verse <N>            - View an ayah in the current surah\n");
    help.push_str("  read <S:A>                - View a specific ayah by surah:ayah\n");
    help.push_str("  read sentence <N>         - View a sentence (may span ayat)\n");
    help.push_str("  read word <N>             - View a specific word in the current verse\n");
    help.push_str("  read morpheme <letter>    - View morpheme details (best-effort)\n");
    help.push_str("  read letter <N>           - View a specific letter (placeholder)\n\n");
    help.push_str("Interpret (write mode):\n");
    help.push_str("  write                     - Enter write mode for the current ayah\n");
    help.push_str("  write <ayah> [text]       - Use current surah context; save text if provided\n");
    help.push_str("  write <S:A> [text]        - Target a specific ayah and optionally save text\n");
    help.push_str("  write chapter <N>         - View a surah with interpretation slots\n\n");
    help.push_str("  edit <N>                  - Prefill interpretation number N for editing (write mode)\n\n");
    help.push_str("Inspect Linguistic Details:\n");
    help.push_str("  inspect                   - Show full linguistic analysis of current verse\n");
    help.push_str("  inspect <surah:ayah>      - Inspect a specific verse directly\n\n");
    help.push_str("General:\n");
    help.push_str("  clear                     - Clear the interface output\n");
    help.push_str("  status                    - Show current base URL and context state\n");
    help.push_str("  legend                    - Show color legend for syntax roles/POS/case\n");
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

        assert!(
            analysis.tree.is_some(),
            "expected hierarchical tree output to be present"
        );
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
    }    #[test]
    fn build_tree_display_groups_segments_by_word_order() {
        let verse = Verse {
            surah: SurahInfo {
                number: 1,
                name: "Al-Fatiha".into(),
            },
            ayah: 1,
            text: "بِسْمِ ٱللَّهِ ٱلرَحْمَٰنِ ٱلرَّحِيمِ".into(),
            tokens: vec![],
        };
        // Simulated segments with explicit word indices.
        let segments = vec![
            json!({"text":"ب","type":"Prefix","pos":"PREP","role":"??? ??","case":"????","features":"type:Prefix | invar:???? | role:??? ?? | phrase:شبه جملة | phrase_fn:خبر","word_index":1}),
            json!({"text":"سم","type":"Stem","pos":"NOUN","role":"??? ?????","case":"?????","features":"type:Stem | poss:????","root":"? ? ?","word_index":1}),
            json!({"text":"??","type":"Prefix","pos":"DET","word_index":2}),
            json!({"text":"له","type":"Stem","pos":"PROP-NOUN","role":"???? ????","case":"?????","root":"? ? ?","word_index":2}),
            json!({"text":"??","type":"Prefix","pos":"DET","word_index":3}),
            json!({"text":"رحمن","type":"Stem","pos":"ADJ","role":"???","case":"?????","root":"? ? ?","word_index":3}),
            json!({"text":"??","type":"Prefix","pos":"DET","word_index":4}),
            json!({"text":"رحيم","type":"Stem","pos":"ADJ","role":"???","case":"?????","root":"? ? ?","word_index":4}),
        ];

        let tree = build_tree_display(&verse, &segments);
        assert!(tree.contains("Word 1: بِسْمِ"), "word 1 surface missing");
        assert!(tree.contains("Word 2: ٱللَّهِ"), "word 2 surface missing");
        assert!(tree.contains("Word 3: ٱلرَحْمَٰنِ"), "word 3 surface missing");
        assert!(tree.contains("Word 4: ٱلرَّحِيمِ"), "word 4 surface missing");
        assert!(tree.contains("Prefix: ب"), "prefix for word1 missing");
        assert!(tree.contains("Stem: سم"), "stem for word1 missing");
        assert!(tree.contains("Stem: له"), "stem for word2 missing");
        assert!(tree.contains("Stem: رحمن"), "stem for word3 missing");
        assert!(tree.contains("Stem: رحيم"), "stem for word4 missing");
    }

}
