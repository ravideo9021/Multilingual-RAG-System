import { motion } from 'framer-motion'
import { Menu, X } from 'lucide-react'
import { cn, ease } from '@/lib/utils'

interface HeaderProps {
  embeddingModel: string
  llmProvider: string
  isLive: boolean
  onToggleSidebar: () => void
  sidebarOpen?: boolean
}

export function Header({ embeddingModel, llmProvider, isLive, onToggleSidebar, sidebarOpen }: HeaderProps) {
  return (
    <motion.header
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease }}
      className="flex items-center justify-between h-14 px-5 shrink-0 bg-background/80 backdrop-blur-xl border-b border-border/50 relative z-50"
    >
      <div className="flex items-center gap-3">
        <motion.button
          whileTap={{ scale: 0.9 }}
          onClick={onToggleSidebar}
          className="md:hidden flex items-center justify-center w-9 h-9 rounded-xl bg-card border border-border text-muted-foreground hover:text-foreground sera-transition"
        >
          {sidebarOpen ? <X size={16} /> : <Menu size={16} />}
        </motion.button>

        <div className="flex items-center gap-2.5">
          <motion.div
            whileHover={{ rotate: -15 }}
            transition={{ duration: 0.4, ease }}
            className="w-8 h-8 rounded-xl bg-card border border-border flex items-center justify-center"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="hsl(var(--accent-glow))" strokeWidth="2" strokeLinecap="round">
              <path d="M12 3v18M3 12h18M5.6 5.6l12.8 12.8M18.4 5.6 5.6 18.4" />
            </svg>
          </motion.div>
          <span className="text-[15px] font-semibold text-foreground tracking-tight hidden sm:inline">
            Multilingual RAG
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {isLive && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-card border border-border"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
            </span>
            <span className="text-xs text-muted-foreground font-medium hidden sm:inline">
              {llmProvider ? llmProvider.split('(')[0].trim() : 'Connected'}
            </span>
          </motion.div>
        )}

        <div className={cn(
          'hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-card border border-border text-xs text-muted-foreground font-medium',
        )}>
          {embeddingModel.toUpperCase()}
        </div>
      </div>
    </motion.header>
  )
}
