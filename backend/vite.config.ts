import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import { fileURLToPath } from 'url';
import path from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      hmr: process.env.DISABLE_HMR !== 'true',
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
      proxy: {
        '/health': 'http://127.0.0.1:8000',
        '/transcribe': 'http://127.0.0.1:8000',
        '/analyze': 'http://127.0.0.1:8000',
        '/rag': 'http://127.0.0.1:8000',
        '/calls': 'http://127.0.0.1:8000',
        '/sync': 'http://127.0.0.1:8000',
        '/telegram': 'http://127.0.0.1:8000',
        '/internal': {
          target: 'http://127.0.0.1:8000',
          ws: true,
        },
      },
    },
  };
});
