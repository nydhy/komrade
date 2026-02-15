/**
 * Journey API client.
 */

import { get, post } from './http'
import { getToken } from '../state/authStore'

export interface JourneyChallenge {
  id: number
  title: string
  description: string | null
  difficulty: string
  xp_reward: number
  is_completed: boolean
  sort_order: number
  created_at: string
  completed_at: string | null
  challenge_number?: number | null
  duration?: string | null
  recommended_times?: string[]
  suggested_locations?: string[]
  interaction_required?: string | null
  comfort_zone?: 'quiet_solo' | 'small_groups' | 'active_social' | string | null
  what_this_builds?: string | null
  why_this_works?: string | null
  exit_strategy?: string | null
  you_can_also?: string[]
  modifications?: {
    if_easier_needed?: string
    if_ready_for_more?: string
  } | null
}

export interface JourneyProgress {
  user_id: number
  active_challenge_id: number | null
  xp_total: number
  level: number
  current_streak: number
  best_streak: number
  current_feeling: string | null
  next_step: string | null
  avoidance_list: string[]
  updated_at: string
}

export interface JourneyProgressResponse {
  progress: JourneyProgress
  challenges: JourneyChallenge[]
}

export interface JourneyGenerateRequest {
  anxiety_level: number
  interests: string[]
  triggers: string[]
  time_since_comfortable?: string
  end_goal?: string
  energy_times?: string[]
  location?: string
  avoid_situations?: string
  challenge_count?: number
}

export interface JourneyGenerateResponse {
  challenges: JourneyChallenge[]
  blocked_terms: string[]
  provider: string
}

export interface JourneySaveProgressRequest {
  challenge_id?: number
  completed?: boolean
  xp_earned?: number
  current_feeling?: string
  next_step?: string
  avoidance_list?: string[]
}

export interface JourneyInsightTimelineItem {
  date_label: string
  feeling: string
  xp: number
}

export interface JourneyChallengeInsights {
  challenge_id: number
  modal_subtitle: string
  success_timeline: JourneyInsightTimelineItem[]
  what_you_built: string[]
  memory_quote: string
  full_breakdown: string[]
  what_youll_build_skill: string
  what_youll_build_prepares_for: string
  practical_best_time: string
  practical_duration: string
  practical_near_you: string
  exit_strategy: string
  modification_easier: string
  modification_harder: string
}

function requireToken(): string {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return token
}

export async function getJourneyProgress(): Promise<JourneyProgressResponse> {
  return get<JourneyProgressResponse>('/api/journey/progress', requireToken())
}

export async function generateJourneyChallenges(data: JourneyGenerateRequest): Promise<JourneyGenerateResponse> {
  return post<JourneyGenerateResponse>('/api/journey/challenges/generate', data, requireToken())
}

export async function saveJourneyProgress(data: JourneySaveProgressRequest): Promise<JourneyProgressResponse> {
  return post<JourneyProgressResponse>('/api/journey/progress/save', data, requireToken())
}

export async function getJourneyChallengeInsights(challengeId: number): Promise<JourneyChallengeInsights> {
  return get<JourneyChallengeInsights>(`/api/journey/challenges/${challengeId}/insights`, requireToken())
}
