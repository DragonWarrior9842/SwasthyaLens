import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import ts from 'typescript'
import { describe, expect, it } from 'vitest'
import { hindi } from './hindi'
import { codeLabels, displayCode, translate } from './core'
import { decodeSettings } from '../services/account'
import { decodeThread } from '../services/assistant'
import fixture from '../services/fixtures/assistant.json'

const placeholders = (s: string) => [...s.matchAll(/\{([a-zA-Z][a-zA-Z0-9]*)\}/g)].map(m => m[1]).sort()
describe('local application language contract', () => {
  it('has nonempty Unicode Hindi and identical placeholders for every English key', () => {
    for (const [english, translated] of Object.entries(hindi)) {
      expect(translated.trim(), english).not.toBe('')
      expect(translated, english).not.toMatch(/�|Ã|â€|ðŸ/)
      expect(placeholders(translated), english).toEqual(placeholders(english))
      expect(translate('en', english)).toBe(english)
    }
  })
  it('audits every static t call and visible JSX text, plus central dynamic labels', () => {
    const missing: string[] = []
    function scan(dir: string) {
      for (const entry of readdirSync(dir, { withFileTypes: true })) {
        const path = join(dir, entry.name)
        if (entry.isDirectory()) { scan(path); continue }
        if (!path.endsWith('.tsx')) continue
        const source = ts.createSourceFile(path, readFileSync(path, 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
        function visit(node: ts.Node) {
          if (ts.isCallExpression(node) && node.expression.getText(source) === 't' && node.arguments[0] && ts.isStringLiteral(node.arguments[0]) && !(node.arguments[0].text in hindi)) missing.push(node.arguments[0].text)
          if (ts.isJsxText(node)) {
            const text = node.text.replace(/\s+/g, ' ').trim()
            // Language self-names, product name and file formats are intentional.
            if (/[A-Za-z]{3}/.test(text) && !['English', 'हिन्दी · Hindi', 'Hinglish · Hindi in Latin script', 'SwasthyaLens'].includes(text)) missing.push(path + ': ' + text)
          }
          ts.forEachChild(node, visit)
        }
        visit(source)
      }
    }
    scan('src')
    for (const key of Object.values(codeLabels)) if (!(key in hindi)) missing.push(key)
    expect(missing).toEqual([])
  })
  it('falls back deterministically to readable English for an unknown key', () => {
    expect(translate('hi', 'A newly introduced sentence.')).toBe('A newly introduced sentence.')
    expect(displayCode('hi', 'active')).toBe(hindi.Active)
  })
  it.each(['13.20', '18', '2.4', '<5', '>10', '0.4–4.0', '30–100', '1:80'])('does not parse or reformat source value %s', value => {
    for (const locale of ['en', 'hi'] as const) for (const unit of ['mg/dL', 'g/dL', 'ng/mL', 'mIU/L', 'kg', 'bpm']) {
      const result = translate(locale, '{value} {unit} · {source} · revision {revision}', { value, unit, source: 'Original स्रोत', revision: 1 })
      expect(result.startsWith(`${value} ${unit} · Original स्रोत`)).toBe(true)
    }
  })
  it.each(['en', 'hi', 'hinglish'])('keeps interface and assistant preferences independent: %s', language => {
    const record = { user_id: fixture.conversation.id, preferred_language: 'hi', assistant_language: language, timezone: 'UTC', created_at: '2026-09-20T00:00:00Z', updated_at: '2026-09-20T00:00:00Z' }
    expect(decodeSettings(record).assistant_language).toBe(language)
    expect(() => decodeSettings({ ...record, preferred_language: 'hinglish' })).toThrow()
    expect(() => decodeSettings({ ...record, assistant_language: 'fr' })).toThrow()
  })
  it.each(['en', 'hi', 'hinglish'])('validates frozen v2 language while preserving legacy history: %s', language => {
    const old = fixture.messages[0]!
    const message = { ...old, id: '33333333-3333-4333-8333-333333333333', sequence: old.sequence + 1, prompt_version: 'assistant-evidence-v2', schema_version: 'assistant-closed-v2', response_language: language, answer: { ...old.answer, text: 'Synthetic saved text 13.20 g/dL', choice: { ...old.answer.choice, response_language: language } } }
    const thread = decodeThread({ ...fixture, messages: [old, message] })
    expect(thread.messages[0]!.answer!.text).toBe(old.answer.text)
    expect(thread.messages[1]!.answer!.text).toBe(message.answer.text)
    expect(() => decodeThread({ ...fixture, messages: [{ ...message, response_language: 'fr' }] })).toThrow()
    expect(() => decodeThread({ ...fixture, messages: [{ ...message, response_language: undefined }] })).toThrow()
    expect(() => decodeThread({ ...fixture, messages: [{ ...message, answer: { ...message.answer, choice: { ...message.answer.choice, response_language: 'fr' } } }] })).toThrow()
  })
})
