"""Feature type mapping between segments and ref_features.

Two namespaces exist:
1. Segment FK column names (what the segments table stores as *_id integers)
2. ref_features (feature_type, category) pairs

This module centralizes the mapping between them.
"""

from typing import Optional

# Maps logical feature name -> (feature_type, category) in ref_features
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
FEATURE_TO_SEGMENT_COL: dict[tuple[str, str | None], str] = {
    v: k for k, v in TERM_TYPE_TO_FEATURE.items()
}

# Maps logical feature name -> FK column name in segments table
SEGMENT_FK_COL: dict[str, str] = {
    name: f"{name}_id" for name in TERM_TYPE_TO_FEATURE
}


def feature_to_segment_col(feature_type: str, category: str | None) -> Optional[str]:
    """Map ref_features type/category back to logical feature name."""
    return FEATURE_TO_SEGMENT_COL.get((feature_type, category))


def fk_col(feature_name: str) -> str:
    """Get the FK column name in segments for a logical feature name.

    e.g. fk_col('root') -> 'root_id', fk_col('verb_form') -> 'verb_form_id'
    """
    return SEGMENT_FK_COL[feature_name]
