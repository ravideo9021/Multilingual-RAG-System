import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Paperclip, ArrowUp, Sparkles } from 'lucide-react'
import { cn, ease } from '@/lib/utils'
import type { EffortLevel } from '@/types'

const EFFORT_LABELS = ['Concise', 'Balanced', 'Detailed'] as const

interface ChatInputProps {
  onSend: (text: string) => void
  onAttach: () => void
  disabled: boolean
  modelName: string
}

export function ChatInput({ onSend, onAttach, disabled, modelName }: ChatInputProps) {
  const [text, setText] = useState('')
  const [effort, setEffort] = useState<EffortLevel>(2)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = () => {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setText('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const autoGrow = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 140) + 'px'
  }

  useEffect(() => {
    textareaRef.current?.focus()
  }, [])

  const cycleEffort = () => {
    setEffort(prev => ((prev + 1) % 3) as EffortLevel)
  }

  return (
    <div className="px-5 pb-5 pt-2" style={{ background: 'linear-gradient(to top, hsl(var(--background)) 60%, transparent)' }}>
      <motion.div
        layout
        className={cn(
          'max-w-[720px] mx-auto rounded-2xl px-5 pt-3 pb-3 sera-transition',
          'bg-card border border-border',
          'focus-within:border-foreground/15 focus-within:shadow-[0_0_0_3px_hsl(var(--ring)/0.06)]'
        )}
      >
        <div className="flex items-center gap-2 mb-2">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-secondary border border-border text-[11px] font-medium text-muted-foreground">
            <Sparkles size={11} className="text-accent-glow opacity-70" />
            <span>{modelName}</span>
          </div>

          <motion.button
            whileTap={{ scale: 0.95 }}
            onClick={cycleEffort}
            className={cn(
              'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-medium cursor-pointer sera-transition',
              effort === 2
                ? 'text-accent-glow border-accent-glow/20 bg-secondary'
                : 'text-muted-foreground border-border bg-secondary hover:text-foreground'
            )}
          >
            <DynamicBars level={effort} />
            <span>{EFFORT_LABELS[effort]}</span>
          </motion.button>
        </div>

        <textarea
          ref={textareaRef}
          value={text}
          onChange={e => { setText(e.target.value); autoGrow() }}
          onKeyDown={handleKeyDown}
          rows={1}
          placeholder="Ask anything in Hindi, English, or Hinglish..."
          className="w-full bg-transparent border-none outline-none text-foreground text-[15px] leading-relaxed resize-none max-h-[140px] min-h-[28px] px-0.5 py-0 placeholder:text-muted-foreground/30"
        />

        <div className="flex items-center justify-between mt-2">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onAttach}
            className="flex items-center justify-center w-9 h-9 rounded-xl bg-transparent text-muted-foreground hover:bg-secondary hover:text-foreground sera-transition cursor-pointer"
          >
            <Paperclip size={17} />
          </motion.button>

          <motion.button
            whileHover={!disabled ? { scale: 1.05 } : undefined}
            whileTap={!disabled ? { scale: 0.95 } : undefined}
            transition={{ duration: 0.2, ease }}
            onClick={handleSend}
            disabled={disabled || !text.trim()}
            className={cn(
              'w-9 h-9 rounded-xl flex items-center justify-center cursor-pointer sera-transition',
              disabled || !text.trim()
                ? 'bg-secondary opacity-30 cursor-not-allowed text-muted-foreground'
                : 'bg-foreground text-background hover:opacity-90'
            )}
          >
            <ArrowUp size={17} />
          </motion.button>
        </div>
      </motion.div>
    </div>
  )
}

function DynamicBars({ level }: { level: number }) {
  return (
    <div className="flex items-end gap-[2px] h-3">
      {[4, 7, 10].map((h, i) => (
        <motion.span
          key={i}
          animate={{ opacity: i <= level ? 1 : 0.2, height: h }}
          transition={{ duration: 0.3, ease }}
          className="w-[2.5px] rounded-sm bg-current"
        />
      ))}
    </div>
  )
}
