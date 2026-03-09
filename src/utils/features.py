"""Feature type mapping between morphemes and features.

Two namespaces exist:
1. Morpheme FK column names (what the morphemes table stores as *_id integers)
2. features (feature_type, category) pairs

This module centralizes the mapping between them.
"""

from typing import Optional

# Maps logical feature name -> (feature_type, category) in features
TERM_TYPE_TO_FEATURE: dict[str, tuple[str, str | None]] = {
    'root':              ('root', None),
    'lemma':             ('lemma', None),
    'pos':               ('pos', None),
    'verb_form':         ('morph', 'VerbForm'),
    'aspect':            ('morph', 'VerbState'),
    'mood':              ('morph', 'VerbMood'),
    'voice':             ('morph', 'VerbVoice'),
    'person':            ('morph', 'Person'),
    'number':            ('morph', 'Number'),
    'gender':            ('morph', 'Gender'),
    'case_value':        ('morph', 'NominalCase'),
    'state':             ('morph', 'NominalState'),
    'derived_noun_type': ('morph', 'DerivedNoun'),
    'dependency_rel':    ('dep_rel', None),
    'role':              ('role', None),
    'type':              ('segment_type', None),
}

# Reverse mapping: (feature_type, category) -> logical feature name
FEATURE_TO_MORPHEME_COL: dict[tuple[str, str | None], str] = {
    v: k for k, v in TERM_TYPE_TO_FEATURE.items()
}

# Maps logical feature name -> FK column name in morphemes table
MORPHEME_FK_COL: dict[str, str] = {
    name: f"{name}_id" for name in TERM_TYPE_TO_FEATURE
}


def feature_to_morpheme_col(feature_type: str, category: str | None) -> Optional[str]:
    """Map features type/category back to logical feature name."""
    return FEATURE_TO_MORPHEME_COL.get((feature_type, category))


def fk_col(feature_name: str) -> str:
    """Get the FK column name in morphemes for a logical feature name.

    e.g. fk_col('root') -> 'root_id', fk_col('verb_form') -> 'verb_form_id'
    """
    return MORPHEME_FK_COL[feature_name]
