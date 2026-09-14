import { useEffect, useState, type FormEvent } from 'react'
import { Button } from '../components/Button'
import { ErrorState } from '../components/ErrorState'
import { LoadingState } from '../components/LoadingState'
import { PageHeader } from '../components/PageHeader'
import { useAuth } from '../features/auth/auth-context'
import { ApiError, errorMessage, isUnauthorized } from '../services/api-client'
import { getProfile, getSettings, saveProfile, saveSettings } from '../services/account'
import type { Profile, UserSettings } from '../types/auth'

type AccountData =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; profile: Profile; settings: UserSettings }

export function SettingsPage() {
  const { state, checkSession } = useAuth()
  const [data, setData] = useState<AccountData>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)
  const userId = state.status === 'authenticated' ? state.session.user.id : null

  useEffect(() => {
    const controller = new AbortController()
    void Promise.all([getProfile(controller.signal), getSettings(controller.signal)]).then(([profile, settings]) => {
      if (!controller.signal.aborted) {
        if (profile.id !== userId || settings.user_id !== userId) {
          setData({ status: 'error', message: 'The account response could not be verified. Please try again.' })
          return
        }
        setData({ status: 'ready', profile, settings })
      }
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) {
        setData({ status: 'error', message: errorMessage(error) })
        if (isUnauthorized(error)) void checkSession()
      }
    })
    return () => controller.abort()
  }, [userId, attempt, checkSession])

  return (
    <>
      <PageHeader eyebrow="YOUR ACCOUNT" title="Make yourself at home" description="Manage your name and preferences for your SwasthyaLens account." />
      {(data.status === 'loading' || (data.status === 'ready' && (data.profile.id !== userId || data.settings.user_id !== userId))) && <LoadingState title="Loading your account…" />}
      {data.status === 'error' && <ErrorState title="Unable to load your account" description={data.message} onRetry={() => { setData({ status: 'loading' }); setAttempt((value) => value + 1) }} />}
      {data.status === 'ready' && data.profile.id === userId && data.settings.user_id === userId && <div className="settings-grid"><ProfileForm key={`${userId}-profile`} profile={data.profile} /><PreferencesForm key={`${userId}-settings`} settings={data.settings} /></div>}
    </>
  )
}

function ProfileForm({ profile }: { profile: Profile }) {
  const { state, checkSession } = useAuth()
  const [displayName, setDisplayName] = useState(profile.display_name ?? '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    setBusy(true)
    setError(null)
    setSaved(false)
    try {
      const updated = await saveProfile(displayName.trim() || null, profile.id)
      if (updated.id !== profile.id) throw new Error('Mismatched profile')
      setDisplayName(updated.display_name ?? '')
      setSaved(true)
    } catch (failure) {
      setError(errorMessage(failure))
      if (isUnauthorized(failure) || (failure instanceof ApiError && failure.code === 'account_changed')) await checkSession()
    } finally { setBusy(false) }
  }

  return (
    <section className="card settings-card" aria-labelledby="profile-heading">
      <h2 id="profile-heading">Personal details</h2>
      <p className="settings-card__description">Choose how your name appears in your account.</p>
      <form className="account-form" onSubmit={(event) => { void submit(event) }} aria-busy={busy}>
        <div className="form-field"><label htmlFor="profile-name">Display name <span>(optional)</span></label><input id="profile-name" name="display_name" type="text" autoComplete="nickname" maxLength={80} value={displayName} disabled={busy} onChange={(event) => { setDisplayName(event.target.value); setSaved(false) }} aria-describedby="profile-name-help" /><p id="profile-name-help">Up to 80 characters. You can leave this blank.</p></div>
        <div className="form-field"><span className="field-label">Email address</span><p className="account-email">{state.status === 'authenticated' ? state.session.user.email : ''}</p></div>
        {error && <div className="form-error" role="alert">{error}</div>}
        {saved && <div className="form-success" role="status">Your profile has been saved.</div>}
        <Button type="submit" disabled={busy}>{busy ? 'Saving…' : 'Save profile'}</Button>
      </form>
    </section>
  )
}

function PreferencesForm({ settings }: { settings: UserSettings }) {
  const { checkSession } = useAuth()
  const [language, setLanguage] = useState(settings.preferred_language)
  const [timezone, setTimezone] = useState(settings.timezone)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    setError(null)
    setSaved(false)
    const selectedTimezone = timezone.trim()
    try { new Intl.DateTimeFormat('en', { timeZone: selectedTimezone }).format() }
    catch { setError('Enter a valid time zone, such as Asia/Kolkata or UTC.'); return }
    setBusy(true)
    try {
      const updated = await saveSettings({ preferred_language: language, timezone: selectedTimezone }, settings.user_id)
      if (updated.user_id !== settings.user_id) throw new Error('Mismatched settings')
      setLanguage(updated.preferred_language)
      setTimezone(updated.timezone)
      setSaved(true)
    } catch (failure) {
      setError(errorMessage(failure))
      if (isUnauthorized(failure) || (failure instanceof ApiError && failure.code === 'account_changed')) await checkSession()
    } finally { setBusy(false) }
  }

  return (
    <section className="card settings-card" aria-labelledby="preferences-heading">
      <h2 id="preferences-heading">Your preferences</h2>
      <p className="settings-card__description">Saved to your account, so they stay with you.</p>
      <form className="account-form" onSubmit={(event) => { void submit(event) }} aria-busy={busy}>
        <div className="form-field"><label htmlFor="preferred-language">Preferred language</label><select id="preferred-language" value={language} disabled={busy} onChange={(event) => { setLanguage(event.target.value === 'hi' ? 'hi' : 'en'); setSaved(false) }} aria-describedby="language-help"><option value="en">English</option><option value="hi">हिन्दी · Hindi</option></select><p id="language-help">Your preference is saved. The interface is currently available in English.</p></div>
        <div className="form-field"><label htmlFor="account-timezone">Time zone</label><input id="account-timezone" name="timezone" type="text" list="common-timezones" required maxLength={100} value={timezone} disabled={busy} onChange={(event) => { setTimezone(event.target.value); setSaved(false) }} aria-describedby="timezone-help" autoCapitalize="none" spellCheck={false} /><datalist id="common-timezones"><option value="Asia/Kolkata" /><option value="UTC" /><option value="Europe/London" /><option value="America/New_York" /><option value="Asia/Dubai" /></datalist><p id="timezone-help">Use an IANA time zone, such as Asia/Kolkata.</p></div>
        {error && <div className="form-error" role="alert">{error}</div>}
        {saved && <div className="form-success" role="status">Your preferences have been saved.</div>}
        <Button type="submit" disabled={busy}>{busy ? 'Saving…' : 'Save preferences'}</Button>
      </form>
    </section>
  )
}
