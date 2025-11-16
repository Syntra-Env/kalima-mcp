#!/usr/bin/env python3
"""
Annotation Manager - Search, version control, and evidence collection
Supports systematic hypothesis testing across Quranic corpus
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import shutil
from collections import defaultdict

# Handle Windows console encoding for Arabic text
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


class AnnotationManager:
    def __init__(self, corpus_path: str = None, tags_path: str = None):
        if corpus_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            corpus_path = os.path.join(project_root, 'corpus', 'quran.jsonl')
            tags_path = os.path.join(project_root, 'corpus', 'tags.json')

        self.corpus_path = corpus_path
        self.tags_path = tags_path
        self.verses = self.load_corpus()
        self.tags_data = self.load_tags()

    def load_corpus(self) -> List[dict]:
        """Load entire corpus into memory"""
        verses = []
        with open(self.corpus_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    verses.append(json.loads(line))
        return verses

    def load_tags(self) -> dict:
        """Load tag registry"""
        if os.path.exists(self.tags_path):
            with open(self.tags_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_corpus(self, backup: bool = True):
        """Save corpus with optional backup"""
        if backup:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(os.path.dirname(self.corpus_path), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, f"quran_{timestamp}.jsonl")
            shutil.copy2(self.corpus_path, backup_path)
            print(f"[OK] Backup created: {backup_path}")

        with open(self.corpus_path, 'w', encoding='utf-8') as f:
            for verse in self.verses:
                f.write(json.dumps(verse, ensure_ascii=False) + '\n')

    def get_verse(self, surah: int, ayah: int) -> Optional[dict]:
        """Get specific verse by surah:ayah"""
        for verse in self.verses:
            if verse['surah']['number'] == surah and verse['ayah'] == ayah:
                return verse
        return None

    def find_annotations(self, tag: Optional[str] = None,
                        annotation_type: Optional[str] = None,
                        status: Optional[str] = None,
                        verse_ref: Optional[str] = None) -> List[Tuple[str, dict]]:
        """
        Search for annotations with filters
        Returns list of (verse_ref, annotation) tuples
        """
        results = []

        for verse in self.verses:
            verse_ref = f"{verse['surah']['number']}:{verse['ayah']}"

            for annotation in verse.get('annotations', []):
                # Apply filters
                if tag and tag not in annotation.get('tags', []):
                    continue
                if annotation_type and annotation.get('type') != annotation_type:
                    continue
                if status and annotation.get('status') != status:
                    continue
                if verse_ref and not verse_ref.startswith(verse_ref):
                    continue

                results.append((verse_ref, annotation))

        return results

    def search_text(self, search_term: str, surah: Optional[int] = None) -> List[dict]:
        """Search Arabic text in corpus"""
        results = []

        for verse in self.verses:
            if surah and verse['surah']['number'] != surah:
                continue

            if search_term in verse['text']:
                results.append(verse)

        return results

    def find_root_instances(self, root: str) -> List[dict]:
        """
        Find all verses containing tokens with specific root
        Note: Requires tokens to be populated with root data
        """
        results = []

        for verse in self.verses:
            found = False
            for token in verse.get('tokens', []):
                if token.get('root') == root:
                    found = True
                    break

            if found:
                results.append(verse)

        return results

    def get_annotation_statistics(self) -> dict:
        """Generate annotation statistics"""
        stats = {
            'total_annotations': 0,
            'by_type': defaultdict(int),
            'by_status': defaultdict(int),
            'by_tag': defaultdict(int),
            'verses_with_annotations': 0,
            'avg_annotations_per_verse': 0.0
        }

        verses_with_annotations = set()

        for verse in self.verses:
            verse_ref = f"{verse['surah']['number']}:{verse['ayah']}"

            if verse.get('annotations'):
                verses_with_annotations.add(verse_ref)

            for annotation in verse.get('annotations', []):
                stats['total_annotations'] += 1
                stats['by_type'][annotation.get('type', 'unknown')] += 1
                stats['by_status'][annotation.get('status', 'unknown')] += 1

                for tag in annotation.get('tags', []):
                    stats['by_tag'][tag] += 1

        stats['verses_with_annotations'] = len(verses_with_annotations)
        if stats['verses_with_annotations'] > 0:
            stats['avg_annotations_per_verse'] = (
                stats['total_annotations'] / stats['verses_with_annotations']
            )

        return stats

    def add_annotation_version(self, surah: int, ayah: int, annotation_id: str,
                               changes: dict, change_note: str = "") -> bool:
        """Add new version to annotation (version control)"""
        verse = self.get_verse(surah, ayah)
        if not verse:
            print(f"[ERROR] Verse {surah}:{ayah} not found")
            return False

        # Find annotation
        annotation = None
        for ann in verse.get('annotations', []):
            if ann.get('id') == annotation_id:
                annotation = ann
                break

        if not annotation:
            print(f"[ERROR] Annotation {annotation_id} not found")
            return False

        # Initialize version control if not exists
        if 'versions' not in annotation:
            # Create version 1 from current state
            annotation['versions'] = [{
                'version': 1,
                'timestamp': annotation.get('created_at', datetime.now().isoformat()),
                'type': annotation.get('type'),
                'note': annotation.get('note'),
                'tags': annotation.get('tags', []),
                'status': annotation.get('status', 'hypothesis')
            }]
            annotation['current_version'] = 1

        # Create new version
        current_version = annotation['current_version']
        new_version = current_version + 1

        new_version_data = {
            'version': new_version,
            'timestamp': datetime.now().isoformat(),
            'type': annotation.get('type'),
            'note': annotation.get('note'),
            'tags': annotation.get('tags', []),
            'status': annotation.get('status', 'hypothesis'),
            'change_note': change_note
        }

        # Apply changes
        for key, value in changes.items():
            if key in new_version_data:
                new_version_data[key] = value
                annotation[key] = value

        annotation['versions'].append(new_version_data)
        annotation['current_version'] = new_version
        annotation['updated_at'] = datetime.now().isoformat()

        self.save_corpus()

        print(f"[OK] Created version {new_version} for annotation {annotation_id}")
        if change_note:
            print(f"Change: {change_note}")

        return True

    def show_annotation_history(self, surah: int, ayah: int, annotation_id: str):
        """Display version history of annotation"""
        verse = self.get_verse(surah, ayah)
        if not verse:
            print(f"[ERROR] Verse {surah}:{ayah} not found")
            return

        annotation = None
        for ann in verse.get('annotations', []):
            if ann.get('id') == annotation_id:
                annotation = ann
                break

        if not annotation:
            print(f"[ERROR] Annotation {annotation_id} not found")
            return

        print("=" * 60)
        print(f"Annotation History: {annotation_id}")
        print(f"Verse: {surah}:{ayah}")
        print("=" * 60)

        if 'versions' not in annotation:
            print("No version history available")
            return

        current = annotation.get('current_version', 1)

        for version_data in annotation['versions']:
            ver = version_data['version']
            marker = " [CURRENT]" if ver == current else ""
            print(f"\nVersion {ver}{marker}")
            print(f"  Timestamp: {version_data['timestamp']}")
            print(f"  Type: {version_data.get('type')}")
            print(f"  Status: {version_data.get('status')}")
            print(f"  Tags: {', '.join(version_data.get('tags', []))}")
            print(f"  Note: {version_data.get('note', '')[:80]}...")

            if 'change_note' in version_data:
                print(f"  Change: {version_data['change_note']}")

        print("=" * 60)

    def export_annotations(self, output_path: str, tag: Optional[str] = None,
                          format: str = 'json'):
        """Export annotations to file"""
        annotations = self.find_annotations(tag=tag)

        if format == 'json':
            export_data = []
            for verse_ref, annotation in annotations:
                export_data.append({
                    'verse': verse_ref,
                    'annotation': annotation
                })

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

        elif format == 'markdown':
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# Annotations\n\n")
                if tag:
                    f.write(f"Filtered by tag: {tag}\n\n")

                for verse_ref, annotation in annotations:
                    f.write(f"## {verse_ref}\n\n")
                    f.write(f"**Type:** {annotation.get('type')}\n\n")
                    f.write(f"**Status:** {annotation.get('status')}\n\n")
                    f.write(f"**Tags:** {', '.join(annotation.get('tags', []))}\n\n")
                    f.write(f"**Note:** {annotation.get('note')}\n\n")

                    if annotation.get('refs'):
                        f.write(f"**References:** {', '.join(annotation.get('refs'))}\n\n")

                    f.write("---\n\n")

        print(f"[OK] Exported {len(annotations)} annotations to {output_path}")

    def list_annotations(self, tag: Optional[str] = None,
                        annotation_type: Optional[str] = None,
                        limit: int = 20):
        """List annotations with filters"""
        annotations = self.find_annotations(tag=tag, annotation_type=annotation_type)

        if not annotations:
            print("No annotations found matching criteria")
            return

        print(f"\nFound {len(annotations)} annotation(s):")
        print("-" * 60)

        for i, (verse_ref, annotation) in enumerate(annotations[:limit], 1):
            print(f"\n{i}. {verse_ref}")
            print(f"   Type: {annotation.get('type')} | Status: {annotation.get('status')}")
            print(f"   Tags: {', '.join(annotation.get('tags', []))}")
            print(f"   Note: {annotation.get('note', '')[:70]}...")

        if len(annotations) > limit:
            print(f"\n... and {len(annotations) - limit} more")

    def show_statistics(self):
        """Display annotation statistics"""
        stats = self.get_annotation_statistics()

        print("=" * 60)
        print("Annotation Statistics")
        print("=" * 60)
        print(f"Total annotations: {stats['total_annotations']}")
        print(f"Verses with annotations: {stats['verses_with_annotations']}")
        print(f"Average annotations per verse: {stats['avg_annotations_per_verse']:.2f}")

        if stats['by_type']:
            print(f"\nBy Type:")
            for ann_type, count in sorted(stats['by_type'].items()):
                print(f"  {ann_type}: {count}")

        if stats['by_status']:
            print(f"\nBy Status:")
            for status, count in sorted(stats['by_status'].items()):
                print(f"  {status}: {count}")

        if stats['by_tag']:
            print(f"\nTop Tags:")
            top_tags = sorted(stats['by_tag'].items(), key=lambda x: x[1], reverse=True)[:10]
            for tag, count in top_tags:
                print(f"  {tag}: {count}")

        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Annotation Manager - Search, version control, and evidence collection"
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Find annotations
    find_parser = subparsers.add_parser('find', help='Find annotations')
    find_parser.add_argument('--tag', help='Filter by tag')
    find_parser.add_argument('--type', help='Filter by annotation type')
    find_parser.add_argument('--status', help='Filter by status')
    find_parser.add_argument('--limit', type=int, default=20, help='Limit results')

    # Search text
    search_parser = subparsers.add_parser('search', help='Search Arabic text')
    search_parser.add_argument('term', help='Search term (Arabic)')
    search_parser.add_argument('--surah', type=int, help='Limit to surah')

    # Find root
    root_parser = subparsers.add_parser('find-root', help='Find verses with root')
    root_parser.add_argument('root', help='Arabic root (e.g., ع-ل-م)')

    # Show history
    history_parser = subparsers.add_parser('history', help='Show annotation version history')
    history_parser.add_argument('verse', help='Verse reference (e.g., 2:31)')
    history_parser.add_argument('annotation_id', help='Annotation ID')

    # Export
    export_parser = subparsers.add_parser('export', help='Export annotations')
    export_parser.add_argument('output', help='Output file path')
    export_parser.add_argument('--tag', help='Filter by tag')
    export_parser.add_argument('--format', choices=['json', 'markdown'],
                               default='markdown', help='Export format')

    # Statistics
    subparsers.add_parser('stats', help='Show annotation statistics')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        am = AnnotationManager()

        if args.command == 'find':
            am.list_annotations(tag=args.tag, annotation_type=args.type, limit=args.limit)

        elif args.command == 'search':
            results = am.search_text(args.term, args.surah)
            print(f"\nFound {len(results)} verse(s) containing '{args.term}':")
            for verse in results[:20]:
                surah_num = verse['surah']['number']
                surah_name = verse['surah']['name']
                ayah = verse['ayah']
                print(f"  {surah_num}:{ayah} ({surah_name})")
                print(f"    {verse['text'][:80]}...")

        elif args.command == 'find-root':
            results = am.find_root_instances(args.root)
            if results:
                print(f"\nFound {len(results)} verse(s) with root '{args.root}':")
                for verse in results[:20]:
                    print(f"  {verse['surah']['number']}:{verse['ayah']}")
            else:
                print(f"No verses found with root '{args.root}'")
                print("Note: Corpus must have tokens with root data populated")

        elif args.command == 'history':
            # Parse verse reference
            parts = args.verse.split(':')
            if len(parts) != 2:
                print("[ERROR] Verse format should be SURAH:AYAH (e.g., 2:31)")
                return 1
            surah, ayah = int(parts[0]), int(parts[1])
            am.show_annotation_history(surah, ayah, args.annotation_id)

        elif args.command == 'export':
            am.export_annotations(args.output, tag=args.tag, format=args.format)

        elif args.command == 'stats':
            am.show_statistics()

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
