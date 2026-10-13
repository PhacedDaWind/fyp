<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue';
import Registry from './App.vue';
import { api, readPlatePhoto } from './api';
const sessionBar = ref(null), barHeight = ref(66);
let barObserver;
watch(sessionBar, el => {
  barObserver?.disconnect();
  if(el){barObserver=new ResizeObserver(()=>{barHeight.value=el.getBoundingClientRect().height;});barObserver.observe(el);barHeight.value=el.getBoundingClientRect().height;}
}, {flush:'post'});
onUnmounted(()=>barObserver?.disconnect());
const user = ref(null), loading = ref(true), email = ref(''), password = ref(''), error = ref(''), busy = ref(false), tab = ref('registry');
const plate = ref(''), direction = ref('entry'), attempt = ref(null), visits = ref([]), filter = ref(''), message = ref('');
const photo = ref(null), photoPreview = ref(''), photoReading = ref(null);
function choosePhoto(event) {
  if (photoPreview.value) URL.revokeObjectURL(photoPreview.value);
  photo.value = event.target.files?.[0] || null;
  photoPreview.value = photo.value ? URL.createObjectURL(photo.value) : '';
  photoReading.value = null;
}
async function readPhoto() {
  if (!photo.value) return;
  await run(async () => {
    photoReading.value = await readPlatePhoto(photo.value);
    if (photoReading.value.plate) plate.value = photoReading.value.plate;
  });
}
const passwords = ref({current_password:'',new_password:'',confirm_password:''});
async function changePassword(){await run(async()=>{await api('/password','POST',passwords.value);passwords.value={current_password:'',new_password:'',confirm_password:''};expired();message.value='Password changed. Sign in with your new password.';});}
const account = ref({email:'',password:'',role:'guard'});
function expired() { user.value = null; attempt.value = null; visits.value = []; }
async function run(fn) { if(busy.value)return;busy.value=true;error.value='';message.value='';try{await fn();}catch(e){error.value=e.message;}finally{busy.value=false;} }
async function login(){await run(async()=>{user.value=await api('/login','POST',{email:email.value,password:password.value});password.value='';tab.value=user.value.role==='admin'?'registry':'parking';await refresh();});}
async function logout(){await run(async()=>{await api('/logout','POST');expired();});}
async function refresh(){visits.value=await api('/visits');}
async function scan(){await run(async()=>{attempt.value=null;attempt.value=await api('/simulator/scan','POST',{id:crypto.randomUUID(),plate:plate.value,direction:direction.value});});}
async function open(){await run(async()=>{await api(`/simulator/${attempt.value.id}/open`,'POST');attempt.value={...attempt.value,decision:'ALLOW',reason:'Guard manually opened simulated gate'};});}
async function passage(){await run(async()=>{await api(`/simulator/${attempt.value.id}/passage`,'POST');attempt.value.confirmed=true;message.value='Passage saved to the database.';await refresh();});}
const duration=n=>n==null?'Duration unavailable':`${Math.floor(n/3600)}h ${Math.floor(n%3600/60)}m ${n%60}s`;
const time=v=>v?new Date(v).toLocaleString('en-GB',{timeZone:'Asia/Kuala_Lumpur'}):'—';
onMounted(async()=>{window.addEventListener('parking:unauthorized',expired);try{user.value=await api('/me');tab.value=user.value.role==='admin'?'registry':'parking';await refresh();}catch{}finally{loading.value=false;}});
onUnmounted(()=>{window.removeEventListener('parking:unauthorized',expired);if(photoPreview.value)URL.revokeObjectURL(photoPreview.value);});
</script>
<template>
  <div v-if="loading" class="auth-page">Loading parking system…</div>
  <div v-else-if="!user" class="auth-page"><form class="auth-card" @submit.prevent="login"><div class="eyebrow">HELP UNIVERSITY</div><h1>Parking sign in</h1><p>Use your administrator or guard account.</p><label>Email<input v-model="email" type="email" required autocomplete="username"></label><label>Password<input v-model="password" type="password" required autocomplete="current-password"></label><p v-if="message" role="status">{{message}}</p><p v-if="error" role="alert">{{ error }}</p><button class="btn primary" :disabled="busy">{{busy?'Signing in…':'Sign in'}}</button><small>First account details are in your local .env file.</small></form></div>
  <div v-else class="portal-shell" :style="{'--session-bar-height': barHeight + 'px'}">
    <header ref="sessionBar" class="session-bar"><strong>HELP Park</strong><button v-if="user.role==='admin'" @click="tab='registry'">Vehicle registry</button><button @click="tab='parking';run(refresh)">Parking simulator & visits</button><button v-if="user.role==='admin'" @click="tab='accounts'">Add account</button><button @click="tab='password';error='';message=''">Change password</button><span>{{user.email}} · {{user.role}}</span><button @click="logout" :disabled="busy">Sign out</button></header>
    <p v-if="error" class="portal-error" role="alert">{{error}}</p><p v-if="message" class="portal-message" role="status">{{message}}</p>
    <Registry v-if="tab==='registry' && user.role==='admin'" />
    <main v-else-if="tab==='parking'" class="parking-page"><h1>Parking control simulator</h1><p>Try photo OCR or type a plate. The partner AI model and physical gate are not connected.</p>
      <section class="parking-panel"><h2>Read a number plate from a photo</h2><p>On your phone, tap the camera option and take a close, straight photo of the plate. This temporary OCR works best when the plate fills most of the image.</p><div class="photo-controls"><input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" aria-label="Take or choose a plate photo" @change="choosePhoto"><button type="button" class="btn primary" :disabled="busy || !photo" @click="readPhoto">{{busy?'Reading…':'Read plate'}}</button></div><img v-if="photoPreview" class="plate-preview" :src="photoPreview" alt="Selected plate photo"><p v-if="photoReading" role="status"><template v-if="photoReading.plate">OCR suggests <strong>{{photoReading.plate}}</strong>. Check and correct the plate below before scanning.</template><template v-else>No plate text was found. Try a closer, clearer photo or enter the plate manually.</template></p><small>The photo is processed for this request only. OCR does not open the gate or save a visit.</small></section>
      <section class="parking-panel"><h2>Simulate a plate scan</h2><form class="scan-form" @submit.prevent="scan"><label>Number plate<input v-model="plate" required maxlength="20" placeholder="WXY 2841"></label><label>Direction<select v-model="direction"><option value="entry">Entry</option><option value="exit">Exit</option></select></label><button class="btn primary" :disabled="busy">Scan plate</button></form>
      <div v-if="attempt" class="decision"><h3>{{attempt.plate}} · {{attempt.direction.toUpperCase()}}</h3><p>{{attempt.reason}}</p><p v-if="attempt.direction==='exit'"><strong>Parking duration: {{duration(attempt.duration_seconds)}}</strong></p><p>{{attempt.confirmed?'Passage recorded':attempt.decision==='ALLOW'?'Simulated gate open. Waiting for passage.':'Gate remains closed.'}}</p><button v-if="attempt.decision==='REVIEW'" class="btn secondary" @click="open" :disabled="busy">Guard: manually open gate</button><button v-if="attempt.decision==='ALLOW' && !attempt.confirmed" class="btn primary" @click="passage" :disabled="busy">Confirm vehicle passed</button></div></section>
      <section class="parking-panel"><h2>Parking visits <small>{{visits.filter(v=>v.status==='INSIDE').length}} inside in loaded records</small></h2><p>Guest plates are saved after entry. Guests still need guard approval next time. Latest 1,000 visits; times shown in Malaysia time.</p><label>Search plate<input v-model="filter" placeholder="Search number plate"></label><button class="btn secondary" @click="run(refresh)" :disabled="busy">Refresh</button><div class="table-scroll"><table><thead><tr><th>Plate</th><th>Type</th><th>Entry</th><th>Exit</th><th>Duration</th><th>Status</th><th>Guard</th></tr></thead><tbody><tr v-for="v in visits.filter(v=>v.plate.includes(filter.toUpperCase().replace(/\s/g,'')))" :key="v.id"><td>{{v.plate}}</td><td>{{v.kind}}</td><td>{{time(v.entry_at)}}</td><td>{{time(v.exit_at)}}</td><td>{{v.status==='INSIDE'?'Still parked':duration(v.duration_seconds)}}</td><td>{{v.status}}</td><td>{{v.guard||'—'}}</td></tr></tbody></table><p v-if="!visits.length">No parking visits yet. Try a simulated scan above.</p></div></section>
    </main>
    <main v-else-if="tab==='password'" class="parking-page"><form class="auth-card" @submit.prevent="changePassword"><h1>Change password</h1><p>All sessions will be signed out after the change.</p><label>Current password<input v-model="passwords.current_password" type="password" required maxlength="256" autocomplete="current-password"></label><label>New password<input v-model="passwords.new_password" type="password" required minlength="12" maxlength="256" autocomplete="new-password"><small>Use at least 12 characters.</small></label><label>Confirm new password<input v-model="passwords.confirm_password" type="password" required minlength="12" maxlength="256" autocomplete="new-password"></label><button class="btn primary" :disabled="busy">{{busy?'Saving…':'Update password'}}</button></form></main>
    <main v-else class="parking-page"><form class="auth-card" @submit.prevent="run(async()=>{await api('/users','POST',account);account={email:'',password:'',role:'guard'};message='Account created';})"><h1>Add account</h1><label>Email<input v-model="account.email" type="email" required></label><label>Password<input v-model="account.password" type="password" required minlength="12" autocomplete="new-password"></label><label>Role<select v-model="account.role"><option value="guard">Guard</option><option value="admin">Administrator</option></select></label><button class="btn primary" :disabled="busy">Create account</button></form></main>
  </div>
