import { Button } from './Button'
import { Icon } from './Icon'

interface ErrorStateProps {
  title?: string
  description: string
  onRetry?: () => void
}

export function ErrorState({ title = 'Something went wrong', description, onRetry }: ErrorStateProps) {
  return (
    <div className="feedback-state feedback-state--error" role="alert">
      <Icon name="info" />
      <div>
        <p className="feedback-state__title">{title}</p>
        <p>{description}</p>
        {onRetry && <Button variant="secondary" size="sm" onClick={onRetry}><Icon name="retry" />Try again</Button>}
      </div>
    </div>
  )
}
