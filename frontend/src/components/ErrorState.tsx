import { useI18n } from '../i18n/core'
import { Button } from './Button'
import { Icon } from './Icon'

interface ErrorStateProps {
  title?: string
  description: string
  onRetry?: () => void
}

export function ErrorState({ title = 'Something went wrong', description, onRetry }: ErrorStateProps) {
  const { t, copy } = useI18n()
  return (
    <div className="feedback-state feedback-state--error" role="alert">
      <Icon name="info" />
      <div>
        <p className="feedback-state__title">{copy(title)}</p>
        <p>{copy(description)}</p>
        {onRetry && <Button variant="secondary" size="sm" onClick={onRetry}><Icon name="retry" />{t("Try again")}</Button>}
      </div>
    </div>
  )
}
