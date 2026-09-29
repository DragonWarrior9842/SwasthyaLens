import { useI18n, displayCode } from '../i18n/core'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { useHistoryAccount, useOwnedHistory } from '../features/observations/useOwnedHistory'
import { errorMessage } from '../services/api-client'
import { createConversation, deleteConversation, getConversation, listConversations, sendMessage } from '../services/assistant'
import type { Answer, Thread } from '../services/assistant'
import { ReadAloud, VoiceInput } from '../features/voice/VoiceControls'

const suggestions = ['Explain my latest report.', 'What was my latest weight?', 'How has my Vitamin D changed over 30 days?', 'What does my report say about TSH?']
function EvidenceAnswer({ answer, voice }: { answer: Answer; voice: boolean }) {
  const { t, locale } = useI18n()
  const c = answer.calculation
  return <><p lang={answer.choice.response_language === 'hi' ? 'hi' : answer.choice.response_language === 'hinglish' ? 'hi-Latn' : 'en'}>{answer.text}</p>
    {voice && <ReadAloud text={answer.text} language={answer.choice.response_language ?? 'en'} />}
    {answer.selection === 'latest_uploaded_report' && <p>{t("Selected report: most recently uploaded. Upload time is not the measurement date. Only reviewed, explicitly published findings are included.")}</p>}
    {answer.selection === 'recent_metric' && <p>{t("Up to five recent matching observations, known measurement days first. Unknown dates cannot establish which result is clinically latest.")}</p>}
    {answer.facts.map((f, index) => { const s = answer.sources[index]!; return <details key={f.evidence_id} className="assistant-evidence"><summary>{"" + t("Source fact:") + " "}{f.label} · {f.value} {f.unit ?? t("(unit not supplied)")}</summary>
      <p>{"" + t("Measurement:") + " "}{f.measured_at ? t("{p0} · UTC instant", { p0: new Date(f.measured_at).toISOString() }) : f.measurement_date ? t("{p0} · supplied day only", { p0: f.measurement_date }) : t("Measurement date unknown")}</p>
      <p>{"" + t("Supplied reference:") + " "}{f.reference ?? t("Not supplied")}{" " + t("· Source flag:") + " "}{f.source_flag ?? t("Not supplied")}</p>
      <p>{f.source_type === 'report' ? t("Published report · page {p0} · personal review {p1}", { p0: f.page_number, p1: s.review_revision }) : t("Manually entered")}{" " + t("· observation revision") + " "}{s.revision}</p>
      <p>{"" + t("Value form:") + " "}{displayCode(locale, f.value_kind)}{f.comparator ? t(" · comparator {p0}", { p0: f.comparator }) : ''}{t(". Range interpretation remains unknown.")}</p>
      <Link to={`/history?${s.report_id ? `report_id=${s.report_id}` : 'source_type=manual'}`}>{t("Inspect current source in health history")}</Link>
    </details> })}
    {c && <details className="assistant-evidence" open><summary>{"" + t("Deterministic calculation ·") + " "}{displayCode(locale, c.metric)} · {c.window}</summary>
      <p>{"" + t("Snapshot:") + " "}{new Date(c.as_of).toISOString()}{" " + t("· calendar timezone") + " "}{c.timezone}{" " + t("· rules") + " "}{c.rules_version}</p>
      <p>{"" + t("Current:") + " "}{c.current.start}{" " + t("to") + " "}{c.current.end}. {c.current.sample_count}{" " + t("samples across") + " "}{c.current.observed_days}{" " + t("days.")}{c.current.median !== null && t(" Median of daily medians: {p0} {p1}.", { p0: c.current.median, p1: c.unit })}</p>
      <p>{"" + t("Previous:") + " "}{c.previous.start}{" " + t("to") + " "}{c.previous.end}. {c.previous.sample_count}{" " + t("samples across") + " "}{c.previous.observed_days}{" " + t("days.")}{c.previous.median !== null && t(" Median of daily medians: {p0} {p1}.", { p0: c.previous.median, p1: c.unit })}</p>
      {c.minimum_days !== null && <p>{"" + t("Each period requires") + " "}{c.minimum_days}{" " + t("observed days. Coverage:") + " "}{c.current.coverage_percent}{"" + t("% current /") + " "}{c.previous.coverage_percent}{t("% previous.")}</p>}
      {c.change && <p>{"" + t("Period change:") + " "}{c.change.absolute} {c.unit}{c.change.percent !== null && ` (${c.change.percent}%)`}.</p>}
      {c.latest_value !== null && <p>{"" + t("Latest dated value:") + " "}{c.latest_value} {c.unit} · {c.latest_day}.</p>}
      {c.previous_value !== null && <p>{"" + t("Previous dated value:") + " "}{c.previous_value} {c.unit} · {c.previous_day}.</p>}
      {c.latest_change && <p>{"" + t("Latest difference:") + " "}{c.latest_change.absolute} {c.unit}{c.latest_change.percent !== null && ` (${c.latest_change.percent}%)`}.</p>}
      <p>{"" + t("Period reason:") + " "}{displayCode(locale, c.reason)}{"" + t(". Latest comparison:") + " "}{displayCode(locale, c.latest_reason)}. {c.unknown_date_count}{" " + t("unknown-date observations and") + " "}{c.excluded_history_count}{" " + t("non-scalar observations excluded.")}</p>
      <Link to="/trends">{t("Inspect current trends and source observations")}</Link>
    </details>}
    {(answer.facts.length > 0 || c) && <p className="form-hint">{t("Educational information only. A healthcare professional can interpret measurements alongside your history. This saved answer is a snapshot; source changes remove it.")}</p>}
  </>
}

