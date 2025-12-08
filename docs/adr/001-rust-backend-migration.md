# ADR 001: Migrate Backend from Python to Rust

**Status:** Accepted (Implemented November 2025)

**Decision Date:** 2025-11-01

## Context

The original Kalima backend was implemented in Python, which served well for prototyping and initial development. However, as the project matured, we encountered performance bottlenecks:

- Search latency was 500-1000ms for complex morphological queries
- Database operations were blocking, limiting concurrent request handling
- Memory usage grew linearly with dataset size
- Packaging and deployment required managing Python dependencies across platforms

## Decision

We decided to rewrite the entire backend in Rust while maintaining API compatibility with the existing frontend.

## Rationale

### Performance
- **10-100x speedup**: Search queries now complete in 10-50ms (vs 500-1000ms in Python)
- **Async I/O**: Tokio runtime enables non-blocking database and search operations
- **Zero-cost abstractions**: Rust's performance is comparable to C/C++ without sacrificing safety

### Type Safety
- Compile-time guarantees prevent entire classes of runtime errors
- No null pointer exceptions (Result/Option types)
- Strong typing catches API contract violations at build time

### Concurrency
- Safe concurrent access via Rust's ownership system
- No GIL (Global Interpreter Lock) limitations
- Arc/RwLock for shared state without data races

### Deployment
- Single static binary (no Python interpreter required)
- Cross-compilation for Windows/Linux/macOS
- Smaller binary size (~10MB vs ~50MB+ with Python + dependencies)

## Consequences

### Positive
- ✅ Dramatic performance improvement (measured 10-100x faster)
- ✅ Lower memory footprint (~50MB runtime vs ~200MB+ Python)
- ✅ Simplified deployment (one executable)
- ✅ Better error messages at compile time
- ✅ Type-safe API contracts enforced by compiler

### Negative
- ❌ Higher initial development time (Rust learning curve)
- ❌ Longer compile times (~25s release build vs instant Python)
- ❌ Smaller ecosystem for some niche libraries
- ❌ Team must learn Rust ownership/borrowing concepts

### Neutral
- 🔹 API compatibility maintained (no frontend changes required)
- 🔹 Migration completed incrementally over 3 weeks
- 🔹 All existing tests ported and passing

## Alternatives Considered

### Go
**Pros:** Simpler language, faster compile times, good concurrency
**Cons:** Garbage collected (unpredictable latency), nil pointers, less type safety
**Verdict:** Rejected due to GC pauses affecting search latency

### C++
**Pros:** Maximum performance, mature ecosystem
**Cons:** No memory safety, manual memory management, undefined behavior risks
**Verdict:** Rejected due to safety concerns and development velocity

### Keep Python with optimizations
**Pros:** No rewrite needed, team familiarity
**Cons:** Fundamental performance limits, GIL contention, type safety limitations
**Verdict:** Rejected as optimizations couldn't achieve target performance

## References

- [Changelog v1.0.0](../../CHANGELOG.md) - Performance benchmarks
- [RUNBOOK.md](../RUNBOOK.md) - Deployment procedures
- Python codebase (archived in git history at commit `c3bcf77`)
