/**
 * Translation Layer API client.
 */

import { get, post } from './http'
import { getToken } from '../state/authStore'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

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

export interface SttResponse {
  transcript: string
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

export async function transcribeAudio(audioFile: File): Promise<string> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')

  const form = new FormData()
  form.append('audio', audioFile)

  const res = await fetch(`${API_BASE}/stt/elevenlabs`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    const detail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
    throw new Error(detail)
  }

  const data: SttResponse = await res.json()
  if (!data.transcript?.trim()) {
    throw new Error('No transcript returned from speech-to-text')
  }
  return data.transcript.trim()
}
