import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    cssMinify: "esbuild",
  },
  server: {
    proxy: {
      "/analyze": "http://127.0.0.1:8787",
      "/analyze-song": "http://127.0.0.1:8787",
      "/health": "http://127.0.0.1:8787",
      "/storage": "http://127.0.0.1:8787",
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})
