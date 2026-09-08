import { motion } from 'framer-motion'
import { FileText, Sun, Lightbulb, LayoutGrid, Globe, Zap, RefreshCw } from 'lucide-react'
import { cn, springBouncy } from '@/lib/utils'
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
    {
      icon: <FileText size={14} />,
      label: 'Indexed Chunks',
      value: stats ? stats.index_size.toLocaleString() : '0',
    },
    {
      icon: <Sun size={14} />,
      label: 'Embedder',
      value: stats?.embedding_model || 'BGE-M3',
    },
    {
      icon: <Lightbulb size={14} />,
      label: 'LLM Provider',
      value: llm || 'Not configured',
    },
    {
      icon: <LayoutGrid size={14} />,
      label: 'Index Type',
      value: stats ? stats.faiss_index_type.toUpperCase() : 'FLAT',
    },
    {
      icon: <Globe size={14} />,
      label: 'Languages',
      value: stats?.languages?.length ? stats.languages.join(', ') : '—',
    },
    {
      icon: <Zap size={14} />,
      label: 'Dimension',
      value: stats?.embedding_dim ? `${stats.embedding_dim}d` : '—',
    },
  ]

  const statusType = error
    ? 'err'
    : llm
      ? 'ok'
      : health?.status === 'ok'
        ? 'warn'
        : 'err'

  const statusText = error
    ? error
    : llm
      ? `Backend connected. LLM: ${llm}`
      : health?.status === 'ok'
        ? 'Backend connected but no LLM configured.'
        : 'Connecting to backend...'

  return (
    <div className="flex flex-col h-full">
      <div className="font-mono text-[10px] font-semibold text-zinc-600 uppercase tracking-[0.1em] px-4 pt-4 pb-3">
        System
      </div>

      {/* Stat rows */}
      <div className="px-3 flex flex-col gap-0.5">
        {rows.map((row, i) => (
          <motion.div
            key={row.label}
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04, duration: 0.3 }}
            className="flex items-center gap-2.5 py-2.5 px-2 rounded-lg transition-colors hover:bg-white/[0.02]"
          >
            <div className="w-8 h-8 rounded-lg bg-bg-card border border-white/[0.06] flex items-center justify-center shrink-0 text-zinc-500">
              {row.icon}
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-mono text-[9px] text-zinc-600 uppercase tracking-[0.08em] font-semibold">
                {row.label}
              </div>
              <div className="text-[13px] font-semibold text-white mt-px truncate">
                {row.value}
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Status card */}
      <div
        className={cn(
          'mx-3 mt-3 p-2.5 px-3.5 rounded-[10px] text-[11px] leading-relaxed border',
          statusType === 'ok' && 'bg-emerald-500/[0.08] border-emerald-500/[0.12] text-emerald-400',
          statusType === 'warn' && 'bg-yellow-500/[0.08] border-yellow-500/[0.12] text-yellow-400',
          statusType === 'err' && 'bg-red-500/[0.08] border-red-500/[0.12] text-red-400'
        )}
      >
        {statusText}
      </div>

      {/* Refresh button */}
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.97 }}
        transition={springBouncy}
        onClick={onRefresh}
        disabled={loading}
        className="flex items-center justify-center gap-1.5 mx-3 mt-2 py-2 px-4 rounded-xl bg-bg-card border border-white/[0.06] text-zinc-400 text-xs font-medium cursor-pointer transition-colors hover:bg-bg-card-hover hover:text-white hover:border-white/10 disabled:opacity-50"
      >
        <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
        {loading ? 'Loading...' : 'Refresh Stats'}
      </motion.button>
    </div>
  )
}
