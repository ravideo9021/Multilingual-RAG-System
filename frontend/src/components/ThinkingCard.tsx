import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'

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
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8, transition: { duration: 0.2 } }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      className="flex flex-col gap-2.5 max-w-[460px]"
    >
      {/* Header with spinner and timer */}
      <div className="flex items-center gap-2">
        <Loader2 size={16} className="text-accent animate-spin" />
        <span className="text-[13px] font-medium text-zinc-400">Thinking</span>
        <span className="font-mono text-[11px] text-zinc-600 tabular-nums">
          {(elapsed / 1000).toFixed(1)}s
        </span>
      </div>

      {/* Auto-scrolling text card with shimmer and fade overlays (ai-thinking) */}
      <div className="relative h-[110px] overflow-hidden bg-bg-card border border-white/[0.06] rounded-xl">
        {/* Top fade overlay */}
        <div className="absolute top-0 left-0 right-0 h-9 z-[3] pointer-events-none bg-gradient-to-b from-bg-card via-bg-card/80 to-transparent" />

        {/* Bottom fade overlay */}
        <div className="absolute bottom-0 left-0 right-0 h-9 z-[3] pointer-events-none bg-gradient-to-t from-bg-card via-bg-card/80 to-transparent" />

        {/* Shimmer effect */}
        <div className="absolute inset-0 z-[2] pointer-events-none thinking-shimmer animate-shimmer" />

        {/* Scrolling content */}
        <div className="p-3.5 px-4 font-mono text-[11px] leading-relaxed text-zinc-600 overflow-hidden h-full">
          <div className="animate-think-scroll">
            {[...THINKING_LINES, ...THINKING_LINES].map((line, i) => (
              <div key={i} className="py-0.5 opacity-70">{line}</div>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
