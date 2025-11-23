#!/usr/bin/env python3
"""
Codex - Quran Research Web Interface
Flask backend with RESTful API
"""

from flask import Flask, render_template, jsonify, request
import json
import os
import re
import csv
from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict
from pathlib import Path
import unicodedata

app = Flask(__name__, static_folder='static', static_url_path='')
app.config['JSON_AS_ASCII'] = False  # Enable Unicode in JSON responses

# Paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CORPUS_PATH = os.path.join(PROJECT_ROOT, 'datasets', 'corpus', 'quran.jsonl')
DEFAULT_TAGS_PATH = os.path.join(PROJECT_ROOT, 'datasets', 'corpus', 'tags.json')
CORPUS_PATH = os.getenv('CORPUS_PATH', DEFAULT_CORPUS_PATH)
TAGS_PATH = os.getenv('TAGS_PATH', DEFAULT_TAGS_PATH)
DATA_PATH = os.getenv('DATA_PATH', os.path.join(PROJECT_ROOT, 'datasets', 'resources'))
NOTES_PATH = os.path.join(PROJECT_ROOT, 'notes')
MASAQ_PATH = os.path.join(PROJECT_ROOT, 'datasets', 'masaq')
MORPHOLOGY_PATH = os.path.join(PROJECT_ROOT, 'datasets', 'morphology')
READ_ONLY_MODE = os.getenv('CODEX_READ_ONLY', '').lower() in ('1', 'true', 'yes')


