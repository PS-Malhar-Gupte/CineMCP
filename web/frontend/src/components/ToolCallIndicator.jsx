import { motion } from 'framer-motion'
import { Wrench, Bot } from 'lucide-react'

export default function ToolCallIndicator({ tool, args }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex gap-3"
    >
      <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center 
                    bg-gradient-to-br from-purple-500 to-pink-500">
        <Bot className="w-5 h-5 text-white" />
      </div>
      
      <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 
                    rounded-2xl px-4 py-3 shadow-sm">
        <div className="flex items-center gap-2 mb-1">
          <Wrench className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          <span className="text-sm font-medium text-amber-900 dark:text-amber-100">
            Calling tool: {tool}
          </span>
        </div>
        {args && Object.keys(args).length > 0 && (
          <div className="text-xs text-amber-700 dark:text-amber-300 font-mono">
            {JSON.stringify(args, null, 2)}
          </div>
        )}
      </div>
    </motion.div>
  )
}
