import { get, post } from './http'
import { getToken } from '../state/authStore'
import type { LadderWeek } from './ai'

export interface LadderChallenge {
  id: string
  week: number
  title: string
  difficulty: string
  rationale: string
  suggested_time: string | null
  status: string
  completed: boolean
}

export interface LadderPlan {
  plan_id: string
  created_at: string
  challenges: LadderChallenge[]
}

export async function saveLadderPlan(weeks: LadderWeek[]): Promise<LadderPlan> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return post<LadderPlan>('/ladder/plans', { weeks }, token)
}

export async function getLatestLadderPlan(): Promise<LadderPlan> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return get<LadderPlan>('/ladder/plans/latest', token)
}

export async function completeLadderChallenge(challengeId: string): Promise<LadderPlan> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return post<LadderPlan>(`/ladder/challenges/${challengeId}/complete`, {}, token)
}

