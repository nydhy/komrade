import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/auth': { target: 'http://localhost:8000', changeOrigin: true },
      '/buddies': { target: 'http://localhost:8000', changeOrigin: true },
      '/checkins': { target: 'http://localhost:8000', changeOrigin: true },
      '/sos': { target: 'http://localhost:8000', changeOrigin: true },
      '/presence': { target: 'http://localhost:8000', changeOrigin: true },
      '/location': { target: 'http://localhost:8000', changeOrigin: true },
      '/settings': { target: 'http://localhost:8000', changeOrigin: true },
      '/translate': { target: 'http://localhost:8000', changeOrigin: true },
      '/report': { target: 'http://localhost:8000', changeOrigin: true },
      '/health': { target: 'http://localhost:8000', changeOrigin: true },
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/tests/setup.ts'],
  },
})
