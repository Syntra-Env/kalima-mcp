use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConcordanceQuery {
    pub anchors: Vec<AnchorConstraint>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnchorConstraint {
    pub anchor_num: usize,
    pub constraints: Vec<FieldConstraint>,
    #[serde(default)]
    pub gap_to_next: Option<GapRange>,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub struct GapRange {
    pub min: usize,
    pub max: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FieldConstraint {
    pub field: String,   // "root", "gender", "pos", etc.
    pub value: String,   // "ajl", "M", "NOUN"
    #[serde(default)]
    pub negated: bool,
}

impl ConcordanceQuery {
    /// Parse a query string like "#1 r:ajl c:Nom #2 g:M p:V"
    pub fn parse(query_string: &str) -> Result<Self, String> {
        let mut anchors = Vec::new();
        let mut current_anchor: Option<AnchorConstraint> = None;

        for token in tokenize_query(query_string)? {
            if token.starts_with('#') {
                // New anchor - save previous one if exists
                if let Some(anchor) = current_anchor.take() {
                    anchors.push(anchor);
                }

                // Parse anchor number
                let num = token[1..].parse::<usize>()
                    .map_err(|_| format!("Invalid anchor number: {}", token))?;

                current_anchor = Some(AnchorConstraint {
                    anchor_num: num,
                    constraints: Vec::new(),
                    gap_to_next: None,
                });
            } else if token.starts_with('~') {
                let gap = parse_gap_range(&token)?;
                if let Some(anchor) = current_anchor.as_mut() {
                    anchor.gap_to_next = Some(gap);
                } else {
                    return Err(format!("Gap '{}' found before anchor declaration", token));
                }
            } else if let Some(colon_pos) = token.find(':') {
                // key:value constraint
                let key_raw = &token[..colon_pos];
                let raw_value = &token[colon_pos + 1..];
                let value = unquote_value(raw_value)?;

                if let Some(anchor) = current_anchor.as_mut() {
                    let (negated, key) = key_raw
                        .strip_prefix('!')
                        .map(|k| (true, k))
                        .unwrap_or((false, key_raw));
                    anchor.constraints.push(FieldConstraint {
                        field: expand_key(key).to_string(),
                        value,
                        negated,
                    });
                } else {
                    return Err(format!("Constraint '{}' found before anchor declaration", token));
                }
            } else {
                return Err(format!("Invalid token format: '{}'. Expected '#N' or 'key:value'", token));
            }
        }

        // Save the last anchor
        if let Some(anchor) = current_anchor {
            anchors.push(anchor);
        }

        if anchors.is_empty() {
            return Err("No anchors found in query".to_string());
        }

        Ok(ConcordanceQuery { anchors })
    }

    /// Get the number of anchors in the query
    pub fn anchor_count(&self) -> usize {
        self.anchors.len()
    }

    /// Check if query is valid (all anchors have at least one constraint)
    pub fn is_valid(&self) -> bool {
        self.anchors.iter().all(|a| !a.constraints.is_empty())
    }
}

/// Expand short key names to full field names
fn expand_key(short: &str) -> &str {
    match short {
        "o" => "original",
        "r" => "root",
        "l" => "lemma",
        "p" => "pos",
        "c" => "case",
        "g" => "gender",
        "n" => "number",
        "pat" => "pattern",
        "v" => "voice",
        "m" => "mood",
        "a" => "aspect",
        "per" => "person",
        "vf" => "verb_form",
        "dep" => "dependency",
        "role" => "role",
        "st" => "segment_type",
        "sf" => "segment_form",
        _ => short, // Pass through if not recognized
    }
}

fn parse_gap_range(token: &str) -> Result<GapRange, String> {
    let rest = token.trim_start_matches('~').trim();
    if rest.is_empty() {
        return Err("Gap '~' requires a number, like '~0' or '~0-3'".to_string());
    }

    if let Some((a, b)) = rest.split_once('-') {
        let min = a
            .trim()
            .parse::<usize>()
            .map_err(|_| format!("Invalid gap range: {}", token))?;
        let max = b
            .trim()
            .parse::<usize>()
            .map_err(|_| format!("Invalid gap range: {}", token))?;
        if min > max {
            return Err(format!("Invalid gap range (min > max): {}", token));
        }
        Ok(GapRange { min, max })
    } else {
        let n = rest
            .parse::<usize>()
            .map_err(|_| format!("Invalid gap: {}", token))?;
        Ok(GapRange { min: n, max: n })
    }
}

fn tokenize_query(input: &str) -> Result<Vec<String>, String> {
    let mut tokens = Vec::new();
    let mut current = String::new();
    let mut in_quotes = false;
    let mut escaping = false;

    for ch in input.chars() {
        if escaping {
            current.push(ch);
            escaping = false;
            continue;
        }

        if in_quotes && ch == '\\' {
            current.push(ch);
            escaping = true;
            continue;
        }

        if ch == '"' {
            in_quotes = !in_quotes;
            current.push(ch);
            continue;
        }

        if ch.is_whitespace() && !in_quotes {
            if !current.is_empty() {
                tokens.push(current);
                current = String::new();
            }
            continue;
        }

        current.push(ch);
    }

    if in_quotes {
        return Err("Unterminated quoted value".to_string());
    }

    if !current.is_empty() {
        tokens.push(current);
    }

    Ok(tokens)
}

fn unquote_value(raw: &str) -> Result<String, String> {
    let raw = raw.trim();
    if raw.is_empty() {
        return Err("Empty constraint value".to_string());
    }

    if !(raw.starts_with('"') || raw.ends_with('"')) {
        return Ok(raw.to_string());
    }

    if !(raw.starts_with('"') && raw.ends_with('"') && raw.len() >= 2) {
        return Err(format!("Invalid quoted value: {}", raw));
    }

    let inner = &raw[1..raw.len() - 1];
    let mut out = String::new();
    let mut chars = inner.chars();
    while let Some(ch) = chars.next() {
        if ch != '\\' {
            out.push(ch);
            continue;
        }
        match chars.next() {
            Some('"') => out.push('"'),
            Some('\\') => out.push('\\'),
            Some(other) => {
                out.push('\\');
                out.push(other);
            }
            None => {
                return Err(format!("Invalid escape at end of value: {}", raw));
            }
        }
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_simple_query() {
        let query = ConcordanceQuery::parse("#1 r:ajl").unwrap();
        assert_eq!(query.anchors.len(), 1);
        assert_eq!(query.anchors[0].anchor_num, 1);
        assert_eq!(query.anchors[0].constraints.len(), 1);
        assert_eq!(query.anchors[0].constraints[0].field, "root");
        assert_eq!(query.anchors[0].constraints[0].value, "ajl");
    }

    #[test]
    fn test_parse_multi_constraint() {
        let query = ConcordanceQuery::parse("#1 r:ajl c:Nom").unwrap();
        assert_eq!(query.anchors.len(), 1);
        assert_eq!(query.anchors[0].constraints.len(), 2);
        assert_eq!(query.anchors[0].constraints[0].field, "root");
        assert_eq!(query.anchors[0].constraints[1].field, "case");
    }

    #[test]
    fn test_parse_multi_anchor() {
        let query = ConcordanceQuery::parse("#1 r:ajl c:Nom #2 g:M p:V").unwrap();
        assert_eq!(query.anchors.len(), 2);
        assert_eq!(query.anchors[0].anchor_num, 1);
        assert_eq!(query.anchors[1].anchor_num, 2);
        assert_eq!(query.anchors[1].constraints.len(), 2);
    }

    #[test]
    fn test_parse_quoted_values_with_spaces() {
        let query = ConcordanceQuery::parse("#1 r:\"ع ج ل\" #2 o:\"foo bar\"").unwrap();
        assert_eq!(query.anchors.len(), 2);
        assert_eq!(query.anchors[0].constraints[0].value, "ع ج ل");
        assert_eq!(query.anchors[1].constraints[0].field, "original");
        assert_eq!(query.anchors[1].constraints[0].value, "foo bar");
    }

    #[test]
    fn test_parse_invalid_anchor() {
        let result = ConcordanceQuery::parse("#invalid r:ajl");
        assert!(result.is_err());
    }

    #[test]
    fn test_parse_constraint_before_anchor() {
        let result = ConcordanceQuery::parse("r:ajl #1");
        assert!(result.is_err());
    }

    #[test]
    fn test_parse_empty() {
        let result = ConcordanceQuery::parse("");
        assert!(result.is_err());
    }

    #[test]
    fn test_key_expansion() {
        assert_eq!(expand_key("r"), "root");
        assert_eq!(expand_key("p"), "pos");
        assert_eq!(expand_key("g"), "gender");
        assert_eq!(expand_key("unknown"), "unknown");
    }

    #[test]
    fn test_parse_gap_range() {
        let query = ConcordanceQuery::parse("#1 g:M ~0-3 #2 c:GEN").unwrap();
        assert_eq!(query.anchors.len(), 2);
        assert_eq!(query.anchors[0].gap_to_next, Some(GapRange { min: 0, max: 3 }));
    }

    #[test]
    fn test_parse_negated_constraint() {
        let query = ConcordanceQuery::parse("#1 !g:M").unwrap();
        assert_eq!(query.anchors[0].constraints[0].field, "gender");
        assert_eq!(query.anchors[0].constraints[0].value, "M");
        assert!(query.anchors[0].constraints[0].negated);
    }

    #[test]
    fn test_is_valid() {
        let valid = ConcordanceQuery::parse("#1 r:ajl").unwrap();
        assert!(valid.is_valid());

        let mut invalid = valid.clone();
        invalid.anchors[0].constraints.clear();
        assert!(!invalid.is_valid());
    }
}
