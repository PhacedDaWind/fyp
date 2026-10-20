<script setup>
import { ref, shallowRef, nextTick, onMounted, onBeforeUnmount } from 'vue';

const props = defineProps({ busy: Boolean });
const emit = defineEmits(['capture']);
const video = ref(null), stream = shallowRef(null), starting = ref(false);
const detecting = ref(false), capturing = ref(false), error = ref('');
let generation = 0, detectionVersion = 0, timer;
const secure = window.isSecureContext && !!navigator.mediaDevices?.getUserMedia;

function pauseDetection() { detectionVersion++; detecting.value = false; clearTimeout(timer); }
function stopCamera() {
  generation++;
  pauseDetection();
  stream.value?.getTracks().forEach(track => track.stop());
  stream.value = null;
  if (video.value) video.value.srcObject = null;
  starting.value = false;
}
async function startCamera() {
  if (starting.value || stream.value) return;
  error.value = '';
  if (!secure) { error.value = 'Live camera needs HTTPS on your phone. You can still use Take or choose a plate photo below.'; return; }
  const version = ++generation;
  starting.value = true;
  try {
    const media = await navigator.mediaDevices.getUserMedia({ audio: false, video: {
      facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 },
    } });
    // A late permission response must not leave a camera on after navigation.
    if (version !== generation) { media.getTracks().forEach(track => track.stop()); return; }
    stream.value = media;
    await nextTick();
    if (version !== generation) return;
    video.value.srcObject = media;
    await video.value.play();
    for (const track of media.getTracks()) track.onended = () => stopCamera();
  } catch (e) {
    if (version !== generation) return;
    stopCamera();
    error.value = e.name === 'NotAllowedError' ? 'Camera permission was denied. Allow camera access in your browser settings, then try again.'
      : e.name === 'NotFoundError' ? 'No camera was found on this device.'
      : 'Could not start the camera. Close other camera apps and try again.';
  } finally { if (version === generation) starting.value = false; }
}
async function capture() {
  if (!stream.value || props.busy || capturing.value || !video.value?.videoWidth) return;
  const version = generation;
  capturing.value = true;
  try {
    const canvas = document.createElement('canvas');
    const scale = Math.min(1, 1920 / Math.max(video.value.videoWidth, video.value.videoHeight));
    canvas.width = Math.round(video.value.videoWidth * scale);
    canvas.height = Math.round(video.value.videoHeight * scale);
    canvas.getContext('2d').drawImage(video.value, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', .9));
    if (!blob) throw new Error('No frame');
    if (version === generation && !props.busy) emit('capture', new File([blob], 'camera-frame.jpg', { type: 'image/jpeg' }));
  } catch {
    pauseDetection();
    error.value = 'Could not capture a frame. Try restarting the camera.';
  } finally { capturing.value = false; }
}
async function tick(version) {
  if (!detecting.value || version !== detectionVersion) return;
  await capture();
  if (detecting.value && version === detectionVersion) timer = setTimeout(() => tick(version), 1500);
}
function toggleDetection() {
  if (detecting.value) pauseDetection();
  else { detecting.value = true; tick(++detectionVersion); }
}
function visibilityChanged() { if (document.hidden) stopCamera(); }
onMounted(() => document.addEventListener('visibilitychange', visibilityChanged));
onBeforeUnmount(() => { stopCamera(); document.removeEventListener('visibilitychange', visibilityChanged); });
defineExpose({ pauseDetection, stopCamera });
</script>

<template>
  <section class="live-camera">
    <h3>Use live camera</h3>
    <p>Point your rear camera at the vehicle. Capture one frame, or turn on repeated detection.</p>
    <p v-if="!secure">Phone live preview requires a trusted HTTPS connection. The photo capture option below also works over HTTP.</p>
    <div class="photo-controls">
      <button type="button" class="btn secondary" :disabled="starting || !!stream" @click="startCamera">{{starting ? 'Opening camera…' : 'Start camera'}}</button>
      <button v-if="stream || starting" type="button" class="btn secondary" @click="stopCamera">Stop camera</button>
      <button v-if="stream" type="button" class="btn primary" :disabled="busy || capturing" @click="capture">Capture &amp; detect</button>
      <button v-if="stream" type="button" class="btn secondary" :disabled="busy && !detecting" @click="toggleDetection">{{detecting ? 'Pause detection' : 'Start repeated detection'}}</button>
    </div>
    <p v-if="error" role="alert">{{error}}</p>
    <video v-show="stream" ref="video" autoplay playsinline muted aria-label="Live camera preview"></video>
    <p v-if="stream" role="status">{{detecting ? 'Repeated detection on. Frames are sent at most once every 1.5 seconds, when the previous request has finished.' : 'Camera ready. Capture a frame to read its plate.'}}</p>
    <small>Results appear on a captured frame below. Selecting a plate pauses repeated detection. The camera stops when you leave this screen or hide this page.</small>
  </section>
</template>

<style scoped>
.live-camera{margin:20px 0;padding:18px;border:1px solid #cbdacf;border-radius:10px;background:#f6f9f7}
video{display:block;width:100%;max-width:640px;max-height:420px;object-fit:contain;background:#14251a;border-radius:8px;margin-top:16px}
</style>
