import { useEffect, useState, type ReactNode } from 'react'
import { useAuth } from '../features/auth/auth-context'
import { getSettings } from '../services/account'
import type { UserSettings } from '../types/auth'
import { LocaleContext } from './core'

export function LocaleProvider({ children }: { children: ReactNode }) {
  const { state } = useAuth()
  const owner = state.status === 'authenticated' ? state.session.user.id : null
  const [settings, setSettings] = useState<UserSettings | null>(null)
  const locale = owner && settings?.user_id === owner ? settings.preferred_language : 'en'
  useEffect(() => { document.documentElement.lang = locale }, [locale])
  useEffect(() => {
    if (!owner) return
    const controller = new AbortController()
    let revision = 0
    const load = () => {
      const current = ++revision
      void getSettings(controller.signal).then(value => {
        if (!controller.signal.aborted && current === revision && value.user_id === owner) setSettings(value)
      }).catch(() => { /* English fallback; settings page exposes read errors and retry. */ })
    }
    const changed = (event: Event) => {
      const value = (event as CustomEvent<UserSettings>).detail
      if (value?.user_id === owner) { revision++; setSettings(value) }
    }
    const channel = typeof BroadcastChannel === 'undefined' ? null : new BroadcastChannel('swasthyalens-settings')
    if (channel) channel.onmessage = event => { if (event.data === 'settings-changed') load() }
    window.addEventListener('swasthyalens-settings-changed', changed)
    load()
    return () => { controller.abort(); channel?.close(); window.removeEventListener('swasthyalens-settings-changed', changed) }
  }, [owner])
  return <LocaleContext value={locale}>{children}</LocaleContext>
}
