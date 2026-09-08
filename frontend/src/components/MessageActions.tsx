import { useState } from 'react'
import { motion } from 'framer-motion'
import { Copy, RotateCcw, ThumbsUp, ThumbsDown, Check } from 'lucide-react'
import { cn, ease } from '@/lib/utils'

interface MessageActionsProps {
  answer: string
  onRetry: () => void
}

export function MessageActions({ answer, onRetry }: MessageActionsProps) {
  const [copied, setCopied] = useState(false)
  const [vote, setVote] = useState<'up' | 'down' | null>(null)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(answer)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const handleVote = (v: 'up' | 'down') => {
    setVote(prev => prev === v ? null : v)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1, duration: 0.35, ease }}
      className="flex items-center gap-1 mt-3"
    >
      <ActionButton onClick={handleCopy} tooltip={copied ? 'Copied!' : 'Copy'} active={copied}>
        {copied ? <Check size={14} /> : <Copy size={14} />}
      </ActionButton>

      <ActionButton onClick={onRetry} tooltip="Retry">
        <RotateCcw size={14} />
      </ActionButton>

      <div className="w-px h-4 bg-border mx-1.5" />

      <ActionButton onClick={() => handleVote('up')} tooltip="Good" active={vote === 'up'}>
        <ThumbsUp size={14} />
      </ActionButton>

      <ActionButton onClick={() => handleVote('down')} tooltip="Bad" active={vote === 'down'}>
        <ThumbsDown size={14} />
      </ActionButton>
    </motion.div>
  )
}

function ActionButton({
  children,
  onClick,
  tooltip,
  active,
}: {
  children: React.ReactNode
  onClick: () => void
  tooltip: string
  active?: boolean
}) {
  return (
    <motion.button
      whileHover={{ scale: 1.08 }}
      whileTap={{ scale: 0.92 }}
      onClick={onClick}
      className={cn(
        'relative group flex items-center justify-center w-8 h-8 rounded-xl border-0 bg-transparent cursor-pointer sera-transition',
        active ? 'text-accent-glow' : 'text-muted-foreground/40 hover:text-foreground hover:bg-card'
      )}
    >
      {children}
      <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2.5 py-1 rounded-lg bg-card border border-border text-muted-foreground text-[10px] whitespace-nowrap pointer-events-none opacity-0 group-hover:opacity-100 sera-transition">
        {tooltip}
      </span>
    </motion.button>
  )
}
