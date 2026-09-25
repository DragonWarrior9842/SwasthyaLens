import { useCallback, useEffect } from 'react'
import { useHistoryAccount, useOwnedHistory } from '../observations/useOwnedHistory'
import { getTrend } from '../../services/trends'
import type { Metric } from '../../services/trends'

export function useTrend(metric: Metric, unit: string, period: '7d' | '30d', end: string) {
  const { owner, authFailure } = useHistoryAccount()
  const load = useCallback((signal: AbortSignal) => getTrend(metric, unit, period, end, owner, signal), [metric, unit, period, end, owner])
  const result = useOwnedHistory(load, authFailure)
  const refresh = result.refresh
  useEffect(() => {
    const visible = () => { if (document.visibilityState === 'visible') refresh() }
    const timer = window.setInterval(visible, 60_000)
    document.addEventListener('visibilitychange', visible)
    return () => { window.clearInterval(timer); document.removeEventListener('visibilitychange', visible) }
  }, [refresh])
  return result
}