function Workspace({ owner, authFailure }: { owner: string; authFailure: (error: unknown) => void }) {
  const { t, copy } = useI18n()
  const [selected, setSelected] = useState<string | null>(null), [question, setQuestion] = useState('')
  const [voice, setVoice] = useState(false)
  const [busy, setBusy] = useState(false), [error, setError] = useState<string | null>(null), [confirmDelete, setConfirmDelete] = useState(false)
  const operation = useRef<AbortController | null>(null), pending = useRef<{ content: string; conversation: string; key: string } | null>(null), createKey = useRef<string | null>(null)
  const composer = useRef<HTMLTextAreaElement | null>(null)
  const loadList = useCallback((signal: AbortSignal) => listConversations(owner, signal), [owner])
  const list = useOwnedHistory(loadList, authFailure)
  const loadThread = useCallback((signal: AbortSignal): Promise<Thread | null> => selected ? getConversation(selected, owner, signal) : Promise.resolve(null), [selected, owner])
  const thread = useOwnedHistory(loadThread, authFailure)
  const refreshList = list.refresh, refreshThread = thread.refresh
  useEffect(() => () => operation.current?.abort(), [])
  useEffect(() => { if (selected) composer.current?.focus() }, [selected])
  useEffect(() => {
    const refresh = () => { if (document.visibilityState === 'visible') { refreshList(); refreshThread() } }
    const interval = window.setInterval(refresh, 60_000)
    document.addEventListener('visibilitychange', refresh)
    return () => { window.clearInterval(interval); document.removeEventListener('visibilitychange', refresh) }
  }, [refreshList, refreshThread])
  async function perform(task: (signal: AbortSignal) => Promise<void>) {
    if (operation.current) return
    const controller = new AbortController(); operation.current = controller; setBusy(true); setError(null)
    try { await task(controller.signal) } catch (failure) { if (!controller.signal.aborted) { setError(errorMessage(failure)); authFailure(failure) } }
    finally { operation.current = null; if (!controller.signal.aborted) setBusy(false) }
  }
  async function send(content: string) {
    if (!selected || !content.trim()) return
    if (pending.current?.content !== content || pending.current.conversation !== selected) pending.current = { content, conversation: selected, key: crypto.randomUUID() }
    const key = pending.current.key
    await perform(async signal => {
      await sendMessage(selected, content, key, owner, signal)
      if (!signal.aborted) { pending.current = null; setQuestion(''); list.refresh(); thread.refresh() }
    })
  }
  return <><PageHeader eyebrow={t("AI HEALTH ASSISTANT")} title={t("More understanding, less jargon")} description={t("Private conversations grounded in reviewed observations and deterministic trends.")} />
    <p className="assistant-notice" role="status">{t("Live AI answers are unavailable while provider acceptance is blocked. Conversations are saved privately. Clarifications and safety guidance are deterministic application responses.")}</p>
    <div className="voice-preference"><label className="checkbox-label"><input type="checkbox" checked={voice} onChange={event => setVoice(event.target.checked)} />{t('Enable optional voice for this visit')}</label>
      {voice && <p className="form-hint">{t('Only browser-reported local speech services are used. Raw audio is not saved by SwasthyaLens. Submitted text is saved as a normal private chat message. Check your surroundings before reading a health response aloud.')}</p>}
    </div>
    <div className="assistant-workspace"><Card className="assistant-sidebar"><div className="card-heading"><h2>{t("Conversations")}</h2><Button size="sm" disabled={busy} onClick={() => { void perform(async signal => { createKey.current ??= crypto.randomUUID(); const result = await createConversation(createKey.current, owner, signal); if (!signal.aborted) { createKey.current = null; setSelected(result.conversation.id); setQuestion(''); setConfirmDelete(false); list.refresh() } }) }}>{t("New chat")}</Button></div>
      {list.loading && <p role="status">{t("Loading conversations…")}</p>}{list.error && <p role="alert">{copy(list.error)}</p>}
      {list.data?.conversations.length === 0 && <><p>{t("Your health story comes first.")}</p><p>{t("Start a new chat when you have a question.")}</p></>}
      <ul className="assistant-conversations">{list.data?.conversations.map(c => <li key={c.id}><button className="button button--ghost" aria-pressed={selected === c.id} disabled={busy} onClick={() => { setSelected(c.id); setQuestion(''); setConfirmDelete(false); setError(null); pending.current = null }}>{t("Health conversation")}<br /><time dateTime={c.created_at}>{new Date(c.created_at).toLocaleString('en-GB')}</time></button></li>)}</ul>
      <Button variant="ghost" size="sm" disabled={busy} onClick={() => { list.refresh(); thread.refresh() }}>{t("Refresh conversations")}</Button><p className="form-hint">{t("Up to 20 conversations, 25 question/answer pairs each. Deleting a conversation removes its messages.")}</p>
    </Card><Card className="assistant-thread"><div className="card-heading"><h2>{selected ? t("Your conversation") : t("Ask about your records")}</h2>{selected && <Button variant="ghost" size="sm" disabled={busy} onClick={() => setConfirmDelete(true)}>{t("Delete conversation")}</Button>}</div>
      {confirmDelete && selected && <div role="group" aria-label={t("Confirm conversation deletion")}><p>{t("Delete this conversation and every saved message? This cannot be undone.")}</p><Button disabled={busy} onClick={() => { void perform(async signal => { await deleteConversation(selected, owner, signal); if (!signal.aborted) { setSelected(null); setConfirmDelete(false); pending.current = null; list.refresh() } }) }}>{t("Confirm delete conversation")}</Button><Button variant="ghost" disabled={busy} onClick={() => setConfirmDelete(false)}>{t("Cancel deletion")}</Button></div>}
      {thread.loading && selected && <p role="status">{t("Loading messages…")}</p>}{thread.error && <p role="alert">{copy(thread.error)}</p>}
      {!selected && <p>{t("Choose New chat to begin. No question is sent until you choose Send.")}</p>}
      {thread.data?.messages.length === 0 && <p>{t("No messages yet. Ask about one metric or your latest uploaded report.")}</p>}
      <div className="assistant-messages" aria-label={t("Conversation messages")}>{thread.data?.messages.map((m, index) => <article key={m.id} className={`assistant-message assistant-message--${m.role}`} aria-label={m.role === 'user' ? t("Your message") : t("Assistant response")}><h3>{m.role === 'user' ? t("You") : m.provider === 'rules' ? t("Application guidance") : m.provider === 'mock-test' ? t("Deterministic mock · testing only") : t("Assistant")}</h3>
        {m.content && <p className="assistant-user-text">{m.content}</p>}{m.answer && <EvidenceAnswer answer={m.answer} voice={voice} />}
        {m.status === 'generating' && <p role="status">{t("Answer pending. Refresh to check its status; no automatic generation retry occurs.")}</p>}
        {m.status === 'stale' && <p>{t("Source data changed or was removed. This answer and its source links have been cleared. Ask again for current evidence.")}</p>}
        {m.status === 'failed' && <p role="status">{m.error_category === 'invalid_output' ? t("The answer failed verification and was not displayed.") : m.error_category === 'timeout' ? t("The answer timed out.") : t("An AI answer is unavailable. Your question was saved.")}{" " + t("No automatic retry was made.")}</p>}
        {['failed', 'stale'].includes(m.status) && thread.data?.messages[index - 1]?.content && <Button variant="ghost" size="sm" disabled={busy} onClick={() => setQuestion(thread.data!.messages[index - 1]!.content!)}>{t("Use question again")}</Button>}
      </article>)}</div>
      {selected && <form className="assistant-composer" aria-label={t("Send an assistant question")} onSubmit={event => { event.preventDefault(); void send(question) }}>
        <div className="assistant-suggestions">{suggestions.map(prompt => <Button key={copy(prompt)} variant="ghost" size="sm" disabled={busy} onClick={() => setQuestion(copy(prompt))}>{copy(prompt)}</Button>)}</div>
        {voice && !busy && thread.data && <VoiceInput key={selected} onUse={text => { const combined = question ? `${question}\n${text}` : text; if (combined.length > 2000) return false; setQuestion(combined); composer.current?.focus(); return true }} />}
        <label htmlFor="assistant-question">{t("Your question")}</label><textarea ref={composer} id="assistant-question" value={question} onChange={event => setQuestion(event.target.value)} maxLength={2000} rows={4} required disabled={busy} aria-describedby="assistant-limit" />
        <p id="assistant-limit" className="form-hint">{question.length}{t("/2000 characters. Ask in English, Hindi or Hinglish. New answers follow your assistant preference; an explicit language request in this question overrides it. Do not use chat for emergencies.")}</p>
        <Button type="submit" disabled={busy || !question.trim() || thread.loading}>{busy ? t("Saving question…") : error ? t("Retry sending") : t("Send")}</Button>
      </form>}{error && <p role="alert" className="form-error">{copy(error)}</p>}
    </Card></div></>
}
export function AssistantPage() { const { owner, authFailure } = useHistoryAccount(); return <Workspace key={owner} owner={owner} authFailure={authFailure} /> }
