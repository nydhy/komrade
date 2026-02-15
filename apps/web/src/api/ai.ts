import { post } from './http'
import { getToken } from '../state/authStore'

export interface LadderWeek {
  week: number
  title: string
  difficulty: 'low' | 'med' | 'high'
  rationale: string
  suggested_time: string
}

export interface LadderResult {
  weeks: LadderWeek[]
}

export interface TranslateResult {
  generic_answer: string
  empathetic_personalized_answer: string
  safety_flag: 'none' | 'crisis'
}

export async function generateLadder(intake: Record<string, unknown>): Promise<LadderResult> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return post<LadderResult>('/ai/ladder', { intake }, token)
}

export async function translateContext(
  message: string,
  context?: Record<string, unknown>,
): Promise<TranslateResult> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return post<TranslateResult>('/ai/translate', { message, context: context ?? {} }, token)
}

