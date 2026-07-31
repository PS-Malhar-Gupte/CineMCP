import { motion } from 'framer-motion'
import { Bot } from 'lucide-react'

export default function TypingIndicator() {
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
      
      <div className="bg-white dark:bg-gray-800 rounded-2xl px-5 py-3 shadow-sm 
                    border border-gray-200 dark:border-gray-700">
        <div className="flex gap-1.5">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full"
              animate={{
                y: [0, -8, 0],
              }}
              transition={{
                duration: 0.6,
                repeat: Infinity,
                delay: i * 0.15,
              }}
            />
          ))}
        </div>
      </div>
    </motion.div>
  )
}
