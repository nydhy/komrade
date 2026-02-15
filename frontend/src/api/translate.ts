/**
 * Translation Layer API client.
 */

import { get, post } from './http'
import { getToken } from '../state/authStore'

export interface TranslateRequest {
  message: string
  context?: Record<string, unknown>
}

export interface TranslateResponse {
  empathetic_personalized_answer: string
  safety_flag: string
}

export interface TranslateHistoryItem extends TranslateResponse {
  created_at: string
  user_id: number
  question: string
  response: string
  context?: Record<string, unknown> | null
}

export async function translateText(data: TranslateRequest): Promise<TranslateResponse> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return post<TranslateResponse>('/translate', data, token)
}

export async function getTranslateHistory(limit = 10): Promise<TranslateHistoryItem[]> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return get<TranslateHistoryItem[]>(`/translate/history?limit=${limit}`, token)
}
