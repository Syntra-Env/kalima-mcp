# API Contracts (Minimal)

These capture the shapes the desktop CLI relies on. Treat them as contracts for both server and clients/tests.

## `GET /api/verse/{surah}/{ayah}`
```json
{
  "surah": { "number": 1, "name": "..." },
  "ayah": 1,
  "text": "...",
  "tokens": [
    {
      "index": 0,
      "text": "...",
      "form": "...",
      "segments": [
        { "id": "...", "root": "...", "pos": "...", "type": "..." }
      ]
    }
  ]
}
```

## `GET /api/morphology/{surah}/{ayah}`
```json
{
  "surah": 1,
  "ayah": 1,
  "morphology": [
    {
      "text": "...",
      "pos": "...",
      "root": "...",
      "form": "...",
      "type": "...",
      "dependency_rel": "..."
    }
  ]
}
```

## `GET /api/dependency/{surah}/{ayah}`
```json
{
  "surah": 1,
  "ayah": 1,
  "dependency_tree": [
    {
      "rel_label": "subj",
      "word": "...",
      "pos": "N"
    }
  ]
}
```

## Invariants
- `surah >= 1`, `ayah >= 1`.
- `tokens[*].segments` may be empty but must be present.
- Morphology entries should preserve `text`, `pos`, `root`, `form` when known; missing fields are null/omitted.
- Dependency entries should include `rel_label` and `word`; `pos` optional.

Use these shapes when creating fixtures and when validating responses in contract tests.
