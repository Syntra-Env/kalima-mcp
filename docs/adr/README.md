# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) documenting significant architectural and design decisions made in the Kalima project.

## What is an ADR?

An Architecture Decision Record (ADR) is a document that captures an important architectural decision made along with its context and consequences. ADRs help teams:

- Understand **why** decisions were made, not just **what** was decided
- Onboard new team members by documenting historical context
- Avoid relitigating past decisions
- Learn from both successful and unsuccessful choices

## Format

Each ADR follows this structure:
- **Title**: Short, descriptive name (e.g., "Use SQLite for Storage")
- **Status**: Proposed, Accepted, Deprecated, Superseded
- **Context**: What forces/constraints led to the decision
- **Decision**: What was decided
- **Rationale**: Why this choice over alternatives
- **Consequences**: Positive, negative, and neutral outcomes
- **Alternatives Considered**: Other options and why they were rejected

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](001-rust-backend-migration.md) | Migrate Backend from Python to Rust | Accepted | 2025-11-01 |
| [002](002-sqlite-for-storage.md) | Use SQLite for Primary Storage | Accepted | 2025-11-01 |
| [003](003-tantivy-for-search.md) | Use Tantivy for Full-Text Search | Accepted | 2025-11-01 |
| [004](004-vanilla-javascript-frontend.md) | Vanilla JavaScript Frontend (No Framework) | Accepted | 2025-11-01 |

## Decision Categories

### Backend Architecture
- [ADR 001](001-rust-backend-migration.md): Why Rust over Python/Go/C++
- [ADR 002](002-sqlite-for-storage.md): Why SQLite over PostgreSQL/NoSQL
- [ADR 003](003-tantivy-for-search.md): Why Tantivy over Elasticsearch/MeiliSearch

### Frontend Architecture
- [ADR 004](004-vanilla-javascript-frontend.md): Why no React/Vue/Angular

## Creating New ADRs

When making significant architectural decisions:

1. Copy the template from an existing ADR
2. Number sequentially (next would be `005-title.md`)
3. Fill in all sections thoughtfully
4. Consider alternatives seriously (document why rejected)
5. Add to this index
6. Commit with the implementation or before if proposing

## Key Principles

Based on our ADRs, Kalima values:

1. **Performance over convenience**: Rust chosen for 10-100x speedup
2. **Simplicity over features**: SQLite, vanilla JS chosen over complex alternatives
3. **Type safety over flexibility**: Compile-time guarantees preferred
4. **Single-user optimization**: Desktop-first, not distributed systems
5. **Minimal dependencies**: Reduce supply chain risk and complexity

## References

- [ADR process by Michael Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [ADR GitHub organization](https://adr.github.io/)
- Our [RUNBOOK.md](../RUNBOOK.md) for operational procedures
- Our [TESTING.md](../TESTING.md) for testing strategy
