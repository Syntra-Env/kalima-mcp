---
root: "ق و ل"   # change this per note
---

# Root view: `=this.root`

This note shows all tokens in the corpus whose `root` field matches the frontmatter `root`.

You can duplicate this file and change the `root` in the frontmatter for other roots (e.g. "ج ع ل", "ر ب ب", etc.).

```dataviewjs
// CONFIG
const root = dv.current().root ?? "ق و ل";   // fallback if frontmatter missing
const corpusPath = "corpus/quran.jsonl";

// LOAD CORPUS
const raw = await app.vault.adapter.read(corpusPath);
const lines = raw.split("\n").filter(l => l.trim().length > 0);

// EXTRACT MATCHING TOKENS
let rows = [];
for (const line of lines) {
    let verse;
    try {
        verse = JSON.parse(line);
    } catch (e) {
        console.error("Failed to parse line:", line, e);
        continue;
    }

    const surah = verse.surah;
    const ayah = verse.ayah;
    const tokens = verse.tokens ?? [];
    const annotations = verse.annotations ?? [];

    for (const t of tokens) {
        if (t.root === root) {
            rows.push({
                verseRef: `${surah}:${ayah}`,
                form: t.form ?? "",
                lemma: t.lemma ?? "",
                pos: t.pos ?? "",
                semanticField: (t.semantic_field ?? ""),
                annotationCount: annotations.length
            });
        }
    }
}

// SORT AND RENDER
rows.sort((a, b) => {
    const [s1, a1] = a.verseRef.split(":").map(Number);
    const [s2, a2] = b.verseRef.split(":").map(Number);
    return s1 - s2 || a1 - a2;
});

dv.table(
    ["Verse", "Form", "Lemma", "POS", "Semantic Field", "#Annotations"],
    rows.map(r => [r.verseRef, r.form, r.lemma, r.pos, r.semanticField, r.annotationCount])
);
