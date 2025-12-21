const FIELD_TO_SHORT = {
  text: 'o',
  root: 'r',
  lemma: 'l',
  pos: 'p',
  pattern: 'pat',
  case: 'c',
  gender: 'g',
  number: 'n',
  person: 'per',
  verb_form: 'vf',
  voice: 'v',
  mood: 'm',
  aspect: 'a',
  dependency_rel: 'dep',
  role: 'role',
  type: 'st',
  form: 'sf',
};

export class QueryBuilder {
  constructor() {
    this.anchors = [];
    this.nextAnchorNum = 1;
    this.isActive = false;
  }

  clear() {
    this.anchors = [];
    this.nextAnchorNum = 1;
  }

  getAnchor(anchorNum) {
    return this.anchors.find((a) => a.anchorNum === anchorNum) || null;
  }

  ensureAnchor(anchorNum) {
    let anchor = this.getAnchor(anchorNum);
    if (anchor) return anchor;

    anchor = { anchorNum, constraints: [] };
    this.anchors.push(anchor);
    this.anchors.sort((a, b) => a.anchorNum - b.anchorNum);

    if (anchorNum >= this.nextAnchorNum) {
      this.nextAnchorNum = anchorNum + 1;
    }

    return anchor;
  }

  createAnchor() {
    const anchorNum = this.nextAnchorNum++;
    this.ensureAnchor(anchorNum);
    return anchorNum;
  }

  removeAnchor(anchorNum) {
    this.anchors = this.anchors.filter((a) => a.anchorNum !== anchorNum);
  }

  addConstraint(anchorNum, field, value) {
    if (!field || value == null || value === '') return;

    const anchor = this.ensureAnchor(anchorNum);
    const existing = anchor.constraints.find((c) => c.field === field);
    if (existing) {
      existing.value = value;
      return;
    }
    anchor.constraints.push({ field, value });
  }

  toggleConstraint(anchorNum, field, value) {
    if (!field || value == null || value === '') return;

    const anchor = this.ensureAnchor(anchorNum);
    const idx = anchor.constraints.findIndex((c) => c.field === field && c.value === value);
    if (idx >= 0) {
      anchor.constraints.splice(idx, 1);
      if (anchor.constraints.length === 0) {
        this.removeAnchor(anchorNum);
      }
      return;
    }
    this.addConstraint(anchorNum, field, value);
  }

  buildQueryString() {
    const parts = [];
    const anchors = [...this.anchors].sort((a, b) => a.anchorNum - b.anchorNum);

    for (const anchor of anchors) {
      if (!anchor.constraints || anchor.constraints.length === 0) continue;
      parts.push(`#${anchor.anchorNum}`);
      for (const c of anchor.constraints) {
        const short = FIELD_TO_SHORT[c.field] || c.field;
        parts.push(`${short}:${encodeValue(c.value)}`);
      }
    }
    return parts.join(' ').trim();
  }

  toConcordanceRequest() {
    return { query: this.buildQueryString() };
  }
}

function encodeValue(value) {
  const s = String(value ?? '');
  if (!s) return s;
  if (!/[\s"\\]/.test(s)) return s;
  const escaped = s.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
  return `"${escaped}"`;
}
