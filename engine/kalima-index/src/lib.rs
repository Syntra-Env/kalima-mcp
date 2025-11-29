//! SearchBackend implementation using Tantivy. Indexes text plus flattened
//! morphological features to support basic filtering.

use async_trait::async_trait;
use kalima_core::{EngineError, EngineResult, QuerySpec, SearchBackend, SearchHit, SegmentView};
use std::path::Path;
use std::sync::{Arc, RwLock};
use tantivy::{
    collector::TopDocs, doc,
    schema::{Schema, Value, TEXT},
    Index, IndexReader, IndexWriter,
};

pub struct TantivyIndex {
    index: Index,
    writer: Arc<RwLock<IndexWriter>>,
    reader: IndexReader,
    text_field: tantivy::schema::Field,
    id_field: tantivy::schema::Field,
    roots_field: tantivy::schema::Field,
    lemmas_field: tantivy::schema::Field,
    pos_field: tantivy::schema::Field,
    verb_form_field: tantivy::schema::Field,
    gender_field: tantivy::schema::Field,
    number_field: tantivy::schema::Field,
    case_field: tantivy::schema::Field,
    pattern_field: tantivy::schema::Field,
    voice_field: tantivy::schema::Field,
    mood_field: tantivy::schema::Field,
    tense_field: tantivy::schema::Field,
    aspect_field: tantivy::schema::Field,
}

impl TantivyIndex {
    pub fn open_or_create<P: AsRef<Path>>(path: P) -> EngineResult<Self> {
        let mut schema_builder = Schema::builder();
        let id_field = schema_builder.add_text_field("id", TEXT | tantivy::schema::STORED);
        let text_field = schema_builder.add_text_field("text", TEXT);
        let roots_field = schema_builder.add_text_field("roots", TEXT);
        let lemmas_field = schema_builder.add_text_field("lemmas", TEXT);
        let pos_field = schema_builder.add_text_field("pos", TEXT);
        let verb_form_field = schema_builder.add_text_field("verb_form", TEXT);
        let gender_field = schema_builder.add_text_field("gender", TEXT);
        let number_field = schema_builder.add_text_field("number", TEXT);
        let case_field = schema_builder.add_text_field("case", TEXT);
        let pattern_field = schema_builder.add_text_field("pattern", TEXT);
        let voice_field = schema_builder.add_text_field("voice", TEXT);
        let mood_field = schema_builder.add_text_field("mood", TEXT);
        let tense_field = schema_builder.add_text_field("tense", TEXT);
        let aspect_field = schema_builder.add_text_field("aspect", TEXT);
        let schema = schema_builder.build();

        let path = path.as_ref();
        let meta_path = path.join("meta.json");
        
        let index = if meta_path.exists() {
            Index::open_in_dir(path).map_err(|e| EngineError::Search(e.to_string()))?
        } else {
            std::fs::create_dir_all(path)
                .map_err(|e| EngineError::Search(e.to_string()))?;
            Index::create_in_dir(path, schema.clone())
                .map_err(|e| EngineError::Search(e.to_string()))?
        };

        let writer = index
            .writer(50_000_000)
            .map_err(|e| EngineError::Search(e.to_string()))?;
        let reader = index
            .reader()
            .map_err(|e| EngineError::Search(e.to_string()))?;

        Ok(Self {
            index,
            writer: Arc::new(RwLock::new(writer)),
            reader,
            text_field,
            id_field,
            roots_field,
            lemmas_field,
            pos_field,
            verb_form_field,
            gender_field,
            number_field,
            case_field,
            pattern_field,
            voice_field,
            mood_field,
            tense_field,
            aspect_field,
        })
    }

    fn parse_query(&self, spec: &QuerySpec) -> EngineResult<Box<dyn tantivy::query::Query>> {
        let parser = tantivy::query::QueryParser::for_index(
            &self.index,
            vec![
                self.text_field,
                self.roots_field,
                self.lemmas_field,
                self.pos_field,
                self.pattern_field,
            ],
        );

        let needle_owned = spec
            .query
            .as_str()
            .map(str::to_string)
            .unwrap_or_else(|| serde_json::to_string(&spec.query).unwrap_or_default());

        let mut queries: Vec<Box<dyn tantivy::query::Query>> = Vec::new();
        if needle_owned.trim().is_empty() {
            queries.push(Box::new(tantivy::query::AllQuery));
        } else {
            let main_q = parser
                .parse_query(&needle_owned)
                .map_err(|e| EngineError::Search(e.to_string()))?;
            queries.push(main_q);
        }

        for f in &spec.filters {
            let field = match f.field.as_str() {
                "root" | "roots" => Some(self.roots_field),
                "lemma" | "lemmas" => Some(self.lemmas_field),
                "pos" => Some(self.pos_field),
                "pattern" => Some(self.pattern_field),
                "verb_form" => Some(self.verb_form_field),
                "gender" => Some(self.gender_field),
                "number" => Some(self.number_field),
                "case" | "case_" => Some(self.case_field),
                "voice" => Some(self.voice_field),
                "mood" => Some(self.mood_field),
                "tense" => Some(self.tense_field),
                "aspect" => Some(self.aspect_field),
                _ => None,
            };
            if let Some(field_ref) = field {
                let values: Vec<String> = if f.op == "in" {
                    f.value
                        .as_array()
                        .cloned()
                        .unwrap_or_default()
                        .into_iter()
                        .filter_map(|v| v.as_str().map(|s| s.to_string()))
                        .collect()
                } else {
                    f.value
                        .as_str()
                        .map(|s| vec![s.to_string()])
                        .unwrap_or_default()
                };
                for val in values {
                    let term = tantivy::Term::from_field_text(field_ref, &val);
                    queries.push(Box::new(tantivy::query::TermQuery::new(
                        term,
                        tantivy::schema::IndexRecordOption::Basic,
                    )));
                }
            }
        }

        if queries.len() == 1 {
            Ok(queries.remove(0))
        } else {
            Ok(Box::new(tantivy::query::BooleanQuery::intersection(
                queries,
            )))
        }
    }
}

