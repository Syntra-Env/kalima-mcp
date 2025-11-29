// ===== Codex Research Canvas - Configuration Constants =====
// Layer definitions, morphology blocks, syntax blocks, and structure color mappings

// ===== Codex Research Canvas =====
// Interactive Quran text with layered analysis

const LAYER_DEFINITIONS = {
    letter: {
        label: 'Letters & Diacritics',
        description: 'Select individual graphemes or diacritics to describe orthographic cues.',
        categories: [
            { id: 'primary-letter', label: 'حرف أصلي · Primary Letter' },
            { id: 'diacritic-vowel', label: 'حركة · Vowel Diacritic' },
            { id: 'sukun', label: 'سكون · Sukun' },
            { id: 'shadda', label: 'شدة · Gemination' }
        ]
    },
    morphological: {
        label: 'Morphological Units',
        description: 'Assign prefixes, stems, clitics, and suffixes built from letter spans.',
        categories: [
            { id: 'prefix', label: 'سابقة · Prefix' },
            { id: 'stem', label: 'جذر/أصل · Stem' },
            { id: 'suffix', label: 'لاحقة · Suffix' },
            { id: 'clitic', label: 'ضمير/واو/ياء · Clitic' },
            { id: 'particle', label: 'حرف جر · Particle' }
        ]
    },
    word: {
        label: 'Words & Phrases',
        description: 'Compose linguistically valid word-level structures and idioms.',
        categories: [
            { id: 'idafa', label: 'إضافة · Genitive Construct' },
            { id: 'verbal-clause', label: 'جملة فعلية · Verbal Clause' },
            { id: 'nominal-clause', label: 'جملة اسمية · Nominal Clause' },
            { id: 'prepositional-phrase', label: 'شبه جملة · Prepositional Phrase' },
            { id: 'adjectival-phrase', label: 'تركيب وصفي · Adjectival Phrase' }
        ]
    },
    sentence: {
        label: 'Sentence Structures',
        description: 'Work with supra-ayat structures and discourse composition.',
        categories: [
            { id: 'compound', label: 'جملة مركبة · Compound' },
            { id: 'conditional', label: 'جملة شرطية · Conditional' },
            { id: 'emphatic', label: 'جملة توكيدية · Emphatic' },
            { id: 'interrogative', label: 'جملة استفهامية · Interrogative' },
            { id: 'narrative', label: 'تركيب خبري · Narrative Unit' }
        ]
    }
};

const MORPH_BLOCKS = [
    { label: 'PREFIX', value: 'prefix' },
    { label: 'STEM', value: 'stem' },
    { label: 'SUFFIX', value: 'suffix' },
    { label: 'CLITIC', value: 'clitic' },
    { label: 'NOUN (N)', value: 'pos:n' },
    { label: 'VERB (V)', value: 'pos:v' },
    { label: 'ADJ', value: 'pos:adj' },
    { label: 'PRON', value: 'pos:pron' },
    { label: 'PARTICLE', value: 'pos:part' }
];

const SYNTAX_BLOCKS = [
    { label: 'Noun (N)', value: 'n' },
    { label: 'Verb (V)', value: 'v' },
    { label: 'Adj (ADJ)', value: 'adj' },
    { label: 'Pron (PRON)', value: 'pron' },
    { label: 'Prep (P)', value: 'p' },
    { label: 'Conj (CONJ)', value: 'conj' },
    { label: 'Particle (PART)', value: 'part' }
];

const STRUCTURE_COLOR_CLASSES = {
    'prefix': 'structure-tag-prefix',
    'stem': 'structure-tag-stem',
    'suffix': 'structure-tag-suffix',
    'clitic': 'structure-tag-clitic',
    'particle': 'structure-tag-particle',
    'idafa': 'structure-tag-idafa',
    'verbal-clause': 'structure-tag-verbal-clause',
    'nominal-clause': 'structure-tag-nominal-clause',
    'prepositional-phrase': 'structure-tag-prepositional-phrase',
    'adjectival-phrase': 'structure-tag-adjectival-phrase',
    'compound': 'structure-tag-compound',
    'conditional': 'structure-tag-conditional',
    'emphatic': 'structure-tag-emphatic',
    'interrogative': 'structure-tag-interrogative',
    'narrative': 'structure-tag-narrative',
    'primary-letter': 'structure-tag-primary-letter',
    'diacritic-vowel': 'structure-tag-diacritic-vowel',
    'sukun': 'structure-tag-sukun',
    'shadda': 'structure-tag-shadda'
};
