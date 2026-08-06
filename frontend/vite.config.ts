import { fileURLToPath, URL } from 'node:url';

import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  build: { chunkSizeWarningLimit: 700 },
  plugins: [react()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    proxy: {
      '/api': { target: 'http://127.0.0.1:19090', changeOrigin: true },
      '/health': { target: 'http://127.0.0.1:19090', changeOrigin: true },
    },
  },
});
