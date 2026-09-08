import { useState } from 'react'
import { motion } from 'framer-motion'
import { Copy, RotateCcw, ThumbsUp, ThumbsDown, Check } from 'lucide-react'
import { cn, springBouncy } from '@/lib/utils'

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
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1, duration: 0.3 }}
      className="flex items-center gap-0.5 mt-2"
    >
      <ActionButton
        onClick={handleCopy}
        tooltip={copied ? 'Copied!' : 'Copy'}
        active={copied}
      >
        {copied ? <Check size={14} /> : <Copy size={14} />}
      </ActionButton>

      <ActionButton onClick={onRetry} tooltip="Retry">
        <RotateCcw size={14} />
      </ActionButton>

      <div className="w-px h-4 bg-white/[0.06] mx-1" />

      <ActionButton
        onClick={() => handleVote('up')}
        tooltip="Good"
        active={vote === 'up'}
      >
        <ThumbsUp size={14} />
      </ActionButton>

      <ActionButton
        onClick={() => handleVote('down')}
        tooltip="Bad"
        active={vote === 'down'}
      >
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
      whileHover={{ scale: 1.1 }}
      whileTap={{ scale: 0.9 }}
      transition={springBouncy}
      onClick={onClick}
      className={cn(
        'relative group flex items-center justify-center w-[30px] h-[30px] rounded-lg border-0 bg-transparent cursor-pointer transition-colors',
        active ? 'text-accent' : 'text-zinc-600 hover:text-zinc-400 hover:bg-bg-card'
      )}
    >
      {children}
      <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 rounded-md bg-bg-card border border-white/10 text-zinc-400 text-[10px] whitespace-nowrap pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity">
        {tooltip}
      </span>
    </motion.button>
  )
}
