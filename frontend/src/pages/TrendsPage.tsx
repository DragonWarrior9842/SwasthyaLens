import { Badge } from '../components/Badge'
import { Card } from '../components/Card'
import { EmptyState } from '../components/EmptyState'
import { PageHeader } from '../components/PageHeader'

export function TrendsPage() {
  return (
    <>
      <PageHeader eyebrow="HEALTH TRENDS" title="The picture over time" description="Understand changes in your health with observations that build on one another." />
      <Card>
        <div className="card-heading"><h2>Your health trends</h2><Badge>Coming later</Badge></div>
        <EmptyState icon="trends" title="Every trend starts with observations." description="Trend data will appear after health observations are available. Health tracking and trend calculations are not available in this version.">
          <p>Future views will compare dated observations across 7-day and 30-day periods, when enough data is available.</p>
        </EmptyState>
      </Card>
      <div className="page-note"><span className="page-note__line" /><p>Meaningful patterns need real data and time.</p></div>
    </>
  )
}
