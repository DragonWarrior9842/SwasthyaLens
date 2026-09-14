const LOCAL_API_BASE_URL = 'http://127.0.0.1:8000'

/** Validate public configuration without preventing the rest of the UI loading. */
export function resolveApiBaseUrl(value: string | undefined): string {
  const input = value?.trim() || LOCAL_API_BASE_URL
  let url: URL

  try {
    url = new URL(input)
  } catch {
    throw new Error('VITE_API_BASE_URL must be an absolute HTTP or HTTPS URL.')
  }

  if (
    !['http:', 'https:'].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash
  ) {
    throw new Error('VITE_API_BASE_URL must be an HTTP(S) URL without credentials, query, or fragment.')
  }

  return url.toString().replace(/\/+$/, '')
}
