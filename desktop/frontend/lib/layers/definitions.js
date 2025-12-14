export const CASE_COLORS = { NOM: '#FF8C42', ACC: '#FF5252', GEN: '#9C6ADE' };
export const GENDER_COLORS = { M: '#4A90E2', F: '#E91E63' };
export const NUMBER_COLORS = { SG: '#66BB6A', DU: '#FFA726', PL: '#AB47BC' };
export const PERSON_COLORS = { P1: '#42A5F5', P2: '#66BB6A', P3: '#FFA726' };
export const POS_COLORS = {
  N: '#4CAF50',
  NOUN: '#4CAF50',
  V: '#2196F3',
  VERB: '#2196F3',
  PREP: '#FF9800',
  P: '#FF9800',
  ADJ: '#9C27B0',
  PRON: '#00BCD4',
  DET: '#FFC107',
  default: '#9E9E9E',
};
export const VOICE_COLORS = { ACT: '#66BB6A', PASS: '#EF5350' };

export const DEFAULT_LAYER_INDEX = 0;
export const ANNOTATION_LAYER_INDEX = 13;

export const LAYERS = [
  { id: 0, name: 'Original Arabic', field: null, colorMap: null },
  { id: 1, name: 'Root', field: 'root', colorMap: null },
  { id: 2, name: 'Lemma', field: 'lemma', colorMap: null },
  { id: 3, name: 'Part of Speech', field: 'pos', colorMap: POS_COLORS },
  { id: 4, name: 'Pattern', field: 'pattern', colorMap: null },
  { id: 5, name: 'Case', field: 'case', colorMap: CASE_COLORS },
  { id: 6, name: 'Gender', field: 'gender', colorMap: GENDER_COLORS },
  { id: 7, name: 'Number', field: 'number', colorMap: NUMBER_COLORS },
  { id: 8, name: 'Person', field: 'person', colorMap: PERSON_COLORS },
  { id: 9, name: 'Verb Form', field: 'verb_form', colorMap: null },
  { id: 10, name: 'Voice', field: 'voice', colorMap: VOICE_COLORS },
  { id: 11, name: 'Dependency', field: 'dependency_rel', colorMap: null },
  { id: 12, name: 'Role', field: 'role', colorMap: null },
  { id: 13, name: 'Annotations', field: null, colorMap: null },

  // Extended morphology layers (keep core indices stable, append only).
  { id: 14, name: 'Segment Type', field: 'type', colorMap: null },
  { id: 15, name: 'Segment Form', field: 'form', colorMap: null },
  { id: 16, name: 'Mood', field: 'mood', colorMap: null },
  { id: 17, name: 'Aspect', field: 'aspect', colorMap: null },
  { id: 18, name: 'Derived Noun Type', field: 'derived_noun_type', colorMap: null },
  { id: 19, name: 'State', field: 'state', colorMap: null },
];
