<script setup>
import { computed, ref, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { CarFront, LayoutDashboard, ContactRound, History, ArrowUpRight, Plus, Search, Download, ChevronLeft, ChevronRight, X, ShieldCheck, Clock3, Ban, Pencil, Trash2, SlidersHorizontal, ArrowRight, Check, CircleParking, FlaskConical, Menu, CalendarDays } from 'lucide-vue-next';
import { accessStatus, localDate, normalizePlate, validateVehicle, toCsv, permitEnd, splitPlates } from './domain';
import { api } from './api';

const loadError = ref('');
const state = ref({vehicles:[],activity:[],demo:false}), error = ref(''), toast = ref('');
async function refresh(){try{state.value=await api('/state');loadError.value='';}catch(e){error.value=e.message;loadError.value=e.message;}}
const page = ref('Vehicles'), search = ref(''), category = ref('All vehicles'), status = ref('All statuses'), pageNo = ref(1), mobileNav = ref(false);
const today = ref(localDate()), modal = ref(false), formError = ref(''), form = ref({}), confirmation = ref(null), dialog = ref(null);
const permitMonths = ref('3'), saving = ref(false);
function updatePermit(){if(permitMonths.value!=='custom')form.value.validTo=permitEnd(form.value.validFrom,permitMonths.value);}
let timer, toastTimer, returnFocus, previousOverflow;
watch(() => !!(modal.value || confirmation.value), open => {
  if(open){previousOverflow=document.body.style.overflow;document.body.style.overflow='hidden';}
  else if(previousOverflow!==undefined){document.body.style.overflow=previousOverflow;previousOverflow=undefined;}
});
const vehicles = computed(() => state.value.vehicles);
const stats = computed(() => ({ total: vehicles.value.length, active: vehicles.value.filter(v => accessStatus(v, today.value) === 'Active').length, visitors: vehicles.value.filter(v => v.category === 'Visitor' && accessStatus(v, today.value) === 'Active').length, attention: vehicles.value.filter(v => ['Blocked', 'Expired'].includes(accessStatus(v, today.value))).length }));
const filtered = computed(() => vehicles.value.filter(v => {
  const query = search.value.toLowerCase().trim();
  const matches = [v.plate, v.owner, v.ownerId, v.model].join(' ').toLowerCase().includes(query) || v.plate.toLowerCase().includes(query.replace(/\s/g, ''));
  return matches && (category.value === 'All vehicles' || v.category === category.value) && (status.value === 'All statuses' || accessStatus(v, today.value) === status.value);
}));
const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / 7)));
const currentPage = computed(() => Math.min(pageNo.value, totalPages.value));
const visible = computed(() => filtered.value.slice((currentPage.value - 1) * 7, currentPage.value * 7));
const attention = computed(() => vehicles.value.filter(v => ['Expired', 'Blocked'].includes(accessStatus(v, today.value))));
const dateLabel = computed(() => new Date(today.value + 'T12:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }));
function date(value) { return new Date(value + 'T12:00:00').toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }); }
function initials(name) { return name.split(/\s+/).filter(Boolean).slice(0, 2).map(x => x[0]).join(''); }
function plateLabel(plate) { return plate.replace(/^([A-Z]+)(\d)/, '$1 $2'); }
function notify(message) { toast.value = message; clearTimeout(toastTimer); toastTimer = setTimeout(() => toast.value = '', 4000); }
function navigate(value) { page.value = value; mobileNav.value = false; }
async function focusDialog() { returnFocus = document.activeElement; await nextTick(); dialog.value?.querySelector('input, button')?.focus(); }
function openVehicle(vehicle) {
  if (loadError.value) return;
  form.value = vehicle ? { ...vehicle } : { id: '', plate: '', owner: '', ownerId: '', category: 'Student', model: '', validFrom: today.value, validTo: permitEnd(today.value,3), notes: '', blocked: false };
  permitMonths.value = vehicle ? 'custom' : '3';
  formError.value = ''; modal.value = true; focusDialog();
}
function closeDialog() { modal.value = false; confirmation.value = null; nextTick(() => returnFocus?.focus()); }
async function submit() {
  if(saving.value)return;
  const editing=!!form.value.id;
  const plates=editing?[normalizePlate(form.value.plate)]:splitPlates(form.value.plate);
  if(!plates.length || plates.length>100){formError.value='Enter between 1 and 100 plates.';return;}
  if(new Set(plates).size!==plates.length){formError.value='Remove duplicate plates from this batch.';return;}
  const values=plates.map(plate=>({...form.value,plate,owner:form.value.owner.trim(),ownerId:form.value.ownerId.trim(),model:form.value.model.trim(),notes:form.value.notes.trim()}));
  for(const value of values){const problem=validateVehicle(value,vehicles.value);if(problem){formError.value=value.plate+': '+problem;return;}}
  saving.value=true;
  try {await api(editing?'/vehicles/'+form.value.id:'/vehicles/batch',editing?'PUT':'POST',editing?values[0]:{vehicles:values});await refresh();closeDialog();pageNo.value=1;notify(editing?'Vehicle saved':`${values.length} vehicle(s) registered`);}
  catch(e){formError.value=e.message;}finally{saving.value=false;}
}

