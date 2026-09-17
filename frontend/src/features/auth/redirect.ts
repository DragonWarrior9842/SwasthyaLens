const destinations = new Set(['/', '/reports', '/history', '/trends', '/assistant', '/settings'])

/** Redirects are application destinations, never arbitrary URLs or user input paths. */
export function safeReturnTo(value: unknown): string {
  return typeof value === 'string' && destinations.has(value) ? value : '/'
}
