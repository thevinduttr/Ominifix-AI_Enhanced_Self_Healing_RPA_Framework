import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
const orchestratorProxyTarget = process.env.ORCHESTRATOR_PROXY_TARGET || 'http://orchestrator_monitor:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/orchestrator/status': {
        target: orchestratorProxyTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/orchestrator\/status$/, '/status')
      }
    }
  }
})
