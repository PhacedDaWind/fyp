import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { readFileSync } from 'node:fs';
export default defineConfig(({ mode }) => ({ plugins: [vue()], server: {
  proxy: { '/api': 'http://127.0.0.1:8000' },
  ...(mode === 'camera' ? { port: 5443, strictPort: true, https: {
    key: readFileSync(new URL('./.certs/server-key.pem', import.meta.url)),
    cert: readFileSync(new URL('./.certs/server.pem', import.meta.url)),
  } } : {}),
} }));
