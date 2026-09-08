import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronRight } from 'lucide-react'
import { cn, escapeHtml, ease } from '@/lib/utils'
import type { SourceHit } from '@/types'

interface SourcesCollapsibleProps {
  sources: SourceHit[]
}

export function SourcesCollapsible({ sources }: SourcesCollapsibleProps) {
  const [open, setOpen] = useState(false)

  if (!sources.length) return null

  return (
    <div className="mt-4">
      <motion.button
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium text-muted-foreground bg-card border border-border cursor-pointer sera-transition hover:bg-secondary hover:text-foreground"
      >
        <motion.span
          animate={{ rotate: open ? 90 : 0 }}
          transition={{ duration: 0.25, ease }}
        >
          <ChevronRight size={13} />
        </motion.span>
        {sources.length} source{sources.length > 1 ? 's' : ''} retrieved
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.4, ease }}
            className="overflow-hidden mt-2"
          >
            <div className="flex flex-col gap-1.5">
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
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-card border border-border rounded-2xl p-4 sera-transition hover:border-foreground/10 hover:bg-secondary/50"
    >
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-medium text-foreground flex items-center gap-2">
          <span className="text-[10px] font-semibold bg-secondary text-muted-foreground px-2 py-0.5 rounded-lg">
            #{source.rank}
          </span>
          {escapeHtml(name)}
        </span>
        <span
          className={cn(
            'text-[11px] font-semibold px-2.5 py-0.5 rounded-lg',
            tier === 'high' && 'bg-emerald-500/8 text-emerald-400',
            tier === 'mid' && 'bg-yellow-500/8 text-yellow-400',
            tier === 'low' && 'bg-red-500/8 text-red-400'
          )}
        >
          {pct}%
        </span>
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3">
        {text}{source.text && source.text.length > 200 ? '...' : ''}
      </p>
    </motion.div>
  )
}
