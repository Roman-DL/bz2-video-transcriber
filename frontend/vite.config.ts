import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
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
