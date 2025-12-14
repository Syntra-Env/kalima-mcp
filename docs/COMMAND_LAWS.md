# Command Laws (Operational Spec)

Minimal algebraic-style laws to keep the CLI behavior consistent. Each command is modeled as a function on `(state, output)` where `state = { current_verse }` and `output` is the stream of rendered messages.

- `clear`: `state' = state`, `output' = ∅`.
- `read chapter n`: `state'.current_verse = verse(n,1)`, `output' = render(surah n)`.
- `read verse a` (when `state.current_verse = v`): `state'.current_verse = verse(v.surah, a)`, `output' = render(verse)`.
- `read s:a`: `state'.current_verse = verse(s, a)`, `output' = render(verse)`.
- `layer x`: `state' = state`, `output' = render(layer x)` (no navigation; changes token overlay only).

Invariants:
- `render(verse)` always includes `surah:ayah` and token forms/text.
- If morphology is available, layers can display root | pos | type | form and other features per token (one layer at a time).
- `layer` never mutates `state.current_verse`.

These laws act as acceptance criteria for tests and future refinements.
