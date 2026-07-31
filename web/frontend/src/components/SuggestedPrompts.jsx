import { motion } from 'framer-motion'
import { Sparkles, TrendingUp, Star, Film } from 'lucide-react'

const prompts = [
  { text: "What's playing in theaters now?", icon: Film },
  { text: "Suggest a comedy movie", icon: Sparkles },
  { text: "Tell me about Inception", icon: Star },
  { text: "What are the upcoming releases?", icon: TrendingUp },
]

export default function SuggestedPrompts({ onPromptClick, compact = false }) {
  if (compact) {
    return (
      <div className="flex gap-2 overflow-x-auto scrollbar-hide pb-2">
        {prompts.map((prompt, index) => (
          <button
            key={index}
            onClick={() => onPromptClick(prompt.text)}
            className="flex-shrink-0 px-3 py-1.5 text-xs rounded-full 
                     bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300
                     hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            {prompt.text}
          </button>
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {prompts.map((prompt, index) => {
        const Icon = prompt.icon
        return (
          <motion.button
            key={index}
            onClick={() => onPromptClick(prompt.text)}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="flex items-center gap-3 p-4 rounded-xl
                     bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700
                     hover:border-primary-500 dark:hover:border-primary-500
                     transition-colors text-left group"
          >
            <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-primary-50 dark:bg-primary-900/20 
                          flex items-center justify-center group-hover:bg-primary-100 dark:group-hover:bg-primary-900/40
                          transition-colors">
              <Icon className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            </div>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {prompt.text}
            </span>
          </motion.button>
        )
      })}
    </div>
  )
}
