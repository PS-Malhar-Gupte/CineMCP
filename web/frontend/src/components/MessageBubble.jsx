import { motion } from 'framer-motion'
import { User, Bot, Activity } from 'lucide-react'
import MovieCard from './MovieCard'

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  const isError = message.isError

  // Check if message contains movie data
  const movieData = message.movieData

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      {/* Avatar */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
        isUser 
          ? 'bg-primary-500' 
          : isError 
            ? 'bg-red-500' 
            : 'bg-gradient-to-br from-purple-500 to-pink-500'
      }`}>
        {isUser ? (
          <User className="w-5 h-5 text-white" />
        ) : (
          <Bot className="w-5 h-5 text-white" />
        )}
      </div>

      {/* Message Content */}
      <div className={`flex-1 ${isUser ? 'items-end max-w-[80%]' : 'items-start max-w-full'}`}>
        {/* Text Message */}
        <div className={`rounded-2xl px-4 py-3 ${
          isUser 
            ? 'bg-primary-500 text-white' 
            : isError
              ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800'
              : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm border border-gray-200 dark:border-gray-700'
        }`}>
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <p className="text-sm whitespace-pre-wrap break-words m-0">{message.content}</p>
          </div>
        </div>

        {/* Movie Cards (if any) */}
        {movieData && movieData.length > 0 && (
          <div className="mt-3 space-y-3">
            {movieData.map((movie, index) => (
              <MovieCard key={index} movie={movie} />
            ))}
          </div>
        )}
        
        {/* Evaluation Metrics */}
        {!isUser && message.evaluation && message.observability && (
          <div className="mt-3 bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-100 dark:border-gray-700 shadow-sm text-xs text-gray-600 dark:text-gray-300">
            <div className="flex items-center gap-1.5 mb-2 font-medium text-gray-700 dark:text-gray-200">
              <Activity className="w-3.5 h-3.5 text-blue-500" />
              <span>Observability</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-y-2 gap-x-4">
              <div>
                <span className="text-gray-400 block mb-0.5">Latency</span>
                <span>
                  {message.observability.find(s => s.span_name === 'agent_run_loop')?.duration_ms?.toFixed(0) || 0}ms
                </span>
              </div>
              <div>
                <span className="text-gray-400 block mb-0.5">Execution</span>
                <span>
                  {message.observability.filter(s => s.span_name === 'tool_execution').reduce((acc, s) => acc + s.duration_ms, 0).toFixed(0)}ms
                </span>
              </div>
              <div>
                <span className="text-gray-400 block mb-0.5">Relevance</span>
                <span className={message.evaluation.relevance >= 0.8 ? 'text-green-500' : 'text-amber-500'}>
                  {(message.evaluation.relevance * 100).toFixed(0)}%
                </span>
              </div>
              <div>
                <span className="text-gray-400 block mb-0.5">Confidence</span>
                <span className={message.evaluation.confidence >= 0.8 ? 'text-green-500' : 'text-amber-500'}>
                  {(message.evaluation.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div>
                <span className="text-gray-400 block mb-0.5">Precision</span>
                <span className={message.evaluation.precision >= 0.8 ? 'text-green-500' : 'text-amber-500'}>
                  {(message.evaluation.precision * 100).toFixed(0)}%
                </span>
              </div>
              <div>
                <span className="text-gray-400 block mb-0.5">Similarity</span>
                <span className={message.evaluation.similarity >= 0.8 ? 'text-green-500' : 'text-amber-500'}>
                  {(message.evaluation.similarity * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>
        )}
        
        <p className={`text-xs text-gray-500 dark:text-gray-400 mt-1 px-2 ${
          isUser ? 'text-right' : 'text-left'
        }`}>
          {message.timestamp.toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
          })}
        </p>
      </div>
    </motion.div>
  )
}
