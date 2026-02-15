/**
 * Auth API client.
 */

import { get, post, put } from './http'
import { getToken } from '../state/authStore'

export interface UserMe {
  id: number
  email: string
  full_name: string
  role: string
  is_active: boolean
  latitude: number | null
  longitude: number | null
  created_at: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  full_name: string
  role?: string
  latitude?: number
  longitude?: number
}

export interface UpdateProfileRequest {
  full_name?: string
  latitude?: number
  longitude?: number
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export async function login(data: LoginRequest): Promise<TokenResponse> {
  return post<TokenResponse>('/auth/login', data)
}

export async function register(data: RegisterRequest): Promise<UserMe> {
  return post<UserMe>('/auth/register', data)
}

export async function getMe(token: string): Promise<UserMe> {
  return get<UserMe>('/auth/me', token)
}

/** Get current user with cache-busting to ensure fresh location data. */
export async function getMeFresh(token: string): Promise<UserMe> {
  return get<UserMe>(`/auth/me?_=${Date.now()}`, token)
}

export async function updateProfile(data: UpdateProfileRequest): Promise<UserMe> {
  const token = getToken()
  if (!token) throw new Error('Not authenticated')
  return put<UserMe>('/auth/me', data, token)
}