function ask(type, vehicle) { confirmation.value = { type, vehicle }; focusDialog(); }
async function confirmAction() {
 const {type,vehicle}=confirmation.value;
 try { await api('/vehicles/'+vehicle.id, type==='delete'?'DELETE':'PUT',type==='delete'?undefined:{...vehicle,blocked:!vehicle.blocked}); await refresh();closeDialog();notify('Vehicle updated'); }catch(e){error.value=e.message;}
}
function exportCsv() {
  const url = URL.createObjectURL(new Blob([toCsv(filtered.value, today.value)], { type: 'text/csv;charset=utf-8;' }));
  const a = document.createElement('a'); a.href = url; a.download = `help-park-vehicles-${today.value}.csv`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  notify(`Exported ${filtered.value.length} vehicle records`);
}
function keydown(event) {
  if (!modal.value && !confirmation.value) return;
  if (event.key === 'Escape') closeDialog();
  if (event.key === 'Tab') {
    const elements = [...dialog.value.querySelectorAll('button, input, select, textarea, [tabindex="0"]')].filter(el => !el.disabled);
    const first = elements[0], last = elements.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }
}
onMounted(() => { refresh(); timer = setInterval(() => today.value = localDate(), 30000); document.addEventListener('keydown', keydown); });
onUnmounted(() => { if(previousOverflow!==undefined)document.body.style.overflow=previousOverflow; clearInterval(timer); clearTimeout(toastTimer); document.removeEventListener('keydown', keydown); });
</script>

