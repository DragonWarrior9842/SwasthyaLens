import { createContext, useContext, useMemo } from 'react'
import { hindi } from './hindi'

export type Locale = 'en' | 'hi'
export type AssistantLanguage = 'en' | 'hi' | 'hinglish'
export type CopyKey = keyof typeof hindi
export type Parameters = Readonly<Record<string, string | number | null>>
export const LocaleContext = createContext<Locale>('en')

// Presentation labels for closed application enums; source fields never use this map.
export const codeLabels = {
  active: 'Active', superseded: 'Superseded', invalidated: 'Invalidated',
  scalar: 'Scalar', comparator: 'Comparator', range: 'Range', ratio: 'Ratio', text: 'Text',
  hemoglobin: 'Hemoglobin', tsh: 'TSH', vitamin_d_unspecified: 'Vitamin D (unspecified)',
  glucose_unspecified: 'Glucose (unspecified)', crp: 'CRP', weight: 'Weight', heart_rate: 'Heart rate',
  available: 'Available', no_numeric_observations: 'No numeric observations',
  current_coverage: 'Current period coverage insufficient', previous_coverage: 'Previous period coverage insufficient',
  occasional_metric: 'Occasional metric', no_dated_numeric_data: 'No dated numeric data',
  fewer_than_two_days: 'Fewer than two days', ambiguous_same_day: 'Ambiguous same day',
  provider_unavailable: 'Provider unavailable', invalid_output: 'Invalid output', timeout: 'Timeout',
} as const satisfies Record<string, CopyKey>

export function displayCode(locale: Locale, code: string) {
  return translate(locale, (codeLabels as Readonly<Record<string, string>>)[code] ?? code.replaceAll('_', ' '))
}

/** Application copy only. Never pass report fields or saved message bodies here. */
export function translate(locale: Locale, key: string, parameters: Parameters = {}): string {
  const translated = locale === 'hi' ? (hindi as Readonly<Record<string, string>>)[key] : undefined
  const template = translated?.trim() ? translated : key
  return template.replace(/\{([a-zA-Z][a-zA-Z0-9]*)\}/g, (match, name: string) =>
    Object.hasOwn(parameters, name) ? parameters[name] === null ? translate(locale, 'Not supplied') : String(parameters[name]) : match)
}

export function useI18n() {
  const locale = useContext(LocaleContext)
  return useMemo(() => ({ locale,
    t: (key: CopyKey, parameters?: Parameters) => translate(locale, key, parameters),
    // Dynamic lookup is restricted to known application-owned labels and errors.
    copy: (key: string) => translate(locale, key),
  }), [locale])
}
