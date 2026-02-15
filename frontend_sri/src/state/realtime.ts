/**
 * Realtime state helpers.
 * Provides a React hook that re-fetches data when relevant WS events arrive.
 */

import { useEffect, useRef } from 'react'
import { connectWs, disconnectWs, onWsEvent, type WsEvent } from '../api/ws'

/**
 * Hook: connect to WS on mount, disconnect on unmount.
 * Calls `onEvent` when matching events arrive.
 */
export function useRealtime(
  eventNames: string[],
  onEvent: (event: WsEvent) => void,
): void {
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  useEffect(() => {
    connectWs()

    const unsub = onWsEvent((evt) => {
      if ('event' in evt && eventNames.includes(evt.event)) {
        onEventRef.current(evt)
      }
    })

    return () => {
      unsub()
      // Don't disconnect on unmount — keep connection shared
    }
  }, [eventNames.join(',')])
}

/**
 * Connect WS globally (call once at app level).
 */
export function useGlobalWs(): void {
  useEffect(() => {
    connectWs()
    return () => disconnectWs()
  }, [])
}
