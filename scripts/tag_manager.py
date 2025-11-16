#!/usr/bin/env python3
"""
Tag Manager - Hypothesis verification and tag lifecycle management
Supports scientific methodology for Quranic research
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import difflib

# Handle Windows console encoding for Arabic text
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


class TagManager:
    def __init__(self, tags_path: str = None):
        if tags_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            tags_path = os.path.join(project_root, 'corpus', 'tags.json')

        self.tags_path = tags_path
        self.data = self.load()

    def load(self) -> dict:
        """Load tag registry"""
        if not os.path.exists(self.tags_path):
            raise FileNotFoundError(f"Tag registry not found: {self.tags_path}")

        with open(self.tags_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save(self):
        """Save tag registry"""
        self.data['last_updated'] = datetime.now().isoformat()
        self.update_statistics()

        with open(self.tags_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def update_statistics(self):
        """Recalculate tag statistics"""
        tags = self.data.get('tags', {})

        self.data['statistics']['total_tags'] = len(tags)

        # Reset counters
        for status in self.data['statistics']['by_status']:
            self.data['statistics']['by_status'][status] = 0
        for category in self.data['statistics']['by_category']:
            self.data['statistics']['by_category'][category] = 0

        # Count tags
        for tag_data in tags.values():
            status = tag_data.get('status', 'hypothesis')
            category = tag_data.get('category', 'thematic')

            if status in self.data['statistics']['by_status']:
                self.data['statistics']['by_status'][status] += 1
            if category in self.data['statistics']['by_category']:
                self.data['statistics']['by_category'][category] += 1

    def create_tag(self, tag_name: str, category: str, hypothesis: str,
                   initial_evidence: Optional[str] = None) -> bool:
        """Create new hypothesis tag"""
        if tag_name in self.data['tags']:
            print(f"[ERROR] Tag '{tag_name}' already exists")
            return False

        if category not in self.data['taxonomy']:
            print(f"[ERROR] Unknown category '{category}'")
            print(f"Available: {', '.join(self.data['taxonomy'].keys())}")
            return False

        tag_data = {
            "category": category,
            "status": "hypothesis",
            "hypothesis": hypothesis,
            "created_date": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "evidence": {
                "supporting": [],
                "counter_examples": [],
                "total_instances": None,
                "tested_instances": 0,
                "pending_review": None
            },
            "verification_log": [
                {
                    "date": datetime.now().isoformat(),
                    "action": "created",
                    "status": "hypothesis",
                    "note": "Tag created with initial hypothesis"
                }
            ],
            "challenges": [],
            "related_hypotheses": []
        }

        if initial_evidence:
            tag_data['evidence']['supporting'].append({
                "verse": initial_evidence,
                "note": "Initial observation",
                "date": datetime.now().isoformat()
            })

        self.data['tags'][tag_name] = tag_data
        self.save()

        print(f"[OK] Created hypothesis tag: {tag_name}")
        print(f"Category: {category}")
        print(f"Status: hypothesis")
        if initial_evidence:
            print(f"Initial evidence: {initial_evidence}")

        return True

    def add_evidence(self, tag_name: str, verse: str, note: str,
                     is_counter: bool = False) -> bool:
        """Add supporting evidence or counter-example"""
        if tag_name not in self.data['tags']:
            print(f"[ERROR] Tag '{tag_name}' not found")
            return False

        tag = self.data['tags'][tag_name]
        evidence_entry = {
            "verse": verse,
            "note": note,
            "date": datetime.now().isoformat()
        }

        if is_counter:
            tag['evidence']['counter_examples'].append(evidence_entry)
            evidence_type = "counter-example"

            # Add to verification log
            tag['verification_log'].append({
                "date": datetime.now().isoformat(),
                "action": "counter_example_added",
                "verse": verse,
                "note": note
            })
        else:
            tag['evidence']['supporting'].append(evidence_entry)
            evidence_type = "supporting evidence"

            # Add to verification log
            tag['verification_log'].append({
                "date": datetime.now().isoformat(),
                "action": "evidence_added",
                "verse": verse,
                "note": note
            })

        tag['evidence']['tested_instances'] += 1
        tag['last_updated'] = datetime.now().isoformat()

        # Check for auto-promotion
        self._check_promotion(tag_name)

        self.save()

        print(f"[OK] Added {evidence_type} to '{tag_name}'")
        print(f"Verse: {verse}")
        print(f"Note: {note}")

        return True

    def _check_promotion(self, tag_name: str):
        """Check if tag should be auto-promoted to next status"""
        tag = self.data['tags'][tag_name]
        current_status = tag['status']
        supporting = len(tag['evidence']['supporting'])
        counter = len(tag['evidence']['counter_examples'])

        # hypothesis → viable (needs 2+ supporting examples)
        if current_status == 'hypothesis' and supporting >= 2:
            self.promote_status(tag_name, 'viable',
                               f"Auto-promoted: {supporting} supporting examples found")

        # viable/testing → challenged (if counter-examples found)
        elif current_status in ['viable', 'testing'] and counter > 0:
            unresolved = [c for c in tag['evidence']['counter_examples']
                         if 'resolution' not in c or c['resolution'] == 'pending']
            if unresolved:
                self.promote_status(tag_name, 'challenged',
                                   f"Status changed: {len(unresolved)} unresolved counter-examples")

    def promote_status(self, tag_name: str, new_status: str, note: str = "") -> bool:
        """Promote tag to new status"""
        if tag_name not in self.data['tags']:
            print(f"[ERROR] Tag '{tag_name}' not found")
            return False

        valid_statuses = list(self.data['status_definitions'].keys())
        if new_status not in valid_statuses:
            print(f"[ERROR] Invalid status '{new_status}'")
            print(f"Valid: {', '.join(valid_statuses)}")
            return False

        tag = self.data['tags'][tag_name]
        old_status = tag['status']
        tag['status'] = new_status
        tag['last_updated'] = datetime.now().isoformat()

        tag['verification_log'].append({
            "date": datetime.now().isoformat(),
            "action": "status_change",
            "from_status": old_status,
            "to_status": new_status,
            "note": note
        })

        self.save()

        print(f"[OK] Status updated: {old_status} -> {new_status}")
        if note:
            print(f"Note: {note}")

        return True

    def add_challenge(self, tag_name: str, challenge_text: str) -> bool:
        """Add challenge/question to hypothesis"""
        if tag_name not in self.data['tags']:
            print(f"[ERROR] Tag '{tag_name}' not found")
            return False

        tag = self.data['tags'][tag_name]
        tag['challenges'].append({
            "date": datetime.now().isoformat(),
            "challenge": challenge_text,
            "status": "open"
        })

        tag['last_updated'] = datetime.now().isoformat()
        self.save()

        print(f"[OK] Added challenge to '{tag_name}'")
        print(f"Challenge: {challenge_text}")

        return True

    def show_status(self, tag_name: str):
        """Display detailed tag status"""
        if tag_name not in self.data['tags']:
            print(f"[ERROR] Tag '{tag_name}' not found")
            return

        tag = self.data['tags'][tag_name]

        print("=" * 60)
        print(f"Tag: {tag_name}")
        print("=" * 60)
        print(f"Category: {tag['category']}")
        print(f"Status: {tag['status']}")
        print(f"Hypothesis: {tag['hypothesis']}")
        print(f"\nCreated: {tag['created_date']}")
        print(f"Last updated: {tag['last_updated']}")

        # Evidence summary
        supporting = len(tag['evidence']['supporting'])
        counter = len(tag['evidence']['counter_examples'])
        tested = tag['evidence']['tested_instances']

        print(f"\nEvidence:")
        print(f"  Supporting: {supporting}")
        print(f"  Counter-examples: {counter}")
        print(f"  Tested instances: {tested}")

        if tag['evidence']['total_instances']:
            total = tag['evidence']['total_instances']
            pending = tag['evidence']['pending_review'] or (total - tested)
            progress = (tested / total * 100) if total > 0 else 0
            print(f"  Total instances: {total}")
            print(f"  Pending review: {pending}")
            print(f"  Progress: {progress:.1f}%")

        # Supporting evidence
        if supporting > 0:
            print(f"\nSupporting Evidence:")
            for i, ev in enumerate(tag['evidence']['supporting'][:5], 1):
                print(f"  {i}. {ev['verse']}: {ev['note']}")
            if supporting > 5:
                print(f"  ... and {supporting - 5} more")

        # Counter-examples
        if counter > 0:
            print(f"\nCounter-Examples:")
            for i, ev in enumerate(tag['evidence']['counter_examples'][:5], 1):
                resolution = ev.get('resolution', 'pending')
                print(f"  {i}. {ev['verse']}: {ev['note']} [{'resolution'}]")
            if counter > 5:
                print(f"  ... and {counter - 5} more")

        # Active challenges
        open_challenges = [c for c in tag['challenges'] if c['status'] == 'open']
        if open_challenges:
            print(f"\nActive Challenges:")
            for i, ch in enumerate(open_challenges, 1):
                print(f"  {i}. {ch['challenge']}")

        # Related hypotheses
        if tag['related_hypotheses']:
            print(f"\nRelated Hypotheses:")
            for related in tag['related_hypotheses']:
                print(f"  - {related}")

        print("=" * 60)

    def list_tags(self, filter_status: Optional[str] = None,
                  filter_category: Optional[str] = None):
        """List all tags with optional filters"""
        tags = self.data['tags']

        if not tags:
            print("No tags found.")
            return

        filtered = tags
        if filter_status:
            filtered = {k: v for k, v in filtered.items()
                       if v['status'] == filter_status}
        if filter_category:
            filtered = {k: v for k, v in filtered.items()
                       if v['category'] == filter_category}

        if not filtered:
            print(f"No tags found matching filters.")
            return

        print(f"\nTags ({len(filtered)}):")
        print("-" * 60)

        for tag_name, tag_data in sorted(filtered.items()):
            status = tag_data['status']
            category = tag_data['category']
            supporting = len(tag_data['evidence']['supporting'])
            counter = len(tag_data['evidence']['counter_examples'])

            print(f"{tag_name}")
            print(f"  Status: {status} | Category: {category}")
            print(f"  Evidence: {supporting} supporting, {counter} counter")
            print(f"  Hypothesis: {tag_data['hypothesis'][:60]}...")
            print()

    def show_statistics(self):
        """Display tag statistics"""
        stats = self.data['statistics']

        print("=" * 60)
        print("Tag Statistics")
        print("=" * 60)
        print(f"Total tags: {stats['total_tags']}")

        print(f"\nBy Status:")
        for status, count in stats['by_status'].items():
            if count > 0:
                desc = self.data['status_definitions'][status]
                print(f"  {status}: {count} - {desc}")

        print(f"\nBy Category:")
        for category, count in stats['by_category'].items():
            if count > 0:
                desc = self.data['taxonomy'][category]['description']
                print(f"  {category}: {count} - {desc}")

        print("=" * 60)

    def suggest_similar(self, tag_name: str, threshold: float = 0.6) -> List[str]:
        """Find similar tag names (catch typos)"""
        existing_tags = list(self.data['tags'].keys())
        similar = difflib.get_close_matches(tag_name, existing_tags, n=5, cutoff=threshold)
        return similar


def main():
    parser = argparse.ArgumentParser(
        description="Tag Manager - Hypothesis verification and tag lifecycle"
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Create tag
    create_parser = subparsers.add_parser('create', help='Create new hypothesis tag')
    create_parser.add_argument('tag_name', help='Tag name')
    create_parser.add_argument('--category', required=True, help='Tag category')
    create_parser.add_argument('--hypothesis', required=True, help='Hypothesis statement')
    create_parser.add_argument('--evidence', help='Initial evidence (verse reference)')

    # Add evidence
    evidence_parser = subparsers.add_parser('add-evidence', help='Add supporting evidence')
    evidence_parser.add_argument('tag_name', help='Tag name')
    evidence_parser.add_argument('--verse', required=True, help='Verse reference (e.g., 2:31)')
    evidence_parser.add_argument('--note', required=True, help='Evidence note')
    evidence_parser.add_argument('--counter', action='store_true', help='Mark as counter-example')

    # Promote status
    promote_parser = subparsers.add_parser('promote', help='Promote tag status')
    promote_parser.add_argument('tag_name', help='Tag name')
    promote_parser.add_argument('--to', required=True, dest='new_status', help='New status')
    promote_parser.add_argument('--note', default='', help='Note about promotion')

    # Add challenge
    challenge_parser = subparsers.add_parser('challenge', help='Add challenge to hypothesis')
    challenge_parser.add_argument('tag_name', help='Tag name')
    challenge_parser.add_argument('--question', required=True, help='Challenge question')

    # Show status
    status_parser = subparsers.add_parser('status', help='Show detailed tag status')
    status_parser.add_argument('tag_name', help='Tag name')

    # List tags
    list_parser = subparsers.add_parser('list', help='List all tags')
    list_parser.add_argument('--status', help='Filter by status')
    list_parser.add_argument('--category', help='Filter by category')

    # Statistics
    subparsers.add_parser('stats', help='Show tag statistics')

    # Suggest similar
    suggest_parser = subparsers.add_parser('suggest', help='Find similar tag names')
    suggest_parser.add_argument('tag_name', help='Tag name to check')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        tm = TagManager()

        if args.command == 'create':
            tm.create_tag(args.tag_name, args.category, args.hypothesis, args.evidence)

        elif args.command == 'add-evidence':
            tm.add_evidence(args.tag_name, args.verse, args.note, args.counter)

        elif args.command == 'promote':
            tm.promote_status(args.tag_name, args.new_status, args.note)

        elif args.command == 'challenge':
            tm.add_challenge(args.tag_name, args.question)

        elif args.command == 'status':
            tm.show_status(args.tag_name)

        elif args.command == 'list':
            tm.list_tags(args.status, args.category)

        elif args.command == 'stats':
            tm.show_statistics()

        elif args.command == 'suggest':
            similar = tm.suggest_similar(args.tag_name)
            if similar:
                print(f"Did you mean:")
                for tag in similar:
                    print(f"  - {tag}")
            else:
                print(f"No similar tags found for '{args.tag_name}'")

    except Exception as e:
        print(f"[ERROR] {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
