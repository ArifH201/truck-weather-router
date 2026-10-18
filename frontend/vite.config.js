import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, proxy /api to Django so the browser sees one origin (no CORS needed).
// In production set VITE_API_URL to the hosted backend's URL.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
  test: { environment: 'node' },
})
