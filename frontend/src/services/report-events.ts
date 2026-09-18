const channelName = 'swasthyalens-report-changed'
export function reportChanged(reportId: string) {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent(channelName, { detail: reportId }))
  if (typeof BroadcastChannel !== 'undefined') {
    const channel = new BroadcastChannel(channelName)
    channel.postMessage(reportId)
    channel.close()
  }
}
export function onReportChanged(reportId: string, action: () => void) {
  const local = (event: Event) => { if ((event as CustomEvent<unknown>).detail === reportId) action() }
  window.addEventListener(channelName, local)
  const channel = typeof BroadcastChannel === 'undefined' ? null : new BroadcastChannel(channelName)
  if (channel) channel.onmessage = (event: MessageEvent<unknown>) => { if (event.data === reportId) action() }
  return () => { window.removeEventListener(channelName, local); channel?.close() }
}
