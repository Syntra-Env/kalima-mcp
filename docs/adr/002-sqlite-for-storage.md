# ADR 002: Use SQLite for Primary Storage

**Status:** Accepted (Implemented November 2025)

**Decision Date:** 2025-11-01

## Context

Kalima requires persistent storage for:
- 6,236 Quranic verses with metadata
- 77,000+ tokens with morphological segments
- User annotations, connections, and research data
- Verse-level metadata (translations, hypotheses, pronouns)

The application primarily serves single-user desktop deployments, with optional server mode for multi-user scenarios.

## Decision

We chose SQLite as the primary relational database, using sqlx for async query execution.

## Rationale

### Simplicity
- **Zero configuration**: No server setup, no admin overhead
- **Single file**: Database is self-contained at `data/database/kalima.db`
- **No network layer**: Direct file access eliminates connection pool complexity
- **Bundled**: Ships with the application, no separate installation

### Performance
- **Local access**: Sub-millisecond query latency for indexed lookups
- **Write-ahead logging**: Concurrent reads don't block writers
- **In-memory option**: Can run entirely in RAM for testing (`sqlite::memory:`)
- **Efficient for dataset**: 6,236 verses fit comfortably in SQLite (tested up to millions of rows)

### Reliability
- **ACID transactions**: Full transactional guarantees
- **Crash-safe**: WAL mode ensures durability
- **Proven stability**: SQLite is the most deployed database worldwide
- **Well-tested**: Comprehensive test suite with 100% branch coverage

### Integration
- **sqlx library**: Compile-time query checking prevents SQL errors
- **Async support**: Non-blocking queries via tokio runtime
- **Type safety**: Rust types mapped to SQL types with validation
- **Migration support**: Schema versioning built into sqlx

## Consequences

### Positive
- ✅ No external dependencies (database ships with app)
- ✅ Simple backup (copy single file)
- ✅ Fast local queries (<1ms for indexed lookups)
- ✅ Works offline (no network required)
- ✅ Portable across platforms (Windows/Linux/macOS)
- ✅ Compile-time SQL validation via sqlx macros

### Negative
- ❌ Limited concurrency (one writer at a time)
- ❌ No built-in replication (single file)
- ❌ File locking issues on network filesystems
- ❌ Maximum database size ~140TB (not a practical concern)

### Neutral
- 🔹 Sufficient for single-user desktop use case
- 🔹 Can migrate to PostgreSQL if multi-user server demand grows
- 🔹 Connection pooling still used (max 5 connections)

## Alternatives Considered

### PostgreSQL
**Pros:** Better concurrency, replication, more features
**Cons:** Requires separate server, complex setup, overkill for single-user
**Verdict:** Rejected for desktop use case; SQLite is appropriate

### JSON files
**Pros:** Human-readable, no schema migration
**Cons:** No indexing, no transactions, slow queries, data integrity risks
**Verdict:** Rejected due to query performance and data integrity concerns

### Embedded key-value stores (RocksDB, sled)
**Pros:** High write throughput, LSM tree structure
**Cons:** No SQL queries, manual indexing, complex for relational data
**Verdict:** Rejected as relational model is natural fit for verse/token hierarchy

## Migration Path

If multi-user server deployment becomes primary use case:
1. Abstract storage behind `StorageBackend` trait (already done)
2. Implement `PostgresStorage` struct
3. Keep SQLite for desktop, use Postgres for server
4. Schema compatible (same normalization structure)

## References

- [SQLite documentation](https://www.sqlite.org/docs.html)
- [sqlx repository](https://github.com/launchbadge/sqlx)
- [engine/store/src/lib.rs](../../engine/store/src/lib.rs) - Storage implementation
- [ADR 003: Tantivy for Search](003-tantivy-for-search.md) - Complementary decision
