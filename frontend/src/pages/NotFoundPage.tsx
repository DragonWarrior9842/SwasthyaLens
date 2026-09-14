import { ButtonLink } from '../components/Button'
import { Card } from '../components/Card'
import { EmptyState } from '../components/EmptyState'
import { Icon } from '../components/Icon'
import { PageHeader } from '../components/PageHeader'

export function NotFoundPage() {
  return (
    <>
      <PageHeader eyebrow="PAGE NOT FOUND" title="This page is not here" description="The address may be incorrect, or the page may have moved." />
      <Card><EmptyState icon="info" title="Let’s get you back to your workspace." description="Use the navigation to explore SwasthyaLens or return to your overview." action={<ButtonLink to="/">Back to dashboard<Icon name="arrow-right" /></ButtonLink>} /></Card>
    </>
  )
}
