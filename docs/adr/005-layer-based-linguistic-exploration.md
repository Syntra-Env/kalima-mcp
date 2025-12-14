# ADR 005: Layer-Based Linguistic Exploration (Remove `inspect`)

## Status
Accepted

## Date
2025-12-14

## Context
Kalima originally provided an `inspect` command that printed a large, monolithic linguistic analysis view.
As the UI grew, this became harder to maintain and harder to scan during normal reading/annotation workflows.

We also introduced a token-level "layer" system in the frontend where users can swap the visible token overlay
between different linguistic fields (root, lemma, POS, pattern, dependency, etc.) without losing the verse context.

## Decision
Adopt the layer system as the primary way to explore linguistic data in the UI and remove the legacy `inspect` command
from the CLI surface (and from help/docs).

## Rationale
- Keeps the verse in view while exploring a single dimension of morphology/syntax.
- Reduces large "wall of text" outputs that require scrolling.
- Encourages a consistent UI pattern (switch layers) instead of special-case commands.

## Consequences
- Users explore linguistic details via `layer <name|number>` and `layer next|prev`.
- Any future "summary" view should be designed as a dedicated UI component rather than a CLI text dump.
- Documentation and command laws must reference `layer` instead of `inspect`.

## Alternatives Considered
- Keep `inspect` and add layers: rejected to avoid two overlapping ways to do the same thing.
- Replace `inspect` with a different text-based command: rejected in favor of UI-native interaction.

