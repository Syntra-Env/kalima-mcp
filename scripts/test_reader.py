#!/usr/bin/env python3
"""
Test script for Quran Reader
Validates core functionality programmatically
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.quran_reader import QuranReader

def test_navigation():
    """Test navigation functions"""
    print("=" * 60)
    print("TEST 1: Navigation")
    print("=" * 60)

    reader = QuranReader()

    # Test goto
    print("\n1. Testing goto(2, 31)...")
    success = reader.goto(2, 31)
    verse = reader.get_current_verse()
    assert success, "goto(2, 31) failed"
    assert verse['surah']['number'] == 2, "Surah number incorrect"
    assert verse['ayah'] == 31, "Ayah number incorrect"
    print(f"   [OK] Navigated to {verse['surah']['number']}:{verse['ayah']}")
    print(f"   Arabic: {verse['text'][:50]}...")

    # Test next
    print("\n2. Testing next_verse()...")
    reader.next_verse()
    verse = reader.get_current_verse()
    assert verse['ayah'] == 32, "next_verse() failed"
    print(f"   [OK] Moved to ayah {verse['ayah']}")

    # Test prev
    print("\n3. Testing prev_verse()...")
    reader.prev_verse()
    verse = reader.get_current_verse()
    assert verse['ayah'] == 31, "prev_verse() failed"
    print(f"   [OK] Moved back to ayah {verse['ayah']}")

    print("\n[SUCCESS] All navigation tests passed!")
    return reader

def test_token_display(reader):
    """Test token and morphology display"""
    print("\n" + "=" * 60)
    print("TEST 2: Token Display")
    print("=" * 60)

    # Navigate to verse with tokens
    reader.goto(1, 1)
    verse = reader.get_current_verse()

    print("\n1. Checking tokens exist...")
    assert 'tokens' in verse, "No tokens in verse"
    assert len(verse['tokens']) > 0, "Tokens array is empty"
    print(f"   [OK] Found {len(verse['tokens'])} tokens")

    print("\n2. Checking token structure...")
    token = verse['tokens'][0]
    assert 'id' in token, "Token missing 'id'"
    assert 'form' in token, "Token missing 'form'"
    assert 'segments' in token, "Token missing 'segments'"
    print(f"   [OK] Token structure valid")
    print(f"   Token 1: {token['form']}")

    print("\n3. Checking morpheme segments...")
    assert len(token['segments']) > 0, "No segments in token"
    segment = token['segments'][0]
    assert 'id' in segment, "Segment missing 'id'"
    assert 'form' in segment, "Segment missing 'form'"
    assert 'type' in segment, "Segment missing 'type'"
    assert 'pos' in segment, "Segment missing 'pos'"
    print(f"   [OK] Segment structure valid")
    print(f"   Segment: {segment['id']} - {segment['form']} [{segment['type']}] {segment['pos']}")

    if segment.get('root'):
        print(f"   Root: {segment['root']}")

    print("\n[SUCCESS] All token display tests passed!")
    return reader

def test_annotation_creation(reader):
    """Test annotation creation"""
    print("\n" + "=" * 60)
    print("TEST 3: Annotation Creation")
    print("=" * 60)

    # Navigate to test verse
    reader.goto(2, 31)
    verse_before = reader.get_current_verse()
    annotations_before = len(verse_before.get('annotations', []))

    print(f"\n1. Creating annotation on verse 2:31...")
    print(f"   Annotations before: {annotations_before}")

    # Create annotation
    success = reader.create_annotation(
        token_spec="1-3",
        ann_type="morphological",
        note="Test annotation: root ع-ل-م pattern فَعَّلَ indicates teaching through demonstration",
        tags=["root-علم", "pattern-فعل"],
        link_to_hypothesis=None
    )

    assert success, "Annotation creation failed"

    # Check it was added
    verse_after = reader.get_current_verse()
    annotations_after = len(verse_after.get('annotations', []))

    assert annotations_after == annotations_before + 1, "Annotation count didn't increase"
    print(f"   Annotations after: {annotations_after}")
    print(f"   [OK] Annotation created successfully")

    # Check annotation structure
    annotation = verse_after['annotations'][-1]
    print(f"\n2. Validating annotation structure...")
    assert 'id' in annotation, "Annotation missing 'id'"
    assert 'type' in annotation, "Annotation missing 'type'"
    assert 'note' in annotation, "Annotation missing 'note'"
    assert 'tags' in annotation, "Annotation missing 'tags'"
    assert 'status' in annotation, "Annotation missing 'status'"
    print(f"   [OK] Structure valid")
    print(f"   ID: {annotation['id']}")
    print(f"   Type: {annotation['type']}")
    print(f"   Status: {annotation['status']}")
    print(f"   Tags: {', '.join(annotation['tags'])}")

    print("\n[SUCCESS] All annotation creation tests passed!")
    return reader

def test_tag_linking(reader):
    """Test tag linking and auto-evidence"""
    print("\n" + "=" * 60)
    print("TEST 4: Tag Linking & Auto-Evidence")
    print("=" * 60)

    # Check if tags exist
    if not reader.tags or 'tags' not in reader.tags or not reader.tags['tags']:
        print("\n[SKIP] No hypothesis tags available for linking test")
        print("       This is expected if tags.json is empty")
        return reader

    # Get first available tag
    tag_name = list(reader.tags['tags'].keys())[0]
    tag_before = reader.tags['tags'][tag_name].copy()
    evidence_before = len(tag_before['evidence']['supporting'])

    print(f"\n1. Testing tag linking with '{tag_name}'...")
    print(f"   Evidence before: {evidence_before}")

    # Navigate to a different verse
    reader.goto(3, 1)

    # Create annotation with tag link
    success = reader.create_annotation(
        token_spec="1",
        ann_type="morphological",
        note="Test evidence for hypothesis verification",
        tags=["test"],
        link_to_hypothesis=tag_name
    )

    assert success, "Annotation with tag link failed"

    # Check evidence was added
    tag_after = reader.tags['tags'][tag_name]
    evidence_after = len(tag_after['evidence']['supporting'])

    assert evidence_after == evidence_before + 1, "Evidence wasn't added to tag"
    print(f"   Evidence after: {evidence_after}")
    print(f"   [OK] Evidence linked successfully")

    # Check for auto-promotion
    if tag_after['status'] != tag_before['status']:
        print(f"\n2. Auto-promotion detected!")
        print(f"   Status changed: {tag_before['status']} -> {tag_after['status']}")
    else:
        print(f"\n2. Status: {tag_after['status']} (no auto-promotion)")

    print("\n[SUCCESS] All tag linking tests passed!")
    return reader

def main():
    print("\n" + "=" * 60)
    print("CODEX Quran Reader - Automated Test Suite")
    print("=" * 60)

    try:
        # Run tests
        reader = test_navigation()
        reader = test_token_display(reader)
        reader = test_annotation_creation(reader)
        reader = test_tag_linking(reader)

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        print("\nThe Quran Reader is fully functional:")
        print("  ✓ Navigation (goto, next, prev)")
        print("  ✓ Token display with morphology")
        print("  ✓ Annotation creation")
        print("  ✓ Tag linking with auto-evidence")
        print("\nReady for interactive use: python scripts/quran_reader.py")
        print("=" * 60)

        return 0

    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit(main())
