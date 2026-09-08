import { motion } from 'framer-motion'
import { Menu } from 'lucide-react'
import { cn, spring } from '@/lib/utils'

interface HeaderProps {
  embeddingModel: string
  llmProvider: string
  isLive: boolean
  onToggleSidebar: () => void
}

function NotchWing({ flip }: { flip?: boolean }) {
  return (
    <svg
      className={cn(
        'absolute top-1/2 -translate-y-1/2 w-5 h-8 hidden lg:block',
        flip ? 'left-full -scale-x-100' : 'right-full'
      )}
      viewBox="0 0 20 32"
      fill="hsl(var(--notch-bg))"
    >
      <path d="M20 0 C20 0, 20 10, 14 16 C8 22, 0 24, 0 32 L20 32Z" />
    </svg>
  )
}

export function Header({ embeddingModel, llmProvider, isLive, onToggleSidebar }: HeaderProps) {
  return (
    <header className="flex items-center justify-center h-12 shrink-0 bg-card border-b border-border relative z-50">
      <div className="flex items-center justify-between w-full px-4">
        <div className="flex items-center gap-2">
          <motion.button
            whileTap={{ scale: 0.92 }}
            onClick={onToggleSidebar}
            className="md:hidden flex items-center justify-center w-7 h-7 rounded-control bg-secondary border border-border text-muted-foreground hover:text-foreground transition-colors"
          >
            <Menu size={15} />
          </motion.button>
          <Pill>{embeddingModel.toUpperCase()}</Pill>
          <Pill>FAISS</Pill>
        </div>

        <div className="relative flex items-center justify-center">
          <NotchWing />
          <motion.div
            whileHover={{ scale: 1.02 }}
            transition={spring}
            className="flex items-center gap-2 bg-[hsl(var(--notch-bg))] border border-border rounded-full py-1 px-3.5 pl-2"
          >
            <motion.div
              whileHover={{ rotate: -8, scale: 1.1 }}
              transition={spring}
              className="w-6 h-6 flex items-center justify-center bg-warm rounded-full"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="hsl(var(--primary-foreground))" strokeWidth="2.5" strokeLinecap="round">
                <path d="M12 3v18M3 12h18" />
              </svg>
            </motion.div>
            <span className="font-serif text-[15px] text-foreground tracking-tight">
              Multilingual RAG
            </span>
          </motion.div>
          <NotchWing flip />
        </div>

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
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full font-mono text-[10px] font-medium uppercase tracking-[0.08em] border transition-colors cursor-default whitespace-nowrap',
        live
          ? 'text-emerald-400 border-emerald-400/20 bg-secondary'
          : 'text-muted-foreground border-border bg-secondary hover:text-foreground'
      )}
    >
      {live && (
        <span className="relative flex h-1.5 w-1.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-400" />
        </span>
      )}
      {children}
    </span>
  )
}
