import type { Profile, UserSettings } from '../types/auth'
import { accountPatch, accountRead } from './auth'
import { historyChanged } from './history-events'

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object'
}

function hasAuditDates(value: Record<string, unknown>): boolean {
  return typeof value.created_at === 'string' && Number.isFinite(Date.parse(value.created_at)) && typeof value.updated_at === 'string' && Number.isFinite(Date.parse(value.updated_at))
}

export function decodeProfile(value: unknown): Profile {
  if (!isRecord(value) || typeof value.id !== 'string' || !(value.display_name === null || typeof value.display_name === 'string') || !hasAuditDates(value)) throw new Error('Invalid profile')
  return { id: value.id, display_name: value.display_name, created_at: String(value.created_at), updated_at: String(value.updated_at) }
}

export function decodeSettings(value: unknown): UserSettings {
  if (!isRecord(value) || typeof value.user_id !== 'string' || !['en', 'hi'].includes(String(value.preferred_language)) || typeof value.timezone !== 'string' || !hasAuditDates(value)) throw new Error('Invalid settings')
  return { user_id: value.user_id, preferred_language: value.preferred_language as 'en' | 'hi', timezone: value.timezone, created_at: String(value.created_at), updated_at: String(value.updated_at) }
}

export function getProfile(signal?: AbortSignal) { return accountRead('/profile', decodeProfile, signal) }
export function getSettings(signal?: AbortSignal) { return accountRead('/settings', decodeSettings, signal) }
export function saveProfile(displayName: string | null, expectedOwnerId: string) { return accountPatch('/profile', { display_name: displayName }, decodeProfile, expectedOwnerId) }
export async function saveSettings({ preferred_language, timezone }: Pick<UserSettings, 'preferred_language' | 'timezone'>, expectedOwnerId: string) {
  const result = await accountPatch('/settings', { preferred_language, timezone }, decodeSettings, expectedOwnerId)
  historyChanged()
  return result
}
