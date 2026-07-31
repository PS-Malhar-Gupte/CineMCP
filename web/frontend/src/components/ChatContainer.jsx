import { useState, useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble'
import InputBox from './InputBox'
import SuggestedPrompts from './SuggestedPrompts'
import TypingIndicator from './TypingIndicator'
import ToolCallIndicator from './ToolCallIndicator'
import useWebSocket from '../hooks/useWebSocket'

export default function ChatContainer() {
  const [messages, setMessages] = useState([])
  const [isThinking, setIsThinking] = useState(false)
  const [currentToolCall, setCurrentToolCall] = useState(null)
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
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.length === 0 ? (
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
