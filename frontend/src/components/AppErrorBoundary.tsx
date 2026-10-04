import { Component, type ReactNode } from 'react'
import { translate } from '../i18n/core'

/** Unmount the private UI on failure; never persist or log exception contents. */
export class AppErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    if (!this.state.failed) return this.props.children
    const locale = document.documentElement.lang === 'hi' ? 'hi' : 'en'
    const t = (key: string) => translate(locale, key)
    return <main className="session-screen"><section className="card session-card" role="alert">
      <h1>{t('This page could not be displayed.')}</h1>
      <p>{t('Reload to reconnect to your private workspace. Unsaved edits may need to be entered again.')}</p>
      <button className="button" onClick={() => window.location.reload()}>{t('Reload application')}</button>
    </section></main>
  }
}
