import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const defaultAllowedHosts = ['localhost', '127.0.0.1', 'frontend', 'host.docker.internal']
const allowedHosts = (process.env.VITE_ALLOWED_HOSTS || defaultAllowedHosts.join(','))
  .split(',')
  .map((host) => host.trim())
  .filter(Boolean)

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    allowedHosts,
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
    pool: 'forks',
    maxWorkers: 1,
    fileParallelism: false,
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['node_modules/**', 'e2e/**', '**/*.spec.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules/', 'src/test/', 'e2e/'],
    },
  },
})
