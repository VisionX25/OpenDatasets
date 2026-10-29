import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  base: process.env.DEPLOY_BASE || '/',
  server: { allowedHosts: ['terminal.local'] },
  plugins: [react(), tailwindcss()],
})
