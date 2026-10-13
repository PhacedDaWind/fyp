import { demoVehicles, validateVehicle } from './domain.js';
const KEY = 'help-park-admin-v1';
export function loadState() {
  const raw = localStorage.getItem(KEY);
  if (!raw) return { vehicles: demoVehicles(), activity: [], demo: true };
  const state = JSON.parse(raw);
  if (!Array.isArray(state.vehicles) || !Array.isArray(state.activity) || typeof state.demo !== 'boolean') throw new Error('Invalid saved data');
  const ids = new Set();
  for (const v of state.vehicles) {
    if (!v || typeof v.id !== 'string' || ids.has(v.id) || typeof v.blocked !== 'boolean' || ['plate', 'owner', 'category', 'ownerId', 'model', 'validFrom', 'validTo', 'notes'].some(k => typeof v[k] !== 'string') || validateVehicle(v, state.vehicles)) throw new Error('Invalid saved vehicle');
    ids.add(v.id);
  }
  for (const a of state.activity) if (!a || ['id', 'message', 'at'].some(k => typeof a[k] !== 'string') || Number.isNaN(Date.parse(a.at))) throw new Error('Invalid saved activity');
  return state;
}
export function saveState(state) { localStorage.setItem(KEY, JSON.stringify(state)); }
