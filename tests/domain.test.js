import { test } from 'node:test';
import assert from 'node:assert/strict';
import { accessStatus, normalizePlate, validateVehicle, toCsv, permitEnd, splitPlates } from '../src/domain.js';
test('permit months handle year rollover and short/leap months', () => {
  assert.equal(permitEnd('2026-09-29',3),'2026-12-29');
  assert.equal(permitEnd('2026-01-31',1),'2026-02-28');
  assert.equal(permitEnd('2028-01-31',1),'2028-02-29');
  assert.equal(permitEnd('2026-11-30',3),'2027-02-28');
  assert.equal(permitEnd('',3),'');
});
test('batch plate parsing preserves spaces within plates and detects normalized repeats', () => {
  assert.deepEqual(splitPlates('wxy 2841, ABC123\nVJK9012;\n'),['WXY2841','ABC123','VJK9012']);
  const plates=splitPlates('ABC 123,abc123');assert.equal(new Set(plates).size,1);
});
const vehicle = { id: '1', plate: 'ABC123', owner: 'Example', ownerId: 'B123', category: 'Student', validFrom: '2026-09-01', validTo: '2026-09-18', blocked: false };
test('permit boundaries are inclusive and blocking overrides validity', () => {
  assert.equal(accessStatus(vehicle, '2026-09-18'), 'Active');
  assert.equal(accessStatus(vehicle, '2026-09-19'), 'Expired');
  assert.equal(accessStatus(vehicle, '2026-08-31'), 'Scheduled');
  assert.equal(accessStatus({ ...vehicle, blocked: true }, '2026-09-19'), 'Blocked');
});
test('normalizes plates and prevents duplicates while allowing updates', () => {
  assert.equal(normalizePlate('abc 123'), 'ABC123');
  assert.match(validateVehicle({ ...vehicle, id: '2', plate: 'abc 123' }, [vehicle]), /already registered/);
  assert.equal(validateVehicle(vehicle, [vehicle]), '');
});
test('rejects invalid date ranges and missing owner identification', () => {
  assert.match(validateVehicle({ ...vehicle, validTo: '2026-08-01' }, []), /expiry/);
  assert.match(validateVehicle({ ...vehicle, validTo: '2026-02-30' }, []), /valid permit/);
  assert.match(validateVehicle({ ...vehicle, ownerId: '' }, []), /student or staff ID/);
  assert.equal(validateVehicle({ ...vehicle, ownerId: '', category: 'Visitor' }, []), '');
});
test('CSV quotes content and neutralizes spreadsheet formulas', () => {
  const csv = toCsv([{ ...vehicle, owner: '=1+1', model: 'Car, "White"' }]);
  assert.ok(csv.includes('"\'=1+1"'));
  assert.ok(csv.includes('"Car, ""White"""'));
});
