/**
 * Presence + Location + Nearby buddies API client.
 */

import { get, post } from './http'
import { getToken } from '../state/authStore'

export type PresenceStatus = 'AVAILABLE' | 'BUSY' | 'OFFLINE'

export interface PresenceResponse {
  user_id: number
  status: PresenceStatus
  updated_at: string
}

export interface NearbyBuddy {
  buddy_id: number
  buddy_name: string
  buddy_email: string
  trust_level: number
  presence_status: string
  distance_km: number | null
}

export async function getMyPresence(): Promise<PresenceResponse> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return get<PresenceResponse>('/presence/me', token)
}

export async function updatePresence(status: PresenceStatus): Promise<PresenceResponse> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return post<PresenceResponse>('/presence', { status }, token)
}

export async function updateLocation(latitude: number, longitude: number): Promise<{ status: string }> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return post<{ status: string }>('/location', { latitude, longitude }, token)
}

export async function getNearbyBuddies(limit = 10): Promise<NearbyBuddy[]> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return get<NearbyBuddy[]>(`/buddies/nearby?limit=${limit}`, token)
}
