import { useEffect, useId, useState, useSyncExternalStore } from 'react'
import { Button } from '../../components/Button'
import { useI18n } from '../../i18n/core'
import type { CopyKey } from '../../i18n/core'
import { onHistoryChanged } from '../../services/history-events'
import { browserRecognition, SpeechOutputController, VoiceInputController } from './speech'
import type { InputLanguage, VoiceError } from './speech'

const voiceErrors: Record<VoiceError, CopyKey> = {
  unsupported: 'Local voice input is not available in this browser. You can continue by typing.',
  language: 'An installed local recognition pack is not available for this language. You can continue by typing.',
  permission: 'Microphone permission was not granted. You can continue by typing or change permission in your browser settings.',
  microphone: 'The microphone could not be used. You can continue by typing.',
  silence: 'No final speech was detected. You can continue by typing.',
  timeout: 'The voice operation timed out and was stopped. Nothing was sent.',
  failed: 'Voice input stopped because of an error. Nothing was sent. You can continue by typing.',
  length: 'The transcript exceeded 2000 characters and was discarded. Use a shorter question or type it.',
  tts: 'Local read-aloud is unavailable or was interrupted. The displayed text remains available.',
}

function useCancellation(cancel: () => void) {
  useEffect(() => {
    const hidden = () => { if (document.visibilityState !== 'visible') cancel() }
    document.addEventListener('visibilitychange', hidden)
    window.addEventListener('pagehide', cancel)
    const unsubscribe = onHistoryChanged(cancel)
    const channel = typeof BroadcastChannel === 'undefined' ? null : new BroadcastChannel('swasthyalens-session')
    if (channel) channel.onmessage = event => { if (event.data === 'session-changed') cancel() }
    return () => { document.removeEventListener('visibilitychange', hidden); window.removeEventListener('pagehide', cancel); unsubscribe(); channel?.close(); cancel() }
  }, [cancel])
}

export function VoiceInput({ onUse, disabled }: { onUse: (text: string) => boolean; disabled: boolean }) {
  const { t } = useI18n(), id = useId()
  const [language, setLanguage] = useState<InputLanguage>('en-US')
  const [full, setFull] = useState(false)
  const [controller] = useState(() => new VoiceInputController(browserRecognition()))
  const state = useSyncExternalStore(controller.subscribe, controller.snapshot)
  useCancellation(controller.cancel)
  const active = ['checking', 'starting', 'listening', 'stopping'].includes(state.phase)
  return <div className="voice-panel" role="group" aria-label={t('Optional voice input')}>
    <label htmlFor={`${id}-language`}>{t('Recognition language')}</label>
    <select id={`${id}-language`} value={language} disabled={active || state.phase === 'review'} onChange={event => { setLanguage(event.target.value as InputLanguage); controller.cancel(); setFull(false) }}>
      <option value="en-US">English</option><option value="hi-IN">हिन्दी · Hindi</option>
    </select>
    <p className="form-hint">{t('Recognition language is separate from interface and answer language. Mixed Hindi/English recognition is not guaranteed. No language packs are downloaded here.')}</p>
    <div className="voice-actions">
      {['idle', 'error'].includes(state.phase) && <Button variant="secondary" disabled={disabled} onClick={() => { setFull(false); void controller.prepare(language) }}>{t('Check local voice availability')}</Button>}
      {state.phase === 'ready' && <Button disabled={disabled} onClick={controller.start}>{t('Start voice input')}</Button>}
      {['starting', 'listening'].includes(state.phase) && <Button onClick={controller.stop}>{t('Stop listening')}</Button>}
      {state.phase !== 'idle' && <Button variant="ghost" onClick={() => { controller.cancel(); setFull(false) }}>{t('Cancel voice input')}</Button>}
    </div>
    <div role="status" aria-live="polite" aria-atomic="true">
      {state.phase === 'checking' && <p>{t('Checking installed local recognition…')}</p>}
      {state.phase === 'ready' && <p>{t('Ready. Start voice input will request microphone access if needed.')}</p>}
      {state.phase === 'starting' && <p>{t('Waiting for microphone permission or startup. You can cancel.')}</p>}
      {state.phase === 'listening' && <p className="voice-listening">{t('Microphone active — listening. Stops after 30 seconds.')}</p>}
      {state.phase === 'stopping' && <p>{t('Stopping microphone and finishing the transcript…')}</p>}
      {state.phase === 'review' && <p>{t('Transcript ready. Review and edit it before use.')}</p>}
      {state.error && <p>{t(voiceErrors[state.error])}</p>}
    </div>
    {state.phase === 'review' && <>
      <label htmlFor={`${id}-transcript`}>{t('Review and edit transcript')}</label>
      <textarea id={`${id}-transcript`} lang={language} rows={4} maxLength={2000} value={state.transcript} onChange={event => { controller.edit(event.target.value); setFull(false) }} aria-describedby={`${id}-review`} />
      <p id={`${id}-review`} className="form-hint">{t('Check every word, number and unit. Nothing has been sent. Use the reviewed transcript in your question, then choose Send.')}</p>
      <Button variant="secondary" disabled={disabled || !state.transcript.trim()} onClick={() => { if (onUse(state.transcript)) { controller.cancel(); setFull(false) } else setFull(true) }}>{t('Use reviewed transcript')}</Button>
      {full && <p role="alert">{t('Your question and transcript together exceed 2000 characters. Shorten either before combining them.')}</p>}
    </>}
  </div>
}

export function ReadAloud({ text, language }: { text: string; language: string }) {
  const { t } = useI18n()
  const [controller] = useState(() => new SpeechOutputController(
    typeof window.speechSynthesis === 'undefined' ? null : window.speechSynthesis,
    typeof window.SpeechSynthesisUtterance === 'undefined' ? null : value => new SpeechSynthesisUtterance(value),
  ))
  const state = useSyncExternalStore(controller.subscribe, controller.snapshot)
  useCancellation(controller.stop)
  useEffect(() => () => controller.stop(), [controller, text, language])
  const active = ['starting', 'speaking', 'paused'].includes(state.phase)
  return <div className="voice-output" role="group" aria-label={t('Read displayed response aloud')}>
    {language === 'hinglish' ? <p className="form-hint">{t('Hinglish read-aloud is unavailable. Read the displayed response instead.')}</p> : <>
      <div className="voice-actions">
        <Button variant="ghost" size="sm" disabled={active} onClick={() => controller.start(text, language)}>{state.phase === 'done' ? t('Replay response') : t('Read aloud')}</Button>
        {active && <Button variant="secondary" size="sm" onClick={controller.stop}>{t('Stop playback')}</Button>}
        {state.phase === 'speaking' && <Button variant="ghost" size="sm" onClick={controller.pause}>{t('Pause playback')}</Button>}
        {state.phase === 'paused' && <Button variant="ghost" size="sm" onClick={controller.resume}>{t('Resume playback')}</Button>}
      </div>
      <div role="status" aria-live="polite">
        {state.phase === 'starting' && <p>{t('Starting local playback…')}</p>}
        {state.phase === 'speaking' && <p>{t('Reading the displayed response aloud.')}</p>}
        {state.phase === 'paused' && <p>{t('Playback paused.')}</p>}
        {state.phase === 'done' && <p>{t('Playback finished.')}</p>}
        {state.error && <p>{t(state.error === 'timeout' ? 'Playback reached its time limit and stopped.' : voiceErrors.tts)}</p>}
      </div>
    </>}
  </div>
}
