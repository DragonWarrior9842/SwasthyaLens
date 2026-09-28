import { useI18n } from '../i18n/core'
import { useEffect, useState, type FormEvent } from 'react'
import { Button, ButtonLink } from '../components/Button'
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
  const { t } = useI18n()
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
      <PageHeader eyebrow={t("YOUR ACCOUNT")} title={t("Make yourself at home")} description={t("Manage your name and preferences for your SwasthyaLens account.")} />
      {(data.status === 'loading' || (data.status === 'ready' && (data.profile.id !== userId || data.settings.user_id !== userId))) && <LoadingState title={t("Loading your account…")} />}
      {data.status === 'error' && <ErrorState title={t("Unable to load your account")} description={data.message} onRetry={() => { setData({ status: 'loading' }); setAttempt((value) => value + 1) }} />}
      {data.status === 'ready' && data.profile.id === userId && data.settings.user_id === userId && <div className="settings-grid"><ProfileForm key={`${userId}-profile`} profile={data.profile} /><PreferencesForm key={`${userId}-settings`} settings={data.settings} /></div>}
      <section className="card settings-card data-management"><h2>{t('Manage your data')}</h2><p>{t('Export current health history, or open the relevant section to delete an individual report, manual observation or assistant conversation.')}</p><div className="parameter-actions"><ButtonLink to="/exports">{t('Export health history')}</ButtonLink><ButtonLink to="/reports" variant="secondary">{t('Open reports')}</ButtonLink><ButtonLink to="/history" variant="secondary">{t('Open health history')}</ButtonLink><ButtonLink to="/assistant" variant="secondary">{t('AI Assistant')}</ButtonLink></div></section>
    </>
  )
}

function ProfileForm({ profile }: { profile: Profile }) {
  const { t, copy } = useI18n()
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
      <h2 id="profile-heading">{t("Personal details")}</h2>
      <p className="settings-card__description">{t("Choose how your name appears in your account.")}</p>
      <form className="account-form" onSubmit={(event) => { void submit(event) }} aria-busy={busy}>
        <div className="form-field"><label htmlFor="profile-name">{"" + t("Display name") + " "}<span>{t("(optional)")}</span></label><input id="profile-name" name="display_name" type="text" autoComplete="nickname" maxLength={80} value={displayName} disabled={busy} onChange={(event) => { setDisplayName(event.target.value); setSaved(false) }} aria-describedby="profile-name-help" /><p id="profile-name-help">{t("Up to 80 characters. You can leave this blank.")}</p></div>
        <div className="form-field"><span className="field-label">{t("Email address")}</span><p className="account-email">{state.status === 'authenticated' ? state.session.user.email : ''}</p></div>
        {error && <div className="form-error" role="alert">{copy(error)}</div>}
        {saved && <div className="form-success" role="status">{t("Your profile has been saved.")}</div>}
        <Button type="submit" disabled={busy}>{busy ? t("Saving…") : t("Save profile")}</Button>
      </form>
    </section>
  )
}

function PreferencesForm({ settings }: { settings: UserSettings }) {
  const { t, copy } = useI18n()
  const { checkSession } = useAuth()
  const [language, setLanguage] = useState(settings.preferred_language)
  const [assistantLanguage, setAssistantLanguage] = useState(settings.assistant_language)
  const [notifications, setNotifications] = useState(settings.in_app_notifications)
  const [savedTimezone, setSavedTimezone] = useState(settings.timezone)
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
      const updated = await saveSettings({ preferred_language: language, assistant_language: assistantLanguage, in_app_notifications: notifications, ...(selectedTimezone === savedTimezone ? {} : { timezone: selectedTimezone }) }, settings.user_id)
      if (updated.user_id !== settings.user_id) throw new Error('Mismatched settings')
      setLanguage(updated.preferred_language)
      setAssistantLanguage(updated.assistant_language)
      setNotifications(updated.in_app_notifications)
      setTimezone(updated.timezone)
      setSavedTimezone(updated.timezone)
      setSaved(true)
    } catch (failure) {
      setError(errorMessage(failure))
      if (isUnauthorized(failure) || (failure instanceof ApiError && failure.code === 'account_changed')) await checkSession()
    } finally { setBusy(false) }
  }

  return (
    <section className="card settings-card" aria-labelledby="preferences-heading">
      <h2 id="preferences-heading">{t("Your preferences")}</h2>
      <p className="settings-card__description">{t("Saved to your account, so they stay with you.")}</p>
      <form className="account-form" onSubmit={(event) => { void submit(event) }} aria-busy={busy}>
        <div className="form-field"><label htmlFor="preferred-language">{t("Interface language")}</label><select id="preferred-language" value={language} disabled={busy} onChange={(event) => { setLanguage(event.target.value === 'hi' ? 'hi' : 'en'); setSaved(false) }} aria-describedby="language-help"><option value="en">English</option><option value="hi">हिन्दी · Hindi</option></select><p id="language-help">{t("Choose the language for application menus and controls.")}</p></div>
        <div className="form-field"><label htmlFor="assistant-language">{t("Assistant response language")}</label><select id="assistant-language" value={assistantLanguage} disabled={busy} onChange={event => { const value = event.target.value; setAssistantLanguage(value === 'hi' || value === 'hinglish' ? value : 'en'); setSaved(false) }} aria-describedby="assistant-language-help"><option value="en">English</option><option value="hi">हिन्दी · Hindi</option><option value="hinglish">Hinglish · Hindi in Latin script</option></select><p id="assistant-language-help">{t("New answers use this preference. Existing messages and report text stay unchanged.")}</p></div>
        <div className="form-field"><label htmlFor="account-timezone">{t("Time zone")}</label><input id="account-timezone" name="timezone" type="text" list="common-timezones" required maxLength={64} value={timezone} disabled={busy} onChange={(event) => { setTimezone(event.target.value); setSaved(false) }} aria-describedby="timezone-help" autoCapitalize="none" spellCheck={false} /><datalist id="common-timezones"><option value="Asia/Kolkata" /><option value="UTC" /><option value="Europe/London" /><option value="America/New_York" /><option value="Asia/Dubai" /></datalist><p id="timezone-help">{t("Use an IANA time zone, such as Asia/Kolkata.")}</p></div>
        {error && <div className="form-error" role="alert">{copy(error)}</div>}
        {saved && <div className="form-success" role="status">{t("Your preferences have been saved.")}</div>}
        <label className="checkbox-label"><input type="checkbox" checked={notifications} disabled={busy} onChange={e => { setNotifications(e.target.checked); setSaved(false) }} />{t('Receive in-app operational notifications')}</label><p>{t('Applies to future report events. Existing notifications remain until dismissed or expired. No email or push is sent.')}</p>
        <Button type="submit" disabled={busy}>{busy ? t("Saving…") : t("Save preferences")}</Button>
      </form>
    </section>
  )
}
