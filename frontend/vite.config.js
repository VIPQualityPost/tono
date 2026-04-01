import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    allowedHosts: ["bronchial-lorita-gorgeously.ngrok-free.dev"],
    hmr:{
      clientPort: 80,
    },
    port: 5173,
    proxy: {
      '/nodes': 'http://127.0.0.1:8188',
      '/docs': 'http://127.0.0.1:8188',
      '/files': 'http://127.0.0.1:8188',
      '/folder-files': 'http://127.0.0.1:8188',
      '/channels': 'http://127.0.0.1:8188',
      '/upload-folder': 'http://127.0.0.1:8188',
      '/upload': 'http://127.0.0.1:8188',
      '/download': 'http://127.0.0.1:8188',
      '/help-docs': { target: 'http://127.0.0.1:8188', changeOrigin: true },
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
