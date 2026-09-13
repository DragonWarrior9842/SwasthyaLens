import type { HealthResponse } from '../types/api'
import { requestJson } from './api-client'

function decodeHealthResponse(payload: unknown): HealthResponse {
  if (
    typeof payload !== 'object' ||
    payload === null ||
    !('status' in payload) ||
    !('service' in payload) ||
    payload.status !== 'ok' ||
    payload.service !== 'swasthyalens-api'
  ) {
    throw new Error('Invalid service-health response.')
  }

  return { status: payload.status, service: payload.service }
}

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return requestJson('health', decodeHealthResponse, signal ? { signal } : {})
}
