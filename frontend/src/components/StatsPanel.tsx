import { motion } from 'framer-motion'
import { FileText, Sparkles, Lightbulb, LayoutGrid, Globe, Zap, RefreshCw } from 'lucide-react'
import { cn, ease } from '@/lib/utils'
import type { StatsData, HealthData } from '@/types'

interface StatsPanelProps {
  stats: StatsData | null
  health: HealthData | null
  loading: boolean
  error: string | null
  onRefresh: () => void
}

export function StatsPanel({ stats, health, loading, error, onRefresh }: StatsPanelProps) {
  const llm = health?.llm_provider || ''

  const rows = [
    { icon: <FileText size={15} />, label: 'Indexed Chunks', value: stats ? stats.index_size.toLocaleString() : '0' },
    { icon: <Sparkles size={15} />, label: 'Embedder', value: stats?.embedding_model || 'BGE-M3' },
    { icon: <Lightbulb size={15} />, label: 'LLM Provider', value: llm || 'Not configured' },
    { icon: <LayoutGrid size={15} />, label: 'Index Type', value: stats ? stats.faiss_index_type.toUpperCase() : 'FLAT' },
    { icon: <Globe size={15} />, label: 'Languages', value: stats?.languages?.length ? stats.languages.join(', ') : '—' },
    { icon: <Zap size={15} />, label: 'Dimension', value: stats?.embedding_dim ? `${stats.embedding_dim}d` : '—' },
  ]

  const statusType = error ? 'err' : llm ? 'ok' : health?.status === 'ok' ? 'warn' : 'err'
  const statusText = error
    ? error
    : llm
      ? `Backend connected. LLM: ${llm}`
      : health?.status === 'ok'
        ? 'Backend connected but no LLM configured.'
        : 'Connecting to backend...'

  return (
    <div className="flex flex-col h-full p-4 gap-3">
      <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">System</span>

      <div className="flex flex-col gap-1">
        {rows.map((row, i) => (
          <motion.div
            key={row.label}
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04, duration: 0.4, ease }}
            className="flex items-center gap-3 py-2.5 px-3 rounded-xl sera-transition hover:bg-card"
          >
            <div className="w-8 h-8 rounded-xl bg-card border border-border flex items-center justify-center shrink-0 text-muted-foreground/40">
              {row.icon}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[10px] text-muted-foreground/40 uppercase tracking-widest font-semibold">
                {row.label}
              </div>
              <div className="text-sm font-medium text-foreground mt-0.5 truncate">
                {row.value}
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      <div
        className={cn(
          'p-3.5 rounded-2xl text-xs leading-relaxed border',
          statusType === 'ok' && 'bg-emerald-500/[0.04] border-emerald-500/[0.08] text-emerald-400/80',
          statusType === 'warn' && 'bg-yellow-500/[0.04] border-yellow-500/[0.08] text-yellow-400/80',
          statusType === 'err' && 'bg-red-500/[0.04] border-red-500/[0.08] text-red-400/80'
        )}
      >
        {statusText}
      </div>

      <motion.button
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
        onClick={onRefresh}
        disabled={loading}
        className="flex items-center justify-center gap-2 py-2.5 px-4 rounded-2xl bg-card border border-border text-muted-foreground text-sm font-medium cursor-pointer sera-transition hover:bg-secondary hover:text-foreground hover:border-foreground/10 disabled:opacity-30"
      >
        <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
        {loading ? 'Loading...' : 'Refresh Stats'}
      </motion.button>
    </div>
  )
}
