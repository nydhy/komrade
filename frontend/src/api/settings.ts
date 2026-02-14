/**
 * User settings API client.
 */

import { get, post } from './http'
import { getToken } from '../state/authStore'

// http.ts doesn't have a `put` helper — use post with method override via fetch
async function put<T>(path: string, body: unknown, token?: string): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${path}`, {
    method: 'PUT',
    headers,
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail))
  }
  return res.json()
}

export interface UserSettings {
  user_id: number
  quiet_hours_start: string | null
  quiet_hours_end: string | null
  share_precise_location: boolean
  sos_radius_km: number | null
  updated_at: string
}

export interface UserSettingsUpdate {
  quiet_hours_start?: string | null
  quiet_hours_end?: string | null
  share_precise_location?: boolean
  sos_radius_km?: number
}

export async function getMySettings(): Promise<UserSettings> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return get<UserSettings>('/settings/me', token)
}

export async function updateMySettings(data: UserSettingsUpdate): Promise<UserSettings> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return put<UserSettings>('/settings/me', data, token)
}

export async function reportUser(reportedUserId: number, reason: string): Promise<{ status: string }> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return post<{ status: string }>('/report', { reported_user_id: reportedUserId, reason }, token)
}
