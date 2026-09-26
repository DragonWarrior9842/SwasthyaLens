import { useI18n } from '../i18n/core'
interface LoadingStateProps {
  title?: string
  description?: string
}

export function LoadingState({ title = 'Loading…', description }: LoadingStateProps) {
  const { copy } = useI18n()
  return (
    <div className="feedback-state" role="status">
      <span className="loading-spinner" aria-hidden="true" />
      <div><p className="feedback-state__title">{copy(title)}</p>{description && <p>{copy(description)}</p>}</div>
    </div>
  )
}
