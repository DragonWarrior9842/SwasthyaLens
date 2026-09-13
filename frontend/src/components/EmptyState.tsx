import type { ReactNode } from 'react'
import { Icon, type IconName } from './Icon'

interface EmptyStateProps {
  icon: IconName
  title: string
  description: string
  action?: ReactNode
  children?: ReactNode
}

export function EmptyState({ icon, title, description, action, children }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <div className="empty-state__symbol"><Icon name={icon} /></div>
      <h2>{title}</h2>
      <p className="empty-state__description">{description}</p>
      {action && <div className="empty-state__action">{action}</div>}
      {children && <div className="empty-state__detail">{children}</div>}
    </div>
  )
}
