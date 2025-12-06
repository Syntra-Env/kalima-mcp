use anyhow::{anyhow, Context, Result};
use clap::Parser;
use colored::*;
use reqwest::blocking::Client;
use rustyline::completion::Completer;
use rustyline::error::ReadlineError;
use rustyline::history::DefaultHistory;
use rustyline::hint::Hinter;
use rustyline::highlight::Highlighter;
use rustyline::validate::Validator;
use rustyline::{Editor, Helper};
use serde::Deserialize;
use std::collections::HashSet;
use minus::{Pager, ExitStrategy};

#[derive(Parser, Debug)]
#[command(author, version, about = "Kalima CLI - Quran navigation and search", long_about = None)]
struct Cli {
    /// Base URL of the running Kalima API (e.g., http://127.0.0.1:8080)
    #[arg(short, long, default_value = "http://127.0.0.1:8080")]
    api: String,
}

#[derive(Debug, Clone, Deserialize)]
struct SurahSummary {
    number: i64,
    name: String,
    #[serde(rename = "ayah_count")]
    _ayah_count: i64,
}

#[derive(Debug, Clone, Deserialize)]
struct SurahInfo {
    number: i64,
    #[serde(rename = "name")]
    _name: String,
}

#[derive(Debug, Clone, Deserialize)]
struct Segment {
    #[serde(rename = "id")]
    _id: String,
    #[serde(default)]
    root: Option<String>,
    #[serde(default)]
    pos: Option<String>,
    #[serde(default, rename = "type")]
    _type: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
struct Token {
    #[serde(default, rename = "index")]
    _index: Option<i64>,
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

#[derive(Debug, Clone, Deserialize)]
struct SurahData {
    surah: SurahBasicInfo,
    verses: Vec<VerseSimple>,
}

#[derive(Debug, Clone, Deserialize)]
struct SurahBasicInfo {
    number: i64,
    name: String,
}

#[derive(Debug, Clone, Deserialize)]
struct VerseSimple {
    ayah: i64,
    text: String,
}


#[derive(Debug)]
struct ContextState {
    base_url: String,
    client: Client,
    surahs: Vec<SurahSummary>,
    current: Option<Verse>,
    show_morph: bool,
    show_syntax: bool,
    show_general: bool,
}

impl ContextState {
    fn new(base_url: String) -> Result<Self> {
        Ok(Self {
            base_url,
            client: Client::builder().build()?,
            surahs: Vec::new(),
            current: None,
            show_morph: false,
            show_syntax: false,
            show_general: true,
        })
    }

    fn prompt(&self) -> String {
        if let Some(v) = &self.current {
            format!("kalima ({}:{})> ", v.surah.number, v.ayah)
        } else {
            "kalima > ".to_string()
        }
    }

    fn legend(&self) -> String {
        let mut parts = vec![];
        if self.show_morph {
            parts.push("morphology on");
        }
        if self.show_syntax {
            parts.push("syntax on");
        }
        if self.show_general {
            parts.push("general on");
        }
        if parts.is_empty() {
            "layers: (none)".to_string()
        } else {
            format!("layers: {}", parts.join(" | "))
        }
    }
}

struct LineHelper {
    completions: Vec<String>,
}

impl Completer for LineHelper {
    type Candidate = String;