<template>
  <div class="app-shell" :inert="modal || confirmation ? true : undefined">
    <aside class="sidebar" :class="{ 'mobile-open': mobileNav }">
      <a href="#" class="brand" @click.prevent="navigate('Overview')"><span class="brand-icon"><CircleParking :size="25" /></span><span>HELP<span class="brand-light">park</span><small>CAMPUS ACCESS MANAGEMENT</small></span></a>
      <div class="campus"><span class="campus-symbol">H</span><div>HELP University<small>Parking administration</small></div><ShieldCheck :size="16" /></div>
      <div class="nav-label">WORKSPACE</div>
      <nav aria-label="Main navigation"><button v-for="item in [{name: 'Overview', icon: LayoutDashboard}, {name: 'Vehicles', icon: CarFront}, {name: 'Activity', icon: History}]" :key="item.name" :class="{ selected: page === item.name }" @click="navigate(item.name)"><component :is="item.icon" :size="19" />{{ item.name }}<span v-if="item.name === 'Vehicles'" class="nav-count">{{ stats.total }}</span></button></nav>
      <div class="sidebar-note"><span class="small-icon"><ShieldCheck :size="20" /></span><strong>A smoother way in.</strong><p>Manage campus vehicle access from one place.</p><span class="note-line"></span><small>HELP UNIVERSITY · PARKING</small></div>
      <div class="sidebar-user"><span class="avatar admin">AD</span><div>Administrator<small>Database connected</small></div><span class="user-dot"></span></div>
    </aside>
    <div class="workspace">
      <header class="topbar"><div class="breadcrumbs"><button class="icon-btn mobile-menu" aria-label="Toggle navigation" @click="mobileNav = !mobileNav"><Menu :size="20" /></button><span>Workspace</span><ChevronRight :size="14" /><strong>{{ page }}</strong></div><div class="topbar-right"><span class="prototype"><span></span>Local development</span><span class="top-divider"></span><span class="avatar mini">AD</span></div></header>
      <main>
        <div class="page-heading"><div><div class="eyebrow">CAMPUS PARKING</div><h1>{{ page === 'Vehicles' ? 'Vehicle registry' : page === 'Overview' ? 'Parking overview' : 'Admin activity' }}<span class="heading-dot">.</span></h1><p>{{ page === 'Vehicles' ? 'The right vehicles. The right access. All in one place.' : page === 'Overview' ? 'A clear view of your registered vehicles and parking permits.' : 'A record of changes saved by the server.' }}</p></div><button v-if="page !== 'Activity'" class="btn primary" :disabled="!!loadError" @click="openVehicle()"><Plus :size="18" />Register vehicle</button><span v-else class="date-label"><CalendarDays :size="16" />{{ dateLabel }}</span></div>
        <div v-if="error" class="error-banner" role="alert">{{ error }}</div>
        <div class="demo-banner"><FlaskConical :size="17" /><span><strong>{{ state.demo ? 'Sample workspace' : 'Local workspace' }}</strong><span class="banner-divider">/</span>{{ state.demo ? 'Fictional vehicles to explore the workflow. Changes are saved in this browser.' : 'Records are saved in MySQL. Camera and gate actions are simulated.' }}</span><button v-if="state.demo" :disabled="!!loadError" @click="ask('samples')">Remove samples <ArrowRight :size="14" /></button></div>
        <section v-if="page !== 'Activity'" class="stats-grid" aria-label="Vehicle statistics">
          <article class="stat-card"><div class="stat-top">Registered vehicles<span class="stat-icon"><CarFront :size="19" /></span></div><div class="stat-value">{{ String(stats.total).padStart(2, '0') }}<span class="stat-tag neutral">TOTAL</span></div><small>All vehicles in your registry</small></article>
          <article class="stat-card"><div class="stat-top">Active permits<span class="stat-icon green"><ShieldCheck :size="19" /></span></div><div class="stat-value">{{ String(stats.active).padStart(2, '0') }}<span class="stat-tag green">VALID TODAY</span></div><small><span class="tiny-dot"></span>Within permit dates and unblocked</small></article>
          <article class="stat-card"><div class="stat-top">Visitor access<span class="stat-icon blue"><ContactRound :size="19" /></span></div><div class="stat-value">{{ String(stats.visitors).padStart(2, '0') }}</div><small>Visitors with an active permit</small></article>
          <article class="stat-card"><div class="stat-top">Needs attention<span class="stat-icon amber"><Clock3 :size="19" /></span></div><div class="stat-value">{{ String(stats.attention).padStart(2, '0') }}<span v-if="stats.attention" class="stat-tag amber">REVIEW</span></div><small>Expired permits or blocked vehicles</small></article>
        </section>
        <section v-if="page === 'Vehicles'" class="registry panel">
          <div class="panel-heading"><div><h2>Registered vehicles <span class="count-pill">{{ stats.total }}</span></h2><p>Manage owners, number plates, and parking permissions.</p></div><button class="btn secondary" @click="exportCsv" :disabled="!filtered.length"><Download :size="16" />Export CSV</button></div>
          <div class="registry-toolbar"><div class="tabs" aria-label="Owner category"><button v-for="tab in ['All vehicles', 'Student', 'Staff', 'Visitor']" :key="tab" :class="{ active: category === tab }" @click="category = tab; pageNo = 1">{{ tab === 'All vehicles' || tab === 'Staff' ? tab : tab + 's' }}<span v-if="category === tab">{{ tab === 'All vehicles' ? stats.total : vehicles.filter(v => v.category === tab).length }}</span></button></div><div class="filters"><div class="search-field"><Search :size="17" /><input v-model="search" aria-label="Search vehicles" placeholder="Search plate, owner or ID…" @input="pageNo = 1"><button v-if="search" class="clear-search" aria-label="Clear search" @click="search = ''; pageNo = 1"><X :size="14" /></button></div><div class="status-select"><SlidersHorizontal :size="15" /><select v-model="status" aria-label="Filter by access status" @change="pageNo = 1"><option>All statuses</option><option>Active</option><option>Scheduled</option><option>Expired</option><option>Blocked</option></select></div></div></div>
          <div class="table-scroll"><table><thead><tr><th>NUMBER PLATE</th><th>OWNER</th><th>CATEGORY</th><th>PERMIT EXPIRY</th><th>ACCESS STATUS</th><th class="actions-heading">ACTIONS</th></tr></thead><tbody><tr v-for="v in visible" :key="v.id"><td><button class="plate" :disabled="!!loadError" @click="openVehicle(v)">{{ plateLabel(v.plate) }}</button><small class="vehicle-model">{{ v.model || 'Vehicle details not added' }}</small></td><td><div class="owner-cell"><span class="avatar" :class="v.category.toLowerCase()">{{ initials(v.owner) }}</span><div class="owner-text"><strong>{{ v.owner }}</strong><small>{{ v.ownerId || 'Temporary visitor' }}</small></div></div></td><td><span class="category-tag" :class="v.category.toLowerCase()">{{ v.category }}</span></td><td><span class="expiry" :class="{ overdue: accessStatus(v, today) === 'Expired' }">{{ date(v.validTo) }}</span><small class="expiry-note">{{ v.validTo === today ? 'Expires today' : accessStatus(v, today) === 'Scheduled' ? 'Starts ' + date(v.validFrom) : 'Permit end date' }}</small></td><td><span class="status-badge" :class="accessStatus(v, today).toLowerCase()"><span></span>{{ accessStatus(v, today) }}</span></td><td><div class="row-actions"><button class="icon-btn" :aria-label="'Edit ' + v.plate" :title="'Edit ' + v.plate" :disabled="!!loadError" @click="openVehicle(v)"><Pencil :size="15" /></button><button class="icon-btn" :aria-label="(v.blocked ? 'Unblock ' : 'Block ') + v.plate" :title="v.blocked ? 'Unblock access' : 'Block access'" :disabled="!!loadError" @click="ask('block', v)"><ShieldCheck v-if="v.blocked" :size="16" /><Ban v-else :size="16" /></button><button class="icon-btn delete" :aria-label="'Delete ' + v.plate" title="Delete vehicle" :disabled="!!loadError" @click="ask('delete', v)"><Trash2 :size="15" /></button></div></td></tr></tbody></table></div>
          <div v-if="!filtered.length" class="empty-state"><CarFront :size="32" /><h3>{{ vehicles.length ? 'No matching vehicles' : 'Your registry starts here' }}</h3><p>{{ vehicles.length ? 'Try another search or reset your filters.' : 'Register a vehicle to manage its campus parking permit.' }}</p><button class="btn secondary" v-if="vehicles.length" @click="search = ''; category = 'All vehicles'; status = 'All statuses'">Reset filters</button><button v-else class="btn primary" :disabled="!!loadError" @click="openVehicle()">Register vehicle</button></div>
          <div class="table-footer"><span>Showing <strong>{{ filtered.length ? (currentPage - 1) * 7 + 1 : 0 }}–{{ Math.min(currentPage * 7, filtered.length) }}</strong> of <strong>{{ filtered.length }}</strong> vehicles</span><div class="pagination"><button class="icon-btn" aria-label="Previous page" :disabled="currentPage === 1" @click="pageNo = currentPage - 1"><ChevronLeft :size="16" /></button><span>{{ currentPage }} / {{ totalPages }}</span><button class="icon-btn" aria-label="Next page" :disabled="currentPage === totalPages" @click="pageNo = currentPage + 1"><ChevronRight :size="16" /></button></div></div>
        </section>
        <div v-if="page === 'Overview'" class="overview-grid"><section class="panel"><div class="panel-heading"><div><h2>Permit review</h2><p>Vehicles that need an administrator’s attention.</p></div><Clock3 :size="20" /></div><div class="review-list"><div v-for="v in attention" :key="v.id" class="review-item"><span class="avatar"><CarFront :size="19" /></span><div><strong>{{ plateLabel(v.plate) }}</strong><small>{{ v.owner }} · {{ accessStatus(v, today) }}</small></div><button class="btn secondary" @click="openVehicle(v)" :disabled="!!loadError">Review<ArrowUpRight :size="14" /></button></div><div v-if="!attention.length" class="empty-state"><ShieldCheck :size="30" /><h3>All clear</h3><p>No expired or blocked vehicles to review.</p></div></div></section><section class="panel"><div class="panel-heading"><div><h2>Registry breakdown</h2><p>Vehicles by owner category.</p></div></div><div class="breakdown"><div v-for="type in ['Student', 'Staff', 'Visitor']" :key="type"><div class="breakdown-label"><span>{{ type === 'Staff' ? type : type + 's' }}</span><strong>{{ vehicles.filter(v => v.category === type).length }}</strong></div><div class="bar-track"><div :style="{ width: (stats.total ? vehicles.filter(v => v.category === type).length / stats.total * 100 : 0) + '%' }"></div></div></div><button class="text-link" @click="navigate('Vehicles')">Open vehicle registry<ArrowRight :size="16" /></button></div></section></div>
        <section v-if="page === 'Activity'" class="panel"><div class="panel-heading"><div><h2>Registry changes</h2><p>The latest 200 server-recorded actions. See Parking simulator & visits for vehicle movements.</p></div><History :size="20" /></div><div v-if="!state.activity.length" class="empty-state"><History :size="32" /><h3>No changes yet</h3><p>Register or update a vehicle to start your activity history.</p></div><ol class="activity-list"><li v-for="a in state.activity" :key="a.id"><span class="activity-icon"><Check :size="16" /></span><div><strong>{{ a.message }}</strong><small>{{ a.actor }}</small></div><time :datetime="a.at">{{ new Date(a.at).toLocaleString('en-GB') }}</time></li></ol></section>
        <div class="below-panel"><span><ShieldCheck :size="15" />Permit status is based on dates and blocking rules.</span><span>Last checked · {{ dateLabel }}</span></div>
        <footer>HELP<span>park</span><span class="footer-separator">/</span>Built for a better campus journey.<small>ADMIN WORKSPACE · V0.1</small></footer>
      </main>
    </div>
  </div>
  <div v-if="modal || confirmation" class="modal-backdrop" @click.self="closeDialog"><section ref="dialog" class="dialog" :class="{ compact: confirmation }" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
    <template v-if="modal"><div class="dialog-heading"><div><div class="eyebrow">VEHICLE REGISTRY</div><h2 id="dialog-title">{{ form.id ? 'Edit vehicle' : 'Register a vehicle' }}</h2><p>Connect a number plate to a campus parking permit.</p></div><button class="icon-btn" aria-label="Close dialog" @click="closeDialog"><X :size="20" /></button></div><form @submit.prevent="submit"><div class="form-body"><div v-if="formError" class="error-banner" role="alert">{{ formError }}</div><div class="form-row"><label>Number plate <span>*</span><textarea v-if="!form.id" v-model="form.plate" required rows="3" maxlength="2200" placeholder="WXY 2841, ABC 1234&#10;VJK 9012" aria-label="Number plates"></textarea><input v-else v-model="form.plate" required maxlength="20" placeholder="e.g. WXY 2841" class="plate-input" autocomplete="off"><small>{{ form.id ? 'Letters and numbers; spaces are removed on save.' : 'One plate per line, or separate with commas. Up to 100 plates share the owner and permit details below.' }}</small></label><label>Owner category <span>*</span><select v-model="form.category"><option>Student</option><option>Staff</option><option>Visitor</option></select></label></div><div class="form-row"><label>Owner name <span>*</span><input v-model="form.owner" required maxlength="100" placeholder="Full name"></label><label>{{ form.category === 'Visitor' ? 'Reference (optional)' : form.category + ' ID' }}<span v-if="form.category !== 'Visitor'"> *</span><input v-model="form.ownerId" :required="form.category !== 'Visitor'" maxlength="50" :placeholder="form.category === 'Student' ? 'e.g. B2400196' : 'Owner reference'"></label></div><label>Vehicle description<input v-model="form.model" maxlength="100" placeholder="e.g. Perodua Myvi · White"></label><div class="form-section-label"><ShieldCheck :size="16" />PARKING PERMIT</div><label>Permit duration<select v-model="permitMonths" @change="updatePermit"><option v-for="n in 24" :key="n" :value="String(n)">{{ n }} {{ n === 1 ? 'month' : 'months' }}</option><option value="custom">Custom dates</option></select><small>Expiry includes the displayed end date. Shorter months use their last day.</small></label><div class="form-row"><label>Valid from <span>*</span><input v-model="form.validFrom" type="date" required @change="updatePermit"></label><label>Valid until <span>*</span><input v-model="form.validTo" :readonly="permitMonths !== 'custom'" type="date" :min="form.validFrom" required></label></div><label>Notes <span class="optional">(optional)</span><textarea v-model="form.notes" rows="2" maxlength="500" placeholder="Additional details about this vehicle or permit"></textarea></label><label class="checkbox-label"><input v-model="form.blocked" type="checkbox"><span>Block this vehicle’s access<small>A blocked vehicle is ineligible even with a valid permit.</small></span></label></div><div class="dialog-footer"><span>* Required fields</span><button type="button" class="btn secondary" @click="closeDialog">Cancel</button><button class="btn primary" type="submit" :disabled="saving"><Check :size="16" />{{ saving ? 'Saving…' : form.id ? 'Save changes' : 'Register vehicle(s)' }}</button></div></form></template>
    <template v-else><div class="dialog-heading"><div><h2 id="dialog-title">{{ confirmation.type === 'samples' ? 'Remove sample vehicles?' : confirmation.type === 'delete' ? 'Delete this vehicle?' : confirmation.vehicle.blocked ? 'Unblock this vehicle?' : 'Block this vehicle?' }}</h2></div><button class="icon-btn" aria-label="Close dialog" @click="closeDialog"><X :size="20" /></button></div><div class="confirmation-body"><p v-if="confirmation.type === 'samples'">This removes the fictional sample records. Vehicles you have registered yourself will stay in the registry.</p><p v-else-if="confirmation.type === 'delete'">{{ confirmation.vehicle.plate }} and its owner details will be removed from the registry; parking history is retained. This cannot be undone.</p><p v-else>{{ confirmation.vehicle.plate }} {{ confirmation.vehicle.blocked ? 'will be assessed using its permit dates again.' : 'will be marked as blocked, regardless of its permit dates.' }}</p><p v-if="error" class="error-banner" role="alert">{{ error }}</p></div><div class="dialog-footer"><button class="btn secondary" @click="closeDialog">Cancel</button><button class="btn" :class="confirmation.type === 'delete' ? 'danger' : 'primary'" @click="confirmAction">{{ confirmation.type === 'samples' ? 'Remove samples' : confirmation.type === 'delete' ? 'Delete vehicle' : confirmation.vehicle.blocked ? 'Unblock vehicle' : 'Block vehicle' }}</button></div></template>
  </section></div>
  <div v-if="toast" class="toast" role="status"><span><Check :size="16" /></span>{{ toast }}</div>
</template>
