import { motion } from 'framer-motion'
import { Menu, X, Database } from 'lucide-react'
import { cn, ease } from '@/lib/utils'

interface HeaderProps {
  onToggleSidebar: () => void
  sidebarOpen?: boolean
  fileCount?: number
}

export function Header({ onToggleSidebar, sidebarOpen, fileCount = 0 }: HeaderProps) {
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
          className="md:hidden flex items-center justify-center w-9 h-9 rounded-xl bg-card border border-border text-muted-foreground hover:text-foreground transition-all duration-200"
        >
          {sidebarOpen ? <X size={16} /> : <Menu size={16} />}
        </motion.button>

        <div className="flex items-center gap-2.5">
          <motion.div
            whileHover={{ rotate: -15 }}
            transition={{ duration: 0.4, ease }}
            className="w-8 h-8 rounded-xl bg-card border border-border flex items-center justify-center"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="hsl(var(--primary))" strokeWidth="2" strokeLinecap="round">
              <path d="M12 3v18M3 12h18M5.6 5.6l12.8 12.8M18.4 5.6 5.6 18.4" />
            </svg>
          </motion.div>
          <span className="text-[15px] font-semibold text-foreground tracking-tight hidden sm:inline">
            Multilingual RAG
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {fileCount > 0 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-card border border-border',
              'text-xs text-muted-foreground font-medium',
            )}
          >
            <Database size={12} className="text-emerald-400" />
            <span>{fileCount} indexed</span>
          </motion.div>
        )}

        <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-card border border-border text-xs text-muted-foreground font-medium">
          BGE-M3
        </div>
      </div>
    </motion.header>
  )
}
