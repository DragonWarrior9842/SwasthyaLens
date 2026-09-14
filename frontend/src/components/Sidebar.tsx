import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { Brand } from './Brand'
import { Icon, type IconName } from './Icon'

const destinations: { to: string; label: string; icon: IconName }[] = [
  { to: '/', label: 'Dashboard', icon: 'dashboard' },
  { to: '/reports', label: 'Reports', icon: 'report' },
  { to: '/trends', label: 'Trends', icon: 'trends' },
  { to: '/assistant', label: 'AI Assistant', icon: 'assistant' },
  { to: '/settings', label: 'Account settings', icon: 'info' },
]

interface SidebarProps {
  isOpen: boolean
  onNavigate: () => void
  footer?: ReactNode
}

export function Sidebar({ isOpen, onNavigate, footer }: SidebarProps) {
  return (
    <aside id="primary-navigation" className={`sidebar ${isOpen ? 'sidebar--open' : ''}`} aria-label="Application sidebar">
      <div className="sidebar__brand"><Brand /></div>
      <div className="sidebar__navigation">
        <p className="sidebar__label">YOUR WORKSPACE</p>
        <nav aria-label="Primary navigation">
          <ul>
            {destinations.map(({ to, label, icon }) => (
              <li key={to}>
                <NavLink to={to} end={to === '/'} onClick={onNavigate} className={({ isActive }) => `nav-link ${isActive ? 'nav-link--active' : ''}`}>
                  <Icon name={icon} /><span>{label}</span><span className="nav-link__indicator" aria-hidden="true" />
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </div>
      <div className="sidebar__bottom">
        <div className="sidebar__message">
          <span className="sidebar__message-icon"><Icon name="heart" /></span>
          <p>A clearer view<br />of your health.</p>
          <span>One place for the information<br className="desktop-break" /> that matters to you.</span>
        </div>
        {footer && <div className="sidebar__footer">{footer}</div>}
      </div>
    </aside>
  )
}
