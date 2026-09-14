import { useEffect, useRef, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Brand } from '../components/Brand'
import { Button } from '../components/Button'
import { Icon } from '../components/Icon'
import { Sidebar } from '../components/Sidebar'
import { ApiStatus } from '../features/system/ApiStatus'
import { AccountMenu } from '../features/auth/AccountMenu'

export function AppLayout() {
  const { pathname, key: locationKey } = useLocation()
  const [navigationLocation, setNavigationLocation] = useState<string | null>(null)
  const isNavigationOpen = navigationLocation === locationKey
  const menuButtonRef = useRef<HTMLButtonElement>(null)
  const mainRef = useRef<HTMLElement>(null)
  const previousPath = useRef(pathname)

  useEffect(() => {
    if (previousPath.current !== pathname) {
      previousPath.current = pathname
      mainRef.current?.focus()
    }
  }, [pathname])

  useEffect(() => {
    // Clear the disclosure state so returning to an old history key cannot reopen it.
    const closeOnHistoryChange = () => setNavigationLocation(null)
    window.addEventListener('popstate', closeOnHistoryChange)
    return () => window.removeEventListener('popstate', closeOnHistoryChange)
  }, [])

  useEffect(() => {
    if (!isNavigationOpen) return
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setNavigationLocation(null)
        menuButtonRef.current?.focus()
      }
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [isNavigationOpen])

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <header className="mobile-header">
        <Brand />
        <Button ref={menuButtonRef} variant="ghost" className="menu-toggle" aria-label={isNavigationOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={isNavigationOpen} aria-controls="primary-navigation" onClick={() => setNavigationLocation((openedAt) => openedAt === locationKey ? null : locationKey)}>
          <Icon name={isNavigationOpen ? 'close' : 'menu'} />
        </Button>
      </header>
      <Sidebar isOpen={isNavigationOpen} onNavigate={() => setNavigationLocation(null)} footer={<ApiStatus />} />
      <div className="app-main">
        <AccountMenu />
        <main id="main-content" ref={mainRef} tabIndex={-1}>
          <Outlet />
        </main>
        <footer className="app-footer">
          <Icon name="info" />
          <p>SwasthyaLens is for health information and understanding. It does not provide medical diagnoses.</p>
        </footer>
      </div>
    </div>
  )
}
