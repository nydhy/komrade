/**
 * Mood check-ins API client.
 */

import { get, post } from './http'
import { getToken } from '../state/authStore'

export interface MoodCheckin {
  id: number
  veteran_id: number
  mood_score: number
  tags: string[]
  note: string | null
  wants_company: boolean
  created_at: string
}

export interface MoodCheckinCreate {
  mood_score: number
  tags?: string[]
  note?: string | null
  wants_company?: boolean
}

export async function createCheckin(data: MoodCheckinCreate): Promise<MoodCheckin> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return post<MoodCheckin>('/checkins', data, token)
}

export async function getMyCheckins(limit = 30): Promise<MoodCheckin[]> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return get<MoodCheckin[]>(`/checkins/me?limit=${limit}`, token)
}
