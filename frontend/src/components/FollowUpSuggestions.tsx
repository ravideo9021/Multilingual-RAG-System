import { motion } from 'framer-motion'
import { ArrowRight } from 'lucide-react'
import { ease } from '@/lib/utils'

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
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2, duration: 0.5, ease }}
      className="flex flex-col sm:flex-row gap-2 mt-4"
    >
      {suggestions.map((s, i) => (
        <motion.button
          key={s}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 + i * 0.08, duration: 0.4, ease }}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => onSelect(s)}
          className="inline-flex items-center gap-2 px-4 py-3 rounded-2xl text-sm text-muted-foreground bg-card border border-border cursor-pointer transition-all duration-200 hover:bg-secondary hover:border-foreground/10 hover:text-foreground group"
        >
          <ArrowRight size={14} className="text-muted-foreground/20 group-hover:text-foreground/40 transition-colors duration-200 shrink-0" />
          {s}
        </motion.button>
      ))}
    </motion.div>
  )
}
