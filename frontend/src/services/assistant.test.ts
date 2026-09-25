import { describe, expect, it } from 'vitest'
import fixture from './fixtures/assistant.json'
import { decodeAnswer, decodeConversationList, decodeThread } from './assistant'

describe('owned assistant response contract', () => {
  it('preserves the exact server-generated fact and provenance', () => {
    const thread = decodeThread(fixture)
    expect(thread.messages[0]!.answer!.facts[0]!.value).toBe('73.125')
    expect(thread.messages[0]!.provider).toBe('mock-test')
  })
  it.each([{ conversation_id: 'foreign' }, { provider: 'gemini' }, { model: 'another-model' }, { schema_version: 'unknown' }, { prompt_version: 'unknown' }, { status: 'stale' }, { status: 'failed' }, { content: 'invented prose' }, { role: 'tool' }])('rejects invalid message metadata %j', changes => {
    expect(() => decodeThread({ ...fixture, messages: [{ ...fixture.messages[0], ...changes }] })).toThrow()
  })
  it.each([{ evidence_ids: [] }, { evidence_ids: ['foreign'] }, { evidence_ids: ['e1', 'e1'] }, { explanation_code: 'diagnosis' }, { explanation_code: 'increasing' }, { limitation: 'none' }, { follow_up: 'stop_treatment' }, { scope: 'diagnostic' }])('rejects unsupported evidence and claims %j', changes => {
    const answer = fixture.messages[0]!.answer
    expect(() => decodeAnswer({ ...answer, choice: { ...answer.choice, ...changes } })).toThrow()
  })
  it.each([{ value: '73125' }, { unit: 'lb' }, { reference: '0–100' }, { source_flag: 'normal' }, { measurement_date: '2026-09-25' }, { measured_at: null }, { calculated_range_status: 'normal' }, { source_type: 'ocr' }, { evidence_id: 'foreign' }])('rejects altered facts %j', changes => {
    const a = fixture.messages[0]!.answer
    expect(() => decodeAnswer({ ...a, facts: [{ ...a.facts[0], ...changes }] })).toThrow()
  })
  it('rejects duplicates and unbounded histories', () => {
    expect(() => decodeThread({ ...fixture, messages: [...fixture.messages, ...fixture.messages] })).toThrow()
    expect(() => decodeThread({ ...fixture, messages: Array(51).fill(fixture.messages[0]) })).toThrow()
    expect(() => decodeConversationList({ conversations: Array(21).fill(fixture.conversation), provider_available: false })).toThrow()
  })
  it('accepts an honest failed provider state without an answer', () => {
    const result = decodeThread({ ...fixture, provider_available: false, messages: [{ ...fixture.messages[0], status: 'failed', answer: null, error_category: 'unavailable', provider: 'gemini', model: 'gemini-3.8-flash' }] })
    expect(result.messages[0]!.answer).toBeNull()
    expect(result.provider_available).toBe(false)
  })
  it('accepts stale state only after answer and sources were cleared', () => {
    expect(decodeThread({ ...fixture, messages: [{ ...fixture.messages[0], status: 'stale', answer: null, error_category: 'source_changed' }] }).messages[0]!.answer).toBeNull()
  })
})
