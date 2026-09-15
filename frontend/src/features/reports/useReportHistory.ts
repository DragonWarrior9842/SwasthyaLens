import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, errorMessage, isUnauthorized } from '../../services/api-client'
import { cleanupReports, getReportConfig, listReports } from '../../services/reports'
import type { ReportConfig, ReportPage } from '../../types/reports'

type HistoryState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; config: ReportConfig; page: ReportPage; notice: string | null; refreshError: string | null }

export function useReportHistory(ownerId: string, checkSession: () => Promise<void>) {
  const [state, setState] = useState<HistoryState>({ status: 'loading' })
  const [revision, setRevision] = useState(0)
  const [loadingMore, setLoadingMore] = useState(false)
  const [moreError, setMoreError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const moreController = useRef<AbortController | null>(null)

  const authFailure = useCallback((error: unknown) => {
    if (isUnauthorized(error) || (error instanceof ApiError && error.code === 'account_changed')) void checkSession()
  }, [checkSession])

  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      let notice: string | null = null
      try {
        const cleanup = await cleanupReports(ownerId, controller.signal)
        if (cleanup.pending > 0) notice = 'Some earlier deletions are still pending. Refresh to check again.'
      } catch (error) {
        if (controller.signal.aborted) return
        if (isUnauthorized(error) || (error instanceof ApiError && error.code === 'account_changed')) throw error
        notice = 'Earlier deletion cleanup could not be confirmed. Reports awaiting deletion remain listed.'
      }
      const config = await getReportConfig(ownerId, controller.signal)
      const page = await listReports(ownerId, null, controller.signal)
      if (!controller.signal.aborted) setState({ status: 'ready', config, page, notice, refreshError: null })
    }
    void load().catch((error: unknown) => {
      if (!controller.signal.aborted) {
        setState((previous) => previous.status === 'ready' ? { ...previous, refreshError: errorMessage(error) } : { status: 'error', message: errorMessage(error) })
        authFailure(error)
      }
    }).finally(() => { if (!controller.signal.aborted) setRefreshing(false) })
    return () => { controller.abort(); moreController.current?.abort() }
  }, [ownerId, revision, authFailure])

  const refresh = useCallback(() => {
    moreController.current?.abort()
    setLoadingMore(false)
    setMoreError(null)
    setRefreshing(true)
    // Keep an existing upload form mounted during a history refresh.
    setRevision((value) => value + 1)
  }, [])

  async function loadMore() {
    if (state.status !== 'ready' || !state.page.next_cursor || loadingMore) return
    const cursor = state.page.next_cursor
    const controller = new AbortController()
    moreController.current = controller
    setLoadingMore(true)
    setMoreError(null)
    try {
      const page = await listReports(ownerId, cursor, controller.signal)
      if (controller.signal.aborted) return
      if (page.next_cursor === cursor) throw new Error('Non-advancing report cursor')
      setState((previous) => {
        if (previous.status !== 'ready' || previous.page.next_cursor !== cursor) return previous
        const knownIds = new Set(previous.page.reports.map((report) => report.id))
        return { ...previous, page: { reports: [...previous.page.reports, ...page.reports.filter((report) => !knownIds.has(report.id))], next_cursor: page.next_cursor } }
      })
    } catch (error) {
      if (!controller.signal.aborted) { setMoreError(errorMessage(error)); authFailure(error) }
    } finally { if (!controller.signal.aborted) setLoadingMore(false) }
  }

  return { state, refresh, loadMore, loadingMore, moreError, refreshing, authFailure }
}
