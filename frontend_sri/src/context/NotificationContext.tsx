import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'
import { getBuddies } from '../api/buddies'
import { getIncomingAlerts } from '../api/sos'
import { getToken } from '../state/authStore'

interface NotificationState {
  pendingInvites: number
  incomingSOS: number
  total: number
  refresh: () => void
}

const NotificationContext = createContext<NotificationState | null>(null)

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [pendingInvites, setPendingInvites] = useState(0)
  const [incomingSOS, setIncomingSOS] = useState(0)
  const mountedRef = useRef(true)

  const refresh = useCallback(async () => {
    if (!getToken()) return
    try {
      const [buddies, alerts] = await Promise.all([
        getBuddies(),
        getIncomingAlerts(),
      ])
      if (!mountedRef.current) return
      setPendingInvites(buddies.filter((b) => b.status === 'PENDING').length)
      setIncomingSOS(
        alerts.filter(
          (a) => a.alert_status !== 'CLOSED' && a.my_status === 'NOTIFIED'
        ).length
      )
    } catch {
      // Silently ignore errors during refresh
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    refresh()

    const interval = setInterval(refresh, 30_000)

    return () => {
      mountedRef.current = false
      clearInterval(interval)
    }
  }, [refresh])

  const total = pendingInvites + incomingSOS

  const value: NotificationState = {
    pendingInvites,
    incomingSOS,
    total,
    refresh,
  }

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  )
}

export function useNotifications(): NotificationState {
  const ctx = useContext(NotificationContext)
  if (!ctx) {
    throw new Error('useNotifications must be used within NotificationProvider')
  }
  return ctx
}
