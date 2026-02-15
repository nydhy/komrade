/**
 * Buddies API client.
 */

import { get, post } from './http'
import { getToken } from '../state/authStore'

export interface BuddyLink {
  id: number
  veteran_id: number
  buddy_id: number
  status: string
  trust_level: number
  created_at: string
}

export interface BuddyLinkWithUser extends BuddyLink {
  other_email: string
  other_name: string
  other_latitude: number | null
  other_longitude: number | null
  other_location_label: string | null
  other_presence_status: string | null
}

export interface InviteRequest {
  buddy_email?: string
  buddy_id?: number
  trust_level?: number
}

export async function inviteBuddy(data: InviteRequest): Promise<BuddyLink> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return post<BuddyLink>('/buddies/invite', data, token)
}

export async function acceptInvite(linkId: number): Promise<BuddyLink> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return post<BuddyLink>(`/buddies/${linkId}/accept`, {}, token)
}

export async function blockLink(linkId: number): Promise<BuddyLink> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return post<BuddyLink>(`/buddies/${linkId}/block`, {}, token)
}

export async function getBuddies(): Promise<BuddyLinkWithUser[]> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return get<BuddyLinkWithUser[]>('/buddies', token)
}
