import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// В режиме разработки запросы к /upload, /status и /result Vite сам пересылает на backend.
// Для браузера это тот же адрес, поэтому CORS на backend настраивать не нужно.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000'
  const proxy = Object.fromEntries(
    ['/upload', '/status', '/result'].map((path) => [path, { target, changeOrigin: true }]),
  )
  return { plugins: [react()], server: { proxy } }
})
