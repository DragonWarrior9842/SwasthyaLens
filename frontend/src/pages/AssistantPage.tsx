import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { useHistoryAccount, useOwnedHistory } from '../features/observations/useOwnedHistory'
import { errorMessage } from '../services/api-client'
import { createConversation, deleteConversation, getConversation, listConversations, sendMessage } from '../services/assistant'
import type { Answer, Thread } from '../services/assistant'

const suggestions = ['Explain my latest report.', 'What was my latest weight?', 'How has my Vitamin D changed over 30 days?', 'What does my report say about TSH?']
function EvidenceAnswer({ answer }: { answer: Answer }) {
  const c = answer.calculation
  return <><p>{answer.text}</p>
    {answer.selection === 'latest_uploaded_report' && <p>Selected report: most recently uploaded. Upload time is not the measurement date. Only reviewed, explicitly published findings are included.</p>}
    {answer.selection === 'recent_metric' && <p>Up to five recent matching observations, known measurement days first. Unknown dates cannot establish which result is clinically latest.</p>}
    {answer.facts.map((f, index) => { const s = answer.sources[index]!; return <details key={f.evidence_id} className="assistant-evidence"><summary>Source fact: {f.label} · {f.value} {f.unit ?? '(unit not supplied)'}</summary>
      <p>Measurement: {f.measured_at ? `${new Date(f.measured_at).toISOString()} · UTC instant` : f.measurement_date ? `${f.measurement_date} · supplied day only` : 'Measurement date unknown'}</p>
      <p>Supplied reference: {f.reference ?? 'Not supplied'} · Source flag: {f.source_flag ?? 'Not supplied'}</p>
      <p>{f.source_type === 'report' ? `Published report · page ${f.page_number} · personal review ${s.review_revision}` : 'Manually entered'} · observation revision {s.revision}</p>
      <p>Value form: {f.value_kind}{f.comparator ? ` · comparator ${f.comparator}` : ''}. Range interpretation remains unknown.</p>
      <Link to={`/history?${s.report_id ? `report_id=${s.report_id}` : 'source_type=manual'}`}>Inspect current source in health history</Link>
    </details> })}
    {c && <details className="assistant-evidence" open><summary>Deterministic calculation · {c.metric.replaceAll('_', ' ')} · {c.window}</summary>
      <p>Snapshot: {new Date(c.as_of).toISOString()} · calendar timezone {c.timezone} · rules {c.rules_version}</p>
      <p>Current: {c.current.start} to {c.current.end}. {c.current.sample_count} samples across {c.current.observed_days} days.{c.current.median !== null && ` Median of daily medians: ${c.current.median} ${c.unit}.`}</p>
      <p>Previous: {c.previous.start} to {c.previous.end}. {c.previous.sample_count} samples across {c.previous.observed_days} days.{c.previous.median !== null && ` Median of daily medians: ${c.previous.median} ${c.unit}.`}</p>
      {c.minimum_days !== null && <p>Each period requires {c.minimum_days} observed days. Coverage: {c.current.coverage_percent}% current / {c.previous.coverage_percent}% previous.</p>}
      {c.change && <p>Period change: {c.change.absolute} {c.unit}{c.change.percent !== null && ` (${c.change.percent}%)`}.</p>}
      {c.latest_value !== null && <p>Latest dated value: {c.latest_value} {c.unit} · {c.latest_day}.</p>}
      {c.previous_value !== null && <p>Previous dated value: {c.previous_value} {c.unit} · {c.previous_day}.</p>}
      {c.latest_change && <p>Latest difference: {c.latest_change.absolute} {c.unit}{c.latest_change.percent !== null && ` (${c.latest_change.percent}%)`}.</p>}
      <p>Period reason: {c.reason.replaceAll('_', ' ')}. Latest comparison: {c.latest_reason.replaceAll('_', ' ')}. {c.unknown_date_count} unknown-date observations and {c.excluded_history_count} non-scalar observations excluded.</p>
      <Link to="/trends">Inspect current trends and source observations</Link>
    </details>}
    {(answer.facts.length > 0 || c) && <p className="form-hint">Educational information only. A healthcare professional can interpret measurements alongside your history. This saved answer is a snapshot; source changes remove it.</p>}
  </>
}