    fn complete(
        &self,
        line: &str,
        pos: usize,
        _ctx: &rustyline::Context<'_>,
    ) -> rustyline::Result<(usize, Vec<Self::Candidate>)> {
        let start = line[..pos].rfind(' ').map(|i| i + 1).unwrap_or(0);
        let frag = &line[start..pos];
        let mut out = Vec::new();
        for c in &self.completions {
            if c.starts_with(frag) {
                out.push(c.clone());
            }
        }
        Ok((start, out))
    }
}

impl Hinter for LineHelper {
    type Hint = String;
    fn hint(&self, _line: &str, _pos: usize, _ctx: &rustyline::Context<'_>) -> Option<Self::Hint> {
        None
    }
}

impl Highlighter for LineHelper {}
impl Validator for LineHelper {}
impl Helper for LineHelper {}

fn main() -> Result<()> {
    let args = Cli::parse();
    let mut ctx = ContextState::new(args.api)?;
    ctx.surahs = load_surahs(&ctx)?;

    let mut editor: Editor<LineHelper, DefaultHistory> = Editor::new()?;
    let completions = build_completions(&ctx);
    editor.set_helper(Some(LineHelper { completions }));

    println!("Kalima CLI. Type 'help' for commands.");
    loop {
        let line = match editor.readline(&ctx.prompt()) {
            Ok(l) => l.trim().to_string(),
            Err(ReadlineError::Interrupted) => continue,
            Err(ReadlineError::Eof) => break,
            Err(e) => {
                eprintln!("readline error: {e}");
                break;
            }
        };
        if line.is_empty() {
            continue;
        }
        editor.add_history_entry(line.as_str())?;
        if let Err(err) = handle_command(&mut ctx, &line) {
            eprintln!("{}", format!("error: {err}").red());
        }
    }
    Ok(())
}

fn build_completions(ctx: &ContextState) -> Vec<String> {
    let mut set: HashSet<String> = [
        "search".into(),
        "inspect".into(),
        "see".into(),
        "help".into(),
        "exit".into(),
        "quit".into(),
        // See subcommands
        "see book".into(),
        "see chapter".into(),
        "see verse".into(),
        "see word".into(),
        "see sentence".into(),
        "see morpheme".into(),
        "see letter".into(),
        // Inspect dimensions
        "inspect morphology".into(),
        "inspect syntax".into(),
    ]
    .into_iter()
    .collect();
    for s in &ctx.surahs {
        set.insert(s.number.to_string());
    }
    set.into_iter().collect()
}

fn handle_command(ctx: &mut ContextState, line: &str) -> Result<()> {
    let mut parts = line.split_whitespace();
    let cmd = parts.next().unwrap_or("");
    match cmd {
        "search" => {
            let arg = parts.next().ok_or_else(|| anyhow!("usage: search <surah:ayah>"))?;
            let (s, a) = parse_verse_ref(arg)?;
            let verse = fetch_verse(ctx, s, a)?;
            ctx.current = Some(verse.clone());
            render_verse(&verse, ctx);
        }
        "inspect" => {
            let dimension = parts.collect::<Vec<_>>().join(" ");
            if dimension.is_empty() {
                // Show all available linguistic details for current focus
                inspect_current(ctx)?;
            } else if dimension.contains(':') {
                // inspect surah:ayah
                let (s, a) = parse_verse_ref(&dimension)?;
                let verse = fetch_verse(ctx, s, a)?;
                ctx.current = Some(verse.clone());
                ctx.show_morph = true;
                ctx.show_syntax = true;
                render_verse(&verse, ctx);
            } else {
                // inspect <linguistic_dimension>
                inspect_dimension(ctx, &dimension)?;
            }
        }
        "see" => {
            let subtype = parts.next().ok_or_else(|| anyhow!("usage: see <book|chapter|verse|sentence|word|morpheme|letter> [number]"))?;
            let arg = parts.collect::<Vec<_>>().join(" ");
            match subtype {
                "book" => see_book(ctx)?,
                "chapter" => {
                    let num = parse_number(&arg)?;
                    see_chapter(ctx, num)?;
                }
                "verse" => {
                    let num = parse_number(&arg)?;
                    see_verse(ctx, num)?;
                }
                "sentence" => {
                    let num = parse_number(&arg)?;
                    see_sentence(ctx, num)?;
                }
                "word" => {
                    let num = parse_number(&arg)?;
                    see_word(ctx, num)?;
                }
                "morpheme" => {
                    see_morpheme(ctx, &arg)?;
                }
                "letter" => {
                    let num = parse_number(&arg)?;
                    see_letter(ctx, num)?;
                }
                _ => return Err(anyhow!("unknown see subcommand: {subtype}")),
            }
        }
        "help" => {
            print_help();
        }
        "exit" | "quit" => std::process::exit(0),
        _ => {
            return Err(anyhow!("unknown command: {cmd}. Type 'help' for available commands."));
        }
    }
    Ok(())
}

fn parse_verse_ref(s: &str) -> Result<(i64, i64)> {
    let parts: Vec<_> = s.split(':').collect();
    let surah = parts.get(0).ok_or_else(|| anyhow!("missing surah"))?.parse()?;
    let ayah = parts.get(1).ok_or_else(|| anyhow!("missing ayah"))?.parse()?;
    Ok((surah, ayah))
}

fn parse_number(s: &str) -> Result<i64> {
    // Try parsing as number first
    if let Ok(n) = s.trim().parse::<i64>() {
        return Ok(n);
    }

    // Parse word numbers: one, two, three, etc.
    let words = [
        ("zero", 0), ("one", 1), ("two", 2), ("three", 3), ("four", 4),
        ("five", 5), ("six", 6), ("seven", 7), ("eight", 8), ("nine", 9),
        ("ten", 10), ("eleven", 11), ("twelve", 12), ("thirteen", 13),
        ("fourteen", 14), ("fifteen", 15), ("sixteen", 16), ("seventeen", 17),
        ("eighteen", 18), ("nineteen", 19), ("twenty", 20), ("thirty", 30),
        ("forty", 40), ("fifty", 50), ("sixty", 60), ("seventy", 70),
        ("eighty", 80), ("ninety", 90), ("hundred", 100), ("thousand", 1000),
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
        // Handle compound numbers like "twenty three", "one hundred"
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

fn fetch_verse(ctx: &ContextState, surah: i64, ayah: i64) -> Result<Verse> {
    ctx.client
        .get(format!("{}/api/verse/{}/{}", ctx.base_url, surah, ayah))
        .send()
        .context("request failed")?
        .error_for_status()
        .context("bad status")?
        .json::<Verse>()
        .context("invalid JSON")
}

fn fetch_surah(ctx: &ContextState, surah_num: i64) -> Result<SurahData> {
    ctx.client
        .get(format!("{}/api/surah/{}", ctx.base_url, surah_num))
        .send()
        .context("request failed")?
        .error_for_status()
        .context("bad status")?
        .json::<SurahData>()
        .context("invalid JSON")
}

fn display_with_pager(content: String) -> Result<()> {
    let pager = Pager::new();
    pager.set_exit_strategy(ExitStrategy::PagerQuit)?;
    pager.push_str(&content)?;
    minus::page_all(pager)?;
    Ok(())
}

// Helper function to format Arabic text for terminal display
// Adds Unicode bidirectional formatting to improve RTL rendering
fn format_arabic(text: &str) -> String {
    // RTL MARK (U+200F) helps terminals display Arabic text right-to-left
    // We prepend and append it to ensure proper directionality
    const RTL_MARK: char = '\u{200F}';

    // Check if text contains Arabic characters
    let has_arabic = text.chars().any(|c| {
        matches!(c, '\u{0600}'..='\u{06FF}' | '\u{0750}'..='\u{077F}' | '\u{08A0}'..='\u{08FF}')
    });

    if has_arabic {
        // Add RTL mark at the start and end to signal RTL text
        format!("{}{}{}", RTL_MARK, text, RTL_MARK)
    } else {
        text.to_string()
    }
}

// Format verse reference with proper handling of mixed LTR/RTL content
fn format_verse_ref(surah: i64, ayah: i64, text: &str) -> String {
    const LTR_MARK: char = '\u{200E}';
    // Keep the reference LTR, then switch to RTL for Arabic text
    format!("{}:{}{}  {}", surah, ayah, LTR_MARK, format_arabic(text))
}

// Inspect commands
fn inspect_current(ctx: &ContextState) -> Result<()> {
    if let Some(v) = &ctx.current {
        println!("{}", "=== Full Linguistic Analysis ===".bold());
        println!("Verse: {}:{}", v.surah.number, v.ayah);
        println!("Text: {}", format_arabic(&v.text).green());
        println!();

        // Show all tokens with full morphological detail
        for (idx, token) in v.tokens.iter().enumerate() {
            let token_text = token.text.as_deref().unwrap_or("");
            println!("{}. {}", idx + 1, format_arabic(token_text).cyan());
            if !token.segments.is_empty() {
                for seg in &token.segments {
                    let root = seg.root.as_deref().unwrap_or("—");
                    println!("   Root: {}", format_arabic(root).green());
                    println!("   POS: {}", seg.pos.as_deref().unwrap_or("—").blue());
                    if let Some(form) = &token.form {
                        println!("   Form: {}", format_arabic(form));
                    }
                }
            }
            println!();
        }
    } else {
        println!("{}", "No verse in focus. Use 'search <surah:ayah>' first.".yellow());
    }
    Ok(())
}

fn inspect_dimension(ctx: &ContextState, dimension: &str) -> Result<()> {
    if let Some(v) = &ctx.current {
        match dimension {
            "morphology" | "morph" => {
                println!("{}", "=== Morphological Analysis ===".bold());
                for (idx, t) in v.tokens.iter().enumerate() {
                    let root = t.segments.get(0).and_then(|s| s.root.as_deref()).unwrap_or("");
                    let pos = t.segments.get(0).and_then(|s| s.pos.as_deref()).unwrap_or("");
                    let form = t.form.as_deref().unwrap_or("");
                    println!(
                        "{}. {} [POS: {} | Root: {}]",
                        idx + 1,
                        format_arabic(form),
                        pos.blue(),
                        format_arabic(root).green()
                    );
                }
            }
            "syntax" => {
                println!("{}", "=== Syntactic Analysis ===".bold());
                println!("{}", "Syntax layer data coming soon...".yellow());
            }
            _ => {
                return Err(anyhow!("unknown linguistic dimension: {}", dimension));
            }
        }
    } else {
        println!("{}", "No verse in focus. Use 'search <surah:ayah>' first.".yellow());
    }
    Ok(())
}

// See commands - hierarchical navigation
fn see_book(ctx: &ContextState) -> Result<()> {
    println!("{}", "Loading entire Quran...".yellow());

    let mut content = String::new();
    content.push_str("═══════════════════════════════════════════════════════════\n");
    content.push_str(&format!("                    {}\n", format_arabic("القرآن الكريم")));
    content.push_str("                   The Noble Quran\n");
    content.push_str("═══════════════════════════════════════════════════════════\n\n");

    // Fetch all surahs
    for surah_summary in &ctx.surahs {
        let surah_data = fetch_surah(ctx, surah_summary.number)?;

        content.push_str(&format!("\n{}\n", "─".repeat(60)));
        content.push_str(&format!("Surah {}: {}\n", surah_data.surah.number, format_arabic(&surah_data.surah.name)));
        content.push_str(&format!("{}\n\n", "─".repeat(60)));

        for verse in &surah_data.verses {
            content.push_str(&format!("{}\n\n",
                format_verse_ref(surah_data.surah.number, verse.ayah, &verse.text)
            ));
        }
    }

    content.push_str("\n═══════════════════════════════════════════════════════════\n");
    content.push_str("             Use q to quit, arrows to navigate\n");
    content.push_str("═══════════════════════════════════════════════════════════\n");

    display_with_pager(content)
}

fn see_chapter(ctx: &mut ContextState, chapter: i64) -> Result<()> {
    println!("{}", format!("Loading Surah {}...", chapter).yellow());

    let surah_data = fetch_surah(ctx, chapter)?;

    // Set first verse as current context
    if !surah_data.verses.is_empty() {
        let first = fetch_verse(ctx, chapter, 1)?;
        ctx.current = Some(first);
    }

    let mut content = String::new();
    content.push_str("═══════════════════════════════════════════════════════════\n");
    content.push_str(&format!("           Surah {}: {}\n", surah_data.surah.number, format_arabic(&surah_data.surah.name)));
    content.push_str(&format!("           {} Ayahs\n", surah_data.verses.len()));
    content.push_str("═══════════════════════════════════════════════════════════\n\n");

    for verse in &surah_data.verses {
        content.push_str(&format!("{}\n\n",
            format_verse_ref(surah_data.surah.number, verse.ayah, &verse.text)
        ));
    }

    content.push_str("\n═══════════════════════════════════════════════════════════\n");
    content.push_str("             Use q to quit, arrows to navigate\n");
    content.push_str("═══════════════════════════════════════════════════════════\n");

    display_with_pager(content)
}

fn see_verse(ctx: &mut ContextState, ayah: i64) -> Result<()> {
    let surah = if let Some(v) = &ctx.current {
        v.surah.number
    } else {
        return Err(anyhow!("No surah in context. Use 'see chapter <N>' first or 'search <surah:ayah>'"));
    };

    let verse = fetch_verse(ctx, surah, ayah)?;
    ctx.current = Some(verse.clone());
    render_verse(&verse, ctx);
    Ok(())
}

fn see_sentence(_ctx: &ContextState, _num: i64) -> Result<()> {
    println!("{}", "Sentence-level navigation coming soon...".yellow());
    println!("Note: Sentences can span multiple ayat.");
    Ok(())
}

fn see_word(ctx: &ContextState, word_num: i64) -> Result<()> {
    if let Some(v) = &ctx.current {
        let idx = (word_num - 1) as usize;
        if let Some(token) = v.tokens.get(idx) {
            println!("{}", format!("=== Word {} ===", word_num).bold());
            let token_text = token.text.as_deref().unwrap_or("");
            println!("Text: {}", format_arabic(token_text).cyan());
            if let Some(form) = &token.form {
                println!("Form: {}", format_arabic(form));
            }

            if !token.segments.is_empty() {
                println!("\n{}", "Segments:".bold());
                for (i, seg) in token.segments.iter().enumerate() {
                    let root = seg.root.as_deref().unwrap_or("—");
                    println!("  {}. {}", i + 1, format_arabic(root));
                    println!("     POS: {}", seg.pos.as_deref().unwrap_or("—").blue());
                }
            }
        } else {
            println!("{}", format!("Word {} not found in current verse", word_num).yellow());
        }
    } else {
        println!("{}", "No verse in focus. Use 'search <surah:ayah>' first.".yellow());
    }
    Ok(())
}

fn see_morpheme(ctx: &ContextState, _letter: &str) -> Result<()> {
    if ctx.current.is_some() {
        println!("{}", "Morpheme-level navigation coming soon...".yellow());
    } else {
        println!("{}", "No verse in focus. Use 'search <surah:ayah>' first.".yellow());
    }
    Ok(())
}

fn see_letter(ctx: &ContextState, _num: i64) -> Result<()> {
    if ctx.current.is_some() {
        println!("{}", "Letter-level navigation coming soon...".yellow());
    } else {
        println!("{}", "No verse in focus. Use 'search <surah:ayah>' first.".yellow());
    }
    Ok(())
}


fn render_verse(v: &Verse, ctx: &ContextState) {
    println!(
        "{}",
        format_verse_ref(v.surah.number, v.ayah, &v.text).bold()
    );
    if ctx.show_general {
        let mut line = String::new();
        for (idx, t) in v.tokens.iter().enumerate() {
            let token_text = t.form.as_deref().unwrap_or(t.text.as_deref().unwrap_or(""));
            line.push_str(&format!(
                "{}:{} ",
                idx + 1,
                format_arabic(token_text)
            ));
        }
        println!("{line}");
    }
    if ctx.show_morph {
        let mut line = String::new();
        for (idx, t) in v.tokens.iter().enumerate() {
            let root = t.segments.get(0).and_then(|s| s.root.as_deref()).unwrap_or("");
            let pos = t.segments.get(0).and_then(|s| s.pos.as_deref()).unwrap_or("");
            let form = t.form.as_deref().unwrap_or("");
            line.push_str(&format!(
                "{}:{} [{} {}] ",
                idx + 1,
                format_arabic(form),
                pos.blue(),
                format_arabic(root).green()
            ));
        }
        if !line.is_empty() {
            println!("{line}");
        }
        println!("Legend: {} {} {} {}", "N".blue(), "V".green(), "PRON".purple(), "PART".truecolor(150,150,150));
    }
    if ctx.show_syntax {
        println!("Syntax legend: subj (cyan), obj (yellow), prep (magenta)");
    }
    println!("{}", ctx.legend());
}


fn load_surahs(ctx: &ContextState) -> Result<Vec<SurahSummary>> {
    let res = ctx
        .client
        .get(format!("{}/api/surahs", ctx.base_url))
        .send()?
        .error_for_status()?
        .json::<Vec<SurahSummary>>()?;
    Ok(res)
}

fn print_help() {
    println!("{}", "=== Kalima CLI Commands ===".bold());
    println!();
    println!("{}", "Search & Navigate:".green());
    println!("  search <surah:ayah>       - Load and display a specific verse");
    println!("                              Example: search 1:1");
    println!();
    println!("{}", "Inspect Linguistic Details:".green());
    println!("  inspect                   - Show full linguistic analysis of current verse");
    println!("  inspect <dimension>       - Show specific dimension (morphology, syntax)");
    println!("  inspect <surah:ayah>      - Inspect a specific verse");
    println!();
    println!("{}", "See Hierarchical Levels:".green());
    println!("  see book                  - View the entire Quran structure");
    println!("  see chapter <N>           - View a specific surah");
    println!("  see verse <N>             - View a specific ayah in current surah");
    println!("  see word <N>              - View a specific word (accepts: 1, one, twenty three)");
    println!("  see sentence <N>          - View a sentence (coming soon)");
    println!("  see morpheme <letter>     - View a morpheme (coming soon)");
    println!("  see letter <N>            - View a letter (coming soon)");
    println!();
    println!("{}", "General:".green());
    println!("  help                      - Show this help");
    println!("  exit | quit               - Exit the CLI");
}
