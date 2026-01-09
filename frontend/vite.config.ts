import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const getBuildTime = () => {
  const d = new Date()
  const date = `${d.getDate().toString().padStart(2, '0')}.${(d.getMonth() + 1).toString().padStart(2, '0')}.${d.getFullYear().toString().slice(-2)}`
  const time = `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
  return `${date} ${time}`
}

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '0.1.0'),
    __BUILD_TIME__: JSON.stringify(getBuildTime()),
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
