import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../services/api-client'
import { getHealth } from '../services/health'

type ConnectionState =
  | { status: 'checking' }
  | { status: 'connected' }
  | { status: 'unavailable'; message: string }

export function useApiHealth() {
  const [state, setState] = useState<ConnectionState>({ status: 'checking' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    void getHealth(controller.signal).then(
      () => {
        if (!controller.signal.aborted) setState({ status: 'connected' })
      },
      (error: unknown) => {
        if (!controller.signal.aborted) {
          setState({
            status: 'unavailable',
            message: error instanceof ApiError ? error.message : 'The local API could not be reached.',
          })
        }
      },
    )

    return () => controller.abort()
  }, [attempt])

  const retry = useCallback(() => {
    setState({ status: 'checking' })
    setAttempt((previous) => previous + 1)
  }, [])

  return { state, retry }
}
