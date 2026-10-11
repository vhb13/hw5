import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The backend allows requests from http://localhost:5173 (CORS), so the browser
// talks to http://localhost:8000 directly. strictPort keeps us on 5173 so that
// CORS origin never silently changes.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
})
