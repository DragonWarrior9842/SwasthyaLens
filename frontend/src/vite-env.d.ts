/// <reference types="vite/client" />

interface ViteTypeOptions {
  strictImportMetaEnv: unknown
}

interface ImportMetaEnv {
  readonly VITE_ENABLE_VOICE?: string
  readonly VITE_API_BASE_URL?: string
}