#[async_trait]
impl SearchBackend for TantivyIndex {
    async fn search(&self, query: &QuerySpec) -> EngineResult<Vec<SearchHit>> {
        self.reader
            .reload()
            .map_err(|e| EngineError::Search(e.to_string()))?;
        let searcher = self.reader.searcher();
        let q = self.parse_query(query)?;
        let top_docs = searcher
            .search(&q, &TopDocs::with_limit(query.limit))
            .map_err(|e| EngineError::Search(e.to_string()))?;

        let mut hits = Vec::new();
        for (score, addr) in top_docs {
            let id_val = searcher
                .doc::<tantivy::TantivyDocument>(addr)
                .map_err(|e| EngineError::Search(e.to_string()))?
                .get_first(self.id_field)
                .and_then(|f| f.as_str())
                .unwrap_or_default()
                .to_string();
            hits.push(SearchHit { id: id_val, score });
        }
        Ok(hits)
    }

    async fn index_document(&self, doc: &SegmentView) -> EngineResult<()> {
        let mut writer = self.writer.write().unwrap();
        let mut roots = Vec::new();
        let mut lemmas = Vec::new();
        let mut pos = Vec::new();
        let mut verb_forms = Vec::new();
        let mut genders = Vec::new();
        let mut numbers = Vec::new();
        let mut cases = Vec::new();
        let mut patterns = Vec::new();
        let mut voices = Vec::new();
        let mut moods = Vec::new();
        let mut tenses = Vec::new();
        let mut aspects = Vec::new();

        for seg in &doc.segments {
            if let Some(v) = &seg.root {
                roots.push(v.clone());
            }
            if let Some(v) = &seg.lemma {
                lemmas.push(v.clone());
            }
            if let Some(v) = &seg.pos {
                pos.push(v.clone());
            }
            if let Some(v) = &seg.verb_form {
                verb_forms.push(v.clone());
            }
            if let Some(v) = &seg.gender {
                genders.push(v.clone());
            }
            if let Some(v) = &seg.number {
                numbers.push(v.clone());
            }
            if let Some(v) = &seg.case_ {
                cases.push(v.clone());
            }
            if let Some(v) = &seg.pattern {
                patterns.push(v.clone());
            }
            if let Some(v) = &seg.voice {
                voices.push(v.clone());
            }
            if let Some(v) = &seg.mood {
                moods.push(v.clone());
            }
            if let Some(v) = &seg.tense {
                tenses.push(v.clone());
            }
            if let Some(v) = &seg.aspect {
                aspects.push(v.clone());
            }
        }

        let mut tdoc = doc!(self.id_field => doc.id.clone(), self.text_field => doc.text.clone());
        for v in roots {
            tdoc.add_text(self.roots_field, v);
        }
        for v in lemmas {
            tdoc.add_text(self.lemmas_field, v);
        }
        for v in pos {
            tdoc.add_text(self.pos_field, v);
        }
        for v in verb_forms {
            tdoc.add_text(self.verb_form_field, v);
        }
        for v in genders {
            tdoc.add_text(self.gender_field, v);
        }
        for v in numbers {
            tdoc.add_text(self.number_field, v);
        }
        for v in cases {
            tdoc.add_text(self.case_field, v);
        }
        for v in patterns {
            tdoc.add_text(self.pattern_field, v);
        }
        for v in voices {
            tdoc.add_text(self.voice_field, v);
        }
        for v in moods {
            tdoc.add_text(self.mood_field, v);
        }
        for v in tenses {
            tdoc.add_text(self.tense_field, v);
        }
        for v in aspects {
            tdoc.add_text(self.aspect_field, v);
        }

        writer
            .add_document(tdoc)
            .map_err(|e| EngineError::Search(e.to_string()))?;

        Ok(())
    }

}

impl TantivyIndex {
    pub fn commit(&self) -> EngineResult<()> {
        let mut writer = self.writer.write().unwrap();
        writer
            .commit()
            .map_err(|e| EngineError::Search(e.to_string()))?;
        Ok(())
    }

    pub async fn search_with_filters(
        &self,
        query: &str,
        filters: Vec<(String, Vec<String>)>,
        limit: usize,
    ) -> EngineResult<Vec<SearchHit>> {
        let filter_objs = filters
            .into_iter()
            .map(|(field, values)| kalima_core::QueryFilter {
                field,
                op: "in".into(),
                value: serde_json::Value::Array(values.into_iter().map(serde_json::Value::from).collect()),
            })
            .collect();
        let spec = kalima_core::QuerySpec {
            query: serde_json::Value::String(query.to_string()),
            filters: filter_objs,
            limit,
            offset: 0,
            sort: None,
        };
        self.search(&spec).await
    }
}
