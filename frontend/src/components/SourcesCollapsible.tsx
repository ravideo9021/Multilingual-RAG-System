import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronRight } from 'lucide-react'
import { cn, escapeHtml } from '@/lib/utils'
import type { SourceHit } from '@/types'

interface SourcesCollapsibleProps {
  sources: SourceHit[]
}

export function SourcesCollapsible({ sources }: SourcesCollapsibleProps) {
  const [open, setOpen] = useState(false)

  if (!sources.length) return null

  return (
    <div className="mt-3">
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-mono text-[11px] font-medium text-indigo-400 bg-accent-subtle border border-accent/20 cursor-pointer transition-colors hover:bg-accent-glow hover:text-white"
      >
        <motion.span
          animate={{ rotate: open ? 90 : 0 }}
          transition={{ type: 'spring', stiffness: 400, damping: 25 }}
        >
          <ChevronRight size={12} />
        </motion.span>
        {sources.length} source{sources.length > 1 ? 's' : ''} retrieved
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden mt-1.5"
          >
            <div className="flex flex-col gap-1">
              {sources.map((s, i) => (
                <SourceCard key={i} source={s} />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function SourceCard({ source }: { source: SourceHit }) {
  const score = source.score || 0
  const pct = Math.round(score * 100)
  const tier = score >= 0.6 ? 'high' : score >= 0.35 ? 'mid' : 'low'
  const name = source.source || source.title || `Passage ${source.rank}`
  const text = (source.text || '').slice(0, 200).replace(/\n/g, ' ')

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-bg-card border border-white/[0.06] rounded-[10px] p-2.5 px-3.5 transition-colors hover:border-white/10 hover:bg-bg-card-hover"
    >
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs font-semibold text-white flex items-center gap-1.5">
          <span className="font-mono text-[9px] font-bold bg-accent-glow text-indigo-400 px-1.5 py-0.5 rounded">
            #{source.rank}
          </span>
          {escapeHtml(name)}
        </span>
        <span
          className={cn(
            'font-mono text-[10px] font-bold px-2 py-0.5 rounded-md',
            tier === 'high' && 'bg-emerald-500/10 text-emerald-400',
            tier === 'mid' && 'bg-yellow-500/10 text-yellow-400',
            tier === 'low' && 'bg-red-500/10 text-red-400'
          )}
        >
          {pct}%
        </span>
      </div>
      <p className="text-xs text-zinc-500 leading-relaxed line-clamp-3">
        {text}{source.text && source.text.length > 200 ? '...' : ''}
      </p>
    </motion.div>
  )
}
