// Invalidation signals carry no measurements, report text, identity or credentials.
const channelName = 'swasthyalens-history-changed'
export function historyChanged() {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new Event(channelName))
  if (typeof BroadcastChannel !== 'undefined') {
    const channel = new BroadcastChannel(channelName)
    channel.postMessage('changed')
    channel.close()
  }
}
export function onHistoryChanged(action: () => void) {
  window.addEventListener(channelName, action)
  const channel = typeof BroadcastChannel === 'undefined' ? null : new BroadcastChannel(channelName)
  if (channel) channel.onmessage = (event: MessageEvent<unknown>) => { if (event.data === 'changed') action() }
  return () => { window.removeEventListener(channelName, action); channel?.close() }
}
