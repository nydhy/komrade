/**
 * WebSocket client for real-time events.
 * Connects to ws://host/ws?token=<jwt>
 * Automatically reconnects on disconnect.
 */

import { getToken } from '../state/authStore'

export type WsEvent =
  | { event: 'sos.created'; data: unknown }
  | { event: 'sos.recipient_updated'; data: unknown }
  | { event: 'sos.closed'; data: unknown }
  | { event: 'pong' }

type EventListener = (event: WsEvent) => void

let socket: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
const listeners = new Set<EventListener>()
let pingInterval: ReturnType<typeof setInterval> | null = null

function getWsUrl(): string {
  const token = getToken()
  const explicitBase = import.meta.env.VITE_WS_URL as string | undefined
  if (explicitBase && explicitBase.trim()) {
    const base = explicitBase.trim().replace(/\/$/, '')
    return `${base}?token=${encodeURIComponent(token ?? '')}`
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  return `${proto}//${host}/ws?token=${token}`
}

export function connectWs(): void {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return // already connected
  }

  const token = getToken()
  if (!token) return

  socket = new WebSocket(getWsUrl())

  socket.onopen = () => {
    console.log('[WS] Connected')
    // Heartbeat every 30s
    pingInterval = setInterval(() => {
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send('ping')
      }
    }, 30_000)
  }

  socket.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data) as WsEvent
      listeners.forEach((fn) => fn(parsed))
    } catch {
      // ignore non-JSON
    }
  }

  socket.onclose = (event) => {
    console.log(`[WS] Disconnected (code=${event.code}, reason=${event.reason || 'n/a'}), reconnecting in 3s...`)
    cleanup()
    reconnectTimer = setTimeout(connectWs, 3000)
  }

  socket.onerror = () => {
    socket?.close()
  }
}

export function disconnectWs(): void {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  cleanup()
  socket?.close()
  socket = null
}

function cleanup() {
  if (pingInterval) {
    clearInterval(pingInterval)
    pingInterval = null
  }
}

export function onWsEvent(listener: EventListener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