</template>
<style>
.auth-page{min-height:100vh;display:grid;place-items:center;background:#f3f6f3}.auth-card{width:min(460px,95vw);padding:32px;background:white;border:1px solid #dce5de;border-radius:16px;display:grid;gap:18px}.auth-card label,.scan-form label{display:grid;gap:8px}.auth-card input,.auth-card select,.parking-page input,.parking-page select{border:1px solid #b9c9be;border-radius:7px;padding:12px;background:white;color:#213a2d}.session-bar{position:sticky;top:0;z-index:40;display:flex;gap:18px;align-items:center;padding:16px 24px;background:#244c3c;color:white;flex-wrap:wrap}.session-bar button{color:white;background:transparent;border:1px solid #709784;border-radius:6px;padding:8px}.session-bar span{margin-left:auto;font-size:12px}.parking-page{max-width:1250px;margin:35px auto;padding:20px}.parking-panel{background:white;border:1px solid #dce5de;border-radius:12px;padding:24px;margin-top:24px}.scan-form{display:flex;gap:20px;align-items:end;flex-wrap:wrap}.decision{margin-top:24px;padding:20px;background:#f0f6f1;border-radius:8px}.decision button{margin-right:10px}.portal-error{padding:16px;background:#ffe1dc;color:#832716}.portal-message{padding:16px;background:#dceee0}.parking-panel h2 small{font-size:14px;margin-left:20px}.parking-panel table{margin-top:20px}

.portal-shell .sidebar{top:var(--session-bar-height);height:calc(100dvh - var(--session-bar-height));overflow-y:auto}
.photo-controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.plate-preview{display:block;max-width:min(100%,480px);max-height:240px;object-fit:contain;margin:16px 0;border-radius:8px}.photo-controls input{max-width:100%}
.portal-shell .app-shell{min-height:calc(100dvh - var(--session-bar-height))}
@media(max-width:700px){.portal-shell .topbar{top:var(--session-bar-height)}.portal-shell .sidebar{top:calc(var(--session-bar-height) + 64px);height:calc(100dvh - var(--session-bar-height) - 64px)}.session-bar{gap:8px;padding:10px 12px}.session-bar span{font-size:11px}}

</style>
