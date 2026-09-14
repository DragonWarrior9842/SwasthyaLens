import { Badge } from '../components/Badge'
import { ButtonLink } from '../components/Button'
import { Card } from '../components/Card'
import { EmptyState } from '../components/EmptyState'
import { Icon } from '../components/Icon'
import { PageHeader } from '../components/PageHeader'

export function AssistantPage() {
  return (
    <>
      <PageHeader eyebrow="AI HEALTH ASSISTANT" title="More understanding, less jargon" description="A future space for questions about your reports and health history." />
      <Card>
        <div className="card-heading"><h2>Your health, in conversation</h2><Badge>Coming later</Badge></div>
        <EmptyState icon="assistant" title="Your health story comes first." description="Upload or add health information before asking questions about your health history. Uploading and AI conversations are not available in this version." action={<ButtonLink to="/reports" variant="secondary">View reports<Icon name="arrow-right" /></ButtonLink>}>
          <p>Future responses will be designed to explain health information, with links back to the records behind it.</p>
        </EmptyState>
      </Card>
    </>
  )
}
