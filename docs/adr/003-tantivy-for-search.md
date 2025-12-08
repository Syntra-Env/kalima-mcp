# ADR 003: Use Tantivy for Full-Text Search

**Status:** Accepted (Implemented November 2025)

**Decision Date:** 2025-11-01

## Context

Kalima requires sophisticated search capabilities:
- **Full-text search**: Find Arabic text across 6,236 verses
- **Morphological filtering**: Search by root, POS tag, morphological pattern
- **Faceted search**: Combine text queries with multiple filters (e.g., root="سمع" + pos="V")
- **Performance**: Sub-50ms search latency for all queries
- **Arabic support**: Proper handling of Unicode, diacritics, and variants

## Decision

We chose Tantivy as our full-text search engine, running in-process with the API server.

## Rationale

### Pure Rust Integration
- **Native Rust library**: Zero FFI overhead, type-safe integration
- **In-process**: No separate search server, simpler deployment
- **Memory safety**: Rust's guarantees extend to search indexing
- **Async-first**: Non-blocking search queries via async API

### Performance
- **Sub-50ms queries**: Measured 10-50ms for complex morphological searches
- **Inverted index**: Optimized for text and keyword lookups
- **RAM-efficient**: Mmap for index data, low memory footprint
- **Fast indexing**: 6,236 verses indexed in <1 second

### Features
- **Full-text search**: BM25 ranking algorithm
- **Faceted search**: Multi-field filtering (root, pos, pattern, etc.)
- **Field types**: Text (analyzed), keywords (exact match), numeric
- **Query parser**: Boolean logic, phrase queries, wildcards
- **Schema flexibility**: 13 indexed fields for morphological data

### Arabic Support
- **Unicode-aware**: Handles Arabic script natively
- **Diacritic handling**: Can index with or without tashkeel
- **Custom analyzers**: Potential for Arabic-specific tokenization
- **Root normalization**: Store multiple roots per token

## Consequences

### Positive
- ✅ Fast search (<50ms for 99th percentile)
- ✅ No external dependencies (embedded library)
- ✅ Type-safe query construction
- ✅ Flexible schema supports morphological complexity
- ✅ Compact index size (~8MB for full Quran corpus)
- ✅ Simple deployment (index stored in `data/search-index/`)

### Negative
- ❌ Less mature than Elasticsearch/Solr
- ❌ No distributed search (single-node only)
- ❌ Limited query language compared to Lucene
- ❌ Smaller community/ecosystem

### Neutral
- 🔹 Index must be committed after writes (explicit flush)
- 🔹 No hot-reload of index (requires restart for schema changes)
- 🔹 Sufficient for single-machine deployment

## Schema Design

```rust
// Indexed fields:
- text (analyzed)      // Full verse text
- root (keyword)       // Morphological root (multiple)
- lemma (keyword)      // Lemma forms
- pos (keyword)        // Part-of-speech tags
- pattern (keyword)    // Morphological patterns
- verb_form (keyword)  // Verb forms (I-X)
- gender (keyword)     // Grammatical gender
- number (keyword)     // Singular/dual/plural
- case (keyword)       // Grammatical case
- voice (keyword)      // Active/passive
- mood (keyword)       // Indicative/subjunctive/jussive
- tense (keyword)      // Past/present/imperative
- aspect (keyword)     // Perfective/imperfective
- id (stored)          // Document ID (not indexed)
```

## Alternatives Considered

### Elasticsearch
**Pros:** Battle-tested, distributed, rich query language
**Cons:** Separate JVM process, complex deployment, heavy resource usage (>512MB RAM)
**Verdict:** Rejected as overkill for single-user desktop app

### MeiliSearch
**Pros:** Modern Rust search engine, typo-tolerance, instant search
**Cons:** Focus on prefix search, less flexible for linguistic analysis
**Verdict:** Rejected as morphological filtering is priority over typo-tolerance

### SQLite FTS5
**Pros:** Integrated with SQLite, no extra dependency
**Cons:** Limited to simple full-text, no faceted search, poor performance for complex queries
**Verdict:** Rejected due to morphological search requirements

### Custom inverted index
**Pros:** Full control, minimal dependencies
**Cons:** Significant development effort, unlikely to match Tantivy performance
**Verdict:** Rejected in favor of proven library

## Search Patterns

### Example: Root-based search
```rust
index.search_with_filters(
    "",  // No text query
    vec![("root".into(), vec!["سمع".into()])],
    50   // Limit
)
```

### Example: Combined morphological query
```rust
// Find all perfective active verbs from root "قول"
index.search_with_filters(
    "",
    vec![
        ("root".into(), vec!["قول".into()]),
        ("pos".into(), vec!["V".into()]),
        ("aspect".into(), vec!["perfective".into()]),
        ("voice".into(), vec!["active".into()])
    ],
    100
)
```

## Performance Benchmarks

| Query Type | Latency (p50) | Latency (p99) |
|------------|---------------|---------------|
| Full-text search | 12ms | 28ms |
| Root lookup | 8ms | 15ms |
| POS filter | 10ms | 22ms |
| Complex (3+ filters) | 25ms | 48ms |

*Measured on Intel i7 with 6,236 verse corpus*

## Future Considerations

- **Arabic stemming**: Custom analyzer for root extraction
- **Diacritic-insensitive search**: Optional normalization layer
- **Fuzzy matching**: Edit distance for typos (low priority)
- **Relevance tuning**: Adjust BM25 parameters for Arabic text

## References

- [Tantivy documentation](https://docs.rs/tantivy)
- [Tantivy repository](https://github.com/tantivy-search/tantivy)
- [engine/search/src/lib.rs](../../engine/search/src/lib.rs) - Search implementation
- [ADR 002: SQLite for Storage](002-sqlite-for-storage.md) - Complementary decision
