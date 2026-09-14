import { Link } from 'react-router-dom'
import { ButtonLink } from '../components/Button'
import { Card } from '../components/Card'
import { EmptyState } from '../components/EmptyState'
import { Icon } from '../components/Icon'
import { PageHeader } from '../components/PageHeader'

export function DashboardPage() {
  return (
    <>
      <PageHeader eyebrow="YOUR HEALTH, IN CONTEXT" title="Your health overview" description="A place to understand your reports and see how your health changes over time." />
      <Card className="overview-card">
        <div className="card-heading"><h2>My health at a glance</h2><span className="subtle-label">Getting started</span></div>
        <EmptyState icon="heart" title="No health data available yet." description="Your overview will take shape as reports and health observations become available. For now, explore your new workspace." action={<ButtonLink to="/reports">Explore reports<Icon name="arrow-right" /></ButtonLink>} />
      </Card>
      <section className="workspace-section" aria-labelledby="workspace-heading">
        <div className="section-heading"><h2 id="workspace-heading">A little more clarity, in one place</h2><p>Your workspace starts here.</p></div>
        <div className="workspace-grid">
          <Link className="workspace-link" to="/reports">
            <span className="workspace-link__icon"><Icon name="report" /></span>
            <div><h3>Your reports, together</h3><p>A home for your medical reports and the information they contain.</p></div>
            <Icon name="arrow-right" className="workspace-link__arrow" />
          </Link>
          <Link className="workspace-link" to="/trends">
            <span className="workspace-link__icon"><Icon name="trends" /></span>
            <div><h3>See the bigger picture</h3><p>A place for changes and patterns across your health history.</p></div>
            <Icon name="arrow-right" className="workspace-link__arrow" />
          </Link>
        </div>
      </section>
    </>
  )
}
