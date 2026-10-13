import test from 'node:test';
import assert from 'node:assert/strict';
import { calculateKappa, parseCSV } from '../web/kappa.mjs';

test('canonical balanced-margin example', () => {
  const res = calculateKappa([[3,0],[2,1],[1,2],[0,3]]);
  assert.ok(Math.abs(res.kappa - 1/3) < 1e-12);
  assert.ok(Math.abs(res.standard_error - Math.sqrt(1/12)) < 1e-12);
  assert.ok(Math.abs(res.p_value - 0.248213) < 1e-5);
  assert.equal(res.n_raters, 3);
});

test('invalid and inconsistent counts are rejected', () => {
  for (const matrix of [[],[[1]],[[1,1],[1,2]],[[2.5,0.5]],[[true,2]],[[1,-1]]]) {
    assert.throws(() => calculateKappa(matrix));
  }
});

test('unanimous marginals and single-subject data have no hypothesis test', () => {
  assert.equal(calculateKappa([[3,0],[3,0]]).standard_error, null);
  assert.equal(calculateKappa([[2,1]]).p_value, null);
});

test('import quoted RFC4180-like CSV, ignore subject identifiers and reorder category numbers', () => {
  const csv='ID,cat2,cat1\r\n"subject, one",0,3\r\n"subject two",3,0\r\n';
  assert.deepEqual(parseCSV(csv).matrix, [[3,0],[0,3]]);
  assert.equal(calculateKappa(parseCSV(csv).matrix).kappa,1);
});

test('import rejects fractional and unsafe integer category counts', () => {
  assert.throws(() => parseCSV('ID,cat1,cat2\nX,1.5,1.5'), /integer/);
  assert.throws(() => parseCSV('ID,cat1,cat2\nX,9007199254740992,0'), /safe integer/);
});
