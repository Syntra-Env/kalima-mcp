use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use anyhow::{anyhow, Result};

#[derive(Debug, Clone, Deserialize)]
struct SurahInfo {
    number: i64,
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
    Pager { content: String },
    Error { message: String },
    Success { message: String },
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
}

impl AppState {
    fn new() -> Self {
        Self {
            current_verse: None,
            base_url: "http://127.0.0.1:8080".to_string(),
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

    match cmd {
        "search" => {
            let arg = parts.next().ok_or_else(|| anyhow!("usage: search <surah:ayah>"))?;
            let (s, a) = parse_verse_ref(arg)?;
            let verse = fetch_verse(&state.base_url, s, a)?;
            state.current_verse = Some(verse.clone());

            Ok(CommandOutput::Verse(VerseOutput {
                surah: verse.surah.number,
                ayah: verse.ayah,
                text: verse.text.clone(),
                tokens: Some(
                    verse
                        .tokens
                        .iter()
                        .map(|t| t.form.clone().unwrap_or_default())
                        .collect(),
                ),
                legend: Some("layers: general on".to_string()),
            }))
        }
        "inspect" => {
            let dimension = parts.collect::<Vec<_>>().join(" ");
            if dimension.is_empty() {
                inspect_current(state)
            } else {
                inspect_dimension(state, &dimension)
            }
        }
        "see" => {
            let subtype = parts.next().ok_or_else(|| {
                anyhow!("usage: see <book|chapter|verse|word> [number]")
            })?;
            match subtype {
                "book" | "chapter" | "verse" | "word" => Ok(CommandOutput::Info {
                    message: format!("'see {}' - Coming soon in desktop version", subtype),
                }),
                _ => Err(anyhow!("unknown see subcommand: {}", subtype)),
            }
        }
        "help" => Ok(CommandOutput::Info {
            message: print_help(),
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
        let tokens: Vec<AnalysisToken> = v
            .tokens
            .iter()
            .map(|token| {
                let text = token.text.clone().unwrap_or_default();
                let root = token.segments.get(0).and_then(|s| s.root.clone());
                let pos = token.segments.get(0).and_then(|s| s.pos.clone());
                let form = token.form.clone();

                AnalysisToken {
                    text,
                    root,
                    pos,
                    form,
                }
            })
            .collect();

        Ok(CommandOutput::Analysis(AnalysisOutput {
            header: Some("=== Full Linguistic Analysis ===".to_string()),
            verse_ref: Some(format!("{}:{}", v.surah.number, v.ayah)),
            text: Some(v.text.clone()),
            tokens: Some(tokens),
        }))
    } else {
        Err(anyhow!("No verse in focus. Use 'search <surah:ayah>' first."))
    }
}

fn inspect_dimension(state: &AppState, dimension: &str) -> Result<CommandOutput> {
    if let Some(v) = &state.current_verse {
        match dimension {
            "morphology" | "morph" => {
                let tokens: Vec<AnalysisToken> = v
                    .tokens
                    .iter()
                    .map(|t| {
                        let root = t.segments.get(0).and_then(|s| s.root.clone());
                        let pos = t.segments.get(0).and_then(|s| s.pos.clone());
                        let form = t.form.clone().unwrap_or_default();

                        AnalysisToken {
                            text: form.clone(),
                            root,
                            pos,
                            form: Some(form),
                        }
                    })
                    .collect();

                Ok(CommandOutput::Analysis(AnalysisOutput {
                    header: Some("=== Morphological Analysis ===".to_string()),
                    verse_ref: None,
                    text: None,
                    tokens: Some(tokens),
                }))
            }
            "syntax" => Ok(CommandOutput::Info {
                message: "Syntax layer data coming soon...".to_string(),
            }),
            _ => Err(anyhow!("unknown linguistic dimension: {}", dimension)),
        }
    } else {
        Err(anyhow!("No verse in focus. Use 'search <surah:ayah>' first."))
    }
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

fn fetch_verse(base_url: &str, surah: i64, ayah: i64) -> Result<Verse> {
    let client = reqwest::blocking::Client::new();
    let verse = client
        .get(format!("{}/api/verse/{}/{}", base_url, surah, ayah))
        .send()?
        .error_for_status()?
        .json::<Verse>()?;
    Ok(verse)
}

fn print_help() -> String {
    let mut help = String::new();
    help.push_str("=== Kalima CLI Commands ===\n\n");
    help.push_str("Search & Navigate:\n");
    help.push_str("  search <surah:ayah>       - Load and display a specific verse\n");
    help.push_str("                              Example: search 1:1\n\n");
    help.push_str("Inspect Linguistic Details:\n");
    help.push_str("  inspect                   - Show full linguistic analysis of current verse\n");
    help.push_str("  inspect <dimension>       - Show specific dimension (morphology, syntax)\n\n");
    help.push_str("General:\n");
    help.push_str("  help                      - Show this help\n");
    help.push_str("  exit | quit               - Exit the application\n");
    help
}
