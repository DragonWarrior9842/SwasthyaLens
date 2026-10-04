import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const proxy = {
  '/api': {
    target: 'http://127.0.0.1:8000',
    rewrite: (path: string) => path.replace(/^\/api(?=\/|$)/, ''),
  },
}

// Install the emitted headers at the real HTTPS gateway; preview is local QA only.
const headers = {
  'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; form-action 'self'",
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'no-referrer',
  'X-Frame-Options': 'DENY',
  'Permissions-Policy': 'camera=(), geolocation=(), payment=(), microphone=(self), on-device-speech-recognition=(self)',
}

export default defineConfig(({ command, mode }) => {
  const envDir = fileURLToPath(new URL('..', import.meta.url))
  const env = loadEnv(mode, envDir, 'VITE_')
  if (Object.keys(env).some(key => !['VITE_API_BASE_URL', 'VITE_ENABLE_VOICE'].includes(key))) {
    throw new Error('Unapproved public frontend configuration name; values are not displayed.')
  }
  if (env.VITE_ENABLE_VOICE && !['true', 'false'].includes(env.VITE_ENABLE_VOICE)) {
    throw new Error('VITE_ENABLE_VOICE must be true or false.')
  }
  if (command === 'build' && env.VITE_API_BASE_URL && env.VITE_API_BASE_URL !== '/api') {
    throw new Error('Release builds require the same-origin /api endpoint.')
  }
  return {
  plugins: [react(), tailwindcss(), {
    name: 'release-header-artifact',
    generateBundle() {
      this.emitFile({ type: 'asset', fileName: 'security-headers.json', source: JSON.stringify(headers, null, 2) })
    },
  }],
  envDir,
  define: { 'import.meta.env.VITE_ENABLE_VOICE': JSON.stringify(env.VITE_ENABLE_VOICE || 'false') },
  server: { host: '127.0.0.1', port: 5173, strictPort: true, proxy },
  preview: { host: '127.0.0.1', port: 5173, strictPort: true, proxy, headers },
  }
})
