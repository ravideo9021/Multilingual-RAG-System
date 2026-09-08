import { motion } from 'framer-motion'
import { ArrowRight } from 'lucide-react'
import { springBouncy } from '@/lib/utils'

interface FollowUpSuggestionsProps {
  query: string
  onSelect: (text: string) => void
}

function generateSuggestions(query: string): string[] {
  const q = query.toLowerCase()
  if (q.includes('summarize') || q.includes('summary')) {
    return ['Go deeper on the key points', 'What are the main themes?']
  }
  if (/\?$/.test(query.trim())) {
    return ['Tell me more about this', 'Give me specific examples']
  }
  return ['Can you elaborate?', 'What else is relevant?']
}

export function FollowUpSuggestions({ query, onSelect }: FollowUpSuggestionsProps) {
  const suggestions = generateSuggestions(query)

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="flex flex-wrap gap-1.5 mt-3"
    >
      {suggestions.map((s, i) => (
        <motion.button
          key={s}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 + i * 0.06, ...springBouncy }}
          whileHover={{ y: -2, scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => onSelect(s)}
          className="inline-flex items-center gap-1.5 px-3.5 py-[7px] rounded-full text-xs font-medium font-sans text-zinc-400 bg-bg-card border border-white/[0.06] cursor-pointer transition-shadow hover:bg-accent-glow hover:border-accent hover:text-white hover:shadow-md hover:shadow-indigo-500/10"
        >
          <ArrowRight size={12} className="opacity-50" />
          {s}
        </motion.button>
      ))}
    </motion.div>
  )
}
