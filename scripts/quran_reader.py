#!/usr/bin/env python3
"""
Quran Reader - Interactive research interface
Navigate, read, annotate with hypothesis-driven workflow
"""

import json
import os
import sys
import re
from datetime import datetime
from typing import List, Optional, Tuple

# Handle Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


def reverse_arabic_text(text: str) -> str:
    """
    Reverse Arabic text for display in non-RTL terminals.
    Keeps diacritics with their base letters (grapheme clusters).

    Arabic diacritics (combining marks) must stay with their base letter.
    Unicode combining marks: 0x064B-0x065F, 0x0670, 0x06D6-0x06ED
    """
    # Arabic combining marks (diacritics, hamza, etc.)
    ARABIC_DIACRITICS = re.compile(r'[\u064B-\u065F\u0670\u06D6-\u06ED]')

    # Split into grapheme clusters (base char + following diacritics)
    clusters = []
    i = 0
    while i < len(text):
        cluster = text[i]
        i += 1
        # Collect all following diacritics
        while i < len(text) and ARABIC_DIACRITICS.match(text[i]):
            cluster += text[i]
            i += 1
        clusters.append(cluster)

    # Reverse the clusters
    return ''.join(reversed(clusters))


class QuranReader:
    def __init__(self):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.corpus_path = os.path.join(project_root, 'corpus', 'quran.jsonl')
        self.tags_path = os.path.join(project_root, 'corpus', 'tags.json')

        self.verses = self.load_corpus()
        self.tags = self.load_tags()
        self.current_index = 0

    def load_corpus(self) -> List[dict]:
        """Load corpus"""
        verses = []
        with open(self.corpus_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    verses.append(json.loads(line))
        return verses

    def load_tags(self) -> dict:
        """Load tag registry"""
        if os.path.exists(self.tags_path):
            with open(self.tags_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_corpus(self):
        """Save corpus with backups"""
        # Backup
        backup_dir = os.path.join(os.path.dirname(self.corpus_path), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"quran_{timestamp}.jsonl")

        import shutil
        shutil.copy2(self.corpus_path, backup_path)

        # Save
        with open(self.corpus_path, 'w', encoding='utf-8') as f:
            for verse in self.verses:
                f.write(json.dumps(verse, ensure_ascii=False) + '\n')

    def save_tags(self):
        """Save tag registry"""
        self.tags['last_updated'] = datetime.now().isoformat()
        with open(self.tags_path, 'w', encoding='utf-8') as f:
            json.dump(self.tags, f, ensure_ascii=False, indent=2)

    def goto(self, surah: int, ayah: int) -> bool:
        """Navigate to specific verse"""
        for i, verse in enumerate(self.verses):
            if verse['surah']['number'] == surah and verse['ayah'] == ayah:
                self.current_index = i
                return True
        return False

    def next_verse(self):
        """Go to next verse"""
        if self.current_index < len(self.verses) - 1:
            self.current_index += 1

    def prev_verse(self):
        """Go to previous verse"""
        if self.current_index > 0:
            self.current_index -= 1

    def get_current_verse(self) -> dict:
        """Get current verse"""
        return self.verses[self.current_index]

    def display_verse(self, show_tokens: bool = True, show_morphology: bool = False):
        """Display current verse"""
        verse = self.get_current_verse()
        surah_num = verse['surah']['number']
        surah_name = verse['surah']['name']
        ayah = verse['ayah']

        print("\n" + "=" * 70)
        print(f"Surah {surah_num} ({surah_name}), Ayah {ayah}")
        print("=" * 70)
        # Reverse Arabic text for proper display in non-RTL terminals
        print(f"\n{reverse_arabic_text(verse['text'])}\n")

        if show_tokens and verse.get('tokens'):
            print("-" * 70)
            print("Tokens:")
            # Display tokens in reverse order for right-to-left reading
            for token in reversed(verse['tokens']):
                # Reverse Arabic token form for display
                reversed_form = reverse_arabic_text(token['form'])
                print(f"  [{token['id']}] {reversed_form}", end="")
                if show_morphology and token.get('segments'):
                    print()
                    # Display segments in reverse order too
                    for seg in reversed(token['segments']):
                        root_info = f" root:{seg['root']}" if seg.get('root') else ""
                        lemma_info = f" lemma:{seg['lemma']}" if seg.get('lemma') else ""
                        # Only show morphological metadata, not transliterated forms
                        print(f"      {seg['id']}: [{seg['type']}] {seg['pos']}{root_info}{lemma_info}")
                else:
                    print("  ", end="")
            print("\n" + "-" * 70)

        # Show existing annotations
        if verse.get('annotations'):
            print(f"\nAnnotations ({len(verse['annotations'])}):")
            for ann in verse['annotations']:
                print(f"  - [{ann.get('type')}] {ann.get('note', '')[:50]}...")
                if ann.get('tags'):
                    print(f"    Tags: {', '.join(ann['tags'])}")

    def show_token_details(self, token_spec: str):
        """Show detailed morphology for token"""
        verse = self.get_current_verse()

        if not verse.get('tokens'):
            print("[ERROR] No tokens available for this verse")
            return

        # Parse token spec (e.g., "1", "1.2", "1-3")
        if '-' in token_spec:
            # Range
            parts = token_spec.split('-')
            start, end = int(parts[0]), int(parts[1])
            tokens = [t for t in verse['tokens'] if start <= t['id'] <= end]
        elif '.' in token_spec:
            # Specific segment
            word_id, seg_id = token_spec.split('.')
            word_id = int(word_id)
            token = next((t for t in verse['tokens'] if t['id'] == word_id), None)
            if token and token.get('segments'):
                segment = next((s for s in token['segments'] if s['id'] == token_spec), None)
                if segment:
                    print(f"\nSegment {segment['id']}")
                    print(f"  Type: {segment['type']}")
                    print(f"  POS: {segment['pos']}")
                    if segment.get('root'):
                        print(f"  Root: {segment['root']}")
                    if segment.get('lemma'):
                        print(f"  Lemma: {segment['lemma']}")
                    if segment.get('features'):
                        print(f"  Features: {segment['features']}")
                return
        else:
            # Single token
            token_id = int(token_spec)
            tokens = [t for t in verse['tokens'] if t['id'] == token_id]

        if not tokens:
            print(f"[ERROR] Token '{token_spec}' not found")
            return

        for token in tokens:
            reversed_form = reverse_arabic_text(token['form'])
            print(f"\nToken {token['id']}: {reversed_form}")
            if token.get('segments'):
                for seg in token['segments']:
                    print(f"  {seg['id']}: [{seg['type']}]")
                    print(f"    POS: {seg['pos']}")
                    if seg.get('root'):
                        print(f"    Root: {seg['root']}")
                    if seg.get('lemma'):
                        print(f"    Lemma: {seg['lemma']}")

    def create_annotation(self, token_spec: str, ann_type: str, note: str,
                         tags: List[str], link_to_hypothesis: Optional[str] = None):
        """Create new annotation"""
        verse = self.get_current_verse()

        # Parse token selection
        target_tokens = self.parse_token_selection(token_spec)
        if not target_tokens:
            print(f"[ERROR] Invalid token selection: {token_spec}")
            return False

        # Determine scope
        if '-' in token_spec or ',' in token_spec:
            scope = "span"
        elif '.' in token_spec:
            scope = "token"  # morpheme level
        else:
            scope = "token"

        # Generate annotation ID
        timestamp = datetime.now()
        ann_id = timestamp.strftime("a-%Y%m%d-%H%M%S-001-YA")

        # Create annotation
        annotation = {
            "id": ann_id,
            "type": ann_type,
            "scope": scope,
            "target_token_ids": target_tokens,
            "note": note,
            "tags": tags,
            "refs": [],
            "status": "hypothesis",
            "created_at": timestamp.isoformat(),
            "updated_at": timestamp.isoformat()
        }

        # Add to verse
        if 'annotations' not in verse:
            verse['annotations'] = []
        verse['annotations'].append(annotation)

        # Save corpus
        self.save_corpus()

        print(f"[OK] Created annotation {ann_id}")

        # Link to hypothesis tag if specified
        if link_to_hypothesis and link_to_hypothesis in self.tags.get('tags', {}):
            self.link_annotation_to_tag(annotation, link_to_hypothesis)

        return True

    def parse_token_selection(self, token_spec: str) -> List[str]:
        """Parse token selection string"""
        result = []

        if ',' in token_spec:
            # Multiple selections: "1,3,5" or "1.2,2.1"
            parts = token_spec.split(',')
            for part in parts:
                result.extend(self.parse_token_selection(part.strip()))
        elif '-' in token_spec:
            # Range: "1-3"
            parts = token_spec.split('-')
            start, end = int(parts[0]), int(parts[1])
            result.extend([str(i) for i in range(start, end + 1)])
        else:
            # Single: "1" or "1.2"
            result.append(token_spec)

        return result

    def link_annotation_to_tag(self, annotation: dict, tag_name: str):
        """Link annotation as evidence to hypothesis tag"""
        if tag_name not in self.tags.get('tags', {}):
            print(f"[ERROR] Tag '{tag_name}' not found")
            return

        verse = self.get_current_verse()
        verse_ref = f"{verse['surah']['number']}:{verse['ayah']}"

        tag = self.tags['tags'][tag_name]

        # Add to evidence
        evidence_entry = {
            "verse": verse_ref,
            "note": annotation['note'],
            "date": datetime.now().isoformat(),
            "annotation_id": annotation['id']
        }

        tag['evidence']['supporting'].append(evidence_entry)
        tag['evidence']['tested_instances'] += 1
        tag['last_updated'] = datetime.now().isoformat()

        # Add to verification log
        tag['verification_log'].append({
            "date": datetime.now().isoformat(),
            "action": "evidence_added",
            "verse": verse_ref,
            "note": annotation['note']
        })

        # Check for auto-promotion
        self.check_tag_promotion(tag_name)

        # Save tags
        self.save_tags()

        print(f"[OK] Linked to hypothesis '{tag_name}' as supporting evidence")

    def check_tag_promotion(self, tag_name: str):
        """Check if tag should be auto-promoted"""
        tag = self.tags['tags'][tag_name]
        current_status = tag['status']
        supporting = len(tag['evidence']['supporting'])

        # hypothesis → viable (2+ supporting)
        if current_status == 'hypothesis' and supporting >= 2:
            tag['status'] = 'viable'
            tag['verification_log'].append({
                "date": datetime.now().isoformat(),
                "action": "status_change",
                "from_status": "hypothesis",
                "to_status": "viable",
                "note": f"Auto-promoted: {supporting} supporting examples found"
            })
            print(f"[OK] Tag auto-promoted: hypothesis -> viable")

    def list_tags(self):
        """List available hypothesis tags"""
        tags = self.tags.get('tags', {})
        if not tags:
            print("No hypothesis tags available")
            return

        print("\nAvailable Hypothesis Tags:")
        print("-" * 70)
        for tag_name, tag_data in sorted(tags.items()):
            status = tag_data['status']
            supporting = len(tag_data['evidence']['supporting'])
            print(f"  {tag_name} [{status}] - {supporting} evidence")
            print(f"    {tag_data['hypothesis'][:60]}...")

    def interactive(self):
        """Interactive reader mode"""
        print("\n" + "=" * 70)
        print("CODEX - Quran Reader")
        print("=" * 70)
        print("\nCommands:")
        print("  go SURAH:AYAH  - Navigate to verse (e.g., 'go 2:31')")
        print("  next, prev     - Navigate verses")
        print("  show           - Display current verse")
        print("  tokens         - Show tokens with morphology")
        print("  info TOKEN     - Show token details (e.g., 'info 1.2')")
        print("  annotate       - Create annotation (guided)")
        print("  tags           - List hypothesis tags")
        print("  quit           - Exit")
        print("=" * 70)

        # Show first verse
        self.display_verse()

        while True:
            try:
                cmd = input("\n> ").strip().lower()

                if not cmd:
                    continue

                if cmd == 'quit' or cmd == 'exit' or cmd == 'q':
                    print("Goodbye!")
                    break

                elif cmd == 'next' or cmd == 'n':
                    self.next_verse()
                    self.display_verse()

                elif cmd == 'prev' or cmd == 'p':
                    self.prev_verse()
                    self.display_verse()

                elif cmd == 'show' or cmd == 's':
                    self.display_verse()

                elif cmd == 'tokens' or cmd == 't':
                    self.display_verse(show_tokens=True, show_morphology=True)

                elif cmd.startswith('go '):
                    parts = cmd.split()[1].split(':')
                    if len(parts) == 2:
                        surah, ayah = int(parts[0]), int(parts[1])
                        if self.goto(surah, ayah):
                            self.display_verse()
                        else:
                            print(f"[ERROR] Verse {surah}:{ayah} not found")
                    else:
                        print("[ERROR] Format: go SURAH:AYAH (e.g., go 2:31)")

                elif cmd.startswith('info '):
                    token_spec = cmd.split()[1]
                    self.show_token_details(token_spec)

                elif cmd == 'annotate' or cmd == 'a':
                    self.guided_annotation()

                elif cmd == 'tags':
                    self.list_tags()

                elif cmd == 'help' or cmd == 'h':
                    self.display_help()

                else:
                    print(f"[ERROR] Unknown command: {cmd}")
                    print("Type 'help' for commands")

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"[ERROR] {e}")

    def guided_annotation(self):
        """Guided annotation creation"""
        print("\n--- Create Annotation ---")

        # Token selection
        tokens_input = input("Select tokens (e.g., '1', '1.2', '1-3', '1,3,5'): ").strip()
        if not tokens_input:
            print("Cancelled")
            return

        # Type
        print("\nAnnotation types:")
        print("  1. morphological  2. syntactic    3. rhetorical")
        print("  4. stylistic      5. thematic     6. compositional")
        print("  7. phonological   8. logical      9. psychological")
        print("  10. ontology")
        type_choice = input("Choose type (1-10 or name): ").strip()

        type_map = {
            '1': 'morphological', '2': 'syntactic', '3': 'rhetorical',
            '4': 'stylistic', '5': 'thematic', '6': 'compositional',
            '7': 'phonological', '8': 'logical', '9': 'psychological',
            '10': 'ontology'
        }

        ann_type = type_map.get(type_choice, type_choice)

        # Note
        note = input("\nAnnotation note: ").strip()
        if not note:
            print("Cancelled")
            return

        # Tags
        tags_input = input("Tags (comma-separated): ").strip()
        tags = [t.strip() for t in tags_input.split(',')] if tags_input else []

        # Link to hypothesis
        self.list_tags()
        link_tag = input("\nLink to hypothesis tag (or press Enter to skip): ").strip()

        # Create
        self.create_annotation(
            tokens_input,
            ann_type,
            note,
            tags,
            link_tag if link_tag else None
        )

    def display_help(self):
        """Display help"""
        print("\n" + "=" * 70)
        print("CODEX Quran Reader - Commands")
        print("=" * 70)
        print("\nNavigation:")
        print("  go 2:31        - Jump to surah 2, ayah 31")
        print("  next (or n)    - Next verse")
        print("  prev (or p)    - Previous verse")
        print("\nDisplay:")
        print("  show (or s)    - Show current verse")
        print("  tokens (or t)  - Show with full morphology")
        print("  info 1.2       - Show details for token/segment")
        print("\nAnnotation:")
        print("  annotate (or a) - Create annotation (guided)")
        print("  tags           - List hypothesis tags")
        print("\nOther:")
        print("  help (or h)    - Show this help")
        print("  quit (or q)    - Exit")
        print("=" * 70)


def main():
    reader = QuranReader()
    reader.interactive()


if __name__ == '__main__':
    main()
