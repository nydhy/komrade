const PROFILE_UPDATED_EVENT = 'komrade:profile-updated'

export function notifyProfileUpdated(): void {
  window.dispatchEvent(new Event(PROFILE_UPDATED_EVENT))
}

export function onProfileUpdated(callback: () => void): () => void {
  window.addEventListener(PROFILE_UPDATED_EVENT, callback)
  return () => window.removeEventListener(PROFILE_UPDATED_EVENT, callback)
}

