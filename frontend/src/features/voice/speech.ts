// Browser speech only. No transport, persistence, medical parsing or provider fallback.
export type InputLanguage = 'en-US' | 'hi-IN'
export type VoiceError = 'unsupported' | 'language' | 'permission' | 'microphone' | 'silence' | 'timeout' | 'failed' | 'length' | 'tts'
export interface RecognitionResult { isFinal: boolean; 0: { transcript: string } }
export interface Recognition {
  processLocally?: boolean
  lang: string
  continuous: boolean
  interimResults: boolean
  maxAlternatives: number
  onstart: (() => void) | null
  onresult: ((event: { results: ArrayLike<RecognitionResult> }) => void) | null
  onerror: ((event: { error: string }) => void) | null
  onend: (() => void) | null
  start(): void
  stop(): void
  abort(): void
}
export interface RecognitionConstructor {
  new(): Recognition
  available(options: { langs: string[]; processLocally: true }): Promise<string>
}
export function browserRecognition(): RecognitionConstructor | null {
  if (typeof window === 'undefined' || !window.isSecureContext) return null
  const candidate = (window as unknown as { SpeechRecognition?: RecognitionConstructor }).SpeechRecognition
  return candidate && typeof candidate.available === 'function' ? candidate : null
}

// One microphone OR one utterance per page; starting either cancels the previous one.
let activeAudio: (() => void) | null = null
function claim(stop: () => void) { activeAudio?.(); activeAudio = stop }
function release(stop: () => void) { if (activeAudio === stop) activeAudio = null }

class Store<T> {
  protected state: T
  private listeners = new Set<() => void>()
  constructor(initial: T) { this.state = initial }
  snapshot = () => this.state
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener) } }
  protected publish(next: T) { this.state = next; this.listeners.forEach(listener => listener()) }
}
export interface InputState {
  phase: 'idle' | 'checking' | 'ready' | 'starting' | 'listening' | 'stopping' | 'review' | 'error'
  transcript: string
  error: VoiceError | null
}
export class VoiceInputController extends Store<InputState> {
  private factory: RecognitionConstructor | null
  private recognition: Recognition | null = null
  private timer: ReturnType<typeof setTimeout> | undefined
  private revision = 0
  private language: InputLanguage = 'en-US'
  private finalText = ''
  constructor(factory: RecognitionConstructor | null) { super({ phase: 'idle', transcript: '', error: null }); this.factory = factory }
  private clear() {
    clearTimeout(this.timer)
    const previous = this.recognition; this.recognition = null
    if (previous) {
      previous.onstart = previous.onresult = previous.onerror = previous.onend = null
      try { previous.abort() } catch { /* Browser teardown is best effort; no fallback. */ }
    }
    release(this.cancel)
  }
  cancel = () => { this.revision++; this.clear(); this.finalText = ''; this.publish({ phase: 'idle', transcript: '', error: null }) }
  private fail(error: VoiceError) { this.revision++; this.clear(); this.finalText = ''; this.publish({ phase: 'error', transcript: '', error }) }
  async prepare(language: InputLanguage) {
    this.cancel(); this.language = language
    if (!this.factory) { this.fail('unsupported'); return }
    const current = this.revision
    this.publish({ phase: 'checking', transcript: '', error: null })
    this.timer = setTimeout(() => this.fail('timeout'), 10_000)
    try {
      const status = await this.factory.available({ langs: [language], processLocally: true })
      if (current !== this.revision) return
      clearTimeout(this.timer)
      if (status !== 'available') { this.fail('language'); return }
      this.publish({ phase: 'ready', transcript: '', error: null })
    } catch { if (current === this.revision) this.fail('unsupported') }
  }
  start = () => {
    if (this.state.phase !== 'ready' || !this.factory) return
    try {
      const recognition = new this.factory()
      // Check BEFORE assignment: an expando property on an old API proves nothing.
      if (!('processLocally' in recognition)) { this.fail('unsupported'); return }
      recognition.processLocally = true
      if (recognition.processLocally !== true) { this.fail('unsupported'); return }
      claim(this.cancel)
      const current = this.revision
      this.recognition = recognition; this.finalText = ''
      recognition.lang = this.language; recognition.continuous = true
      recognition.interimResults = false; recognition.maxAlternatives = 1
      recognition.onstart = () => {
        if (current !== this.revision || this.state.phase !== 'starting') return
        clearTimeout(this.timer)
        this.publish({ phase: 'listening', transcript: '', error: null })
        this.timer = setTimeout(this.stop, 30_000)
      }
      recognition.onresult = event => {
        if (current !== this.revision) return
        try {
          if (!Number.isSafeInteger(event.results.length) || event.results.length > 128) throw new Error()
          const pieces: string[] = []
          for (let i = 0; i < event.results.length; i++) {
            const result = event.results[i]
            if (!result || typeof result.isFinal !== 'boolean' || typeof result[0]?.transcript !== 'string') throw new Error()
            if (result.isFinal) pieces.push(result[0].transcript)
          }
          const text = pieces.join(' ')
          if (text.length > 2000) { this.fail('length'); return }
          this.finalText = text
        } catch { this.fail('failed') }
      }
      recognition.onerror = event => {
        if (current !== this.revision) return
        this.fail(event.error === 'not-allowed' ? 'permission' : event.error === 'audio-capture' ? 'microphone' : event.error === 'no-speech' ? 'silence' : ['language-not-supported', 'service-not-allowed'].includes(event.error) ? 'language' : 'failed')
      }
      recognition.onend = () => { if (current === this.revision) this.finish() }
      this.publish({ phase: 'starting', transcript: '', error: null })
      this.timer = setTimeout(() => this.fail('timeout'), 15_000)
      recognition.start()
    } catch { this.fail('failed') }
  }
  stop = () => {
    if (!['starting', 'listening'].includes(this.state.phase)) return
    clearTimeout(this.timer)
    this.publish({ phase: 'stopping', transcript: '', error: null })
    this.timer = setTimeout(() => this.finish(), 3000)
    try { this.recognition?.stop() } catch { this.fail('failed') }
  }
  private finish() {
    const transcript = this.finalText
    this.revision++; this.clear(); this.finalText = ''
    this.publish(transcript.trim() ? { phase: 'review', transcript, error: null } : { phase: 'error', transcript: '', error: 'silence' })
  }
  edit = (transcript: string) => {
    if (this.state.phase === 'review' && transcript.length <= 2000) this.publish({ phase: 'review', transcript, error: null })
  }
}

