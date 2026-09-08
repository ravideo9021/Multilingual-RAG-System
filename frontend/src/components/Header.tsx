import { motion } from 'framer-motion'
import { Menu } from 'lucide-react'
import { cn, springBouncy } from '@/lib/utils'

interface HeaderProps {
  embeddingModel: string
  llmProvider: string
  isLive: boolean
  onToggleSidebar: () => void
}

export function Header({ embeddingModel, llmProvider, isLive, onToggleSidebar }: HeaderProps) {
  return (
    <header className="flex items-center justify-center h-14 shrink-0 bg-bg-secondary border-b border-white/[0.06] relative z-50">
      <div className="flex items-center justify-between w-full px-4">
        {/* Left pills */}
        <div className="flex items-center gap-3">
          <motion.button
            whileTap={{ scale: 0.92 }}
            onClick={onToggleSidebar}
            className="md:hidden flex items-center justify-center w-8 h-8 rounded-lg bg-bg-card border border-white/[0.06] text-white"
          >
            <Menu size={18} />
          </motion.button>
          <Pill>{embeddingModel.toUpperCase()}</Pill>
          <Pill>FAISS</Pill>
        </div>

        {/* Center notch (adaptive-notch-navigation-bar) */}
        <div className="relative flex items-center justify-center">
          <svg className="notch-wing absolute right-full top-1/2 -translate-y-1/2 w-6 h-10 hidden lg:block" viewBox="0 0 24 40">
            <path d="M24 0 C24 0, 24 14, 16 20 C8 26, 0 28, 0 40 L24 40 L24 0Z" />
          </svg>

          <motion.div
            whileHover={{ scale: 1.02 }}
            transition={springBouncy}
            className="flex items-center gap-2.5 bg-bg-primary border border-white/10 rounded-full py-1.5 px-4 pl-2 shadow-lg shadow-black/30"
            style={{ boxShadow: '0 2px 12px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.04)' }}
          >
            <motion.div
              whileHover={{ rotate: -8, scale: 1.1 }}
              transition={springBouncy}
              className="w-7 h-7 flex items-center justify-center bg-accent rounded-full"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round">
                <path d="M12 3v18M3 12h18" />
              </svg>
            </motion.div>
            <span className="font-serif text-[17px] text-white tracking-tight">
              Multilingual RAG
            </span>
          </motion.div>

          <svg className="notch-wing absolute left-full top-1/2 -translate-y-1/2 w-6 h-10 -scale-x-100 hidden lg:block" viewBox="0 0 24 40">
            <path d="M24 0 C24 0, 24 14, 16 20 C8 26, 0 28, 0 40 L24 40 L24 0Z" />
          </svg>
        </div>

        {/* Right pills */}
        <div className="hidden md:flex items-center gap-1.5">
          <Pill live={isLive}>{llmProvider ? llmProvider.split('(')[0].trim() : 'LLM'}</Pill>
          <Pill>v0.2</Pill>
        </div>
      </div>
    </header>
  )
}

function Pill({ children, live }: { children: React.ReactNode; live?: boolean }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full font-mono text-[10px] font-medium uppercase tracking-wide border transition-colors cursor-default whitespace-nowrap',
        live
          ? 'text-emerald-400 border-emerald-400/20 bg-bg-tertiary'
          : 'text-zinc-600 border-white/[0.06] bg-bg-tertiary hover:text-zinc-500 hover:border-white/10'
      )}
    >
      {live && (
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse-dot" />
      )}
      {children}
    </span>
  )
}
