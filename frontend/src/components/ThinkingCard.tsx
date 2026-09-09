import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { ease } from '@/lib/utils'

const THINKING_LINES = [
  'Analyzing query language and intent...',
  'Routing through language classifier...',
  'Searching knowledge base for relevant passages...',
  'Ranking results by semantic similarity...',
  'Cross-referencing Hindi and English content...',
  'Applying relevance threshold filtering...',
  'Fusing results from multi-lingual retrieval...',
  'Constructing context from top passages...',
  'Generating grounded response with citations...',
  'Verifying response coherence and accuracy...',
]

export function ThinkingCard() {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => setElapsed(prev => prev + 100), 100)
    return () => clearInterval(timer)
  }, [])

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8, transition: { duration: 0.25 } }}
      transition={{ duration: 0.4, ease }}
      className="flex flex-col gap-3 max-w-[480px]"
    >
      <div className="flex items-center gap-2.5">
        <div className="relative w-5 h-5">
          <div className="absolute inset-0 rounded-full border-[1.5px] border-border" />
          <div className="absolute inset-0 rounded-full border-[1.5px] border-t-primary border-r-transparent border-b-transparent border-l-transparent animate-spin" />
        </div>
        <span className="text-sm font-medium text-muted-foreground">Thinking</span>
        <span className="text-xs text-muted-foreground/40 tabular-nums">
          {(elapsed / 1000).toFixed(1)}s
        </span>
      </div>

      <div className="relative h-[120px] overflow-hidden bg-card border border-border rounded-2xl">
        <div className="absolute top-0 left-0 right-0 h-10 z-[3] pointer-events-none bg-gradient-to-b from-card to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 h-10 z-[3] pointer-events-none bg-gradient-to-t from-card to-transparent" />
        <div className="absolute inset-0 z-[2] pointer-events-none shimmer-overlay" />

        <div className="p-4 px-5 text-xs leading-relaxed text-muted-foreground/40 overflow-hidden h-full">
          <div className="think-scroll">
            {[...THINKING_LINES, ...THINKING_LINES].map((line, i) => (
              <div key={i} className="py-0.5">{line}</div>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
