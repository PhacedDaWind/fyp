export const normalizePlate = value => value.toUpperCase().replace(/\s/g, '');
export const splitPlates = value => value.split(/[,;\n\r]+/).map(v => normalizePlate(v.trim())).filter(Boolean);
// Expiry is inclusive. Clamp anniversaries such as January 31 to February's last day.
export function permitEnd(start, months) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(start) || !Number.isInteger(Number(months)) || Number(months)<1 || Number(months)>60) return '';
  const [y,m,d] = start.split('-').map(Number);
  const target = new Date(Date.UTC(y,m-1+Number(months),1));
  const last = new Date(Date.UTC(target.getUTCFullYear(),target.getUTCMonth()+1,0)).getUTCDate();
  target.setUTCDate(Math.min(d,last));
  return target.toISOString().slice(0,10);
}
export function localDate(date = new Date()) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kuala_Lumpur', year: 'numeric', month: '2-digit', day: '2-digit' }).format(date);
}
export function accessStatus(vehicle, today = localDate()) {
  if (vehicle.blocked) return 'Blocked';
  if (vehicle.validTo < today) return 'Expired';
  if (vehicle.validFrom > today) return 'Scheduled';
  return 'Active';
}
export function validateVehicle(vehicle, vehicles) {
  const plate = normalizePlate(vehicle.plate || '');
  if (!/^[A-Z0-9]{2,12}$/.test(plate)) return 'Enter 2–12 letters or numbers for the plate. Spaces are removed automatically.';
  if (vehicles.some(v => v.id !== vehicle.id && normalizePlate(v.plate) === plate)) return 'This number plate is already registered.';
  if (!vehicle.owner?.trim()) return 'Enter the vehicle owner’s name.';
  if (!['Student', 'Staff', 'Visitor'].includes(vehicle.category)) return 'Choose a valid owner category.';
  if (vehicle.category !== 'Visitor' && !vehicle.ownerId?.trim()) return 'Enter a student or staff ID.';
  const isDate = value => /^\d{4}-\d{2}-\d{2}$/.test(value || '') && !Number.isNaN(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
  if (!isDate(vehicle.validFrom) || !isDate(vehicle.validTo)) return 'Enter valid permit start and end dates.';
  if (vehicle.validTo < vehicle.validFrom) return 'The expiry date must be on or after the start date.';
  return '';
}
export function toCsv(vehicles, today = localDate()) {
  const cell = value => {
    let text = String(value ?? '');
    if (/^[\s]*[=+@-]/.test(text) || /^[\t\r\n]/.test(text)) text = "'" + text;
    return '"' + text.replaceAll('"', '""') + '"';
  };
  const rows = [['Number plate', 'Owner', 'Category', 'Student / staff ID', 'Vehicle', 'Valid from', 'Valid until', 'Status'], ...vehicles.map(v => [v.plate, v.owner, v.category, v.ownerId, v.model, v.validFrom, v.validTo, accessStatus(v, today)])];
  return '\uFEFF' + rows.map(row => row.map(cell).join(',')).join('\r\n');
}
export function demoVehicles() {
  const date = new Date();
  const relative = days => { const d = new Date(date); d.setDate(d.getDate() + days); return localDate(d); };
  const rows = [
    ['WXY 2841', 'Amelia Tan', 'Student', 'B2400101', 'Perodua Myvi · White', 180, false],
    ['VJK 9012', 'Daniel Lim', 'Staff', 'H00124', 'Honda City · Silver', 240, false],
    ['BPK 7738', 'Nur Aisyah', 'Student', 'B2400102', 'Proton Saga · Grey', 120, false],
    ['VDN 4520', 'Arjun Kumar', 'Visitor', '', 'Toyota Vios · Blue', 0, false],
    ['WQA 1866', 'Chloe Wong', 'Student', 'B2300103', 'Perodua Axia · Red', -4, false],
    ['BTR 6089', 'Marcus Lee', 'Staff', 'H00231', 'Honda HR-V · Black', 90, false],
    ['VFH 3351', 'Siti Farah', 'Student', 'B2300104', 'Proton Iriz · Silver', 60, true],
    ['WA 7294', 'Ethan Chan', 'Visitor', '', 'Mazda 3 · Grey', 2, false]
  ];
  return rows.map(([plate, owner, category, ownerId, model, end, blocked], i) => ({ id: `demo-${i}`, plate: normalizePlate(plate), owner, category, ownerId, model, blocked, validFrom: relative(-30), validTo: relative(end), notes: 'Fictional sample record for demonstration.' }));
}
