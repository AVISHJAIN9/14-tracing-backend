import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  base: '/14-tracing-backend/',
  plugins: [react()],
  server: {
    port: 5140,
    proxy: {
      '/api': {
        target: 'http://localhost:8140',
        changeOrigin: true
      }
    }
  }
});