function Workspace({ owner, authFailure }: { owner: string; authFailure: (error: unknown) => void }) {
  const [selected, setSelected] = useState<string | null>(null), [question, setQuestion] = useState('')
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
  return <><PageHeader eyebrow="AI HEALTH ASSISTANT" title="More understanding, less jargon" description="Private conversations grounded in reviewed observations and deterministic trends." />
    <p className="assistant-notice" role="status">Live AI answers are unavailable while provider acceptance is blocked. Conversations are saved privately. Clarifications and safety guidance are deterministic application responses.</p>
    <div className="assistant-workspace"><Card className="assistant-sidebar"><div className="card-heading"><h2>Conversations</h2><Button size="sm" disabled={busy} onClick={() => { void perform(async signal => { createKey.current ??= crypto.randomUUID(); const result = await createConversation(createKey.current, owner, signal); if (!signal.aborted) { createKey.current = null; setSelected(result.conversation.id); setQuestion(''); setConfirmDelete(false); list.refresh() } }) }}>New chat</Button></div>
      {list.loading && <p role="status">Loading conversations…</p>}{list.error && <p role="alert">{list.error}</p>}
      {list.data?.conversations.length === 0 && <><p>Your health story comes first.</p><p>Start a new chat when you have a question.</p></>}
      <ul className="assistant-conversations">{list.data?.conversations.map(c => <li key={c.id}><button className="button button--ghost" aria-pressed={selected === c.id} disabled={busy} onClick={() => { setSelected(c.id); setQuestion(''); setConfirmDelete(false); setError(null); pending.current = null }}>Health conversation<br /><time dateTime={c.created_at}>{new Date(c.created_at).toLocaleString('en-GB')}</time></button></li>)}</ul>
      <Button variant="ghost" size="sm" disabled={busy} onClick={() => { list.refresh(); thread.refresh() }}>Refresh conversations</Button><p className="form-hint">Up to 20 conversations, 25 question/answer pairs each. Deleting a conversation removes its messages.</p>
    </Card><Card className="assistant-thread"><div className="card-heading"><h2>{selected ? 'Your conversation' : 'Ask about your records'}</h2>{selected && <Button variant="ghost" size="sm" disabled={busy} onClick={() => setConfirmDelete(true)}>Delete conversation</Button>}</div>
      {confirmDelete && selected && <div role="group" aria-label="Confirm conversation deletion"><p>Delete this conversation and every saved message? This cannot be undone.</p><Button disabled={busy} onClick={() => { void perform(async signal => { await deleteConversation(selected, owner, signal); if (!signal.aborted) { setSelected(null); setConfirmDelete(false); pending.current = null; list.refresh() } }) }}>Confirm delete conversation</Button><Button variant="ghost" disabled={busy} onClick={() => setConfirmDelete(false)}>Cancel deletion</Button></div>}
      {thread.loading && selected && <p role="status">Loading messages…</p>}{thread.error && <p role="alert">{thread.error}</p>}
      {!selected && <p>Choose New chat to begin. No question is sent until you choose Send.</p>}
      {thread.data?.messages.length === 0 && <p>No messages yet. Ask about one metric or your latest uploaded report.</p>}
      <div className="assistant-messages" aria-label="Conversation messages">{thread.data?.messages.map((m, index) => <article key={m.id} className={`assistant-message assistant-message--${m.role}`} aria-label={m.role === 'user' ? 'Your message' : 'Assistant response'}><h3>{m.role === 'user' ? 'You' : m.provider === 'rules' ? 'Application guidance' : m.provider === 'mock-test' ? 'Deterministic mock · testing only' : 'Assistant'}</h3>
        {m.content && <p className="assistant-user-text">{m.content}</p>}{m.answer && <EvidenceAnswer answer={m.answer} />}
        {m.status === 'generating' && <p role="status">Answer pending. Refresh to check its status; no automatic generation retry occurs.</p>}
        {m.status === 'stale' && <p>Source data changed or was removed. This answer and its source links have been cleared. Ask again for current evidence.</p>}
        {m.status === 'failed' && <p role="status">{m.error_category === 'invalid_output' ? 'The answer failed verification and was not displayed.' : m.error_category === 'timeout' ? 'The answer timed out.' : 'An AI answer is unavailable. Your question was saved.'} No automatic retry was made.</p>}
        {['failed', 'stale'].includes(m.status) && thread.data?.messages[index - 1]?.content && <Button variant="ghost" size="sm" disabled={busy} onClick={() => setQuestion(thread.data!.messages[index - 1]!.content!)}>Use question again</Button>}
      </article>)}</div>
      {selected && <form className="assistant-composer" aria-label="Send an assistant question" onSubmit={event => { event.preventDefault(); void send(question) }}>
        <div className="assistant-suggestions">{suggestions.map(prompt => <Button key={prompt} variant="ghost" size="sm" disabled={busy} onClick={() => setQuestion(prompt)}>{prompt}</Button>)}</div>
        <label htmlFor="assistant-question">Your question</label><textarea ref={composer} id="assistant-question" value={question} onChange={event => setQuestion(event.target.value)} maxLength={2000} rows={4} required disabled={busy} aria-describedby="assistant-limit" />
        <p id="assistant-limit" className="form-hint">{question.length}/2000 characters. English questions only in this phase. Do not use chat for emergencies.</p>
        <Button type="submit" disabled={busy || !question.trim() || thread.loading}>{busy ? 'Saving question…' : error ? 'Retry sending' : 'Send'}</Button>
      </form>}{error && <p role="alert" className="form-error">{error}</p>}
    </Card></div></>
}
export function AssistantPage() { const { owner, authFailure } = useHistoryAccount(); return <Workspace key={owner} owner={owner} authFailure={authFailure} /> }
