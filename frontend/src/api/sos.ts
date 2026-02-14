/**
 * SOS alerts API client.
 */

import { get, post } from './http'
import { getToken } from '../state/authStore'

export interface SosRecipient {
  id: number
  sos_alert_id: number
  buddy_id: number
  status: string
  message: string | null
  eta_minutes: number | null
  responded_at: string | null
  buddy_email: string
  buddy_name: string
}

export interface SosAlert {
  id: number
  veteran_id: number
  trigger_type: string
  severity: string
  status: string
  created_at: string
  closed_at: string | null
  recipients: SosRecipient[]
}

/** Module 6: Incoming SOS alert as seen by a buddy */
export interface IncomingSosAlert {
  alert_id: number
  veteran_id: number
  veteran_name: string
  trigger_type: string
  severity: string
  alert_status: string
  created_at: string
  recipient_id: number
  my_status: string
  my_message: string | null
  my_eta_minutes: number | null
  responded_at: string | null
}

export interface SosRespondData {
  status: 'ACCEPTED' | 'DECLINED'
  message?: string
  eta_minutes?: number
}

export interface SosCreateOptions {
  buddy_ids?: number[]
  broadcast?: boolean
}

export async function createManualSos(
  severity: 'LOW' | 'MED' | 'HIGH',
  options?: SosCreateOptions
): Promise<SosAlert> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return post<SosAlert>('/sos', { severity, ...options }, token)
}

export async function createSosFromCheckin(
  checkinId: number,
  options?: { severity?: 'LOW' | 'MED' | 'HIGH'; buddy_ids?: number[]; broadcast?: boolean }
): Promise<SosAlert> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return post<SosAlert>(`/sos/from-checkin/${checkinId}`, options ?? {}, token)
}

export async function getSos(sosId: number): Promise<SosAlert> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return get<SosAlert>(`/sos/${sosId}`, token)
}

export async function closeSos(sosId: number): Promise<SosAlert> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return post<SosAlert>(`/sos/${sosId}/close`, {}, token)
}

export async function getMySos(limit = 20): Promise<SosAlert[]> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return get<SosAlert[]>(`/sos/me?limit=${limit}`, token)
}

/** Module 6: Get incoming SOS alerts for the current buddy */
export async function getIncomingAlerts(): Promise<IncomingSosAlert[]> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return get<IncomingSosAlert[]>('/sos/incoming', token)
}

/** Module 6: Buddy responds to an SOS alert */
export async function respondToSos(sosId: number, data: SosRespondData): Promise<SosRecipient> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return post<SosRecipient>(`/sos/${sosId}/respond`, data, token)
}
