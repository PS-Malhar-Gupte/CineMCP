import { useEffect, useRef, useState } from 'react'
import { getSessionId, resetSessionId } from '../lib/session'

const WS_BASE_URL = 'ws://localhost:8000/ws/chat'

export default function useWebSocket({ onMessage }) {
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const reconnectAttemptsRef = useRef(0)

  const connect = () => {
    try {
      // Every connection - including auto-reconnects after a drop - sends
      // the persisted session_id, so the backend can rehydrate this
      // session's conversation history instead of starting blank. Without
      // this, the exponential-backoff reconnect in onclose below would
      // silently wipe multi-turn context on every wifi blip/tab sleep.
      const sessionId = getSessionId()
      const ws = new WebSocket(`${WS_BASE_URL}?session_id=${encodeURIComponent(sessionId)}`)
      
      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        reconnectAttemptsRef.current = 0
      }
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          // The backend resolves/mints the session_id for this connection and
          // echoes it back immediately after accept - persist it so a first-
          // ever visit (no local id yet) still gets continuity from here on.
          if (data.type === 'session' && data.session_id) {
            resetSessionId(data.session_id)
          }
          onMessage(data)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
      
      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setIsConnected(false)
        
        // Attempt to reconnect with exponential backoff
        const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000)
        reconnectAttemptsRef.current += 1
        
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log(`Reconnecting... (attempt ${reconnectAttemptsRef.current})`)
          connect()
        }, delay)
      }
      
      wsRef.current = ws
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
    }
  }

  useEffect(() => {
    connect()
    
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const sendMessage = (content) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'message',
        content: content
      }))
    } else {
      console.error('WebSocket is not connected')
    }
  }

  return {
    sendMessage,
    isConnected
  }
}