class CorpusManager:
    """Manage corpus data and operations"""

    def __init__(self):
        self.verses = self.load_corpus()
        self.tags = self.load_tags()
        self.masaq_data = self.load_masaq_data()
        self.surah_index = self.build_surah_index()
        self.root_index = {}
        self.root_list = []
        self.morph_pattern_index = {}
        self.morph_patterns = []
        self.syntax_pattern_index = {}
        self.syntax_patterns = []
        self.build_linguistic_indexes()

    def build_surah_index(self) -> Dict[int, List[Dict]]:
        """Index verses by surah number for quick lookup"""
        index: Dict[int, List[Dict]] = defaultdict(list)
        self.verse_lookup = {}
        for verse in self.verses:
            surah_num = verse['surah']['number']
            index[surah_num].append(verse)
            self.verse_lookup[(surah_num, verse['ayah'])] = verse
        return dict(index)

    def load_corpus(self) -> List[Dict]:
        """Load all verses from corpus"""
        verses = []
        with open(CORPUS_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    verses.append(json.loads(line))
        return verses

    def load_tags(self) -> Dict:
        """Load tag registry"""
        if os.path.exists(TAGS_PATH):
            with open(TAGS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def load_masaq_data(self) -> Dict:
        """Load MASAQ morphological dataset indexed by surah:ayah:word"""
        masaq_csv = os.path.join(MASAQ_PATH, 'MASAQ.csv')
        if not os.path.exists(masaq_csv):
            print(f"Warning: MASAQ dataset not found at {masaq_csv}")
            return {}

        masaq_index = defaultdict(list)

        try:
            with open(masaq_csv, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    surah = int(row['Sura_No'])
                    ayah = int(row['Verse_No'])
                    key = (surah, ayah)
                    masaq_index[key].append(row)

            print(f"Loaded MASAQ data: {len(masaq_index)} verses with detailed morphology")
            return dict(masaq_index)
        except Exception as e:
            print(f"Error loading MASAQ data: {e}")
            return {}

    def save_corpus(self):
        """Save corpus (versioned by git)"""
        if READ_ONLY_MODE:
            return

        with open(CORPUS_PATH, 'w', encoding='utf-8') as f:
            for verse in self.verses:
                f.write(json.dumps(verse, ensure_ascii=False) + '\n')

    def save_tags(self):
        """Save tag registry"""
        if READ_ONLY_MODE:
            return
        self.tags['last_updated'] = datetime.now().isoformat()
        with open(TAGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.tags, f, ensure_ascii=False, indent=2)

    def get_verse(self, surah: int, ayah: int) -> Optional[Dict]:
        """Get specific verse"""
        for verse in self.verses:
            if verse['surah']['number'] == surah and verse['ayah'] == ayah:
                return verse
        return None

    def get_verse_by_index(self, index: int) -> Optional[Dict]:
        """Get verse by index (0-based)"""
        if 0 <= index < len(self.verses):
            return self.verses[index]
        return None

    def get_surah(self, surah_number: int) -> List[Dict]:
        """Return all verses for a surah"""
        return self.surah_index.get(surah_number, [])

    def get_surah_summary(self) -> List[Dict]:
        """Return metadata for available surahs"""
        summary = []
        for number in sorted(self.surah_index.keys()):
            verses = self.surah_index[number]
            name = verses[0]['surah']['name'] if verses else ''
            summary.append({
                'number': number,
                'name': name,
                'ayah_count': len(verses)
            })
        return summary

    def build_linguistic_indexes(self):
        """Precompute roots, morphological patterns, and syntactic patterns"""
        root_map: Dict[str, set] = defaultdict(set)
        morph_meta: Dict[str, Dict] = {}
        syntax_meta: Dict[str, Dict] = {}

        for verse in self.verses:
            surah_num = verse['surah']['number']
            ayah_num = verse['ayah']
            verse_key = (surah_num, ayah_num)

            tokens = verse.get('tokens', [])
            for token in tokens:
                segments = token.get('segments', [])
                for segment in segments:
                    root = (segment.get('root') or '').strip()
                    if root:
                        root_map[root].add(verse_key)

                    pattern_key = self._make_morph_pattern_key(segment)
                    if pattern_key:
                        meta = morph_meta.setdefault(pattern_key, {
                            'label': self._format_morph_pattern_label(segment),
                            'verses': set()
                        })
                        meta['verses'].add(verse_key)

            pos_sequence = self._extract_pos_sequence(tokens)
            if pos_sequence:
                max_len = min(3, len(pos_sequence))
                for length in range(2, max_len + 1):
                    for start in range(len(pos_sequence) - length + 1):
                        seq = pos_sequence[start:start + length]
                        key = '|'.join(seq)
                        meta = syntax_meta.setdefault(key, {
                            'label': ' → '.join(part.upper() for part in seq),
                            'verses': set()
                        })
                        meta['verses'].add(verse_key)

        self.root_index = root_map
        self.root_list = sorted(root_map.keys())

        self.morph_pattern_index = morph_meta
        self.morph_patterns = sorted(
            [
                {
                    'id': key,
                    'label': meta['label'],
                    'count': len(meta['verses'])
                }
                for key, meta in morph_meta.items()
            ],
            key=lambda item: item['label']
        )

        self.syntax_pattern_index = syntax_meta
        self.syntax_patterns = sorted(
            [
                {
                    'id': key,
                    'label': meta['label'],
                    'count': len(meta['verses'])
                }
                for key, meta in syntax_meta.items()
            ],
            key=lambda item: item['label']
        )

    def _extract_pos_sequence(self, tokens: List[Dict]) -> List[str]:
        sequence = []
        for token in tokens:
            pos = ''
            if token.get('segments'):
                pos = token['segments'][0].get('pos') or ''
            elif token.get('pos'):
                pos = token['pos']
            if pos:
                sequence.append(pos.lower())
        return sequence

    def _make_morph_pattern_key(self, segment: Dict) -> Optional[str]:
        if not segment:
            return None
        type_ = (segment.get('type') or '').lower()
        pos = (segment.get('pos') or '').lower()
        lemma = (segment.get('lemma') or '').lower()
        features = (segment.get('features') or '').lower()
        if not (type_ or pos or lemma or features):
            return None
        return '|'.join([type_, pos, lemma, features])

    def _format_morph_pattern_label(self, segment: Dict) -> str:
        if not segment:
            return 'Morph Pattern'
        parts = []
        type_ = segment.get('type')
        pos = segment.get('pos')
        lemma = segment.get('lemma')
        features = segment.get('features')
        if type_:
            parts.append(type_.upper())
        if pos:
            parts.append(pos)
        if lemma:
            parts.append(lemma)
        if features:
            parts.append(features)
        return ' • '.join(parts) or 'Morph Pattern'

    def parse_morphological_features(self, segment: Dict) -> Dict:
        """
        Parse morphological features from segment into structured data.
        Extracts: verb form, person, number, gender, voice, mood, case, tense, aspect
        """
        features_str = segment.get('features', '')
        pos = segment.get('pos', '')

        parsed = {
            'pos': pos,
            'pos_full': self._get_pos_full_name(pos),
            'root': segment.get('root'),
            'lemma': segment.get('lemma'),
            'type': segment.get('type'),
            'verb_form': None,
            'person': None,
            'number': None,
            'gender': None,
            'voice': None,
            'mood': None,
            'case': None,
            'tense': None,
            'aspect': None,
            'features_raw': features_str
        }

        if not features_str:
            return parsed

        # Parse features string
        features_upper = features_str.upper()

        # Verb Form (I-X) - extract from parentheses like (IV), (III), (X)
        import re
        verb_form_match = re.search(r'\((I{1,3}V?|VI{0,3}|I?X)\)', features_str)
        if verb_form_match:
            form_num = verb_form_match.group(1)
            roman_to_arabic = {
                'I': 'I', 'II': 'II', 'III': 'III', 'IV': 'IV', 'V': 'V',
                'VI': 'VI', 'VII': 'VII', 'VIII': 'VIII', 'IX': 'IX', 'X': 'X'
            }
            parsed['verb_form'] = f"Form {roman_to_arabic.get(form_num, form_num)}"

        # Person (1P, 2P, 3P, etc.)
        if '1P' in features_str or '1S' in features_str or '1D' in features_str:
            parsed['person'] = '1st'
        elif '2P' in features_str or '2MS' in features_str or '2FS' in features_str or '2MD' in features_str or '2FD' in features_str or '2MP' in features_str or '2FP' in features_str:
            parsed['person'] = '2nd'
        elif '3P' in features_str or '3MS' in features_str or '3FS' in features_str or '3MD' in features_str or '3FD' in features_str or '3MP' in features_str or '3FP' in features_str:
            parsed['person'] = '3rd'

        # Number (singular, dual, plural)
        if 'S|' in features_str or features_str.endswith('S') or 'MS' in features_str or 'FS' in features_str:
            parsed['number'] = 'singular'
        elif 'D|' in features_str or features_str.endswith('D') or 'MD' in features_str or 'FD' in features_str:
            parsed['number'] = 'dual'
        elif 'P|' in features_str or features_str.endswith('P') or 'MP' in features_str or 'FP' in features_str:
            parsed['number'] = 'plural'

        # Gender (M/F)
        if '|M|' in features_str or '|M' in features_str or 'MS' in features_str or 'MD' in features_str or 'MP' in features_str:
            parsed['gender'] = 'masculine'
        elif '|F|' in features_str or '|F' in features_str or 'FS' in features_str or 'FD' in features_str or 'FP' in features_str:
            parsed['gender'] = 'feminine'

        # Voice (ACT/PASS)
        if 'ACT' in features_upper or 'ACTIVE' in features_upper:
            parsed['voice'] = 'active'
        elif 'PASS' in features_upper or 'PASSIVE' in features_upper:
            parsed['voice'] = 'passive'

        # Mood (IND/SUBJ/JUS)
        if 'MOOD:IND' in features_str:
            parsed['mood'] = 'indicative'
        elif 'MOOD:SJ' in features_str or 'SUBJ' in features_upper:
            parsed['mood'] = 'subjunctive'
        elif 'MOOD:JUS' in features_str or 'JUS' in features_upper:
            parsed['mood'] = 'jussive'

        # Case (NOM/ACC/GEN)
        if 'NOM' in features_upper:
            parsed['case'] = 'nominative'
        elif 'ACC' in features_upper:
            parsed['case'] = 'accusative'
        elif 'GEN' in features_upper:
            parsed['case'] = 'genitive'

        # Tense/Aspect
        if 'PERF' in features_upper:
            parsed['tense'] = 'perfect'
            parsed['aspect'] = 'perfective'
        elif 'IMPF' in features_upper:
            parsed['tense'] = 'imperfect'
            parsed['aspect'] = 'imperfective'
        elif 'IMPV' in features_upper:
            parsed['tense'] = 'imperative'

        return parsed

    def _get_pos_full_name(self, pos: str) -> str:
        """Convert POS code to full name"""
        pos_map = {
            'N': 'Noun',
            'PN': 'Proper Noun',
            'ADJ': 'Adjective',
            'V': 'Verb',
            'P': 'Preposition',
            'PRON': 'Pronoun',
            'DET': 'Determiner',
            'REL': 'Relative Pronoun',
            'T': 'Particle',
            'NEG': 'Negative Particle',
            'CONJ': 'Conjunction',
            'INTERROG': 'Interrogative',
            'VOC': 'Vocative Particle',
            'SUB': 'Subordinating Conjunction',
            'EMPH': 'Emphatic Particle',
            'IMPV': 'Imperative Particle',
            'ACC': 'Accusative Particle',
            'AMD': 'Amendment Particle',
            'ANS': 'Answer Particle',
            'AVR': 'Aversion Particle',
            'CAUS': 'Causative Particle',
            'CERT': 'Certainty Particle',
            'CIRC': 'Circumstantial Particle',
            'COM': 'Comitative Particle',
            'COND': 'Conditional Particle',
            'EQ': 'Equalization Particle',
            'EXH': 'Exhortation Particle',
            'EXL': 'Explanation Particle',
            'EXP': 'Exceptive Particle',
            'FUT': 'Future Particle',
            'INC': 'Inceptive Particle',
            'INT': 'Intensification Particle',
            'INTG': 'Interrogative Particle',
            'PRO': 'Prohibition Particle',
            'REM': 'Resumption Particle',
            'RES': 'Restriction Particle',
            'RET': 'Retraction Particle',
            'RSLT': 'Result Particle',
            'SUP': 'Supplemental Particle',
            'SUR': 'Surprise Particle'
        }
        return pos_map.get(pos, pos)

    def _build_pronoun_id(self, token_id, segment_id=None) -> str:
        """Create stable identifier for pronoun-bearing segment/token"""
        if segment_id:
            return f"{token_id}:{segment_id}"
        return str(token_id)

    def detect_pronouns(self, verse: Dict) -> List[Dict]:
        """Return pronoun segments/tokens present in a verse"""
        if not verse:
            return []

        pronouns: List[Dict] = []
        tokens = verse.get('tokens', [])
        for token in tokens:
            token_id = token.get('id')
            token_form = token.get('form') or ''
            token_pos = (token.get('pos') or '').lower()

            # Whole-token pronouns
            if token_pos == 'pron':
                pronouns.append({
                    'pronoun_id': self._build_pronoun_id(token_id),
                    'token_id': token_id,
                    'segment_id': None,
                    'form': token_form,
                    'pos': token.get('pos'),
                    'features': token.get('features', ''),
                    'token_form': token_form,
                    'segment_type': None
                })

            # Pronoun morphemes (suffixes/clitics/segments)
            for seg in token.get('segments', []):
                pos = (seg.get('pos') or '').lower()
                features = (seg.get('features') or '').lower()
                is_pronoun = pos == 'pron' or 'pron' in features
                if not is_pronoun:
                    continue

                pronouns.append({
                    'pronoun_id': self._build_pronoun_id(token_id, seg.get('id')),
                    'token_id': token_id,
                    'segment_id': seg.get('id'),
                    'form': seg.get('form') or token_form,
                    'pos': seg.get('pos'),
                    'features': seg.get('features', ''),
                    'token_form': token_form,
                    'segment_type': seg.get('type')
                })

        return pronouns

    def get_pronoun_references(self, surah: int, ayah: int) -> Optional[Dict]:
        """Return pronoun candidates with user supplied referents for a verse"""
        verse = self.get_verse(surah, ayah)
        if not verse:
            return None

        pronouns = self.detect_pronouns(verse)
        pronoun_lookup = {p['pronoun_id']: p for p in pronouns}
        references = []

        for ref in verse.get('pronoun_references', []):
            ref_copy = dict(ref)
            evidence = ref_copy.get('evidence', [])
            supporting = sum(1 for e in evidence if (e.get('type') or '').lower() == 'supporting')
            counter = sum(1 for e in evidence if (e.get('type') or '').lower() == 'counter')
            ref_copy['evidence_summary'] = {
                'supporting': supporting,
                'counter': counter,
                'total': len(evidence)
            }
            if ref_copy.get('pronoun_id') and ref_copy['pronoun_id'] in pronoun_lookup:
                ref_copy['pronoun_form'] = ref_copy.get('pronoun_form') or pronoun_lookup[ref_copy['pronoun_id']].get('form')
            references.append(ref_copy)

        stats = {
            'total_pronouns': len(pronouns),
            'annotated_pronouns': len(references),
            'supporting_evidence': sum(r['evidence_summary']['supporting'] for r in references) if references else 0,
            'counter_evidence': sum(r['evidence_summary']['counter'] for r in references) if references else 0
        }

        return {
            'verse': {
                'surah': surah,
                'ayah': ayah,
                'text': verse.get('text')
            },
            'pronouns': pronouns,
            'references': references,
            'structure_hypotheses': [h for h in verse.get('structure_hypotheses', []) if h.get('target_type') == 'pronoun'],
            'stats': stats
        }

    def search_text(self, query: str, limit: int = 100) -> List[Dict]:
        """Search verses by text content"""
        results = []
        query_lower = query.lower()

        for i, verse in enumerate(self.verses):
            if query_lower in verse['text'].lower():
                results.append({
                    'index': i,
                    'verse': verse
                })
                if len(results) >= limit:
                    break

        return results

    def search_by_root(self, root: str, limit: int = 100) -> List[Dict]:
        """Search verses containing words with specific root"""
        results = []

        for i, verse in enumerate(self.verses):
            if not verse.get('tokens'):
                continue

            # Check if any token has this root
            has_root = False
            for token in verse['tokens']:
                if token.get('segments'):
                    for seg in token['segments']:
                        if seg.get('root') == root:
                            has_root = True
                            break
                if has_root:
                    break

            if has_root:
                results.append({
                    'index': i,
                    'verse': verse
                })
                if len(results) >= limit:
                    break

        return results

    def get_root_list(self) -> List[str]:
        return self.root_list

    def get_morph_patterns(self) -> List[Dict]:
        return self.morph_patterns

    def get_syntax_patterns(self) -> List[Dict]:
        return self.syntax_patterns

    def search_root(self, root: str, limit: int = 200) -> List[Dict]:
        root = (root or '').strip()
        if not root or root not in self.root_index:
            return []
        references = sorted(self.root_index[root])

        results = []
        for surah_num, ayah_num in references[:limit]:
            verse = self.verse_lookup.get((surah_num, ayah_num))
            if not verse:
                continue

            match_form = None
            for token in verse.get('tokens', []):
                for seg in token.get('segments', []):
                    if seg.get('root') == root:
                        match_form = token.get('form')
                        break
                if match_form:
                    break

            entry = {'verse': verse, 'match': f"Root: {root}"}
            if match_form:
                entry['match_term'] = match_form
            results.append(entry)

        return {'results': results, 'total_count': len(references)}

    def search_morph_pattern(self, pattern_id: str, limit: int = 100) -> List[Dict]:
        if not pattern_id or pattern_id not in self.morph_pattern_index:
            return []
        meta = self.morph_pattern_index[pattern_id]
        references = sorted(meta['verses'])
        return self._build_search_results(references, meta['label'], limit)

    def search_syntax_pattern(self, pattern_id: str, limit: int = 100) -> List[Dict]:
        if not pattern_id or pattern_id not in self.syntax_pattern_index:
            return []
        meta = self.syntax_pattern_index[pattern_id]
        references = sorted(meta['verses'])
        return self._build_search_results(references, meta['label'], limit)

    def _build_search_results(self, references: List, match_label: str, limit: int) -> List[Dict]:
        results = []
        for surah_num, ayah_num in references[:limit]:
            verse = self.verse_lookup.get((surah_num, ayah_num))
            if verse:
                entry = {'verse': verse}
                if match_label:
                    entry['match'] = match_label
                results.append(entry)
        return results

    def search_morphology(self, query: str, limit: int = 100) -> List[Dict]:
        """Search for morphological segments matching query"""
        q = query.strip().lower()
        if not q:
            return []

        results = []
        total_count = 0
        for i, verse in enumerate(self.verses):
            if not verse.get('tokens'):
                continue

            found = False
            for token in verse['tokens']:
                for segment in token.get('segments', []):
                    fields = [
                        segment.get('type', ''),
                        segment.get('pos', ''),
                        segment.get('root', ''),
                        segment.get('lemma', ''),
                        segment.get('features', '')
                    ]
                    if any(q in str(field).lower() for field in fields if field):
                        total_count += 1
                        if len(results) < limit:
                            match_desc = f"{segment.get('type', '').upper()} • {segment.get('pos', '')} • {segment.get('lemma', '') or ''}"
                            entry = {
                                'index': i,
                                'verse': verse,
                                'match': match_desc.strip()
                            }
                            token_form = token.get('form')
                            if token_form:
                                entry['match_term'] = token_form
                            results.append(entry)
                        found = True
                        break
                if found:
                    break
        return {'results': results, 'total_count': total_count}

    def search_syntax(self, pattern: str, limit: int = 100) -> List[Dict]:
        """Search for syntactic POS sequences"""
        tokens = [p.strip().lower() for p in re.split(r'[\s,>+-]+', pattern) if p.strip()]
        if not tokens:
            return []

        results = []
        total_count = 0
        length = len(tokens)

        for i, verse in enumerate(self.verses):
            if not verse.get('tokens'):
                continue

            pos_sequence = []
            for token in verse['tokens']:
                pos = None
                if token.get('segments'):
                    pos = token['segments'][0].get('pos')
                pos_sequence.append((pos or '').lower())

            if len(pos_sequence) < length:
                continue

            for start in range(len(pos_sequence) - length + 1):
                window = pos_sequence[start:start + length]
                if window == tokens:
                    total_count += 1
                    if len(results) < limit:
                        match_desc = "POS pattern: " + ' '.join(p.upper() for p in window)
                        entry = {
                            'index': i,
                            'verse': verse,
                            'match': match_desc
                        }
                        window_forms = [t.get('form') for t in verse['tokens'][start:start + length] if t.get('form')]
                        if window_forms:
                            entry['match_term'] = ' '.join(window_forms)
                        results.append(entry)
                    break

        return {'results': results, 'total_count': total_count}

    def get_masaq_morphology(self, surah: int, ayah: int) -> Optional[List[Dict]]:
        """Get MASAQ morphological data for a specific verse"""
        return self.masaq_data.get((surah, ayah))

    def search_masaq_morphology(self, morph_tag: str = None, syntactic_role: str = None,
                                case_mood: str = None, limit: int = 100) -> List[Dict]:
        """
        Search verses using MASAQ morphological features.
        Can filter by: morph_tag (VERB, NOUN, etc.), syntactic_role, case_mood, etc.
        """
        results = []
        total_count = 0

        for (surah, ayah), masaq_words in self.masaq_data.items():
            verse_matches = []

            for word_data in masaq_words:
                matches = True

                if morph_tag and word_data.get('Morph_tag') != morph_tag:
                    matches = False
                if syntactic_role and word_data.get('Syntactic_Role') != syntactic_role:
                    matches = False
                if case_mood and word_data.get('Case_Mood') != case_mood:
                    matches = False

                if matches:
                    verse_matches.append(word_data)
                    total_count += 1

            if verse_matches and len(results) < limit:
                verse = self.get_verse(surah, ayah)
                if verse:
                    # Build match description
                    match_parts = []
                    if morph_tag:
                        match_parts.append(f"Type: {morph_tag}")
                    if syntactic_role:
                        match_parts.append(f"Role: {syntactic_role}")
                    if case_mood:
                        match_parts.append(f"Case: {case_mood}")
                    match_desc = ', '.join(match_parts) if match_parts else 'MASAQ morphology match'

                    results.append({
                        'verse': verse,
                        'match': match_desc,
                        'masaq_matches': verse_matches[:5],  # Show first 5 matches
                        'match_count': len(verse_matches)
                    })

        return {'results': results, 'total_count': total_count}

    def search_library(self, query: str, limit: int = 30) -> List[Dict]:
        """Search text-based resources under data/ for supporting references"""
        q = (query or '').strip()
        if not q or not os.path.exists(DATA_PATH):
            return []

        q_lower = q.lower()
        results: List[Dict] = []
        allowed_ext = {'.txt', '.md'}
        data_root = Path(DATA_PATH)

        for file_path in data_root.rglob('*'):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in allowed_ext:
                continue

            try:
                with file_path.open('r', encoding='utf-8') as f:
                    for lineno, line in enumerate(f, 1):
                        if q_lower in line.lower():
                            results.append({
                                'path': str(file_path.relative_to(data_root)),
                                'line': lineno,
                                'snippet': line.strip()
                            })
                            if len(results) >= limit:
                                return results
            except UnicodeDecodeError:
                # Skip binary/unknown encoding files
                continue

        return results

    def search_pattern_word(self, pattern_spec: Dict, limit: int = 50) -> List[Dict]:
        """
        Search verses whose text matches a diacritic-aware pattern built from segments.
        pattern_spec = {
            'segments': [{'letter': 'ب', 'diacritics': ['\u064e'], 'any_letter': False, 'any_diacritics': False}, ...],
            'allow_prefix': True/False,
            'allow_suffix': True/False
        }
        """
        segments = pattern_spec.get('segments') if isinstance(pattern_spec, dict) else None
        if not segments:
            return []
        allow_prefix = bool(pattern_spec.get('allow_prefix'))
        allow_suffix = bool(pattern_spec.get('allow_suffix'))

        regex = self._pattern_segments_to_regex(segments, allow_prefix, allow_suffix)
        if not regex:
            return []

        results: List[Dict] = []
        total_matches = 0
        compiled = re.compile(regex)

        for verse in self.verses:
            text = verse.get('text') or ''
            matches = list(compiled.finditer(text))
            if matches:
                total_matches += len(matches)
                if len(results) < limit:
                    results.append({
                        'verse': verse,
                        'match': 'Pattern match',
                        'match_regex': regex,
                        'match_count': len(matches)
                    })
        return {'results': results, 'total_count': total_matches}

    def _pattern_segments_to_regex(self, segments: List[Dict], allow_prefix: bool, allow_suffix: bool) -> Optional[str]:
        # Include extended alef/hamza forms
        arabic_letters = r'[\u0621-\u064A\u0671-\u0673\u0675]'
        diacritic_class = r'[\u064B-\u0652\u0670\u0653-\u0655]'
        tatweel = r'\u0640*'  # allow optional elongation marks inside words
        parts = []
        for seg in segments:
            letter = seg.get('letter')
            any_letter = seg.get('any_letter') or not letter
            diacritics = seg.get('diacritics') if seg.get('diacritics') is not None else []
            any_diacritics = seg.get('any_diacritics')

            letter_part = arabic_letters if any_letter else re.escape(letter)
            if any_diacritics:
                diac_part = f'{diacritic_class}*'
            else:
                specific = ''.join(re.escape(d) for d in diacritics if d)
                # Allow any extra combining marks even when specific ones are provided
                diac_part = f'{specific}{diacritic_class}*'
            parts.append(f'{letter_part}{diac_part}{tatweel}')

        body = ''.join(parts)
        left = '' if allow_prefix else r'(?<!\S)'
        right = '' if allow_suffix else r'(?!\S)'

        try:
            return f'{left}{body}{right}'
        except re.error:
            return None

    def _normalize_evidence_entry(self, evidence: Dict) -> Dict:
        """Ensure evidence entries have consistent fields"""
        evidence_type = (evidence.get('type') or 'supporting').lower()
        note = (evidence.get('note') or '').strip()
        verse_ref = (evidence.get('verse') or '').strip()
        return {
            'id': evidence.get('id') or datetime.now().strftime("ev-%Y%m%d-%H%M%S"),
            'type': evidence_type,
            'note': note,
            'verse': verse_ref or None,
            'created_at': datetime.now().isoformat()
        }

    def _normalize_hypothesis_entry(self, verse: Dict, data: Dict) -> Dict:
        """Create a unified hypothesis record for any target type"""
        target_type = data.get('target_type') or data.get('type') or 'unknown'
        target_id = data.get('target_id') or data.get('pronoun_id')
        evidence_list = []
        if data.get('evidence'):
            evidence_list = [self._normalize_evidence_entry(ev) for ev in data.get('evidence', [])]
        elif data.get('evidence_note'):
            evidence_list = [self._normalize_evidence_entry({
                'type': data.get('evidence_type') or 'supporting',
                'note': data.get('evidence_note'),
                'verse': data.get('evidence_verse')
            })]

        return {
            'id': data.get('id') or datetime.now().strftime("hyp-%Y%m%d-%H%M%S"),
            'target_type': target_type,
            'target_id': target_id,
            'target_meta': data.get('target_meta') or {},
            'hypothesis': data.get('hypothesis') or data.get('referent'),
            'status': data.get('status') or 'hypothesis',
            'note': data.get('note') or '',
            'evidence': evidence_list,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

    def add_structure_hypothesis(self, surah: int, ayah: int, hyp_data: Dict) -> Optional[Dict]:
        """Add unified hypothesis entry for any structure target"""
        verse = self.get_verse(surah, ayah)
        if not verse:
            return None
        entry = self._normalize_hypothesis_entry(verse, hyp_data)
        verse.setdefault('structure_hypotheses', []).append(entry)
        self.save_corpus()
        return entry

    def update_structure_hypothesis(self, surah: int, ayah: int, hyp_id: str, updates: Dict) -> Optional[Dict]:
        verse = self.get_verse(surah, ayah)
        if not verse:
            return None
        for hyp in verse.get('structure_hypotheses', []):
            if hyp.get('id') == hyp_id:
                for field in ['hypothesis', 'status', 'note', 'target_meta']:
                    if field in updates and updates[field] is not None:
                        hyp[field] = updates[field]
                if updates.get('evidence_entry'):
                    ev = self._normalize_evidence_entry(updates['evidence_entry'])
                    hyp.setdefault('evidence', []).append(ev)
                hyp['updated_at'] = datetime.now().isoformat()
                self.save_corpus()
                return hyp
        return None

    def delete_structure_hypothesis(self, surah: int, ayah: int, hyp_id: str) -> bool:
        verse = self.get_verse(surah, ayah)
        if not verse:
            return False
        before = len(verse.get('structure_hypotheses', []))
        verse['structure_hypotheses'] = [h for h in verse.get('structure_hypotheses', []) if h.get('id') != hyp_id]
        after = len(verse.get('structure_hypotheses', []))
        if after < before:
            self.save_corpus()
            return True
        return False

    def add_pronoun_reference(self, surah: int, ayah: int, ref_data: Dict) -> Optional[Dict]:
        """Store a referent hypothesis for a pronoun"""
        verse = self.get_verse(surah, ayah)
        if not verse:
            return None

        pronouns = {p['pronoun_id']: p for p in self.detect_pronouns(verse)}
        target_id = ref_data.get('pronoun_id')
        pronoun_meta = pronouns.get(target_id, {})

        # Build evidence entry if provided
        evidence_note = (ref_data.get('evidence_note') or '').strip()
        evidence_type = (ref_data.get('evidence_type') or '').strip().lower()
        evidence_list = []
        if evidence_note:
            evidence_list.append(self._normalize_evidence_entry({
                'type': evidence_type or 'supporting',
                'note': evidence_note,
                'verse': ref_data.get('evidence_verse')
            }))
        elif ref_data.get('evidence'):
            evidence_list = [self._normalize_evidence_entry(ev) for ev in ref_data.get('evidence', [])]

        entry = {
            'id': ref_data.get('id') or datetime.now().strftime("pr-%Y%m%d-%H%M%S"),
            'pronoun_id': target_id,
            'token_id': ref_data.get('token_id') or pronoun_meta.get('token_id'),
            'segment_id': ref_data.get('segment_id') or pronoun_meta.get('segment_id'),
            'pronoun_form': ref_data.get('pronoun_form') or pronoun_meta.get('form'),
            'referent': ref_data.get('referent'),
            'referent_type': ref_data.get('referent_type') or 'entity',
            'status': ref_data.get('status') or 'hypothesis',
            'note': ref_data.get('note') or ref_data.get('rationale'),
            'evidence': evidence_list,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        # Store in unified hypothesis bucket as well
        hyp_entry = self._normalize_hypothesis_entry(verse, {
            'id': entry['id'],
            'target_type': 'pronoun',
            'target_id': entry['pronoun_id'],
            'target_meta': {
                'token_id': entry['token_id'],
                'segment_id': entry['segment_id'],
                'form': entry['pronoun_form']
            },
            'hypothesis': entry['referent'],
            'status': entry['status'],
            'note': entry['note'],
            'evidence': entry['evidence']
        })

        verse.setdefault('pronoun_references', []).append(entry)
        verse.setdefault('structure_hypotheses', []).append(hyp_entry)
        self.save_corpus()
        return hyp_entry

    def update_pronoun_reference(self, surah: int, ayah: int, ref_id: str, updates: Dict) -> Optional[Dict]:
        """Update pronoun referent status/evidence"""
        verse = self.get_verse(surah, ayah)
        if not verse:
            return None

        references = verse.get('pronoun_references', [])
        for ref in references:
            if ref.get('id') == ref_id:
                fields = ['referent', 'referent_type', 'status', 'note']
                for field in fields:
                    if field in updates and updates[field] is not None:
                        ref[field] = updates[field]

                if updates.get('evidence_entry'):
                    evidence_entry = self._normalize_evidence_entry(updates['evidence_entry'])
                    ref.setdefault('evidence', []).append(evidence_entry)

                ref['updated_at'] = datetime.now().isoformat()
                self.save_corpus()
                return ref
        return None

    def delete_pronoun_reference(self, surah: int, ayah: int, ref_id: str) -> bool:
        """Remove a pronoun referent hypothesis"""
        verse = self.get_verse(surah, ayah)
        if not verse:
            return False

        before = len(verse.get('pronoun_references', []))
        verse['pronoun_references'] = [
            r for r in verse.get('pronoun_references', []) if r.get('id') != ref_id
        ]
        after = len(verse.get('pronoun_references', []))
        if after < before:
            self.save_corpus()
            return True
        return False

    def add_annotation(self, surah: int, ayah: int, annotation: Dict) -> bool:
        """Add annotation to verse"""
        verse = self.get_verse(surah, ayah)
        if not verse:
            return False

        # Generate annotation ID if not present
        if 'id' not in annotation:
            timestamp = datetime.now()
            annotation['id'] = timestamp.strftime("a-%Y%m%d-%H%M%S-001-YA")

        # Add timestamps
        if 'created_at' not in annotation:
            annotation['created_at'] = datetime.now().isoformat()
        annotation['updated_at'] = datetime.now().isoformat()

        # Add to verse
        if 'annotations' not in verse:
            verse['annotations'] = []
        verse['annotations'].append(annotation)

        self.save_corpus()
        return True


# Initialize corpus manager
corpus = CorpusManager()


# Routes
@app.route('/')
def index():
    """Main interface - minimal layered canvas"""
    return app.send_static_file('index.html')


@app.route('/api/verses')
def api_verses():
    """Get all verses (paginated)"""
    start = int(request.args.get('start', 0))
    limit = int(request.args.get('limit', 50))

    end = min(start + limit, len(corpus.verses))
    verses = corpus.verses[start:end]

    return jsonify({
        'verses': verses,
        'total': len(corpus.verses),
        'start': start,
        'limit': limit
    })


@app.route('/api/verse/<int:surah>/<int:ayah>')
def api_verse(surah, ayah):
    """Get specific verse"""
    verse = corpus.get_verse(surah, ayah)
    if verse:
        return jsonify(verse)
    return jsonify({'error': 'Verse not found'}), 404


@app.route('/api/verse/index/<int:index>')
def api_verse_by_index(index):
    """Get verse by index"""
    verse = corpus.get_verse_by_index(index)
    if verse:
        return jsonify(verse)
    return jsonify({'error': 'Verse not found'}), 404


@app.route('/api/surahs')
def api_surahs():
    """List all surahs with metadata"""
    return jsonify(corpus.get_surah_summary())


@app.route('/api/surah/<int:surah>')
def api_surah_details(surah):
    """Get all verses for a surah"""
    verses = corpus.get_surah(surah)
    if not verses:
        return jsonify({'error': 'Surah not found'}), 404
    return jsonify({
        'surah': verses[0]['surah'],
        'verses': verses
    })


@app.route('/api/roots')
def api_roots():
    """List all unique roots"""
    return jsonify(corpus.get_root_list())


@app.route('/api/morph_patterns')
def api_morph_patterns():
    """List morphological patterns"""
    return jsonify(corpus.get_morph_patterns())


@app.route('/api/syntax_patterns')
def api_syntax_patterns():
    """List syntactic POS patterns"""
    return jsonify(corpus.get_syntax_patterns())


@app.route('/api/search')
def api_search():
    """Search verses"""
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'text')  # text or root
    limit = int(request.args.get('limit', 100))

    if search_type == 'root':
        results = corpus.search_by_root(query, limit)
    else:
        results = corpus.search_text(query, limit)

    return jsonify({
        'results': results,
        'query': query,
        'type': search_type,
        'count': len(results)
    })


@app.route('/api/search/roots')
def api_search_roots():
    """Search occurrences for a specific root"""
    root = request.args.get('root', '')
    limit = int(request.args.get('limit', 200))
    data = corpus.search_root(root, limit)
    results = data['results']
    total_count = data.get('total_count', len(results))
    return jsonify({
        'results': results,
        'query': root,
        'type': 'root',
        'count': total_count
    })


@app.route('/api/search/morphology')
def api_search_morphology():
    """Search morphological segments"""
    query = request.args.get('q', '')
    pattern_id = request.args.get('pattern_id')
    limit = int(request.args.get('limit', 100))
    if pattern_id:
        results = corpus.search_morph_pattern(pattern_id, limit)
        total_count = len(results)
    else:
        data = corpus.search_morphology(query, limit)
        results = data['results']
        total_count = data.get('total_count', len(results))
    return jsonify({
        'results': results,
        'query': pattern_id or query,
        'type': 'morphology',
        'count': total_count
    })


@app.route('/api/search/syntax')
def api_search_syntax():
    """Search syntactic POS patterns"""
    query = request.args.get('q', '')
    pattern_id = request.args.get('pattern_id')
    limit = int(request.args.get('limit', 100))
    if pattern_id:
        results = corpus.search_syntax_pattern(pattern_id, limit)
        total_count = len(results)
    else:
        data = corpus.search_syntax(query, limit)
        results = data['results']
        total_count = data.get('total_count', len(results))
    return jsonify({
        'results': results,
        'query': pattern_id or query,
        'type': 'syntax',
        'count': total_count
    })


@app.route('/api/search/pattern_word', methods=['POST'])
def api_search_pattern_word():
    """Search diacritic-aware word patterns with placeholders"""
    payload = request.json or {}
    limit = int(payload.get('limit', 50))
    data = corpus.search_pattern_word(payload, limit)
    return jsonify({
        'results': data['results'],
        'query': payload,
        'type': 'pattern_word',
        'count': data.get('total_count', len(data['results']))
    })


@app.route('/api/notes')
def api_notes():
    """List simple note files under /notes"""
    notes_dir = Path(NOTES_PATH)
    if not notes_dir.exists():
        return jsonify({'notes': []})

    notes = []
    for path in notes_dir.rglob('*'):
        if path.is_file() and path.suffix.lower() in {'.md', '.txt'}:
            rel = str(path.relative_to(notes_dir))
            snippet = ''
            try:
                snippet = path.read_text(encoding='utf-8', errors='ignore').strip().split('\n')[0][:200]
            except Exception:
                snippet = ''
            notes.append({'path': rel, 'title': path.stem, 'snippet': snippet})

    return jsonify({'notes': notes})


@app.route('/api/notes/content')
def api_note_content():
    """Return full note content by relative path under /notes"""
    rel_path = request.args.get('path', '')
    if not rel_path:
        return jsonify({'error': 'path required'}), 400
    notes_dir = Path(NOTES_PATH)
    target = notes_dir / rel_path
    try:
        target = target.resolve()
    except Exception:
        return jsonify({'error': 'invalid path'}), 400
    # prevent path traversal
    if notes_dir not in target.parents:
        return jsonify({'error': 'invalid path'}), 400
    if not target.exists() or not target.is_file():
        return jsonify({'error': 'not found'}), 404
    try:
        content = target.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return jsonify({'error': 'unable to read'}), 500
    return jsonify({'path': rel_path, 'content': content})


@app.route('/api/library_search')
def api_library_search():
    """Search text resources in the data/ folder"""
    query = request.args.get('q', '')
    limit = int(request.args.get('limit', 30))
    results = corpus.search_library(query, limit)
    return jsonify({
        'results': results,
        'query': query,
        'type': 'library',
        'count': len(results)
    })


@app.route('/api/annotations/<int:surah>/<int:ayah>', methods=['GET', 'POST'])
def api_annotations(surah, ayah):
    """Get or create annotations for verse"""
    if request.method == 'POST':
        annotation = request.json
        success = corpus.add_annotation(surah, ayah, annotation)
        if success:
            return jsonify({'success': True})
        return jsonify({'error': 'Failed to add annotation'}), 400

    # GET
    verse = corpus.get_verse(surah, ayah)
    if verse:
        return jsonify(verse.get('annotations', []))
    return jsonify({'error': 'Verse not found'}), 404


@app.route('/api/tags')
def api_tags():
    """Get all hypothesis tags"""
    return jsonify(corpus.tags)


@app.route('/api/tags/<tag_name>', methods=['GET', 'PUT'])
def api_tag(tag_name):
    """Get or update specific tag"""
    if request.method == 'PUT':
        tag_data = request.json
        if 'tags' not in corpus.tags:
            corpus.tags['tags'] = {}
        corpus.tags['tags'][tag_name] = tag_data
        corpus.save_tags()
        return jsonify({'success': True})

    # GET
    if 'tags' in corpus.tags and tag_name in corpus.tags['tags']:
        return jsonify(corpus.tags['tags'][tag_name])
    return jsonify({'error': 'Tag not found'}), 404


@app.route('/api/stats')
def api_stats():
    """Get corpus statistics"""
    total_verses = len(corpus.verses)
    total_annotations = sum(len(v.get('annotations', [])) for v in corpus.verses)
    total_tags = len(corpus.tags.get('tags', {}))

    # Count verses with tokens
    verses_with_tokens = sum(1 for v in corpus.verses if v.get('tokens'))

    return jsonify({
        'total_verses': total_verses,
        'verses_with_tokens': verses_with_tokens,
        'total_annotations': total_annotations,
        'total_hypothesis_tags': total_tags
    })


@app.route('/api/pronouns/<verse_ref>', methods=['GET', 'POST'])
def api_pronouns(verse_ref):
    """Inspect and persist pronoun referent hypotheses for a verse"""
    try:
        surah, ayah = verse_ref.split(':')
        surah_num = int(surah)
        ayah_num = int(ayah)
    except ValueError:
        return jsonify({'error': 'Invalid verse reference'}), 400

    if request.method == 'POST':
        ref_data = request.json or {}
        saved = corpus.add_pronoun_reference(surah_num, ayah_num, ref_data)
        if not saved:
            return jsonify({'error': 'Failed to save pronoun reference'}), 400
        return jsonify({'success': True, 'reference': saved})

    payload = corpus.get_pronoun_references(surah_num, ayah_num)
    if payload is None:
        return jsonify({'error': 'Verse not found'}), 404
    return jsonify(payload)


@app.route('/api/hypotheses/<verse_ref>', methods=['GET', 'POST'])
def api_hypotheses(verse_ref):
    """Unified hypothesis management for any structure target"""
    try:
        surah, ayah = verse_ref.split(':')
        surah_num = int(surah)
        ayah_num = int(ayah)
    except ValueError:
        return jsonify({'error': 'Invalid verse reference'}), 400

    verse = corpus.get_verse(surah_num, ayah_num)
    if not verse:
        return jsonify({'error': 'Verse not found'}), 404

    if request.method == 'POST':
        hyp_data = request.json or {}
        entry = corpus.add_structure_hypothesis(surah_num, ayah_num, hyp_data)
        if not entry:
            return jsonify({'error': 'Failed to save hypothesis'}), 400
        return jsonify({'success': True, 'hypothesis': entry})

    return jsonify(verse.get('structure_hypotheses', []))


@app.route('/api/hypotheses/<verse_ref>/<hyp_id>', methods=['PUT', 'DELETE'])
def api_hypothesis_item(verse_ref, hyp_id):
    try:
        surah, ayah = verse_ref.split(':')
        surah_num = int(surah)
        ayah_num = int(ayah)
    except ValueError:
        return jsonify({'error': 'Invalid verse reference'}), 400

    if request.method == 'DELETE':
        ok = corpus.delete_structure_hypothesis(surah_num, ayah_num, hyp_id)
        if not ok:
            return jsonify({'error': 'Hypothesis not found'}), 404
        return jsonify({'success': True})

    updates = request.json or {}
    updated = corpus.update_structure_hypothesis(surah_num, ayah_num, hyp_id, updates)
    if not updated:
        return jsonify({'error': 'Hypothesis not found'}), 404
    return jsonify({'success': True, 'hypothesis': updated})


@app.route('/api/pronouns/<verse_ref>/<ref_id>', methods=['PUT', 'DELETE'])
def api_pronoun_ref(verse_ref, ref_id):
    """Update or delete a specific pronoun referent hypothesis"""
    try:
        surah, ayah = verse_ref.split(':')
        surah_num = int(surah)
        ayah_num = int(ayah)
    except ValueError:
        return jsonify({'error': 'Invalid verse reference'}), 400

    if request.method == 'DELETE':
        success = corpus.delete_pronoun_reference(surah_num, ayah_num, ref_id)
        if not success:
            return jsonify({'error': 'Pronoun reference not found'}), 404
        return jsonify({'success': True})

    # PUT
    updates = request.json or {}
    updated = corpus.update_pronoun_reference(surah_num, ayah_num, ref_id, updates)
    if not updated:
        return jsonify({'error': 'Pronoun reference not found'}), 404
    return jsonify({'success': True, 'reference': updated})


@app.route('/api/connections/<verse_ref>', methods=['GET', 'POST'])
def api_connections(verse_ref):
    """Get or save connections for a verse"""
    try:
        surah, ayah = verse_ref.split(':')
        verse = corpus.get_verse(int(surah), int(ayah))
        if not verse:
            return jsonify({'error': 'Verse not found'}), 404

        if request.method == 'POST':
            # Save connections
            connections = request.json
            verse['connections'] = connections
            corpus.save_corpus()
            return jsonify({'success': True})

        # GET - return connections
        return jsonify(verse.get('connections', {'internal': [], 'external': []}))

    except ValueError:
        return jsonify({'error': 'Invalid verse reference'}), 400


@app.route('/api/patterns', methods=['GET', 'POST'])
def api_patterns():
    """Get or create pattern definitions"""
    if request.method == 'POST':
        pattern = request.json

        # Store patterns in tags as a new section
        if 'patterns' not in corpus.tags:
            corpus.tags['patterns'] = {}

        pattern_id = pattern.get('id', f"pattern-{len(corpus.tags['patterns']) + 1}")
        corpus.tags['patterns'][pattern_id] = pattern
        corpus.save_tags()

        return jsonify({'success': True, 'id': pattern_id})

    # GET - return all patterns
    return jsonify(corpus.tags.get('patterns', {}))


@app.route('/api/patterns/<pattern_id>', methods=['GET', 'DELETE'])
def api_pattern(pattern_id):
    """Get or delete specific pattern"""
    patterns = corpus.tags.get('patterns', {})

    if pattern_id not in patterns:
        return jsonify({'error': 'Pattern not found'}), 404

    if request.method == 'DELETE':
        del patterns[pattern_id]
        corpus.save_tags()
        return jsonify({'success': True})

    return jsonify(patterns[pattern_id])


@app.route('/api/translations/<verse_ref>', methods=['GET', 'POST', 'PUT'])
def api_translations(verse_ref):
    """Get or save translations for a verse"""
    try:
        surah, ayah = verse_ref.split(':')
        verse = corpus.get_verse(int(surah), int(ayah))
        if not verse:
            return jsonify({'error': 'Verse not found'}), 404

        if request.method == 'POST':
            # Add new translation
            translation = request.json
            if 'translations' not in verse:
                verse['translations'] = []

            # Generate ID if not present
            if 'id' not in translation:
                translation['id'] = f"tr-{len(verse['translations']) + 1}"

            translation['created_at'] = datetime.now().isoformat()
            verse['translations'].append(translation)
            corpus.save_corpus()
            return jsonify({'success': True, 'translation': translation})

        if request.method == 'PUT':
            # Update all translations
            verse['translations'] = request.json
            corpus.save_corpus()
            return jsonify({'success': True})

        # GET - return translations
        return jsonify(verse.get('translations', []))

    except ValueError:
        return jsonify({'error': 'Invalid verse reference'}), 400


@app.route('/api/translations/<verse_ref>/<translation_id>', methods=['DELETE'])
def api_translation_delete(verse_ref, translation_id):
    """Delete specific translation"""
    try:
        surah, ayah = verse_ref.split(':')
        verse = corpus.get_verse(int(surah), int(ayah))
        if not verse:
            return jsonify({'error': 'Verse not found'}), 404

        translations = verse.get('translations', [])
        verse['translations'] = [t for t in translations if t.get('id') != translation_id]
        corpus.save_corpus()
        return jsonify({'success': True})

    except ValueError:
        return jsonify({'error': 'Invalid verse reference'}), 400


@app.route('/api/morphology/<int:surah>/<int:ayah>')
def api_masaq_morphology(surah, ayah):
    """Get detailed MASAQ morphological data for a verse"""
    masaq_data = corpus.get_masaq_morphology(surah, ayah)
    if masaq_data is None:
        return jsonify({'error': 'MASAQ data not found for this verse'}), 404
    return jsonify({
        'surah': surah,
        'ayah': ayah,
        'morphology': masaq_data
    })


@app.route('/api/search/morphology_advanced')
def api_search_masaq():
    """Advanced morphological search using MASAQ dataset"""
    morph_tag = request.args.get('morph_tag')
    syntactic_role = request.args.get('syntactic_role')
    case_mood = request.args.get('case_mood')
    limit = int(request.args.get('limit', 50))

    data = corpus.search_masaq_morphology(
        morph_tag=morph_tag,
        syntactic_role=syntactic_role,
        case_mood=case_mood,
        limit=limit
    )

    return jsonify({
        'results': data['results'],
        'query': {
            'morph_tag': morph_tag,
            'syntactic_role': syntactic_role,
            'case_mood': case_mood
        },
        'type': 'masaq_morphology',
        'count': data.get('total_count', len(data['results']))
    })


@app.route('/api/morphology/features')
def api_morphology_features():
    """Get available morphological features from MASAQ dataset"""
    # Collect unique values for filtering
    morph_tags = set()
    syntactic_roles = set()
    case_moods = set()

    for masaq_words in corpus.masaq_data.values():
        for word in masaq_words:
            if word.get('Morph_tag'):
                morph_tags.add(word['Morph_tag'])
            if word.get('Syntactic_Role'):
                syntactic_roles.add(word['Syntactic_Role'])
            if word.get('Case_Mood'):
                case_moods.add(word['Case_Mood'])

    return jsonify({
        'morph_tags': sorted(morph_tags),
        'syntactic_roles': sorted(syntactic_roles),
        'case_moods': sorted(case_moods)
    })


@app.route('/api/morphology/parsed/<int:surah>/<int:ayah>')
def api_parsed_morphology(surah, ayah):
    """Get parsed morphological features for a verse including verb forms"""
    verse = corpus.get_verse(surah, ayah)
    if not verse:
        return jsonify({'error': 'Verse not found'}), 404

    tokens_with_parsed = []
    for token in verse.get('tokens', []):
        token_data = {
            'id': token.get('id'),
            'form': token.get('form'),
            'segments': []
        }
        for segment in token.get('segments', []):
            parsed = corpus.parse_morphological_features(segment)
            token_data['segments'].append({
                'original': segment,
                'parsed': parsed
            })
        tokens_with_parsed.append(token_data)

    return jsonify({
        'surah': surah,
        'ayah': ayah,
        'text': verse.get('text'),
        'tokens': tokens_with_parsed
    })


@app.route('/api/search/verb_forms')
def api_search_verb_forms():
    """Search for specific verb forms (I-X) with optional filters"""
    verb_form = request.args.get('form')  # e.g., "IV", "III", "X"
    person = request.args.get('person')  # e.g., "3rd"
    number = request.args.get('number')  # e.g., "plural"
    gender = request.args.get('gender')  # e.g., "masculine"
    voice = request.args.get('voice')    # e.g., "passive"
    tense = request.args.get('tense')    # e.g., "perfect"
    limit = int(request.args.get('limit', 50))

    results = []
    total_count = 0

    for verse in corpus.verses:
        if not verse.get('tokens'):
            continue

        verse_matches = []
        for token in verse['tokens']:
            for segment in token.get('segments', []):
                if segment.get('pos') != 'V':  # Only verbs
                    continue

                parsed = corpus.parse_morphological_features(segment)

                # Check filters
                matches = True
                if verb_form and not (parsed.get('verb_form') == f"Form {verb_form}"):
                    matches = False
                if person and parsed.get('person') != person:
                    matches = False
                if number and parsed.get('number') != number:
                    matches = False
                if gender and parsed.get('gender') != gender:
                    matches = False
                if voice and parsed.get('voice') != voice:
                    matches = False
                if tense and parsed.get('tense') != tense:
                    matches = False

                if matches:
                    verse_matches.append({
                        'token_form': token.get('form'),
                        'root': parsed.get('root'),
                        'lemma': parsed.get('lemma'),
                        'parsed': parsed
                    })
                    total_count += 1

        if verse_matches and len(results) < limit:
            # Build match description
            match_parts = []
            if verb_form:
                match_parts.append(f"Form {verb_form}")
            if person:
                match_parts.append(f"{person} person")
            if number:
                match_parts.append(number)
            if gender:
                match_parts.append(gender)
            if voice:
                match_parts.append(voice)
            if tense:
                match_parts.append(tense)

            match_desc = ', '.join(match_parts) if match_parts else 'Verb'

            results.append({
                'verse': verse,
                'match': match_desc,
                'matches': verse_matches[:3],
                'match_count': len(verse_matches)
            })

    return jsonify({
        'results': results,
        'query': {
            'verb_form': verb_form,
            'person': person,
            'number': number,
            'gender': gender,
            'voice': voice,
            'tense': tense
        },
        'type': 'verb_forms',
        'count': total_count
    })


if __name__ == '__main__':
    print("=" * 70)
    print("Codex - Quran Research Interface")
    print("=" * 70)
    print(f"Loaded {len(corpus.verses)} verses")
    print(f"Loaded {len(corpus.masaq_data)} verses with MASAQ morphology")
    print(f"Loaded {len(corpus.tags.get('tags', {}))} hypothesis tags")
    print("\nStarting server at http://localhost:5000")
    print("=" * 70)

    app.run(debug=True, host='0.0.0.0', port=5000)
