interface LoadingStateProps {
  title?: string
  description?: string
}

export function LoadingState({ title = 'Loading…', description }: LoadingStateProps) {
  return (
    <div className="feedback-state" role="status">
      <span className="loading-spinner" aria-hidden="true" />
      <div><p className="feedback-state__title">{title}</p>{description && <p>{description}</p>}</div>
    </div>
  )
}
