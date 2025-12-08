# Command Laws (Operational Spec)

Minimal algebraic-style laws to keep the CLI behavior consistent. Each command is modeled as a function on `(state, output)` where `state = { current_verse }` and `output` is the stream of rendered messages.

- `clear`: `state' = state`, `output' = ∅`.
- `see chapter n`: `state'.current_verse = verse(n,1)`, `output' = render(surah n)`.
- `see verse a` (when `state.current_verse = v`): `state'.current_verse = verse(v.surah, a)`, `output' = render(verse)`.
- `see verse s:a`: `state'.current_verse = verse(s, a)`, `output' = render(verse)`.
- `inspect` (with `state.current_verse = v`): `output' = render(analysis(v, morphology(v), dependency(v)))`, `state' = state`.
- `inspect s:a`: same as `inspect` after setting `current_verse = verse(s, a)`.

Invariants:
- `render(verse)` always includes `surah:ayah` and token forms/text.
- If morphology is available, `analysis` includes root | pos | type | form for each segment; otherwise falls back to verse tokens.
- Dependency render lists relation → word (and POS when present).

These laws act as acceptance criteria for tests and future refinements.
