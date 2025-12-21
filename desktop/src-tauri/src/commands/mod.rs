mod http;
mod state;
mod types;

use anyhow::{anyhow, Result};
use serde_json::Value;
use std::time::{SystemTime, UNIX_EPOCH};

#[cfg(test)]
use std::collections::{HashMap, HashSet};

use http::{fetch_surah, fetch_surah_list, fetch_verse};
use state::{
    surah_name_or_fallback, AppState, CommandResponse, Mode, APP_STATE,
};
use types::*;

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
                anyhow!("usage: read <chapters|chapter|verse|sentence|word|morpheme|letter> [value]")
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
            message: "Colors: role subj=green, obj=red, comp=blue, other=gold. POS is blue text. Case is cyan text. Concordance: anchors=blue outline, hits=yellow highlight.".to_string(),
        }),
        "exit" | "quit" => std::process::exit(0),
        _ => Err(anyhow!(
            "unknown command: {}. Type 'help' for available commands.",
            cmd
        )),
    }
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

    let mut verse_outputs = Vec::new();

    for verse_summary in &surah.verses {
        // Fetch full verse data with tokens for each verse
        let verse = fetch_verse(state, surah.surah.number, verse_summary.ayah)?;

        let token_texts: Vec<String> = verse
            .tokens
            .iter()
            .map(|t| t.text.clone().unwrap_or_default())
            .collect();

        verse_outputs.push(VerseOutput {
            surah: verse.surah.number,
            ayah: verse.ayah,
            text: verse.text.clone(),
            tokens: if token_texts.is_empty() { None } else { Some(token_texts) },
            legend: None,
        });
    }

    Ok(CommandOutput::Chapter(ChapterOutput {
        surah: surah.surah.number,
        name: surah_name,
        verses: verse_outputs,
    }))
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
        .ok_or_else(|| anyhow!("No verse in focus. Use 'read <surah:ayah>' first."))?;

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
        .ok_or_else(|| anyhow!("No verse in focus. Use 'read <surah:ayah>' first."))?;

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
    let token_texts: Vec<String> = verse
        .tokens
        .iter()
        .map(|t| t.text.clone().unwrap_or_default())
        .collect();

    CommandOutput::Verse(VerseOutput {
        surah: verse.surah.number,
        ayah: verse.ayah,
        text: verse.text.clone(),
        tokens: if token_texts.is_empty() { None } else { Some(token_texts) },
        legend: None,
    })
}

#[cfg(test)]
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

#[cfg(test)]
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

#[cfg(test)]
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

#[cfg(test)]
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
    help.push_str(&format!(
        "=== Kalima CLI v{} ===\n\n",
        env!("CARGO_PKG_VERSION")
    ));
    help.push_str("Read (navigate):\n");
    help.push_str("  read chapters             - List all surahs with their Arabic names\n");
    help.push_str("  read chapter <N>          - View a surah\n");
    help.push_str("  read verse <N>            - View an ayah in the current surah\n");
    help.push_str("  read <S:A>                - View a specific ayah by surah:ayah\n");
    help.push_str("  read sentence <N>         - View a sentence (may span ayat)\n");
    help.push_str("  read word <N>             - View a specific word in the current verse\n");
    help.push_str("  read morpheme <letter>    - View morpheme details (best-effort)\n");
    help.push_str("  read letter <N>           - View a specific letter (placeholder)\n\n");
    help.push_str("Layers (UI):\n");
    help.push_str("  layer                     - Show current layer and list available layers\n");
    help.push_str("  layer <number|name>       - Switch layer (e.g. 'layer root', 'layer 3')\n");
    help.push_str("  layer next | prev         - Cycle layers\n\n");
    help.push_str("Concordance (Query Mode):\n");
    help.push_str("  Ctrl+Q                    - Enter Query Mode\n");
    help.push_str("  q | query | concordance   - Enter Query Mode as a command\n");
    help.push_str("  Alt+O/R/L/P/C/G           - Switch display layer (Original/Root/Lemma/POS/Case/Gender)\n");
    help.push_str("  click token               - Add/update constraint for next anchor\n");
    help.push_str("  Shift+click token         - Toggle that token's constraint on/off\n");
    help.push_str("  Shift+hover token         - Show the current layer label\n");
    help.push_str("  Ctrl+Z                    - Remove the last anchor\n");
    help.push_str("  Enter                     - Run concordance search\n");
    help.push_str("  Esc                       - Exit Query Mode\n\n");
    help.push_str("Concordance syntax:\n");
    help.push_str("  #N key:value key:value ...   - Anchors match a token pattern anywhere (use ~ for gaps)\n");
    help.push_str("  Quote values with spaces:    r:\"...\" (and other fields)\n\n");
    help.push_str("  OR values:                   g:M|F (also supports commas: g:M,F)\n");
    help.push_str("  Wildcards:                   r:عجل* (* expands as wildcard)\n");
    help.push_str("  Negation:                    !g:M\n");
    help.push_str("  Gap (distance):              ~0 (adjacent), ~1-3 (allow 1..3 tokens between anchors)\n\n");
    help.push_str("General:\n");
    help.push_str("  clear                     - Clear the interface output\n");
    help.push_str("  history                   - Show command history (click to re-run)\n");
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

    #[test]
    fn chapter_output_serializes_correctly() {
        let chapter = ChapterOutput {
            surah: 1,
            name: "الفاتحة".to_string(),
            verses: vec![
                VerseOutput {
                    surah: 1,
                    ayah: 1,
                    text: "بِسْمِ ٱللَّهِ ٱلرَحْمَٰنِ ٱلرَّحِيمِ".to_string(),
                    tokens: Some(vec!["بِسْمِ".to_string(), "ٱللَّهِ".to_string()]),
                    legend: None,
                },
            ],
        };

        let output = CommandOutput::Chapter(chapter);
        let json = serde_json::to_value(&output).unwrap();

        assert_eq!(json["output_type"], "chapter");
        assert_eq!(json["surah"], 1);
        assert_eq!(json["name"], "الفاتحة");
        assert_eq!(json["verses"][0]["surah"], 1);
        assert_eq!(json["verses"][0]["ayah"], 1);
        assert!(json["verses"][0]["tokens"].is_array());
    }

    #[test]
    fn chapter_output_includes_all_verses() {
        let verses = vec![
            VerseOutput {
                surah: 1,
                ayah: 1,
                text: "verse 1".to_string(),
                tokens: Some(vec!["token1".to_string()]),
                legend: None,
            },
            VerseOutput {
                surah: 1,
                ayah: 2,
                text: "verse 2".to_string(),
                tokens: Some(vec!["token2".to_string()]),
                legend: None,
            },
        ];

        let chapter = ChapterOutput {
            surah: 1,
            name: "Test".to_string(),
            verses,
        };

        assert_eq!(chapter.verses.len(), 2);
        assert_eq!(chapter.verses[0].ayah, 1);
        assert_eq!(chapter.verses[1].ayah, 2);
    }

    #[test]
    fn verse_output_handles_empty_tokens() {
        let verse = VerseOutput {
            surah: 1,
            ayah: 1,
            text: "test".to_string(),
            tokens: None,
            legend: None,
        };

        let json = serde_json::to_value(&verse).unwrap();
        assert!(json.get("tokens").is_none());
    }

}