export interface OutputState { phase: 'idle' | 'starting' | 'speaking' | 'paused' | 'done' | 'error'; error: VoiceError | null }
export function localVoice(voices: readonly SpeechSynthesisVoice[], language: string) {
  if (language !== 'en' && language !== 'hi') return undefined
  return voices.find(voice => voice.localService === true && new RegExp(`^${language}(?:-|$)`, 'i').test(voice.lang))
}
export class SpeechOutputController extends Store<OutputState> {
  private synth: SpeechSynthesis | null
  private create: ((text: string) => SpeechSynthesisUtterance) | null
  private utterance: SpeechSynthesisUtterance | null = null
  private timer: ReturnType<typeof setTimeout> | undefined
  constructor(synth: SpeechSynthesis | null, create: ((text: string) => SpeechSynthesisUtterance) | null) {
    super({ phase: 'idle', error: null }); this.synth = synth; this.create = create
  }
  private clear() {
    clearTimeout(this.timer)
    if (this.utterance) {
      this.utterance.onstart = this.utterance.onend = this.utterance.onerror = this.utterance.onpause = this.utterance.onresume = null
      this.utterance = null
      try { this.synth?.cancel() } catch { /* Do not retry or switch voices. */ }
    }
    release(this.stop)
  }
  stop = () => { this.clear(); this.publish({ phase: 'idle', error: null }) }
  private fail(error: VoiceError = 'tts') { this.clear(); this.publish({ phase: 'error', error }) }
  start = (text: string, language: string) => {
    this.stop()
    try {
      if (!this.synth || !this.create || !text.trim() || text.length > 1000) { this.fail(); return }
      const voice = localVoice(this.synth.getVoices(), language)
      if (!voice) { this.fail(); return }
      claim(this.stop)
      const utterance = this.create(text) // Exact frozen paragraph. Never normalize medical text.
      this.utterance = utterance; utterance.voice = voice; utterance.lang = voice.lang
      utterance.onstart = () => { if (this.utterance === utterance) this.publish({ phase: 'speaking', error: null }) }
      utterance.onpause = () => { if (this.utterance === utterance) this.publish({ phase: 'paused', error: null }) }
      utterance.onresume = () => { if (this.utterance === utterance) this.publish({ phase: 'speaking', error: null }) }
      utterance.onend = () => { if (this.utterance === utterance) { this.clear(); this.publish({ phase: 'done', error: null }) } }
      utterance.onerror = () => { if (this.utterance === utterance) this.fail() }
      this.publish({ phase: 'starting', error: null })
      this.timer = setTimeout(() => this.fail('timeout'), 120_000)
      this.synth.speak(utterance)
    } catch { this.fail() }
  }
  pause = () => { try { if (this.state.phase === 'speaking') this.synth?.pause() } catch { this.fail() } }
  resume = () => { try { if (this.state.phase === 'paused') this.synth?.resume() } catch { this.fail() } }
}
