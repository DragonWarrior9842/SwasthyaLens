import { useI18n } from '../i18n/core'
import { ButtonLink } from '../components/Button'
import { Card } from '../components/Card'
import { EmptyState } from '../components/EmptyState'
import { Icon } from '../components/Icon'
import { PageHeader } from '../components/PageHeader'

export function NotFoundPage() {
  const { t } = useI18n()
  return (
    <>
      <PageHeader eyebrow={t("PAGE NOT FOUND")} title={t("This page is not here")} description={t("The address may be incorrect, or the page may have moved.")} />
      <Card><EmptyState icon="info" title={t("Let’s get you back to your workspace.")} description={t("Use the navigation to explore SwasthyaLens or return to your overview.")} action={<ButtonLink to="/">{t("Back to dashboard")}<Icon name="arrow-right" /></ButtonLink>} /></Card>
    </>
  )
}
