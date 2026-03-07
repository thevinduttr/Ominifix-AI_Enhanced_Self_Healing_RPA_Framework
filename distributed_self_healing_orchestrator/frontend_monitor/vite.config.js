import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/status': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/element-locator': {
        target: 'http://localhost:8001',
        changeOrigin: true
      },
      '/healing-direct': {
        target: 'http://localhost:8501',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/healing-direct/, '/api/v1/heal')
      }
    }
  }
})
