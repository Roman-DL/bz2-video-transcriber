import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const getBuildTime = () => {
  const d = new Date()
  // Format in Moscow timezone (UTC+3)
  const options: Intl.DateTimeFormatOptions = {
    timeZone: 'Europe/Moscow',
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }
  const formatted = d.toLocaleString('ru-RU', options)
  // "10.01.26, 18:30" -> "10.01.26 18:30"
  return formatted.replace(',', '')
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
