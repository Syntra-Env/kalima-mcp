import test from 'node:test';
import assert from 'node:assert/strict';
import { QueryBuilder } from '../../desktop/frontend/lib/concordance/queryBuilder.js';

test('QueryBuilder builds anchored query string', () => {
  const builder = new QueryBuilder();
  const a1 = builder.createAnchor();
  builder.addConstraint(a1, 'root', 'ajl');
  builder.addConstraint(a1, 'case', 'Nom');

  const a2 = builder.createAnchor();
  builder.addConstraint(a2, 'gender', 'M');
  builder.addConstraint(a2, 'pos', 'V');

  assert.equal(builder.buildQueryString(), '#1 r:ajl c:Nom #2 g:M p:V');
});

test('QueryBuilder toggle removes constraints and anchors', () => {
  const builder = new QueryBuilder();
  const a1 = builder.createAnchor();
  builder.addConstraint(a1, 'root', 'ajl');
  builder.toggleConstraint(a1, 'root', 'ajl');

  assert.equal(builder.buildQueryString(), '');
  assert.equal(builder.getAnchor(a1), null);
});

test('QueryBuilder toggle updates existing field value', () => {
  const builder = new QueryBuilder();
  const a1 = builder.createAnchor();
  builder.addConstraint(a1, 'gender', 'M');
  builder.toggleConstraint(a1, 'gender', 'F');

  assert.equal(builder.buildQueryString(), '#1 g:F');
});

