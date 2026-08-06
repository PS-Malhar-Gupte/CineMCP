import { useState, useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble'
import InputBox from './InputBox'
import SuggestedPrompts from './SuggestedPrompts'
import TypingIndicator from './TypingIndicator'
import ToolCallIndicator from './ToolCallIndicator'
import useWebSocket from '../hooks/useWebSocket'
import { getSessionId, resetSessionId, API_BASE_URL } from '../lib/session'
import { RotateCcw } from 'lucide-react'

// Turns stored history (flat [{role, content}, ...] pairs, as persisted by
// the backend's conversation store) into the shape MessageBubble expects.
function historyToMessages(history) {
  return history.map((turn, idx) => ({
    id: `history-${idx}`,
    role: turn.role,
    content: turn.content,
    timestamp: new Date(),
  }))
}

export default function ChatContainer() {
  const [messages, setMessages] = useState([])
  const [isThinking, setIsThinking] = useState(false)
  const [currentToolCall, setCurrentToolCall] = useState(null)
  const [isHistoryLoaded, setIsHistoryLoaded] = useState(false)
  const messagesEndRef = useRef(null)
  
  const { sendMessage, isConnected } = useWebSocket({
    onMessage: (data) => handleWebSocketMessage(data),
  })

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isThinking, currentToolCall])

  // Hydrate from durable history on mount, so a page refresh (or the
  // WebSocket hook's auto-reconnect-with-backoff on a dropped connection)
  // shows prior turns immediately instead of a blank chat while the socket
  // handshake is still in flight.
  useEffect(() => {
    const sessionId = getSessionId()
    fetch(`${API_BASE_URL}/api/history/${sessionId}`)
      .then((res) => (res.ok ? res.json() : { history: [] }))
      .then((data) => {
        if (data.history?.length) {
          setMessages(historyToMessages(data.history))
        }
      })
      .catch((err) => console.error('Failed to load conversation history:', err))
      .finally(() => setIsHistoryLoaded(true))
  }, [])

  const handleNewConversation = async () => {
    const sessionId = getSessionId()
    try {
      await fetch(`${API_BASE_URL}/api/history/${sessionId}`, { method: 'DELETE' })
    } catch (err) {
      console.error('Failed to clear conversation history:', err)
    }
    // Drop the local session id entirely - the next WebSocket connection
    // will have none to send, so the backend mints a fresh one and this
    // becomes a genuinely new, empty conversation rather than reusing the
    // (now-cleared) old id.
    resetSessionId(null)
    window.location.reload()
  }

  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'thinking':
        setIsThinking(true)
        setCurrentToolCall(null)
        break
        
      case 'tool_call':
        setCurrentToolCall({
          tool: data.tool,
          args: data.args
        })
        break
        
      case 'tool_result':
        setCurrentToolCall(null)
        break
        
      case 'response':
        setIsThinking(false)
        setCurrentToolCall(null)
        setMessages(prev => [...prev, {
          id: Date.now(),
          role: 'assistant',
          content: data.content,
          timestamp: new Date()
        }])
        break
        
      case 'error':
        setIsThinking(false)
        setCurrentToolCall(null)
        setMessages(prev => [...prev, {
          id: Date.now(),
          role: 'assistant',
          content: `Sorry, I encountered an error: ${data.content}`,
          timestamp: new Date(),
          isError: true
        }])
        break
        
      case 'evaluation':
        setMessages(prev => {
          const newMessages = [...prev]
          // Find the last assistant message to attach the metrics
          const lastAssistantIndex = [...newMessages].reverse().findIndex(m => m.role === 'assistant')
          if (lastAssistantIndex !== -1) {
            const actualIndex = newMessages.length - 1 - lastAssistantIndex
            newMessages[actualIndex] = {
              ...newMessages[actualIndex],
              evaluation: data.metrics,
              observability: data.observability
            }
          }
          return newMessages
        })
        break
    }
  }

  const handleSendMessage = (content) => {
    if (!content.trim() || !isConnected) return

    // Add user message to chat
    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date()
    }
    setMessages(prev => [...prev, userMessage])

    // Send to backend
    sendMessage(content.trim())
  }

  const handlePromptClick = (prompt) => {
    handleSendMessage(prompt)
  }

  return (
    <div className="flex-1 flex flex-col max-w-6xl w-full mx-auto">
      {messages.length > 0 && (
        <div className="px-4 pt-2 flex justify-end">
          <button
            onClick={handleNewConversation}
            className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            New conversation
          </button>
        </div>
      )}
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.length === 0 && !isHistoryLoaded ? null : messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center max-w-md">
              <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-200 mb-2">
                Welcome to CineMCP! 🎬
              </h2>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                Ask me anything about movies - from current releases to classic films, 
                ratings, cast information, and more!
              </p>
              <SuggestedPrompts onPromptClick={handlePromptClick} />
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            
            {currentToolCall && (
              <ToolCallIndicator 
                tool={currentToolCall.tool} 
                args={currentToolCall.args} 
              />
            )}
            
            {isThinking && !currentToolCall && <TypingIndicator />}
            
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Suggested Prompts (show when messages exist but agent is idle) */}
      {messages.length > 0 && !isThinking && (
        <div className="px-4 pb-2">
          <SuggestedPrompts onPromptClick={handlePromptClick} compact />
        </div>
      )}

      {/* Input Area */}
      <InputBox 
        onSendMessage={handleSendMessage} 
        disabled={!isConnected || isThinking}
      />
      
      {!isConnected && (
        <div className="px-4 pb-2 text-center">
          <span className="text-xs text-red-500">
            Connecting to server...
          </span>
        </div>
      )}
    </div>
  )
}
