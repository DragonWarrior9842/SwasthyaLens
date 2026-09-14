import { afterEach, describe, expect, it, vi } from 'vitest'
import { getHealth } from './health'

// Transport fixtures are confined to tests. The application always calls the API.
const healthy = { status: 'ok', service: 'swasthyalens-api' }

afterEach(() => {
  vi.useRealTimers()
})

describe('service-health API client', () => {
  it('calls the configured backend and validates the real contract', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000/')
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(Response.json(healthy))
    vi.stubGlobal('fetch', fetchMock)

    await expect(getHealth()).resolves.toEqual(healthy)
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/health', expect.objectContaining({
      method: 'GET', credentials: 'omit', cache: 'no-store',
    }))
  })

  it.each([{}, { status: 'ok', service: 'unrelated-api' }, { status: 'down', service: 'swasthyalens-api' }, null])(
    'rejects malformed or unrelated service responses',
    async (payload) => {
      vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(Response.json(payload)))
      await expect(getHealth()).rejects.toMatchObject({ code: 'invalid-response' })
    },
  )

  it('does not display raw server error bodies', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(new Response('internal detail', { status: 500 })))
    await expect(getHealth()).rejects.toMatchObject({ code: 'http', message: 'The local API returned an unsuccessful response.' })
  })

  it('handles non-JSON responses', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(new Response('<html>Not JSON</html>')))
    await expect(getHealth()).rejects.toMatchObject({ code: 'invalid-response' })
  })

  it('reports connection failure without a false connected state', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(getHealth()).rejects.toMatchObject({ code: 'network' })
  })

  it('rejects invalid configuration before any network call', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'invalid')
    const fetchMock = vi.fn<typeof fetch>()
    vi.stubGlobal('fetch', fetchMock)
    await expect(getHealth()).rejects.toMatchObject({ code: 'configuration' })
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('cancels an outstanding request when its consumer goes away', async () => {
    const controller = new AbortController()
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockImplementation((_input, init) => new Promise((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () => reject(new DOMException('Cancelled', 'AbortError')), { once: true })
    })))
    const result = getHealth(controller.signal)
    controller.abort()
    await expect(result).rejects.toMatchObject({ name: 'AbortError' })
  })

  it('bounds an unresponsive request with a timeout', async () => {
    vi.useFakeTimers()
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockImplementation((_input, init) => new Promise((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () => reject(new DOMException('Timed out', 'AbortError')), { once: true })
    })))
    const assertion = expect(getHealth()).rejects.toMatchObject({ code: 'timeout' })
    await vi.advanceTimersByTimeAsync(5_000)
    await assertion
  })
})
