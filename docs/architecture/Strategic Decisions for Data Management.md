## Summary
The corpus is built on a **lossless, atom-level foundation** using the **Uthmānī Qurʾānic text** encoded in UTF-8. Each character (including letters, diacritics, and special signs) is stored as a distinct **Unicode code point (“atom”)** with stable positional indices.  
All annotations are **stand-off**, meaning they reference spans of these atoms by index rather than altering the text.

There are **no pre-built tokenizations or linguistic layers**; users define their own **segmentation schemes** (e.g., words, morphemes, rhetorical units). This keeps the base immutable and maximally flexible.

The data resides in a **relational database (PostgreSQL/SQLite)** for integrity, version control, and precise querying. Exports to **JSONL, Parquet, CoNLL-U, or graph formats** are handled through simple ETL scripts or read-only SQL views, ensuring smooth integration with **computational linguistics and machine learning pipelines**.

Every transformation—from normalization to transliteration—is **lossless and reversible**, maintaining one canonical textual source and guaranteeing that all derived data can be traced back to the original Qurʾānic script.
## Architecture Design Diagram
```
                     ┌──────────────────────────────────────────┐
                     │              Ingestion                   │
                     │  • Canonical Uthmānī UTF-8 verses        │
                     │  • Versioned import scripts               │
                     └───────────────┬───────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         Authoritative Store (RDBMS)                      │
│  ┌───────────────┐   ┌──────────────┐   ┌────────────────┐   ┌──────────┐│
│  │   verse       │   │    atom      │   │  segmentation  │   │annotation││
│  │ id,sura,aya   │   │ cp_idx,uchar │   │ scheme,unit,   │   │ layer,    ││
│  │ text, sha256  │   │ offsets,…    │   │ start..end     │   │ span,payload││
│  └───────────────┘   └──────────────┘   └────────────────┘   └──────────┘│
│                              ┌──────────────────────────────┐            │
│                              │        relation (edges)      │            │
│                              │ head_span ⇄ dep_span, rel    │            │
│                              └──────────────────────────────┘            │
└──────────────────────────────────────────────────────────────────────────┘
                                     │
                     ┌───────────────┼───────────────┐
                     │               │               │
                     ▼               ▼               ▼
          ┌─────────────────┐  ┌────────────────┐  ┌──────────────────┐
          │ Read-only Views │  │  Export/ETL    │  │   API/Access     │
          │ (per target)    │  │  Jobs          │  │ (REST/GraphQL)   │
          │ • CoNLLU_view   │  │ • JSONL writer │  │ • JSON-LD/RDF     │
          │ • Graph_edges   │  │ • Parquet dump │  │ • slice by span   │
          │ • JSONL_rows    │  │ • CSV for Neo4j│  │ • pick scheme     │
          └────────┬────────┘  └────────┬───────┘  └─────────┬─────────┘
                   │                    │                     │
                   ▼                    ▼                     ▼
        ┌───────────────────┐  ┌────────────────┐   ┌──────────────────────┐
        │  CoNLL-U files    │  │ JSONL / Parquet│   │   Graph DB (Neo4j)   │
        │  (seq labeling,   │  │ (ML training)  │   │   (:Span)-[:REL]->   │
        │   parsing)        │  │                │   │   (:Span)            │
        └───────────────────┘  └────────────────┘   └──────────────────────┘
```
## References
1. [Chat2DB - AI Text2SQL Tool for Easy Database Management](https://chat2db.ai/pricing)