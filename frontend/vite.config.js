import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/nodes': 'http://127.0.0.1:8188',
      '/files': 'http://127.0.0.1:8188',
      '/browse': 'http://127.0.0.1:8188',
      '/channels': 'http://127.0.0.1:8188',
      '/upload': 'http://127.0.0.1:8188',
      '/download': 'http://127.0.0.1:8188',
      '/prompt': 'http://127.0.0.1:8188',
      '/ws': {
        target: 'http://127.0.0.1:8188',
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
});
