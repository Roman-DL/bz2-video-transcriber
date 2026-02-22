import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '0.1.0'),
    __BUILD_NUMBER__: JSON.stringify(process.env.BUILD_NUMBER || '0'),
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://100.64.0.1:8801',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://100.64.0.1:8801',
        ws: true,
      },
      '/health': {
        target: 'http://100.64.0.1:8801',
        changeOrigin: true,
      },
    },
  },
})
